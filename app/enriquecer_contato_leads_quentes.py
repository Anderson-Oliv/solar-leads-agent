"""
Piloto de enriquecimento de contato para os leads quentes (Sprint 02, secao 5 -
"SDR IA - Prototipo"): tenta achar email/telefone de uma amostra estratificada
(UF x segmento) dos leads classificados como Lead Quente, pra medir taxa de
assertividade antes de rodar em escala nos 17.761.

Funil de 2 niveis por empresa:
  1. BrasilAPI (wrapper gratuito dos dados publicos de CNPJ da Receita) - pode
     trazer email/telefone se a empresa preencheu isso no cadastro.
  2. Fallback via busca na web (Firecrawl CLI) quando a BrasilAPI nao tem
     contato - procura o site oficial/LinkedIn da empresa como canal
     alternativo de contato.

Resultado vai pra tabela `enriquecimento_contato_piloto` no Supabase, com uma
linha por empresa amostrada e o que foi encontrado em cada nivel.

Uso:
    python3 app/enriquecer_contato_leads_quentes.py --por-celula 6
"""

import argparse
import json
import random
import re
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent
sys.path.insert(0, str(APP_DIR))

import requests  # noqa: E402
from supabase_client import supabase  # noqa: E402

SEED = 42
TABELA_ORIGEM = "leads_qualificados"
TABELA_DESTINO = "enriquecimento_contato_piloto"
BRASILAPI_URL = "https://brasilapi.com.br/api/cnpj/v1/{cnpj}"
BRASILAPI_PAUSA_S = 1.3
BRASILAPI_MAX_TENTATIVAS = 3

BUCKETS = [
    ("Combustível", ["combustív", "combustivel"]),
    ("Supermercado/Hipermercado", ["supermercado", "hipermercado"]),
    ("Padaria/Panificação", ["padaria", "panifica"]),
    ("Hotel/Motel", ["hotéis", "hotel", "motéis", "motel"]),
    ("Farmácia", ["farmac"]),
    ("Restaurante", ["restaurante"]),
    ("Saúde/Hospitalar", ["hospit", "pronto-socorro", "médico-hospitalar"]),
    ("Aluguel de Imóveis", ["aluguel de imóv"]),
]


def bucket_de(segmento: str) -> str:
    texto = (segmento or "").lower()
    for nome, chaves in BUCKETS:
        if any(chave in texto for chave in chaves):
            return nome
    return "Outros"


def buscar_leads_quentes() -> list[dict]:
    """Pagina sobre a tabela leads_qualificados (PostgREST limita a 1000/request)."""
    registros = []
    passo = 1000
    inicio = 0
    while True:
        resp = (
            supabase.table(TABELA_ORIGEM)
            .select("cnpj,razao_social,uf,segmento")
            .eq("classificacao", "🟢 Lead Quente")
            .order("cnpj")
            .range(inicio, inicio + passo - 1)
            .execute()
        )
        lote = resp.data
        if not lote:
            break
        registros.extend(lote)
        if len(lote) < passo:
            break
        inicio += passo
    return registros


def amostra_estratificada(leads: list[dict], por_celula: int) -> list[dict]:
    celulas: dict = defaultdict(list)
    for lead in leads:
        lead["segmento_bucket"] = bucket_de(lead.get("segmento"))
        celulas[(lead["uf"], lead["segmento_bucket"])].append(lead)

    rng = random.Random(SEED)
    amostra = []
    for chave, grupo in celulas.items():
        rng.shuffle(grupo)
        amostra.extend(grupo[:por_celula])
    return amostra


def consultar_brasilapi(cnpj: str) -> dict:
    """Retorna {'email': ..., 'telefone': ...} (None se ausente/erro)."""
    for tentativa in range(1, BRASILAPI_MAX_TENTATIVAS + 1):
        try:
            resp = requests.get(BRASILAPI_URL.format(cnpj=cnpj), timeout=15)
        except requests.RequestException:
            return {"email": None, "telefone": None, "status": "erro_rede"}

        if resp.status_code == 429:
            time.sleep(5 * tentativa)
            continue
        if resp.status_code != 200:
            return {"email": None, "telefone": None, "status": f"http_{resp.status_code}"}

        dados = resp.json()
        email = dados.get("email") or None
        ddd = dados.get("ddd_telefone_1") or ""
        telefone = ddd.strip() or None
        return {"email": email, "telefone": telefone, "status": "ok"}

    return {"email": None, "telefone": None, "status": "rate_limited"}


EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
TELEFONE_RE = re.compile(r"\(?\d{2}\)?\s?9?\d{4}[-\s]?\d{4}")


