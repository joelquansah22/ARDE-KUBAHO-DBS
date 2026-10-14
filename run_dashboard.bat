@echo off
rem ARDE/KUBAHO MEAL dashboard: double-click to start, then open http://localhost:8501
cd /d "%~dp0"
call .venv\Scripts\activate.bat
if not exist data\warehouse\arde.duckdb (
  echo Building the data warehouse first...
  python src\pipeline.py
)
streamlit run dashboard\app.py
pause
