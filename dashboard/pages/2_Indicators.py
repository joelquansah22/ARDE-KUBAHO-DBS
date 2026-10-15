"""Indicators: one row per indicator with target, actual, % achieved and status; drill-down; reconciliation."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ui                # first: it makes src/ importable
import measures          # noqa: E402  (src/measures.py: one definition per figure)

f = ui.filters()
cat = ui.catalogue()
run = ui.query
st.title("Indicators")
ui.how_to_read("indicators")
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

rows = measures.indicator_rows(run, cat, ptype, period, f)
plist, district, per_project = measures.indicator_scope(f)
project = plist[0] if len(plist) == 1 else None
if per_project:
    st.info("Results are stored for each project, so this view has one row per indicator AND project. Choose a project "
            "in the sidebar (or clear the programme and district filters) for one row per indicator.")
if f.sex:
    st.caption(f"Sex filter: indicators broken down by sex show {f.sex} only; the others show everyone.")


def achieved(r) -> str:
    if pd.notna(r.pct_achieved):
        return f"{r.pct_achieved:.0f}%"
    if pd.notna(r.partial_pct_achieved):
        return f"{r.partial_pct_achieved:.0f}% ({str(r.target_note).replace('partial: ', 'partial, ')})"
    return "–"


st.markdown(f"### {period} · {f.scope_text}")
if len(rows):
    table = pd.DataFrame({
        "Indicator": rows["name"], "Project": rows["project_id"],
        "Target": [ui.number(t, u) for t, u in zip(rows["target"], rows["unit"])],
        "Actual": [(cat[c].get("when_missing", "–").capitalize() if pd.isna(a) else
                    ui.number(a, u) + ("" if s == "reported" else " (worked out)"))
                   for c, a, u, s in zip(rows["indicator_code"], rows["actual"], rows["unit"], rows["source"])],
        "% achieved": [achieved(r) for r in rows.itertuples()],
        "Status": [ui.status_html(s) for s in rows["status"]],
        "Compared with records": [measures.records_comparison(a, r) for a, r in zip(rows["actual"], rows["records_value"])],
        "Coverage": [("" if pd.isna(c) or c >= 100 else f"{c:.0f}% of the data") for c in rows["coverage_pct"]],
    })
    if not per_project:
        table = table.drop(columns="Project")
    ui.html_table(table, f"indicators_{period}".replace("/", "-").replace(" ", "_"), html_columns=("Status",),
                  widths={"Indicator": "30%", "Target": "8%", "Actual": "11%", "% achieved": "13%", "Status": "12%",
                          "Compared with records": "15%", "Coverage": "9%"})
    st.caption("Actual = the monthly reports where the indicator is reported; otherwise '(worked out)' from the "
               "activity, register and report files (see the definitions below). 'Compared with records' is shown where the records count the same thing as the "
               "report (see the reconciliation below). Coverage is shown when a value could only be worked out from "
               "part of the data. WASH-03 and AGR-03 are not shown: their survey data does not exist yet.")
else:
    st.info("No indicator values for this period and selection.")

with st.expander("Indicator definitions (draft, for co-design)"):
    for code, ind in cat.items():
        st.markdown(f"**{ind['name']}** ({code}) · {ind['level']} · {ind['unit']} · {ind['frequency']} · "
                    f"rolls up by {ind.get('aggregation', 'sum')}")
        st.markdown(f"<div class='small'>{' '.join(str(ind['definition']).split())}<br><i>Counting:</i> "
                    f"{' '.join(str(ind.get('counting_rule', '')).split())}<br><i>Availability:</i> {ind['availability']}"
                    "</div>", unsafe_allow_html=True)

# ------------------------------------------------------------------ drill-down
st.markdown("### Drill-down by month")
available = [c for c, i in cat.items() if i["availability"] == "available"]
code = st.selectbox("Indicator", available, format_func=lambda c: cat[c]["name"], key="ind_drill")
disagg = f"sex={f.sex}" if f.sex and cat[code]["disaggregation"] == "sex" else "total"
if project is None:
    st.info("Choose a single project (or no programme and no district) to see the monthly drill-down.")
    monthly = pd.DataFrame()
else:
    monthly = ui.query("""SELECT value_id, period_start, source, actual, target FROM indicator_values
                          WHERE indicator_code = ? AND period_type = 'month' AND project_id = ? AND district = ?
                            AND disaggregation = ? AND period_start BETWEEN ? AND ? ORDER BY period_start""",
                       code, project, district, disagg, f.start, f.end)
if len(monthly):
    # Months whose value includes at least one record that is in the review queue.
    ids = list(monthly["value_id"])
    under_review = ui.query(f"""
        SELECT s.value_id, COUNT(DISTINCT r.source_file || r.source_sheet || r.source_row) AS records,
               string_agg(DISTINCT r.reasons, ', ') AS reasons
        FROM indicator_value_sources s JOIN review_queue r
          ON r.source_file = s.source_file AND r.source_sheet = s.source_sheet AND r.source_row = s.source_row
        WHERE s.value_id IN {ui.in_list(ids)} GROUP BY 1""", *ids)
    monthly = monthly.merge(under_review, on="value_id", how="left")
    fig = go.Figure()
    for source, colour in (("reported", "#1f6f8b"), ("derived", "#e36209")):
        s = monthly[monthly["source"] == source]
        if len(s):
            fig.add_scatter(x=s["period_start"], y=s["actual"], name="Reported" if source == "reported" else "From records",
                            mode="lines+markers", line_color=colour)
    t = monthly[(monthly["source"] == "reported") & monthly["target"].notna()]
    if len(t):
        fig.add_scatter(x=t["period_start"], y=t["target"], name="Target", mode="lines", line=dict(dash="dash", color="#57606a"))
    flagged = monthly[monthly["records"].notna()]
    if len(flagged):
        fig.add_scatter(x=flagged["period_start"], y=flagged["actual"], name="Includes records under review",
                        mode="markers", marker=dict(symbol="diamond-open", size=14, color="#9a6700", line=dict(width=2)),
                        customdata=flagged[["records"]].astype(int),
                        hovertemplate="%{x|%b %Y}: %{customdata[0]} record(s) in the review queue<extra></extra>")
    fig.update_layout(height=290, margin=dict(l=10, r=10, t=10, b=10), legend_orientation="h",
                      yaxis_title=ui.axis_title(code))
    ui.month_axis(fig)
    st.plotly_chart(fig, width="stretch")
    if len(flagged):
        months = ", ".join(f"{pd.Timestamp(m):%b %Y}" for m in sorted(flagged["period_start"].unique()))
        reasons = sorted({c.strip() for r in flagged["reasons"] for c in str(r).split(",")})
        st.caption(f"◇ {len(flagged['period_start'].unique())} months include records in the MEAL officer's review "
                   f"queue (most common: {ui.issue_label(flagged['reasons'].str.split(', ').explode().mode().iloc[0]).lower()})"
                   ". Those values may change once the records are checked; see Data quality for the list.")
elif project is not None:
    st.info("No monthly values for this indicator and selection.")

# ------------------------------------------------------------------ reconciliation
st.markdown("### Reported versus records (reconciliation)")
tol = ui.SETTINGS["indicators"]["reconciliation_tolerance_pct"]
min_diff = ui.SETTINGS["indicators"]["reconciliation_min_difference"]
levels = {c: {"period": "month", **i["calculation"]["derived"].get("reconcile", {})} for c, i in cat.items()
          if i.get("calculation", {}).get("derived", {}).get("like_for_like")}
level_text = "; ".join(f"{cat[c]['name']} ({c}): by {lvl['period']}" for c, lvl in levels.items())
st.markdown(f"<div class='muted'>Where the monthly report and the activity or register records count the same thing, "
            "the two are compared for each project and district, all people together. A gap is flagged for follow-up "
            f"when it is more than {tol}% of the report AND at least {min_diff} apart: it may be over-reporting, "
            "under-reporting, or a recording problem. Comparison level, set per indicator in the catalogue: "
            f"{level_text}. A quarter adds up only the months that have a report.</div>", unsafe_allow_html=True)
rec = measures.reconciliation(run, f.project_ids, f.start, f.end, f.district, f.sex)
if f.sex:
    st.caption("The sex filter does not apply here: gaps are checked on totals. Figures by sex are below, for "
               "information.")
if len(rec):
    n = measures.reconciliation_counts(rec)
    words = ui.LABELS["reconciliation_status"]
    ui.tiles([("Comparisons", f"{n['compared']:,}", "by project, district and month or quarter"),
              (words["within tolerance"], f"{n['within tolerance']:,}", "report and records agree"),
              (words["gap above tolerance"], f"{n['gap above tolerance']:,}", "above the tolerance and minimum"),
              (words["derived only"], f"{n['derived only']:,}", "records exist but no report was received")])
    rec_code = st.selectbox("Indicator", sorted(rec["indicator_code"].unique()), format_func=lambda c: cat[c]["name"],
                            key="rec_code")
    rc = rec[rec["indicator_code"] == rec_code].groupby("period_start")[["reported", "derived"]].sum(min_count=1).reset_index()
    fig = go.Figure()
    fig.add_bar(x=rc["period_start"], y=rc["reported"], name="Reported", marker_color="#1f6f8b")
    fig.add_bar(x=rc["period_start"], y=rc["derived"], name="From records", marker_color="#e36209")
    fig.update_layout(barmode="group", height=270, margin=dict(l=10, r=10, t=10, b=10),
                      yaxis_title=ui.axis_title(rec_code))
    ui.month_axis(fig)
    st.plotly_chart(fig, width="stretch")
    st.caption(f"All projects and districts in the selection added up, by {levels[rec_code]['period']}.")
    gaps = rec[rec["flag"]].sort_values(["period_start", "project_id", "district"])
    gaps_table = pd.DataFrame({
        "Indicator": gaps["indicator_code"].map(lambda c: cat[c]["name"]),
        "Period": [pd.Timestamp(d).strftime("%b %Y") if t == "month" else p
                   for d, t, p in zip(gaps["period_start"], gaps["period_type"], gaps["period"])],
        "Project": gaps["project_id"], "District": gaps["district"],
        "Reported": gaps["reported"].map(lambda x: f"{x:,.0f}"), "Records": gaps["derived"].map(lambda x: f"{x:,.0f}"),
        "What differs": [measures.difference_in_words(r, d) for r, d in zip(gaps["reported"], gaps["derived"])],
        "Report to check": measures.report_rows_behind(run, gaps)})
    st.markdown(f"**Gaps to follow up** ({len(gaps_table)}, most recent first)")
    ui.html_table(gaps_table.iloc[::-1], "reconciliation_gaps_to_follow_up", max_rows=15,
                  widths={"Indicator": "20%", "Period": "9%", "Project": "6%", "District": "8%", "Reported": "7%",
                          "Records": "7%", "What differs": "18%"})
    info = measures.reconciliation_breakdowns(run, f.project_ids, f.start, f.end, f.district)
    if len(info):
        with st.expander("Figures by sex (for information; gaps are not flagged at this level)"):
            info = info[info["period_type"] == info["indicator_code"].map(lambda c: levels[c]["period"])]
            ui.table(pd.DataFrame({
                "Indicator": info["indicator_code"].map(lambda c: cat[c]["name"]), "Period": info["period"],
                "Project": info["project_id"], "District": info["district"],
                "Sex": info["disaggregation"].str.replace("sex=", "").str.capitalize(),
                "Reported": info["reported"], "Records": info["derived"],
                "What differs": [measures.difference_in_words(r, d) for r, d in zip(info["reported"], info["derived"])]
            }), "reconciliation_by_sex_information", height=300)
else:
    st.info("Nothing to compare for this selection.")

ui.footer()          # data last updated, with the source files (on every page, and printed)
