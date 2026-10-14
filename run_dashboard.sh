#!/usr/bin/env sh
# ARDE/KUBAHO MEAL dashboard: run ./run_dashboard.sh, then open http://localhost:8501
cd "$(dirname "$0")"
. .venv/bin/activate
[ -f data/warehouse/arde.duckdb ] || python src/pipeline.py
streamlit run dashboard/app.py
