"""Panel interactivo (Streamlit) para explorar los resultados de PolFace.

Se lanza con ``polface dashboard <carpeta de resultados>``. No hace falta
ejecutar este fichero directamente.
"""

from __future__ import annotations

import os
import zlib
from pathlib import Path

import pandas as pd
import streamlit as st

from polface import FINANCIACION, FINANCIACION_EN, analisis
from polface import dashboard_datos as dd
from polface import graficos as gr
from polface import trabajo as tb
from polface.i18n import IDIOMA_POR_DEFECTO, IDIOMAS, miles, tr

ASSETS = Path(__file__).parent / "assets"

_def = os.environ.get("POLFACE_IDIOMA", IDIOMA_POR_DEFECTO)
st.session_state.setdefault("idioma_ui", _def if _def in IDIOMAS else IDIOMA_POR_DEFECTO)
L = st.session_state["idioma_ui"]


def T(clave: str, **kw) -> str:
    return tr(L, clave, **kw)


st.set_page_config(page_title=T("titulo_pagina"), layout="wide",
                   page_icon=str(ASSETS / "logo-polcom.png"))
FIN = FINANCIACION_EN if L == "en" else FINANCIACION

# ---------------------------------------------------------------- cabecera
# La publicidad de la financiación va en la parte superior, como exige la AEI.
cab1, cab2, cab3 = st.columns([5, 1, 2], vertical_alignment="center")
cab1.image(str(ASSETS / "financiacion.png"), width=520)
cab2.image(str(ASSETS / "logo-polcom.png"), width=110)
cab3.radio(T("idioma"), list(IDIOMAS), format_func=IDIOMAS.get, key="idioma_ui",
           horizontal=True)
st.title(T("titulo"))
st.caption(FIN)
st.info(T("aviso"), icon="ℹ️")

# ---------------------------------------------------------------- datos
def _clave(prefijo: str, opciones) -> str:
    """Clave de widget que cambia si cambian las opciones (evita selecciones obsoletas)."""
    return f"{prefijo}_{zlib.crc32('|'.join(map(str, opciones)).encode()) % 10**8}"


def _ir(clave: str, destino: str) -> None:
    st.session_state[clave + "_dlg"] = destino


def _subir(clave: str) -> None:
    st.session_state[clave + "_dlg"] = str(Path(st.session_state[clave + "_dlg"]).parent)


def _escribir_ruta(clave: str) -> None:
    ruta = Path(st.session_state[clave + "_dlg_txt"]).expanduser()
    if ruta.is_dir():
        st.session_state[clave + "_dlg"] = str(ruta)


def _usar(clave: str) -> None:
    st.session_state[clave] = st.session_state[clave + "_dlg"]
    st.session_state["_dlg_cerrar"] = True


def _dialogo_carpeta(clave: str) -> None:
    """Buscador de carpetas propio: se ve con el tamaño del navegador (sirve en pantallas 4K)."""
    dk = clave + "_dlg"
    if dk not in st.session_state:
        actual = Path(st.session_state.get(clave, "")).expanduser()
        st.session_state[dk] = str(actual.resolve() if actual.is_dir() else Path.home())
    st.session_state[clave + "_dlg_txt"] = st.session_state[dk]
    st.text_input(T("nav_ruta"), key=clave + "_dlg_txt", on_change=_escribir_ruta, args=(clave,),
                  label_visibility="collapsed")
    actual = Path(st.session_state[dk])
    lugares = [(T("nav_inicio"), str(Path.home()))] + dd.lugares_rapidos()
    cols = st.columns([1.3] + [1] * min(len(lugares), 5))
    cols[0].button(T("nav_subir"), key=clave + "_dlg_up", on_click=_subir, args=(clave,),
                   disabled=actual.parent == actual, width="stretch")
    for i, (nombre, ruta) in enumerate(lugares[:5]):
        cols[i + 1].button(nombre, key=f"{clave}_dlg_l{i}", on_click=_ir, args=(clave, ruta),
                           width="stretch")
    filtro = st.text_input(T("nav_filtro"), key=clave + "_dlg_filtro").strip().lower()
    hijos = [h for h in dd.subcarpetas(actual) if filtro in h.lower()]
    with st.container(height=380, border=True):
        if not hijos:
            st.caption(T("nav_vacia"))
        for i, h in enumerate(hijos[:400]):
            st.button(f"📁 {h}", key=f"{clave}_dlg_h{i}", on_click=_ir,
                      args=(clave, str(actual / h)), width="stretch")
        if len(hijos) > 400:
            st.caption(T("nav_mas", n=len(hijos) - 400))
    st.caption(f"{T('nav_actual')}: `{actual}`")
    st.button(T("nav_usar"), key=clave + "_dlg_use", on_click=_usar, args=(clave,),
              type="primary", width="stretch")
    if st.session_state.pop("_dlg_cerrar", False):
        st.rerun()


