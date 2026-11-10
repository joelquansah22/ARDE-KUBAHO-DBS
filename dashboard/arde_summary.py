"""Executive summary (ARDE/KUBAHO workbook mode): the three questions on one screen (team instruction 22).

1. Are we on track? KPI bands for the ACTIVE projects (status On track, Active or In progress: settings
   arde.active_statuses), with the workbook's thresholds.
2. Can we trust the numbers? The data-quality score and the checks with the most records to correct or review.
3. Funding: the contributions history (valued contributions by start year, one currency at a time, never added
   across currencies) and the open pipeline opportunities entered on the Donor entry page.
The sidebar filters apply to sections 1 and 3; the score covers the whole workbook.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

import ui                # first: it makes src/ importable
import arde_funding      # noqa: E402
from arde_model import BAND_ORDER  # noqa: E402

f = ui.arde_filters()
ui.page_header("Executive summary", "arde_summary")
codes = f.project_codes
IN = ui.in_list(codes)
active_statuses = ui.SETTINGS["arde"]["active_statuses"]
today = ui.as_of()
col1, col2, col3 = st.columns(3, gap="medium")

# ------------------------------------------------------------------ 1. on track
with col1:
    st.markdown("#### 1. Are the active projects on track?")
    k = ui.query(f"""SELECT k.project_code, k.band FROM fact_kpi k JOIN dim_project p USING (project_code)
                     WHERE p.status IN {ui.in_list(active_statuses)} AND k.project_code IN {IN}""",
                 *active_statuses, *codes)
    if not len(k):
        st.markdown("No active project in this selection.")
    else:
        counts = k["band"].value_counts()
        st.markdown(f"**{k['project_code'].nunique()} active projects, {len(k)} KPIs**")
        st.markdown("".join(f"<div>{ui.band_html(b)}: <b>{int(counts.get(b, 0))}</b></div>" for b in BAND_ORDER
                            if counts.get(b, 0)), unsafe_allow_html=True)
        by = k.pivot_table(index="project_code", columns="band", aggfunc="size", fill_value=0)
        by = by.reindex(columns=[b for b in BAND_ORDER if b in by.columns])
        ui.table(by.reset_index().rename(columns={"project_code": "Project"}), "summary_active_bands", height=220)
    st.page_link(ui.menu_page("results_kpis")["file"], label="Results and KPIs", icon=":material/account_tree:")

# ------------------------------------------------------------------ 2. trust
with col2:
    st.markdown("#### 2. Can we trust the numbers?")
    score = float(ui.query("SELECT dq_score FROM run_info")["dq_score"].iloc[0])
    st.markdown(ui.tile("Data-quality score", f"{score:.1f}%", "whole workbook: average pass rate of the checks"),
                unsafe_allow_html=True)
    top = ui.query("""SELECT label, level, flagged FROM dq_rule_summary WHERE level IN ('held_back', 'review')
                      AND flagged > 0 ORDER BY CASE level WHEN 'held_back' THEN 0 ELSE 1 END, flagged DESC LIMIT 5""")
    st.markdown("**Top issues**")
    st.markdown("\n".join(f"- **{r.flagged}** {r.label if r.label[:3].isupper() else r.label[0].lower() + r.label[1:]} "
                          f"({'held back' if r.level == 'held_back' else 'to review'})" for r in top.itertuples())
                or "None.")
    st.page_link(ui.menu_page("data_quality")["file"], label="Data quality", icon=":material/fact_check:")

# ------------------------------------------------------------------ 3. funding
with col3:
    st.markdown("#### 3. What funding is coming in?")
    c = ui.query(f"""SELECT c.currency, c.value, p.start_year FROM fact_contribution c
                     JOIN dim_project p USING (project_code)
                     WHERE c.is_money AND c.value > 0 AND c.project_code IN {IN}""", *codes)
    if len(c):
        st.markdown("**Contributions history** (valued contributions, by project start year)")
        currencies = [x for x in ("RWF", "EUR", "USD") if x in set(c["currency"])]
        chosen = (st.radio("Currency", currencies, horizontal=True, key="summary_currency", label_visibility="collapsed")
                  if len(currencies) > 1 else currencies[0])
        by = c[c["currency"] == chosen].groupby("start_year", as_index=False)["value"].sum()
        fig = px.bar(by, x="start_year", y="value", labels={"start_year": "", "value": chosen}, height=190)
        fig.update_traces(marker_color=ui.CHART[0])
        fig.update_layout(margin=dict(l=0, r=0, t=5, b=0))
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        st.caption("One currency at a time; amounts in different currencies are never added together.")
    else:
        st.markdown("No valued contribution in this selection.")
    opps = arde_funding.opportunities()
    open_ = opps[opps["is_open"]]
    if len(open_):
        st.markdown(f"**Open pipeline:** {len(open_)} opportunities, weighted "
                    f"{ui.money(open_['weighted'].sum(), 'RWF', short=True)}; "
                    f"{len(arde_funding.deadlines_within(opps, today, 30))} deadlines in the next 30 days.")
        st.page_link(ui.menu_page("donor_pipeline")["file"], label="Donor pipeline", icon=":material/handshake:")
    else:
        st.markdown("**Open pipeline:** no funding opportunities recorded yet.")
        st.page_link(ui.menu_page("donor_entry")["file"], label="Add your first one: Donor entry",
                     icon=":material/volunteer_activism:")
    st.page_link(ui.menu_page("partners_funding")["file"], label="Funding history: Partners and funding",
                 icon=":material/payments:")
ui.footer()
