"""Tests del dashboard: capa de datos, gráficos y la app completa (AppTest)."""

import os
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import pytest

import datos_demo
from polface import dashboard_datos as dd


@pytest.fixture(scope="module")
def carpeta(tmp_path_factory):
    return datos_demo.crear(tmp_path_factory.mktemp("res"), n_videos=2, duracion=(60, 90))


def test_grupo_de():
    assert dd.grupo_de("TVE/n1.mp4") == "TVE"
    assert dd.grupo_de("n1.mp4") == "(sin carpeta)"
    assert dd.grupo_de("a\\b\\n1.mp4") == "a"


def test_cargar_prefiere_texto_si_esta_al_dia(carpeta):
    r = dd.cargar_resultados(carpeta)
    assert r.tiene_texto and r.aviso == ""
    assert {"grupo", "area_pct", "minuto"} <= set(r.det.columns)
    # si el CSV de texto es más antiguo que detecciones.csv, no se usa y se avisa
    f_txt, f_det = carpeta / "detecciones_texto.csv", carpeta / "detecciones.csv"
    t = f_det.stat().st_mtime
    os.utime(f_txt, (t - 100, t - 100))
    r2 = dd.cargar_resultados(carpeta)
    assert not r2.tiene_texto and "más antiguo" in r2.aviso
    os.utime(f_txt, (t + 100, t + 100))


def test_cargar_sin_resultados(tmp_path):
    with pytest.raises(FileNotFoundError):
        dd.cargar_resultados(tmp_path)


def test_cargar_separa_desconocidos(tmp_path):
    pd.DataFrame([{"video": "a/v.mp4", "duracion_seg": 10, "cada_segundos": 1.0}]).to_csv(
        tmp_path / "videos.csv", index=False)
    pd.DataFrame([
        {"video": "a/v.mp4", "fotograma": 0, "tiempo_seg": 0.0, "persona": "Ana", "distancia": .2,
         "area_relativa": .1},
        {"video": "a/v.mp4", "fotograma": 25, "tiempo_seg": 1.0, "persona": "Desconocido",
         "distancia": .7, "area_relativa": .1}]).to_csv(tmp_path / "detecciones.csv", index=False)
    r = dd.cargar_resultados(tmp_path)
    assert r.desconocidos == 1 and list(r.det["persona"]) == ["Ana"]


def test_filtrar_e_indicadores(carpeta):
    r = dd.cargar_resultados(carpeta)
    d = dd.filtrar(r.det, personas=["Persona A"], grupos=["Cadena 1"], distancia_max=0.3, area_min_pct=1.0)
    assert set(d["persona"]) == {"Persona A"} and set(d["grupo"]) == {"Cadena 1"}
    assert (d["distancia"] <= 0.3).all() and (d["area_pct"] >= 1.0).all()
    assert len(dd.filtrar(r.det)) == len(r.det)
    v = dd.videos_seleccionados(r.videos, grupos=["Cadena 1"])
    ind = dd.indicadores(d, v)
    assert ind["videos"] == 2 and ind["personas"] == 1 and ind["detecciones"] == len(d)


def test_tiempo_por_grupo(carpeta):
    r = dd.cargar_resultados(carpeta)
    t = dd.tiempo_por_grupo(r.det, r.videos)
    assert list(t.columns) == sorted(datos_demo.GRUPOS) and (t.to_numpy() >= 0).all()
    assert t.index[0] == t.sum(axis=1).idxmax()  # ordenado por tiempo total


def test_resumen_texto_por_persona(carpeta):
    r = dd.cargar_resultados(carpeta)
    t = dd.resumen_texto_por_persona(r.det)
    assert set(t["persona"]) == set(r.det["persona"])
    assert t["toxicidad_maxima"].max() > 0.9           # la frase «idiota» se detecta
    assert (t["n_apariciones_puntuadas"] <= r.det.groupby("persona").size().to_numpy()).all()
    assert dd.resumen_texto_por_persona(r.det[["persona"]]).empty


