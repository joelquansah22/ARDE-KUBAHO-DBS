"""Home: the landing page (team instruction 20). Fits a 1366 x 768 screen without scrolling.

1. A welcome header: the logo, the system's name and one line on what it does.
2. Four key figures: people reached, indicators on track this quarter, weighted open pipeline, data-quality score.
   They follow the sidebar filters and use the same definitions as the other pages (src/measures.py), so each
   figure here is the same number as on its own page.
3. "Needs attention": records to review, records held back for correction, overdue donor actions and deadlines in
   the next 30 days, each a link to the page where it is dealt with.
4. The menu as tiles, in the same three sections as the sidebar (config/page_help.yaml: menu).
"""

import streamlit as st

import ui                # first: it makes src/ importable
import measures          # noqa: E402  (src/measures.py: one definition per figure)

f = ui.filters()
run = ui.query
quarter, q_start, q_end = ui.current_quarter()
today = ui.as_of()

# ------------------------------------------------------------------ 1. welcome header
logo = ui.ROOT / ui.THEME.get("logo", "")
c_logo, c_text = st.columns([1, 15], vertical_alignment="center")
if ui.THEME.get("logo") and logo.is_file():
    c_logo.image(str(logo), width=56)
c_text.markdown(f"<div class='welcome'><div><h1>{ui.THEME.get('organisation_name', '')} Programme and Donor Data "
                f"System</h1><p>{ui.load_yaml('page_help.yaml')['summaries']['start']} Data as of "
                f"{today:%d %B %Y} · {f.scope_text}.</p></div></div>", unsafe_allow_html=True)

# ------------------------------------------------------------------ 2. key figures (one definition each: measures.py)
people = measures.people_reached(run, f.project_ids, f.start, f.end, f.district, f.sex)
rows = measures.indicator_rows(run, ui.catalogue(), "quarter", quarter, f)
counts = measures.status_counts(rows)
opps = measures.opportunities(run, ui.SETTINGS)
weighted = opps.loc[opps["is_open"], "weighted"].sum()
dq = ui.query("SELECT dimension, score FROM dq_dimension_scores")
overall = dq.loc[dq["dimension"] == "overall", "score"].iloc[0]
ui.tiles([
    ("People reached (different people)", f"{people['people']:,}", f"{f.start:%d %b %Y} to {f.end:%d %b %Y}"),
    (f"{ui.STATUS['on track'][0]} Indicators on track", f"{counts.get('on track', 0)} of {counts['total']}",
     f"{quarter}"),
    ("Weighted open pipeline", ui.money(weighted, short=True, currency=f.currency), "amount × chance of success"),
    ("Data-quality score", f"{overall:.1f}%", "average of six checks"),
])

# ------------------------------------------------------------------ 3. needs attention
review = int(ui.query("SELECT COUNT(*) AS n FROM review_queue")["n"].iloc[0])
held = int(ui.query("SELECT COUNT(*) AS n FROM quarantine")["n"].iloc[0])
overdue = len(measures.overdue_actions(opps, today))
soon = len(measures.deadlines_within(opps, today, 30))
st.markdown("<div class='menu-section'>Needs attention</div>", unsafe_allow_html=True)
with st.container(border=True):
    a1, a2, a3, a4 = st.columns(4)
    for col, key, number, words in (
            (a1, "data_quality", review, "records to review"),
            (a2, "data_quality", held, "held back for correction"),
            (a3, "donor_pipeline", overdue, "overdue donor actions"),
            (a4, "donor_pipeline", soon, "donor deadlines in 30 days")):
        page = ui.menu_page(key)
        col.page_link(page["file"], label=f"**{number:,}** {words}", icon=page["icon"])

# ------------------------------------------------------------------ 4. the menu, as tiles
def tiles(pages: list[dict], per_row: int) -> None:
    cols = st.columns(per_row)
    for col, page in zip(cols, pages):
        with col.container(border=True, height=122):          # the same height for every tile
            st.page_link(page["file"], label=f"**{page['title']}**", icon=page["icon"])
            st.markdown(f"<div class='menu-note'>{page['description']}</div>", unsafe_allow_html=True)


sections = {s["section"]: s["pages"] for s in ui.menu() if s["section"]}
st.markdown("<div class='menu-section'>Insights</div>", unsafe_allow_html=True)
tiles(sections["Insights"], 5)
left, right = st.columns([3, 2])
with left:
    st.markdown("<div class='menu-section'>Data</div>", unsafe_allow_html=True)
    tiles(sections["Data"], 3)
with right:
    st.markdown("<div class='menu-section'>Donors</div>", unsafe_allow_html=True)
    tiles(sections["Donors"], 2)
