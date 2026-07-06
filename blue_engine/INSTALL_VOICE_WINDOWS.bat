@echo off
echo Installing Blue voice control packages for current Python...
python -m pip install --upgrade pip
python -m pip install -r requirements_voice.txt
echo.
echo Done. Run: python main.py
echo Then type: voice status
echo Then type: voice
pause
