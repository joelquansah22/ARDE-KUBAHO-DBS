"""Phase 6: the dashboard's numbers agree with each other.

Two kinds of check, each under several filter combinations:
  1. every total shown on more than one page is the same number on each page (read from the rendered pages);
  2. every breakdown (by district, by theme, by status, by project, by sex) adds up to its total.
"""

import datetime as dt
import re
from pathlib import Path

import duckdb
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from common import load_settings, load_yaml, resolve_path

import measures

APP = Path(__file__).resolve().parent.parent / "dashboard" / "app.py"
S = load_settings()
CAT = {i["code"]: i for i in load_yaml("indicator_catalogue.yaml")["indicators"]}
FY = (dt.date(2024, 7, 1), dt.date(2025, 6, 30))

# Filter combinations: (programme, project, district, (start, end), sex)
COMBOS = {
    "no filters": (None, None, None, None, None),
    "WASH programme": ("PRG01", None, None, None, None),
    "one project": (None, "PRJ04", None, None, None),
    "one district": (None, None, "Bugesera", None, None),
    "women only": (None, None, None, None, "female"),
    "one fiscal year, men, agriculture": ("PRG02", None, None, FY, "male"),
    "project + district + year": (None, "PRJ01", "Nyagatare", FY, None),
}


@pytest.fixture(scope="module")
def con():
    path = resolve_path("warehouse")
    if not path.exists():
        pytest.skip("Build the warehouse first: python src/pipeline.py")
    c = duckdb.connect(str(path), read_only=True)
    yield c
    c.close()


@pytest.fixture(scope="module")
def run(con):
    return lambda sql, *params: con.execute(sql, list(params)).df()


class F:
    """The filter choices, as the pages see them (ui.Filters without Streamlit)."""

    def __init__(self, run, programme, project, district, dates, sex):
        window = S["reporting_window"]
        self.programme_id, self.project_id, self.district, self.sex = programme, project, district, sex
        self.start, self.end = dates or (window["start"], window["end"])
        p = run("SELECT project_id, programme_id FROM dim_project")
        self.project_ids = ([project] if project else
                            list(p.loc[p["programme_id"] == programme, "project_id"]) if programme
                            else list(p["project_id"]))


def filters(run, name):
    return F(run, *COMBOS[name])


# ---------------------------------------------------------------- rendering pages with filters
def render(page, combo, con):
    programme, project, district, dates, sex = COMBOS[combo]
    names = dict(con.execute("SELECT programme_id, name FROM dim_programme").fetchall())
    pnames = dict(con.execute("SELECT project_id, name FROM dim_project").fetchall())
    at = AppTest.from_file(str(APP), default_timeout=120)
    at.session_state["f_programme"] = f"{programme} {names[programme]}" if programme else "All programmes"
    at.session_state["f_project"] = f"{project} {pnames[project]}" if project else "All projects"
    at.session_state["f_district"] = district or "All districts"
    window = S["reporting_window"]
    at.session_state["f_dates"] = dates or (window["start"], window["end"])
    at.session_state["f_sex"] = sex.capitalize() if sex else "All"
    if page:
        at.switch_page(page)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def html(at) -> str:
    return " ".join(m.value for m in at.markdown) + " " + " ".join(c.value for c in at.caption)


def tile(at, label: str) -> tuple[str, str]:
    """(value, note) of the tile with this label."""
    m = re.search(rf"<div class='tile-label'>{re.escape(label)}</div><div class='tile-value'>(.*?)</div>"
                  r"(?:<div class='tile-note'>(.*?)</div>)?", html(at))
    assert m, f"tile '{label}' not found"
    return m.group(1), m.group(2) or ""


def to_int(text: str) -> int:
    return int(re.sub(r"[^\d]", "", text.split(" of ")[0]))


