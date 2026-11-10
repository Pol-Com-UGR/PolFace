"""Línea de comandos / command line: ``polface galeria | analizar | transcribir | texto | unir | procesar | dashboard | demo | resumen``.

Idioma de los mensajes / message language: ``--lang es|en`` o la variable ``POLFACE_LANG``.
"""

from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from . import FINANCIACION, FINANCIACION_EN, __version__, analisis
from .galeria import Galeria, construir_galeria
from .i18n import IDIOMAS, fijar_idioma, idioma_actual, idioma_desde, m
from .transcripcion import (cargar_transcripciones, crear_modelo, nombre_csv,
                            transcribir_video, unir_texto)
from .texto import InformeTexto, crear_puntuadores, puntuar_transcripcion
from .video import analizar_video, listar_videos, nombre_video


def _aviso() -> str:
    return m("Herramienta para investigación. Identifica personas por reconocimiento facial: "
             "lee AVISO_DE_USO.md antes de usarla. Las cifras de tiempo en pantalla son "
             "estimaciones.",
             "Research tool. It identifies people through face recognition: read "
             "AVISO_DE_USO.en.md before using it. Screen-time figures are estimates.")


def _crear_detector(args):
    from .deteccion import DetectorInsightFace
    return DetectorInsightFace(args.modelo, args.dispositivo, args.tam_deteccion)


def cmd_galeria(args) -> int:
    detector = _crear_detector(args)
    galeria = construir_galeria(Path(args.referencias), detector)
    salida = Path(args.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    galeria.guardar(salida)
    print(m("\nGalería guardada en {s}: {p} personas, {i} imágenes.",
            "\nGallery saved to {s}: {p} people, {i} images.",
            s=salida, p=len(galeria.personas), i=len(galeria.nombres)))
    print(m("ATENCIÓN: este fichero contiene embeddings faciales (datos biométricos). "
            "No lo subas a ningún repositorio ni lo compartas.",
            "WARNING: this file contains face embeddings (biometric data). "
            "Do not upload it to any repository or share it."))
    return 0


def cmd_analizar(args) -> int:
    galeria = Galeria.cargar(Path(args.galeria))
    detector = _crear_detector(args)
    return _analizar(args, galeria, detector)


def _analizar(args, galeria, detector) -> int:
    entrada = Path(args.entrada)
    videos = listar_videos(entrada)
    if not videos:
        print(m("No se encontraron vídeos.", "No videos found."), file=sys.stderr)
        return 1
    base = entrada if entrada.is_dir() else None
    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)
    f_det, f_vid = salida / "detecciones.csv", salida / "videos.csv"

    ya_hechos = set()
    if args.reanudar and f_vid.exists():
        ya_hechos = set(pd.read_csv(f_vid)["video"])
    elif not args.reanudar:
        f_det.unlink(missing_ok=True)
        f_vid.unlink(missing_ok=True)

    print(m("{n} vídeos · dispositivo: {d} · umbral: {u} · un fotograma cada {c} s",
            "{n} videos · device: {d} · threshold: {u} · one frame every {c} s",
            n=len(videos), d=detector.dispositivo, u=args.umbral, c=args.cada_segundos))
    for i, v in enumerate(videos, 1):
        nombre = nombre_video(v, base)
        if nombre in ya_hechos:
            print(m("[{i}/{n}] {v}: ya procesado, se omite",
                    "[{i}/{n}] {v}: already processed, skipped", i=i, n=len(videos), v=nombre))
            continue
        print(f"[{i}/{len(videos)}] {nombre}", flush=True)
        try:
            info, dets = analizar_video(
                v, detector, galeria, args.cada_segundos, args.umbral,
                args.area_minima, args.guardar_desconocidos, base)
        except RuntimeError as e:
            print(f"   [error] {e}", file=sys.stderr)
            continue
        _anadir_csv(f_det, dets)
        _anadir_csv(f_vid, [asdict(info)])
        print(m("   {f} fotogramas, {d} detecciones", "   {f} frames, {d} detections",
                f=info.fotogramas_muestreados, d=len(dets)))
    print(m("\nListo. Resultados en {s}. Siguiente paso: polface resumen {s}",
            "\nDone. Results in {s}. Next step: polface resumen {s}", s=salida))
    return 0


