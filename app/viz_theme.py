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

# Ordinal (sequencial azul, um so hue) para a escala de qualidade do lead:
# mais escuro = mais quente. Piso de contraste 2:1 no claro = step 250.
CLASSIFICACAO_ORDEM = ["🟢 Lead Quente", "🟡 Lead Bom", "🟠 Nutrição"]
ORDINAL_BLUE = {
    "🟢 Lead Quente": "#1c5cab",  # step 550
    "🟡 Lead Bom": "#3987e5",     # step 400
    "🟠 Nutrição": "#86b6ef",     # step 250
}

FONT = dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", color=INK_PRIMARY, size=13)


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
    )
    style.update(overrides)
    return style


def fmt_int(n) -> str:
    """Formata inteiro no padrao pt-BR (652.663)."""
    return f"{int(n):,}".replace(",", ".")
