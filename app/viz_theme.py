"""
Tema visual compartilhado do dashboard - paleta e specs de mark seguindo o
metodo dataviz (skill `dataviz`): cor atribuida pela funcao (categorica,
sequencial, ordinal), marcas finas, grid recessivo, legenda sempre presente
para 2+ series. Paleta validada (ver skill) para o modo claro, que e o tema
padrao do Streamlit usado neste projeto.
"""

SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
BASELINE = "#c3c2b7"

# Categorica, ordem fixa (slots 1-3) - usada onde ha series distintas por
# identidade (ex: funil de prospeccao), nunca ciclada.
BLUE = "#2a78d6"    # slot 1
ORANGE = "#eb6834"  # slot 2
AQUA = "#1baf7a"    # slot 3
YELLOW = "#d4b106"  # so para a classificacao do lead (nao faz parte do slot 1-3)

# Categorica (identidade, nao ordinal) pra classificacao do lead - bate com
# os emojis usados no resto da UI (KPIs, tabelas). Reusa AQUA/ORANGE dos
# slots 1-3 pra "quente"/"nutricao" ficarem consistentes com o funil.
# Trio validado com scripts/validate_palette.js do skill dataviz: CVD
# deutan ΔE 9.8, visao normal ΔE 18.0 (pisos 8 e 15) - ambos acima do piso.
# O aviso de contraste (<3:1 no claro, no amarelo e no aqua) e mitigado pela
# legenda com emoji+texto sempre visivel nos dois graficos que usam este mapa.
CLASSIFICACAO_ORDEM = ["🟢 Lead Quente", "🟡 Lead Bom", "🟠 Nutrição"]
CLASSIFICACAO_COR = {
    "🟢 Lead Quente": AQUA,
    "🟡 Lead Bom": YELLOW,
    "🟠 Nutrição": ORANGE,
}

FONT = dict(family="'Fira Sans', system-ui, sans-serif", color=INK_PRIMARY, size=13)

# Sem isso a barra de zoom/pan/download do Plotly fica fixa por cima do
# grafico em telas touch (nao tem estado ':hover' pra sumir sozinha).
PLOTLY_CONFIG = {"displayModeBar": False}


def base_layout(**overrides):
    layout = dict(
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=FONT,
        margin=dict(l=8, r=8, t=8, b=8),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.03, xanchor="left", x=0,
            font=dict(color=INK_SECONDARY, size=12),
        ),
        hoverlabel=dict(bgcolor=SURFACE, font=dict(color=INK_PRIMARY, size=12), bordercolor=BASELINE),
    )
    layout.update(overrides)
    return layout


def axis_style(**overrides):
    style = dict(
        gridcolor=GRIDLINE,
        zerolinecolor=BASELINE,
        linecolor=BASELINE,
        tickfont=dict(color=INK_MUTED, size=11),
        title_font=dict(color=INK_SECONDARY, size=12),
        # sem isso o rotulo de categoria (eixo y) corta em vez de empurrar
        # a margem - critico em telas estreitas, ver PR do fix de mobile.
        automargin=True,
    )
    style.update(overrides)
    return style


def fmt_int(n) -> str:
    """Formata inteiro no padrao pt-BR (652.663)."""
    return f"{int(n):,}".replace(",", ".")


def truncar(texto: str, max_len: int = 34) -> str:
    """Corta rotulos longos demais pro eixo de um grafico (ex: nome de
    segmento). O nome completo continua disponivel no hover via customdata -
    truncar so evita que o rotulo espreme o grafico pra quase nada em telas
    estreitas."""
    texto = str(texto)
    if len(texto) <= max_len:
        return texto
    return texto[: max_len - 1].rstrip() + "…"
