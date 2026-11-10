"""Datos sintéticos para probar el panel (nada de esto son personas reales).

Se usan con ``polface demo``. Los nombres («Persona A»…) y los textos son inventados.
"""

from pathlib import Path

import numpy as np
import pandas as pd

PERSONAS = ["Persona A", "Persona B", "Persona C", "Persona D", "Persona E", "Persona F"]
SIN_APARICIONES = "Persona G"   # ofrecida al programa, pero no sale en los vídeos de ejemplo
GRUPOS = ["Cadena 1", "Cadena 2", "Cadena 3"]
FRASES = {
    "es": ["Hoy el Gobierno ha presentado nuevas medidas.", "Eres un idiota, dijo el portavoz.",
           "La oposición critica el plan.", "Gracias por acompañarnos."],
    "en": ["The minister announced new measures today.", "Thank you for watching."],
    "ca": ["Moltes gràcies per acompanyar-nos."],
}


def crear(carpeta, n_videos=4, semilla=7, duracion=(900, 1800)):
    carpeta = Path(carpeta)
    rng = np.random.default_rng(semilla)
    videos, dets = [], []
    for g_i, g in enumerate(GRUPOS):
        for k in range(n_videos):
            nombre = f"{g}/noticias_{k + 1:02d}.mp4"
            dur = float(rng.integers(*duracion))
            videos.append(dict(video=nombre, duracion_seg=dur, fps=25.0, ancho=640, alto=360,
                               fotogramas_muestreados=int(dur), cada_segundos=1.0))
            idioma = rng.choice(["es", "es", "es", "en", "ca"])
            for t in range(0, int(dur), 1):
                if rng.random() < 0.35:
                    k_pers = rng.choice(len(PERSONAS), size=rng.integers(1, 3), replace=False)
                    for p_i in k_pers:
                        w = int(rng.integers(40, 220))
                        dets.append(dict(
                            video=nombre, fotograma=t * 25, tiempo_seg=float(t),
                            persona=PERSONAS[(p_i + g_i) % len(PERSONAS)],
                            distancia=round(float(rng.uniform(0.15, 0.5)), 4),
                            distancia_segunda=round(float(rng.uniform(0.5, 0.9)), 4),
                            x=int(rng.integers(0, 300)), y=int(rng.integers(0, 100)),
                            ancho=w, alto=int(w * 1.2), area_relativa=round(w * w * 1.2 / (640 * 360), 5),
                            score_deteccion=round(float(rng.uniform(.7, 1)), 4),
                            _idioma=idioma))
    det = pd.DataFrame(dets)
    vid = pd.DataFrame(videos)
    idioma = det.pop("_idioma")
    carpeta.mkdir(parents=True, exist_ok=True)
    vid.to_csv(carpeta / "videos.csv", index=False)
    det.to_csv(carpeta / "detecciones.csv", index=False)
    # con texto puntuado
    t = det.copy()
    t["texto"] = [rng.choice(FRASES[i]) for i in idioma]
    t["n_segmentos_texto"] = 1
    t["idioma_texto"] = idioma.to_numpy()
    soportado_s = t["idioma_texto"].isin(["es", "en"])
    soportado_t = t["idioma_texto"].isin(["es", "en"])
    t["sent_neg"] = np.where(soportado_s, rng.uniform(0, .6, len(t)), np.nan)
    t["sent_neu"] = np.where(soportado_s, rng.uniform(0, .4, len(t)), np.nan)
    t["sent_pos"] = np.where(soportado_s, rng.uniform(0, .6, len(t)), np.nan)
    t["sent_polaridad"] = t["sent_pos"] - t["sent_neg"]
    t["tox_toxicity"] = np.where(soportado_t, np.where(t["texto"].str.contains("idiota"), .93, rng.uniform(0, .15, len(t))), np.nan)
    t.to_csv(carpeta / "detecciones_texto.csv", index=False)
    crear_caras(carpeta / "referencias")
    return carpeta


def crear_caras(carpeta):
    """Fotos de referencia de mentira (un cuadrado de color con la inicial)."""
    import cv2

    carpeta = Path(carpeta)
    for i, nombre in enumerate(PERSONAS + [SIN_APARICIONES]):
        d = carpeta / nombre
        d.mkdir(parents=True, exist_ok=True)
        img = np.full((120, 120, 3), 60 + 25 * i, np.uint8)
        cv2.putText(img, nombre[-1], (38, 82), cv2.FONT_HERSHEY_SIMPLEX, 2.2, (255, 255, 255), 4)
        cv2.imwrite(str(d / "foto.png"), img)
    return carpeta
