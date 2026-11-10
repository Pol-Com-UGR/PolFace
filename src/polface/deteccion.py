"""Detección de caras y extracción de embeddings (InsightFace).

InsightFace se importa de forma perezosa para que el resto del paquete
(y los tests) funcionen sin tener instalado el modelo.

IMPORTANTE: los modelos preentrenados de InsightFace (p. ej. ``buffalo_l``)
se distribuyen solo para investigación no comercial. Ver AVISO_DE_USO.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Protocol

import numpy as np

from .i18n import m


@dataclass
class CaraDetectada:
    """Una cara encontrada en un fotograma."""

    bbox: tuple  # (x1, y1, x2, y2) en píxeles, ya recortado al fotograma
    score: float  # confianza del detector
    embedding: np.ndarray  # vector normalizado (norma 1)


class Detector(Protocol):
    """Cualquier objeto con este método sirve (útil para tests)."""

    def detectar(self, frame_bgr: np.ndarray) -> List[CaraDetectada]: ...


class DetectorInsightFace:
    """Detector + embeddings con InsightFace.

    Parameters
    ----------
    modelo:
        Nombre del paquete de modelos de InsightFace (por defecto ``buffalo_l``).
    dispositivo:
        ``"auto"`` (GPU si hay), ``"cuda"`` o ``"cpu"``.
    tam_deteccion:
        Tamaño de entrada del detector. Más grande = más caras pequeñas
        detectadas, pero más lento.
    """

    def __init__(self, modelo: str = "buffalo_l", dispositivo: str = "auto",
                 tam_deteccion: int = 640):
        try:
            from insightface.app import FaceAnalysis
            import onnxruntime
        except ImportError as e:  # pragma: no cover
            raise SystemExit(m(
                "Falta instalar InsightFace. Ejecuta:\n"
                "  pip install insightface onnxruntime      (CPU)\n"
                "  pip install insightface onnxruntime-gpu  (GPU NVIDIA)",
                "InsightFace is not installed. Run:\n"
                "  pip install insightface onnxruntime      (CPU)\n"
                "  pip install insightface onnxruntime-gpu  (NVIDIA GPU)"
            )) from e

        disponibles = onnxruntime.get_available_providers()
        usar_gpu = (dispositivo == "cuda") or (
            dispositivo == "auto" and "CUDAExecutionProvider" in disponibles)
        if dispositivo == "cuda" and "CUDAExecutionProvider" not in disponibles:
            raise SystemExit(m(
                "Has pedido --dispositivo cuda pero onnxruntime no ve la GPU. "
                "Instala onnxruntime-gpu o usa --dispositivo cpu.",
                "You asked for --dispositivo cuda but onnxruntime cannot see the GPU. "
                "Install onnxruntime-gpu or use --dispositivo cpu."))
        proveedores = (["CUDAExecutionProvider", "CPUExecutionProvider"]
                       if usar_gpu else ["CPUExecutionProvider"])
        self.dispositivo = "cuda" if usar_gpu else "cpu"

        # Solo necesitamos detección + reconocimiento (no edad/género/landmarks 3D).
        self._app = FaceAnalysis(
            name=modelo, providers=proveedores,
            allowed_modules=["detection", "recognition"])
        self._app.prepare(ctx_id=0 if usar_gpu else -1,
                          det_size=(tam_deteccion, tam_deteccion))

    def detectar(self, frame_bgr: np.ndarray) -> List[CaraDetectada]:
        # InsightFace espera imágenes BGR (como las devuelve OpenCV): no convertir a RGB.
        alto, ancho = frame_bgr.shape[:2]
        caras = []
        for f in self._app.get(frame_bgr):
            x1, y1, x2, y2 = (int(round(v)) for v in f.bbox)
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(ancho, x2), min(alto, y2)
            if x2 <= x1 or y2 <= y1:
                continue
            emb = np.asarray(f.normed_embedding, dtype=np.float32)
            caras.append(CaraDetectada((x1, y1, x2, y2), float(f.det_score), emb))
        return caras
