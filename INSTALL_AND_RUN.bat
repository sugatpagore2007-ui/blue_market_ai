@echo off
title Blue Forex Market AI - Install and Run
python -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
echo.
echo Install complete. Edit .env / broker_settings.json if needed.
echo Start Blue with RUN_BLUE_FOREX_AI.bat or python main.py
pause