def _anadir_csv(ruta: Path, filas) -> None:
    if not filas:
        return
    nuevo = not ruta.exists()
    with open(ruta, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
        if nuevo:
            w.writeheader()
        w.writerows(filas)


def _no_encuentro(ruta: Path) -> str:
    return m("No encuentro {r}. ¿Has ejecutado 'polface analizar'?",
             "Cannot find {r}. Did you run 'polface analizar'?", r=ruta)


def cmd_resumen(args) -> int:
    carpeta = Path(args.carpeta)
    f_det, f_vid = carpeta / "detecciones.csv", carpeta / "videos.csv"
    if not f_vid.exists():
        print(_no_encuentro(f_vid), file=sys.stderr)
        return 1
    videos = pd.read_csv(f_vid)
    det = pd.read_csv(f_det) if f_det.exists() else pd.DataFrame(
        columns=["video", "fotograma", "persona", "area_relativa", "distancia"])
    det = det[det["persona"] != "Desconocido"]
    por_persona = analisis.resumen_por_persona(det, videos)
    por_video = analisis.resumen_por_video(det, videos)
    por_persona.to_csv(carpeta / "resumen_por_persona.csv", index=False)
    por_video.to_csv(carpeta / "resumen_por_video.csv", index=False)
    co = analisis.coapariciones(det)
    if not co.empty:
        co.to_csv(carpeta / "coapariciones.csv")
    print(por_persona.to_string(index=False) if not por_persona.empty
          else m("No hay detecciones de personas de la galería.",
                 "No detections of people from the gallery."))
    print(m("\nTablas guardadas en {c}", "\nTables saved to {c}", c=carpeta))
    print(m("Recuerda: el tiempo en pantalla es una estimación (fotogramas muestreados).",
            "Remember: screen time is an estimate (sampled frames)."))
    return 0


def cmd_transcribir(args) -> int:
    entrada = Path(args.entrada)
    videos = listar_videos(entrada)
    if not videos:
        print(m("No se encontraron vídeos.", "No videos found."), file=sys.stderr)
        return 1
    base = entrada if entrada.is_dir() else None
    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)
    pendientes = []
    for v in videos:
        nombre = nombre_video(v, base)
        destino = salida / nombre_csv(nombre)
        if destino.exists() and not args.rehacer:
            continue
        pendientes.append((v, nombre, destino))
    print(m("{n} vídeos, {p} pendientes", "{n} videos, {p} pending",
            n=len(videos), p=len(pendientes)))
    if not pendientes:
        return 0
    print(m("Cargando modelo {x} ...", "Loading model {x} ...", x=args.modelo), flush=True)
    modelo = crear_modelo(args.modelo, args.dispositivo)
    print(m("Modelo cargado ({d}).", "Model loaded ({d}).", d=modelo.dispositivo))
    errores = []
    for i, (v, nombre, destino) in enumerate(pendientes, 1):
        print(f"[{i}/{len(pendientes)}] {nombre}", flush=True)
        t0 = time.time()
        try:
            seg, duracion = transcribir_video(
                v, modelo, nombre, args.idioma, log=print if args.mostrar else None)
        except Exception as e:  # un vídeo defectuoso no debe parar el lote
            errores.append({"video": nombre, "error": str(e)})
            print(f"   [error] {e}", file=sys.stderr)
            continue
        tmp = destino.with_suffix(".csv.tmp")
        seg.to_csv(tmp, index=False)
        tmp.replace(destino)  # escritura atómica: un CSV existente siempre está completo
        dt = max(time.time() - t0, 1e-6)
        print(m("   {n} segmentos · {a:.1f} min de audio en {t:.1f} min ({x:.0f}x tiempo real)",
                "   {n} segments · {a:.1f} min of audio in {t:.1f} min ({x:.0f}x real time)",
                n=len(seg), a=duracion / 60, t=dt / 60, x=duracion / dt))
    if errores:
        pd.DataFrame(errores).to_csv(salida / "errores_transcripcion.csv", index=False)
    print(m("\nListo. {e} errores. Siguiente paso: "
            "polface unir <carpeta de resultados> --transcripciones {s}",
            "\nDone. {e} errors. Next step: "
            "polface unir <results folder> --transcripciones {s}", e=len(errores), s=salida))
    return 0


