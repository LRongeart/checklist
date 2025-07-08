@echo off
REM Run the Checklist Qt app using the local Python environment

REM Change directory to the script location
cd /d %~dp0

REM Use the default Python, or specify the path if needed
python main.py

pause
