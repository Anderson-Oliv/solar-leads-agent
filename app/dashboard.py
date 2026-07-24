"""
Dashboard operacional (Sprint 02, tarefa 3) - visao geral dos leads qualificados:
resumo por classificacao, top segmentos, distribuicao por UF, e tabela filtravel
(UF, segmento, score minimo).

Le das views agregadas `v_leads_by_classificacao`, `v_leads_by_uf` e
`v_leads_by_segmento` (criadas no Supabase pra nao escanear as 419k linhas de
`leads_qualificados` a cada refresh). A tabela filtravel no final consulta
`leads_qualificados` direto, limitada a 500 linhas.

Uso:
    streamlit run app/dashboard.py
"""

import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from supabase_client import supabase  # noqa: E402
from viz_theme import (  # noqa: E402
    AQUA,
    BASELINE,
    BLUE,
    CLASSIFICACAO_COR,
    CLASSIFICACAO_ORDEM,
    GRIDLINE,
    INK_MUTED,
    ORANGE,
    PLOTLY_CONFIG,
    SURFACE,
    axis_style,
    base_layout,
    fmt_int,
    truncar,
)

st.set_page_config(page_title="Sistema de Leads — Dashboard", layout="wide")

UFS_ICP = ["SP", "MG", "GO", "MT", "MS", "PR"]

# Nao vem de tabela propria - a base bruta da RFB foi processada em lote e o
# total de empresas mapeadas so ficou registrado no card de status do projeto
# (17/07/2026). Atualizar aqui se uma nova expansao de base for feita.
EMPRESAS_MAPEADAS = 652_663

# Decisao do Anderson em 24/07/2026: aceitar o baseline atual do piloto de
# enriquecimento (sem investir em credito Firecrawl agora) ate essa data.
PROXIMO_REPROCESSAMENTO_FIRECRAWL = "05/08/2026"


@st.cache_data(ttl=3600)
def carregar_por_classificacao() -> pd.DataFrame:
    resp = supabase.table("v_leads_by_classificacao").select("*").execute()
    return pd.DataFrame(resp.data)


@st.cache_data(ttl=3600)
def carregar_por_uf() -> pd.DataFrame:
    resp = supabase.table("v_leads_by_uf").select("*").execute()
    return pd.DataFrame(resp.data)


@st.cache_data(ttl=3600)
def carregar_por_segmento(top_n: int = 10) -> pd.DataFrame:
    resp = supabase.table("v_leads_by_segmento").select("*").order("total", desc=True).limit(top_n).execute()
    return pd.DataFrame(resp.data)


@st.cache_data(ttl=3600)
def carregar_timeline() -> pd.DataFrame:
    resp = supabase.table("v_leads_timeline").select("*").order("dia").execute()
    return pd.DataFrame(resp.data)


@st.cache_data(ttl=3600)
def carregar_stats_contato() -> tuple[int, int]:
    """Retorna (total processado no piloto, quantos tem contato) - so cobre a
    amostra de leads quentes enriquecida ate agora, nao a base toda."""
    resp = supabase.table("enriquecimento_contato_piloto").select("tem_contato").execute()
    df = pd.DataFrame(resp.data)
    if df.empty:
        return 0, 0
    return len(df), int(df["tem_contato"].sum())


@st.cache_data(ttl=600)
def carregar_piloto_enriquecido() -> pd.DataFrame:
    """Traz os 376 CNPJs ja processados no piloto de enriquecimento (nao a
    base toda de leads quentes), com os dados do lead + contato encontrado."""
    resp_piloto = (
        supabase.table("enriquecimento_contato_piloto")
        .select("cnpj,telefone,email,site,tem_contato")
        .execute()
    )
    df_piloto = pd.DataFrame(resp_piloto.data)
    if df_piloto.empty:
        return df_piloto

    resp_leads = (
        supabase.table("leads_qualificados")
        .select("cnpj,razao_social,uf,segmento,score,classificacao,porte")
        .in_("cnpj", df_piloto["cnpj"].tolist())
        .execute()
    )
    df_leads = pd.DataFrame(resp_leads.data)
    return df_leads.merge(df_piloto, on="cnpj", how="left")


st.title("Sistema de Leads para Empresas — Dashboard Operacional")
st.caption("Prospecção B2B para energia solar · SolarScore Fase 1 · dados de `leads_qualificados` no Supabase")

df_class = carregar_por_classificacao()
total_geral = int(df_class["total"].sum()) if not df_class.empty else 0
qualificados_60 = int(df_class.loc[df_class["classificacao"].isin(["🟢 Lead Quente", "🟡 Lead Bom"]), "total"].sum()) if not df_class.empty else 0
quentes_80 = int(df_class.loc[df_class["classificacao"] == "🟢 Lead Quente", "total"].sum()) if not df_class.empty else 0
total_piloto, com_contato = carregar_stats_contato()

