"""Gráficos Plotly del dashboard (paleta de datos validada, un solo eje, marcas finas).

Colores: azul (#2a78d6) para magnitud, rampa azul de claro a oscuro para
mapas de calor y el par azul-rojo para polaridad (positivo/negativo). El
color nunca es el único canal: las categorías van rotuladas en los ejes y los
valores en las barras.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .i18n import tr

AZUL = "#2a78d6"
ROJO = "#e34948"
NARANJA = "#eb6834"
RAMPA_AZUL = ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]
REJILLA = "rgba(128,128,128,0.22)"
TEXTO = "rgba(128,128,128,0.95)"


def _base(fig: go.Figure, alto: int, titulo_x: str = "", titulo_y: str = "") -> go.Figure:
    fig.update_layout(
        height=alto, margin=dict(l=8, r=16, t=8, b=8), showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=13), hoverlabel=dict(font_size=13), bargap=0.35,
    )
    fig.update_xaxes(title_text=titulo_x, gridcolor=REJILLA, zeroline=False,
                     linecolor=REJILLA, automargin=True)
    fig.update_yaxes(title_text=titulo_y, gridcolor=REJILLA, zeroline=False,
                     linecolor=REJILLA, automargin=True)
    try:  # extremos redondeados (Plotly >= 5.23)
        fig.update_layout(barcornerradius=4)
    except ValueError:
        pass
    return fig


def _alto(n: int, por_fila: int = 30, minimo: int = 160) -> int:
    return max(minimo, 70 + por_fila * n)


def barras_tiempo(resumen: pd.DataFrame, idioma: str = "es") -> go.Figure:
    """Minutos estimados en pantalla por persona (barras horizontales, una serie)."""
    d = resumen.sort_values("tiempo_pantalla_seg")
    minutos = d["tiempo_pantalla_seg"] / 60
    fig = go.Figure(go.Bar(
        x=minutos, y=d["persona"], orientation="h", marker_color=AZUL,
        text=[f"{m:,.1f}".replace(",", " ") for m in minutos], textposition="outside",
        cliponaxis=False, customdata=np.c_[d["n_fotogramas"], d["n_videos"]],
        hovertemplate="<b>%{y}</b><br>" + tr(idioma, "g_hover_min", x="%{x:.1f}") + "<br>"
                      + tr(idioma, "g_hover_fv", f="%{customdata[0]}", v="%{customdata[1]}")
                      + "<extra></extra>"))
    return _base(fig, _alto(len(d)), tr(idioma, "g_min_pantalla"))


def mapa_calor(tabla: pd.DataFrame, titulo_color: str = "min", diagonal_nula: bool = False,
               alto: int | None = None) -> go.Figure:
    """Mapa de calor con rampa de un solo tono (azul, de claro a oscuro)."""
    z = tabla.to_numpy(dtype=float).copy()
    if diagonal_nula:
        np.fill_diagonal(z, np.nan)
    pequeno = z.size <= 225
    fig = go.Figure(go.Heatmap(
        z=z, x=list(tabla.columns), y=list(tabla.index),
        colorscale=[[i / (len(RAMPA_AZUL) - 1), c] for i, c in enumerate(RAMPA_AZUL)],
        xgap=2, ygap=2, colorbar=dict(title=titulo_color, thickness=12),
        text=np.round(z, 1) if pequeno else None,
        texttemplate="%{text}" if pequeno else None,
        hovertemplate="%{y} · %{x}<br>%{z:.1f} " + titulo_color + "<extra></extra>"))
    fig.update_yaxes(autorange="reversed")
    return _base(fig, alto or _alto(len(tabla.index), 34, 220))


def linea_tiempo(det_video: pd.DataFrame, duracion_min: float | None = None,
                 idioma: str = "es") -> go.Figure:
    """Cuándo aparece cada persona dentro de un vídeo (una fila por persona)."""
    orden = (det_video.groupby("persona").size().sort_values().index.tolist())
    fig = go.Figure(go.Scatter(
        x=det_video["minuto"], y=det_video["persona"], mode="markers",
        marker=dict(color=AZUL, size=10, symbol="square",
                    line=dict(width=2, color="rgba(255,255,255,0.9)")),
        customdata=np.c_[det_video["distancia"], det_video["area_pct"]],
        hovertemplate="<b>%{y}</b><br>" + tr(idioma, "g_minuto") + " %{x:.2f}<br>"
                      + tr(idioma, "g_distancia") + " %{customdata[0]:.2f} · "
                      + tr(idioma, "g_cara_pct", a="%{customdata[1]:.1f}") + "<extra></extra>"))
    fig.update_yaxes(categoryorder="array", categoryarray=orden)
    if duracion_min:
        fig.update_xaxes(range=[0, duracion_min])
    return _base(fig, _alto(len(orden), 36, 200), tr(idioma, "g_minuto_video"))


def cajas_area(det: pd.DataFrame, idioma: str = "es") -> go.Figure:
    """Tamaño de la cara (% del fotograma) por persona: un indicio de protagonismo."""
    orden = det.groupby("persona")["area_pct"].median().sort_values().index.tolist()
    fig = go.Figure(go.Box(
        x=det["area_pct"], y=det["persona"], orientation="h", marker_color=AZUL,
        line=dict(width=1.5), boxpoints=False,
        hovertemplate="%{y}<br>%{x:.2f} " + tr(idioma, "g_pct_fotograma") + "<extra></extra>"))
    fig.update_yaxes(categoryorder="array", categoryarray=orden)
    return _base(fig, _alto(len(orden)), tr(idioma, "g_area_cara"))


def barras_polaridad(tabla: pd.DataFrame, idioma: str = "es") -> go.Figure:
    """Polaridad media del texto asociado (azul = positivo, rojo = negativo)."""
    d = tabla.dropna(subset=["polaridad_media"]).sort_values("polaridad_media")
    v = d["polaridad_media"]
    fig = go.Figure(go.Bar(
        x=v, y=d["persona"], orientation="h",
        marker_color=[AZUL if x >= 0 else ROJO for x in v],
        text=[f"{x:+.2f}" for x in v], textposition="outside", cliponaxis=False,
        customdata=d["n_apariciones_puntuadas"],
        hovertemplate="<b>%{y}</b><br>" + tr(idioma, "g_pol_media") + " %{x:+.2f}<br>"
                      "%{customdata} " + tr(idioma, "g_apar_punt") + "<extra></extra>"))
    fig.update_xaxes(range=[-1, 1], zeroline=True, zerolinecolor=TEXTO)
    return _base(fig, _alto(len(d)), tr(idioma, "g_polaridad"))


def barras_toxicidad(tabla: pd.DataFrame, idioma: str = "es") -> go.Figure:
    """Toxicidad media del texto asociado (0 a 1)."""
    d = tabla.dropna(subset=["toxicidad_media"]).sort_values("toxicidad_media")
    v = d["toxicidad_media"]
    fig = go.Figure(go.Bar(
        x=v, y=d["persona"], orientation="h", marker_color=NARANJA,
        text=[f"{x:.2f}" for x in v], textposition="outside", cliponaxis=False,
        customdata=np.c_[d["toxicidad_maxima"], d["n_apariciones_puntuadas"]],
        hovertemplate="<b>%{y}</b><br>" + tr(idioma, "g_tox_media") + " %{x:.2f} · "
                      + tr(idioma, "g_maxima") + " %{customdata[0]:.2f}<br>"
                      "%{customdata[1]} " + tr(idioma, "g_apar_punt") + "<extra></extra>"))
    fig.update_xaxes(range=[0, max(0.05, float(v.max()) * 1.25)])
    return _base(fig, _alto(len(d)), tr(idioma, "g_toxicidad"))


def barras_idiomas(conteo: pd.Series, idioma: str = "es") -> go.Figure:
    """Número de apariciones por idioma del texto asociado."""
    d = conteo.sort_values()
    fig = go.Figure(go.Bar(
        x=d.values, y=d.index, orientation="h", marker_color=AZUL,
        text=d.values, textposition="outside", cliponaxis=False,
        hovertemplate="%{y}: %{x} " + tr(idioma, "g_apariciones_n") + "<extra></extra>"))
    return _base(fig, _alto(len(d), 30, 140), tr(idioma, "g_apariciones"))
