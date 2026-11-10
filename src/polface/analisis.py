"""Estadísticos descriptivos a partir de las detecciones.

Entrada: ``detecciones.csv`` y ``videos.csv`` (los genera ``polface analizar``).
Todas las cifras de "tiempo en pantalla" son ESTIMACIONES: cada fotograma
muestreado representa ``cada_segundos`` segundos de vídeo.
"""

from __future__ import annotations

import pandas as pd


def _fotogramas_unicos(det: pd.DataFrame) -> pd.DataFrame:
    """Una fila por (vídeo, fotograma, persona), aunque la cara salga repetida."""
    return (det.sort_values("area_relativa", ascending=False)
               .drop_duplicates(["video", "fotograma", "persona"]))


def resumen_por_persona(det: pd.DataFrame, videos: pd.DataFrame) -> pd.DataFrame:
    """Apariciones, tiempo estimado en pantalla y tamaño medio de la cara."""
    cols = ["persona", "n_fotogramas", "tiempo_pantalla_seg", "n_videos",
            "area_relativa_media", "area_relativa_mediana", "distancia_media"]
    if det.empty:
        return pd.DataFrame(columns=cols)
    u = _fotogramas_unicos(det).merge(
        videos[["video", "cada_segundos"]], on="video", how="left")
    u["cada_segundos"] = u["cada_segundos"].fillna(1.0)
    g = u.groupby("persona")
    out = pd.DataFrame({
        "n_fotogramas": g.size(),
        "tiempo_pantalla_seg": g["cada_segundos"].sum(),
        "n_videos": g["video"].nunique(),
        "area_relativa_media": g["area_relativa"].mean(),
        "area_relativa_mediana": g["area_relativa"].median(),
        "distancia_media": g["distancia"].mean(),
    }).reset_index()
    return out.sort_values("tiempo_pantalla_seg", ascending=False).round(4)[cols]


def resumen_por_video(det: pd.DataFrame, videos: pd.DataFrame) -> pd.DataFrame:
    """Tiempo estimado en pantalla de cada persona en cada vídeo y su % del vídeo."""
    cols = ["video", "persona", "n_fotogramas", "tiempo_pantalla_seg",
            "duracion_video_seg", "porcentaje_video"]
    if det.empty:
        return pd.DataFrame(columns=cols)
    u = _fotogramas_unicos(det).merge(
        videos[["video", "cada_segundos", "duracion_seg"]], on="video", how="left")
    u["cada_segundos"] = u["cada_segundos"].fillna(1.0)
    out = (u.groupby(["video", "persona"])
             .agg(n_fotogramas=("fotograma", "size"),
                  tiempo_pantalla_seg=("cada_segundos", "sum"),
                  duracion_video_seg=("duracion_seg", "first"))
             .reset_index())
    out["porcentaje_video"] = (100 * out["tiempo_pantalla_seg"]
                               / out["duracion_video_seg"]).round(2)
    return out[cols].sort_values(["video", "tiempo_pantalla_seg"],
                                 ascending=[True, False])


def coapariciones(det: pd.DataFrame) -> pd.DataFrame:
    """Matriz de fotogramas en los que aparecen juntas dos personas."""
    u = _fotogramas_unicos(det)
    if u.empty:
        return pd.DataFrame()
    u = u.assign(valor=1)
    m = u.pivot_table(index=["video", "fotograma"], columns="persona",
                      values="valor", aggfunc="max", fill_value=0)
    return m.T.dot(m)
