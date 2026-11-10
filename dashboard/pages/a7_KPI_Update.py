"""KPI update (ARDE/KUBAHO workbook mode): pick project > result > KPI and record the new achieved value and status.

This replaces editing the amber cells of the workbook's 'Results & KPIs' sheet. The workbook file is never changed:
updates are kept in data/real/app/kpi_updates.db (src/arde_store.py) with a change history (who, when, old and new
value) and a backup after every save, the same pattern as donor entry. They reach the other pages when the figures
are updated (button at the bottom).
"""

import pandas as pd
import streamlit as st

import ui                # first: it makes src/ importable
import arde_store        # noqa: E402

f = ui.arde_filters()
ui.page_header("KPI update", "kpi_update")
ui.how_to_read("kpi_update")
who, labels, ready = ui.staff_picker("updating a KPI")

codes = f.project_codes
if not codes:
    ui.no_data()
    st.stop()
IN = ui.in_list(codes)
k = ui.query(f"SELECT * FROM fact_kpi WHERE project_code IN {IN} ORDER BY kpi_code", *codes)
r = ui.query(f"SELECT result_code, project_code, level, statement, result_order FROM fact_result "
             f"WHERE project_code IN {IN} ORDER BY result_order", *codes)
_, uploaded_at = arde_store.current_workbook()
latest = arde_store.current_updates(since=uploaded_at).set_index("kpi_code")

# ------------------------------------------------------------------ choose the KPI
c1, c2, c3 = st.columns([2, 3, 3])
projects = sorted(k["project_code"].unique())
project = c1.selectbox("1. Project", projects, key="ku_project",
                       index=projects.index(f.project_code) if f.project_code in projects else 0)
LEVEL_TAG = {"General Objective": "GO", "Specific Objective": "SO", "Output": "Output"}
res = r[(r["project_code"] == project) & r["result_code"].isin(k["result_code"])]
res = res.assign(order=res["level"].map({"General Objective": 0, "Specific Objective": 1, "Output": 2})).sort_values(
    ["order", "result_order"])
result = c2.selectbox("2. Result", list(res["result_code"]), key=f"ku_result_{project}",
                      format_func=lambda c: f"{LEVEL_TAG.get(res.set_index('result_code').loc[c, 'level'], '')} {c}: "
                                            f"{str(res.set_index('result_code').loc[c, 'statement'])[:70]}")
ks = k[k["result_code"] == result]
kpi_code = c3.selectbox("3. KPI", list(ks["kpi_code"]), key=f"ku_kpi_{result}",
                        format_func=lambda c: f"{c}: {str(ks.set_index('kpi_code').loc[c, 'indicator'])[:70]}")
row = ks.set_index("kpi_code").loc[kpi_code]

# The value now: the newest dashboard update (made since the workbook in use was added), else the workbook's.
if kpi_code in latest.index:
    now_achieved, now_status = float(latest.loc[kpi_code, "achieved"]), latest.loc[kpi_code, "kpi_status"]
    since = f"updated on the dashboard by {latest.loc[kpi_code, 'updated_by']} on {latest.loc[kpi_code, 'updated_at'][:16].replace('T', ' ')}"
else:
    now_achieved, now_status = float(row["achieved_workbook"]), row["status_workbook"]
    since = f"from the workbook ('Results & KPIs' row {row['source_row']})"

st.markdown(f"**{row['indicator']}**")
ui.tiles([("Target", f"{row['target']:,.4g} {row['unit_original']}", f"baseline {row['baseline']:,.4g}"),
          ("Achieved now", f"{now_achieved:,.4g}", since),
          ("Status now", str(now_status), f"frequency: {row['frequency']}"),
          ("Band now", ui.band_label(row["band"]), "as in the figures (updates appear after 'Update the figures')")])
st.caption(f"Responsible: {ui.roles(pd.Series([row['responsible']])).iloc[0]}. Evidence: {row['evidence']}.")

# ------------------------------------------------------------------ the update
with st.form("kpi_update_form", clear_on_submit=False):
    a, b = st.columns(2)
    achieved = a.number_input(f"New achieved value ({row['unit_original']})", min_value=0.0, value=now_achieved,
                              step=1.0, format="%g")
    status = b.selectbox("New status", arde_store.KPI_STATUSES,
                         index=arde_store.KPI_STATUSES.index(now_status) if now_status in arde_store.KPI_STATUSES else 0)
    target = float(row["target"]) if pd.notna(row["target"]) else 0
    if target:
        st.caption(f"With this value: {achieved / target:.0%} of target.")
    note = st.text_input("Note (evidence or source of the new value)", max_chars=300)
    saved = st.form_submit_button("Save the update", type="primary", disabled=not ready)
if saved:
    try:
        uid = arde_store.add_update({"kpi_code": kpi_code, "achieved": now_achieved, "kpi_status": now_status,
                                     "unit": row["unit_original"]}, achieved, status, note, who)
        st.success(f"Saved as {uid}. A backup was made. Use 'Update the figures now' below so the other pages show it.")
    except arde_store.EntryError as err:
        st.error(str(err))

# ------------------------------------------------------------------ history
st.markdown("#### Change history of this KPI")
hist = pd.DataFrame(arde_store.table("change_history"))
mine = hist[hist["record_id"] == kpi_code] if len(hist) else hist
if not len(mine):
    st.caption("No change made on the dashboard yet: the value is the workbook's.")
else:
    ui.table(pd.DataFrame({"When": mine["changed_at"].str.replace("T", " "), "Who": mine["changed_by"],
                           "What": mine["action"], "Field": mine["field"], "Old": mine["old_value"],
                           "New": mine["new_value"]}).iloc[::-1], "kpi_history")

with st.expander("All KPI updates made on the dashboard"):
    ups = pd.DataFrame(arde_store.table("kpi_updates"))
    if not len(ups):
        st.caption("None yet.")
    else:
        used = ups["updated_at"] > (uploaded_at or "")
        ui.table(pd.DataFrame({"Update": ups["update_id"], "KPI": ups["kpi_code"], "Achieved": ups["achieved"],
                               "Status": ups["kpi_status"], "Was": ups["previous_achieved"],
                               "Status was": ups["previous_status"], "Note": ups["note"], "Who": ups["updated_by"],
                               "When": ups["updated_at"].str.replace("T", " "),
                               "In use": used.map({True: "yes", False: "no: a newer workbook was uploaded"})}
                              ).iloc[::-1], "kpi_updates")

st.divider()
ui.update_figures_button(ready, "the Home, Results and KPIs and Records pages")
ui.footer()
