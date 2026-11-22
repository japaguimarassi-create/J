@echo off
setlocal
cd /d "%~dp0"
py -3 --version >nul 2>&1 || (echo Python 3.10+ nao encontrado.& pause & exit /b 1)
py -3 -m pip install -r requirements.txt || (echo Falha ao instalar dependencias.& pause & exit /b 1)
py -3 agent.py
pause
