"""Phase 6 items confirmed before Phase 7: the over-budget warning, plain messages for empty selections, the
missing-pipeline message, "How to read this page", "Data last updated" on every page, A4 landscape printing."""

import datetime as dt
import re
import sys
from pathlib import Path

import duckdb
import pytest
from streamlit.testing.v1 import AppTest

import measures
from common import load_settings, load_yaml, resolve_path

APP = Path(__file__).resolve().parent.parent / "dashboard" / "app.py"
S = load_settings()
PAGES = {None: "home", "pages/1_Programme_Overview.py": "overview", "pages/2_Indicators.py": "indicators",
         "pages/3_Geography.py": "geography", "pages/4_Data_Quality.py": "data_quality",
         "pages/5_Donor_Pipeline.py": "donor_pipeline"}


@pytest.fixture(scope="module")
def run():
    path = resolve_path("warehouse")
    if not path.exists():
        pytest.skip("Build the warehouse first: python src/pipeline.py")
    con = duckdb.connect(str(path), read_only=True)
    yield lambda sql, *p: con.execute(sql, list(p)).df()
    con.close()


def render(page=None, **state):
    at = AppTest.from_file(str(APP), default_timeout=120)
    for k, v in state.items():
        at.session_state[k] = v
    if page:
        at.switch_page(page)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def text(at) -> str:
    return " ".join(m.value for m in at.markdown) + " " + " ".join(m.value for m in at.info) + " " + \
        " ".join(c.value for c in at.caption)


# ---------------------------------------------------------------- a. over budget
def test_one_project_is_over_budget_by_about_ten_percent(run):
    b = measures.budget_status(run, ["PRJ01", "PRJ02", "PRJ03", "PRJ04", "PRJ05"], S["as_of_date"], S)
    over = b[b["status"] == "over budget"]
    assert list(over["project_id"]) == ["PRJ03"]
    assert 105 <= over["pct_spent"].iloc[0] <= 115
    assert re.fullmatch(r"over budget by RWF [\d,]+ \(\d+%\)", over["message"].iloc[0])
    assert over["over_by"].iloc[0] == pytest.approx(over["spent"].iloc[0] - over["budget"].iloc[0])
    assert (b.loc[b["status"] == "within budget", "pct_spent"] <= S["budget_monitoring"]["over_budget_pct"]).all()


def test_over_budget_warning_is_shown_with_a_warning_status(run):
    message = measures.budget_status(run, ["PRJ03"], S["as_of_date"], S)["message"].iloc[0]
    overview = text(render("pages/1_Programme_Overview.py"))
    assert f"▲ Warning: {message}" in overview          # the budget table: symbol and words, not colour alone
    assert f"▲ PRJ03 {message}" in overview             # the budget tile
    assert f"{message}" in text(render())                # the executive summary


# ---------------------------------------------------------------- d. empty selections, help, footer, print
@pytest.mark.parametrize("page", list(PAGES))
def test_pages_give_plain_messages_for_an_empty_selection(run, page):
    at = render(page, f_dates=(dt.date(2022, 1, 1), dt.date(2022, 3, 31)))     # before any data
    if PAGES[page] in ("overview", "geography"):
        assert "Nothing was recorded" in text(at)
    if PAGES[page] == "indicators":
        assert "No indicator values for this period and selection." in text(at) or "Nothing to compare" in text(at)


@pytest.mark.parametrize("page", list(PAGES))
def test_every_page_has_how_to_read_and_data_last_updated(run, page):
    at = render(page)
    assert any(e.label == "How to read this page" for e in at.expander)
    assert "Data last updated" in text(at)
    assert any(e.label.startswith("Source files (") for e in at.expander)
    assert load_yaml("page_help.yaml")[PAGES[page]].strip()


def test_a_friendly_message_when_the_pipeline_has_not_been_run(tmp_path, monkeypatch):
    sys.path.insert(0, str(APP.parent))
    import ui
    monkeypatch.setattr(ui, "db_path", lambda: tmp_path / "missing.duckdb")
    at = AppTest.from_file(str(APP), default_timeout=120)
    at.run()
    assert not at.exception
    assert any("The figures have not been prepared yet" in i.value for i in at.info)


def test_pages_print_on_a4_landscape():
    import ui
    assert "@page {size: A4 landscape" in ui.CSS
