"""Lanzar y vigilar un análisis en segundo plano (lo usa el panel).

El análisis se ejecuta como un proceso aparte (``polface procesar``) que escribe su
progreso en ``<salida>/procesar.log``. Así sigue aunque el navegador se recargue y el panel
solo tiene que leer el registro. Sin dependencias de Streamlit.
"""

from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

LOG = "procesar.log"
INFO = "procesar.json"
FLAG_OK = ".procesar_ok"

_PROCESOS: Dict[int, subprocess.Popen] = {}   # hijos lanzados por este proceso (evita zombis)
_PASO = re.compile(r"^## (\w+)")
_AVANCE = re.compile(r"^\[(\d+)/(\d+)\]")


@dataclass
class Estado:
    estado: str            # "ninguno" | "corriendo" | "terminado" | "error"
    paso: str = ""         # galeria | analizar | resumen | transcribir | texto | unir
    hecho: int = 0
    total: int = 0
    log: str = ""          # últimas líneas del registro


def _vivo(pid: int) -> bool:
    p = _PROCESOS.get(pid)
    if p is not None:
        return p.poll() is None
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    try:  # un zombi cuenta como terminado (Linux)
        return Path(f"/proc/{pid}/stat").read_text().split(")")[-1].split()[0] != "Z"
    except OSError:
        return True


def comando(videos: str, caras: str, salida: str, *, idioma: str = "es", cada_segundos: float = 1.0,
            umbral: float = 0.5, area_minima: int = 0, dispositivo: str = "auto",
            reanudar: bool = False, transcribir: bool = False,
            modelo_whisper: str = "large-v3-turbo") -> List[str]:
    """Línea de comandos de ``polface procesar`` para este python."""
    c = [sys.executable, "-m", "polface", "--lang", idioma, "procesar", videos,
         "--caras", caras, "--salida", salida, "--cada-segundos", str(cada_segundos),
         "--umbral", str(umbral), "--area-minima", str(int(area_minima)),
         "--dispositivo", dispositivo]
    if reanudar:
        c.append("--reanudar")
    if transcribir:
        c += ["--transcribir", "--modelo-whisper", modelo_whisper]
    return c


def iniciar(orden: List[str], salida: Path) -> int:
    """Lanza ``orden`` en segundo plano con su registro en ``salida``. Devuelve el pid."""
    salida = Path(salida)
    salida.mkdir(parents=True, exist_ok=True)
    (salida / FLAG_OK).unlink(missing_ok=True)
    log = open(salida / LOG, "w", encoding="utf-8")
    env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")
    kw = {"start_new_session": True} if os.name != "nt" else {}
    p = subprocess.Popen(orden, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                         env=env, **kw)
    log.close()
    _PROCESOS[p.pid] = p
    (salida / INFO).write_text(json.dumps({"pid": p.pid, "orden": orden}), encoding="utf-8")
    return p.pid


def estado(salida: Path, lineas: int = 12) -> Estado:
    """Estado del último análisis lanzado hacia ``salida``."""
    salida = Path(salida)
    f_info = salida / INFO
    if not f_info.exists():
        return Estado("ninguno")
    try:
        pid = int(json.loads(f_info.read_text(encoding="utf-8"))["pid"])
    except (ValueError, KeyError, OSError):
        return Estado("ninguno")
    texto = ""
    try:
        texto = (salida / LOG).read_text(encoding="utf-8", errors="replace")
    except OSError:
        pass
    filas = texto.splitlines()
    paso, hecho, total = "", 0, 0
    for linea in filas:
        mp = _PASO.match(linea)
        if mp:
            paso, hecho, total = mp.group(1), 0, 0
            continue
        ma = _AVANCE.match(linea)
        if ma:
            hecho, total = int(ma.group(1)), int(ma.group(2))
    cola = "\n".join(filas[-lineas:])
    if _vivo(pid):
        return Estado("corriendo", paso, hecho, total, cola)
    return Estado("terminado" if (salida / FLAG_OK).exists() else "error", paso, hecho, total, cola)


def parar(salida: Path) -> bool:
    """Detiene el análisis en curso. Devuelve ``True`` si había uno."""
    salida = Path(salida)
    try:
        pid = int(json.loads((salida / INFO).read_text(encoding="utf-8"))["pid"])
    except (ValueError, KeyError, OSError):
        return False
    if not _vivo(pid):
        return False
    try:
        if os.name == "nt":
            _PROCESOS[pid].terminate() if pid in _PROCESOS else None
        else:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
    except (OSError, KeyError):
        return False
    p = _PROCESOS.get(pid)
    if p is not None:
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            p.kill()
    return True
