"""Textos del panel en español e inglés.

Para añadir un idioma: copia un bloque de ``TEXTOS``, tradúcelo y añade su
código a ``IDIOMAS``.
"""

from __future__ import annotations

IDIOMAS = {"es": "Español", "en": "English"}
IDIOMA_POR_DEFECTO = "es"

TEXTOS = {
    "es": {
        "titulo_pagina": "PolFace · panel de resultados",
        "titulo": "PolFace · panel de resultados",
        "idioma": "Idioma / Language",
        "aviso": ("Las cifras de **tiempo en pantalla son estimaciones** (un fotograma cada N "
                  "segundos) y el reconocimiento facial comete errores. El texto asociado es "
                  "**contexto sonoro, no habla de la persona**. Lee `AVISO_DE_USO.md` antes de "
                  "interpretar o publicar resultados."),
        "datos": "Datos",
        "carpeta_res": "Carpeta de resultados",
        "carpeta_vid": "Carpeta de vídeos",
        "carpeta_vid_ayuda": ("Los vídeos que se analizan. La pestaña «Fotograma» también los usa "
                              "para dibujar la caja de la cara."),
        "recargar": "Recargar datos",
        "cargando": "Cargando resultados…",
        "sin_personas": ("Los resultados no contienen ninguna persona identificada. Prueba con "
                         "un umbral más alto (`--umbral`) o revisa la galería de referencia."),
        "filtros": "Filtros",
        "personas": "Personas",
        "grupo": "Grupo (carpeta de primer nivel)",
        "elegir_videos": "Elegir vídeos concretos",
        "videos": "Vídeos",
        "dist_max": "Distancia máxima de identificación",
        "dist_max_ayuda": ("Menor = más estricto. Permite endurecer el umbral usado al analizar, "
                           "no relajarlo."),
        "area_min": "Tamaño mínimo de la cara (% del fotograma)",
        "idioma_texto": "Idioma del texto asociado",
        "sin_apariciones": "Con estos filtros no queda ninguna aparición.",
        "k_videos": "Vídeos analizados",
        "k_horas": "Horas de vídeo",
        "k_personas": "Personas identificadas",
        "k_apar": "Apariciones",
        "desconocidos": "{n} caras sin identificar guardadas en los resultados (no se muestran aquí).",
        "tab_vis": "Visibilidad",
        "tab_grp": "Por grupo o vídeo",
        "tab_lin": "Línea de tiempo",
        "tab_area": "Tamaño de la cara",
        "tab_co": "Coapariciones",
        "tab_txt": "Texto",
        "tab_fot": "Fotograma",
        "tab_dat": "Datos",
        "t_tiempo": "Tiempo estimado en pantalla",
        "c_persona": "Persona",
        "c_fotogramas": "Fotogramas",
        "c_videos": "Vídeos",
        "c_segundos": "Segundos en pantalla",
        "c_area_media": "Área media",
        "c_area_mediana": "Área mediana",
        "c_dist_media": "Distancia media",
        "c_video": "Vídeo",
        "c_minuto": "Minuto",
        "c_tox": "Toxicidad",
        "c_texto": "Texto",
        "comparar": "Comparar por",
        "modo_grupo": "Grupo (carpeta)",
        "modo_video": "Vídeo",
        "un_grupo": ("Solo hay un grupo. Si ordenas los vídeos en subcarpetas (por ejemplo, una "
                     "por cadena) podrás compararlos aquí."),
        "top30": "Se muestran los 30 vídeos con más tiempo en pantalla.",
        "sin_datos": "No hay datos para este filtro.",
        "unidad_min": "min",
        "unidad_fotogramas": "fotogramas",
        "video": "Vídeo",
        "nota_linea": "Cada marca es un fotograma muestreado en el que se identifica a la persona.",
        "nota_area": ("Una cara grande suele indicar un primer plano y una pequeña, un plano "
                      "general o de fondo. El tamaño solo no mide la importancia de la "
                      "aparición."),
        "necesita_mas": "Hace falta más de una persona para ver coapariciones.",
        "nota_co": ("Fotogramas muestreados en los que aparecen juntas dos personas (la "
                    "diagonal se oculta)."),
        "sin_texto": ("Los resultados no incluyen texto. Ejecuta `polface transcribir`, "
                      "`polface texto` y `polface unir` (ver README) y pulsa «Recargar datos»."),
        "aviso_texto": ("El texto es el audio que suena alrededor de la aparición, no "
                        "necesariamente lo que dice la persona. Sentimiento y toxicidad son "
                        "puntuaciones automáticas y aproximadas: valídalas con una muestra "
                        "codificada a mano."),
        "h_polaridad": "Polaridad media del texto asociado",
        "h_toxicidad": "Toxicidad media del texto asociado",
        "sin_puntuar": ("El texto aún no está puntuado. Ejecuta `polface texto` y vuelve a "
                        "ejecutar `polface unir`."),
        "desconocido_idioma": "¿?",
        "h_idiomas": "Idioma del texto asociado (apariciones)",
        "h_contextos": "Contextos con mayor toxicidad",
        "tox_min": "Toxicidad mínima",
        "fot_sin_carpeta": ("Indica la carpeta de vídeos en la barra lateral para ver la caja "
                            "de la cara sobre cada fotograma."),
        "persona": "Persona",
        "aparicion": "Aparición",
        "fot_no_video": "No encuentro «{v}» dentro de {c}.",
        "fot_no_leer": "No se pudo leer ese fotograma del vídeo.",
        "fot_pie": "{v} · minuto {m:.2f} · {n} cara(s) identificada(s)",
        "fot_texto": "**Texto en ±5 s:** {t}",
        "dat_intro": "Descarga lo que se está viendo con los filtros actuales.",
        "dl_apar": "Apariciones filtradas (CSV)",
        "dl_resumen": "Resumen por persona (CSV)",
        "primeras_filas": "Se muestran las primeras 1.000 filas; la descarga incluye todas.",
        "carpeta_caras": "Carpeta de caras",
        "carpeta_caras_ayuda": ("La misma carpeta que usas con «polface galeria»: una subcarpeta "
                                "por persona con sus fotos. La lista de personas sale de aquí."),
        "examinar": "📁 Examinar…",
        "dlg_res": "Elige la carpeta de resultados",
        "dlg_videos": "Elige la carpeta de vídeos",
        "dlg_caras": "Elige la carpeta de caras",
        "nav_actual": "Carpeta actual",
        "nav_subir": "⬆ Carpeta superior",
        "nav_entrar": "Entrar en…",
        "nav_usar": "Usar esta carpeta",
        "caras_n": "{n} personas ofrecidas en la carpeta de caras.",
        "caras_vacia": "No hay subcarpetas con imágenes en {c}: se usan las personas detectadas.",
        "personas_fuera": ("{n} personas detectadas no están en la carpeta de caras y se "
                           "ocultan: {l}."),
        "h_texto_filtros": "Texto",
        "idioma_texto_ayuda": ("Solo afecta a la pestaña Texto. Por defecto, español e inglés; "
                               "el resto de idiomas se pueden añadir aquí."),
        "nota_idiomas_texto": "El gráfico de idiomas muestra todos los idiomas detectados.",
        "an_titulo": "Analizar vídeos",
        "an_ayuda": ("Elige la carpeta de vídeos y la de caras (una subcarpeta por persona, con sus "
                     "fotos) y pulsa «Analizar». Se hace en este ordenador y nada se envía fuera; "
                     "los resultados se guardan en la carpeta de resultados y salen aquí debajo."),
        "an_resumen": "{v} vídeos y {p} personas con fotos.",
        "an_falta_videos": "Indica una carpeta que contenga vídeos.",
        "an_falta_caras": ("Indica una carpeta de caras con una subcarpeta por persona y al menos "
                           "una foto en cada una."),
        "an_cada": "Un fotograma cada (segundos)",
        "an_cada_ayuda": "Más pequeño = más preciso y más lento.",
        "an_umbral": "Umbral de identificación",
        "an_umbral_ayuda": "Menor = más estricto. 0,5 es un punto de partida: calíbralo con tus datos.",
        "an_area": "Área mínima de la cara (píxeles²)",
        "an_area_ayuda": "6400 = 80×80 px. Ignora caras pequeñas, por ejemplo en pantallas de fondo.",
        "an_disp": "Dispositivo",
        "an_reanudar": "Reanudar (omitir vídeos ya procesados)",
        "an_transc": "Transcribir y puntuar el texto (lento; necesita los extras de transcripción y texto)",
        "an_modelo": "Modelo Whisper",
        "an_sobrescribe": "Se sobrescribirán los resultados de {c}.",
        "an_iniciar": "▶ Analizar",
        "an_parar": "⏹ Parar",
        "an_corriendo": "Analizando…",
        "an_paso_galeria": "Creando la galería de caras",
        "an_paso_analizar": "Buscando a las personas en los vídeos",
        "an_paso_resumen": "Calculando descriptivos",
        "an_paso_transcribir": "Transcribiendo con Whisper",
        "an_paso_texto": "Calculando sentimiento y toxicidad",
        "an_paso_unir": "Uniendo el texto con las apariciones",
        "an_progreso": "{h} de {t}",
        "an_terminado": "Análisis terminado.",
        "an_error": "El análisis ha fallado o se ha interrumpido. Revisa el registro.",
        "an_log": "Registro",
        "an_sin_resultados": "Todavía no hay resultados en {c}. Elige las carpetas y pulsa «Analizar».",
        "nav_ruta": "Ruta",
        "nav_inicio": "🏠 Inicio",
        "nav_filtro": "Filtrar carpetas por nombre",
        "nav_vacia": "No hay subcarpetas aquí.",
        "nav_mas": "… y {n} carpetas más (usa el filtro).",
        "an_sin_gpu": ("No se detecta GPU para onnxruntime: se usará la CPU. Para usar la GPU "
                       "NVIDIA: pip uninstall onnxruntime && pip install onnxruntime-gpu"),
        # gráficos
        "g_min_pantalla": "Minutos estimados en pantalla",
        "g_hover_min": "{x} min estimados",
        "g_hover_fv": "{f} fotogramas · {v} vídeos",
        "g_minuto_video": "Minuto del vídeo",
        "g_minuto": "minuto",
        "g_distancia": "distancia",
        "g_cara_pct": "cara {a} % del fotograma",
        "g_area_cara": "Área de la cara (% del fotograma)",
        "g_pct_fotograma": "% del fotograma",
        "g_polaridad": "Polaridad media (−1 negativo … +1 positivo)",
        "g_pol_media": "polaridad media",
        "g_apar_punt": "apariciones puntuadas",
        "g_toxicidad": "Toxicidad media (0 a 1)",
        "g_tox_media": "toxicidad media",
        "g_maxima": "máxima",
        "g_apariciones": "Apariciones",
        "g_apariciones_n": "apariciones",
    },
    "en": {
        "titulo_pagina": "PolFace · results dashboard",
        "titulo": "PolFace · results dashboard",
        "idioma": "Idioma / Language",
        "aviso": ("**Screen-time figures are estimates** (one frame every N seconds) and face "
                  "recognition makes mistakes. The associated text is **background audio, not "
                  "what the person said**. Read `AVISO_DE_USO.en.md` before interpreting or "
                  "publishing results."),
        "datos": "Data",
        "carpeta_res": "Results folder",
        "carpeta_vid": "Videos folder",
        "carpeta_vid_ayuda": ("The videos to analyse. The “Frame” tab also uses them to draw the "
                              "face box."),
        "recargar": "Reload data",
        "cargando": "Loading results…",
        "sin_personas": ("The results contain no identified person. Try a higher threshold "
                         "(`--umbral`) or check the reference gallery."),
        "filtros": "Filters",
        "personas": "People",
        "grupo": "Group (top-level folder)",
        "elegir_videos": "Choose specific videos",
        "videos": "Videos",
        "dist_max": "Maximum identification distance",
        "dist_max_ayuda": ("Lower = stricter. You can tighten the threshold used when analysing, "
                           "not loosen it."),
        "area_min": "Minimum face size (% of the frame)",
        "idioma_texto": "Language of the associated text",
        "sin_apariciones": "No appearances are left with these filters.",
        "k_videos": "Videos analysed",
        "k_horas": "Hours of video",
        "k_personas": "People identified",
        "k_apar": "Appearances",
        "desconocidos": "{n} unidentified faces are stored in the results (not shown here).",
        "tab_vis": "Visibility",
        "tab_grp": "By group or video",
        "tab_lin": "Timeline",
        "tab_area": "Face size",
        "tab_co": "Co-appearances",
        "tab_txt": "Text",
        "tab_fot": "Frame",
        "tab_dat": "Data",
        "t_tiempo": "Estimated screen time",
        "c_persona": "Person",
        "c_fotogramas": "Frames",
        "c_videos": "Videos",
        "c_segundos": "Seconds on screen",
        "c_area_media": "Mean area",
        "c_area_mediana": "Median area",
        "c_dist_media": "Mean distance",
        "c_video": "Video",
        "c_minuto": "Minute",
        "c_tox": "Toxicity",
        "c_texto": "Text",
        "comparar": "Compare by",
        "modo_grupo": "Group (folder)",
        "modo_video": "Video",
        "un_grupo": ("There is only one group. If you sort the videos into subfolders (for "
                     "example, one per channel) you can compare them here."),
        "top30": "Showing the 30 videos with the most screen time.",
        "sin_datos": "No data for this filter.",
        "unidad_min": "min",
        "unidad_fotogramas": "frames",
        "video": "Video",
        "nota_linea": "Each mark is a sampled frame in which the person is identified.",
        "nota_area": ("A large face usually means a close-up and a small one a wide or "
                      "background shot. Size alone does not measure how important the "
                      "appearance is."),
        "necesita_mas": "At least two people are needed to show co-appearances.",
        "nota_co": ("Sampled frames in which two people appear together (the diagonal is "
                    "hidden)."),
        "sin_texto": ("The results include no text. Run `polface transcribir`, `polface texto` "
                      "and `polface unir` (see the README) and press “Reload data”."),
        "aviso_texto": ("The text is the audio heard around the appearance, not necessarily "
                        "what the person says. Sentiment and toxicity are automatic, approximate "
                        "scores: validate them against a hand-coded sample."),
        "h_polaridad": "Mean polarity of the associated text",
        "h_toxicidad": "Mean toxicity of the associated text",
        "sin_puntuar": ("The text has not been scored yet. Run `polface texto` and then "
                        "`polface unir` again."),
        "desconocido_idioma": "?",
        "h_idiomas": "Language of the associated text (appearances)",
        "h_contextos": "Contexts with the highest toxicity",
        "tox_min": "Minimum toxicity",
        "fot_sin_carpeta": ("Enter the videos folder in the sidebar to see the face box on each "
                            "frame."),
        "persona": "Person",
        "aparicion": "Appearance",
        "fot_no_video": "Cannot find “{v}” inside {c}.",
        "fot_no_leer": "That frame could not be read from the video.",
        "fot_pie": "{v} · minute {m:.2f} · {n} face(s) identified",
        "fot_texto": "**Text within ±5 s:** {t}",
        "dat_intro": "Download what you are seeing with the current filters.",
        "dl_apar": "Filtered appearances (CSV)",
        "dl_resumen": "Summary by person (CSV)",
        "primeras_filas": "Showing the first 1,000 rows; the download includes all of them.",
        "carpeta_caras": "Faces folder",
        "carpeta_caras_ayuda": ("The same folder you use with “polface galeria”: one subfolder "
                                "per person with their photos. The people list comes from here."),
        "examinar": "📁 Browse…",
        "dlg_res": "Choose the results folder",
        "dlg_videos": "Choose the videos folder",
        "dlg_caras": "Choose the faces folder",
        "nav_actual": "Current folder",
        "nav_subir": "⬆ Parent folder",
        "nav_entrar": "Go into…",
        "nav_usar": "Use this folder",
        "caras_n": "{n} people offered in the faces folder.",
        "caras_vacia": "No subfolders with images in {c}: using the detected people.",
        "personas_fuera": ("{n} detected people are not in the faces folder and are hidden: "
                           "{l}."),
        "h_texto_filtros": "Text",
        "idioma_texto_ayuda": ("Only affects the Text tab. Spanish and English by default; other "
                               "languages can be added here."),
        "nota_idiomas_texto": "The language chart shows every language detected.",
        "an_titulo": "Analyse videos",
        "an_ayuda": ("Choose the videos folder and the faces folder (one subfolder per person, with "
                     "their photos) and press “Analyse”. It runs on this computer and nothing is "
                     "sent out; results are saved in the results folder and appear below."),
        "an_resumen": "{v} videos and {p} people with photos.",
        "an_falta_videos": "Enter a folder that contains videos.",
        "an_falta_caras": ("Enter a faces folder with one subfolder per person and at least one "
                           "photo in each."),
        "an_cada": "One frame every (seconds)",
        "an_cada_ayuda": "Smaller = more precise and slower.",
        "an_umbral": "Identification threshold",
        "an_umbral_ayuda": "Lower = stricter. 0.5 is a starting point: calibrate it with your data.",
        "an_area": "Minimum face area (pixels²)",
        "an_area_ayuda": "6400 = 80×80 px. Ignores small faces, e.g. on background screens.",
        "an_disp": "Device",
        "an_reanudar": "Resume (skip videos already processed)",
        "an_transc": "Transcribe and score the text (slow; needs the transcription and text extras)",
        "an_modelo": "Whisper model",
        "an_sobrescribe": "The results in {c} will be overwritten.",
        "an_iniciar": "▶ Analyse",
        "an_parar": "⏹ Stop",
        "an_corriendo": "Analysing…",
        "an_paso_galeria": "Building the faces gallery",
        "an_paso_analizar": "Looking for the people in the videos",
        "an_paso_resumen": "Computing descriptive statistics",
        "an_paso_transcribir": "Transcribing with Whisper",
        "an_paso_texto": "Computing sentiment and toxicity",
        "an_paso_unir": "Joining the text with the appearances",
        "an_progreso": "{h} of {t}",
        "an_terminado": "Analysis finished.",
        "an_error": "The analysis failed or was interrupted. Check the log.",
        "an_log": "Log",
        "an_sin_resultados": "There are no results in {c} yet. Choose the folders and press “Analyse”.",
        "nav_ruta": "Path",
        "nav_inicio": "🏠 Home",
        "nav_filtro": "Filter folders by name",
        "nav_vacia": "There are no subfolders here.",
        "nav_mas": "… and {n} more folders (use the filter).",
        "an_sin_gpu": ("No GPU detected for onnxruntime: the CPU will be used. To use an NVIDIA "
                       "GPU: pip uninstall onnxruntime && pip install onnxruntime-gpu"),
        # gráficos
        "g_min_pantalla": "Estimated minutes on screen",
        "g_hover_min": "{x} estimated min",
        "g_hover_fv": "{f} frames · {v} videos",
        "g_minuto_video": "Video minute",
        "g_minuto": "minute",
        "g_distancia": "distance",
        "g_cara_pct": "face {a} % of the frame",
        "g_area_cara": "Face area (% of the frame)",
        "g_pct_fotograma": "% of the frame",
        "g_polaridad": "Mean polarity (−1 negative … +1 positive)",
        "g_pol_media": "mean polarity",
        "g_apar_punt": "scored appearances",
        "g_toxicidad": "Mean toxicity (0 to 1)",
        "g_tox_media": "mean toxicity",
        "g_maxima": "maximum",
        "g_apariciones": "Appearances",
        "g_apariciones_n": "appearances",
    },
}


