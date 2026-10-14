"""Unit tests for reading sheets, duplicate matching and pseudonymisation."""

import datetime as dt

import pandas as pd
import pytest

import ingest
from common import PROJECT_ROOT, load_settings

S = load_settings()


def test_header_found_below_title_and_merged_group_header():
    rows = [("Activity monitoring log - FO02",) + (None,) * 4,
            ("Activity details", None, None, "Participants", None),
            ("Activity date", "District", "F", "M", "Total"),
            ("2024-03-12", "Kirehe", 10, 12, 22)]
    index = ingest.alias_index("activity")
    position, score = ingest.find_header(rows, index)
    assert position == 2 and score == 5


def test_ambiguous_header_takes_the_free_field():
    index = ingest.alias_index("registration")
    # In this sheet "ID" is the registration number, because "National ID" is present too.
    assigned, _ = ingest.assign_fields(["ID", "Name", "National ID"], index)
    assert assigned == {0: "reg_no", 1: "name", 2: "national_id"}
    # Here "ID" is the national ID, because "Form No." is the registration number.
    assigned, _ = ingest.assign_fields(["Form No.", "Name", "ID"], index)
    assert assigned == {0: "reg_no", 1: "name", 2: "national_id"}


def test_unknown_columns_are_reported():
    _, unmapped = ingest.assign_fields(["Date", "Favourite colour"], ingest.alias_index("activity"))
    assert unmapped == ["Favourite colour"]


def _people(*rows):
    cols = ["source_file", "source_sheet", "source_row", "reg_no", "name", "phone", "national_id", "sex",
            "district", "age", "age_source", "reg_date"]
    return pd.DataFrame([("f.xlsx", "Register", i + 2, f"R{i}", *r, "age", "2024-01-01") for i, r in enumerate(rows)],
                        columns=cols)


def test_spelling_variants_of_one_person_are_matched():
    ids = _people(("uwimana marie claire", "0781234567", None, "female", "Kirehe", 30),
                  ("uwimnaa marie claire", "0781234567", None, "female", "Kirehe", 31),
                  ("marie claire uwimana", None, None, "female", "Kirehe", 30))
    clusters = ingest.cluster_identities(ids, 88, S)
    assert len(set(clusters)) == 1


def test_same_name_different_people_are_kept_apart():
    ids = _people(("habimana eric", "0781234567", None, "male", "Huye", 30),
                  ("habimana eric", "0739876543", None, "male", "Huye", 30),      # different phone
                  ("habimana eric", None, None, "male", "Huye", 55),              # different age
                  ("habimana eric", None, None, "female", "Huye", 30),            # different sex
                  ("habimana eric", None, None, "male", "Kirehe", 30))            # different district
    assert len(set(ingest.cluster_identities(ids, 88, S))) == 5


def test_id_with_lost_last_digit_still_matches():
    ids = _people(("mugisha jean", None, "1199080012345678", "male", "Huye", 30),
                  ("mugisha jean", None, "1199080012345670", "male", "Huye", 30))
    assert len(set(ingest.cluster_identities(ids, 88, S))) == 1


def test_different_ids_are_kept_apart():
    ids = _people(("mugisha jean", None, "1199080012345678", "male", "Huye", 30),
                  ("mugisha jean", None, "1199080099999998", "male", "Huye", 30))
    assert len(set(ingest.cluster_identities(ids, 88, S))) == 2


def test_pseudonym_depends_on_the_salt_and_is_stable():
    a = ingest.pseudonym(b"salt-one", "BEN", "id:119908001234567")
    assert a == ingest.pseudonym(b"salt-one", "BEN", "id:119908001234567")
    assert a != ingest.pseudonym(b"salt-two", "BEN", "id:119908001234567")
    assert a.startswith("BEN-") and "1199" not in a


def test_salt_inside_the_project_is_refused(monkeypatch):
    monkeypatch.setenv("ARDE_SALT_FILE", str(PROJECT_ROOT / "salt.txt"))
    with pytest.raises(RuntimeError):
        ingest.load_salt()


def test_cell_values_are_kept_as_text():
    assert ingest.to_text(dt.datetime(2024, 3, 12)) == "2024-03-12"
    assert ingest.to_text(45363) == "45363"
    assert ingest.to_text(24.0) == "24"
    assert ingest.to_text(0.675) == "0.675"
