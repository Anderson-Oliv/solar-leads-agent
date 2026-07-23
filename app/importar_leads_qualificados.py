"""
Sobe o resultado do SolarScore (CSV gerado por importar_rfb_prospeccao.py) para a
tabela `leads_qualificados` no Supabase - Sprint 02 tarefa 4:
"Criar tabela leads_qualificados no Supabase".

So sobem linhas com score >= 40 (Nutricao, Bom ou Quente) - `Baixa prioridade`
(score < 40) fica de fora, porque a tabela e de leads *qualificados*.

Upsert por `cnpj`: rodar de novo com um CSV mais recente atualiza os leads ja
existentes sem duplicar (mesma logica que a tarefa 5, "atualizacao periodica de
scores", vai reusar).

Uso:
    python3 app/importar_leads_qualificados.py --csv data/output/scoring_prospeccao_rfb_todas_particoes.csv
"""

import argparse
import csv
import os
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent
sys.path.insert(0, str(APP_DIR))

from supabase_client import supabase  # noqa: E402

SCORE_MINIMO_QUALIFICADO = 40
TABELA = "leads_qualificados"

COLUNAS = [
    "cnpj", "razao_social", "nome_fantasia", "municipio_codigo", "uf",
    "cnae_principal", "segmento", "capital_social", "porte",
    "data_inicio_atividade", "tipo_empresa", "score", "classificacao",
    "score_segmento", "score_porte_financeiro", "score_tempo_empresa",
    "score_localizacao", "score_estrutura_societaria",
]


def _num(valor):
    if valor in (None, ""):
        return None
    try:
        return float(valor)
    except ValueError:
        return None


def _texto(valor):
    return valor if valor not in (None, "") else None


def linha_para_registro(linha: dict) -> dict:
    return {
        "cnpj": linha["cnpj"],
        "razao_social": linha["razao_social"],
        "nome_fantasia": _texto(linha.get("nome_fantasia")),
        "municipio_codigo": _texto(linha.get("municipio_codigo")),
        "uf": _texto(linha.get("uf")),
        "cnae_principal": _texto(linha.get("cnae_principal")),
        "segmento": _texto(linha.get("cnae_descricao")),
        "capital_social": _num(linha.get("capital_social")),
        "porte": _texto(linha.get("porte")),
        "data_inicio_atividade": _texto(linha.get("data_inicio_atividade")),
        "tipo_empresa": _texto(linha.get("tipo_empresa")),
        "score": _num(linha["score"]),
        "classificacao": linha["classificacao"],
        "score_segmento": _num(linha.get("score_segmento")),
        "score_porte_financeiro": _num(linha.get("score_porte_financeiro")),
        "score_tempo_empresa": _num(linha.get("score_tempo_empresa")),
        "score_localizacao": _num(linha.get("score_localizacao")),
        "score_estrutura_societaria": _num(linha.get("score_estrutura_societaria")),
    }


def carregar_qualificados(caminho_csv: Path) -> list[dict]:
    registros = []
    total_lido = 0
    with open(caminho_csv, encoding="utf-8", newline="") as f:
        for linha in csv.DictReader(f):
            total_lido += 1
            score = _num(linha.get("score"))
            if score is None or score < SCORE_MINIMO_QUALIFICADO:
                continue
            registros.append(linha_para_registro(linha))
    print(f"{total_lido} linhas lidas do CSV, {len(registros)} qualificadas (score >= {SCORE_MINIMO_QUALIFICADO}).")
    return registros


def enviar_em_lotes(registros: list[dict], tamanho_lote: int) -> None:
    total = len(registros)
    enviados = 0
    for inicio in range(0, total, tamanho_lote):
        lote = registros[inicio:inicio + tamanho_lote]
        supabase.table(TABELA).upsert(lote, on_conflict="cnpj").execute()
        enviados += len(lote)
        print(f"  {enviados}/{total} enviados...")
    print(f"Concluido: {enviados} registros upsertados em '{TABELA}'.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sobe leads qualificados (score >= 40) para o Supabase.")
    parser.add_argument(
        "--csv", type=str,
        default="data/output/scoring_prospeccao_rfb_todas_particoes.csv",
        help="CSV de entrada, gerado por importar_rfb_prospeccao.py",
    )
    parser.add_argument(
        "--batch-size", type=int, default=int(os.getenv("BATCH_SIZE", "500")),
        help="Tamanho do lote de upsert (default: env BATCH_SIZE ou 500).",
    )
    args = parser.parse_args()

    caminho_csv = PROJECT_DIR / args.csv
    print(f"Lendo {caminho_csv}...")
    registros = carregar_qualificados(caminho_csv)

    if not registros:
        print("Nenhum registro qualificado para enviar.")
        return

    print(f"Enviando em lotes de {args.batch_size}...")
    enviar_em_lotes(registros, args.batch_size)


if __name__ == "__main__":
    main()
