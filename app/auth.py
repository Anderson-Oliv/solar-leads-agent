import os
import requests
from dotenv import load_dotenv

load_dotenv()

GOV_CLIENT_ID = os.getenv("GOV_CLIENT_ID")
GOV_CLIENT_SECRET = os.getenv("GOV_CLIENT_SECRET")
GOV_TOKEN_URL = os.getenv("GOV_TOKEN_URL")
GOV_SCOPE = os.getenv("GOV_SCOPE")


def gerar_token():
    payload = {
        "grant_type": "client_credentials",
        "scope": GOV_SCOPE
    }

    response = requests.post(
        GOV_TOKEN_URL,
        data=payload,
        auth=(GOV_CLIENT_ID, GOV_CLIENT_SECRET),
        timeout=30
    )

    print("Status:", response.status_code)

    if response.status_code != 200:
        print("Erro:", response.text)
        return None

    data = response.json()
    token = data.get("access_token")

    if not token:
        print("Erro: resposta 200 sem access_token:", data)
        return None

    print("Token gerado com sucesso!")

    return token


if __name__ == "__main__":
    gerar_token()