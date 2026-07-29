"""
API de feed de leads (Sprint 02, Etapa 4 - Integracao com CRM). Expoe os leads
qualificados do Supabase pra um sistema de CRM consumir via HTTP, com contato
(telefone/email/site) anexado quando ja foi enriquecido pela Etapa 5 (SDR IA).

So retorna leads que ja passaram pelo enriquecimento de contato (join com
`enriquecimento_contato_piloto`) fica opcional via `only_com_contato` - por
padrao traz todos os qualificados, com os campos de contato vazios quando nao
enriquecidos ainda (o time comercial decide se trabalha um lead sem contato
direto, ex: buscando manualmente).

Por padrao tambem exclui leads que ja tem energia solar instalada, segundo o
cruzamento com o dataset da ANEEL (28/07/2026, ver `ja_tem_solar_aneel` em
`leads_qualificados`) - nao faz sentido prospectar quem ja converteu. Da pra
incluir de volta via `excluir_com_solar=false`, ex: pra auditoria.

Uso:
    uvicorn app.main:app --reload --port 8000

Docs interativas (Swagger): http://localhost:8000/docs
"""

import csv
import io
import sys
import time
from datetime import date as Date
from pathlib import Path
from typing import Optional

APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR))

from fastapi import FastAPI, Query  # noqa: E402
from fastapi.responses import StreamingResponse  # noqa: E402
from pydantic import BaseModel  # noqa: E402
from supabase_client import supabase  # noqa: E402

app = FastAPI(
    title="Sistema de Leads — API de Feed",
    description="Feed de leads qualificados para integração com CRM.",
    version="1.0.0",
)

TABELA_LEADS = "leads_qualificados"
TABELA_CONTATO = "enriquecimento_contato_piloto"
# Esse projeto Supabase tem db-max-rows=1000 no PostgREST - pedir mais que isso
# via .limit() e ignorado silenciosamente (mesmo comportamento ja documentado
# em app/dashboard.py). Nao ha como paginar aqui sem violar o SLA de latencia,
# entao o teto da API e travado no mesmo limite do banco em vez de prometer
# mais do que o Supabase de fato entrega.
LIMITE_MAXIMO = 1000

# `leads_qualificados` tem 419k linhas sem indice em `score`, e o Supabase (REST
# remoto) tem uns ~250-300ms de latencia de rede por chamada mesmo pra queries
# triviais - a busca de leads + a busca de contato (2 chamadas sequenciais,
# a segunda depende do resultado da primeira) fica em ~0.7-1s por request "frio".
# Como a base so muda numa cadencia mensal (ver decisao de 28/07 na nota do
# projeto), cachear por CACHE_TTL_SEGUNDOS e seguro e resolve o SLA de <500ms
# pros requests repetidos - o request frio ainda depende de indice em `score`
# pra melhorar (fora do alcance da API, precisa rodar no SQL editor do Supabase).
CACHE_TTL_SEGUNDOS = 300
_cache: dict[tuple, tuple[float, list[dict]]] = {}


def _buscar_leads_cacheado(
    date: Optional[Date], score_min: int, uf: Optional[str], only_com_contato: bool,
    excluir_com_solar: bool, limit: int,
) -> list[dict]:
    chave = (date, score_min, uf, only_com_contato, excluir_com_solar, limit)
    agora = time.monotonic()
    if chave in _cache:
        timestamp, leads = _cache[chave]
        if agora - timestamp < CACHE_TTL_SEGUNDOS:
            return leads
    leads = _buscar_leads(date, score_min, uf, only_com_contato, excluir_com_solar, limit)
    _cache[chave] = (agora, leads)
    return leads


class Lead(BaseModel):
    cnpj: str
    razao_social: str
    nome_fantasia: Optional[str] = None
    uf: Optional[str] = None
    segmento: Optional[str] = None
    porte: Optional[str] = None
    score: float
    classificacao: str
    data_criacao: str
    telefone: Optional[str] = None
    email: Optional[str] = None
    site: Optional[str] = None
    tem_contato: bool = False
    ja_tem_solar_aneel: bool = False


class FeedResponse(BaseModel):
    total: int
    filtros: dict
    leads: list[Lead]


