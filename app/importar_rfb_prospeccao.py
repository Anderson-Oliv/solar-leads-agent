"""
Importa e pontua uma leva de CNPJs a partir dos dados abertos da Receita Federal
(dadosabertos.rfb.gov.br), pra Sprint 02 tarefa 1 do Sistema de Leads para Empresas:
"Importar base maior de CNPJs (target: 10k+ empresas)".

Le uma particao (Empresas + Estabelecimentos, mesmo indice N) ja baixada e
descompactada em data/rfb/, filtra por UF prioritaria do ICP + situacao cadastral
ativa, junta os dois arquivos por CNPJ_BASICO, resolve a descricao do CNAE via
Cnaes.csv, monta o dict esperado por calcular_score() (app/scoring.py) e roda o
score de cada empresa. Salva o resultado em data/output/.

Uso:
    python3 app/importar_rfb_prospeccao.py --dir data/rfb
"""

import argparse
import csv
import glob
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent
sys.path.insert(0, str(APP_DIR))

from scoring import calcular_score  # noqa: E402

UF_PRIORITARIAS = {"SP", "MG", "GO", "MT", "MS", "PR"}
SITUACAO_ATIVA = "02"

PORTE_CODIGOS = {
    "00": None,
    "01": "MICRO EMPRESA",
    "03": "EMPRESA DE PEQUENO PORTE",
    "05": "DEMAIS",
}

FIELDNAMES = [
    "cnpj", "razao_social", "nome_fantasia", "municipio_codigo", "uf",
    "cnae_principal", "cnae_descricao", "capital_social", "porte",
    "data_inicio_atividade", "tipo_empresa", "score", "classificacao",
    "score_segmento", "score_porte_financeiro", "score_tempo_empresa",
    "score_localizacao", "score_estrutura_societaria",
]


def _achar_arquivo(base_dir: Path, sufixo: str) -> Path:
    candidatos = list(base_dir.glob(f"*{sufixo}"))
    if not candidatos:
        raise FileNotFoundError(f"Nenhum arquivo terminado em '{sufixo}' encontrado em {base_dir}")
    return candidatos[0]


def _achar_arquivos(base_dir: Path, sufixo: str) -> list[Path]:
    """As particoes de Empresas/Estabelecimentos NAO sao alinhadas pelo mesmo
    CNPJ_BASICO (confirmado empiricamente: so ~63% de overlap entre particoes de
    mesmo indice) - por isso precisamos varrer TODAS as particoes disponiveis,
    nao so uma."""
    candidatos = sorted(base_dir.glob(f"*{sufixo}"))
    if not candidatos:
        raise FileNotFoundError(f"Nenhum arquivo terminado em '{sufixo}' encontrado em {base_dir}")
    return candidatos


def carregar_cnaes(base_dir: Path) -> Dict[str, str]:
    path = _achar_arquivo(base_dir, "CNAECSV")
    cnaes: Dict[str, str] = {}
    with open(path, encoding="latin-1", newline="") as f:
        for row in csv.reader(f, delimiter=";", quotechar='"'):
            if len(row) < 2:
                continue
            codigo, descricao = row[0], row[1]
            cnaes[codigo] = descricao
    return cnaes


def carregar_empresas_necessarias(base_dir: Path, necessarios: set) -> Dict[str, Dict[str, Optional[str]]]:
    """Varre TODAS as particoes de Empresas, guardando so as CNPJ_BASICO que
    aparecem em `necessarios` (os estabelecimentos ja filtrados) - evita carregar
    os ~45M registros de todas as particoes em memoria."""
    empresas: Dict[str, Dict[str, Optional[str]]] = {}
    faltando = set(necessarios)
    for path in _achar_arquivos(base_dir, "EMPRECSV"):
        if not faltando:
            break
        print(f"  lendo {path.name} ({len(faltando)} CNPJ_BASICO ainda faltando)...")
        with open(path, encoding="latin-1", newline="") as f:
            for row in csv.reader(f, delimiter=";", quotechar='"'):
                if len(row) < 6:
                    continue
                cnpj_basico = row[0]
                if cnpj_basico not in faltando:
                    continue
                razao_social, _natureza, _qualificacao, capital_social, porte = row[1:6]
                empresas[cnpj_basico] = {
                    "razao_social": razao_social,
                    "capital_social": capital_social.replace(",", "."),
                    "porte": PORTE_CODIGOS.get(porte),
                }
                faltando.discard(cnpj_basico)
    if faltando:
        print(f"  aviso: {len(faltando)} CNPJ_BASICO nao encontrados em nenhuma particao de Empresas.")
    return empresas


def _data_iso(valor: str) -> Optional[str]:
    valor = (valor or "").strip()
    if len(valor) != 8 or not valor.isdigit():
        return None
    try:
        return datetime.strptime(valor, "%Y%m%d").date().isoformat()
    except ValueError:
        return None


