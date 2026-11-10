"""Lectura de vídeos, muestreo temporal y localización de personas."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List, Optional

import cv2

from .deteccion import Detector
from .galeria import Galeria
from .i18n import m

EXTENSIONES_VIDEO = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".ts"}


def listar_videos(ruta: Path) -> List[Path]:
    """Un vídeo suelto o todos los vídeos de una carpeta (recursivo)."""
    ruta = Path(ruta)
    if ruta.is_file():
        return [ruta]
    if not ruta.is_dir():
        raise SystemExit(m("No existe: {r}", "Does not exist: {r}", r=ruta))
    return sorted(p for p in ruta.rglob("*") if p.suffix.lower() in EXTENSIONES_VIDEO)


def nombre_video(ruta: Path, base: Optional[Path] = None) -> str:
    """Identificador de un vídeo en los CSV: ruta relativa a la carpeta de entrada."""
    ruta = Path(ruta)
    return ruta.relative_to(base).as_posix() if base else ruta.name


@dataclass
class InfoVideo:
    video: str
    duracion_seg: float
    fps: float
    ancho: int
    alto: int
    fotogramas_muestreados: int
    cada_segundos: float


def analizar_video(ruta: Path, detector: Detector, galeria: Galeria,
                   cada_segundos: float = 1.0, umbral: float = 0.5,
                   area_minima: int = 0, guardar_desconocidos: bool = False,
                   base: Optional[Path] = None):
    """Analiza un vídeo. Devuelve ``(info_video, lista_de_detecciones)``.

    Se toma un fotograma cada ``cada_segundos`` segundos (independiente de los
    fps del vídeo). Cada detección es un diccionario con la persona, el momento,
    la caja de la cara y su tamaño relativo al fotograma.

    ``area_minima`` descarta caras más pequeñas (en píxeles de lado², p. ej.
    6400 = 80x80), útil para ignorar caras de fondo o de pantallas dentro de
    la imagen.
    """
    ruta = Path(ruta)
    nombre = nombre_video(ruta, base)
    cap = cv2.VideoCapture(str(ruta))
    if not cap.isOpened():
        raise RuntimeError(m("No se pudo abrir el vídeo: {r}", "Could not open the video: {r}", r=ruta))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    ancho = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    alto = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    paso = max(1, int(round(fps * cada_segundos)))

    detecciones = []
    muestreados = 0
    idx = 0
    ultimo_idx = -1
    while True:
        if not cap.grab():  # grab() salta fotogramas sin decodificarlos del todo
            break
        ultimo_idx = idx
        if idx % paso == 0:
            ok, frame = cap.retrieve()
            if ok:
                muestreados += 1
                alto_f, ancho_f = frame.shape[:2]
                for cara in detector.detectar(frame):
                    x1, y1, x2, y2 = cara.bbox
                    w, h = x2 - x1, y2 - y1
                    if w * h < area_minima:
                        continue
                    persona, dist, dist2 = galeria.identificar(cara.embedding, umbral)
                    if persona is None and not guardar_desconocidos:
                        continue
                    detecciones.append({
                        "video": nombre,
                        "fotograma": idx,
                        "tiempo_seg": round(idx / fps, 3),
                        "persona": persona if persona is not None else "Desconocido",
                        "distancia": round(dist, 4),
                        "distancia_segunda": round(dist2, 4),
                        "x": x1, "y": y1, "ancho": w, "alto": h,
                        "area_relativa": round(w * h / (ancho_f * alto_f), 5),
                        "score_deteccion": round(cara.score, 4),
                    })
        idx += 1
    cap.release()
    duracion = (ultimo_idx + 1) / fps if ultimo_idx >= 0 else 0.0
    info = InfoVideo(nombre, round(duracion, 3), round(fps, 3), ancho, alto, muestreados,
                     cada_segundos)
    return info, detecciones