def cmd_texto(args) -> int:
    origen = Path(args.transcripciones)
    if not origen.is_dir():
        print(m("No existe la carpeta de transcripciones: {o}",
                "The transcripts folder does not exist: {o}", o=origen), file=sys.stderr)
        return 1
    if args.sentimiento == "no" and args.toxicidad == "no":
        print(m("Has desactivado el sentimiento y la toxicidad: no hay nada que calcular.",
                "You disabled both sentiment and toxicity: there is nothing to compute."),
              file=sys.stderr)
        return 1
    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)
    pendientes = [f for f in sorted(origen.glob("*.csv"))
                  if args.rehacer or not (salida / f.name).exists()]
    print(m("{n} transcripciones, {p} pendientes", "{n} transcripts, {p} pending",
            n=len(list(origen.glob("*.csv"))), p=len(pendientes)))
    if not pendientes:
        return 0
    puntuadores = crear_puntuadores(args.sentimiento, args.toxicidad, args.dispositivo, args.lote)
    total = InformeTexto()
    for i, f in enumerate(pendientes, 1):
        seg = pd.read_csv(f)
        print(f"[{i}/{len(pendientes)}] {f.name}", flush=True)
        if seg.empty:
            seg.to_csv(salida / f.name, index=False)
            continue
        seg, inf = puntuar_transcripcion(seg, puntuadores, args.forzar_idioma)
        total.sumar(inf)
        tmp = (salida / f.name).with_suffix(".csv.tmp")
        seg.to_csv(tmp, index=False)
        tmp.replace(salida / f.name)
    print(m("\n{n} segmentos con texto. Puntuados: {p}",
            "\n{n} segments with text. Scored: {p}", n=total.segmentos_con_texto,
            p=total.puntuados))
    for prefijo, langs in total.idiomas_no_soportados.items():
        print(m("[aviso] sin puntuar por idioma no soportado ({x}): {l}. "
                "Esos segmentos quedan vacíos; --forzar-idioma los puntúa sin validación.",
                "[warning] not scored because the language is unsupported ({x}): {l}. "
                "Those segments are left empty; --forzar-idioma scores them without validation.",
                x=prefijo, l=langs))
    print(m("Guardado en {s}. Siguiente paso: polface unir <resultados> --transcripciones {s}",
            "Saved to {s}. Next step: polface unir <results> --transcripciones {s}", s=salida))
    print(m("Recuerda: son puntuaciones automáticas y aproximadas; valídalas con una muestra "
            "codificada a mano (ver AVISO_DE_USO.md).",
            "Remember: these are automatic, approximate scores; validate them with a "
            "hand-coded sample (see AVISO_DE_USO.en.md)."))
    return 0


def cmd_unir(args) -> int:
    carpeta = Path(args.carpeta)
    f_det = carpeta / "detecciones.csv"
    if not f_det.exists():
        print(_no_encuentro(f_det), file=sys.stderr)
        return 1
    det = pd.read_csv(f_det)
    trans = cargar_transcripciones(Path(args.transcripciones))
    sin_trans = sorted(set(det["video"]) - set(trans))
    out = unir_texto(det, trans, args.ventana_segundos)
    destino = carpeta / "detecciones_texto.csv"
    out.to_csv(destino, index=False)
    con_texto = (out["texto"].str.len() > 0).mean() * 100 if len(out) else 0.0
    print(m("{n} apariciones · {c:.1f} % con texto en ±{w} s",
            "{n} appearances · {c:.1f} % with text within ±{w} s",
            n=len(out), c=con_texto, w=args.ventana_segundos))
    if sin_trans:
        print(m("[aviso] {n} vídeos sin transcripción (p. ej. {e})",
                "[warning] {n} videos without a transcript (e.g. {e})",
                n=len(sin_trans), e=sin_trans[0]))
    print(m("Guardado en {d}", "Saved to {d}", d=destino))
    print(m("Recuerda: el texto es el contexto sonoro de la aparición, no necesariamente "
            "lo que dice la persona (no hay separación de hablantes).",
            "Remember: the text is the background audio of the appearance, not necessarily "
            "what the person says (speakers are not separated)."))
    return 0


