#!/usr/bin/env sh
# ARDE/KUBAHO MEAL dashboard: run ./run_dashboard.sh, then open http://localhost:8501
cd "$(dirname "$0")"
. .venv/bin/activate
# On a fresh copy: create the demonstration files and prepare the figures (skipped when already done)
python src/first_run.py || exit 1
streamlit run dashboard/app.py --server.headless false
