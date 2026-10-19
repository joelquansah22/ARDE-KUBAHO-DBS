"""Redesign (team instruction 20): the Home landing page, the menu grouped in sections, Material icons, lighter colours."""

import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import theme
from common import load_yaml, resolve_path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "dashboard" / "app.py"
MENU = load_yaml("page_help.yaml")["menu"]
PAGES = [p for section in MENU for p in section["pages"]]


@pytest.fixture(scope="module")
def home():
    if not resolve_path("warehouse").exists():
        pytest.skip("Build the warehouse first: python src/pipeline.py")
    at = AppTest.from_file(str(APP), default_timeout=180)
    at.run()                                             # no page chosen: the landing page
    assert not at.exception, [e.value for e in at.exception]
    return at


def tile_value(at, label: str) -> str:
    html = next(m.value for m in at.markdown if f"<div class='tile-label'>{label}</div>" in m.value)
    return re.search(r"<div class='tile-value'>(.*?)</div>", html).group(1)


# ---------------------------------------------------------------- the menu
def test_menu_has_home_on_top_then_insights_data_and_donors():
    assert [s["section"] for s in MENU] == ["", "Insights", "Data", "Donors"]
    assert [p["title"] for p in MENU[0]["pages"]] == ["Home"]
    assert [p["title"] for p in MENU[1]["pages"]] == ["Executive summary", "Programme overview", "Indicators",
                                                      "Geography", "Data quality"]
    assert [p["title"] for p in MENU[2]["pages"]] == ["Data entry", "Upload Excel", "Records"]
    assert [p["title"] for p in MENU[3]["pages"]] == ["Donor pipeline", "Donor entry"]


def test_every_menu_page_exists_with_a_material_icon_and_a_description():
    for p in PAGES:
        assert (ROOT / "dashboard" / p["file"]).is_file(), p["file"]
        assert re.fullmatch(r":material/[a-z_]+:", p["icon"]), p["icon"]
        assert p["description"].strip()
    assert len({p["url"] for p in PAGES}) == len(PAGES)                 # every page its own address


def test_no_emoji_icons_left_in_the_dashboard():
    for path in (ROOT / "dashboard").rglob("*.py"):
        for icon in re.findall(r"icon=\"([^\"]+)\"", path.read_text(encoding="utf-8")):
            assert icon.startswith(":material/"), (path.name, icon)


# ---------------------------------------------------------------- the Home page
def test_home_is_the_landing_page_with_the_welcome_header(home):
    text = " ".join(m.value for m in home.markdown)
    assert "Programme and Donor Data System" in text and "<div class='welcome'>" in text
    assert any("Demonstration data. Synthetic records" in m.value for m in home.markdown)    # banner unchanged


def test_home_links_to_every_page_in_its_section(home):
    targets = [link.page for link in home.get("page_link")]             # the page addresses
    for p in PAGES[1:]:                                                  # every page except Home itself
        assert p["url"] in targets, p["title"]


def test_home_needs_attention_links(home):
    labels = [link.label for link in home.get("page_link")]
    for words in ("records to review", "held back for correction", "overdue donor actions", "donor deadlines in 30 days"):
        assert any(words in label for label in labels), words


def test_home_figures_are_the_same_as_on_their_own_pages(home):
    summary = AppTest.from_file(str(APP), default_timeout=180)
    summary.switch_page("summary.py")
    summary.run()
    overview = AppTest.from_file(str(APP), default_timeout=180)
    overview.switch_page("pages/1_Programme_Overview.py")
    overview.run()
    assert tile_value(home, "Weighted open pipeline") == tile_value(summary, "Weighted open pipeline")
    assert tile_value(home, "Data-quality score") == tile_value(summary, "Data-quality score")
    assert tile_value(home, "People reached (different people)") == tile_value(overview, "People reached (different people)")
    on_track = tile_value(summary, "✔ On track")
    assert tile_value(home, "✔ Indicators on track").split(" of ")[0] == on_track


# ---------------------------------------------------------------- lighter colours
def test_lighter_colours():
    c = theme.load_theme()["colours"]
    assert c["page_background"] == c["card_background"] == "#FFFFFF"
    assert theme.luminance(c["sidebar_background"]) > 0.9                # a very light tint, not a green block
    toml = (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    assert f'backgroundColor = "{c["sidebar_background"]}"' in toml
