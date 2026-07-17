import requests

cnpj = "07799594000191"

url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}"

response = requests.get(url)

print("Status:", response.status_code)

if response.status_code == 200:
    empresa = response.json()

    print("Razão Social:", empresa.get("razao_social"))
    print("Nome Fantasia:", empresa.get("nome_fantasia"))
    print("UF:", empresa.get("uf"))
    print("Município:", empresa.get("municipio"))
    print("Capital Social:", empresa.get("capital_social"))
else:
    print(response.text)