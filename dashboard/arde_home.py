"""Home in ARDE/KUBAHO workbook mode (data_mode: arde): the landing page.

1. A welcome header: the logo, the system's name and one line on what it does.
2. Key figures from ARDE's workbook: projects by status; KPIs achieved / on track / needs attention / not recorded;
   direct reach counted in PEOPLE only (never added across units); the data-quality score.
3. "Needs attention": the result of each data-quality rule that holds a value back or sends it for review, with a
   link to the Data quality page.
4. The menu as tiles (config/page_help.yaml: menu_arde).
The sidebar filters apply to the figures (the data-quality score always covers the whole workbook).
"""

import streamlit as st

import ui                # first: it makes src/ importable

f = ui.arde_filters()
codes = f.project_codes
IN = ui.in_list(codes)

# ------------------------------------------------------------------ 1. welcome header
logo = ui.ROOT / ui.THEME.get("logo", "")
c_logo, c_text = st.columns([1, 15], vertical_alignment="center")
if ui.THEME.get("logo") and logo.is_file():
    c_logo.image(str(logo), width=56)
c_text.markdown(f"<div class='welcome'><div><h1>{ui.THEME.get('organisation_name', '')} Programme and Donor Data "
                f"System</h1><p>{ui.load_yaml('page_help.yaml')['summaries']['arde_start']} Checks as of "
                f"{ui.as_of():%d %B %Y} · {f.scope_text}.</p></div></div>", unsafe_allow_html=True)
ui.how_to_read("arde_start")

# ------------------------------------------------------------------ 2. key figures
projects = ui.query(f"SELECT status, COUNT(*) AS n FROM dim_project WHERE project_code IN {IN} GROUP BY 1 "
                    "ORDER BY 2 DESC", *codes)
bands = ui.query(f"SELECT band, COUNT(*) AS n FROM fact_kpi WHERE project_code IN {IN} GROUP BY 1", *codes)
b = dict(zip(bands["band"], bands["n"]))
people = ui.query(f"SELECT COALESCE(SUM(count), 0) AS n, COUNT(DISTINCT project_code) AS p FROM fact_reach "
                  f"WHERE is_headline_people AND reach_type = 'Direct' AND project_code IN {IN}", *codes).iloc[0]
score = float(ui.query("SELECT dq_score FROM run_info")["dq_score"].iloc[0])
n_kpi = int(sum(b.values()))
ui.tiles([
    ("Projects", f"{int(projects['n'].sum()):,}", " · ".join(f"{r.n} {r.status}" for r in projects.itertuples())),
    ("KPIs achieved", f"{b.get('Achieved', 0):,} of {n_kpi:,}",
     f"{ui.band_label('On track')} {b.get('On track', 0)} · {ui.band_label('Needs attention')} "
     f"{b.get('Needs attention', 0)} · {ui.band_label('Not recorded')} {b.get('Not recorded', 0)}"
     + (f" · no target {b['No target']}" if b.get("No target") else "")),
    ("Direct reach, people", f"{int(people['n']):,}",
     f"rows counted in 'people' only, {int(people['p'])} projects; other units on the Reach page"),
    ("Data-quality score", f"{score:.1f}%", "whole workbook; average pass rate of the checks"),
])

# ------------------------------------------------------------------ 3. needs attention
rules = ui.query(f"""SELECT r.label, r.level, COUNT(*) AS n FROM dq_rule_results r
                     WHERE r.level IN ('held_back', 'review') AND (r.project_code IS NULL OR r.project_code IN {IN})
                     GROUP BY 1, 2 ORDER BY CASE r.level WHEN 'held_back' THEN 0 ELSE 1 END, 3 DESC""", *codes)
st.markdown("<div class='menu-section'>Needs attention</div>", unsafe_allow_html=True)
dq_page = ui.menu_page("data_quality")
with st.container(border=True):
    if not len(rules):
        st.markdown("Nothing to check in this selection.")
    else:
        cols = st.columns(3)
        for i, r in enumerate(rules.itertuples()):
            tag = "held back" if r.level == "held_back" else "to review"
            cols[i % 3].markdown(f"**{r.n:,}** {r.label[0].lower() + r.label[1:] if not r.label[:3].isupper() else r.label} <span class='muted'>({tag})</span>",
                                 unsafe_allow_html=True)
        st.page_link(dq_page["file"], label="Open the Data quality page for the lists", icon=dq_page["icon"])


# ------------------------------------------------------------------ 4. the menu, as tiles
def tiles(pages: list[dict], per_row: int) -> None:
    cols = st.columns(per_row)
    for col, page in zip(cols, pages):
        with col.container(border=True, height=122):
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