def _paso(nombre: str, es: str, en: str) -> None:
    print(f"## {nombre}\n" + m(es, en), flush=True)


def cmd_procesar(args) -> int:
    """Todo en uno: galería → análisis facial → descriptivos (→ texto, opcional)."""
    caras, salida = Path(args.caras), Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)
    (salida / ".procesar_ok").unlink(missing_ok=True)
    detector = _crear_detector(args)
    _paso("galeria", "Creando la galería de caras...", "Building the faces gallery...")
    galeria = construir_galeria(caras, detector)
    galeria.guardar(salida / "galeria.npz")
    print(m("{p} personas, {i} imágenes.", "{p} people, {i} images.",
            p=len(galeria.personas), i=len(galeria.nombres)), flush=True)
    _paso("analizar", "Buscando a las personas en los vídeos...",
          "Looking for the people in the videos...")
    args.entrada = args.videos
    args.guardar_desconocidos = False
    codigo = _analizar(args, galeria, detector)
    if codigo != 0:
        return codigo
    _paso("resumen", "Calculando descriptivos...", "Computing descriptive statistics...")
    codigo = cmd_resumen(argparse.Namespace(carpeta=str(salida)))
    if codigo == 0 and args.transcribir:
        codigo = _procesar_texto(args, salida)
    if codigo == 0:
        (salida / ".procesar_ok").write_text("ok", encoding="utf-8")
    return codigo


def _procesar_texto(args, salida: Path) -> int:
    """Whisper + sentimiento/toxicidad + unión. Si falla, los resultados faciales se conservan."""
    trans, texto = salida / "transcripciones", salida / "texto_analizado"
    try:
        _paso("transcribir", "Transcribiendo con Whisper...", "Transcribing with Whisper...")
        cmd_transcribir(argparse.Namespace(
            entrada=args.videos, salida=str(trans), modelo=args.modelo_whisper,
            dispositivo=args.dispositivo, idioma="auto", rehacer=False, mostrar=False))
        _paso("texto", "Calculando sentimiento y toxicidad...",
              "Computing sentiment and toxicity...")
        cmd_texto(argparse.Namespace(
            transcripciones=str(trans), salida=str(texto), sentimiento="lxyuan",
            toxicidad="detoxify", forzar_idioma=False, dispositivo=args.dispositivo, lote=32,
            rehacer=False))
        _paso("unir", "Uniendo el texto con las apariciones...",
              "Joining the text with the appearances...")
        return cmd_unir(argparse.Namespace(carpeta=str(salida), transcripciones=str(texto),
                                           ventana_segundos=5.0))
    except (SystemExit, Exception) as e:  # noqa: BLE001
        print(m("[aviso] el texto no se pudo calcular ({e}); los resultados faciales se "
                "conservan.", "[warning] the text could not be computed ({e}); the face "
                "results are kept.", e=e), file=sys.stderr, flush=True)
        return 0


