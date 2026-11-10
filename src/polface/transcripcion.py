"""Transcripción de vídeos con Whisper (faster-whisper) y unión con las apariciones.

Flujo:
  1. ``polface transcribir``: transcribe cada vídeo completo y guarda un CSV de
     segmentos (inicio, fin, texto) por vídeo.
  2. ``polface unir``: para cada aparición de una persona, añade el texto que se
     oye en una ventana de tiempo alrededor del momento en que se la ve.

AVISO: no hay separación de hablantes (diarización). El texto unido es el
**contexto sonoro** en el que aparece la persona, no necesariamente lo que dice
ella: en un informativo suele hablar el presentador o el periodista mientras se
ve a un político. Interprétalo como contexto, no como habla de la persona.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import pandas as pd

from .i18n import m

COLUMNAS_SEGMENTOS = ["video", "inicio", "fin", "texto", "idioma", "prob_idioma",
                      "avg_logprob", "no_speech_prob"]


def crear_modelo(nombre: str = "large-v3", dispositivo: str = "auto",
                 compute_type: Optional[str] = None):
    """Carga un modelo faster-whisper.

    ``large-v3`` es el más preciso; ``large-v3-turbo`` es mucho más rápido con
    una pérdida de calidad pequeña. Sin GPU, usa ``--modelo small`` o ``medium``.
    """
    try:
        from faster_whisper import WhisperModel
        import ctranslate2
    except ImportError as e:  # pragma: no cover
        raise SystemExit(m(
            "Falta instalar faster-whisper. Ejecuta:\n  pip install 'polface[transcripcion]'",
            "faster-whisper is not installed. Run:\n  pip install 'polface[transcripcion]'")) from e

    hay_gpu = ctranslate2.get_cuda_device_count() > 0
    if dispositivo == "cuda" and not hay_gpu:
        raise SystemExit(m("Has pedido --dispositivo cuda pero no se detecta ninguna GPU.", "You asked for --dispositivo cuda but no GPU was detected."))
    usar_gpu = dispositivo == "cuda" or (dispositivo == "auto" and hay_gpu)
    dev = "cuda" if usar_gpu else "cpu"
    ct = compute_type or ("float16" if usar_gpu else "int8")
    modelo = WhisperModel(nombre, device=dev, compute_type=ct)
    modelo.dispositivo = dev  # para informar al usuario
    return modelo


def nombre_csv(video: str) -> str:
    """Nombre de fichero seguro para el CSV de un vídeo (``a/b.mp4`` -> ``a__b.csv``)."""
    base = re.sub(r"[\\/]+", "__", Path(video).with_suffix("").as_posix())
    return base + ".csv"


def transcribir_video(ruta: Path, modelo, nombre: Optional[str] = None,
                      idioma: str = "auto", log: Optional[Callable] = None):
    """Transcribe un vídeo. Devuelve ``(DataFrame de segmentos, duración en s)``.

    ``modelo`` es cualquier objeto con el método ``transcribe`` de faster-whisper.
    Se activa el filtro de voz (VAD) y se desactiva el uso del texto previo como
    contexto, que reduce las "alucinaciones" en pasajes con música o silencio.

    ``idioma="auto"`` deja que Whisper detecte el idioma de cada vídeo (se
    detecta una vez por vídeo, con los primeros 30 s). Si un vídeo mezcla
    idiomas, fija ``idioma`` a mano. El idioma y la probabilidad de la detección
    se guardan en cada segmento (``idioma``, ``prob_idioma``).
    """
    ruta = Path(ruta)
    nombre = nombre or ruta.name
    segmentos, info = modelo.transcribe(
        str(ruta), language=None if idioma == "auto" else idioma, beam_size=5,
        vad_filter=True, condition_on_previous_text=False)
    lang = getattr(info, "language", None) or ("" if idioma == "auto" else idioma)
    prob = round(float(getattr(info, "language_probability", 1.0)), 3)
    filas = []
    for s in segmentos:
        filas.append({
            "video": nombre,
            "inicio": round(float(s.start), 2),
            "fin": round(float(s.end), 2),
            "texto": s.text.strip(),
            "idioma": lang,
            "prob_idioma": prob,
            "avg_logprob": round(float(s.avg_logprob), 3),
            "no_speech_prob": round(float(s.no_speech_prob), 3),
        })
        if log:
            log(f"   {s.start:7.1f}s  {s.text.strip()}")
    return pd.DataFrame(filas, columns=COLUMNAS_SEGMENTOS), float(info.duration)


def cargar_transcripciones(carpeta: Path) -> dict:
    """Lee todos los CSV de segmentos de una carpeta. Devuelve ``{video: DataFrame}``."""
    carpeta = Path(carpeta)
    if not carpeta.is_dir():
        raise SystemExit(m("No existe la carpeta de transcripciones: {c}", "The transcripts folder does not exist: {c}", c=carpeta))
    out = {}
    for f in sorted(carpeta.glob("*.csv")):
        df = pd.read_csv(f)
        if df.empty or "video" not in df.columns:
            continue
        df = df.dropna(subset=["inicio", "fin"]).sort_values("inicio")
        out[str(df["video"].iloc[0])] = df.reset_index(drop=True)
    return out


def texto_en_ventana(seg: pd.DataFrame, t: float, ventana: float):
    """Texto de los segmentos que se solapan con ``[t - ventana, t + ventana]``.

    Devuelve ``(texto, n_segmentos)``.
    """
    ini = seg["inicio"].to_numpy()
    fin = seg["fin"].to_numpy()
    lo = np.searchsorted(np.maximum.accumulate(fin), t - ventana, side="left")
    hi = np.searchsorted(ini, t + ventana, side="right")
    idx = [i for i in range(lo, hi) if fin[i] >= t - ventana and ini[i] <= t + ventana]
    textos = [str(seg["texto"].iloc[i]) for i in idx if isinstance(seg["texto"].iloc[i], str)]
    return " ".join(textos).strip(), len(idx)


def resumen_ventana(seg: pd.DataFrame, t: float, ventana: float) -> dict:
    """Texto, idioma y puntuaciones agregadas de la ventana ``[t - ventana, t + ventana]``.

    Las columnas ``sent_*`` (sentimiento) se promedian y las ``tox_*`` (toxicidad)
    se resumen con el máximo. Devuelve un diccionario listo para añadir a la tabla.
    """
    ini = seg["inicio"].to_numpy()
    fin = seg["fin"].to_numpy()
    lo = np.searchsorted(np.maximum.accumulate(fin), t - ventana, side="left")
    hi = np.searchsorted(ini, t + ventana, side="right")
    idx = [i for i in range(lo, hi) if fin[i] >= t - ventana and ini[i] <= t + ventana]
    sub = seg.iloc[idx]
    textos = [x for x in sub["texto"] if isinstance(x, str)]
    out = {"texto": " ".join(textos).strip(), "n_segmentos_texto": len(idx)}
    if "idioma" in sub.columns:
        langs = sub["idioma"].dropna().astype(str)
        langs = langs[langs != ""]
        out["idioma_texto"] = langs.mode().iloc[0] if len(langs) else ""
    for c in seg.columns:
        if c.startswith("sent_") and not c.endswith("_ok"):
            out[c] = sub[c].mean() if len(sub) else np.nan
        elif c.startswith("tox_") and not c.endswith("_ok"):
            out[c] = sub[c].max() if len(sub) else np.nan
    return out


def unir_texto(det: pd.DataFrame, transcripciones: dict,
               ventana: float = 5.0) -> pd.DataFrame:
    """Añade a cada aparición el texto oído alrededor de ``tiempo_seg``.

    Añade ``texto``, ``n_segmentos_texto``, ``idioma_texto`` y, si las
    transcripciones se han puntuado con ``polface texto``, el sentimiento medio
    (``sent_*``) y la toxicidad máxima (``tox_*``) de la ventana. Si un vídeo no
    tiene transcripción, ``texto`` queda vacío y ``n_segmentos_texto`` es NaN.
    """
    det = det.copy()
    det["texto"] = ""
    det["n_segmentos_texto"] = np.nan
    if det.empty:
        return det
    # El texto solo depende del vídeo y del instante: calcular una vez por instante.
    tiempos = det[["video", "tiempo_seg"]].drop_duplicates()
    filas = []
    for video, t in zip(tiempos["video"], tiempos["tiempo_seg"]):
        seg = transcripciones.get(video)
        if seg is None:
            continue
        filas.append({"video": video, "tiempo_seg": t, **resumen_ventana(seg, float(t), ventana)})
    if not filas:
        return det
    tabla = pd.DataFrame(filas)
    det = det.drop(columns=["texto", "n_segmentos_texto"]).merge(
        tabla, on=["video", "tiempo_seg"], how="left")
    det["texto"] = det["texto"].fillna("")
    return det