# ---------------------------------------------------------------- 2. breakdowns add up (measures)
@pytest.mark.parametrize("combo", list(COMBOS))
def test_people_by_district_add_up_to_people_reached(run, combo):
    f = filters(run, combo)
    by = measures.people_by_district(run, f.project_ids, f.start, f.end, None, f.sex)
    total = measures.people_reached(run, f.project_ids, f.start, f.end, None, f.sex)
    assert int(by["people"].sum()) == total["people"]
    assert int(by["pending"].sum()) == total["pending"]
    # Each district's row is what the Programme overview shows with that district chosen.
    for r in by[by["district"] != measures.UNKNOWN_DISTRICT].itertuples():
        assert measures.people_reached(run, f.project_ids, f.start, f.end, r.district, f.sex)["people"] == r.people
    # People counted directly (no grouping) agree too: nobody is in two districts or lost.
    direct = run(f"""SELECT COUNT(DISTINCT s.beneficiary_key) AS n FROM fact_beneficiary_service s
                     JOIN dim_activity a USING (activity_id) JOIN dim_beneficiary b USING (beneficiary_key)
                     WHERE a.project_id IN {measures.in_list(f.project_ids)} AND s.date BETWEEN ? AND ?
                     {"AND b.sex = ?" if f.sex else ""}""", *f.project_ids, f.start, f.end,
                 *([f.sex] if f.sex else []))["n"].iloc[0]
    assert direct == total["people"]


@pytest.mark.parametrize("combo", list(COMBOS))
def test_activities_and_spending_by_district_add_up(run, combo):
    f = filters(run, combo)
    by = measures.activities_by_district(run, f.project_ids, f.start, f.end)
    total = measures.activities_total(run, f.project_ids, f.start, f.end)
    assert int(by["activities"].sum()) == total["activities"]
    assert by["spend"].sum() == pytest.approx(total["spend"])


@pytest.mark.parametrize("combo", list(COMBOS))
def test_reconciliation_statuses_add_up_to_months_compared(run, combo):
    f = filters(run, combo)
    rec = measures.reconciliation(run, f.project_ids, f.start, f.end, f.district, f.sex)
    n = measures.reconciliation_counts(rec)
    assert sum(n[s] for s in measures.RECONCILIATION_GROUPS) == n["compared"]


def test_reconciliation_needs_both_the_percentage_and_the_minimum_difference(run):
    rec = run("SELECT * FROM indicator_reconciliation")
    tol, min_diff = S["indicators"]["reconciliation_tolerance_pct"], S["indicators"]["reconciliation_min_difference"]
    flagged = rec[rec["flag"]]
    assert len(flagged)
    assert (flagged["difference"].abs() >= min_diff).all()
    assert ((flagged["pct_difference"].abs() > tol) | (flagged["reported"] == 0)).all()


def test_pipeline_themes_add_up_to_the_total(run):
    opps = measures.opportunities(run, S)
    by_theme = measures.pipeline_by_theme(opps, S)
    assert by_theme["weighted"].sum() == pytest.approx(opps.loc[opps["is_open"], "weighted"].sum())
    assert by_theme["requested"].sum() == pytest.approx(opps.loc[opps["is_open"], "requested_amount_rwf"].sum())
    assert by_theme["opportunities"].sum() == pytest.approx(opps["is_open"].sum())
    # A two-theme opportunity is split, never counted in full twice.
    assert measures.theme_shares("WASH; Agriculture", ["WASH", "Agriculture"]) == {"WASH": 0.5, "Agriculture": 0.5}
    assert measures.theme_shares("Environment", ["WASH"]) == {"Other themes": 1.0}
    assert measures.theme_shares(None, ["WASH"]) == {"No theme recorded": 1.0}


@pytest.mark.parametrize("period_type", ["quarter", "fiscal_year"])
def test_sum_indicators_by_project_and_district_add_up(con, period_type):
    """For indicators that add up (aggregation: sum), districts add up to the project and projects to all projects."""
    v = con.execute("""SELECT * FROM indicator_values WHERE period_type = ? AND disaggregation = 'total'
                       AND aggregation = 'sum'""", [period_type]).df()
    checked = 0
    for (code, source, period), g in v.groupby(["indicator_code", "source", "period"]):
        # People are counted once per district; a person can only be in one district, so sums hold.
        projects = g[(g["project_id"] != "All") & (g["district"] == "All")].set_index("project_id")["actual"]
        overall = g[(g["project_id"] == "All") & (g["district"] == "All")]["actual"]
        if len(overall) and len(projects):
            assert projects.sum() == pytest.approx(overall.iloc[0]), (code, source, period)
            checked += 1
        for project, gp in g[g["project_id"] != "All"].groupby("project_id"):
            districts = gp[gp["district"] != "All"]["actual"]
            whole = gp[gp["district"] == "All"]["actual"]
            if len(whole) and len(districts) and not (source == "derived" and CAT[code]["calculation"]["derived"]
                                                      ["method"] == "unique_people"):
                assert districts.sum() == pytest.approx(whole.iloc[0]), (code, source, period, project)
    assert checked


