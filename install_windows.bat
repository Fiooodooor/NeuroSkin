@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (set "PYTHON=.venv\Scripts\python.exe") else (set "PYTHON=python")
"%PYTHON%" -m pip install -r requirements.txt || exit /b 1
"%PYTHON%" environment_doctor.py || exit /b 1
endlocal
