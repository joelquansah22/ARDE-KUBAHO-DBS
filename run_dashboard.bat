@echo off
rem ARDE/KUBAHO MEAL dashboard: double-click to start, then open http://localhost:8501
cd /d "%~dp0"
call .venv\Scripts\activate.bat
rem On a fresh copy: create the demonstration files and prepare the figures (skipped when already done)
python src\first_run.py
if errorlevel 1 (
  pause
  exit /b 1
)
streamlit run dashboard\app.py
pause
