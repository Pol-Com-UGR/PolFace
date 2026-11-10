"""Tests de transcripción y unión, con un modelo Whisper simulado."""

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
import cv2

from polface import cli
from polface.transcripcion import (cargar_transcripciones, nombre_csv,
                                   texto_en_ventana, transcribir_video, unir_texto)

SEGMENTOS = [  # (inicio, fin, texto)
    (0.0, 4.0, "Buenas noches."),
    (4.5, 9.0, "El presidente ha comparecido hoy."),
    (20.0, 25.0, "Pasamos a deportes."),
]


class ModeloFalso:
    dispositivo = "cpu"

    def __init__(self):
        self.llamadas = []

    def transcribe(self, ruta, **kw):
        self.llamadas.append((ruta, kw))
        segs = [SimpleNamespace(start=a, end=b, text=f" {t} ", avg_logprob=-0.2,
                                no_speech_prob=0.01) for a, b, t in SEGMENTOS]
        return iter(segs), SimpleNamespace(duration=30.0, language="es", language_probability=0.98)


def seg_df():
    return pd.DataFrame([{"video": "v.mp4", "inicio": a, "fin": b, "texto": t}
                         for a, b, t in SEGMENTOS])


def test_nombre_csv():
    assert nombre_csv("a/b.mp4") == "a__b.csv"
    assert nombre_csv("x.mp4") == "x.csv"


def test_transcribir_video_usa_vad_y_devuelve_segmentos(tmp_path):
    m = ModeloFalso()
    df, dur = transcribir_video(tmp_path / "v.mp4", m, "v.mp4")
    assert dur == 30.0 and list(df["texto"]) == [t for _, _, t in SEGMENTOS]
    kw = m.llamadas[0][1]
    assert kw["language"] is None  # por defecto: detección automática
    assert set(df["idioma"]) == {"es"} and set(df["prob_idioma"]) == {0.98}
    assert kw["vad_filter"] is True
    assert kw["condition_on_previous_text"] is False


def test_texto_en_ventana():
    seg = seg_df()
    assert texto_en_ventana(seg, 2.0, 0.0) == ("Buenas noches.", 1)
    texto, n = texto_en_ventana(seg, 4.2, 1.0)  # toca el primero y el segundo
    assert n == 2 and texto.startswith("Buenas noches. El presidente")
    assert texto_en_ventana(seg, 15.0, 2.0) == ("", 0)  # silencio
    assert texto_en_ventana(seg, 24.0, 0.0)[0] == "Pasamos a deportes."


def test_unir_texto():
    det = pd.DataFrame([
        {"video": "v.mp4", "tiempo_seg": 5.0, "persona": "Ana"},
        {"video": "v.mp4", "tiempo_seg": 5.0, "persona": "Beto"},   # mismo instante
        {"video": "v.mp4", "tiempo_seg": 15.0, "persona": "Ana"},
        {"video": "otro.mp4", "tiempo_seg": 1.0, "persona": "Ana"},  # sin transcripción
    ])
    out = unir_texto(det, {"v.mp4": seg_df()}, ventana=1.0)
    assert len(out) == 4
    assert "El presidente ha comparecido hoy." in out.loc[0, "texto"]
    assert out.loc[0, "texto"] == out.loc[1, "texto"]
    assert out.loc[2, "texto"] == "" and out.loc[2, "n_segmentos_texto"] == 0
    assert out.loc[3, "texto"] == "" and np.isnan(out.loc[3, "n_segmentos_texto"])


def test_unir_texto_vacio():
    det = pd.DataFrame(columns=["video", "tiempo_seg", "persona"])
    assert unir_texto(det, {}, 5.0).empty


def crear_video(ruta, segundos=3, fps=5):
    w = cv2.VideoWriter(str(ruta), cv2.VideoWriter_fourcc(*"MJPG"), fps, (64, 48))
    for _ in range(segundos * fps):
        w.write(np.zeros((48, 64, 3), np.uint8))
    w.release()


def test_cli_transcribir_y_unir(tmp_path, monkeypatch, capsys):
    videos = tmp_path / "videos"
    (videos / "cadena").mkdir(parents=True)
    crear_video(videos / "cadena" / "n1.avi")
    modelo = ModeloFalso()
    monkeypatch.setattr(cli, "crear_modelo", lambda *a, **k: modelo)

    salida = tmp_path / "trans"
    assert cli.main(["transcribir", str(videos), "--salida", str(salida)]) == 0
    assert (salida / "cadena__n1.csv").exists()
    assert not list(salida.glob("*.tmp"))
    assert len(modelo.llamadas) == 1

    # segunda ejecución: se reanuda sin volver a transcribir
    assert cli.main(["transcribir", str(videos), "--salida", str(salida)]) == 0
    assert len(modelo.llamadas) == 1
    assert cli.main(["transcribir", str(videos), "--salida", str(salida), "--rehacer"]) == 0
    assert len(modelo.llamadas) == 2

    res = tmp_path / "res"
    res.mkdir()
    pd.DataFrame([{"video": "cadena/n1.avi", "fotograma": 25, "tiempo_seg": 5.0,
                   "persona": "Ana", "distancia": 0.2, "area_relativa": 0.1}]
                 ).to_csv(res / "detecciones.csv", index=False)
    assert cli.main(["unir", str(res), "--transcripciones", str(salida),
                     "--ventana-segundos", "1"]) == 0
    out = pd.read_csv(res / "detecciones_texto.csv")
    assert "El presidente ha comparecido hoy." in out.loc[0, "texto"]
    assert "contexto sonoro" in capsys.readouterr().out
    assert set(cargar_transcripciones(salida)) == {"cadena/n1.avi"}


def test_cli_unir_sin_detecciones(tmp_path):
    assert cli.main(["unir", str(tmp_path)]) == 1


def test_cli_en_ingles(tmp_path, capsys, monkeypatch):
    res = tmp_path / "res"
    res.mkdir()
    # --lang antes o después de la orden, y también con la variable de entorno
    assert cli.main(["--lang", "en", "unir", str(res)]) == 1
    assert "Cannot find" in capsys.readouterr().err
    assert cli.main(["unir", str(res), "--lang=en"]) == 1
    assert "Cannot find" in capsys.readouterr().err
    assert cli.main(["unir", str(res)]) == 1
    assert "No encuentro" in capsys.readouterr().err  # por defecto, español
    monkeypatch.setenv("POLFACE_LANG", "en")
    assert cli.main(["unir", str(res)]) == 1
    assert "Cannot find" in capsys.readouterr().err
    monkeypatch.delenv("POLFACE_LANG")
    with pytest.raises(SystemExit):
        cli.main(["--lang", "en", "--help"])
    assert "Research tool" in capsys.readouterr().out
    assert cli.main(["unir", str(res)]) == 1  # vuelve a español
    assert "No encuentro" in capsys.readouterr().err


def test_cli_demo(tmp_path, capsys):
    dest = tmp_path / "demo"
    assert cli.main(["demo", str(dest), "--videos-por-grupo", "1", "--lang", "en"]) == 0
    assert "SYNTHETIC" in capsys.readouterr().out
    assert (dest / "videos.csv").exists() and (dest / "detecciones_texto.csv").exists()
    assert cli.main(["resumen", str(dest)]) == 0
