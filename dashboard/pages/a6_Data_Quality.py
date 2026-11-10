"""Data quality (ARDE/KUBAHO workbook mode): this format's rules (config/arde_format.yaml: rules), the review
queue, the values held back, and how the workbook's own Dashboard and Data Quality figures compare with ours.

Rules FLAG; none changes a value in the workbook. Held back = not used in the figures until corrected in the
workbook (for example a budget used % of 5,000%). Review = used, but someone should check it. Info = reported only.
"""

import pandas as pd
import streamlit as st

import ui                # first: it makes src/ importable

f = ui.arde_filters()
ui.page_header("Data quality", "arde_data_quality")
ui.how_to_read("arde_data_quality")
codes = f.project_codes
IN = ui.in_list(codes)
LEVEL = {"held_back": "Held back", "review": "For review", "info": "Information"}

summary = ui.query("SELECT * FROM dq_rule_summary")
flags = ui.query(f"SELECT * FROM dq_rule_results WHERE project_code IS NULL OR project_code IN {IN}", *codes)
score = float(ui.query("SELECT dq_score FROM run_info")["dq_score"].iloc[0])
n = flags["level"].value_counts()
ui.tiles([("Data-quality score", f"{score:.1f}%", "whole workbook: average pass rate of the held-back and review "
                                                    "checks"),
          ("Held back", f"{int(n.get('held_back', 0)):,}", "values not used until corrected in the workbook"),
          ("For review", f"{int(n.get('review', 0)):,}", "used, but to be checked"),
          ("Information", f"{int(n.get('info', 0)):,}", "reported only")])
st.caption(f"Lists below follow the sidebar filters ({f.scope_text}); the score and the table of checks cover the "
           "whole workbook.")

# ------------------------------------------------------------------ every check
st.markdown("#### The checks")
table = summary.assign(level=summary["level"].map(LEVEL))
ui.table(pd.DataFrame({"Check": table["label"], "Kind": table["level"], "Records checked": table["checked"],
                       "Flagged": table["flagged"], "Pass rate (%)": table["pass_rate"].round(1)}), "dq_checks")

# ------------------------------------------------------------------ lists
tabs = st.tabs([f"Held back ({int(n.get('held_back', 0))})", f"Review queue ({int(n.get('review', 0))})",
                f"Information ({int(n.get('info', 0))})", "The workbook's own figures", "Source of truth"])
for tab, level in zip(tabs[:3], ["held_back", "review", "info"]):
    with tab:
        part = flags[flags["level"] == level]
        if not len(part):
            st.markdown("Nothing in this selection.")
            continue
        labels = ["All checks"] + list(part["label"].value_counts().index)
        chosen = st.selectbox("Check", labels, key=f"dq_rule_{level}",
                              format_func=lambda x: x if x == "All checks" else f"{x} ({(part['label'] == x).sum()})")
        rows = part if chosen == "All checks" else part[part["label"] == chosen]
        ui.table(pd.DataFrame({"Check": rows["label"], "Record": rows["record_key"], "Project": rows["project_code"],
                               "What was found": rows["detail"], "Sheet": rows["source_sheet"],
                               "Row in Excel": rows["source_row"]}), f"dq_{level}", height=360)
        if level == "held_back":
            st.caption("Correct these in the workbook, then upload it again (Upload Excel page).")
with tabs[3]:
    figs = ui.query("SELECT * FROM workbook_figures_comparison")
    figs["workbook_value"] = figs["workbook_value"].map(lambda v: "" if pd.isna(v) else f"{v:,.3g}" if v < 1 else f"{v:,.0f}")
    figs["our_value"] = figs["our_value"].map(lambda v: "" if pd.isna(v) else f"{v:,.3g}" if v < 1 else f"{v:,.0f}")
    ui.html_table(figs.rename(columns={"sheet": "Sheet", "figure": "Figure", "workbook_value": "Workbook",
                                       "our_value": "Ours", "rebuilt": "Same?", "how": "How it is worked out"}),
                  "workbook_figures", widths={"How it is worked out": "45%"})
    st.caption("'KPIs not recorded': the workbook counts only KPIs whose register band is 'Not recorded' (target 0 "
               "or blank); KPIs not started with nothing achieved get the band 'Needs attention' there. We count "
               "those as not recorded. Both are shown; the dashboard uses ours.")
with tabs[4]:
    sot = ui.query("SELECT * FROM source_of_truth_comparison")
    ui.html_table(sot.rename(columns={"comparison": "Comparison", "field": "Field", "compared": "Rows compared",
                                      "differ": "Differ", "examples": "Examples", "note": "Note"}),
                  "source_of_truth", widths={"Examples": "30%"})
    st.markdown("**Decision:** KPI values come from the working register ('Results & KPIs'); the results chain "
                "comes from the Results sheet (it also has the results without a KPI, and their descriptions). See "
                "the decision log, 10 November 2026.")
ui.footer()