def _buscar_leads(
    date: Optional[Date], score_min: int, uf: Optional[str], only_com_contato: bool,
    excluir_com_solar: bool, limit: int,
) -> list[dict]:
    query = (
        supabase.table(TABELA_LEADS)
        .select("cnpj,razao_social,nome_fantasia,uf,segmento,porte,score,classificacao,data_criacao,ja_tem_solar_aneel")
        .gte("score", score_min)
    )
    if date:
        query = query.gte("data_criacao", date.isoformat())
    if uf:
        query = query.eq("uf", uf.upper())
    if excluir_com_solar:
        query = query.eq("ja_tem_solar_aneel", False)
    query = query.order("score", desc=True).limit(limit)
    leads = query.execute().data

    if not leads:
        return []

    cnpjs = [lead["cnpj"] for lead in leads]
    resp_contatos = (
        supabase.table(TABELA_CONTATO)
        .select("cnpj,telefone,email,site,tem_contato")
        .in_("cnpj", cnpjs)
        .execute()
    )
    contatos_por_cnpj = {c["cnpj"]: c for c in resp_contatos.data}

    for lead in leads:
        contato = contatos_por_cnpj.get(lead["cnpj"], {})
        lead["telefone"] = contato.get("telefone")
        lead["email"] = contato.get("email")
        lead["site"] = contato.get("site")
        lead["tem_contato"] = bool(contato.get("tem_contato", False))

    if only_com_contato:
        leads = [lead for lead in leads if lead["tem_contato"]]

    return leads


@app.get("/")
def raiz():
    return {"status": "ok", "docs": "/docs", "feed": "/api/leads/feed"}


@app.get("/api/leads/feed", response_model=FeedResponse)
def feed_leads(
    date: Optional[Date] = Query(
        None, description="Retorna só leads criados/atualizados a partir dessa data (YYYY-MM-DD). Omitido = todos."
    ),
    score_min: int = Query(60, ge=0, le=100, description="Score mínimo (padrão 60 = Lead Bom+)."),
    uf: Optional[str] = Query(None, description="Filtra por UF, ex: SP."),
    only_com_contato: bool = Query(
        False, description="Se true, retorna só leads que já têm telefone/email/site encontrado."
    ),
    excluir_com_solar: bool = Query(
        True, description="Se true (padrão), exclui leads que já têm solar instalado segundo a ANEEL."
    ),
    limit: int = Query(500, ge=1, le=LIMITE_MAXIMO, description=f"Máximo de leads retornados (teto {LIMITE_MAXIMO})."),
):
    """Feed de leads qualificados, mais recentes/quentes primeiro, com contato quando disponível."""
    leads = _buscar_leads_cacheado(date, score_min, uf, only_com_contato, excluir_com_solar, limit)
    return FeedResponse(
        total=len(leads),
        filtros={
            "date": date.isoformat() if date else None, "score_min": score_min, "uf": uf,
            "only_com_contato": only_com_contato, "excluir_com_solar": excluir_com_solar,
        },
        leads=leads,
    )


@app.get("/api/leads/feed.csv")
def feed_leads_csv(
    date: Optional[Date] = Query(None),
    score_min: int = Query(60, ge=0, le=100),
    uf: Optional[str] = Query(None),
    only_com_contato: bool = Query(False),
    excluir_com_solar: bool = Query(True),
    limit: int = Query(500, ge=1, le=LIMITE_MAXIMO),
):
    """Mesmo feed, em CSV — pra importação manual no CRM quando não há integração via API."""
    leads = _buscar_leads_cacheado(date, score_min, uf, only_com_contato, excluir_com_solar, limit)

    buffer = io.StringIO()
    campos = [
        "cnpj", "razao_social", "nome_fantasia", "uf", "segmento", "porte",
        "score", "classificacao", "data_criacao", "telefone", "email", "site", "tem_contato",
        "ja_tem_solar_aneel",
    ]
    writer = csv.DictWriter(buffer, fieldnames=campos)
    writer.writeheader()
    writer.writerows(leads)
    buffer.seek(0)

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads_feed.csv"},
    )