def selector_carpeta(etiqueta: str, clave: str, entorno: str, defecto: str, ayuda: str,
                     dialogo: str) -> str:
    """Campo de texto con botón «Examinar…» que abre el buscador de carpetas."""
    st.session_state.setdefault(clave, os.environ.get(entorno, defecto))
    st.text_input(etiqueta, key=clave, help=ayuda or None)
    if st.button(T("examinar"), key=clave + "_btn"):
        st.dialog(T(dialogo), width="large")(_dialogo_carpeta)(clave)
    return st.session_state[clave]


with st.sidebar:
    st.header(T("datos"))
    carpeta = selector_carpeta(T("carpeta_res"), "carpeta", "POLFACE_CARPETA", "resultados", "",
                               "dlg_res")
    carpeta_videos = selector_carpeta(T("carpeta_vid"), "carpeta_videos", "POLFACE_VIDEOS", "",
                                      T("carpeta_vid_ayuda"), "dlg_videos")
    carpeta_caras = selector_carpeta(T("carpeta_caras"), "carpeta_caras", "POLFACE_CARAS", "",
                                     T("carpeta_caras_ayuda"), "dlg_caras")
    if st.button(T("recargar")):
        st.cache_data.clear()


def _firma(c: str):
    ruta = Path(c)
    return tuple((f, (ruta / f).stat().st_mtime if (ruta / f).exists() else 0)
                 for f in ("videos.csv", "detecciones.csv", "detecciones_texto.csv"))


@st.cache_data(show_spinner=False)
def cargar(c: str, firma):
    return dd.cargar_resultados(Path(c))


@st.cache_data(show_spinner=False, ttl=60)
def n_videos_en(c: str) -> int:
    return dd.contar_videos(c)


# ---------------------------------------------------------------- analizar
def _bloque_estado(salida: Path) -> None:
    est = tb.estado(salida)
    antes = st.session_state.get("_an_antes", "ninguno")
    st.session_state["_an_antes"] = est.estado
    if antes == "corriendo" and est.estado != "corriendo":
        st.cache_data.clear()
        st.rerun()                      # al terminar, recarga todo para mostrar los resultados
    if est.estado == "corriendo":
        st.progress(est.hecho / est.total if est.total else 0.0,
                    text=f"{T('an_corriendo')} {T('an_paso_' + est.paso) if est.paso else ''}"
                         + (f" · {T('an_progreso', h=est.hecho, t=est.total)}" if est.total else ""))
        st.button(T("an_parar"), key="an_parar", on_click=tb.parar, args=(salida,))
    elif est.estado == "terminado":
        st.success(T("an_terminado"))
    elif est.estado == "error":
        st.error(T("an_error"))
    if est.estado != "ninguno":
        with st.expander(T("an_log"), expanded=est.estado == "error"):
            st.code(est.log or "…", language=None)