# Aba de timeline ocultada por ora: toda a base ainda foi carregada numa
# unica data (`data_criacao`), entao o grafico de evolucao nao teria o que
# mostrar. Reativar (git log app/dashboard.py) quando houver mais de uma
# data de carga.
tab_geral, tab_segmentacao, tab_explorar = st.tabs(
    ["📊 Visão geral", "🗂️ Segmentação & UF", "🔍 Explorar"]
)

with tab_geral:
    st.subheader("Funil de prospecção")
    with st.container(border=True):
        valores_funil = [EMPRESAS_MAPEADAS, qualificados_60, quentes_80]
        labels_funil = ["Empresas mapeadas", "Qualificados (score ≥ 60)", "Quentes (score ≥ 80)"]
        textos_funil = [f"{fmt_int(v)}<br>{v / valores_funil[0] * 100:.1f}%" for v in valores_funil]
        fig_funil = go.Figure(
            go.Funnel(
                y=labels_funil,
                x=valores_funil,
                text=textos_funil,
                textposition="outside",
                textinfo="text",
                textfont=dict(color=INK_MUTED, size=14),
                marker=dict(color=[BLUE, ORANGE, AQUA], line=dict(color=SURFACE, width=2)),
                connector=dict(line=dict(color=BASELINE, width=1, dash="dot")),
            )
        )
        fig_funil.update_layout(**base_layout(height=340, margin=dict(l=8, r=100, t=8, b=8)))
        # 1.6x (nao 1.3x): a primeira barra (100%) chega quase na ponta do
        # eixo, entao e a que sobra menos folga pro texto "outside" - o
        # multiplicador precisa dar espaco suficiente pra ELA, nao pras
        # barras menores que já tem folga de sobra.
        fig_funil.update_xaxes(range=[0, EMPRESAS_MAPEADAS * 1.6], visible=False)
        fig_funil.update_yaxes(**axis_style(tickfont=dict(color=INK_MUTED, size=13)))
        st.plotly_chart(fig_funil, use_container_width=True, config=PLOTLY_CONFIG)

    col1, col2, col3, col4 = st.columns(4)
    with col1, st.container(border=True):
        st.metric("Total qualificados", fmt_int(total_geral))
    for col, classe in zip([col2, col3, col4], CLASSIFICACAO_ORDEM):
        valor = int(df_class.loc[df_class["classificacao"] == classe, "total"].sum()) if not df_class.empty else 0
        with col, st.container(border=True):
            st.metric(classe, fmt_int(valor))

    st.subheader("Piloto de enriquecimento de contato")
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1, st.container(border=True):
        st.metric(
            "Leads quentes com contato (piloto)", fmt_int(com_contato),
            help=f"{fmt_int(total_piloto)} leads quentes já processados no piloto de enriquecimento, de {fmt_int(quentes_80)} no total de leads quentes.",
        )
    with col_c2, st.container(border=True):
        st.metric("Amostra do piloto processada", f"{fmt_int(total_piloto)} / {fmt_int(quentes_80)}")
    with col_c3, st.container(border=True):
        st.metric(
            "Próximo reprocessamento Firecrawl", PROXIMO_REPROCESSAMENTO_FIRECRAWL,
            help="Decisão de 24/07/2026: manter o baseline atual do piloto até essa data, sem investir em crédito Firecrawl antes disso.",
        )

