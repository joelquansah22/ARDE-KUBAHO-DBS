"""Donor pipeline: open opportunities by stage, outcomes, deadlines, weighted value, thematic fit, overdue actions."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ui                # first: it makes src/ importable
import measures          # noqa: E402  (src/measures.py: one definition per figure)

f = ui.filters(sex_applies=False)
run = ui.query
today = ui.as_of()
cfg = ui.SETTINGS["donor_pipeline"]
ui.page_header("Donor pipeline", "donor_pipeline")
ui.how_to_read("donor_pipeline")
st.markdown(f"<div class='muted'>As of {today:%d %B %Y}. Weighted value = amount requested × probability of "
            "success. Individual donors are shown only as 'Individual donor #NNN'. Programme, project, district and "
            "sex filters do not apply on this page.</div>", unsafe_allow_html=True)
opps = measures.opportunities(run, ui.SETTINGS)
st.caption(ui.donor_sources_note())
open_ = opps[opps["is_open"]]
awarded = opps[opps["stage"] == "Awarded"]
declined = opps[opps["stage"] == "Declined"]
overdue = measures.overdue_actions(opps, today)
ui.tiles([("Open opportunities", f"{len(open_)}", "not yet decided"),
          ("Weighted open pipeline", ui.money(open_["weighted"].sum(), short=True),
           f"of {ui.money(open_['requested_amount_rwf'].sum(), short=True)} requested"),
          ("Outcome: awarded", ui.money(awarded["awarded_amount_rwf"].sum(), short=True), f"{len(awarded)} grants (all time)"),
          ("Outcome: declined", f"{len(declined)}", f"{ui.money(declined['requested_amount_rwf'].sum(), short=True)} requested"),
          ("Overdue next actions", f"{len(overdue)}", "past their due date")])

c1, c2 = st.columns(2)
divisor = ui.SETTINGS["currency"]["usd_to_rwf"] if f.currency == "USD" else 1
with c1:
    st.markdown("### Open opportunities by stage")
    by_stage = (open_.groupby("stage").agg(count=("opportunity_id", "count"), requested=("requested_amount_rwf", "sum"),
                                           weighted=("weighted", "sum"))
                .reindex(cfg["open_stages"]).fillna(0).reset_index())
    fig = go.Figure()
    fig.add_bar(y=by_stage["stage"], x=by_stage["requested"] / divisor, orientation="h", name="Requested",
                marker_color=ui.COMPARE,
                text=[f"{int(c)} opportunit{'y' if c == 1 else 'ies'} · {ui.money(r, short=True)}"
                      for c, r in zip(by_stage["count"], by_stage["requested"])], textposition="auto")
    fig.add_bar(y=by_stage["stage"], x=by_stage["weighted"] / divisor, orientation="h", name="Weighted",
                marker_color=ui.CHART[0], text=[ui.money(w, short=True) for w in by_stage["weighted"]], textposition="auto")
    fig.update_layout(barmode="group", height=320, margin=dict(l=0, r=10, t=10, b=0), legend_orientation="h",
                      xaxis_title=f"Value ({f.currency})", yaxis=dict(autorange="reversed"))
    ui.legend_on_top(fig)
    st.plotly_chart(fig, width="stretch")
    st.caption("Stages run from top (earliest) to bottom. Awarded and declined opportunities are outcomes, shown in "
               "the tiles above, not stages.")
with c2:
    st.markdown("### Thematic fit with current programmes")
    gaps, cutoff = measures.pipeline_gaps(run, opps, today, ui.SETTINGS)
    by_theme = measures.pipeline_by_theme(opps, ui.SETTINGS)
    ending_label = f"Annual budget of projects ending by {cutoff:%b %Y}"
    fig = go.Figure()
    fig.add_bar(x=by_theme["theme"], y=by_theme["weighted"] / divisor, name="Weighted open pipeline",
                marker_color=ui.CHART[0], text=[ui.money(v, short=True) for v in by_theme["weighted"]])
    fig.add_bar(x=gaps["theme"], y=gaps["ending_budget"] / divisor, name=ending_label, marker_color=ui.COMPARE,
                text=[ui.money(v, short=True) for v in gaps["ending_budget"]])
    fig.update_layout(barmode="group", height=320, margin=dict(l=0, r=10, t=10, b=0), legend_orientation="h",
                      yaxis_title=f"Value ({f.currency})")
    fig.update_traces(textangle=0, textposition="outside", cliponaxis=False)
    ui.legend_on_top(fig)
    st.plotly_chart(fig, width="stretch")
    n_projects = int(gaps["projects"].sum())
    all_projects = len(ui.query("SELECT project_id FROM dim_project"))
    n_projects = int(gaps["projects"].sum())
    st.caption(f"Opportunities that fit two themes are split equally between them, so the themes add up to the "
               f"{ui.money(open_['weighted'].sum(), short=True)} total. {n_projects} projects end by {cutoff:%d %b %Y} "
               f"(within {cfg['ending_within_months']} months); their annual budget is the budget divided by the "
               "project's length in years, i.e. what one more year of the work would cost.")
    ui.html_table(pd.DataFrame({
        "Theme": gaps["theme"], "Projects ending": gaps["projects"],
        "Annual budget": [ui.money(x, short=True) for x in gaps["ending_budget"]],
        "Weighted open pipeline": [ui.money(x, short=True) for x in gaps["weighted"]],
        "Pipeline gap": [ui.money(g, short=True) if g > 0 else "covered" for g in gaps["gap"]]}), "pipeline_gaps")
    st.caption("Pipeline gap = annual budget of projects ending within 12 months minus the weighted open pipeline for "
               "the theme. **Draft definition, to be confirmed with ARDE/KUBAHO.**")

st.markdown("### Upcoming deadlines")
tabs = st.tabs([f"Next {d} days" for d in cfg["deadline_windows_days"]])
for tab, days in zip(tabs, cfg["deadline_windows_days"]):
    with tab:
        soon = measures.deadlines_within(opps, today, days)
        ui.html_table(pd.DataFrame({
            "Deadline": soon["deadline"].dt.strftime("%d %b %Y"), "Opportunity": soon["title"],
            "Donor": soon["donor_name"], "Stage": soon["stage"],
            "Requested": [ui.money(x) for x in soon["requested_amount_rwf"]],
            "Probability": [f"{p:.0%}" if pd.notna(p) else "–" for p in soon["probability"]],
            "Weighted": [ui.money(x) for x in soon["weighted"]], "Owner": soon["owner"]}), f"deadlines_{days}_days")

st.markdown("### Overdue next actions")
ui.html_table(pd.DataFrame({
    "Due": overdue["next_action_date"].dt.strftime("%d %b %Y"),
    "Days overdue": [(pd.Timestamp(today) - d).days for d in overdue["next_action_date"]],
    "Action": overdue["next_action"], "Opportunity": overdue["title"], "Stage": overdue["stage"], "Owner": overdue["owner"]
}).sort_values("Days overdue", ascending=False), "overdue_next_actions")

with st.expander("All opportunities"):
    ui.table(pd.DataFrame({
        "Opportunity": opps["title"], "Donor": opps["donor_name"], "Donor type": opps["donor_type"].str.capitalize(),
        "Theme": opps["thematic_fit"], "Stage": opps["stage"], "Deadline": opps["deadline"].dt.strftime("%d %b %Y"),
        "Requested": [ui.money(x) for x in opps["requested_amount_rwf"]],
        "Awarded": [ui.money(x) if pd.notna(x) and x else "" for x in opps["awarded_amount_rwf"]],
        "Probability": [f"{p:.0%}" if pd.notna(p) else "–" for p in opps["probability"]],
        "Weighted": [ui.money(x) for x in opps["weighted"]], "Owner": opps["owner"],
        "Next action": opps["next_action"], "Next action due": opps["next_action_date"].dt.strftime("%d %b %Y"),
        "Source file": opps["source_file"], "Source row": opps["source_row"]}), "all_opportunities")

ui.footer()          # data last updated, with the source files (on every page, and printed)