def test_reported_sex_breakdown_adds_up_to_the_total(con):
    v = con.execute("""SELECT indicator_code, project_id, district, period_type, period, disaggregation, actual
                       FROM indicator_values WHERE source = 'reported' AND indicator_code = 'AGR-01'""").df()
    wide = v.pivot_table(index=["project_id", "district", "period_type", "period"], columns="disaggregation",
                         values="actual", aggfunc="sum")
    wide = wide.dropna(subset=["sex=female", "sex=male", "total"])
    assert len(wide)
    assert (wide["sex=female"] + wide["sex=male"]).round(6).equals(wide["total"].round(6))


@pytest.mark.parametrize("combo", list(COMBOS))
def test_indicator_status_counts_add_up(run, combo):
    f = filters(run, combo)
    quarter = "FY2025/26 Q4"
    rows = measures.indicator_rows(run, CAT, "quarter", quarter, f)
    counts = measures.status_counts(rows)
    assert sum(v for k, v in counts.items() if k != "total") == counts["total"] == len(rows)
    # One row per indicator (per project when the view is split by project).
    key = ["indicator_code", "project_id"]
    assert not rows.duplicated(key).any()


# ---------------------------------------------------------------- 1. the same total on every page (rendered)
@pytest.mark.parametrize("combo", ["no filters", "WASH programme", "women only", "one fiscal year, men, agriculture"])
def test_people_reached_is_the_same_on_overview_and_geography(con, run, combo):
    f = filters(run, combo)
    expected = measures.people_reached(run, f.project_ids, f.start, f.end, f.district, f.sex)
    ov = render("pages/1_Programme_Overview.py", combo, con)
    value, note = tile(ov, "People reached (different people)")
    assert to_int(value) == expected["people"]
    assert f"includes {expected['pending']} people pending duplicate review" in note
    geo = render("pages/3_Geography.py", combo, con)
    table = geo.dataframe[0].value
    assert int(table["People reached"].sum()) == expected["people"]
    assert int(table["Of whom pending duplicate review"].sum()) == expected["pending"]
    assert f"{expected['people']:,} people in all" in html(geo)
    assert f"includes {expected['pending']} people pending duplicate review" in html(geo)
    if expected["unknown_district"]:
        assert measures.UNKNOWN_DISTRICT in set(table["District"])


def test_one_district_on_the_overview_matches_its_row_on_geography(con, run):
    f = filters(run, "one district")
    ov = render("pages/1_Programme_Overview.py", "one district", con)
    geo = render("pages/3_Geography.py", "one district", con)
    table = geo.dataframe[0].value.set_index("District")
    assert to_int(tile(ov, "People reached (different people)")[0]) == int(table.loc[f.district, "People reached"])


@pytest.mark.parametrize("combo", ["no filters", "one project", "one district"])
def test_pending_in_the_whole_register_is_the_same_everywhere(con, run, combo):
    register = measures.pending_in_register(run)
    ov = render("pages/1_Programme_Overview.py", combo, con)
    assert f"({register} in the whole register)" in tile(ov, "People reached (different people)")[1]
    dq = render("pages/4_Data_Quality.py", combo, con)
    assert to_int(tile(dq, "People pending duplicate review")[0]) == register
    home = render(None, combo, con)
    assert f"<b>{register}</b> people in the whole register pending duplicate review" in html(home)


@pytest.mark.parametrize("combo", ["no filters", "WASH programme", "one fiscal year, men, agriculture"])
def test_activity_spending_is_the_same_on_overview_and_geography(con, run, combo):
    f = filters(run, combo)
    expected = measures.activities_total(run, f.project_ids, f.start, f.end, f.district)
    ov = render("pages/1_Programme_Overview.py", combo, con)
    assert to_int(tile(ov, "Activities completed")[0]) == expected["activities"]
    geo = render("pages/3_Geography.py", combo, con)
    geo.selectbox(key="geo_measure").set_value("Activities completed").run()
    assert int(geo.dataframe[0].value["Activities completed"].sum()) == expected["activities"]
    geo.selectbox(key="geo_measure").set_value("Activity spending").run()
    assert geo.dataframe[0].value["Spending (RWF)"].sum() == pytest.approx(expected["spend"])


