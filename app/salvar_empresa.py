import requests
from supabase_client import supabase

cnpj = "07799594000191"

url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}"

response = requests.get(url, timeout=30)

print("Status BrasilAPI:", response.status_code)
print("Resposta:", response.text[:500])

if response.status_code == 429:
    print("Limite da BrasilAPI atingido. Aguarde alguns minutos e tente novamente.")
    exit()

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

resultado = supabase.table("empresas").upsert(
    dados,
    on_conflict="cnpj"
).execute()

print("Empresa salva com sucesso!")
print(resultado.data)