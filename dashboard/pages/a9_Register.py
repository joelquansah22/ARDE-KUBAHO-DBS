"""Register (ARDE/KUBAHO workbook mode): browse every table with its source row, and download the whole register as
an Excel workbook with the same sheets and columns as ARDE's MEAL workbook (src/arde_register.py).

On screen, staff columns show roles, not names. The downloaded register is ARDE's own data in ARDE's own layout, so
it keeps the columns exactly as in their workbook (it can be edited and uploaded again).
"""

import datetime as dt

import pandas as pd
import streamlit as st

import ui                # first: it makes src/ importable
import arde_model        # noqa: E402
import arde_register     # noqa: E402

f = ui.arde_filters()
ui.page_header("Register", "register")
ui.how_to_read("register")
codes = f.project_codes
IN = ui.in_list(codes)
TABLES = {"Projects": "dim_project", "Results chain": "fact_result", "KPIs": "fact_kpi",
          "Activities": "fact_project_activity", "Reach": "fact_reach", "Partner contributions": "fact_contribution",
          "KPI change history": "kpi_change_history"}
choice = st.selectbox("Table", list(TABLES), key="reg_table")
name = TABLES[choice]
if name == "kpi_change_history":
    df = ui.query("SELECT * FROM kpi_change_history ORDER BY row_id DESC")
else:
    df = ui.query(f"SELECT * FROM {name} WHERE project_code IN {IN}", *codes)
for col in arde_model.fmt()["staff_name_columns"].get(name, []):
    df[col] = ui.roles(df[col])
search = st.text_input("Search (any column)", key="reg_search", placeholder="e.g. a code, a word in a title")
if search:
    hit = df.astype(str).apply(lambda c: c.str.contains(search, case=False, regex=False)).any(axis=1)
    df = df[hit]
if "source_row" in df:
    df.insert(0, "Source", df["source_sheet"].astype(str) + " row " + df["source_row"].astype(str))
st.caption(f"{len(df):,} rows. Staff columns show roles, not names.")
ui.table(df.drop(columns=[c for c in ("source_file",) if c in df]), f"register_{name}", height=420)

st.markdown("#### Download the register")
st.markdown("The current data, **with the KPI updates made on the dashboard**, as an Excel file with the same sheets "
            "and columns as ARDE/KUBAHO's MEAL workbook (and the same formulas in the calculated cells). It can be "
            "edited and uploaded again on the Upload Excel page. **Confidential:** it holds the workbook's own "
            "columns, including staff names.")
if st.button("Prepare the register", key="reg_prepare"):
    with st.spinner("Building the workbook..."):
        tables = {n: ui.query(f"SELECT * FROM {n}") for n in ("dim_project", "fact_result", "fact_kpi",
                                                               "fact_project_activity", "fact_reach",
                                                               "fact_contribution")}
        st.session_state["reg_file"] = arde_register.build(tables)
if "reg_file" in st.session_state:
    st.download_button("⬇ Download the register (.xlsx)", st.session_state["reg_file"],
                       file_name=f"ARDE-KUBAHO_MEAL_register_{dt.date.today():%Y-%m-%d}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="reg_download")
ui.footer()