@pytest.mark.parametrize("combo", ["no filters", "one project"])
def test_pipeline_figures_are_the_same_on_summary_and_donor_page(con, run, combo):
    opps = measures.opportunities(run, S)
    home = render(None, combo, con)
    donor = render("pages/5_Donor_Pipeline.py", combo, con)
    assert tile(home, "Weighted open pipeline")[0] == tile(donor, "Weighted open pipeline")[0]
    in_90 = len(measures.deadlines_within(opps, S["as_of_date"], 90))
    assert to_int(tile(home, "Deadlines in 90 days")[0]) == in_90
    tables = [m.value for m in donor.markdown if "class='tbl'" in m.value]
    assert tables[2].split("<tbody>")[1].count("<tr>") == in_90          # the "Next 90 days" tab
    assert len(measures.overdue_actions(opps, S["as_of_date"])) == to_int(tile(donor, "Overdue next actions")[0])
    # Both pages describe the budgets the same way ("projects ending by <month>").
    gaps, cutoff = measures.pipeline_gaps(run, opps, S["as_of_date"], S)
    assert f"ending by {cutoff:%b %Y}" in html(home)
    assert f"end by {cutoff:%d %b %Y}" in html(donor)
    # The gap uses the ANNUAL budget: budget divided by the project's length in years.
    ending, _ = measures.ending_projects(run, S["as_of_date"], S)
    assert gaps["ending_budget"].sum() == pytest.approx(ending["annual_budget"].sum())
    assert ending["annual_budget"].sum() < ending["budget_rwf"].sum()


@pytest.mark.parametrize("combo", ["no filters", "WASH programme", "one project", "women only"])
def test_indicator_statuses_on_summary_match_the_indicators_page(con, run, combo):
    f = filters(run, combo)
    rows = measures.indicator_rows(run, CAT, "quarter", "FY2025/26 Q4", f)
    counts = measures.status_counts(rows)
    home = render(None, combo, con)
    for label, status in (("✔ On track", "on track"), ("▲ At risk", "at risk"), ("✖ Off track", "off track")):
        value, note = tile(home, label)
        assert (value, note) == (f"{counts.get(status, 0)}", f"of {counts['total']}")
    page = render("pages/2_Indicators.py", combo, con)
    table = next(m.value for m in page.markdown if "class='tbl'" in m.value)
    body = table.split("<tbody>")[1]
    assert body.count("<tr>") == counts["total"]
    for status, n in counts.items():
        if status != "total":
            words = {"on track": "On track", "at risk": "At risk", "off track": "Off track",
                     "target incomplete": "Target incomplete", "no target set": "No target set", "no data": "No data"}
            assert body.count(f" {words[status]}</span>") == n


@pytest.mark.parametrize("combo", ["no filters", "one district", "women only"])
def test_reconciliation_cards_add_up_on_the_indicators_page(con, run, combo):
    f = filters(run, combo)
    n = measures.reconciliation_counts(measures.reconciliation(run, f.project_ids, f.start, f.end, f.district, f.sex))
    page = render("pages/2_Indicators.py", combo, con)
    words = S["labels"]["reconciliation_status"]
    shown = [to_int(tile(page, words[s])[0]) for s in measures.RECONCILIATION_GROUPS]
    assert sum(shown) == to_int(tile(page, "Comparisons")[0]) == n["compared"]


def test_donor_report_figures_match_the_dashboard_definitions(con, run):
    import donor_report
    g = donor_report.gather(resolve_path("warehouse"), "PRJ01", "FY2025/26 Q4")
    last = g["end"] - dt.timedelta(days=1)
    people = measures.people_reached(run, ["PRJ01"], g["start"], last)
    acts = measures.activities_total(run, ["PRJ01"], g["start"], last)
    assert (g["people"]["people"], g["people"]["pending"]) == (people["people"], people["pending"])
    assert (g["acts"]["done"], g["acts"]["spend"]) == (acts["activities"], acts["spend"])
    rec = measures.reconciliation_counts(measures.reconciliation(run, ["PRJ01"], g["start"], last))
    assert g["flags"] == rec["gap above tolerance"]
