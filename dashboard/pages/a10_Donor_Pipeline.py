"""Donor pipeline (ARDE/KUBAHO workbook mode): funding opportunities entered on the Donor entry page, and a link to
the funding history (Partners and funding, from the workbook's Stakeholders sheet).

With no opportunities yet, one plain line invites the first one (team instruction 22). Opportunities are recorded
in RWF (the Donor entry form asks for RWF). Definitions: src/arde_funding.py.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ui                # first: it makes src/ importable
import arde_funding      # noqa: E402

f = ui.arde_filters()
ui.page_header("Donor pipeline", "arde_donor_pipeline")
today = ui.as_of()
entry = ui.menu_page("donor_entry")
history = ui.menu_page("partners_funding")
opps = arde_funding.opportunities()


def show_pipeline() -> None:
    """The pipeline, once at least one opportunity is recorded."""
    open_ = opps[opps["is_open"]]
    overdue = arde_funding.overdue_actions(opps, today)
    ui.tiles([("Open opportunities", f"{len(open_):,}", f"of {len(opps):,} recorded"),
              ("Weighted open pipeline", ui.money(open_["weighted"].sum(), "RWF", short=True),
               "amount requested × chance of success"),
              ("Deadlines in 30 days", f"{len(arde_funding.deadlines_within(opps, today, 30)):,}",
               f"{len(arde_funding.deadlines_within(opps, today, 90)):,} in 90 days"),
              ("Overdue next actions", f"{len(overdue):,}", f"as of {today:%d %b %Y}")])
    st.page_link(history["file"], label="Funding history: Partners and funding", icon=history["icon"])

    left, right = st.columns(2)
    with left:
        st.markdown("#### Opportunities by stage")
        stages = ui.SETTINGS["donor_pipeline"]["stages"]
        counts = opps["stage"].value_counts().reindex(stages, fill_value=0)
        fig = go.Figure(go.Funnel(y=counts.index, x=counts.values, marker_color=ui.CHART[0], textinfo="value"))
        fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    with right:
        st.markdown("#### Upcoming deadlines (open opportunities)")
        for days in ui.SETTINGS["donor_pipeline"]["deadline_windows_days"]:
            st.markdown(f"- **{len(arde_funding.deadlines_within(opps, today, days))}** in the next {days} days")
        if len(overdue):
            st.markdown("**Overdue next actions**")
            ui.table(pd.DataFrame({"Opportunity": overdue["opportunity_id"], "Title": overdue["title"],
                                   "Next action": overdue["next_action"], "Due": overdue["next_action_date"],
                                   "Owner": overdue["owner"]}), "arde_overdue_actions")

    st.markdown("#### Every opportunity")
    ui.table(pd.DataFrame({
        "Opportunity": opps["opportunity_id"], "Donor": opps["donor"], "Title": opps["title"],
        "Fits area": opps["thematic_fit"], "Stage": opps["stage"], "Deadline": opps["deadline"],
        "Requested (RWF)": opps["requested_amount_rwf"], "Awarded (RWF)": opps["awarded_amount_rwf"],
        "Probability": (100 * opps["probability"]).round(0), "Weighted (RWF)": opps["weighted"].round(0),
        "Owner": opps["owner"], "Next action": opps["next_action"], "Due": opps["next_action_date"]}),
        "arde_opportunities")
    st.page_link(entry["file"], label="Add or update opportunities: Donor entry", icon=entry["icon"])


if not len(opps):
    # A plain line, not st.stop(): the page must finish so the footer and app.py's end marker are drawn.
    st.markdown("**No funding opportunities recorded yet. Add your first one** on the Donor entry page.")
    st.page_link(entry["file"], label="Add your first opportunity: Donor entry", icon=entry["icon"])
    st.page_link(history["file"], label="Funding history: Partners and funding", icon=history["icon"])
else:
    show_pipeline()
ui.footer()
