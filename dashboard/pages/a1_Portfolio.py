"""Portfolio (ARDE/KUBAHO workbook mode): projects by intervention area and status, the project timeline, budgets in
their own currency with an RWF estimate, budget used and progress (impossible values shown as "invalid, check").

Money is never added across currencies: totals are per currency, and only the RWF ESTIMATES are added together
(always marked ≈). Managers are shown by role, not by name.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

import ui                # first: it makes src/ importable

f = ui.arde_filters()
ui.page_header("Portfolio", "portfolio")
ui.how_to_read("portfolio")
codes = f.project_codes
if not codes:
    ui.no_data()
    st.stop()
IN = ui.in_list(codes)
# One colour per status on every chart of this page.
STATUS_COLOURS = {"Completed": ui.CHART[0], "On track": ui.CHART[1], "Active": ui.CHART[2]}
p = ui.query(f"SELECT * FROM dim_project WHERE project_code IN {IN} ORDER BY start_date", *codes)
funds = ui.query(f"""SELECT project_code, currency, SUM(funds) AS funds, SUM(funds_rwf_estimate) AS funds_rwf,
                     COUNT(*) AS activities FROM fact_project_activity WHERE project_code IN {IN} GROUP BY 1, 2""", *codes)

# ------------------------------------------------------------------ totals per currency
# One tile per currency, side by side (never added across currencies). An RWF total of everything appears only
# when every budget could be converted with a BNR rate entered in settings.
tiles = ui.currency_tiles(p, "approved_budget", "Approved budgets", "projects")
foreign = p[p["currency"] != "RWF"]
if len(foreign) and foreign["budget_rwf_estimate"].notna().all():
    tiles.append(("All budgets, RWF estimate", ui.rwf_estimate(p["budget_rwf_estimate"].sum()),
                  "at BNR annual rates for each start year"))
ui.tiles(tiles)
if len(foreign) and not foreign["budget_rwf_estimate"].notna().all():
    st.caption("Budgets are shown in their own currency. No RWF total is given until BNR exchange rates are entered "
               "in config/settings.yaml (arde: exchange_rates).")

# ------------------------------------------------------------------ by area and status
left, right = st.columns([2, 3])
with left:
    st.markdown("#### Projects by intervention area and status")
    counts = p.groupby(["intervention_area", "status"]).size().reset_index(name="Projects")
    fig = px.bar(counts, y="intervention_area", x="Projects", color="status", orientation="h",
                 labels={"intervention_area": "", "status": "Status"}, height=280,
                 color_discrete_map=STATUS_COLOURS)
    fig.update_yaxes(automargin=True, ticksuffix="  ")
    ui.legend_on_top(fig)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
with right:
    st.markdown("#### Project timeline (start to end)")
    tl = p.assign(Start=p["start_date"], End=p["end_date"])
    fig = px.timeline(tl, x_start="Start", x_end="End", y="project_code", color="status",
                      color_discrete_map=STATUS_COLOURS, labels={"project_code": "", "status": "Status"}, height=max(280, 18 * len(tl) + 80))
    fig.update_yaxes(autorange="reversed", automargin=True)
    fig.add_vline(x=pd.Timestamp(ui.as_of()).timestamp() * 1000, line_dash="dot", line_color=ui.COLOURS["text"])
    ui.legend_on_top(fig)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.caption(f"Dotted line: {ui.as_of():%d %B %Y}. Bars that end before it but are still On track or Active are "
               "listed on the Data quality page.")

# ------------------------------------------------------------------ budgets, budget used and progress
st.markdown("#### Budgets, budget used and progress")


def used(row) -> str:
    if row.budget_used_check == "invalid, check":
        return f"invalid, check ({row.budget_used_pct:,.0f} typed)"
    return ui.pct(row.budget_used_valid) + (" (over 100%, check)" if row.budget_used_check else "")


f_native = funds.groupby("project_code").apply(
    lambda g: "; ".join(ui.native_money(r.funds, r.currency) for r in g.itertuples()), include_groups=False)
table = pd.DataFrame({
    "Project": p["project_code"],
    "Area": p["intervention_area"].replace({"Water, Sanitation and Hygiene (WASH)": "WASH",
                                            "Sustainable Agriculture & Environmental Protection": "Agriculture & environment",
                                            "Community Livelihood & Humanitarian Actions": "Livelihoods & humanitarian"}),
    "Status": p["status"],
    "Start": p["start_date"].dt.strftime("%b %Y"),
    "End": p["end_date"].dt.strftime("%b %Y"),
    "Approved budget": [ui.native_money(a, c) for a, c in zip(p["approved_budget"], p["currency"])],
    "RWF estimate": [("" if c == "RWF" else ui.rwf_estimate(v)) for v, c in zip(p["budget_rwf_estimate"], p["currency"])],
    "Activity funds": p["project_code"].map(f_native).fillna("–"),
    "Budget used": [used(r) for r in p.itertuples()],
    "Progress": [ui.pct(v) if pd.notna(v) else "invalid, check" for v in p["progress_valid"]],
    "Source": "row " + p["source_row"].astype(str),
})
ui.html_table(table, "portfolio_budgets")
st.caption("RWF estimate: blank for budgets already in RWF. Activity funds: the Activities sheet's funds for the "
           "project, in their own currency. A budget of 0 with activity funds above 0 is listed on the Data quality "
           "page.")

with st.expander("Project titles (as written) and managers (by role)"):
    ui.table(pd.DataFrame({"Project": p["project_code"], "Title (as written)": p["project_title"],
                           "Donor / partner": p["donor_partner"], "Manager (role)": ui.roles(p["manager"]),
                           "Location": p["location"]}), "portfolio_titles")

st.markdown("#### Progress by project")
prog = p[p["progress_valid"].notna()].assign(Progress=lambda d: 100 * d["progress_valid"])
fig = px.bar(prog.sort_values("Progress"), x="Progress", y="project_code", color="status", orientation="h",
             color_discrete_map=STATUS_COLOURS,
             labels={"project_code": "", "Progress": "Progress (%)", "status": "Status"},
             height=max(260, 18 * len(prog) + 80), range_x=[0, 100])
fig.update_yaxes(automargin=True)
ui.legend_on_top(fig)
st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
ui.footer()
