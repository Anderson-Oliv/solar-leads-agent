# API de Feed de Leads

Expõe os leads qualificados do Supabase pra qualquer CRM consumir via HTTP.
Parte da Etapa 4️⃣ (Integração com CRM) da Sprint 02.

## Subir localmente

```bash
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

Docs interativas (Swagger, testa direto no navegador): http://localhost:8000/docs

## Endpoints

### `GET /api/leads/feed`

Retorna leads qualificados em JSON, mais quentes primeiro.

| Parâmetro | Tipo | Padrão | Descrição |
|---|---|---|---|
| `date` | `YYYY-MM-DD` | — | só leads criados a partir dessa data |
| `score_min` | int 0–100 | 60 | score mínimo (60 = Lead Bom+, 80 = Lead Quente) |
| `uf` | string | — | filtra por UF, ex: `SP` |
| `only_com_contato` | bool | `false` | só leads que já têm telefone/email/site enriquecido |
| `limit` | int 1–1000 | 500 | máximo de leads retornados (teto de 1000 — ver "Limitações" abaixo) |

Exemplo:

```bash
curl "http://localhost:8000/api/leads/feed?score_min=80&uf=SP&only_com_contato=true"
```

### `GET /api/leads/feed.csv`

Mesmos parâmetros, retorna CSV pra download/importação manual no CRM quando não
há integração via API.

## Limitações conhecidas

- **Teto de 1000 leads por chamada.** Esse projeto Supabase tem
  `db-max-rows=1000` no PostgREST — pedir mais que isso é ignorado
  silenciosamente pelo banco. O parâmetro `limit` já reflete esse teto real
  (não promete o que o banco não entrega). Se precisar de mais de 1000 leads
  de uma vez, pagine por `date`/`uf`/`score_min` em várias chamadas.
- **Latência do primeiro request: ~0.7–1s.** `leads_qualificados` (419k
  linhas) não tem índice em `score`, então a ordenação por score é lenta a
  frio. Requests repetidos com os mesmos filtros usam um cache em memória de 5
  minutos e respondem em <10ms — na prática cobre bem um CRM que consulta o
  feed periodicamente. Pra melhorar a latência a frio também, seria preciso
  criar um índice em `leads_qualificados.score` direto no SQL editor do
  Supabase (fora do escopo desta API).
- **Contato nem sempre disponível.** Só ~38,6% dos leads quentes têm
  telefone/email/site (ver decisão de 28/07 na nota do projeto sobre
  Firecrawl) — `only_com_contato=true` filtra só os que já têm.
- **Cadência dos dados:** a base é atualizada em lotes mensais (não em tempo
  real), então `date` reflete quando o lote rodou, não o cadastro individual
  da empresa na Receita.

## Pendente

- Testar integração de verdade com um CRM (Kommo, Salesforce ou similar) —
  ainda não feito, precisa de uma conta de teste.
- Documentação em linguagem de negócio pro time comercial — faz mais sentido
  escrever depois que o primeiro CRM real estiver conectado, pra descrever o
  fluxo de ponta a ponta em vez de só o contrato da API.
