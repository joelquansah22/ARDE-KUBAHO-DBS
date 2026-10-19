"""ARDE/KUBAHO MEAL dashboard: the entry point.

HOW TO RUN
    run_dashboard.bat (Windows) or ./run_dashboard.sh (Mac/Linux), or:
    streamlit run dashboard/app.py

This file sets up the page, the synthetic-data banner and the filters (shared by every page),
then opens the page chosen in the menu.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ui  # noqa: E402

st.set_page_config(page_title="ARDE/KUBAHO MEAL dashboard", page_icon="📊", layout="wide",
                   initial_sidebar_state="expanded")
st.markdown(ui.CSS, unsafe_allow_html=True)
ui.sidebar_logo()                                     # logo and name, if assets/arde_logo.png exists
ui.startup_backup()                                   # a dated copy of the donor entries, once per start

HERE = Path(__file__).resolve().parent
PAGES = [
    st.Page(str(HERE / "home.py"), title="Executive summary", icon="🏠", default=True),
    st.Page(str(HERE / "pages" / "1_Programme_Overview.py"), title="Programme overview", icon="📈", url_path="overview"),
    st.Page(str(HERE / "pages" / "2_Indicators.py"), title="Indicators", icon="🎯", url_path="indicators"),
    st.Page(str(HERE / "pages" / "3_Geography.py"), title="Geography", icon="🗺️", url_path="geography"),
    st.Page(str(HERE / "pages" / "4_Data_Quality.py"), title="Data quality", icon="✅", url_path="data-quality"),
    st.Page(str(HERE / "pages" / "5_Donor_Pipeline.py"), title="Donor pipeline", icon="🤝", url_path="donor-pipeline"),
    st.Page(str(HERE / "pages" / "6_Donor_Entry.py"), title="Donor entry", icon="✏️", url_path="donor-entry"),
]
page = st.navigation(PAGES)
ui.banner()                                           # on every page
ui.require_warehouse()                                # a friendly message if the pipeline has not been run
# The sex filter only applies where people are counted; elsewhere it is shown greyed out.
st.session_state["filters"] = ui.sidebar_filters(sex_applies=page.title not in ("Data quality", "Donor pipeline", "Donor entry"))
ui.source_files_in_sidebar()
page.run()
