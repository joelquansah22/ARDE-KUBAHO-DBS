"""Data quality: scores, the rules behind them, sources, officers, quarantine, review queue.

Every table uses plain headers and plain words for problems (settings.yaml: labels), never raw column or rule codes.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

import ui                # first: it makes src/ importable
import measures          # noqa: E402  (src/measures.py: one definition per figure)

ui.filters(sex_applies=False)
st.title("Data quality")
st.markdown("<div class='muted'>This page covers every record in the source files, so the programme, project, district, "
            "date and sex filters do not apply here.</div>", unsafe_allow_html=True)


def records_view(df: pd.DataFrame) -> pd.DataFrame:
    """Quarantine or review-queue rows in plain words, oldest first. Details are left blank when they only repeat
    the problem."""
    problems = df["reasons"].map(ui.issues_in_words)
    details = df["details"].map(ui.details_in_words)
    details = [("" if d.strip().rstrip(".") == p.strip() else d) for d, p in zip(details, problems)]
    return pd.DataFrame({
        "Field officer": df["field_officer"], "Month": df["month"], "Record type": df["entity"].map(ui.entity_label),
        "File": df["source_file"], "Sheet": df["source_sheet"], "Row in file": df["source_row"],
        "Problems": problems, "Details": details})


skipped = ui.query("SELECT * FROM skipped_sheets")
if len(skipped):
    st.error(f"**{len(skipped)} sheet(s) could not be read and are left out of every figure.** Add their column names "
             "to config/source_mappings.yaml and run the pipeline again.")
    ui.table(pd.DataFrame({"File": skipped["source_file"], "Sheet": skipped["source_sheet"],
                           "Record type": skipped["entity"].map(ui.entity_label), "Why": skipped["reason"],
                           "Required columns not found": skipped["missing_required"],
                           "Column headings found": skipped["headers_found"]}), "skipped_sheets")

dims = ui.query("SELECT * FROM dq_dimension_scores")
overall = dims.loc[dims["dimension"] == "overall", "score"].iloc[0]
quarantine = ui.query("SELECT * FROM quarantine")
review = ui.query("SELECT * FROM review_queue")
pending = measures.pending_in_register(ui.query)
ui.tiles([("Overall data-quality score", f"{overall:.1f}%", "average of the six dimensions"),
          ("Records quarantined", f"{len(quarantine):,}", "broke a critical rule; not used until corrected"),
          ("Records to review", f"{len(review):,}", "used, but a person should check them"),
          ("People pending duplicate review", f"{pending:,}",
           "whole register; other pages count only those reached in their selection")])

# ------------------------------------------------------------------ dimensions and the rules behind them
c1, c2 = st.columns([2, 3])
with c1:
    st.markdown("### Score by dimension")
    d = dims[dims["dimension"] != "overall"].sort_values("score").assign(
        dimension=lambda x: x["dimension"].str.capitalize())
    fig = px.bar(d, x="score", y="dimension", orientation="h", text="score", range_x=[0, 105],
                 labels={"score": "Score (%)", "dimension": ""})
    fig.update_traces(marker_color="#1f6f8b", texttemplate="%{text:.1f}%")
    fig.update_layout(height=260, margin=dict(l=0, r=10, t=10, b=0))
    st.plotly_chart(fig, width="stretch")
with c2:
    st.markdown("### Which checks drive the scores")
    rules = ui.query("SELECT * FROM dq_results ORDER BY dimension_impact DESC")
    ui.html_table(pd.DataFrame({
        "What is checked": rules["description"], "Dimension": rules["dimension"].str.capitalize(),
        "Score %": rules["score"], "Records failing / checked": [f"{a:,} / {b:,}" for a, b in
                                                                 zip(rules["records_failed"], rules["records_checked"])],
        "Points off the dimension score": rules["dimension_impact"]}), "dq_checks", max_rows=8,
        widths={"What is checked": "46%"})

# ------------------------------------------------------------------ measures
st.markdown("### Data-quality measures")
info = ui.query("SELECT * FROM dq_info_measures")
ui.html_table(pd.DataFrame({"Measure": info["metric"], "%": info["percent"],
                       "Records meeting the standard": info["numerator"], "Records measured": info["denominator"],
                       "How it is measured": info["note"]}), "dq_measures")

# ------------------------------------------------------------------ by source and officer
st.markdown("### By source file")
src = ui.query("SELECT * FROM dq_by_source_file ORDER BY score")
ui.html_table(pd.DataFrame({"File": src["source_file"], "Sheet": src["source_sheet"],
                           "Record type": src["entity"].map(ui.entity_label), "Field officer": src["field_officer"],
                           "Rows read": src["rows_read"], "Quarantined": src["rows_quarantined"],
                           "To review": src["rows_for_review"], "Clean": src["rows_clean"], "Score %": src["score"]}),
              "dq_by_source_file", max_rows=10)
rule_file = ui.query("""SELECT f.*, r.description FROM dq_rule_results_by_file f JOIN dq_results r USING (rule_id)
                        WHERE f.records_failed > 0 ORDER BY f.score""")
with st.expander("Check results for each file (which check makes a file score low)"):
    ui.table(pd.DataFrame({"File": rule_file["source_file"], "Sheet": rule_file["source_sheet"],
                           "What is checked": rule_file["description"],
                           "Dimension": rule_file["dimension"].str.capitalize(),
                           "Records checked": rule_file["records_checked"],
                           "Records failing": rule_file["records_failed"], "Score %": rule_file["score"],
                           "Critical": rule_file["critical_failures"], "Warning": rule_file["warning_failures"],
                           "Counted only": rule_file["info_failures"]}), "dq_checks_by_file")
st.markdown("### By field officer")
off = ui.query("SELECT * FROM dq_by_field_officer ORDER BY score")
ui.html_table(pd.DataFrame({"Field officer": off["field_officer"], "Rows": off["rows"],
                           "Quarantined": off["rows_quarantined"], "To review": off["rows_for_review"],
                           "Entered late": off["late_entries"], "Score %": off["score"]}), "dq_by_field_officer")

# ------------------------------------------------------------------ quarantine and review queue
c1, c2 = st.columns(2)
with c1:
    st.markdown("### Quarantined records, by reason")
    reasons = (quarantine.assign(reason=quarantine["reasons"].str.split(", ")).explode("reason")
               .groupby("reason").size().sort_values().rename("records").reset_index())
    reasons["reason"] = reasons["reason"].map(ui.issue_label)
    fig = px.bar(reasons, x="records", y="reason", orientation="h", text="records",
                 labels={"reason": "", "records": "Number of records"})
    fig.update_traces(marker_color="#cf222e")
    fig.update_layout(height=320, margin=dict(l=0, r=10, t=10, b=0))
    st.plotly_chart(fig, width="stretch")
    st.caption("A record can break more than one rule, so the bars can add up to more than the records quarantined.")
with c2:
    st.markdown("### Review queue per month")
    budget = ui.SETTINGS["review_budget_minutes_per_month"] // ui.SETTINGS["review_minutes_per_row"]
    monthly = review.groupby("month").size().rename("records").reset_index()
    monthly["month"] = pd.to_datetime(monthly["month"] + "-01")
    fig = px.bar(monthly, x="month", y="records", labels={"month": "", "records": "Records to review"})
    fig.add_hline(y=budget, line_dash="dash", annotation_text=f"one hour a month ({budget} records)")
    fig.update_traces(marker_color="#9a6700")
    fig.update_layout(height=320, margin=dict(l=0, r=10, t=10, b=0))
    ui.month_axis(fig)
    st.plotly_chart(fig, width="stretch")
st.markdown("### Work lists")
officers = sorted(set(quarantine["field_officer"].dropna()) | set(review["field_officer"].dropna()))
who = st.selectbox("Field officer", ["All officers"] + officers, key="dq_officer",
                   help="Show one officer's records, e.g. to send them their list.")
pick = (lambda df: df) if who == "All officers" else (lambda df: df[df["field_officer"] == who])
q_rows, r_rows = pick(quarantine).sort_values("month"), pick(review).sort_values("month")
st.markdown(f"**Quarantined records** ({len(q_rows):,}): correct them in the source Excel file, then run the "
            "pipeline again")
ui.html_table(records_view(q_rows), "quarantine" if who == "All officers" else f"quarantine_{who}", max_rows=12)
st.markdown(f"**Review queue** ({len(r_rows):,}): the records are used, but a person should check them")
ui.html_table(records_view(r_rows), "review_queue" if who == "All officers" else f"review_queue_{who}", max_rows=12)

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