def filtrar_estabelecimentos(base_dir: Path, cnaes: Dict[str, str]) -> list[dict]:
    """Varre TODAS as particoes de Estabelecimentos (mesmo motivo do
    carregar_empresas_necessarias: particoes nao sao alinhadas por CNPJ_BASICO)."""
    linhas = []
    total_lidos = 0
    total_filtrados = 0

    for path in _achar_arquivos(base_dir, "ESTABELE"):
        print(f"  lendo {path.name}...")
        with open(path, encoding="latin-1", newline="") as f:
            for row in csv.reader(f, delimiter=";", quotechar='"'):
                total_lidos += 1
                if len(row) < 21:
                    continue

                cnpj_basico = row[0]
                cnpj_ordem = row[1]
                cnpj_dv = row[2]
                matriz_filial = row[3]
                nome_fantasia = row[4]
                situacao_cadastral = row[5]
                data_inicio_atividade = row[10]
                cnae_principal = row[11]
                uf = row[19]
                municipio = row[20]

                if situacao_cadastral != SITUACAO_ATIVA:
                    continue
                if uf not in UF_PRIORITARIAS:
                    continue

                total_filtrados += 1
                cnae_descricao = cnaes.get(cnae_principal)

                registro = {
                    "cnpj_basico": cnpj_basico,
                    "cnpj": f"{cnpj_basico}{cnpj_ordem}{cnpj_dv}",
                    "nome_fantasia": nome_fantasia,
                    "municipio_codigo": municipio,
                    "uf": uf,
                    "cnae_principal": cnae_principal,
                    "cnae_descricao": cnae_descricao,
                    "data_inicio_atividade": _data_iso(data_inicio_atividade),
                    "tipo_empresa": "MATRIZ" if matriz_filial == "1" else "FILIAL",
                    "situacao_cadastral": "ATIVA",
                }
                linhas.append(registro)

    print(f"{total_lidos} estabelecimentos lidos, {total_filtrados} ativos em UF prioritaria.")
    return linhas


def juntar_empresas(
    registros: list[dict],
    empresas: Dict[str, Dict[str, Optional[str]]],
) -> list[dict]:
    for r in registros:
        empresa = empresas.get(r["cnpj_basico"], {})
        r["razao_social"] = empresa.get("razao_social")
        r["capital_social"] = empresa.get("capital_social")
        r["porte"] = empresa.get("porte")
    return registros


def analisar(registros: list[dict]) -> list[dict]:
    saida = []
    for r in registros:
        resultado = calcular_score(r)
        detalhes = resultado["detalhes"]
        saida.append({
            "cnpj": r["cnpj"],
            "razao_social": r["razao_social"],
            "nome_fantasia": r["nome_fantasia"],
            "municipio_codigo": r["municipio_codigo"],
            "uf": r["uf"],
            "cnae_principal": r["cnae_principal"],
            "cnae_descricao": r["cnae_descricao"],
            "capital_social": r["capital_social"],
            "porte": r["porte"],
            "data_inicio_atividade": r["data_inicio_atividade"],
            "tipo_empresa": r["tipo_empresa"],
            "score": resultado["score"],
            "classificacao": resultado["classificacao"],
            "score_segmento": detalhes.get("segmento"),
            "score_porte_financeiro": detalhes.get("porte_financeiro"),
            "score_tempo_empresa": detalhes.get("tempo_empresa"),
            "score_localizacao": detalhes.get("localizacao"),
            "score_estrutura_societaria": detalhes.get("estrutura_societaria"),
        })
    return saida


def imprimir_resumo(linhas: list[dict]) -> None:
    contagem: Dict[str, int] = {}
    com_cnae = 0
    for linha in linhas:
        contagem[linha["classificacao"]] = contagem.get(linha["classificacao"], 0) + 1
        if linha["cnae_descricao"]:
            com_cnae += 1
    total = len(linhas)
    pct_cnae = (com_cnae / total * 100) if total else 0
    print(f"\nTotal processado: {total}")
    print(f"Com CNAE valido (resolvido): {com_cnae} ({pct_cnae:.1f}%)")
    print("\nDistribuicao:")
    for classificacao, qtd in sorted(contagem.items()):
        print(f"  {classificacao}: {qtd}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Importa e pontua CNPJs dos dados abertos da RFB.")
    parser.add_argument("--dir", type=str, default="data/rfb", help="Pasta com os CSVs extraidos (Empresas/Estabelecimentos/Cnaes).")
    parser.add_argument("--out", type=str, default=None, help="Nome do CSV de saida (dentro de data/output/).")
    args = parser.parse_args()

    base_dir = PROJECT_DIR / args.dir
    print(f"Carregando CNAEs de referencia de {base_dir}...")
    cnaes = carregar_cnaes(base_dir)
    print(f"{len(cnaes)} CNAEs carregados.")

    print("Filtrando Estabelecimentos (ativa + UF prioritaria) em todas as particoes...")
    registros = filtrar_estabelecimentos(base_dir, cnaes)

    necessarios = {r["cnpj_basico"] for r in registros}
    print(f"\nBuscando dados de Empresas para {len(necessarios)} CNPJ_BASICO unicos, em todas as particoes...")
    empresas = carregar_empresas_necessarias(base_dir, necessarios)
    print(f"{len(empresas)} empresas encontradas.")

    registros = juntar_empresas(registros, empresas)

    print("Rodando SolarScore...")
    linhas = analisar(registros)

    data_output = PROJECT_DIR / "data" / "output"
    data_output.mkdir(parents=True, exist_ok=True)
    nome_saida = args.out or "scoring_prospeccao_rfb_todas_particoes.csv"
    caminho_saida = data_output / nome_saida

    with open(caminho_saida, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(linhas)

    print(f"\nResultado salvo em: {caminho_saida}")
    imprimir_resumo(linhas)


if __name__ == "__main__":
    main()
