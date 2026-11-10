"""Tests de sentimiento y toxicidad con puntuadores simulados (sin descargar modelos)."""

import numpy as np
import pandas as pd
import pytest

from polface import cli
from polface.texto import (IDIOMAS_SENTIMIENTO_LXYUAN, IDIOMAS_TOXICIDAD_DETOXIFY,
                           normalizar_sentimiento, puntuar_transcripcion)
from polface.transcripcion import cargar_transcripciones, transcribir_video, unir_texto


class SentFalso:
    prefijo = "sent"
    idiomas = IDIOMAS_SENTIMIENTO_LXYUAN

    def __init__(self):
        self.recibidos = []

    def puntuar(self, textos):
        self.recibidos.extend(textos)
        n = len(textos)
        return pd.DataFrame({"sent_neg": [0.1] * n, "sent_neu": [0.2] * n,
                             "sent_pos": [0.7] * n, "sent_polaridad": [0.6] * n})


class ToxFalso:
    prefijo = "tox"
    idiomas = IDIOMAS_TOXICIDAD_DETOXIFY

    def puntuar(self, textos):
        return pd.DataFrame({"tox_toxicity": [0.9 if "idiota" in t else 0.01 for t in textos]})


def seg_multi():
    return pd.DataFrame([
        {"video": "v.mp4", "inicio": 0, "fin": 4, "texto": "Eres un idiota.", "idioma": "es"},
        {"video": "v.mp4", "inicio": 4, "fin": 8, "texto": "Gracias a todos.", "idioma": "es"},
        {"video": "v.mp4", "inicio": 8, "fin": 9, "texto": "", "idioma": "es"},
        {"video": "v.mp4", "inicio": 9, "fin": 12, "texto": "Moltes gràcies.", "idioma": "ca"},
        {"video": "v.mp4", "inicio": 12, "fin": 15, "texto": "ありがとうございます。", "idioma": "ja"},
    ])


def test_normalizar_etiquetas_con_nombre():
    r = normalizar_sentimiento([{"label": "positive", "score": 0.7},
                                {"label": "neutral", "score": 0.2},
                                {"label": "negative", "score": 0.1}])
    assert r == {"neg": 0.1, "neu": 0.2, "pos": 0.7}
    r = normalizar_sentimiento([{"label": "Neutral", "score": 0.5},
                                {"label": "Positive", "score": 0.3},
                                {"label": "Negative", "score": 0.2}])
    assert r["neg"] == 0.2 and r["pos"] == 0.3


def test_normalizar_etiquetas_label_n():
    r = normalizar_sentimiento([{"label": "LABEL_2", "score": 0.6},
                                {"label": "LABEL_0", "score": 0.3},
                                {"label": "LABEL_1", "score": 0.1}])
    assert r == {"neg": 0.3, "neu": 0.1, "pos": 0.6}


def test_idioma_no_soportado_queda_vacio_y_se_avisa():
    sent, tox = SentFalso(), ToxFalso()
    out, inf = puntuar_transcripcion(seg_multi(), [sent, tox])
    # el catalán no está soportado en ninguno; el japonés solo en sentimiento
    assert list(out["sent_ok"]) == [True, True, False, False, True]
    assert list(out["tox_ok"]) == [True, True, False, False, False]
    assert out.loc[3, "sent_pos"] != out.loc[3, "sent_pos"]  # NaN
    assert out.loc[0, "tox_toxicity"] == 0.9 and out.loc[1, "tox_toxicity"] == 0.01
    assert "Moltes gràcies." not in sent.recibidos
    assert inf.segmentos_con_texto == 4
    assert inf.idiomas_no_soportados["sent"] == {"ca": 1}
    assert inf.idiomas_no_soportados["tox"] == {"ca": 1, "ja": 1}


def test_forzar_idioma_puntua_todo_con_texto():
    out, _ = puntuar_transcripcion(seg_multi(), [SentFalso()], forzar_idioma=True)
    assert list(out["sent_ok"]) == [True, True, False, True, True]  # el vacío sigue sin puntuar


def test_idioma_desconocido_no_se_puntua():
    seg = seg_multi().drop(columns="idioma")
    out, inf = puntuar_transcripcion(seg, [SentFalso()])
    assert not out["sent_ok"].any()
    assert inf.idiomas_no_soportados["sent"] == {"desconocido": 4}


def test_unir_agrega_sentimiento_medio_y_toxicidad_maxima():
    out, _ = puntuar_transcripcion(seg_multi(), [SentFalso(), ToxFalso()])
    det = pd.DataFrame([{"video": "v.mp4", "tiempo_seg": 4.0, "persona": "Ana"},
                        {"video": "v.mp4", "tiempo_seg": 10.0, "persona": "Ana"}])
    r = unir_texto(det, {"v.mp4": out}, ventana=1.0)
    assert r.loc[0, "tox_toxicity"] == 0.9            # máximo de los dos segmentos tocados
    assert r.loc[0, "sent_pos"] == pytest.approx(0.7)  # media
    assert r.loc[0, "idioma_texto"] == "es"
    assert r.loc[1, "idioma_texto"] == "ca"
    assert np.isnan(r.loc[1, "sent_pos"])             # catalán: sin puntuar
    assert "sent_ok" not in r.columns and "tox_ok" not in r.columns


def test_cli_texto_de_extremo_a_extremo(tmp_path, monkeypatch, capsys):
    trans = tmp_path / "trans"
    trans.mkdir()
    seg_multi().to_csv(trans / "v.csv", index=False)
    pd.DataFrame(columns=["video", "inicio", "fin", "texto", "idioma"]).to_csv(trans / "vacio.csv", index=False)
    monkeypatch.setattr(cli, "crear_puntuadores", lambda *a, **k: [SentFalso(), ToxFalso()])
    salida = tmp_path / "txt"
    assert cli.main(["texto", str(trans), "--salida", str(salida)]) == 0
    out = capsys.readouterr().out
    assert "idioma no soportado" in out and "'ca': 1" in out
    res = pd.read_csv(salida / "v.csv")
    assert "sent_polaridad" in res.columns and "tox_toxicity" in res.columns
    assert (salida / "vacio.csv").exists()
    # sin tmp y reanudable
    assert not list(salida.glob("*.tmp"))
    assert cli.main(["texto", str(trans), "--salida", str(salida)]) == 0
    assert set(cargar_transcripciones(salida)) == {"v.mp4"}


def test_cli_texto_todo_desactivado(tmp_path):
    (tmp_path / "t").mkdir()
    assert cli.main(["texto", str(tmp_path / "t"), "--sentimiento", "no", "--toxicidad", "no"]) == 1
    assert cli.main(["texto", str(tmp_path / "no_existe")]) == 1


def test_idioma_manual_se_pasa_a_whisper(tmp_path):
    from types import SimpleNamespace

    class M:
        def transcribe(self, ruta, **kw):
            self.kw = kw
            return iter([SimpleNamespace(start=0, end=1, text="x", avg_logprob=0, no_speech_prob=0)]), \
                SimpleNamespace(duration=1.0)  # sin language: se usa el forzado
    m = M()
    df, _ = transcribir_video(tmp_path / "a.mp4", m, "a.mp4", idioma="fr")
    assert m.kw["language"] == "fr" and df.loc[0, "idioma"] == "fr"
