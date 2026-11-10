@echo off
rem PolFace: instala (la primera vez) y abre el panel. Windows.
rem Install (first time) and open the dashboard. Windows.
rem   PolFace.bat            instala lo basico y abre el panel
rem   PolFace.bat completo   anade transcripcion (Whisper) y sentimiento/toxicidad
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo Hace falta Python 3.9 o superior / Python 3.9 or later is required: https://www.python.org/downloads/
  echo Marca "Add python.exe to PATH" al instalarlo / Tick "Add python.exe to PATH" when installing.
  pause
  exit /b 1
)

set EXTRAS=dashboard
if /i "%1"=="completo" set EXTRAS=dashboard,transcripcion,texto
set MARCA=.venv\.polface_instalado_%EXTRAS:,=_%

if not exist .venv\Scripts\python.exe (
  echo Creando el entorno, una sola vez... / Creating the environment, once...
  python -m venv .venv
  if errorlevel 1 ( pause & exit /b 1 )
)
if not exist "%MARCA%" (
  echo Instalando PolFace, puede tardar unos minutos... / Installing PolFace, this can take a few minutes...
  .venv\Scripts\python.exe -m pip install --quiet --upgrade pip
  .venv\Scripts\python.exe -m pip install --quiet -e ".[%EXTRAS%]"
  if errorlevel 1 (
    echo.
    echo La instalacion ha fallado. En Windows, InsightFace puede necesitar las
    echo "Microsoft C++ Build Tools": https://visualstudio.microsoft.com/visual-cpp-build-tools/
    echo Installation failed. On Windows, InsightFace may need the Microsoft C++ Build Tools.
    pause
    exit /b 1
  )
  echo ok> "%MARCA%"
)

echo Abriendo el panel en http://localhost:8501 / Opening the dashboard...
.venv\Scripts\python.exe -m polface dashboard
pause