def tr(idioma: str, clave: str, **kw) -> str:
    """Texto ``clave`` en ``idioma`` (con respaldo al español)."""
    txt = TEXTOS.get(idioma, TEXTOS[IDIOMA_POR_DEFECTO]).get(clave)
    if txt is None:
        txt = TEXTOS[IDIOMA_POR_DEFECTO][clave]
    return txt.format(**kw) if kw else txt


def miles(n: float, idioma: str, decimales: int = 0) -> str:
    """Formatea un número con el separador de miles de cada idioma (1.234 / 1,234)."""
    s = f"{n:,.{decimales}f}"
    if idioma == "es":
        s = s.replace(",", "§").replace(".", ",").replace("§", ".")
    return s


# ----------------------------------------------------- mensajes de la línea de comandos
_estado = {"idioma": IDIOMA_POR_DEFECTO}


def fijar_idioma(idioma: str | None) -> str:
    """Fija el idioma de los mensajes de la línea de comandos (``es`` o ``en``)."""
    if idioma in IDIOMAS:
        _estado["idioma"] = idioma
    return _estado["idioma"]


def idioma_actual() -> str:
    return _estado["idioma"]


def idioma_desde(argv, entorno) -> str:
    """Idioma pedido con ``--lang X`` / ``--lang=X`` o con ``POLFACE_LANG`` (por defecto, es)."""
    argv = list(argv or [])
    pedido = None
    for i, a in enumerate(argv):
        if a == "--lang" and i + 1 < len(argv):
            pedido = argv[i + 1]
        elif a.startswith("--lang="):
            pedido = a.split("=", 1)[1]
    return pedido if pedido in IDIOMAS else (
        entorno.get("POLFACE_LANG") if entorno.get("POLFACE_LANG") in IDIOMAS
        else IDIOMA_POR_DEFECTO)


def m(es: str, en: str, **kw) -> str:
    """Mensaje en el idioma actual; ``kw`` se aplica con ``str.format``."""
    txt = en if _estado["idioma"] == "en" else es
    return txt.format(**kw) if kw else txt
