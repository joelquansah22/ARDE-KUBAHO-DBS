"""Visual design: brand colours in config/theme.yaml, contrast, fixed status colours, the untouched banner."""

import re
import sys
from pathlib import Path

import pytest

import theme
from common import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT / "dashboard"))
import ui  # noqa: E402

BANNER_CSS = (".synthetic-banner {background: #fff3cd; border: 1px solid #e0b100; color: #5c4400; padding: 0.3rem 0.8rem;\n"
              "                   border-radius: 6px; font-weight: 600; font-size: 0.85rem; margin-bottom: 0.4rem;}")


def test_streamlit_theme_is_written_from_theme_yaml(tmp_path):
    t = theme.load_theme()
    current = (PROJECT_ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    assert theme.theme_toml(t).strip() in current.replace("\r\n", "\n")          # rerun src/theme.py if this fails
    assert 'address = "127.0.0.1"' in current                                    # other sections kept


def test_every_colour_pair_in_use_passes_wcag_aa():
    report = theme.contrast_report()
    failing = [r for r in report if not r["passes"]]
    # Only the raw logo colours fail, and they are never used for text or chart marks (darker shades are used).
    assert {r["what"] for r in failing} == {"logo green as text (not used for text)",
                                            "logo yellow as a chart colour (not used)",
                                            "logo blue as text (not used for text)"}
    assert theme.contrast("#000000", "#FFFFFF") == pytest.approx(21.0)


def test_status_colours_stay_fixed_and_separate_from_the_brand():
    assert theme.load_theme()["status"] == {"on_track": "#1A7F37", "at_risk": "#9A6700", "off_track": "#CF222E",
                                            "no_target": "#57606A"}
    assert ui.CHART[0] not in theme.load_theme()["status"].values()
    for status, (symbol, words, colour) in ui.STATUS.items():
        assert symbol and words                                                 # never colour alone


def test_no_colour_is_hard_coded_in_the_pages():
    for path in list((PROJECT_ROOT / "dashboard" / "pages").glob("*.py")) + [PROJECT_ROOT / "dashboard" / "home.py"]:
        found = re.findall(r"#[0-9a-fA-F]{6}\b", path.read_text(encoding="utf-8"))
        assert set(found) <= {"#FFFFFF"}, (path.name, found)


def test_the_synthetic_banner_is_exactly_as_it_was():
    assert BANNER_CSS in ui.CSS
    assert "synthetic-banner" not in (PROJECT_ROOT / "dashboard" / "theme.css").read_text(encoding="utf-8")


def test_logo_only_when_the_file_exists(monkeypatch):
    calls = []
    monkeypatch.setattr(ui.st, "logo", lambda *a, **k: calls.append(a))
    monkeypatch.setitem(ui.THEME, "logo", "assets/does_not_exist.png")
    ui.sidebar_logo()
    assert calls == []
    monkeypatch.setitem(ui.THEME, "logo", "assets/arde_logo.png")
    if (PROJECT_ROOT / "assets" / "arde_logo.png").exists():
        ui.sidebar_logo()
        assert len(calls) == 1


def test_sparkline_and_trend_words():
    assert ui.sparkline([1]) == ""
    svg = ui.sparkline([1, 3, 2, 5])
    assert svg.startswith("<svg") and ui.COLOURS["primary"] in svg
    assert ui.trend([10, 10, 10, 12, 12, 12]) == "▲ up 20% on the previous 3 months"
    assert ui.trend([10, 10, 10, 5, 5, 5]) == "▼ down 50% on the previous 3 months"
    assert ui.trend([1, 2]) == ""                                                # too short to compare


def test_theme_css_has_no_unfilled_placeholders():
    css = ui._theme_css()
    assert not re.findall(r"\{[a-z_]+\}", css)
