import pandas as pd
import requests
import time
from supabase_client import supabase

ARQUIVO = "data/input/cnpjs.csv"

df = pd.read_csv(ARQUIVO)

df.columns = df.columns.str.lower().str.strip()

print(df.columns.tolist())

for _, row in df.iterrows():

    status = str(row["status cnpj"]).strip().lower()

    if status == "baixada":

        print(f"Pulando empresa baixada: {row['nome']}")

        continue

    cnpj = str(row["cnpj"]) \
        .replace(".", "") \
        .replace("/", "") \
        .replace("-", "") \
        .strip()

    print(f"Consultando CNPJ: {cnpj}")

    url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}"

    response = requests.get(url, timeout=30)

    if response.status_code == 429:
        print("Limite atingido. Aguardando 60 segundos...")
        time.sleep(60)
        response = requests.get(url, timeout=30)

    if response.status_code != 200:
        print(f"Erro no CNPJ {cnpj}: {response.status_code}")
        continue

    empresa = response.json()

    dados = {
        "cnpj": cnpj,
        "razao_social": empresa.get("razao_social"),
        "nome_fantasia": empresa.get("nome_fantasia"),
        "cnae_principal": empresa.get("cnae_fiscal_descricao"),
        "situacao_cadastral": empresa.get("descricao_situacao_cadastral"),
        "uf": empresa.get("uf"),
        "cidade": empresa.get("municipio"),
        "capital_social": empresa.get("capital_social")
    }

    resultado = (
        supabase
        .table("empresas")
        .upsert(dados, on_conflict="cnpj")
        .execute()
    )

    print(f"Salvo: {dados['razao_social']}")

    time.sleep(3)

print("Importação finalizada!")