with tab_segmentacao:
    col_esq, col_dir = st.columns([1, 1])

    with col_esq:
        st.subheader("Distribuição por score")
        with st.container(border=True):
            if not df_class.empty:
                df_class["classificacao"] = pd.Categorical(df_class["classificacao"], categories=CLASSIFICACAO_ORDEM, ordered=True)
                df_class = df_class.sort_values("classificacao")
                cores = [CLASSIFICACAO_COR[c] for c in df_class["classificacao"]]
                fig = go.Figure(
                    go.Bar(
                        x=df_class["classificacao"].astype(str),
                        y=df_class["total"],
                        marker=dict(color=cores, cornerradius=4),
                        text=[fmt_int(v) for v in df_class["total"]],
                        textposition="outside",
                        textfont=dict(color=INK_MUTED, size=12),
                        customdata=[fmt_int(v) for v in df_class["total"]],
                        hovertemplate="%{x}<br>%{customdata} empresas<extra></extra>",
                        width=0.5,
                    )
                )
                fig.update_layout(**base_layout(showlegend=False, height=320))
                fig.update_xaxes(**axis_style())
                fig.update_yaxes(**axis_style(title="Empresas"))
                st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
            else:
                st.info("Sem dados na view v_leads_by_classificacao.")

    with col_dir:
        st.subheader("Top 10 segmentos")
        with st.container(border=True):
            df_seg = carregar_por_segmento(10)
            if not df_seg.empty:
                df_seg = df_seg.sort_values("total")
                fig = go.Figure(
                    go.Bar(
                        x=df_seg["total"],
                        y=[truncar(s) for s in df_seg["segmento"]],
                        orientation="h",
                        marker=dict(color=BLUE, cornerradius=4),
                        text=[fmt_int(v) for v in df_seg["total"]],
                        textposition="outside",
                        textfont=dict(color=INK_MUTED, size=11),
                        cliponaxis=False,
                        customdata=list(zip(df_seg["segmento"], [fmt_int(v) for v in df_seg["total"]])),
                        hovertemplate="%{customdata[0]}<br>%{customdata[1]} empresas<extra></extra>",
                    )
                )
                fig.update_layout(**base_layout(showlegend=False, height=320, margin=dict(l=8, r=48, t=8, b=8)))
                fig.update_xaxes(**axis_style(title="Empresas", range=[0, df_seg["total"].max() * 1.18]))
                fig.update_yaxes(**axis_style())
                st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
            else:
                st.info("Sem dados na view v_leads_by_segmento.")

    st.subheader("Distribuição por UF")
    with st.container(border=True):
        df_uf = carregar_por_uf()
        if not df_uf.empty:
            pivot_uf = df_uf.pivot_table(index="uf", columns="classificacao", values="total", fill_value=0)
            ordem_uf = pivot_uf.sum(axis=1).sort_values(ascending=False).index
            pivot_uf = pivot_uf.reindex(ordem_uf)
            classes_presentes = [c for c in CLASSIFICACAO_ORDEM if c in pivot_uf.columns]

            fig = go.Figure()
            for i, classe in enumerate(classes_presentes):
                # so o segmento mais externo da pilha (o ultimo a entrar) recebe ponta
                # arredondada - o resto fica reto, encostando na barra vizinha.
                eh_externo = i == len(classes_presentes) - 1
                fig.add_trace(
                    go.Bar(
                        name=classe,
                        x=pivot_uf.index,
                        y=pivot_uf[classe],
                        marker=dict(
                            color=CLASSIFICACAO_COR[classe],
                            cornerradius=4 if eh_externo else 0,
                            line=dict(color="#fcfcfb", width=2),
                        ),
                        customdata=[fmt_int(v) for v in pivot_uf[classe]],
                        hovertemplate=f"%{{x}} · {classe}<br>%{{customdata}} empresas<extra></extra>",
                    )
                )
            fig.update_layout(**base_layout(barmode="stack", height=380))
            fig.update_xaxes(**axis_style())
            fig.update_yaxes(**axis_style(title="Empresas"))
            st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
        else:
            st.info("Sem dados na view v_leads_by_uf.")

with tab_explorar:
    st.subheader("Explorar leads — piloto de enriquecimento de contato")

    f1, f2, f3 = st.columns([1, 1, 1])
    ufs_selecionadas = f1.multiselect("UF", options=UFS_ICP, default=[])
    segmento_busca = f2.text_input("Segmento contém", value="")
    score_min = f3.slider("Score mínimo", min_value=0, max_value=100, value=60, step=5)

    df_piloto = carregar_piloto_enriquecido()

    if df_piloto.empty:
        st.info("Nenhum CNPJ processado no piloto de enriquecimento ainda.")
    else:
        filtro = df_piloto["score"] >= score_min
        if ufs_selecionadas:
            filtro &= df_piloto["uf"].isin(ufs_selecionadas)
        if segmento_busca:
            filtro &= df_piloto["segmento"].str.contains(segmento_busca, case=False, na=False)
        df_piloto_filtrado = df_piloto[filtro]

        st.caption(
            f"{len(df_piloto_filtrado)} de {len(df_piloto)} CNPJs do piloto de enriquecimento passam nesse "
            f"filtro (o piloto cobre {len(df_piloto)} dos {fmt_int(quentes_80)} leads quentes no total)."
        )

        tem_contato = df_piloto_filtrado["tem_contato"] == True  # noqa: E712 - comparacao explicita, coluna sem NaN aqui

        df_com_contato = df_piloto_filtrado[tem_contato].drop(columns=["tem_contato"]).copy()
        df_com_contato[["telefone", "email", "site"]] = df_com_contato[["telefone", "email", "site"]].fillna("—")
        df_sem_contato = df_piloto_filtrado[~tem_contato].drop(columns=["telefone", "email", "site", "tem_contato"])

        st.subheader(f"📞 Leads com contato disponível ({len(df_com_contato)})")
        if not df_com_contato.empty:
            st.dataframe(df_com_contato, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum lead com contato disponível nesse filtro.")

        st.subheader(f"◻️ Leads sem contato ({len(df_sem_contato)})")
        if not df_sem_contato.empty:
            st.dataframe(df_sem_contato, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum lead sem contato nesse filtro.")
