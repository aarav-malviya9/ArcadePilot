@echo off
echo [ArcadePilot] Setting up virtual environment...
python -m venv venv
call venv\Scripts\activate.bat
echo [ArcadePilot] Installing Python dependencies...
pip install --upgrade pip
pip install -r requirements.txt
echo [ArcadePilot] Installing Playwright browsers...
playwright install chromium
echo [ArcadePilot] Done. Run start.bat to launch.
pause