def panel_analisis(tiene_resultados: bool) -> None:
    salida = Path(carpeta).expanduser()
    est = tb.estado(salida)
    corriendo = est.estado == "corriendo"
    with st.expander(T("an_titulo"), expanded=(not tiene_resultados) or corriendo):
        st.caption(T("an_ayuda"))
        nv = n_videos_en(carpeta_videos) if carpeta_videos else 0
        personas_ref = dd.personas_referencia(Path(carpeta_caras).expanduser()) if carpeta_caras else {}
        if not nv:
            st.warning(T("an_falta_videos"))
        if not personas_ref:
            st.warning(T("an_falta_caras"))
        if nv and personas_ref:
            st.caption(T("an_resumen", v=nv, p=len(personas_ref)))
        c1, c2, c3, c4 = st.columns(4)
        cada = c1.number_input(T("an_cada"), 0.1, 60.0, 1.0, 0.5, key="an_cada",
                               help=T("an_cada_ayuda"))
        umbral = c2.number_input(T("an_umbral"), 0.2, 0.9, 0.5, 0.05, key="an_umbral",
                                 help=T("an_umbral_ayuda"))
        area = c3.number_input(T("an_area"), 0, 1_000_000, 6400, 400, key="an_area",
                               help=T("an_area_ayuda"))
        disp = c4.selectbox(T("an_disp"), ["auto", "cpu", "cuda"], key="an_disp")
        c5, c6 = st.columns([2, 1])
        reanudar = c5.checkbox(T("an_reanudar"), key="an_reanudar")
        transc = c5.checkbox(T("an_transc"), key="an_transc")
        modelo = c6.selectbox(T("an_modelo"), ["large-v3-turbo", "large-v3", "medium", "small"],
                              key="an_modelo", disabled=not transc)
        if tiene_resultados and not reanudar and not corriendo:
            st.caption(T("an_sobrescribe", c=salida))
        if st.button(T("an_iniciar"), type="primary", key="an_iniciar",
                     disabled=corriendo or not (nv and personas_ref)):
            tb.iniciar(tb.comando(
                str(Path(carpeta_videos).expanduser().resolve()),
                str(Path(carpeta_caras).expanduser().resolve()), str(salida.resolve()),
                idioma=L, cada_segundos=cada, umbral=umbral, area_minima=area,
                dispositivo=disp, reanudar=reanudar, transcribir=transc, modelo_whisper=modelo),
                salida)
            st.session_state["_an_antes"] = "corriendo"
            st.rerun()
        st.fragment(run_every=2 if corriendo else None)(_bloque_estado)(salida)


tiene_resultados = (Path(carpeta).expanduser() / "videos.csv").exists()
panel_analisis(tiene_resultados)
if not tiene_resultados:
    st.info(T("an_sin_resultados", c=carpeta))
    st.stop()

try:
    res = cargar(carpeta, _firma(carpeta))
except FileNotFoundError as e:
    st.error(str(e))
    st.stop()

if res.aviso:
    st.warning(res.aviso)
if res.det.empty:
    st.warning(T("sin_personas"))
    st.stop()

det_all, videos_all = res.det, res.videos
# La lista de personas depende de las caras ofrecidas al programa (carpeta de caras).
ref = dd.personas_referencia(Path(carpeta_caras)) if carpeta_caras else {}
if ref:
    fuera = sorted(set(det_all["persona"]) - set(ref))
    det_all = det_all[det_all["persona"].isin(ref)].reset_index(drop=True)
    st.sidebar.caption(T("caras_n", n=len(ref)))
    if fuera:
        st.sidebar.warning(T("personas_fuera", n=len(fuera), l=", ".join(fuera)))
elif carpeta_caras:
    st.sidebar.caption(T("caras_vacia", c=carpeta_caras))
if det_all.empty:
    st.warning(T("sin_personas"))
    st.stop()
detectadas = det_all.groupby("persona").size().sort_values(ascending=False).index.tolist()
orden_personas = detectadas + sorted(set(ref) - set(detectadas))

# ---------------------------------------------------------------- filtros
with st.sidebar:
    st.header(T("filtros"))
    personas = st.multiselect(T("personas"), orden_personas, default=orden_personas,
                              key=_clave("f_personas", orden_personas))
    grupos_op = sorted(videos_all["grupo"].unique())
    grupos = st.multiselect(T("grupo"), grupos_op, default=grupos_op,
                           key=_clave("f_grupos", grupos_op)) \
        if len(grupos_op) > 1 else None
    videos_sel = None
    if st.checkbox(T("elegir_videos"), key="f_elegir"):
        op = sorted(dd.videos_seleccionados(videos_all, grupos)["video"])
        videos_sel = st.multiselect(T("videos"), op, default=op[:1],
                                    key=_clave("f_videos", op))
    dmax = float(round(det_all["distancia"].max(), 2))
    dist_max = st.slider(
        T("dist_max"), 0.0, max(dmax, 0.01), max(dmax, 0.01), 0.01, key="f_dist",
        help=T("dist_max_ayuda"))
    area_max = float(round(det_all["area_pct"].max(), 1))
    area_min = st.slider(T("area_min"), 0.0, max(area_max, 0.1), 0.0, 0.1, key="f_area")
    idiomas = None
    if res.tiene_texto and "idioma_texto" in det_all.columns:
        op_idioma = sorted(x for x in det_all["idioma_texto"].dropna().unique() if x)
        if op_idioma:
            st.subheader(T("h_texto_filtros"))
            por_defecto = [x for x in ("es", "en") if x in op_idioma] or op_idioma
            idiomas = st.multiselect(T("idioma_texto"), op_idioma, default=por_defecto,
                                     key=_clave("f_idiomas", op_idioma),
                                     help=T("idioma_texto_ayuda"))
            if set(idiomas) == set(op_idioma):
                idiomas = None  # sin filtrar

