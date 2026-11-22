@echo off
setlocal
cd /d "%~dp0"
py -3 --version >nul 2>&1 || (echo Python 3.10+ nao encontrado.& pause & exit /b 1)
if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv || (echo Falha ao criar ambiente Python.& pause & exit /b 1)
)
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt || (echo Falha ao instalar dependencias.& pause & exit /b 1)
start "" /b cmd /c "timeout /t 2 >nul & start http://127.0.0.1:8765"
".venv\Scripts\python.exe" agent.py
pause
