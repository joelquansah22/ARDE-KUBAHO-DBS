"""Executive summary: three questions answered on one screen (no scrolling at 1366 x 768)."""

import datetime as dt

import pandas as pd
import streamlit as st

import ui

f = ui.filters()
quarter, q_start, q_end = ui.current_quarter()
projects = f.project_ids
st.title("Executive summary")
st.markdown(f"<div class='muted'>{quarter} ({q_start:%d %b} to {q_end:%d %b %Y}) · {f.scope_text}</div>",
            unsafe_allow_html=True)

c1, c2, c3 = st.columns(3, gap="small")

# ------------------------------------------------------------------ 1. On track against targets?
with c1:
    st.markdown("#### Are we on track this quarter?")
    district_clause = "AND district = ?" if f.district else "AND district <> 'All'"
    params = [quarter] + projects + ([f.district] if f.district else [])
    v = ui.query(f"""SELECT v.indicator_code, v.project_id, v.district, v.status, v.pct_achieved, v.partial_pct_achieved,
                            v.target_note
                     FROM indicator_values v
                     WHERE v.period_type = 'quarter' AND v.period = ? AND v.source = 'reported'
                       AND v.disaggregation = 'total' AND v.project_id IN {ui.in_list(projects)} {district_clause}""",
                 *params)
    counts = v["status"].value_counts()
    ui.tiles([("✔ On track", f"{counts.get('on track', 0)}"), ("▲ At risk", f"{counts.get('at risk', 0)}"),
              ("✖ Off track", f"{counts.get('off track', 0)}")])
    other = counts.get("target incomplete", 0) + counts.get("no target set", 0) + counts.get("no data", 0)
    st.markdown(f"<div class='muted'>Reported results by project and district. {other} more have no complete "
                "target or no report yet.</div>", unsafe_allow_html=True)
    off = v[v["status"] == "off track"].sort_values("pct_achieved").head(4)
    if len(off):
        items = "".join(f"<li>✖ <b>{r.indicator_code}</b> · {r.project_id} {r.district}: {r.pct_achieved:.0f}% of target</li>"
                        for r in off.itertuples())
        st.markdown(f"<div class='small'><b>Where we are off track</b><ul>{items}</ul></div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='small'>No result is off track this quarter.</div>", unsafe_allow_html=True)
    st.page_link("pages/2_Indicators.py", label="See all indicators →", icon="🎯")

# ------------------------------------------------------------------ 2. Can we trust the numbers?
with c2:
    st.markdown("#### Can we trust these numbers?")
    dq = ui.query("SELECT dimension, score FROM dq_dimension_scores")
    overall = dq.loc[dq["dimension"] == "overall", "score"].iloc[0]
    weakest = dq[dq["dimension"] != "overall"].sort_values("score").iloc[0]
    flags = ui.query(f"""SELECT COUNT(*) AS n, SUM(CASE WHEN flag THEN 1 ELSE 0 END) AS flagged
                         FROM indicator_reconciliation WHERE district <> 'All' AND project_id IN {ui.in_list(projects)}
                         AND period_start BETWEEN ? AND ?""", *projects, q_start, q_end).iloc[0]
    review = ui.query("SELECT COUNT(*) AS n FROM review_queue")["n"].iloc[0]
    review_q = ui.query("SELECT COUNT(*) AS n FROM review_queue WHERE month BETWEEN ? AND ?",
                        f"{q_start:%Y-%m}", f"{q_end:%Y-%m}")["n"].iloc[0]
    pending = ui.query("SELECT SUM(CASE WHEN pending_duplicate_review THEN 1 ELSE 0 END) AS n FROM dim_beneficiary")["n"].iloc[0]
    quarantined = ui.query("SELECT COUNT(*) AS n FROM quarantine")["n"].iloc[0]
    ui.tiles([("Data-quality score", f"{overall:.1f}%", f"weakest: {weakest['dimension']} {weakest['score']:.0f}%"),
              ("Reported vs records", f"{int(flags['flagged'] or 0)} gaps", f"of {int(flags['n'])} checks this quarter")])
    st.markdown(f"""<div class='small'><ul>
        <li><b>{int(review_q)}</b> records to review this quarter ({int(review):,} in all)</li>
        <li><b>{int(pending or 0)}</b> people pending duplicate review (people counts may be slightly high)</li>
        <li><b>{int(quarantined):,}</b> records quarantined (not used until corrected)</li></ul></div>""",
                unsafe_allow_html=True)
    st.page_link("pages/4_Data_Quality.py", label="See data quality →", icon="✅")

# ------------------------------------------------------------------ 3. Funding in the next 90 days
with c3:
    st.markdown("#### Funding: the next 90 days")
    today = ui.as_of()
    opps = ui.query(f"""SELECT o.title, o.stage, o.deadline, o.requested_amount_rwf, o.probability, o.thematic_fit,
                               o.next_action_date, d.donor_name
                        FROM fact_opportunity o LEFT JOIN dim_donor d USING (donor_key)""")
    open_ = opps[opps["stage"].isin(ui.OPEN_STAGES)]
    soon = open_[(open_["deadline"] >= pd.Timestamp(today)) &
                 (open_["deadline"] <= pd.Timestamp(today + dt.timedelta(days=90)))].sort_values("deadline")
    weighted = (open_["requested_amount_rwf"] * open_["probability"]).sum()
    overdue = int((open_["next_action_date"] < pd.Timestamp(today)).sum())
    ui.tiles([("Deadlines in 90 days", f"{len(soon)}"), ("Weighted pipeline", ui.money(weighted, short=True))])
    items = "".join(f"<li>{pd.Timestamp(r.deadline):%d %b}: {r.title} ({r.stage})</li>" for r in soon.head(3).itertuples())
    # Pipeline gap: budget of projects ending within 12 months, against the weighted pipeline for their theme.
    ending = ui.query("""SELECT g.thematic_area AS theme, SUM(p.budget_rwf) AS budget FROM dim_project p
                         JOIN dim_programme g USING (programme_id) WHERE p.end_date <= ? GROUP BY 1""",
                      today + dt.timedelta(days=365))
    gaps = []
    for r in ending.itertuples():
        theme_pipe = (open_[open_["thematic_fit"].str.contains(r.theme, na=False)]["requested_amount_rwf"]
                      * open_[open_["thematic_fit"].str.contains(r.theme, na=False)]["probability"]).sum()
        gap = r.budget - theme_pipe
        gaps.append(f"<li>{r.theme}: projects worth {ui.money(r.budget, short=True)} end within 12 months; weighted "
                    f"pipeline {ui.money(theme_pipe, short=True)}" + (f" → <b>gap {ui.money(gap, short=True)}</b>"
                                                                       if gap > 0 else " (covered)") + "</li>")
    st.markdown(f"<div class='small'><b>Next deadlines</b><ul>{items or '<li>None</li>'}</ul>"
                f"<b>Pipeline gaps</b><ul>{''.join(gaps) or '<li>No project ends within 12 months</li>'}</ul>"
                f"<b>{overdue}</b> follow-up actions are overdue.</div>", unsafe_allow_html=True)
    st.page_link("pages/5_Donor_Pipeline.py", label="See the donor pipeline →", icon="🤝")