det = dd.filtrar(det_all, personas, grupos, videos_sel, dist_max, area_min)
det_txt = dd.filtrar(det, idiomas=idiomas)   # el idioma solo afecta a la pestaña Texto
vids = dd.videos_seleccionados(videos_all, grupos, videos_sel)
if det.empty:
    st.warning(T("sin_apariciones"))
    st.stop()

resumen = dd.completar_resumen(analisis.resumen_por_persona(det, vids), personas)
ind = dd.indicadores(det, vids)
k1, k2, k3, k4 = st.columns(4)
k1.metric(T("k_videos"), miles(ind["videos"], L))
k2.metric(T("k_horas"), miles(ind["horas_video"], L, 1))
k3.metric(T("k_personas"), ind["personas"])
k4.metric(T("k_apar"), miles(ind["detecciones"], L))
if res.desconocidos:
    st.caption(T("desconocidos", n=miles(res.desconocidos, L)))

# ---------------------------------------------------------------- pestañas
t_vis, t_grp, t_lin, t_area, t_co, t_txt, t_fot, t_dat = st.tabs([
    T("tab_vis"), T("tab_grp"), T("tab_lin"), T("tab_area"), T("tab_co"), T("tab_txt"),
    T("tab_fot"), T("tab_dat")])

with t_vis:
    st.subheader(T("t_tiempo"))
    st.plotly_chart(gr.barras_tiempo(resumen, L), width="stretch",
                    config={"displayModeBar": False})
    st.dataframe(
        resumen.rename(columns={
            "persona": T("c_persona"), "n_fotogramas": T("c_fotogramas"),
            "n_videos": T("c_videos"), "tiempo_pantalla_seg": T("c_segundos"),
            "area_relativa_media": T("c_area_media"), "area_relativa_mediana": T("c_area_mediana"),
            "distancia_media": T("c_dist_media")}),
        hide_index=True, width="stretch")

with t_grp:
    modo = st.radio(T("comparar"), ["grupo", "video"], horizontal=True, key="modo",
                    format_func=lambda m: T("modo_" + m))
    if modo == "grupo":
        tabla = dd.tiempo_por_grupo(det, vids)
        if tabla.shape[1] < 2:
            st.info(T("un_grupo"))
    else:
        pv = analisis.resumen_por_video(det, vids)
        top = pv.groupby("video")["tiempo_pantalla_seg"].sum().nlargest(30).index
        tabla = (pv[pv["video"].isin(top)]
                 .pivot_table(index="persona", columns="video", values="tiempo_pantalla_seg",
                              aggfunc="sum", fill_value=0) / 60)
        if len(pv["video"].unique()) > 30:
            st.caption(T("top30"))
    if tabla.empty:
        st.info(T("sin_datos"))
    else:
        st.plotly_chart(gr.mapa_calor(tabla, T("unidad_min")), width="stretch",
                        config={"displayModeBar": False})

with t_lin:
    con_dets = sorted(det["video"].unique())
    v = st.selectbox(T("video"), con_dets, key="lin_video")
    d_v = det[det["video"] == v]
    dur = vids.loc[vids["video"] == v, "duracion_seg"]
    dur_min = float(dur.iloc[0]) / 60 if len(dur) and pd.notna(dur.iloc[0]) else None
    st.plotly_chart(gr.linea_tiempo(d_v, dur_min, L), width="stretch",
                    config={"displayModeBar": False})
    st.caption(T("nota_linea"))

with t_area:
    st.plotly_chart(gr.cajas_area(det, L), width="stretch",
                    config={"displayModeBar": False})
    st.caption(T("nota_area"))

with t_co:
    co = analisis.coapariciones(det)
    if co.empty or co.shape[0] < 2:
        st.info(T("necesita_mas"))
    else:
        st.plotly_chart(gr.mapa_calor(co, T("unidad_fotogramas"), diagonal_nula=True,
                                      alto=max(260, 40 * len(co))),
                        width="stretch", config={"displayModeBar": False})
        st.caption(T("nota_co"))