def cmd_dashboard(args) -> int:
    try:
        import plotly  # noqa: F401
        import streamlit  # noqa: F401
    except ImportError:
        print(m("Falta instalar el dashboard:\n  pip install 'polface[dashboard]'",
                "The dashboard is not installed:\n  pip install 'polface[dashboard]'"),
              file=sys.stderr)
        return 1
    carpeta = Path(args.carpeta)
    app = Path(__file__).with_name("dashboard.py")
    env = dict(os.environ, POLFACE_CARPETA=str(carpeta.resolve()),
               POLFACE_VIDEOS=str(Path(args.videos).resolve()) if args.videos else "",
               POLFACE_IDIOMA=args.idioma or idioma_actual(),
               POLFACE_CARAS=str(Path(args.caras).resolve()) if getattr(args, "caras", None) else "")
    orden = [sys.executable, "-m", "streamlit", "run", str(app),
             "--server.port", str(args.puerto), "--browser.gatherUsageStats", "false",
             "--theme.primaryColor", "#2a78d6"]
    if args.sin_navegador:
        orden += ["--server.headless", "true"]
    print(m("Abriendo el panel en http://localhost:{p} (Ctrl+C para cerrarlo)",
            "Opening the dashboard at http://localhost:{p} (Ctrl+C to close it)",
            p=args.puerto))
    try:
        return subprocess.call(orden, env=env)
    except KeyboardInterrupt:
        return 0


def cmd_demo(args) -> int:
    from .demo import crear
    carpeta = Path(args.carpeta)
    crear(carpeta, n_videos=args.videos_por_grupo)
    print(m("Datos de ejemplo SINTÉTICOS creados en {c} (personas y textos inventados).",
            "SYNTHETIC sample data created in {c} (invented people and texts).", c=carpeta))
    if args.abrir:
        return cmd_dashboard(argparse.Namespace(
            carpeta=str(carpeta), videos=None, caras=str(carpeta / "referencias"), idioma=None,
            puerto=args.puerto, sin_navegador=False))
    print(m("Ábrelos con:  polface dashboard {c}",
            "Open them with:  polface dashboard {c}", c=carpeta))
    return 0


