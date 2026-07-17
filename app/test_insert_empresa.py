from supabase_client import supabase

empresa = {
    "cnpj": "98765432000199",
    "razao_social": "Empresa Python Solar LTDA",
    "nome_fantasia": "Python Solar",
    "cnae_principal": "Indústria",
    "porte": "Médio",
    "situacao_cadastral": "Ativa",
    "uf": "SP",
    "cidade": "São Paulo",
    "capital_social": 500000,
    "telefone": "11988887777",
    "email": "contato@pythonsolar.com"
}

response = supabase.table("empresas").insert(empresa).execute()

print(response)