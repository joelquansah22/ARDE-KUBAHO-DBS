"""Donor pipeline: opportunities by stage, deadlines, weighted value, thematic fit, overdue actions."""

import datetime as dt

import pandas as pd
import plotly.express as px
import streamlit as st

import ui

f = ui.filters(sex_applies=False)
today = ui.as_of()
st.title("Donor pipeline")
st.markdown(f"<div class='muted'>As of {today:%d %B %Y}. Weighted value = amount requested × probability of "
            "success. Individual donors are shown only as 'Individual donor #NNN'.</div>", unsafe_allow_html=True)
opps = ui.query("""SELECT o.*, d.donor_name, d.donor_type FROM fact_opportunity o LEFT JOIN dim_donor d USING (donor_key)""")
for c in ("deadline", "next_action_date"):
    opps[c] = pd.to_datetime(opps[c])
opps["weighted"] = opps["requested_amount_rwf"] * opps["probability"]
open_ = opps[opps["stage"].isin(ui.OPEN_STAGES)]
fy_start = dt.date(today.year if today.month >= 7 else today.year - 1, 7, 1)
awarded = opps[(opps["stage"] == "Awarded")]
overdue = open_[open_["next_action_date"] < pd.Timestamp(today)]
ui.tiles([("Open opportunities", f"{len(open_)}"), ("Weighted pipeline", ui.money(open_["weighted"].sum(), short=True)),
          ("Awarded (all time)", ui.money(awarded["awarded_amount_rwf"].sum(), short=True), f"{len(awarded)} grants"),
          ("Overdue next actions", f"{len(overdue)}", "past their due date")])

c1, c2 = st.columns(2)
with c1:
    st.markdown("### Opportunities by stage")
    stages = ui.SETTINGS["donor_pipeline"]["stages"]
    by_stage = (opps.groupby("stage").agg(count=("opportunity_id", "count"), requested=("requested_amount_rwf", "sum"))
                .reindex(stages).fillna(0).reset_index())
    by_stage["label"] = [f"{int(c)} · {ui.money(r, short=True)}" for c, r in zip(by_stage["count"], by_stage["requested"])]
    fig = px.funnel(by_stage, x="count", y="stage", text="label")
    fig.update_traces(marker_color="#1f6f8b", textinfo="text")
    fig.update_layout(height=320, margin=dict(l=0, r=10, t=10, b=0))
    st.plotly_chart(fig, width="stretch")
with c2:
    st.markdown("### Thematic fit with current programmes")
    themes = []
    for theme in ("WASH", "Agriculture"):
        mask = open_["thematic_fit"].str.contains(theme, na=False)
        themes.append(dict(theme=theme, measure="Weighted open pipeline", value=open_.loc[mask, "weighted"].sum()))
    budgets = ui.query("""SELECT g.thematic_area AS theme, SUM(p.budget_rwf) AS value FROM dim_project p
                          JOIN dim_programme g USING (programme_id) GROUP BY 1""").assign(measure="Current project budgets")
    fit = pd.concat([pd.DataFrame(themes), budgets], ignore_index=True)
    divisor = ui.SETTINGS["currency"]["usd_to_rwf"] if f.currency == "USD" else 1
    fit["shown"] = fit["value"] / divisor
    fit["label"] = [ui.money(v, short=True) for v in fit["value"]]
    fig = px.bar(fit, x="theme", y="shown", color="measure", barmode="group", text="label",
                 labels={"shown": f.currency, "theme": "", "measure": ""},
                 color_discrete_sequence=["#1f6f8b", "#c6d4dc"])
    fig.update_layout(height=320, margin=dict(l=0, r=10, t=10, b=0), legend_orientation="h")
    st.plotly_chart(fig, width="stretch")

st.markdown("### Upcoming deadlines")
tabs = st.tabs([f"Next {d} days" for d in ui.SETTINGS["donor_pipeline"]["deadline_windows_days"]])
for tab, days in zip(tabs, ui.SETTINGS["donor_pipeline"]["deadline_windows_days"]):
    with tab:
        soon = open_[(open_["deadline"] >= pd.Timestamp(today)) &
                     (open_["deadline"] <= pd.Timestamp(today + dt.timedelta(days=days)))].sort_values("deadline")
        ui.table(pd.DataFrame({
            "Deadline": soon["deadline"].dt.strftime("%d %b %Y"), "Opportunity": soon["title"],
            "Donor": soon["donor_name"], "Stage": soon["stage"],
            "Requested": [ui.money(x) for x in soon["requested_amount_rwf"]],
            "Probability": [f"{p:.0%}" if pd.notna(p) else "–" for p in soon["probability"]],
            "Weighted": [ui.money(x) for x in soon["weighted"]], "Owner": soon["owner"]}), f"deadlines_{days}_days")

st.markdown("### Overdue next actions")
ui.table(pd.DataFrame({
    "Due": overdue["next_action_date"].dt.strftime("%d %b %Y"),
    "Days overdue": [(pd.Timestamp(today) - d).days for d in overdue["next_action_date"]],
    "Action": overdue["next_action"], "Opportunity": overdue["title"], "Stage": overdue["stage"], "Owner": overdue["owner"]
}).sort_values("Days overdue", ascending=False), "overdue_next_actions")

with st.expander("All opportunities"):
    ui.table(opps.drop(columns=["donor_key"]).assign(
        deadline=opps["deadline"].dt.strftime("%Y-%m-%d"), next_action_date=opps["next_action_date"].dt.strftime("%Y-%m-%d")),
        "all_opportunities")
