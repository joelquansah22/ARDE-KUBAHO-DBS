"""Held-out test set generation, flag severity levels and duplicate certainty."""

import pandas as pd
import pytest

import generate_synthetic
import ingest
from clean import assign_severity
from common import load_settings

S = load_settings()


@pytest.fixture(scope="module")
def holdout(tmp_path_factory):
    root = tmp_path_factory.mktemp("holdout")
    result = generate_synthetic.generate(root / "raw", root / "truth", quiet=True,
                                         config_name="synthetic_holdout.yaml")
    result["raw"], result["truth"] = root / "raw", root / "truth"
    return result


# ---------------------------------------------------------------- held-out set
def test_holdout_matches_its_documented_fingerprint(holdout):
    cfg = generate_synthetic.load_synthetic_config("synthetic_holdout.yaml")
    assert holdout["fingerprint"] == cfg["expected_fingerprint"]


def test_holdout_differs_from_the_main_set(holdout, synthetic):
    assert holdout["fingerprint"] != synthetic["fingerprint"]


def test_holdout_has_the_unseen_officer_and_new_mess(holdout):
    assert "SYNTHETIC_activity_monitoring_FO05.xlsx" in holdout["files"]
    log = pd.read_csv(holdout["truth"] / "SYNTHETIC_injected_errors_log.csv", dtype=str, keep_default_na=False)
    for etype in ("date_new_format", "district_old_name", "district_abbreviation", "namesake_different_person"):
        assert (log["error_type"] == etype).any(), etype
    dups = log[log["error_type"] == "duplicate_beneficiary"]["detail"]
    assert dups.str.contains("nickname").any() and dups.str.contains("swapped").any()


def test_holdout_switches_do_not_change_the_main_config():
    main = generate_synthetic.load_synthetic_config("synthetic.yaml")
    assert "holdout_mess" not in main and "FO05" not in main["field_officers"]


def test_scoring_survives_a_crash_and_sets_aside_unreadable_files(holdout, tmp_path, monkeypatch):
    from score_cleaning import run_pipeline_on
    monkeypatch.setenv("ARDE_SALT_FILE", str(tmp_path.parent / "holdout_test_salt.txt"))
    run = run_pipeline_on(holdout["raw"], tmp_path / "staging")
    if run["crash"]:
        assert "SYNTHETIC_activity_monitoring_FO05.xlsx" in run["set_aside"]
    assert (tmp_path / "staging" / "clean_activity.parquet").exists()


# ---------------------------------------------------------------- severity
def _issues(*rows):
    cols = ["entity", "source_file", "source_sheet", "source_row", "field", "issue_code", "action"]
    return pd.DataFrame([("activity", "f.xlsx", "A", r, fld, code, act) for r, fld, code, act in rows], columns=cols)


def test_three_severity_levels():
    issues = assign_severity(_issues((2, "male", "negative_value", "flagged"),
                                     (3, "total", "sum_mismatch", "flagged"),
                                     (4, "entry_date", "late_entry", "flagged"),
                                     (5, "date", "date_text_converted", "fixed")), S)
    assert list(issues["severity"]) == ["critical", "warning", "info", None]


def test_unlisted_flag_is_a_warning_so_nothing_is_silent():
    issues = assign_severity(_issues((2, "x", "some_new_check", "flagged")), S)
    assert issues["severity"].iloc[0] == "warning"


def test_district_resolved_from_village_is_downgraded_to_warning():
    issues = assign_severity(_issues((2, "district", "district_unrecognised", "flagged"),
                                     (2, "district", "district_filled_from_village", "fixed"),
                                     (3, "district", "district_unrecognised", "flagged")), S)
    assert list(issues["severity"]) == ["warning", None, "critical"]


# ---------------------------------------------------------------- duplicate certainty
def _ids(*rows):
    cols = ["source_file", "source_sheet", "source_row", "name", "phone", "national_id", "cluster",
            "duplicate_group_size"]
    return pd.DataFrame([("f.xlsx", "R", i, *r) for i, r in enumerate(rows)], columns=cols)


def test_same_id_is_a_certain_duplicate():
    ids = _ids(("uwase grace", None, "1199070012345678", 1, 2), ("uwas grace", None, "1199070012345670", 1, 2))
    assert ingest.duplicate_certainty(ids, S) == {1: "certain"}


def test_name_match_without_id_or_phone_is_only_suspected():
    ids = _ids(("uwase grace", None, None, 1, 2), ("uwase grace", None, None, 1, 2))
    assert ingest.duplicate_certainty(ids, S) == {1: "suspected"}
