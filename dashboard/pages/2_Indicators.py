"""Indicators: one row per indicator with target, actual, % achieved and status; drill-down; reconciliation."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ui

f = ui.filters()
cat = ui.catalogue()
st.title("Indicators")
tl = ui.SETTINGS["traffic_light"]
st.markdown(f"<div class='muted'>Status (shown with a symbol and in words): ✔ on track {tl['on_track_min']}% or more of "
            f"target · ▲ at risk {tl['at_risk_min']} to {tl['on_track_min'] - 1}% · ✖ off track below {tl['at_risk_min']}% · "
            "◔ target incomplete (some months have no target; no colour) · – no target set. "
            "<b>Draft indicators, for co-design with ARDE/KUBAHO staff.</b></div>", unsafe_allow_html=True)

# ------------------------------------------------------------------ period and scope
labels = {"quarter": "Quarter", "fiscal_year": "Fiscal year", "month": "Month"}
c1, c2 = st.columns([1, 2])
ptype = c1.selectbox("Period", list(labels), format_func=labels.get, key="ind_ptype")
periods = ui.query("SELECT DISTINCT period, period_start FROM indicator_values WHERE period_type = ? "
                   "ORDER BY period_start", ptype)
current, _, _ = ui.current_quarter()
default = (list(periods["period"]).index(current) if ptype == "quarter" and current in list(periods["period"])
           else len(periods) - 1)
period = c2.selectbox("Which", list(periods["period"]), index=default, key="ind_period")

# Values exist for one project and district, one project across districts, and all projects together.
# A programme, or a district with no project chosen, is shown as one row per project.
district = f.district or "All"
if f.project_id:
    plist = [f.project_id]
elif f.programme_id or f.district:
    plist = f.project_ids
    st.info("Showing one row per project. Choose a project in the sidebar for a single row per indicator.")
else:
    plist = ["All"]
project = plist[0] if len(plist) == 1 else None
rows = ui.query(f"""
    SELECT v.*, i.name FROM indicator_values v JOIN dim_indicator i USING (indicator_id)
    WHERE v.period_type = ? AND v.period = ? AND v.district = ? AND v.project_id IN {ui.in_list(plist)}
    ORDER BY v.indicator_code, v.project_id, v.source DESC""", ptype, period, district, *plist)
want = [f"sex={f.sex}" if f.sex else "total"]
rows = rows[rows["disaggregation"].isin(want) | ((rows["disaggregation"] == "total") &
                                                 ~rows["indicator_code"].map(lambda c: cat[c]["disaggregation"] == "sex"))]
if f.sex:
    st.caption(f"Sex filter: indicators broken down by sex show {f.sex} only; the others show everyone.")


def achieved(r) -> str:
    if pd.notna(r.pct_achieved):
        return f"{r.pct_achieved:.0f}%"
    if pd.notna(r.partial_pct_achieved):
        return f"{r.partial_pct_achieved:.0f}% ({str(r.target_note).replace('partial: ', 'partial, ')})"
    return "–"


table = pd.DataFrame({
    "Code": rows["indicator_code"], "Indicator": rows["name"], "Project": rows["project_id"],
    "Source": rows["source"].str.capitalize(),
    "Target": [ui.number(t, u) for t, u in zip(rows["target"], rows["unit"])],
    "Actual": [ui.number(a, u) for a, u in zip(rows["actual"], rows["unit"])],
    "% achieved": [achieved(r) for r in rows.itertuples()],
    "Status": [ui.status_label(s) for s in rows["status"]],
    "Coverage": [("" if pd.isna(c) or c >= 100 else f"{c:.0f}% of the data") for c in rows["coverage_pct"]],
})
if len(plist) == 1:
    table = table.drop(columns="Project")
st.markdown(f"### {period} · {f.scope_text}")
if len(table):
    ui.table(table, f"indicators_{period}".replace("/", "-").replace(" ", "_"), column_config={
        "Code": st.column_config.TextColumn(width=70), "Indicator": st.column_config.TextColumn(width=330),
        "Source": st.column_config.TextColumn(width=75), "Target": st.column_config.TextColumn(width=80),
        "Actual": st.column_config.TextColumn(width=90),
        "% achieved": st.column_config.TextColumn(width=190), "Status": st.column_config.TextColumn(width=150),
        "Coverage": st.column_config.TextColumn(width=110)})
    st.caption("Coverage is shown when a value could only be worked out from part of the data (for example "
               "activities whose timing can be checked). Outcome indicators WASH-03 and AGR-03 are not shown: their "
               "survey data does not exist yet.")
else:
    st.info("No indicator values for this period and selection.")

with st.expander("Indicator definitions (draft, for co-design)"):
    for code, ind in cat.items():
        st.markdown(f"**{code} {ind['name']}** · {ind['level']} · {ind['unit']} · {ind['frequency']} · "
                    f"rolls up by {ind.get('aggregation', 'sum')}")
        st.markdown(f"<div class='small'>{' '.join(str(ind['definition']).split())}<br><i>Counting:</i> "
                    f"{' '.join(str(ind.get('counting_rule', '')).split())}<br><i>Availability:</i> {ind['availability']}"
                    "</div>", unsafe_allow_html=True)

# ------------------------------------------------------------------ drill-down
st.markdown("### Drill-down by month")
available = [c for c, i in cat.items() if i["availability"] == "available"]
code = st.selectbox("Indicator", available, format_func=lambda c: f"{c} {cat[c]['name']}", key="ind_drill")
disagg = f"sex={f.sex}" if f.sex and cat[code]["disaggregation"] == "sex" else "total"
if project is None:
    st.info("Choose a single project (or no programme and no district) to see the monthly drill-down.")
    monthly = pd.DataFrame()
else:
    monthly = ui.query("""SELECT period_start, source, actual, target FROM indicator_values
                          WHERE indicator_code = ? AND period_type = 'month' AND project_id = ? AND district = ?
                            AND disaggregation = ? AND period_start BETWEEN ? AND ? ORDER BY period_start""",
                       code, project, district, disagg, f.start, f.end)
if len(monthly):
    fig = go.Figure()
    for source, colour in (("reported", "#1f6f8b"), ("derived", "#e36209")):
        s = monthly[monthly["source"] == source]
        if len(s):
            fig.add_scatter(x=s["period_start"], y=s["actual"], name=f"{source.capitalize()} actual",
                            mode="lines+markers", line_color=colour)
    t = monthly[(monthly["source"] == "reported") & monthly["target"].notna()]
    if len(t):
        fig.add_scatter(x=t["period_start"], y=t["target"], name="Target", mode="lines", line=dict(dash="dash", color="#57606a"))
    fig.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10), legend_orientation="h",
                      yaxis_title=cat[code]["unit"])
    st.plotly_chart(fig, width="stretch")
elif project is not None:
    st.info("No monthly values for this indicator and selection.")

# ------------------------------------------------------------------ reconciliation
st.markdown("### Reported versus records (reconciliation)")
tol = ui.SETTINGS["indicators"]["reconciliation_tolerance_pct"]
st.markdown(f"<div class='muted'>Where the monthly report and the activity or register records count the same thing, "
            f"the two are compared month by month. A gap of more than {tol}% is flagged for follow-up: it may be "
            "over-reporting, under-reporting, or a recording problem. WASH-01 is compared with people served on "
            "water-point activities; AGR-01 with different registered training participants.</div>",
            unsafe_allow_html=True)
rec = ui.query(f"""SELECT * FROM indicator_reconciliation WHERE district <> 'All' AND project_id IN {ui.in_list(f.project_ids)}
                   AND period_start BETWEEN ? AND ? {'AND district = ?' if f.district else ''}""",
               *f.project_ids, f.start, f.end, *([f.district] if f.district else []))
rec = rec[rec["disaggregation"].isin(["total", f"sex={f.sex}"] if f.sex else ["total"])]
if len(rec):
    summary = rec.groupby(["indicator_code", "status"]).size().unstack(fill_value=0)
    m1, m2, m3 = st.columns(3)
    m1.markdown(ui.tile("Months compared", f"{len(rec):,}"), unsafe_allow_html=True)
    m2.markdown(ui.tile("✖ Gaps above tolerance", f"{int(rec['flag'].sum()):,}"), unsafe_allow_html=True)
    m3.markdown(ui.tile("✔ Within tolerance", f"{int((rec['status'] == 'within tolerance').sum()):,}"),
                unsafe_allow_html=True)
    rec_code = st.selectbox("Indicator", sorted(rec["indicator_code"].unique()), key="rec_code")
    rc = rec[rec["indicator_code"] == rec_code].groupby("period_start")[["reported", "derived"]].sum(min_count=1).reset_index()
    fig = go.Figure()
    fig.add_bar(x=rc["period_start"], y=rc["reported"], name="Reported", marker_color="#1f6f8b")
    fig.add_bar(x=rc["period_start"], y=rc["derived"], name="From records", marker_color="#e36209")
    fig.update_layout(barmode="group", height=260, margin=dict(l=10, r=10, t=10, b=10), legend_orientation="h")
    st.plotly_chart(fig, width="stretch")
    gaps = rec[rec["flag"]].sort_values(["period_start", "project_id", "district"])
    gaps_table = pd.DataFrame({
        "Indicator": gaps["indicator_code"], "Month": gaps["period"], "Project": gaps["project_id"],
        "District": gaps["district"], "Breakdown": gaps["disaggregation"], "Reported": gaps["reported"],
        "From records": gaps["derived"], "Difference": gaps["difference"],
        "% difference": gaps["pct_difference"].map(lambda x: "–" if pd.isna(x) else f"{x:+.0f}%"),
        "Status": "✖ Gap above tolerance"})
    st.markdown("**Flagged gaps** (months to follow up)")
    ui.table(gaps_table, "reconciliation_flagged_gaps", height=260)
else:
    st.info("No months to compare for this selection.")
