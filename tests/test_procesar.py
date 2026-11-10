"""Análisis desde el panel: ``polface procesar`` y el lanzador en segundo plano."""

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import datos_demo
from polface import cli, trabajo
from polface.galeria import Galeria
from test_nucleo import DetectorFalso, crear_video, unit

A, B = unit([1, 0, 0]), unit([0, 1, 0])


class DetectorConDispositivo(DetectorFalso):
    dispositivo = "cpu"


def test_procesar_hace_todo_y_marca_el_final(tmp_path, monkeypatch, capsys):
    videos = tmp_path / "videos"
    (videos / "cadena").mkdir(parents=True)
    crear_video(videos / "cadena" / "n1.avi")
    caras = datos_demo.crear_caras(tmp_path / "caras")
    monkeypatch.setattr(cli, "_crear_detector", lambda a: DetectorConDispositivo())
    monkeypatch.setattr(cli, "construir_galeria",
                        lambda c, d: Galeria(["Ana", "Beto"], np.vstack([A, B])))
    salida = tmp_path / "res"
    assert cli.main(["procesar", str(videos), "--caras", str(caras), "--salida", str(salida)]) == 0
    assert (salida / "galeria.npz").exists() and (salida / "resumen_por_persona.csv").exists()
    assert (salida / ".procesar_ok").exists()
    det = pd.read_csv(salida / "detecciones.csv")
    assert set(det["persona"]) == {"Ana"} and det["video"].iloc[0] == "cadena/n1.avi"
    out = capsys.readouterr().out
    assert "## galeria" in out and "## analizar" in out and "## resumen" in out
    assert "[1/1] cadena/n1.avi" in out


def test_procesar_sin_videos_no_marca_final(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "_crear_detector", lambda a: DetectorConDispositivo())
    monkeypatch.setattr(cli, "construir_galeria",
                        lambda c, d: Galeria(["Ana"], np.vstack([A])))
    (tmp_path / "vacia").mkdir()
    salida = tmp_path / "res"
    assert cli.main(["procesar", str(tmp_path / "vacia"), "--caras", str(tmp_path),
                     "--salida", str(salida)]) == 1
    assert not (salida / ".procesar_ok").exists()


def test_comando_incluye_opciones():
    c = trabajo.comando("v", "c", "s", idioma="en", cada_segundos=2.0, umbral=0.4,
                        area_minima=6400, dispositivo="cpu", reanudar=True, transcribir=True,
                        modelo_whisper="small")
    assert c[:3] == [sys.executable, "-m", "polface"] and c[3:5] == ["--lang", "en"]
    assert {"procesar", "--reanudar", "--transcribir", "small", "6400"} <= set(c)
    assert "--transcribir" not in trabajo.comando("v", "c", "s")


def esperar(salida, fin=("terminado", "error"), t=20):
    for _ in range(int(t / 0.1)):
        e = trabajo.estado(salida)
        if e.estado in fin:
            return e
        time.sleep(0.1)
    raise AssertionError(trabajo.estado(salida))


GUION_OK = (
    "import sys, time, pathlib\n"
    "print('## analizar', flush=True)\n"
    "for i in (1, 2, 3):\n"
    "    print(f'[{i}/3] v{i}.mp4', flush=True); time.sleep(0.2)\n"
    "pathlib.Path(sys.argv[1], '.procesar_ok').write_text('ok')\n")


def test_trabajo_progreso_y_final_correcto(tmp_path):
    assert trabajo.estado(tmp_path).estado == "ninguno"
    trabajo.iniciar([sys.executable, "-c", GUION_OK, str(tmp_path)], tmp_path)
    e = esperar(tmp_path, ("corriendo",))
    assert e.estado == "corriendo"
    e = esperar(tmp_path)
    assert e.estado == "terminado" and e.paso == "analizar" and (e.hecho, e.total) == (3, 3)
    assert "[3/3] v3.mp4" in e.log


def test_trabajo_error_si_no_hay_marca(tmp_path):
    trabajo.iniciar([sys.executable, "-c", "print('## galeria'); raise SystemExit(3)"], tmp_path)
    e = esperar(tmp_path)
    assert e.estado == "error" and e.paso == "galeria"


def test_trabajo_parar(tmp_path):
    trabajo.iniciar([sys.executable, "-c", "import time; time.sleep(60)"], tmp_path)
    assert trabajo.estado(tmp_path).estado == "corriendo"
    assert trabajo.parar(tmp_path) is True
    assert trabajo.estado(tmp_path).estado == "error"
    assert trabajo.parar(tmp_path) is False          # ya no hay nada que parar


def test_panel_lanza_el_analisis_con_las_carpetas_elegidas(tmp_path, monkeypatch):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    videos = tmp_path / "videos"
    videos.mkdir()
    crear_video(videos / "n1.avi")
    caras = datos_demo.crear_caras(tmp_path / "caras")
    lanzado = {}
    monkeypatch.setattr(trabajo, "iniciar",
                        lambda orden, salida: lanzado.update(orden=orden, salida=salida) or 1)
    monkeypatch.setenv("POLFACE_CARPETA", str(tmp_path / "res"))
    monkeypatch.setenv("POLFACE_VIDEOS", str(videos))
    monkeypatch.setenv("POLFACE_CARAS", str(caras))
    monkeypatch.setenv("POLFACE_IDIOMA", "en")
    app = Path(__file__).parents[1] / "src" / "polface" / "dashboard.py"
    at = AppTest.from_file(str(app), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
    assert not at.button(key="an_iniciar").disabled
    assert any("1 videos and 7 people" in c.value for c in at.caption)
    at.number_input(key="an_cada").set_value(2.0)
    at.checkbox(key="an_reanudar").check()
    at.button(key="an_iniciar").click().run()
    o = lanzado["orden"]
    assert o[o.index("procesar") + 1] == str(videos.resolve())
    assert o[o.index("--caras") + 1] == str(caras.resolve())
    assert o[o.index("--cada-segundos") + 1] == "2.0" and "--reanudar" in o
    assert o[o.index("--lang") + 1] == "en" and lanzado["salida"] == tmp_path / "res"


def test_polface_sin_orden_abre_el_panel(monkeypatch):
    llamadas = []
    monkeypatch.setattr(cli, "cmd_dashboard", lambda a: llamadas.append(a) or 7)
    assert cli.main([]) == 7 and llamadas[-1].carpeta == "resultados"
    assert cli.main(["--lang", "en"]) == 7
    assert cli.main(["dashboard", "otra"]) == 7 and llamadas[-1].carpeta == "otra"


def test_lanzadores_sintaxis():
    import subprocess
    raiz = Path(__file__).parents[1]
    for f in ("PolFace.sh", "PolFace.command"):
        assert subprocess.run(["bash", "-n", str(raiz / f)]).returncode == 0
    bat = (raiz / "PolFace.bat").read_text()
    assert "-m polface dashboard" in bat and "pip install" in bat
