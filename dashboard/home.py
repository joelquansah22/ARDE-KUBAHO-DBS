"""Executive summary: three questions answered on one screen (no scrolling at 1366 x 768)."""

import html

import streamlit as st

import ui                # first: it makes src/ importable
import measures          # noqa: E402  (src/measures.py: one definition per figure)

f = ui.filters()
run = ui.query
cat = ui.catalogue()
quarter, q_start, q_end = ui.current_quarter()
st.title("Executive summary")
st.markdown(f"<div class='muted'>{quarter} ({q_start:%d %b} to {q_end:%d %b %Y}) · {f.scope_text}</div>",
            unsafe_allow_html=True)

c1, c2, c3 = st.columns(3, gap="small")

# ------------------------------------------------------------------ 1. On track against targets?
with c1:
    st.markdown("#### Are we on track this quarter?")
    # The same rows as the Indicators page shows for this quarter and these filters.
    rows = measures.indicator_rows(run, cat, "quarter", quarter, f)
    counts = measures.status_counts(rows)
    total = counts["total"]
    what = "indicator results (one per indicator and project)" if len(rows) and rows["per_project"].iloc[0] else "indicators"
    ui.tiles([(f"{ui.STATUS[s][0]} {ui.STATUS[s][1]}", f"{counts.get(s, 0)}", f"of {total}")
              for s in ("on track", "at risk", "off track")])
    other = total - counts.get("on track", 0) - counts.get("at risk", 0) - counts.get("off track", 0)
    st.markdown(f"<div class='muted'><b>{counts.get('on track', 0)} of {total}</b> {what} on track. The other {other} "
                "have no target, an incomplete target or no data yet.</div>", unsafe_allow_html=True)
    off = rows[rows["status"].isin(["off track", "at risk"])].sort_values("pct_achieved").head(4)
    if len(off):
        items = "".join(
            f"<li>{ui.STATUS[r.status][0]} <b>{html.escape(r.name)}</b>"
            + (f" ({r.project_id})" if r.per_project else "") + f": {r.pct_achieved:.0f}% of target</li>"
            for r in off.itertuples())
        st.markdown(f"<div class='small'><b>Off track or at risk</b><ul>{items}</ul></div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='small'>No indicator is off track or at risk this quarter.</div>", unsafe_allow_html=True)
    st.page_link("pages/2_Indicators.py", label="See all indicators →", icon="🎯")

# ------------------------------------------------------------------ 2. Can we trust the numbers?
with c2:
    st.markdown("#### Can we trust these numbers?")
    dq = ui.query("SELECT dimension, score FROM dq_dimension_scores")
    overall = dq.loc[dq["dimension"] == "overall", "score"].iloc[0]
    weakest = dq[dq["dimension"] != "overall"].sort_values("score").iloc[0]
    rec = measures.reconciliation_counts(measures.reconciliation(run, f.project_ids, q_start, q_end, f.district, f.sex))
    review = ui.query("SELECT COUNT(*) AS n FROM review_queue")["n"].iloc[0]
    review_q = ui.query("SELECT COUNT(*) AS n FROM review_queue WHERE month BETWEEN ? AND ?",
                        f"{q_start:%Y-%m}", f"{q_end:%Y-%m}")["n"].iloc[0]
    pending = measures.pending_in_register(run)
    quarantined = ui.query("SELECT COUNT(*) AS n FROM quarantine")["n"].iloc[0]
    ui.tiles([("Data-quality score", f"{overall:.1f}%", f"weakest: {weakest['dimension']} {weakest['score']:.0f}%"),
              ("Reported vs records", f"{rec['gap above tolerance']} gaps",
               f"in {rec['compared']} months compared this quarter")])
    st.markdown(f"""<div class='small'><ul>
        <li><b>{int(review_q)}</b> records to review this quarter ({int(review):,} in all)</li>
        <li><b>{pending}</b> people in the whole register pending duplicate review (people counts may be slightly high)</li>
        <li><b>{int(quarantined):,}</b> records quarantined (not used until corrected)</li></ul></div>""",
                unsafe_allow_html=True)
    st.page_link("pages/4_Data_Quality.py", label="See data quality →", icon="✅")

# ------------------------------------------------------------------ 3. Funding in the next 90 days
with c3:
    st.markdown("#### Funding: the next 90 days")
    today = ui.as_of()
    opps = measures.opportunities(run, ui.SETTINGS)
    soon = measures.deadlines_within(opps, today, 90)
    weighted = opps.loc[opps["is_open"], "weighted"].sum()
    overdue = len(measures.overdue_actions(opps, today))
    ui.tiles([("Deadlines in 90 days", f"{len(soon)}"), ("Weighted open pipeline", ui.money(weighted, short=True))])
    items = "".join(f"<li>{r.deadline:%d %b}: {html.escape(r.title)} ({r.stage})</li>" for r in soon.head(3).itertuples())
    gaps, cutoff = measures.pipeline_gaps(run, opps, today, ui.SETTINGS)
    lines = []
    for r in gaps[gaps["projects"] > 0].itertuples():
        lines.append(f"<li>{r.theme}: budgets of projects ending by {cutoff:%b %Y} {ui.money(r.ending_budget, short=True)}; "
                     f"weighted pipeline {ui.money(r.weighted, short=True)}"
                     + (f" → <b>gap {ui.money(r.gap, short=True)}</b>" if r.gap > 0 else " (covered)") + "</li>")
    st.markdown(f"<div class='small'><b>Next deadlines</b><ul>{items or '<li>None</li>'}</ul>"
                f"<b>Pipeline gaps</b><ul>{''.join(lines) or '<li>No project ends within 12 months</li>'}</ul>"
                f"<b>{overdue}</b> follow-up actions are overdue.</div>", unsafe_allow_html=True)
    st.page_link("pages/5_Donor_Pipeline.py", label="See the donor pipeline →", icon="🤝")
