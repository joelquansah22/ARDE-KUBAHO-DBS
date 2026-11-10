"""Results and KPIs (ARDE/KUBAHO workbook mode): drill down project > General Objective > Specific Objective >
Output > KPIs, with target, achieved, % achieved and band. Filters: area (sidebar), and level, band and status here.

% achieved and the band are recomputed from target and achieved (src/arde_model.py: band), with the workbook's own
thresholds; the workbook's band is shown next to ours. Responsible staff are shown by role, not by name.
"""

import html

import pandas as pd
import plotly.express as px
import streamlit as st

import ui                # first: it makes src/ importable
from arde_model import BAND_ORDER  # noqa: E402

f = ui.arde_filters()
ui.page_header("Results and KPIs", "results_kpis")
ui.how_to_read("results_kpis")
codes = f.project_codes
if not codes:
    ui.no_data()
    st.stop()
IN = ui.in_list(codes)
k = ui.query(f"SELECT * FROM fact_kpi WHERE project_code IN {IN}", *codes)
r = ui.query(f"SELECT * FROM fact_result WHERE project_code IN {IN} ORDER BY project_code, result_order", *codes)
p = ui.query(f"SELECT project_code, project_title, intervention_area FROM dim_project WHERE project_code IN {IN} "
             "ORDER BY project_code", *codes)

# ------------------------------------------------------------------ page filters
c1, c2, c3 = st.columns(3)
levels = c1.multiselect("Result level", ["General Objective", "Specific Objective", "Output"], key="rk_level",
                        placeholder="All levels")
bands = c2.multiselect("Band", [b for b in BAND_ORDER if b in set(k["band"])], key="rk_band", placeholder="All bands")
statuses = c3.multiselect("KPI status", sorted(k["kpi_status"].dropna().unique()), key="rk_status",
                          placeholder="All statuses")
keep = pd.Series(True, index=k.index)
for column, chosen_values in (("result_level", levels), ("band", bands), ("kpi_status", statuses)):
    if chosen_values:
        keep &= k[column].isin(chosen_values)
sel = k[keep]
if not len(sel):
    st.info("No KPI matches these filters. Clear a filter above or in the sidebar.")
    st.stop()

counts = sel["band"].value_counts()
ui.tiles([(ui.band_label(b), f"{int(counts.get(b, 0)):,}", f"of {len(sel):,} KPIs") for b in BAND_ORDER
          if counts.get(b, 0) or b in ("Achieved", "On track", "Needs attention", "Not recorded")])

# ------------------------------------------------------------------ bands by project
st.markdown("#### KPIs by project and band")
by = sel.groupby(["project_code", "band"]).size().reset_index(name="KPIs")
fig = px.bar(by, y="project_code", x="KPIs", color="band", orientation="h",
             category_orders={"band": BAND_ORDER},
             color_discrete_map={b: ui.BAND_STYLE[b][1] for b in BAND_ORDER},
             labels={"project_code": "", "band": "Band"}, height=max(240, 20 * by["project_code"].nunique() + 90))
fig.update_traces(marker_line_width=0)
fig.update_yaxes(automargin=True, autorange="reversed")
ui.legend_on_top(fig)
st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
st.caption("Colours follow the band and every band also has its name in the legend. Not recorded and No target are "
           "grey.")

# ------------------------------------------------------------------ drill-down: one project's results chain
st.markdown("#### Results chain")
projects = [c for c in p["project_code"] if c in set(sel["project_code"])]
chosen = f.project_code if f.project_code in projects else st.selectbox(
    "Project", projects, key="rk_project",
    format_func=lambda c: f"{c}: {p.set_index('project_code').loc[c, 'project_title']}")
pk = sel[sel["project_code"] == chosen].sort_values("kpi_code")
pr = r[r["project_code"] == chosen]


def kpi_table(result_code: str) -> str:
    rows = pk[pk["result_code"] == result_code]
    if not len(rows):
        return ""
    body = "".join(
        f"<tr><td>{html.escape(str(x.kpi_code))}</td><td>{html.escape(str(x.indicator))}</td>"
        f"<td>{html.escape(str(x.unit_original))}</td><td style='text-align:right'>{x.baseline:,.4g}</td>"
        f"<td style='text-align:right'>{x.target:,.4g}</td><td style='text-align:right'>{x.achieved:,.4g}</td>"
        f"<td style='text-align:right'>{ui.pct(x.achievement)}</td><td>{ui.band_html(x.band)}</td>"
        f"<td class='muted'>{html.escape(str(x.band_workbook))}</td><td>{html.escape(str(x.kpi_status))}</td>"
        f"<td class='muted'>{html.escape(str(x.frequency))}</td>"
        f"<td class='muted'>{'updated ' + str(x.updated_at)[:10] + ' by ' + str(x.updated_by) if pd.notna(x.updated_by) else 'row ' + str(x.source_row)}</td></tr>"
        for x in rows.itertuples())
    return ("<div class='tbl-wrap'><table class='tbl'><thead><tr><th>KPI</th><th>Indicator</th><th>Unit</th>"
            "<th>Baseline</th><th>Target</th><th>Achieved</th><th>%</th><th>Band</th><th>Workbook band</th>"
            "<th>Status</th><th>Frequency</th><th>Source</th></tr></thead><tbody>" + body + "</tbody></table></div>")


def show(result, depth: int) -> None:
    indent = 1.4 * depth
    tag = {"General Objective": "GO", "Specific Objective": "SO", "Output": "Output"}.get(result.level, result.level)
    n = int((pk["result_code"] == result.result_code).sum())
    head = (f"<div style='margin-left:{indent}rem;border-left:3px solid {ui.COLOURS['primary']};padding-left:0.5rem;"
            f"margin-top:0.5rem'><b>{tag} {html.escape(str(result.result_code))}</b> · "
            f"<span class='muted'>{html.escape(str(result.status))} · {n} KPI{'s' if n != 1 else ''}</span><br>"
            f"{html.escape(str(result.statement))}</div>")
    st.markdown(head, unsafe_allow_html=True)
    table = kpi_table(result.result_code)
    if table:
        st.markdown(f"<div style='margin-left:{indent + 0.8}rem'>{table}</div>", unsafe_allow_html=True)
    for child in pr[pr["parent_result"] == result.result_code].sort_values("result_order").itertuples():
        show(child, depth + 1)


tops = pr[pr["level"] == "General Objective"].sort_values("result_order")
for go in tops.itertuples():
    show(go, 0)
orphans = pk[~pk["result_code"].isin(pr["result_code"])]
if len(orphans):
    st.warning(f"{len(orphans)} KPIs point to a result that is not in the Results sheet; see Data quality.")

# ------------------------------------------------------------------ the whole selection, for download
with st.expander(f"All {len(sel):,} KPIs in this selection (table and download)"):
    ui.table(pd.DataFrame({
        "Project": sel["project_code"], "Result": sel["result_code"], "Level": sel["result_level"],
        "KPI": sel["kpi_code"], "Indicator": sel["indicator"], "Unit (as written)": sel["unit_original"],
        "Unit (normalised)": sel["unit"], "Baseline": sel["baseline"], "Target": sel["target"],
        "Achieved": sel["achieved"], "% achieved": (100 * sel["achievement"]).round(1), "Band": sel["band"],
        "Workbook band": sel["band_workbook"], "KPI status": sel["kpi_status"], "Frequency": sel["frequency"],
        "Responsible (role)": ui.roles(sel["responsible"]), "Updated by": sel["updated_by"],
        "Register row": sel["source_row"], "KPIs sheet row": sel["kpis_sheet_row"]}), "results_and_kpis", height=360)
ui.footer()
