"""Programme overview: headline figures, target versus actual by project, trend, donor report."""

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import ui                # first: it makes src/ importable
import measures          # noqa: E402  (src/measures.py: one definition per figure)

f = ui.filters()
projects = f.project_ids
run = ui.query
st.title("Programme overview")
st.markdown(f"<div class='muted'>{f.start:%d %b %Y} to {f.end:%d %b %Y} · {f.scope_text}</div>", unsafe_allow_html=True)

# ------------------------------------------------------------------ headline figures (one definition each: measures.py)
people = measures.people_reached(run, projects, f.start, f.end, f.district, f.sex)
acts = measures.activities_total(run, projects, f.start, f.end, f.district)
budget = measures.budget_total(run, projects)
women_pct = 100 * people["women"] / people["known_sex"] if people["known_sex"] else None
coverage = 100 * people["known_sex"] / people["people"] if people["people"] else None
ui.tiles([
    ("People reached (different people)", f"{people['people']:,}", ui.pending_note(people, f)),
    ("Activities completed", f"{acts['activities']:,}", "completed or completed late, in the date range"),
    ("% women (CC-01 definition)", ui.number(women_pct, "percent") if women_pct is not None else "–",
     f"coverage {coverage:.0f}%: people with sex recorded" if coverage is not None and coverage < 100 else
     ("sex filter applied" if f.sex else "")),
    ("Budget spent (activity costs)", ui.money(acts["spend"], short=True),
     f"{100 * acts['spend'] / budget:.0f}% of the {ui.money(budget, short=True)} project budgets" if budget else ""),
])
if f.district:
    st.caption("People are counted in the district where they registered; activities and spending in the district "
               "where the activity took place. Budgets are for whole projects.")

# ------------------------------------------------------------------ target versus actual by project
st.markdown("### Target versus actual by project")
cat = ui.catalogue()
reported = [c for c, i in cat.items() if "reported" in i.get("calculation", {}) and i["availability"] == "available"]
c1, c2 = st.columns([2, 1])
code = c1.selectbox("Indicator", reported, format_func=lambda c: cat[c]["name"], key="ov_indicator")
years = ui.query("SELECT DISTINCT period FROM indicator_values WHERE period_type = 'fiscal_year' ORDER BY 1")["period"]
year = c2.selectbox("Fiscal year", list(years), index=len(years) - 1, key="ov_year")
district = f.district or "All"
disagg = f"sex={f.sex}" if f.sex and cat[code]["disaggregation"] == "sex" else "total"
tv = ui.query(f"""SELECT v.project_id, p.name, v.target, v.actual, v.pct_achieved, v.status, v.partial_pct_achieved,
                         v.target_note, v.partial_target, v.partial_actual
                  FROM indicator_values v JOIN dim_project p USING (project_id)
                  WHERE v.indicator_code = ? AND v.source = 'reported' AND v.period_type = 'fiscal_year' AND v.period = ?
                    AND v.district = ? AND v.disaggregation = ? AND v.project_id IN {ui.in_list(projects)}""",
              code, year, district, disagg, *projects)
if len(tv):
    tv["label"] = [ui.status_label(s) + (f" {p:.0f}%" if p == p and p is not None else "")
                   for s, p in zip(tv["status"], tv["pct_achieved"].fillna(tv["partial_pct_achieved"]))]
    partial = tv["target"].isna() & tv["partial_target"].notna()
    fig = go.Figure()
    fig.add_bar(name="Actual", x=tv["project_id"], y=tv["actual"], marker_color="#1f6f8b",
                text=tv["label"], textposition="outside", cliponaxis=False,
                hovertemplate="%{x}: actual %{y:,.0f}<extra></extra>")
    full = tv[~partial]
    fig.add_bar(name="Target", x=full["project_id"], y=full["target"], marker_color="#c6d4dc",
                hovertemplate="%{x}: target %{y:,.0f}<extra></extra>")
    part = tv[partial]
    if len(part):
        notes = [str(n).replace("partial: ", "") for n in part["target_note"]]
        fig.add_bar(name="Partial target (months that have one)", x=part["project_id"], y=part["partial_target"],
                    marker=dict(color="#e7edf1", line=dict(color="#57606a", width=1), pattern_shape="/"),
                    text=[f"target for {n}" for n in notes], textposition="inside", insidetextanchor="end",
                    customdata=part["partial_actual"],
                    hovertemplate="%{x}: target %{y:,.0f} (%{text}); actual in those months %{customdata:,.0f}"
                                  "<extra></extra>")
    fig.update_layout(barmode="group", height=300, margin=dict(l=10, r=10, t=30, b=10), legend_orientation="h",
                      yaxis_title=ui.axis_title(code))
    ui.legend_on_top(fig)
    st.plotly_chart(fig, width="stretch")
    st.caption("The words above each bar give the status (not only the colour). Where some months have no target, "
               "the hatched bar is the target for the months that DO have one, and the % compares it with the actual "
               "for those same months.")
else:
    st.info("No reported values for this indicator, year and selection.")

# ------------------------------------------------------------------ trend
st.markdown("### Trend over time")
trend = measures.people_by_month(run, projects, f.start, f.end, f.district, f.sex)
act_trend = ui.query(f"""
    SELECT date_trunc('month', f.date) AS month, COUNT(*) AS activities
    FROM fact_activity f JOIN dim_activity a USING (activity_id) JOIN dim_location l USING (location_id)
    WHERE a.project_id IN {ui.in_list(projects)} AND f.status IN ('completed','delayed') AND f.date BETWEEN ? AND ?
    {"AND l.district = ?" if f.district else ""} GROUP BY 1 ORDER BY 1""",
                     *projects, f.start, f.end, *([f.district] if f.district else []))
both = act_trend.merge(trend, on="month", how="outer").sort_values("month")
long = both.melt(id_vars="month", value_vars=["activities", "people"], var_name="measure", value_name="value")
long["measure"] = long["measure"].map({"activities": "Activities completed",
                                       "people": "Different people served in the month (not cumulative)"})
fig = px.line(long, x="month", y="value", color="measure", markers=True, height=270)
fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), legend_orientation="h", legend_title_text="",
                  yaxis_title="Number of people or activities")
ui.month_axis(fig)
st.plotly_chart(fig, width="stretch")
st.caption("Each month counts the different people who received a service that month; someone served in two months "
           "counts in both months. The first months are lower because people are registered as the projects start.")
with st.expander("Show the trend as a table"):
    ui.table(both.assign(month=both["month"].dt.strftime("%b %Y")).rename(columns={
        "month": "Month", "activities": "Activities completed", "people": "Different people served"}),
        "trend_by_month")

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
