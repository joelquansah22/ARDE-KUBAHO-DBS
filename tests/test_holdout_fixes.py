"""Tests for the general fixes made after held-out set 1 (decision log D66 to D75)."""

import datetime as dt
import hashlib
from pathlib import Path

import pytest
from openpyxl import Workbook

import ingest
import pipeline
from clean import FLAGGED, IssueLog, parse_date, standardise_district
from common import PROJECT_ROOT, load_settings

S = load_settings()


# ---------------------------------------------------------------- (c) dates with month names
@pytest.mark.parametrize("raw, expected", [
    ("12 Mar 24", dt.date(2024, 3, 12)), ("12 March 2024", dt.date(2024, 3, 12)),
    ("12-Mar-2024", dt.date(2024, 3, 12)), ("1 Jul 23", dt.date(2023, 7, 1)),
    ("12th March 2024", dt.date(2024, 3, 12)), ("3rd Jan 2025", dt.date(2025, 1, 3)),
    ("5 Jan 57", dt.date(1957, 1, 5)),        # a 2-digit year above the pivot (30) is in the 1900s
    ("12.03.2024", dt.date(2024, 3, 12)),
])
def test_day_month_year_text_dates(raw, expected):
    result = parse_date(raw, S)
    assert result.value == expected and result.code == "date_text_converted" and not result.approx


def test_text_dates_are_still_rejected_when_impossible():
    assert parse_date("31 Feb 2024", S).action == FLAGGED


# ---------------------------------------------------------------- (b) and (a) headers and skipped sheets
def _workbook(tmp_path: Path, name: str, rows: list[list]) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "Activities"
    for r in rows:
        ws.append(r)
    path = tmp_path / name
    wb.save(path)
    return path


def test_a_single_matching_word_does_not_make_a_header(tmp_path):
    # A data row with one known word ("No") must not be taken as the header.
    _workbook(tmp_path, "SYNTHETIC_activity_monitoring_X.xlsx",
              [["Date of event", "Location (District)", "Attendance"], ["2024-03-12", "No", 12]])
    reader = ingest.Reader(tmp_path, S)
    reader.read_all()
    assert reader.records.get("activity", []) == []
    assert len(reader.skipped) == 1


def test_unrecognised_sheet_is_skipped_with_a_clear_message(tmp_path, capsys):
    _workbook(tmp_path, "SYNTHETIC_activity_monitoring_X.xlsx",
              [["Date of event", "Programme/Project", "Attendance"], ["2024-03-12", "PRJ01", 12]])
    _workbook(tmp_path, "SYNTHETIC_activity_monitoring_Y.xlsx",
              [["Date", "District", "Village", "Total"], ["2024-03-12", "Huye", "Kabona", 12]])
    reader = ingest.Reader(tmp_path, S)
    reader.read_all()
    out = capsys.readouterr().out
    assert "SKIPPED SYNTHETIC_activity_monitoring_X.xlsx" in out and "Date of event" in out
    assert [r["source_file"] for r in reader.records["activity"]] == ["SYNTHETIC_activity_monitoring_Y.xlsx"]


def test_issue_log_accepts_sheet_level_issues():
    log = IssueLog()
    log.add("activity", {"source_file": "f.xlsx", "source_sheet": "A", "source_row": None}, None,
            "sheet_skipped_unrecognised_layout", FLAGGED)
    assert log.frame()["source_row"].isna().all()


# ---------------------------------------------------------------- (g) totals rows
@pytest.mark.parametrize("row, is_total", [
    (["TOTAL", None, 12, 30], True),
    (["Total (RWF)", None, "1,250,000"], True),
    (["Totals:", 45, 30], True),
    (["Sub-total", 4, 5], True),
    (["Total Sanitation Campaign", "Huye", "Kabona", 12], False),   # a real row whose name starts "Total"
    (["2024-03-12", "Huye", "Total", 12], False),
])
def test_totals_rows(row, is_total):
    reader = ingest.Reader(Path("."), S)
    first = next(v for v in row if v is not None)
    assert reader.is_totals_row(tuple(row), first) is is_total


# ---------------------------------------------------------------- (f) old district names
def test_old_district_names_are_never_guessed():
    result = standardise_district("Butare", S)
    assert result.value is None and result.code == "district_legacy_name_ambiguous" and result.action == FLAGGED


def test_legacy_map_is_marked_to_be_confirmed():
    text = (PROJECT_ROOT / "config" / "district_legacy_map.yaml").read_text(encoding="utf-8")
    assert "To be confirmed with partner" in text


# ---------------------------------------------------------------- (d) ages
def test_age_is_not_computed_without_a_readable_registration_date():
    log = IssueLog()
    rec = dict(source_file="f.xlsx", source_sheet="Register", source_row=5, surname="Uwase", first_name="Grace",
               dob="1990-02-01", reg_date="sometime in March", sex="F", district="Huye")
    ids = ingest.identity_frame([rec], S, log)
    assert ids["age"].isna().all()
    assert "age_not_computable" in set(log.frame()["issue_code"])


# ---------------------------------------------------------------- 4. production pipeline vs scoring
def test_production_pipeline_has_no_generation_or_scoring_steps():
    modules = {m for _, m, _, _ in pipeline.STEPS}
    assert not modules & {"generate_synthetic", "score_cleaning", "build_templates"}


# ---------------------------------------------------------------- 1. the frozen v1 scorecard
def test_frozen_v1_scorecard_is_unchanged():
    path = PROJECT_ROOT / "docs" / "phase2_scorecard_v1_holdout1.md"
    content = path.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(content).hexdigest() == "d5ebed8311873ba8272a19d4eae4a68ee47a5bd6e3a59f75debb594113e5af35"
