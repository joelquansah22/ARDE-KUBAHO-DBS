"""Data quality: scores, the rules behind them, sources, officers, quarantine, review queue."""

import pandas as pd
import plotly.express as px
import streamlit as st

import ui

ui.filters(sex_applies=False)
st.title("Data quality")
skipped = ui.query("SELECT * FROM skipped_sheets")
if len(skipped):
    st.error(f"**{len(skipped)} sheet(s) could not be read and are left out of every figure.** Add their column names "
             "to config/source_mappings.yaml and run the pipeline again.")
    ui.table(skipped, "skipped_sheets")

dims = ui.query("SELECT * FROM dq_dimension_scores")
overall = dims.loc[dims["dimension"] == "overall", "score"].iloc[0]
quarantine = ui.query("SELECT * FROM quarantine")
review = ui.query("SELECT * FROM review_queue")
pending = ui.query("SELECT SUM(CASE WHEN pending_duplicate_review THEN 1 ELSE 0 END) AS n FROM dim_beneficiary")["n"].iloc[0]
ui.tiles([("Overall data-quality score", f"{overall:.1f}%", "average of the six dimensions"),
          ("Records quarantined", f"{len(quarantine):,}", "broke a critical rule; not used until corrected"),
          ("Records to review", f"{len(review):,}", "used, but a person should check them"),
          ("People pending duplicate review", f"{int(pending or 0):,}", "people counts may be slightly high")])

# ------------------------------------------------------------------ dimensions and the rules behind them
c1, c2 = st.columns([2, 3])
with c1:
    st.markdown("### Score by dimension")
    d = dims[dims["dimension"] != "overall"].sort_values("score")
    fig = px.bar(d, x="score", y="dimension", orientation="h", text="score", range_x=[0, 105],
                 labels={"score": "Score (%)", "dimension": ""})
    fig.update_traces(marker_color="#1f6f8b", texttemplate="%{text:.1f}%")
    fig.update_layout(height=260, margin=dict(l=0, r=10, t=10, b=0))
    st.plotly_chart(fig, width="stretch")
with c2:
    st.markdown("### Which rules drive the scores")
    rules = ui.query("SELECT * FROM dq_results ORDER BY dimension_impact DESC")
    ui.table(pd.DataFrame({
        "Rule": rules["rule_id"], "Dimension": rules["dimension"], "What it checks": rules["description"],
        "Score %": rules["score"], "Failed / checked": [f"{a:,} / {b:,}" for a, b in
                                                        zip(rules["records_failed"], rules["records_checked"])],
        "Points off dimension": rules["dimension_impact"]}), "dq_rules", height=260)

# ------------------------------------------------------------------ measures
st.markdown("### Data-quality measures")
measures = ui.query("SELECT * FROM dq_info_measures")
ui.table(pd.DataFrame({"Measure": measures["metric"], "%": measures["percent"],
                       "Meets the standard": measures["numerator"], "Measured": measures["denominator"],
                       "How it is measured": measures["note"]}), "dq_measures")

# ------------------------------------------------------------------ by source and officer
c1, c2 = st.columns(2)
with c1:
    st.markdown("### By source file")
    src = ui.query("SELECT * FROM dq_by_source_file ORDER BY score")
    ui.table(src.rename(columns={"source_file": "File", "source_sheet": "Sheet", "score": "Score %"}), "dq_by_source_file",
             height=300)
    rule_file = ui.query("SELECT * FROM dq_rule_results_by_file WHERE records_failed > 0 ORDER BY score")
    with st.expander("Rule results for each file (which rule makes a file score low)"):
        ui.table(rule_file, "dq_rule_results_by_file")
with c2:
    st.markdown("### By field officer")
    off = ui.query("SELECT * FROM dq_by_field_officer ORDER BY score")
    ui.table(off.rename(columns={"field_officer": "Officer", "score": "Score %"}), "dq_by_field_officer")

# ------------------------------------------------------------------ quarantine and review queue
c1, c2 = st.columns(2)
with c1:
    st.markdown("### Quarantined records, by reason")
    reasons = (quarantine.assign(reason=quarantine["reasons"].str.split(", ")).explode("reason")
               .groupby("reason").size().sort_values().rename("records").reset_index())
    fig = px.bar(reasons, x="records", y="reason", orientation="h", text="records", labels={"reason": ""})
    fig.update_traces(marker_color="#cf222e")
    fig.update_layout(height=320, margin=dict(l=0, r=10, t=10, b=0))
    st.plotly_chart(fig, width="stretch")
with c2:
    st.markdown("### Review queue per month")
    budget = ui.SETTINGS["review_budget_minutes_per_month"] // ui.SETTINGS["review_minutes_per_row"]
    monthly = review.groupby("month").size().rename("records").reset_index()
    fig = px.bar(monthly, x="month", y="records", labels={"month": "", "records": "Records to review"})
    fig.add_hline(y=budget, line_dash="dash", annotation_text=f"one hour a month ({budget} records)")
    fig.update_traces(marker_color="#9a6700")
    fig.update_layout(height=320, margin=dict(l=0, r=10, t=10, b=0))
    st.plotly_chart(fig, width="stretch")
st.markdown("**Quarantined records** (correct them in the source Excel file, then run the pipeline again)")
ui.table(quarantine, "quarantine", height=240)
st.markdown("**Review queue**")
ui.table(review, "review_queue", height=240)

# ------------------------------------------------------------------ before and after
st.markdown("### What cleaning changed")
issues_file = ui.resolve_path("staging") / "issues.parquet"
if issues_file.exists():
    issues = pd.read_parquet(issues_file, columns=["issue_code", "action"])
    summary = issues.groupby("action").size().rename("records").reset_index()
    words = {"fixed": "Corrected automatically", "flagged": "Flagged (critical, warning or counted)",
             "removed": "Removed (blank, totals or duplicate rows)"}
    ui.tiles([(words.get(r.action, r.action), f"{r.records:,}") for r in summary.itertuples()])
    st.caption("The full before/after comparison (raw files against cleaned data, for the same records) is added "
               "in Phase 7 (evaluate.py).")
