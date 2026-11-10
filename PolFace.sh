#!/usr/bin/env bash
# PolFace: instala (la primera vez) y abre el panel. Linux y macOS.
# Uso:  ./PolFace.sh            instala lo básico y abre el panel
#       ./PolFace.sh --completo añade transcripción (Whisper) y sentimiento/toxicidad
# Install (first time) and open the dashboard. Linux and macOS.
set -e
cd "$(dirname "$0")"

PY="$(command -v python3 || command -v python || true)"
if [ -z "$PY" ] || ! "$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)'; then
  echo "Hace falta Python 3.9 o superior / Python 3.9 or later is required: https://www.python.org/downloads/"
  exit 1
fi

EXTRAS="dashboard"
[ "$1" = "--completo" ] && EXTRAS="dashboard,transcripcion,texto"

if [ ! -x .venv/bin/python ]; then
  echo "Creando el entorno (una sola vez)... / Creating the environment (once)..."
  "$PY" -m venv .venv
fi
MARCA=".venv/.polface_instalado_${EXTRAS//,/_}"
if [ ! -f "$MARCA" ]; then
  echo "Instalando PolFace ($EXTRAS); puede tardar unos minutos... / Installing PolFace ($EXTRAS); this can take a few minutes..."
  .venv/bin/python -m pip install --quiet --upgrade pip
  .venv/bin/python -m pip install --quiet -e ".[${EXTRAS}]"
  touch "$MARCA"
fi

echo "Abriendo el panel en http://localhost:8501 (Ctrl+C para cerrarlo) / Opening the dashboard..."
exec .venv/bin/python -m polface dashboard