def crear_video(ruta, n=30):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    w = cv2.VideoWriter(str(ruta), cv2.VideoWriter_fourcc(*"MJPG"), 5, (160, 90))
    for _ in range(n):
        w.write(np.full((90, 160, 3), 128, np.uint8))
    w.release()


def test_localizar_video_y_fotograma(tmp_path):
    crear_video(tmp_path / "cadena" / "n1.avi")
    assert dd.localizar_video("cadena/n1.avi", tmp_path) == tmp_path / "cadena" / "n1.avi"
    assert dd.localizar_video("otra/n1.avi", tmp_path) == tmp_path / "cadena" / "n1.avi"
    assert dd.localizar_video("n2.avi", tmp_path) is None
    assert dd.localizar_video("n1.avi", None) is None
    img = dd.fotograma_con_cajas(tmp_path / "cadena" / "n1.avi", 3, [(20, 20, 50, 50, "Ana (0.2)")])
    assert img.shape == (90, 160, 3)
    assert img[20, 30].tolist() != [128, 128, 128]      # se ha dibujado el borde de la caja
    assert dd.fotograma_con_cajas(tmp_path / "cadena" / "n1.avi", 10_000, []) is None
    assert dd.fotograma_con_cajas(tmp_path / "no.avi", 0, []) is None


def test_graficos(carpeta):
    pytest.importorskip("plotly")
    from polface import analisis, graficos as gr
    r = dd.cargar_resultados(carpeta)
    resumen = analisis.resumen_por_persona(r.det, r.videos)
    figs = [
        gr.barras_tiempo(resumen),
        gr.mapa_calor(dd.tiempo_por_grupo(r.det, r.videos)),
        gr.mapa_calor(analisis.coapariciones(r.det), "fotogramas", diagonal_nula=True),
        gr.linea_tiempo(r.det[r.det["video"] == r.det["video"].iloc[0]], 1.5),
        gr.cajas_area(r.det),
    ]
    tt = dd.resumen_texto_por_persona(r.det)
    figs += [gr.barras_polaridad(tt), gr.barras_toxicidad(tt),
             gr.barras_idiomas(r.det["idioma_texto"].value_counts())]
    for f in figs:
        assert len(f.data) == 1 and f.layout.showlegend is False
        f.to_dict()  # serializable


def test_app_completa(carpeta, tmp_path, monkeypatch):
    pytest.importorskip("streamlit")
    pytest.importorskip("plotly")
    from streamlit.testing.v1 import AppTest
    crear_video(tmp_path / "vids" / "Cadena 1" / "noticias_01.mp4", n=2000)
    monkeypatch.setenv("POLFACE_CARPETA", str(carpeta))
    monkeypatch.setenv("POLFACE_VIDEOS", str(tmp_path / "vids"))
    app = Path(__file__).parents[1] / "src" / "polface" / "dashboard.py"
    at = AppTest.from_file(str(app), default_timeout=90).run()
    assert not at.exception, [e.value for e in at.exception]
    assert not at.error
    etiquetas = {m.label: m.value for m in at.metric}
    assert etiquetas["Vídeos analizados"] == "6" and etiquetas["Personas identificadas"] == "6"
    # un filtro de personas reduce las cifras sin romper la app
    sel = at.sidebar.multiselect[0]
    sel.set_value(sel.options[:2]).run()
    assert not at.exception
    assert {m.label: m.value for m in at.metric}["Personas identificadas"] == "2"
    # filtros imposibles: aviso en lugar de error
    sel.set_value([]).run()
    assert not at.exception and any("ninguna aparición" in w.value for w in at.warning)


def test_app_sin_resultados(tmp_path, monkeypatch):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv("POLFACE_CARPETA", str(tmp_path))
    app = Path(__file__).parents[1] / "src" / "polface" / "dashboard.py"
    at = AppTest.from_file(str(app), default_timeout=60).run()
    # sin resultados la app no falla: ofrece analizar y avisa de que faltan datos
    assert not at.exception and any("Todavía no hay resultados" in i.value for i in at.info)
    assert at.button(key="an_iniciar").disabled         # faltan carpetas de vídeos y caras


