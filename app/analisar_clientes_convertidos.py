"""
Backtest do SolarScore (Fase 1) contra os 51 clientes reais ja convertidos.

Le as planilhas de data/input/ reaproveitando o parsing ja usado pra importar
pro Supabase (import_clientes_varejistas_supabase.py), roda calcular_score()
de cada cliente e salva o resultado em data/output/.

Uso:
    python3 app/analisar_clientes_convertidos.py --sample 10
    python3 app/analisar_clientes_convertidos.py
"""

import argparse
import csv
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent
sys.path.insert(0, str(PROJECT_DIR))

from import_clientes_varejistas_supabase import FILES, iter_excel_records  # noqa: E402
from scoring import calcular_score  # noqa: E402

DATA_INPUT = PROJECT_DIR / "data" / "input"
DATA_OUTPUT = PROJECT_DIR / "data" / "output"

FIELDNAMES = [
    "cnpj", "razao_social", "cidade", "estado", "fonte_arquivo",
    "capital_social_ausente", "score", "classificacao",
    "score_segmento", "score_porte_financeiro", "score_tempo_empresa",
    "score_localizacao", "score_estrutura_societaria",
]


def analisar_cliente(record: dict) -> dict:
    resultado = calcular_score(record)
    detalhes = resultado["detalhes"]
    return {
        "cnpj": record.get("cnpj"),
        "razao_social": record.get("razao_social"),
        "cidade": record.get("cidade"),
        "estado": record.get("estado"),
        "fonte_arquivo": record.get("fonte_arquivo"),
        "capital_social_ausente": record.get("capital_social") in (None, ""),
        "score": resultado["score"],
        "classificacao": resultado["classificacao"],
        "score_segmento": detalhes.get("segmento"),
        "score_porte_financeiro": detalhes.get("porte_financeiro"),
        "score_tempo_empresa": detalhes.get("tempo_empresa"),
        "score_localizacao": detalhes.get("localizacao"),
        "score_estrutura_societaria": detalhes.get("estrutura_societaria"),
    }


def carregar_registros() -> list[dict]:
    registros = []
    for filename in FILES:
        file_path = DATA_INPUT / filename
        if not file_path.exists():
            print(f"Arquivo nao encontrado, pulando: {file_path}")
            continue
        registros.extend(iter_excel_records(file_path))
    return registros


def selecionar_semente(registros: list[dict], tamanho: int) -> list[dict]:
    """Amostra estratificada: mantem a proporcao entre os arquivos de origem."""
    por_arquivo: dict[str, list] = {}
    for r in registros:
        por_arquivo.setdefault(r["fonte_arquivo"], []).append(r)

    total = len(registros)
    arquivos = list(por_arquivo.items())
    semente = []
    restante = tamanho
    for i, (_fonte, itens) in enumerate(arquivos):
        if i == len(arquivos) - 1:
            n = restante
        else:
            n = round(tamanho * len(itens) / total)
            restante -= n
        semente.extend(itens[:n])
    return semente


def imprimir_resumo(linhas: list[dict]) -> None:
    contagem: dict[str, int] = {}
    for linha in linhas:
        contagem[linha["classificacao"]] = contagem.get(linha["classificacao"], 0) + 1
    print("\nDistribuicao:")
    for classificacao, qtd in sorted(contagem.items()):
        print(f"  {classificacao}: {qtd}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Roda o SolarScore contra os clientes ja convertidos.")
    parser.add_argument("--sample", type=int, default=None, help="Roda so uma amostra estratificada de N clientes.")
    parser.add_argument("--out", type=str, default=None, help="Nome do arquivo CSV de saida (dentro de data/output/).")
    args = parser.parse_args()

    registros = carregar_registros()
    print(f"{len(registros)} clientes lidos das planilhas.")

    if args.sample:
        registros = selecionar_semente(registros, args.sample)
        print(f"Amostra estratificada: {len(registros)} clientes.")

    linhas = [analisar_cliente(r) for r in registros]

    DATA_OUTPUT.mkdir(parents=True, exist_ok=True)
    sufixo = f"sample{args.sample}" if args.sample else "completo"
    nome_saida = args.out or f"scoring_clientes_convertidos_{sufixo}.csv"
    caminho_saida = DATA_OUTPUT / nome_saida

    with open(caminho_saida, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(linhas)

    print(f"Resultado salvo em: {caminho_saida}")
    imprimir_resumo(linhas)


if __name__ == "__main__":
    main()
