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

st.set_page_config(page_title="ARDE/KUBAHO Programme and Donor Data System", page_icon=":material/monitoring:", layout="wide",
                   initial_sidebar_state="expanded")
st.markdown(ui.CSS, unsafe_allow_html=True)
ui.sidebar_logo()                                     # logo and name, if assets/arde_logo.png exists
ui.startup_backup()                                   # a dated copy of the donor entries, once per start

HERE = Path(__file__).resolve().parent
# The menu, grouped under Insights, Data and Donors with Home at the top (config/page_help.yaml: menu). The same list
# gives the menu tiles on the Home page.
MENU = ui.menu()
PAGES = {section["section"]: [st.Page(str(HERE / p["file"]), title=p["title"], icon=p["icon"], url_path=p["url"] or None,
                                      default=p["key"] == "start")
                              for p in section["pages"]]
         for section in MENU}
NO_SEX_FILTER = {p["title"] for section in MENU for p in section["pages"]
                 if p["key"] in ui.load_yaml("page_help.yaml").get("no_sex_filter", [])}
page = st.navigation(PAGES)                           # the sidebar menu
ui.banner()                                           # on every page
ui.require_warehouse()                                # a friendly message if the pipeline has not been run
# The sex filter only applies where people are counted; elsewhere it is shown greyed out.
st.session_state["filters"] = ui.sidebar_filters(sex_applies=page.title not in NO_SEX_FILTER)
ui.source_files_in_sidebar()
page.run()
# An invisible marker after the whole page: tools/capture_screenshots.py waits for it, so a page is timed and
# photographed only once it has been drawn completely.
st.markdown("<div id='page-complete' style='display:none'></div>", unsafe_allow_html=True)
