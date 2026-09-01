@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo   Radar Laboral - corrida local
echo ============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo No se encontro Python.
  echo Instalalo desde https://www.python.org/downloads/  ^(marca "Add to PATH"^)
  echo y volve a hacer doble clic en este archivo.
  echo.
  pause
  exit /b 1
)

echo Instalando lo que hace falta ^(la primera vez tarda un poco^)...
python -m pip install --quiet --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto error

echo.
echo Buscando avisos... esto tarda varios minutos, no cierres la ventana.
python -m scraper.main
if errorlevel 1 goto error

echo.
echo Abriendo la pagina en el navegador.
echo Para cerrar todo, cerra esta ventana negra cuando termines.
start "" http://localhost:8000
python -m http.server 8000 --directory docs
exit /b 0

:error
echo.
echo Algo fallo. Copiá el texto de arriba si necesitas ayuda.
echo.
pause
exit /b 1
