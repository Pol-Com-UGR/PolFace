"""Galería de referencia: embeddings de las personas que se quieren localizar.

El usuario aporta una carpeta con una subcarpeta por persona::

    referencias/
        Persona Uno/  foto1.jpg  foto2.jpg ...
        Persona Dos/  foto1.jpg ...

El repositorio NO incluye caras de nadie. La galería generada (.npz) contiene
datos biométricos (embeddings faciales): no debe subirse a ningún repositorio
ni compartirse. Ver AVISO_DE_USO.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np

from .deteccion import Detector
from .i18n import m

EXTENSIONES_IMAGEN = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


@dataclass
class Galeria:
    nombres: List[str]  # un nombre por embedding (se repiten)
    embeddings: np.ndarray  # (n, d), normalizados

    @property
    def personas(self) -> List[str]:
        return sorted(set(self.nombres))

    def guardar(self, ruta: Path) -> None:
        np.savez_compressed(ruta, nombres=np.array(self.nombres),
                            embeddings=self.embeddings)

    @classmethod
    def cargar(cls, ruta: Path) -> "Galeria":
        d = np.load(ruta, allow_pickle=False)
        return cls([str(n) for n in d["nombres"]], d["embeddings"].astype(np.float32))

    def identificar(self, embedding: np.ndarray, umbral: float = 0.5
                    ) -> Tuple[Optional[str], float, float]:
        """Devuelve (persona o None, distancia, distancia a la segunda persona).

        La distancia es la distancia coseno (1 - similitud) al embedding de
        referencia más cercano de cada persona. Si la mejor persona queda por
        encima de ``umbral`` se devuelve ``None`` (desconocido).
        ``distancia_segunda`` ayuda a detectar casos ambiguos.
        """
        if len(self.nombres) == 0:
            return None, 1.0, 1.0
        emb = embedding / (np.linalg.norm(embedding) + 1e-12)
        dist = 1.0 - self.embeddings @ emb
        mejor_por_persona = {}
        for nombre, d in zip(self.nombres, dist):
            if nombre not in mejor_por_persona or d < mejor_por_persona[nombre]:
                mejor_por_persona[nombre] = float(d)
        orden = sorted(mejor_por_persona.items(), key=lambda kv: kv[1])
        nombre, d1 = orden[0]
        d2 = orden[1][1] if len(orden) > 1 else 1.0
        return (nombre if d1 < umbral else None), d1, d2


def construir_galeria(carpeta: Path, detector: Detector,
                      avisar=print) -> Galeria:
    """Crea la galería a partir de ``carpeta/<persona>/<imagen>``.

    En cada imagen se usa la cara más grande. Se avisa de las imágenes sin cara
    y de las que tienen varias (para que compruebes que es la persona correcta).
    """
    carpeta = Path(carpeta)
    if not carpeta.is_dir():
        raise SystemExit(m("No existe la carpeta de referencias: {c}", "The references folder does not exist: {c}", c=carpeta))
    nombres: List[str] = []
    embs: List[np.ndarray] = []
    for sub in sorted(p for p in carpeta.iterdir() if p.is_dir()):
        n_ok = 0
        for img_path in sorted(sub.iterdir()):
            if img_path.suffix.lower() not in EXTENSIONES_IMAGEN:
                continue
            img = cv2.imread(str(img_path))
            if img is None:
                avisar(f"  [aviso] no se pudo leer {img_path}")
                continue
            caras = detector.detectar(img)
            if not caras:
                avisar(f"  [aviso] sin cara detectada: {img_path}")
                continue
            if len(caras) > 1:
                avisar(f"  [aviso] {len(caras)} caras en {img_path}; se usa la mayor")
            mayor = max(caras, key=lambda c: (c.bbox[2] - c.bbox[0]) * (c.bbox[3] - c.bbox[1]))
            nombres.append(sub.name)
            embs.append(mayor.embedding)
            n_ok += 1
        avisar(f"{sub.name}: {n_ok} imágenes válidas")
        if n_ok == 0:
            avisar(f"  [aviso] {sub.name} no tiene ninguna imagen válida y quedará fuera")
    if not embs:
        raise SystemExit(m("No se pudo extraer ninguna cara de referencia.", "No reference face could be extracted."))
    return Galeria(nombres, np.vstack(embs).astype(np.float32))