with t_txt:
    if not res.tiene_texto:
        st.info(T("sin_texto"))
    else:
        st.warning(T("aviso_texto"))
        tt = dd.resumen_texto_por_persona(det_txt)
        col_a, col_b = st.columns(2)
        if tt["polaridad_media"].notna().any():
            col_a.markdown(f"**{T('h_polaridad')}**")
            col_a.plotly_chart(gr.barras_polaridad(tt, L), width="stretch",
                               config={"displayModeBar": False})
        if tt["toxicidad_media"].notna().any():
            col_b.markdown(f"**{T('h_toxicidad')}**")
            col_b.plotly_chart(gr.barras_toxicidad(tt, L), width="stretch",
                               config={"displayModeBar": False})
        if tt[["polaridad_media", "toxicidad_media"]].isna().all().all():
            st.info(T("sin_puntuar"))
        if "idioma_texto" in det.columns:
            conteo = det.loc[det["texto"].fillna("") != "", "idioma_texto"].replace("", T("desconocido_idioma")) \
                .value_counts()
            if len(conteo):
                st.markdown(f"**{T('h_idiomas')}**")
                st.caption(T("nota_idiomas_texto"))
                st.plotly_chart(gr.barras_idiomas(conteo, L), width="stretch",
                                config={"displayModeBar": False})
        if "tox_toxicity" in det_txt.columns:
            st.markdown(f"**{T('h_contextos')}**")
            umbral_tox = st.slider(T("tox_min"), 0.0, 1.0, 0.5, 0.05, key="tox_min")
            ctx = (det_txt[det_txt["tox_toxicity"] >= umbral_tox]
                   .sort_values("tox_toxicity", ascending=False)
                   [["persona", "video", "minuto", "tox_toxicity", "texto"]].head(50))
            st.dataframe(ctx.rename(columns={"persona": T("c_persona"), "video": T("c_video"),
                                             "minuto": T("c_minuto"), "tox_toxicity": T("c_tox"),
                                             "texto": T("c_texto")}),
                         hide_index=True, width="stretch")

with t_fot:
    if not carpeta_videos:
        st.info(T("fot_sin_carpeta"))
    else:
        v = st.selectbox(T("video"), sorted(det["video"].unique()), key="fot_video")
        ruta = dd.localizar_video(v, Path(carpeta_videos))
        d_v = det[det["video"] == v]
        persona = st.selectbox(T("persona"), sorted(d_v["persona"].unique()), key="fot_persona")
        apar = d_v[d_v["persona"] == persona].sort_values("tiempo_seg").drop_duplicates("fotograma")
        n = len(apar)
        i = st.slider(T("aparicion"), 1, n, 1, key="fot_i") if n > 1 else 1
        fila = apar.iloc[i - 1]
        if ruta is None:
            st.error(T("fot_no_video", v=v, c=carpeta_videos))
        else:
            mismas = d_v[d_v["fotograma"] == fila["fotograma"]]
            cajas = [(r.x, r.y, r.ancho, r.alto, f"{r.persona} ({r.distancia:.2f})")
                     for r in mismas.itertuples()]
            img = dd.fotograma_con_cajas(ruta, int(fila["fotograma"]), cajas)
            if img is None:
                st.error(T("fot_no_leer"))
            else:
                st.image(img, caption=T("fot_pie", v=v, m=fila["minuto"], n=len(cajas)),
                         width=min(920, img.shape[1]))
                if res.tiene_texto and isinstance(fila.get("texto"), str) and fila["texto"]:
                    st.markdown(T("fot_texto", t=fila["texto"]))

with t_dat:
    st.markdown(T("dat_intro"))
    d1, d2 = st.columns(2)
    d1.download_button(T("dl_apar"), det.to_csv(index=False).encode("utf-8"),
                       "apariciones_filtradas.csv", "text/csv")
    d2.download_button(T("dl_resumen"), resumen.to_csv(index=False).encode("utf-8"),
                       "resumen_por_persona.csv", "text/csv")
    st.dataframe(det.drop(columns=["grupo", "area_pct", "minuto"], errors="ignore").head(1000),
                 hide_index=True, width="stretch")
    if len(det) > 1000:
        st.caption(T("primeras_filas"))

st.divider()
st.caption(FIN)
