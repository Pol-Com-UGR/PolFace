"""Tests sin modelos: un detector falso devuelve embeddings controlados."""

import numpy as np
import pandas as pd
import cv2
import pytest

from polface import analisis
from polface.deteccion import CaraDetectada
from polface.galeria import Galeria
from polface.video import analizar_video, listar_videos


def unit(v):
    v = np.asarray(v, dtype=np.float32)
    return v / np.linalg.norm(v)


A, B = unit([1, 0, 0]), unit([0, 1, 0])


@pytest.fixture
def galeria():
    # Ana tiene dos referencias; Beto una.
    return Galeria(["Ana", "Ana", "Beto"],
                   np.vstack([A, unit([0.95, 0.05, 0]), B]))


def test_identificar_acepta_y_rechaza(galeria):
    p, d, d2 = galeria.identificar(A, umbral=0.5)
    assert p == "Ana" and d < 1e-5 and d2 > 0.9
    p, d, _ = galeria.identificar(unit([0, 0, 1]), umbral=0.5)
    assert p is None and d > 0.5


def test_galeria_guardar_cargar(tmp_path, galeria):
    ruta = tmp_path / "g.npz"
    galeria.guardar(ruta)
    g2 = Galeria.cargar(ruta)
    assert g2.nombres == galeria.nombres
    assert np.allclose(g2.embeddings, galeria.embeddings)


class DetectorFalso:
    """Devuelve a Ana en los fotogramas con número de 'segundo' par."""

    def __init__(self):
        self.llamadas = 0

    def detectar(self, frame):
        self.llamadas += 1
        # el valor del primer píxel codifica el segundo del vídeo (ver crear_video)
        segundo = int(round(float(frame[:, :, 0].mean()) / 40))
        caras = [CaraDetectada((10, 10, 110, 110), 0.99, A)] if segundo % 2 == 0 else []
        if segundo == 3:
            caras.append(CaraDetectada((200, 20, 240, 60), 0.9, unit([0, 0, 1])))
        return caras


def crear_video(ruta, segundos=6, fps=10):
    w = cv2.VideoWriter(str(ruta), cv2.VideoWriter_fourcc(*"MJPG"), fps, (320, 240))
    for s in range(segundos):
        for _ in range(fps):
            frame = np.full((240, 320, 3), 0, np.uint8)
            frame[:, :, 0] = s * 40  # el azul codifica el segundo (x40 por la compresión)
            w.write(frame)
    w.release()


def test_analizar_video_muestreo_y_tiempos(tmp_path, galeria):
    ruta = tmp_path / "prueba.avi"
    crear_video(ruta, segundos=6, fps=10)
    det = DetectorFalso()
    info, filas = analizar_video(ruta, det, galeria, cada_segundos=1.0)
    assert det.llamadas == 6  # un fotograma por segundo
    assert info.fotogramas_muestreados == 6
    assert abs(info.duracion_seg - 6.0) < 0.2
    # Ana en los segundos 0, 2 y 4; el desconocido no se guarda por defecto
    assert [f["persona"] for f in filas] == ["Ana"] * 3
    assert filas[0]["area_relativa"] == pytest.approx(100 * 100 / (320 * 240), rel=1e-3)

    _, filas2 = analizar_video(ruta, det, galeria, cada_segundos=1.0,
                               guardar_desconocidos=True)
    assert any(f["persona"] == "Desconocido" for f in filas2)

    _, filas3 = analizar_video(ruta, det, galeria, cada_segundos=1.0, area_minima=20000)
    assert filas3 == []  # la cara de 100x100 es menor que el mínimo


def test_listar_videos(tmp_path):
    (tmp_path / "sub").mkdir()
    for n in ["a.mp4", "sub/b.MKV", "nota.txt"]:
        (tmp_path / n).write_bytes(b"")
    assert [p.name for p in listar_videos(tmp_path)] == ["a.mp4", "b.MKV"]


def test_resumen_descriptivos(tmp_path, galeria):
    ruta = tmp_path / "prueba.avi"
    crear_video(ruta)
    info, filas = analizar_video(ruta, DetectorFalso(), galeria, cada_segundos=1.0)
    from dataclasses import asdict
    det, vid = pd.DataFrame(filas), pd.DataFrame([asdict(info)])
    pp = analisis.resumen_por_persona(det, vid)
    assert pp.loc[0, "persona"] == "Ana"
    assert pp.loc[0, "tiempo_pantalla_seg"] == pytest.approx(3.0)
    pv = analisis.resumen_por_video(det, vid)
    assert pv.loc[0, "porcentaje_video"] == pytest.approx(50.0, abs=3)


def test_resumen_no_cuenta_dos_veces_la_misma_persona_en_un_fotograma():
    det = pd.DataFrame([
        {"video": "v", "fotograma": 0, "persona": "Ana", "area_relativa": 0.1, "distancia": 0.2},
        {"video": "v", "fotograma": 0, "persona": "Ana", "area_relativa": 0.01, "distancia": 0.4},
    ])
    vid = pd.DataFrame([{"video": "v", "cada_segundos": 2.0, "duracion_seg": 10.0}])
    pp = analisis.resumen_por_persona(det, vid)
    assert pp.loc[0, "n_fotogramas"] == 1 and pp.loc[0, "tiempo_pantalla_seg"] == 2.0


def test_resumen_vacio():
    vid = pd.DataFrame([{"video": "v", "cada_segundos": 1.0, "duracion_seg": 5.0}])
    assert analisis.resumen_por_persona(pd.DataFrame(), vid).empty
    assert analisis.coapariciones(pd.DataFrame(
        columns=["video", "fotograma", "persona", "area_relativa"])).empty


def test_coapariciones():
    det = pd.DataFrame([
        {"video": "v", "fotograma": 0, "persona": "Ana", "area_relativa": 0.1},
        {"video": "v", "fotograma": 0, "persona": "Beto", "area_relativa": 0.1},
        {"video": "v", "fotograma": 25, "persona": "Ana", "area_relativa": 0.1},
    ])
    m = analisis.coapariciones(det)
    assert m.loc["Ana", "Beto"] == 1 and m.loc["Ana", "Ana"] == 2
