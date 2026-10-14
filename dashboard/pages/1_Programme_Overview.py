"""Programme overview: headline figures, target versus actual by project, trend, donor report."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import ui

f = ui.filters()
projects = f.project_ids
st.title("Programme overview")
st.markdown(f"<div class='muted'>{f.start:%d %b %Y} to {f.end:%d %b %Y} · {f.scope_text}</div>", unsafe_allow_html=True)

dist_clause, dist_params = ("AND l.district = ?", [f.district]) if f.district else ("", [])
sex_clause, sex_params = ("AND b.sex = ?", [f.sex]) if f.sex else ("", [])

# ------------------------------------------------------------------ headline figures
people = ui.query(f"""
    SELECT COUNT(DISTINCT s.beneficiary_key) AS people,
           COUNT(DISTINCT CASE WHEN b.pending_duplicate_review THEN s.beneficiary_key END) AS pending,
           COUNT(DISTINCT CASE WHEN b.sex = 'female' THEN s.beneficiary_key END) AS women,
           COUNT(DISTINCT CASE WHEN b.sex IS NOT NULL THEN s.beneficiary_key END) AS known_sex
    FROM fact_beneficiary_service s JOIN dim_activity a USING (activity_id)
    JOIN dim_beneficiary b USING (beneficiary_key) LEFT JOIN dim_location l ON l.location_id = b.location_id
    WHERE a.project_id IN {ui.in_list(projects)} AND s.date BETWEEN ? AND ? {dist_clause} {sex_clause}""",
                  *projects, f.start, f.end, *dist_params, *sex_params).iloc[0]
acts = ui.query(f"""
    SELECT COUNT(*) AS done, SUM(cost_rwf) AS spend FROM fact_activity f JOIN dim_activity a USING (activity_id)
    JOIN dim_location l USING (location_id)
    WHERE a.project_id IN {ui.in_list(projects)} AND f.status IN ('completed', 'delayed') AND f.date BETWEEN ? AND ?
    {dist_clause}""", *projects, f.start, f.end, *dist_params).iloc[0]
budget = ui.query(f"SELECT SUM(budget_rwf) AS b FROM dim_project WHERE project_id IN {ui.in_list(projects)}",
                  *projects)["b"].iloc[0]
women_pct = 100 * people["women"] / people["known_sex"] if people["known_sex"] else None
coverage = 100 * people["known_sex"] / people["people"] if people["people"] else None
ui.tiles([
    ("People reached (different people)", f"{int(people['people']):,}",
     f"includes {int(people['pending'])} people pending duplicate review" if people["pending"] else "none pending duplicate review"),
    ("Activities completed", f"{int(acts['done'] or 0):,}", "completed or completed late, in the date range"),
    ("% women (CC-01 definition)", ui.number(women_pct, "percent") if women_pct is not None else "–",
     f"coverage {coverage:.0f}%: people with sex recorded" if coverage is not None and coverage < 100 else
     ("sex filter applied" if f.sex else "")),
    ("Budget spent (activity costs)", ui.money(acts["spend"] or 0, short=True),
     f"{100 * (acts['spend'] or 0) / budget:.0f}% of {ui.money(budget, short=True)} budget" if budget else ""),
])
if f.district:
    st.caption("People are counted in the district where they registered; activities and spending in the district "
               "where the activity took place. Budgets are for whole projects.")

# ------------------------------------------------------------------ target versus actual by project
st.markdown("### Target versus actual by project")
cat = ui.catalogue()
reported = [c for c, i in cat.items() if "reported" in i.get("calculation", {}) and i["availability"] == "available"]
c1, c2 = st.columns([2, 1])
code = c1.selectbox("Indicator", reported, format_func=lambda c: f"{c} {cat[c]['name']}", key="ov_indicator")
years = ui.query("SELECT DISTINCT period FROM indicator_values WHERE period_type = 'fiscal_year' ORDER BY 1")["period"]
year = c2.selectbox("Fiscal year", list(years), index=len(years) - 1, key="ov_year")
district = f.district or "All"
disagg = f"sex={f.sex}" if f.sex and cat[code]["disaggregation"] == "sex" else "total"
tv = ui.query(f"""SELECT v.project_id, p.name, v.target, v.actual, v.pct_achieved, v.status, v.partial_pct_achieved,
                         v.target_note
                  FROM indicator_values v JOIN dim_project p USING (project_id)
                  WHERE v.indicator_code = ? AND v.source = 'reported' AND v.period_type = 'fiscal_year' AND v.period = ?
                    AND v.district = ? AND v.disaggregation = ? AND v.project_id IN {ui.in_list(projects)}""",
              code, year, district, disagg, *projects)
if len(tv):
    tv["label"] = [ui.status_label(s, n) for s, n in zip(tv["status"], tv["target_note"])]
    fig = go.Figure()
    fig.add_bar(name="Actual", x=tv["project_id"], y=tv["actual"], marker_color="#1f6f8b",
                text=tv["label"], textposition="outside", cliponaxis=False)
    fig.add_bar(name="Target", x=tv["project_id"], y=tv["target"], marker_color="#c6d4dc")
    fig.update_layout(barmode="group", height=280, margin=dict(l=10, r=10, t=30, b=10), legend_orientation="h",
                      yaxis_title=cat[code]["unit"])
    st.plotly_chart(fig, width="stretch")
    st.caption("The words above each bar give the status (not only the colour). A missing target bar means the "
               "target is incomplete or not set; see the Indicators page for the partial % achieved.")
else:
    st.info("No reported values for this indicator, year and selection.")

# ------------------------------------------------------------------ trend
st.markdown("### Trend over time")
trend = ui.query(f"""
    SELECT date_trunc('month', s.date) AS month, COUNT(DISTINCT s.beneficiary_key) AS people
    FROM fact_beneficiary_service s JOIN dim_activity a USING (activity_id) JOIN dim_beneficiary b USING (beneficiary_key)
    LEFT JOIN dim_location l ON l.location_id = b.location_id
    WHERE a.project_id IN {ui.in_list(projects)} AND s.date BETWEEN ? AND ? {dist_clause} {sex_clause}
    GROUP BY 1 ORDER BY 1""", *projects, f.start, f.end, *dist_params, *sex_params)
act_trend = ui.query(f"""
    SELECT date_trunc('month', f.date) AS month, COUNT(*) AS activities, SUM(participants_total) AS attendance
    FROM fact_activity f JOIN dim_activity a USING (activity_id) JOIN dim_location l USING (location_id)
    WHERE a.project_id IN {ui.in_list(projects)} AND f.status IN ('completed','delayed') AND f.date BETWEEN ? AND ?
    {dist_clause} GROUP BY 1 ORDER BY 1""", *projects, f.start, f.end, *dist_params)
both = act_trend.merge(trend, on="month", how="outer").sort_values("month")
long = both.melt(id_vars="month", value_vars=["activities", "people"], var_name="measure", value_name="value")
long["measure"] = long["measure"].map({"activities": "Activities completed",
                                       "people": "Different people reached in the month"})
fig = px.line(long, x="month", y="value", color="measure", markers=True, height=260)
fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), legend_orientation="h", legend_title_text="",
                  xaxis_title="", yaxis_title="")
st.plotly_chart(fig, width="stretch")
with st.expander("Show the trend as a table"):
    ui.table(both.assign(month=both["month"].dt.strftime("%Y-%m")), "trend_by_month")

# ------------------------------------------------------------------ donor report
st.markdown("### Generate donor report")
st.caption("A one-page quarterly progress summary for one project, as Excel and PDF. The time taken is recorded "
           "for the evaluation (evaluation/report_generation_log.csv).")
all_projects = ui.query("SELECT project_id, name FROM dim_project ORDER BY 1")
quarters = ui.query("SELECT DISTINCT period, period_start FROM indicator_values WHERE period_type = 'quarter' "
                    "ORDER BY period_start")["period"].tolist()
current, _, _ = ui.current_quarter()
r1, r2, r3 = st.columns([2, 1, 1])
rep_project = r1.selectbox("Project", list(all_projects["project_id"]),
                           index=list(all_projects["project_id"]).index(f.project_id) if f.project_id else 0,
                           format_func=lambda p: f"{p} {all_projects.set_index('project_id').loc[p, 'name']}",
                           key="rep_project")
rep_quarter = r2.selectbox("Quarter", quarters, index=quarters.index(current) if current in quarters else len(quarters) - 1,
                           key="rep_quarter")
if r3.button("Generate donor report", type="primary", width="stretch"):
    import donor_report
    result = donor_report.make_report(rep_project, rep_quarter)
    st.session_state["last_report"] = result
if "last_report" in st.session_state:
    result = st.session_state["last_report"]
    st.success(f"Report ready: generated in {result['seconds']:.2f} seconds ({result['pages']} page PDF).")
    d1, d2 = st.columns(2)
    d1.download_button("⬇ Download Excel", result["excel"].read_bytes(), file_name=result["excel"].name,
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_report_xlsx")
    d2.download_button("⬇ Download PDF", result["pdf"].read_bytes(), file_name=result["pdf"].name,
                       mime="application/pdf", key="dl_report_pdf")