def test_i18n_mismas_claves_y_formato():
    from polface import i18n
    es, en = i18n.TEXTOS["es"], i18n.TEXTOS["en"]
    assert set(es) == set(en)
    assert i18n.miles(1234.5, "es", 1) == "1.234,5" and i18n.miles(1234.5, "en", 1) == "1,234.5"
    assert i18n.tr("en", "fot_pie", v="a", m=1.5, n=2).startswith("a · minute 1.50")
    assert i18n.tr("xx", "k_apar") == "Apariciones"  # respaldo al español


def test_app_en_ingles_con_selector(carpeta, tmp_path, monkeypatch):
    pytest.importorskip("streamlit")
    pytest.importorskip("plotly")
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv("POLFACE_CARPETA", str(carpeta))
    monkeypatch.setenv("POLFACE_VIDEOS", "")
    app = Path(__file__).parents[1] / "src" / "polface" / "dashboard.py"
    at = AppTest.from_file(str(app), default_timeout=90).run()
    assert at.radio(key="idioma_ui").value == "es"
    assert "Vídeos analizados" in {m.label for m in at.metric}
    at.radio(key="idioma_ui").set_value("en").run()
    assert not at.exception, [e.value for e in at.exception]
    etiquetas = {m.label: m.value for m in at.metric}
    assert etiquetas["Videos analysed"] == "6" and "Vídeos analizados" not in etiquetas
    assert any("funded by" in c.value for c in at.caption)
    assert [t.label for t in at.tabs][0] == "Visibility"
    # el filtro elegido se conserva al cambiar de idioma
    sel = at.sidebar.multiselect[0]
    sel.set_value(sel.options[:2]).run()
    at.radio(key="idioma_ui").set_value("es").run()
    assert {m.label: m.value for m in at.metric}["Personas identificadas"] == "2"


def test_app_idioma_inicial_por_entorno(carpeta, monkeypatch):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv("POLFACE_CARPETA", str(carpeta))
    monkeypatch.setenv("POLFACE_IDIOMA", "en")
    app = Path(__file__).parents[1] / "src" / "polface" / "dashboard.py"
    at = AppTest.from_file(str(app), default_timeout=90).run()
    assert not at.exception and at.radio(key="idioma_ui").value == "en"


def test_personas_referencia_y_completar(tmp_path):
    datos_demo.crear_caras(tmp_path)
    (tmp_path / "vacia").mkdir()                       # sin imágenes: no cuenta
    (tmp_path / "Persona A" / "notas.txt").write_text("x")
    ref = dd.personas_referencia(tmp_path)
    assert list(ref) == datos_demo.PERSONAS + [datos_demo.SIN_APARICIONES]
    assert all(f.suffix == ".png" for fotos in ref.values() for f in fotos)
    assert dd.personas_referencia(None) == {} and dd.personas_referencia(tmp_path / "no") == {}
    res = pd.DataFrame({"persona": ["Ana"], "n_fotogramas": [3], "n_videos": [1],
                        "tiempo_pantalla_seg": [3.0], "area_relativa_media": [.1]})
    out = dd.completar_resumen(res, ["Ana", "Beto"])
    assert out.loc[out.persona == "Beto", "tiempo_pantalla_seg"].item() == 0
    assert np.isnan(out.loc[out.persona == "Beto", "area_relativa_media"].item())
    assert dd.completar_resumen(res, ["Ana"]) is res


def test_filtrar_idiomas_conserva_apariciones_sin_texto():
    det = pd.DataFrame({"persona": list("abcd"), "grupo": "g", "video": "v", "distancia": 0.1,
                        "area_pct": 1.0, "idioma_texto": ["es", "ca", "", None]})
    assert list(dd.filtrar(det, idiomas=["es"])["persona"]) == ["a", "c", "d"]


def test_subcarpetas_y_lugares(tmp_path):
    (tmp_path / "b").mkdir(); (tmp_path / "a").mkdir(); (tmp_path / ".oculta").mkdir()
    assert dd.subcarpetas(tmp_path) == ["a", "b"] and dd.subcarpetas(tmp_path / "x") == []
    lugares = dd.lugares_rapidos()
    assert all(isinstance(n, str) and isinstance(r, str) for n, r in lugares)


