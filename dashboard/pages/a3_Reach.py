"""Reach (ARDE/KUBAHO workbook mode): direct and indirect reach by project and intervention area, ONE CHART PER UNIT
TYPE (people, households, organisations, other).

Rule: reach is never added across units. Within a chart each unit is its own bar colour, and totals are given unit
by unit (src/arde_model.py: totals_by_unit). There is no grand total anywhere on this page. Women/men rows may
overlap people rows in the same project; they are shown separately and flagged on the Data quality page.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

import ui                # first: it makes src/ importable
from arde_model import totals_by_unit  # noqa: E402

f = ui.arde_filters()
ui.page_header("Reach", "reach")
ui.how_to_read("reach")
codes = f.project_codes
if not codes:
    ui.no_data()
    st.stop()
IN = ui.in_list(codes)
b = ui.query(f"""SELECT r.*, p.intervention_area FROM fact_reach r JOIN dim_project p USING (project_code)
                 WHERE r.project_code IN {IN}""", *codes)
if not len(b):
    ui.no_data()
    st.stop()
flagged = set(ui.query("SELECT record_key FROM dq_rule_results WHERE rule = 'reach_possible_double_count'")["record_key"])
b["key"] = b["project_code"] + " / " + b["category"].astype(str)
b["possible_overlap"] = b["key"].isin(flagged)

reach_types = st.radio("Reach", ["Direct", "Indirect", "Both"], horizontal=True, key="reach_type")
shown = b if reach_types == "Both" else b[b["reach_type"] == reach_types]

TYPE_TITLES = {"people": "People", "households": "Households", "organisations": "Organisations (cooperatives, "
               "groups, schools, clubs...)", "other": "Other units"}
for kind in ["people", "households", "organisations", "other"]:
    part = shown[shown["unit_type"] == kind]
    if not len(part):
        continue
    st.markdown(f"#### {TYPE_TITLES[kind]}")
    left, right = st.columns([3, 2])
    with left:
        # One unit at a time: a bar per project, so no bar ever mixes units.
        units = list(part.groupby("unit")["count"].sum().sort_values(ascending=False).index)
        unit = st.radio("Unit", units, horizontal=True, key=f"reach_unit_{kind}") if len(units) > 1 else units[0]
        by = (part[part["unit"] == unit].groupby(["project_code", "reach_type"], as_index=False)["count"].sum()
              .sort_values("count"))
        fig = px.bar(by, y="project_code", x="count", color="reach_type", barmode="group", orientation="h",
                     text="count", labels={"project_code": "", "count": f"Number of {unit}", "reach_type": "Reach"},
                     color_discrete_map={"Direct": ui.CHART[0], "Indirect": ui.COMPARE},
                     height=max(200, 26 * by["project_code"].nunique() + 90))
        fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside", cliponaxis=False)
        fig.update_yaxes(automargin=True)
        ui.legend_on_top(fig)
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key=f"reach_{kind}")
    with right:
        tot = totals_by_unit(part)
        area = part.groupby(["intervention_area", "reach_type", "unit"], as_index=False)["count"].sum()
        st.markdown("**Totals, unit by unit** (never added across units)")
        ui.table(tot.rename(columns={"reach_type": "Reach", "unit_type": "Unit type", "unit": "Unit",
                                     "count": "Total"}), f"reach_totals_{kind}")
        st.markdown("**By intervention area**")
        ui.table(area.rename(columns={"intervention_area": "Area", "reach_type": "Reach", "unit": "Unit",
                                      "count": "Total"}), f"reach_by_area_{kind}")
    if kind == "people" and part["possible_overlap"].any():
        st.caption(f"{int(part['possible_overlap'].sum())} women/men (or similar) rows sit next to 'people' rows in "
                   "the same project and may already be counted in them: see Data quality, possible double counting.")

# ------------------------------------------------------------------ the Projects sheet's own figure, for comparison
st.markdown("#### Compared with the Projects sheet")
p = ui.query(f"SELECT project_code, intervention_area, direct_beneficiaries, indirect_beneficiaries FROM dim_project "
             f"WHERE project_code IN {IN} ORDER BY project_code", *codes)
people = b[b["is_headline_people"]].pivot_table(index="project_code", columns="reach_type", values="count",
                                                 aggfunc="sum")
cmp = pd.DataFrame({
    "Project": p["project_code"], "Area": p["intervention_area"],
    "Projects sheet: direct": p["direct_beneficiaries"],
    "Beneficiaries sheet: direct people rows": p["project_code"].map(people.get("Direct", pd.Series(dtype=float))),
    "Projects sheet: indirect": p["indirect_beneficiaries"],
    "Beneficiaries sheet: indirect people rows": p["project_code"].map(people.get("Indirect", pd.Series(dtype=float)))})
ui.table(cmp, "reach_projects_sheet_comparison")
st.caption("The workbook's own dashboard adds the Projects sheet's Direct Beneficiaries column. That column is not "
           "broken down by unit, so whether it counts people only is a question for ARDE/KUBAHO "
           "(docs/partner_questions.md).")

with st.expander(f"All {len(shown):,} reach rows (table and download)"):
    ui.table(pd.DataFrame({"Project": shown["project_code"], "Area": shown["intervention_area"],
                           "Category (as written)": shown["category"], "Reach": shown["reach_type"],
                           "Count": shown["count"], "Unit (as written)": shown["unit_original"],
                           "Unit (normalised)": shown["unit"], "Unit type": shown["unit_type"],
                           "May overlap people rows": shown["possible_overlap"].map({True: "yes", False: ""}),
                           "Beneficiaries row": shown["source_row"]}), "reach_rows", height=320)
ui.footer()
