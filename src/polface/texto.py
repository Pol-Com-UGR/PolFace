"""Sentimiento y toxicidad del texto transcrito, con control de idioma.

Los modelos solo están validados en ciertos idiomas. Whisper detecta el idioma
de cada vídeo (columna ``idioma`` de las transcripciones) y aquí:

* si el idioma está entre los que el modelo declara soportados, se puntúa;
* si no, la puntuación queda vacía (NaN) y se avisa, en lugar de devolver cifras
  sin sentido. Se puede forzar con ``--forzar-idioma`` (bajo tu responsabilidad:
  esos resultados no están validados).

Modelos por defecto (todos multilingües):

=============  ===================================================  =====================
Qué            Modelo                                               Idiomas declarados
=============  ===================================================  =====================
Sentimiento    lxyuan/distilbert-base-multilingual-cased-           en, es, fr, de, it, pt,
               sentiments-student (Apache-2.0)                      ar, hi, id, ms, ja, zh
Sentimiento    cardiffnlp/twitter-xlm-roberta-base-sentiment        ar, en, fr, de, hi, it,
(opcional)     (entrenado con tuits; comprueba su licencia)         es, pt
Toxicidad      Detoxify «multilingual» (XLM-RoBERTa base,           en, es, fr, it, pt, tr, ru
               paquete Apache-2.0)
=============  ===================================================  =====================

Ninguno está validado en catalán, euskera ni gallego (aunque Whisper los
transcribe): por defecto esos vídeos no se puntúan.

Estas puntuaciones son automáticas y aproximadas. El sentimiento de un modelo
entrenado con reseñas o tuits no equivale al tono político de una noticia, y los
clasificadores de toxicidad marcan como tóxico cualquier texto con insultos o
palabrolas aunque sea una cita, una broma o una denuncia. Valídalos con una
muestra codificada a mano antes de interpretar resultados.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from .i18n import m

IDIOMAS_SENTIMIENTO_LXYUAN = {"en", "es", "fr", "de", "it", "pt", "ar", "hi", "id", "ms", "ja", "zh"}
IDIOMAS_SENTIMIENTO_CARDIFF = {"ar", "en", "fr", "de", "hi", "it", "es", "pt"}
IDIOMAS_TOXICIDAD_DETOXIFY = {"en", "es", "fr", "it", "pt", "tr", "ru"}

MODELOS_SENTIMIENTO = {
    "lxyuan": ("lxyuan/distilbert-base-multilingual-cased-sentiments-student",
               IDIOMAS_SENTIMIENTO_LXYUAN),
    "cardiffnlp": ("cardiffnlp/twitter-xlm-roberta-base-sentiment",
                   IDIOMAS_SENTIMIENTO_CARDIFF),
}
MODELOS_TOXICIDAD = {"detoxify": ("multilingual", IDIOMAS_TOXICIDAD_DETOXIFY)}


def normalizar_sentimiento(puntuaciones: List[dict]) -> Dict[str, float]:
    """Convierte las etiquetas de un modelo de sentimiento en ``neg/neu/pos``.

    ``puntuaciones`` es la lista ``[{"label": ..., "score": ...}, ...]`` que
    devuelve ``pipeline(..., top_k=None)`` para un texto. Acepta etiquetas con
    nombre (``positive``, ``Neutral``, ``NEG``...) y, si el modelo solo tiene
    ``LABEL_0/1/2``, usa la convención 0=negativo, 1=neutro, 2=positivo.
    """
    out = {"neg": np.nan, "neu": np.nan, "pos": np.nan}
    sin_nombre = {}
    for p in puntuaciones:
        et = str(p["label"]).strip().lower()
        if et.startswith("neg"):
            out["neg"] = float(p["score"])
        elif et.startswith("neu"):
            out["neu"] = float(p["score"])
        elif et.startswith("pos"):
            out["pos"] = float(p["score"])
        elif et.startswith("label_") and et[6:].isdigit():
            sin_nombre[int(et[6:])] = float(p["score"])
    if all(np.isnan(v) for v in out.values()) and len(sin_nombre) == 3:
        out = {"neg": sin_nombre[0], "neu": sin_nombre[1], "pos": sin_nombre[2]}
    return out


class SentimientoHF:
    """Sentimiento con un modelo de Hugging Face (``transformers``)."""

    prefijo = "sent"

    def __init__(self, modelo_id: str, idiomas: Sequence[str], dispositivo: str = "auto",
                 lote: int = 32):
        try:
            import torch
            from transformers import pipeline
        except ImportError as e:  # pragma: no cover
            raise SystemExit(m("Falta instalar las dependencias de texto:\n  pip install 'polface[texto]'",
                               "The text dependencies are not installed:\n  pip install 'polface[texto]'")) from e
        cuda = dispositivo == "cuda" or (dispositivo == "auto" and torch.cuda.is_available())
        self.idiomas = set(idiomas)
        self.lote = lote
        self.modelo_id = modelo_id
        self._pipe = pipeline("text-classification", model=modelo_id, top_k=None,
                              device=0 if cuda else -1)

    def puntuar(self, textos: List[str]) -> pd.DataFrame:
        res = self._pipe(textos, batch_size=self.lote, truncation=True, max_length=256)
        filas = [normalizar_sentimiento(r) for r in res]
        df = pd.DataFrame(filas).add_prefix("sent_")
        df["sent_polaridad"] = df["sent_pos"] - df["sent_neg"]
        return df


class ToxicidadDetoxify:
    """Toxicidad con Detoxify (``multilingual``)."""

    prefijo = "tox"

    def __init__(self, variante: str = "multilingual", idiomas: Sequence[str] = (),
                 dispositivo: str = "auto"):
        try:
            import torch
            from detoxify import Detoxify
        except ImportError as e:  # pragma: no cover
            raise SystemExit(m("Falta instalar las dependencias de texto:\n  pip install 'polface[texto]'",
                               "The text dependencies are not installed:\n  pip install 'polface[texto]'")) from e
        cuda = dispositivo == "cuda" or (dispositivo == "auto" and torch.cuda.is_available())
        self.idiomas = set(idiomas)
        self._modelo = Detoxify(variante, device="cuda" if cuda else "cpu")

    def puntuar(self, textos: List[str]) -> pd.DataFrame:
        res = self._modelo.predict(list(textos))
        return pd.DataFrame({f"tox_{k}": np.asarray(v, dtype=float) for k, v in res.items()})


def crear_puntuadores(sentimiento: str = "lxyuan", toxicidad: str = "detoxify",
                      dispositivo: str = "auto", lote: int = 32) -> list:
    """Crea los puntuadores pedidos (``"no"`` desactiva uno)."""
    out = []
    if sentimiento != "no":
        if sentimiento not in MODELOS_SENTIMIENTO:
            raise SystemExit(m("Modelo de sentimiento desconocido: {x}. Opciones: {o}, no",
                               "Unknown sentiment model: {x}. Options: {o}, no",
                               x=sentimiento, o=", ".join(MODELOS_SENTIMIENTO)))
        mid, idiomas = MODELOS_SENTIMIENTO[sentimiento]
        out.append(SentimientoHF(mid, idiomas, dispositivo, lote))
    if toxicidad != "no":
        if toxicidad not in MODELOS_TOXICIDAD:
            raise SystemExit(m("Modelo de toxicidad desconocido: {x}. Opciones: {o}, no",
                               "Unknown toxicity model: {x}. Options: {o}, no",
                               x=toxicidad, o=", ".join(MODELOS_TOXICIDAD)))
        variante, idiomas = MODELOS_TOXICIDAD[toxicidad]
        out.append(ToxicidadDetoxify(variante, idiomas, dispositivo))
    return out


@dataclass
class InformeTexto:
    """Qué se ha puntuado y qué se ha dejado fuera, para avisar al usuario."""
    segmentos_con_texto: int = 0
    puntuados: Dict[str, int] = field(default_factory=dict)
    idiomas_no_soportados: Dict[str, Dict[str, int]] = field(default_factory=dict)

    def sumar(self, otro: "InformeTexto") -> None:
        self.segmentos_con_texto += otro.segmentos_con_texto
        for k, v in otro.puntuados.items():
            self.puntuados[k] = self.puntuados.get(k, 0) + v
        for k, d in otro.idiomas_no_soportados.items():
            dest = self.idiomas_no_soportados.setdefault(k, {})
            for lang, n in d.items():
                dest[lang] = dest.get(lang, 0) + n


def puntuar_transcripcion(seg: pd.DataFrame, puntuadores: list,
                          forzar_idioma: bool = False) -> Tuple[pd.DataFrame, InformeTexto]:
    """Añade puntuaciones a los segmentos de una transcripción.

    Para cada puntuador añade sus columnas y ``<prefijo>_ok`` (``True`` si el
    segmento se puntuó; ``False`` si tenía texto pero su idioma no está
    soportado). Los segmentos sin texto o de idioma no soportado quedan en NaN.
    """
    seg = seg.copy()
    informe = InformeTexto()
    if "idioma" not in seg.columns:
        seg["idioma"] = ""
    texto = seg["texto"].fillna("").astype(str)
    con_texto = texto.str.strip().str.len() > 0
    informe.segmentos_con_texto = int(con_texto.sum())
    idioma = seg["idioma"].fillna("").astype(str).str.lower()
    for p in puntuadores:
        ok = con_texto & (idioma.isin(p.idiomas) | forzar_idioma)
        seg[f"{p.prefijo}_ok"] = ok
        informe.puntuados[p.prefijo] = int(ok.sum())
        fuera = idioma[con_texto & ~ok].replace("", "desconocido")
        if len(fuera):
            informe.idiomas_no_soportados[p.prefijo] = fuera.value_counts().to_dict()
        if not ok.any():
            continue
        punt = p.puntuar(texto[ok].tolist())
        punt.index = seg.index[ok]
        for c in punt.columns:
            seg[c] = np.nan
            seg.loc[ok, c] = punt[c].to_numpy()
    return seg, informe
