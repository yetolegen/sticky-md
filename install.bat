@echo off
cd /d "%~dp0"
where pythonw >nul 2>nul || (echo Python 3 not found. Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH", then run this again. & pause & exit /b 1)
python -m pip install --quiet -r requirements.txt
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0make-shortcut.ps1"
start "" pythonw "%~dp0stickies.py"
echo Done. A sticky-md shortcut is on your Desktop.
timeout /t 4 >nul
