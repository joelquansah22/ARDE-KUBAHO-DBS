"""Unit tests for the cleaning functions: dates, districts, sex and other codes, numbers."""

import datetime as dt

import pytest

from clean import FIXED, FLAGGED, parse_date, parse_number, recode, standardise_district, standardise_province
from common import load_settings

S = load_settings()


# ---------------------------------------------------------------- dates
@pytest.mark.parametrize("raw, expected, code", [
    ("2024-03-12", dt.date(2024, 3, 12), None),                       # real Excel date / ISO text
    ("2024-03-12 00:00:00", dt.date(2024, 3, 12), None),
    ("12/03/2024", dt.date(2024, 3, 12), "date_text_converted"),     # day first, as in Rwanda
    ("1/7/2023", dt.date(2023, 7, 1), "date_text_converted"),
    ("45363", dt.date(2024, 3, 12), "date_serial_converted"),
    (45363, dt.date(2024, 3, 12), "date_serial_converted"),
])
def test_dates_in_every_format(raw, expected, code):
    result = parse_date(raw, S)
    assert result.value == expected
    assert result.code == code
    assert not result.approx


def test_month_only_date_is_flagged_not_guessed():
    result = parse_date("March 2024", S)
    assert result.value == dt.date(2024, 3, 1)
    assert result.approx and result.action == FLAGGED and result.code == "date_day_unknown"


@pytest.mark.parametrize("raw", ["Jul-23", "July 2023", "2023-07", "2023-07-01", "45108"])
def test_reporting_periods(raw):
    result = parse_date(raw, S, period=True)
    assert result.value == dt.date(2023, 7, 1)
    assert result.action != FLAGGED


@pytest.mark.parametrize("raw", ["31/02/2024", "next week", "12345678", "2024-13-01"])
def test_impossible_dates_are_flagged(raw):
    result = parse_date(raw, S)
    assert result.value is None and result.action == FLAGGED


def test_blank_date_is_not_an_error():
    assert parse_date(None, S).code is None
    assert parse_date("  ", S).code is None


# ---------------------------------------------------------------- districts
@pytest.mark.parametrize("raw", ["Nyagatare", "NYAGATARE", "nyagatare", " Nyagatare ", "Nyagatare District",
                                 "Akarere ka Nyagatare", "Nyagatre", "Nyagataree"])
def test_district_variants_and_typos(raw):
    assert standardise_district(raw, S).value == "Nyagatare"


def test_district_typo_is_marked_as_corrected():
    result = standardise_district("Nyagatre", S)
    assert result.code == "district_typo_corrected" and result.action == FIXED


def test_exact_district_needs_no_change():
    assert standardise_district("Huye", S).code is None


@pytest.mark.parametrize("raw", ["Kampala", "Hyue", "xx"])
def test_unknown_or_too_different_district_is_flagged(raw):
    result = standardise_district(raw, S)
    assert result.value is None and result.action == FLAGGED


def test_province_aliases():
    assert standardise_province("Eastern Province").value == "Eastern"
    assert standardise_province("Iburasirazuba").value == "Eastern"
    assert standardise_province("Kigali").value == "Kigali City"


# ---------------------------------------------------------------- sex and other codes
@pytest.mark.parametrize("raw, expected", [("F", "female"), ("f", "female"), ("Female", "female"),
                                           ("Gore", "female"), ("M", "male"), ("Gabo", "male"), ("male ", "male")])
def test_sex_recoding(raw, expected):
    assert recode(raw, S["sex_mapping"], "sex").value == expected


@pytest.mark.parametrize("raw", ["1", "2", "X"])
def test_sex_codes_not_in_the_list_are_flagged(raw):
    result = recode(raw, S["sex_mapping"], "sex")
    assert result.value is None and result.code == "sex_unmapped" and result.action == FLAGGED


def test_status_and_stage_recoding():
    assert recode("Done", S["activity_status_mapping"], "status").value == "completed"
    assert recode("Canceled", S["activity_status_mapping"], "status").value == "cancelled"
    assert recode("CN submitted", S["donor_pipeline"]["stage_mapping"], "stage").value == "Concept note"
    assert recode("Won", S["donor_pipeline"]["stage_mapping"], "stage").value == "Awarded"
    assert recode("Yego", S["disability_mapping"], "disability").value == "yes"


# ---------------------------------------------------------------- numbers
@pytest.mark.parametrize("raw, expected", [
    ("1,250,000", 1_250_000), ("1,250,000 RWF", 1_250_000), ("RWF 1,250,000", 1_250_000),
    ("1 250 000 Frw", 1_250_000), ("45 people", 45), ("45 ", 45), ("12.5 ha", 12.5), ("72%", 72),
    ("72 %", 72), ("3O", 30), ("l5", 15), ("-174000", -174_000), ("RWF -174,000", -174_000),
])
def test_numbers_stored_as_text(raw, expected):
    assert parse_number(raw, S).value == pytest.approx(expected)


def test_usd_amount_is_detected():
    result = parse_number("USD 31,000", S)
    assert result.value == 31_000 and result.currency == "USD"


def test_letter_typo_is_reported():
    assert parse_number("3O", S).code == "number_letter_typo_fixed"


@pytest.mark.parametrize("raw", ["many", "about forty", "N/A"])
def test_text_that_is_not_a_number_is_flagged(raw):
    result = parse_number(raw, S)
    assert result.value is None and result.action == FLAGGED