def test_app_caras_definen_la_lista_de_personas(carpeta, tmp_path, monkeypatch):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    caras = datos_demo.crear_caras(tmp_path / "caras")
    monkeypatch.setenv("POLFACE_CARPETA", str(carpeta))
    monkeypatch.setenv("POLFACE_VIDEOS", "")
    monkeypatch.setenv("POLFACE_CARAS", str(caras))
    app = Path(__file__).parents[1] / "src" / "polface" / "dashboard.py"
    at = AppTest.from_file(str(app), default_timeout=90).run()
    assert not at.exception, [e.value for e in at.exception]
    pers = at.sidebar.multiselect[0]
    assert datos_demo.SIN_APARICIONES in pers.options          # ofrecida pero sin apariciones
    assert {m.label: m.value for m in at.metric}["Personas identificadas"] == "6"
    # solo algunas caras: el resto de personas detectadas se oculta
    import shutil
    shutil.rmtree(caras / "Persona E"); shutil.rmtree(caras / "Persona F")
    at.run()
    assert not at.exception
    assert "Persona E" not in at.sidebar.multiselect[0].options
    assert {m.label: m.value for m in at.metric}["Personas identificadas"] == "4"
    assert any("Persona E" in w.value for w in at.sidebar.warning)


def test_app_idiomas_por_defecto_solo_es_en(carpeta, monkeypatch):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv("POLFACE_CARPETA", str(carpeta))
    monkeypatch.setenv("POLFACE_VIDEOS", "")
    monkeypatch.delenv("POLFACE_CARAS", raising=False)
    app = Path(__file__).parents[1] / "src" / "polface" / "dashboard.py"
    at = AppTest.from_file(str(app), default_timeout=90).run()
    assert not at.exception
    idi = [m for m in at.sidebar.multiselect if m.label == "Idioma del texto asociado"][0]
    assert "ca" in idi.options and sorted(idi.value) == ["en", "es"]


def test_app_buscador_de_carpetas(carpeta, tmp_path, monkeypatch):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv("POLFACE_CARPETA", str(carpeta))
    monkeypatch.setenv("POLFACE_VIDEOS", "")
    (tmp_path / "hijo").mkdir()
    (tmp_path / "otro").mkdir()
    app = Path(__file__).parents[1] / "src" / "polface" / "dashboard.py"
    at = AppTest.from_file(str(app), default_timeout=90).run()
    at.session_state["carpeta_videos"] = str(tmp_path)
    at.run()
    at.sidebar.button(key="carpeta_videos_btn").click().run()        # abre el buscador
    assert not at.exception, [e.value for e in at.exception]
    nombres = [b.label for b in at.button if b.key and b.key.startswith("carpeta_videos_dlg_h")]
    assert nombres == ["📁 hijo", "📁 otro"]
    at.button(key="carpeta_videos_dlg_h0").click().run()             # entra en «hijo»
    # (AppTest repinta toda la app y no solo el diálogo; el resto del flujo se comprueba a mano)
    assert at.session_state["carpeta_videos_dlg"] == str(tmp_path / "hijo")
    assert not at.exception


def test_dispositivo_cuda_solo_si_hay_gpu(carpeta, monkeypatch):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    from polface import dashboard_datos as dd2
    monkeypatch.setenv("POLFACE_CARPETA", str(carpeta))
    app = Path(__file__).parents[1] / "src" / "polface" / "dashboard.py"
    monkeypatch.setattr(dd2, "cuda_disponible", lambda: False)
    at = AppTest.from_file(str(app), default_timeout=90).run()
    assert list(at.selectbox(key="an_disp").options) == ["auto", "cpu"]
    monkeypatch.setattr(dd2, "cuda_disponible", lambda: True)
    at = AppTest.from_file(str(app), default_timeout=90).run()
    assert list(at.selectbox(key="an_disp").options) == ["auto", "cpu", "cuda"]