def buscar_site_via_web(razao_social: str, uf: str) -> dict:
    """Fallback: usa o Firecrawl CLI pra achar site/LinkedIn e tenta extrair
    contato do snippet retornado. Nao faz scrape completo de cada resultado
    (custaria muito mais credito/tempo pro tamanho desse piloto)."""
    query = f'"{razao_social}" {uf} contato telefone email site oficial'
    try:
        resultado = subprocess.run(
            ["firecrawl", "search", query, "--scrape", "--limit", "3", "--json"],
            capture_output=True, text=True, timeout=60,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return {"site": None, "email": None, "telefone": None, "status": f"erro_busca:{e}"}

    if resultado.returncode != 0:
        return {"site": None, "email": None, "telefone": None, "status": "erro_busca"}

    try:
        dados = json.loads(resultado.stdout)
    except json.JSONDecodeError:
        return {"site": None, "email": None, "telefone": None, "status": "resposta_invalida"}

    itens = (dados.get("data") or {}).get("web") or []
    if not itens:
        return {"site": None, "email": None, "telefone": None, "status": "sem_resultado"}

    site = itens[0].get("url")
    texto_completo = " ".join(
        (item.get("markdown") or "") + " " + (item.get("description") or "")
        for item in itens
    )
    email = EMAIL_RE.search(texto_completo)
    telefone = TELEFONE_RE.search(texto_completo)
    return {
        "site": site,
        "email": email.group(0) if email else None,
        "telefone": telefone.group(0) if telefone else None,
        "status": "ok",
    }


def buscar_ja_processados() -> dict:
    resultados = {}
    passo = 1000
    inicio = 0
    while True:
        resp = supabase.table(TABELA_DESTINO).select("*").range(inicio, inicio + passo - 1).execute()
        lote = resp.data
        if not lote:
            break
        for r in lote:
            resultados[r["cnpj"]] = r
        if len(lote) < passo:
            break
        inicio += passo
    return resultados


def enriquecer(amostra: list[dict]) -> list[dict]:
    ja_processados = buscar_ja_processados()
    if ja_processados:
        print(f"{len(ja_processados)} empresas ja processadas antes - vao ser reaproveitadas.", flush=True)

    resultados = []
    total = len(amostra)
    for i, lead in enumerate(amostra, start=1):
        cnpj = lead["cnpj"]

        if cnpj in ja_processados:
            resultados.append(ja_processados[cnpj])
            print(f"[{i}/{total}] {cnpj} - ja processado, reaproveitando.", flush=True)
            continue

        print(f"[{i}/{total}] {cnpj} - {lead['razao_social'][:40]}...", flush=True)

        brasilapi = consultar_brasilapi(cnpj)
        email = brasilapi["email"]
        telefone = brasilapi["telefone"]
        fonte = "brasilapi" if (email or telefone) else None
        site = None

        if not email and not telefone:
            web = buscar_site_via_web(lead["razao_social"], lead["uf"])
            site = web["site"]
            email = email or web["email"]
            telefone = telefone or web["telefone"]
            if email or telefone or site:
                fonte = "web"

        registro = {
            "cnpj": cnpj,
            "razao_social": lead["razao_social"],
            "uf": lead["uf"],
            "segmento_bucket": lead["segmento_bucket"],
            "email": email,
            "telefone": telefone,
            "site": site,
            "fonte": fonte,
            "tem_contato": bool(email or telefone or site),
        }
        resultados.append(registro)
        print(f"    -> fonte={fonte} contato={registro['tem_contato']}", flush=True)

        # salva incremental - se o processo cair no meio, o que ja rodou fica gravado
        for tentativa in range(3):
            try:
                supabase.table(TABELA_DESTINO).upsert(registro, on_conflict="cnpj").execute()
                break
            except Exception as e:
                if tentativa == 2:
                    raise
                print(f"    aviso: falha ao salvar ({e!r}), tentando de novo...", flush=True)
                time.sleep(3 * (tentativa + 1))

        time.sleep(BRASILAPI_PAUSA_S)

    return resultados


def imprimir_resumo(resultados: list[dict]) -> None:
    total = len(resultados)
    com_contato = sum(1 for r in resultados if r["tem_contato"])
    com_email = sum(1 for r in resultados if r["email"])
    com_telefone = sum(1 for r in resultados if r["telefone"])
    print(f"\nTotal amostrado: {total}")
    print(f"Com algum contato: {com_contato} ({com_contato / total * 100:.1f}%)")
    print(f"Com email: {com_email} ({com_email / total * 100:.1f}%)")
    print(f"Com telefone: {com_telefone} ({com_telefone / total * 100:.1f}%)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Piloto de enriquecimento de contato dos leads quentes.")
    parser.add_argument("--por-celula", type=int, default=6, help="Quantas empresas amostrar por celula (UF x segmento).")
    args = parser.parse_args()

    print("Buscando leads quentes no Supabase...")
    leads = buscar_leads_quentes()
    print(f"{len(leads)} leads quentes encontrados.")

    amostra = amostra_estratificada(leads, args.por_celula)
    print(f"Amostra estratificada: {len(amostra)} empresas ({args.por_celula} por celula UF x segmento).")

    resultados = enriquecer(amostra)
    imprimir_resumo(resultados)


if __name__ == "__main__":
    main()
