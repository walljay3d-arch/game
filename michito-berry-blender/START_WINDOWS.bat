@echo off
cd /d "%~dp0"
py -m pip install -r requirements.txt
if errorlevel 1 (echo Python installation or dependency setup failed. & pause & exit /b 1)
start "" "http://localhost:8765/control"
py server.py
pause
