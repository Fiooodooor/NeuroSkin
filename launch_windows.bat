@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (set "PYTHON=.venv\Scripts\python.exe") else (set "PYTHON=python")
if "%~1"=="" ("%PYTHON%" server.py --open --cores auto) else ("%PYTHON%" server.py --open --cores %1)
endlocal
