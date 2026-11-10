"""Capa de datos del dashboard: carga, filtros y utilidades (sin Streamlit).

Se mantiene separada de la interfaz para poder probarla y reutilizarla en
cuadernos o scripts propios.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable, List, Optional, Sequence

import numpy as np
import pandas as pd

from . import analisis

EXT_IMAGEN = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
COLUMNAS_DET = ["video", "fotograma", "tiempo_seg", "persona", "distancia",
                "distancia_segunda", "x", "y", "ancho", "alto", "area_relativa",
                "score_deteccion"]
COLUMNAS_VIDEOS = ["video", "duracion_seg", "fps", "ancho", "alto",
                   "fotogramas_muestreados", "cada_segundos"]


@dataclass
class Resultados:
    det: pd.DataFrame          # solo personas identificadas
    videos: pd.DataFrame
    tiene_texto: bool
    desconocidos: int          # caras sin identificar guardadas con --guardar-desconocidos
    aviso: str = ""            # algo que el usuario debería saber (p. ej. texto desactualizado)


def grupo_de(video: str) -> str:
    """Primera carpeta de la ruta del vídeo (p. ej. la cadena), o «(sin carpeta)»."""
    partes = PurePosixPath(str(video).replace("\\", "/")).parts
    return partes[0] if len(partes) > 1 else "(sin carpeta)"


def cargar_resultados(carpeta: Path) -> Resultados:
    """Lee ``videos.csv`` y ``detecciones.csv`` (o ``detecciones_texto.csv`` si está al día)."""
    carpeta = Path(carpeta)
    f_vid, f_det = carpeta / "videos.csv", carpeta / "detecciones.csv"
    f_txt = carpeta / "detecciones_texto.csv"
    if not f_vid.exists():
        raise FileNotFoundError(
            f"No encuentro {f_vid}. Ejecuta antes 'polface analizar' o indica otra carpeta.")
    videos = pd.read_csv(f_vid)
    for c in COLUMNAS_VIDEOS:
        if c not in videos.columns:
            videos[c] = np.nan
    aviso = ""
    if f_txt.exists() and (not f_det.exists() or f_txt.stat().st_mtime >= f_det.stat().st_mtime):
        det = pd.read_csv(f_txt)
    elif f_det.exists():
        det = pd.read_csv(f_det)
        if f_txt.exists():
            aviso = ("Hay un detecciones_texto.csv más antiguo que detecciones.csv; "
                     "no se usa. Vuelve a ejecutar 'polface unir' para incluir el texto.")
    else:
        det = pd.DataFrame(columns=COLUMNAS_DET)
    desconocidos = int((det["persona"] == "Desconocido").sum()) if len(det) else 0
    det = det[det["persona"] != "Desconocido"].copy()
    det["grupo"] = det["video"].map(grupo_de)
    det["area_pct"] = det["area_relativa"] * 100
    det["minuto"] = det["tiempo_seg"] / 60
    videos["grupo"] = videos["video"].map(grupo_de)
    return Resultados(det.reset_index(drop=True), videos, "texto" in det.columns,
                      desconocidos, aviso)


def filtrar(det: pd.DataFrame, personas: Optional[Sequence[str]] = None,
            grupos: Optional[Sequence[str]] = None, videos: Optional[Sequence[str]] = None,
            distancia_max: Optional[float] = None, area_min_pct: float = 0.0,
            idiomas: Optional[Sequence[str]] = None) -> pd.DataFrame:
    """Aplica los filtros de la barra lateral. ``None`` significa «sin filtrar»."""
    m = pd.Series(True, index=det.index)
    if personas is not None:
        m &= det["persona"].isin(personas)
    if grupos is not None:
        m &= det["grupo"].isin(grupos)
    if videos is not None:
        m &= det["video"].isin(videos)
    if distancia_max is not None:
        m &= det["distancia"] <= distancia_max
    if area_min_pct:
        m &= det["area_pct"] >= area_min_pct
    if idiomas is not None and "idioma_texto" in det.columns:
        # solo se excluyen las apariciones cuyo texto está en un idioma no elegido;
        # las que no tienen texto se conservan
        idi = det["idioma_texto"].fillna("")
        m &= (idi == "") | idi.isin(idiomas)
    return det[m]


def videos_seleccionados(videos: pd.DataFrame, grupos: Optional[Sequence[str]] = None,
                         lista: Optional[Sequence[str]] = None) -> pd.DataFrame:
    m = pd.Series(True, index=videos.index)
    if grupos is not None:
        m &= videos["grupo"].isin(grupos)
    if lista is not None:
        m &= videos["video"].isin(lista)
    return videos[m]


def indicadores(det: pd.DataFrame, videos: pd.DataFrame) -> dict:
    """Cifras de cabecera: vídeos, horas de vídeo, personas y detecciones."""
    return {
        "videos": int(len(videos)),
        "horas_video": float(np.nansum(videos["duracion_seg"]) / 3600),
        "personas": int(det["persona"].nunique()) if len(det) else 0,
        "detecciones": int(len(det)),
    }


def tiempo_por_grupo(det: pd.DataFrame, videos: pd.DataFrame) -> pd.DataFrame:
    """Minutos estimados en pantalla de cada persona (filas) en cada grupo (columnas)."""
    pv = analisis.resumen_por_video(det, videos)
    if pv.empty:
        return pd.DataFrame()
    pv["grupo"] = pv["video"].map(grupo_de)
    t = pv.pivot_table(index="persona", columns="grupo", values="tiempo_pantalla_seg",
                       aggfunc="sum", fill_value=0) / 60
    return t.loc[t.sum(axis=1).sort_values(ascending=False).index]


def resumen_texto_por_persona(det: pd.DataFrame) -> pd.DataFrame:
    """Sentimiento medio y toxicidad (media y máxima) del texto asociado a cada persona.

    Solo cuenta apariciones con texto puntuado. Es contexto sonoro, no habla de
    la persona (ver AVISO_DE_USO.md).
    """
    cols = ["persona", "n_apariciones_puntuadas", "polaridad_media", "toxicidad_media",
            "toxicidad_maxima"]
    if "sent_polaridad" not in det.columns and "tox_toxicity" not in det.columns:
        return pd.DataFrame(columns=cols)
    g = det.groupby("persona")
    out = pd.DataFrame(index=g.size().index)
    cols_p = [c for c in ("sent_polaridad", "tox_toxicity") if c in det.columns]
    puntuada = det[cols_p].notna().any(axis=1)
    out["n_apariciones_puntuadas"] = puntuada.groupby(det["persona"]).sum().astype(int)
    if "sent_polaridad" in det.columns:
        out["polaridad_media"] = g["sent_polaridad"].mean()
    if "tox_toxicity" in det.columns:
        out["toxicidad_media"] = g["tox_toxicity"].mean()
        out["toxicidad_maxima"] = g["tox_toxicity"].max()
    out = out.reset_index()
    for c in cols:
        if c not in out.columns:
            out[c] = np.nan
    return out[cols].round(3)


def localizar_video(nombre: str, carpeta_videos: Optional[Path]) -> Optional[Path]:
    """Busca el vídeo ``nombre`` (ruta relativa o solo nombre) dentro de ``carpeta_videos``."""
    if not carpeta_videos:
        return None
    base = Path(carpeta_videos)
    if not base.is_dir():
        return None
    directo = base / nombre
    if directo.is_file():
        return directo
    final = Path(nombre).name
    for p in base.rglob(final):
        if p.is_file():
            return p
    return None


def fotograma_con_cajas(ruta: Path, fotograma: int,
                        cajas: Iterable[tuple]) -> Optional[np.ndarray]:
    """Devuelve el fotograma (RGB) con las cajas ``(x, y, ancho, alto, etiqueta)`` dibujadas."""
    import cv2

    cap = cv2.VideoCapture(str(ruta))
    if not cap.isOpened():
        return None
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(fotograma))
    ok, frame = cap.read()
    cap.release()
    if not ok:
        return None
    alto = frame.shape[0]
    grosor = max(2, round(alto / 270))
    escala = max(0.5, alto / 900)
    for x, y, w, h, etiqueta in cajas:
        x, y, w, h = int(x), int(y), int(w), int(h)
        cv2.rectangle(frame, (x, y), (x + w, y + h), (57, 135, 229)[::-1], grosor)
        (tw, th), base = cv2.getTextSize(etiqueta, cv2.FONT_HERSHEY_SIMPLEX, escala, 1)
        y0 = max(th + base + 2, y)
        cv2.rectangle(frame, (x, y0 - th - base - 2), (x + tw + 6, y0), (57, 135, 229)[::-1], -1)
        cv2.putText(frame, etiqueta, (x + 3, y0 - base - 1), cv2.FONT_HERSHEY_SIMPLEX,
                    escala, (255, 255, 255), 1, cv2.LINE_AA)
    return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)


# ------------------------------------------------------------- caras de referencia
def personas_referencia(carpeta: Optional[Path]) -> dict:
    """Personas ofrecidas al programa: ``carpeta/<Persona>/*.jpg|png...`` → ``{persona: [fotos]}``.

    Solo cuentan las subcarpetas con al menos una imagen. Es la misma estructura que
    usa ``polface galeria``.
    """
    if not carpeta:
        return {}
    base = Path(carpeta)
    if not base.is_dir():
        return {}
    out = {}
    for sub in sorted(p for p in base.iterdir() if p.is_dir() and not p.name.startswith(".")):
        fotos = sorted(f for f in sub.iterdir() if f.suffix.lower() in EXT_IMAGEN)
        if fotos:
            out[sub.name] = fotos
    return out


def completar_resumen(resumen: pd.DataFrame, personas: Sequence[str]) -> pd.DataFrame:
    """Añade con ceros a las personas ofrecidas que no tienen apariciones."""
    faltan = [p for p in personas if p not in set(resumen["persona"])]
    if not faltan:
        return resumen
    extra = pd.DataFrame({"persona": faltan})
    for c in resumen.columns:
        if c != "persona":
            extra[c] = 0 if c in ("n_fotogramas", "n_videos", "tiempo_pantalla_seg") else np.nan
    return pd.concat([resumen, extra], ignore_index=True)


# ------------------------------------------------------------- selector de carpetas
def lugares_rapidos() -> List[tuple]:
    """Accesos directos del buscador de carpetas: discos montados, ownCloud, unidades..."""
    out: List[tuple] = []
    home = Path.home()
    if (home / "owncloud").is_dir():
        out.append(("ownCloud", str(home / "owncloud")))
    if sys.platform.startswith("win"):
        out += [(f"{c}:", f"{c}:\\") for c in "CDEFGHIJ" if Path(f"{c}:\\").exists()]
    else:
        out.append(("/", "/"))
        for base in (Path("/mnt"), Path("/media") / home.name, Path("/Volumes")):
            try:
                out += [(p.name, str(p)) for p in sorted(base.iterdir()) if p.is_dir()]
            except OSError:
                pass
    return out


def subcarpetas(ruta: Path) -> List[str]:
    """Nombres de las subcarpetas visibles de ``ruta`` (vacío si no se puede leer)."""
    try:
        return sorted(p.name for p in Path(ruta).iterdir()
                      if p.is_dir() and not p.name.startswith("."))
    except OSError:
        return []


def contar_videos(carpeta: Optional[str]) -> int:
    """Número de vídeos que ``polface analizar`` encontraría en ``carpeta`` (0 si no existe)."""
    from .video import listar_videos

    if not carpeta or not Path(carpeta).expanduser().exists():
        return 0
    try:
        return len(listar_videos(Path(carpeta).expanduser()))
    except (OSError, SystemExit):
        return 0


def cuda_disponible() -> bool:
    """``True`` si onnxruntime puede usar la GPU NVIDIA (hace falta ``onnxruntime-gpu``)."""
    try:
        import onnxruntime
        return "CUDAExecutionProvider" in onnxruntime.get_available_providers()
    except Exception:  # noqa: BLE001
        return False