def construir_parser() -> argparse.ArgumentParser:
    """Construye el parser en el idioma actual (ver ``main``)."""
    p = argparse.ArgumentParser(
        prog="polface", description=_aviso(),
        epilog=FINANCIACION_EN if idioma_actual() == "en" else FINANCIACION,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--version", action="version", version=f"polface {__version__}")
    p.add_argument("--lang", choices=list(IDIOMAS), default=None,
                   help=m("idioma de los mensajes (o variable POLFACE_LANG; por defecto es)",
                          "language of the messages (or POLFACE_LANG variable; default es)"))
    sub = p.add_subparsers(dest="orden", required=True)

    def comunes(sp):
        sp.add_argument("--modelo", default="buffalo_l",
                        help=m("modelo InsightFace", "InsightFace model"))
        sp.add_argument("--dispositivo", default="auto", choices=["auto", "cpu", "cuda"],
                        help=m("dónde ejecutar el modelo", "where to run the model"))
        sp.add_argument("--tam-deteccion", type=int, default=640,
                        help=m("tamaño de entrada del detector (por defecto 640)",
                               "detector input size (default 640)"))

    g = sub.add_parser("galeria", help=m(
        "crear la galería de referencia desde una carpeta de fotos",
        "create the reference gallery from a folder of photos"))
    g.add_argument("referencias", help=m("carpeta con una subcarpeta por persona",
                                         "folder with one subfolder per person"))
    g.add_argument("--salida", default="galeria.npz")
    comunes(g)
    g.set_defaults(func=cmd_galeria)

    a = sub.add_parser("analizar", help=m("localizar personas en vídeos",
                                          "locate people in videos"))
    a.add_argument("entrada", help=m("vídeo o carpeta de vídeos", "video or folder of videos"))
    a.add_argument("--galeria", default="galeria.npz")
    a.add_argument("--salida", default="resultados")
    a.add_argument("--cada-segundos", type=float, default=1.0,
                   help=m("un fotograma cada N segundos (por defecto 1)",
                          "one frame every N seconds (default 1)"))
    a.add_argument("--umbral", type=float, default=0.5,
                   help=m("distancia coseno máxima para aceptar una identificación "
                          "(menor = más estricto; por defecto 0.5). Calíbralo con tus datos.",
                          "maximum cosine distance to accept an identification "
                          "(lower = stricter; default 0.5). Calibrate it with your data."))
    a.add_argument("--area-minima", type=int, default=0,
                   help=m("descarta caras con menos píxeles de área (p. ej. 6400 = 80x80)",
                          "discard faces with fewer pixels of area (e.g. 6400 = 80x80)"))
    a.add_argument("--guardar-desconocidos", action="store_true",
                   help=m("guarda también las caras no identificadas (sin nombre)",
                          "also save unidentified faces (without a name)"))
    a.add_argument("--reanudar", action="store_true",
                   help=m("omite los vídeos ya procesados en la carpeta de salida",
                          "skip videos already processed in the output folder"))
    comunes(a)
    a.set_defaults(func=cmd_analizar)

    t = sub.add_parser("transcribir", help=m("transcribir vídeos con Whisper",
                                             "transcribe videos with Whisper"))
    t.add_argument("entrada", help=m("vídeo o carpeta de vídeos", "video or folder of videos"))
    t.add_argument("--salida", default="transcripciones")
    t.add_argument("--modelo", default="large-v3",
                   help=m("modelo Whisper (large-v3, large-v3-turbo, medium, small...)",
                          "Whisper model (large-v3, large-v3-turbo, medium, small...)"))
    t.add_argument("--dispositivo", default="auto", choices=["auto", "cpu", "cuda"])
    t.add_argument("--idioma", default="auto",
                   help=m("código de idioma (es, en, fr...) o 'auto' para detectarlo en cada "
                          "vídeo (por defecto auto)",
                          "language code (es, en, fr...) or 'auto' to detect it in each "
                          "video (default auto)"))
    t.add_argument("--rehacer", action="store_true",
                   help=m("vuelve a transcribir aunque ya exista el CSV del vídeo",
                          "transcribe again even if the video's CSV already exists"))
    t.add_argument("--mostrar", action="store_true",
                   help=m("muestra cada frase al transcribir", "print each phrase as it is transcribed"))
    t.set_defaults(func=cmd_transcribir)

    x = sub.add_parser("texto", help=m(
        "sentimiento y toxicidad de las transcripciones (multilingüe)",
        "sentiment and toxicity of the transcripts (multilingual)"))
    x.add_argument("transcripciones", help=m("carpeta creada por 'polface transcribir'",
                                             "folder created by 'polface transcribir'"))
    x.add_argument("--salida", default="texto_analizado")
    x.add_argument("--sentimiento", default="lxyuan", choices=["lxyuan", "cardiffnlp", "no"],
                   help=m("modelo de sentimiento (por defecto lxyuan; 'no' lo desactiva)",
                          "sentiment model (default lxyuan; 'no' disables it)"))
    x.add_argument("--toxicidad", default="detoxify", choices=["detoxify", "no"],
                   help=m("modelo de toxicidad (por defecto detoxify; 'no' lo desactiva)",
                          "toxicity model (default detoxify; 'no' disables it)"))
    x.add_argument("--forzar-idioma", action="store_true",
                   help=m("puntúa también idiomas que el modelo no declara soportar (sin validar)",
                          "also score languages the model does not declare to support (unvalidated)"))
    x.add_argument("--dispositivo", default="auto", choices=["auto", "cpu", "cuda"])
    x.add_argument("--lote", type=int, default=32,
                   help=m("textos por lote (por defecto 32)", "texts per batch (default 32)"))
    x.add_argument("--rehacer", action="store_true")
    x.set_defaults(func=cmd_texto)

    u = sub.add_parser("unir", help=m("añadir a cada aparición el texto oído alrededor",
                                      "attach to each appearance the text heard around it"))
    u.add_argument("carpeta", help=m("carpeta con detecciones.csv", "folder with detecciones.csv"))
    u.add_argument("--transcripciones", default="transcripciones")
    u.add_argument("--ventana-segundos", type=float, default=5.0,
                   help=m("segundos de texto antes y después de la aparición (por defecto 5)",
                          "seconds of text before and after the appearance (default 5)"))
    u.set_defaults(func=cmd_unir)

    pr = sub.add_parser("procesar", help=m(
        "todo en uno: galería, análisis facial y descriptivos (y texto, si se pide)",
        "all in one: gallery, face analysis and descriptives (and text, if requested)"))
    pr.add_argument("videos", help=m("vídeo o carpeta de vídeos", "video or folder of videos"))
    pr.add_argument("--caras", required=True, help=m(
        "carpeta de caras de referencia (una subcarpeta por persona)",
        "reference faces folder (one subfolder per person)"))
    pr.add_argument("--salida", default="resultados")
    pr.add_argument("--cada-segundos", type=float, default=1.0)
    pr.add_argument("--umbral", type=float, default=0.5)
    pr.add_argument("--area-minima", type=int, default=0)
    pr.add_argument("--reanudar", action="store_true")
    pr.add_argument("--transcribir", action="store_true", help=m(
        "además transcribe con Whisper y calcula sentimiento y toxicidad (lento; necesita los extras)",
        "also transcribe with Whisper and compute sentiment and toxicity (slow; needs the extras)"))
    pr.add_argument("--modelo-whisper", default="large-v3-turbo")
    comunes(pr)
    pr.set_defaults(func=cmd_procesar)

    d = sub.add_parser("dashboard", help=m("abrir el panel interactivo con los resultados",
                                           "open the interactive dashboard with the results"))
    d.add_argument("carpeta", nargs="?", default="resultados",
                   help=m("carpeta con videos.csv y detecciones.csv (por defecto resultados)",
                          "folder with videos.csv and detecciones.csv (default resultados)"))
    d.add_argument("--videos", help=m("carpeta con los vídeos, para ver las cajas sobre el fotograma",
                                      "folder with the videos, to see the boxes on the frame"))
    d.add_argument("--caras", help=m("carpeta de caras de referencia (una subcarpeta por persona): "
                                     "de ella sale la lista de personas del panel",
                                     "reference faces folder (one subfolder per person): the "
                                     "dashboard's people list comes from it"))
    d.add_argument("--idioma", choices=list(IDIOMAS), default=None,
                   help=m("idioma inicial del panel (se puede cambiar dentro del panel; "
                          "por defecto el de --lang)",
                          "initial language of the dashboard (can be changed inside it; "
                          "defaults to --lang)"))
    d.add_argument("--puerto", type=int, default=8501)
    d.add_argument("--sin-navegador", action="store_true",
                   help=m("no abrir el navegador", "do not open the browser"))
    d.set_defaults(func=cmd_dashboard)

    e = sub.add_parser("demo", help=m("crear datos de ejemplo sintéticos para probar el panel",
                                      "create synthetic sample data to try the dashboard"))
    e.add_argument("carpeta", nargs="?", default="resultados_demo")
    e.add_argument("--videos-por-grupo", type=int, default=4)
    e.add_argument("--abrir", action="store_true",
                   help=m("abrir el panel con ellos al terminar", "open the dashboard with them"))
    e.add_argument("--puerto", type=int, default=8501)
    e.set_defaults(func=cmd_demo)

    r = sub.add_parser("resumen", help=m("calcular descriptivos de unos resultados",
                                         "compute descriptive statistics of some results"))
    r.add_argument("carpeta", help=m("carpeta con detecciones.csv y videos.csv",
                                     "folder with detecciones.csv and videos.csv"))
    r.set_defaults(func=cmd_resumen)

    for sp in sub.choices.values():  # --lang también se acepta después de la orden
        sp.add_argument("--lang", choices=list(IDIOMAS), default=argparse.SUPPRESS,
                        help=m("idioma de los mensajes", "language of the messages"))
    return p


COMANDOS = {"galeria", "analizar", "transcribir", "texto", "unir", "procesar", "dashboard",
            "demo", "resumen"}


def main(argv=None) -> int:
    lista = list(sys.argv[1:] if argv is None else argv)
    if not (COMANDOS & set(lista)) and not {"-h", "--help", "--version"} & set(lista):
        lista.append("dashboard")        # sin orden: abre el panel (para quien no usa terminal)
    fijar_idioma(idioma_desde(lista, os.environ))
    args = construir_parser().parse_args(lista)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
