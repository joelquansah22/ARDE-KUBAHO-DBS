"""End-to-end checks of ingest + clean on a fresh synthetic dataset (temporary folders and salt)."""

import re

import pandas as pd
import pytest

import clean
import ingest
from score_cleaning import Scorer


@pytest.fixture(scope="module")
def staged(synthetic, tmp_path_factory):
    root = tmp_path_factory.mktemp("phase2")
    mp = pytest.MonkeyPatch()
    mp.setenv("ARDE_SALT_FILE", str(root.parent / "test_salt.txt"))
    ingest.run(synthetic["raw"], root / "staging")
    tables = clean.run(root / "staging")
    mp.undo()
    return dict(staging=root / "staging", docs=root, tables=tables, **synthetic)


@pytest.fixture(scope="module")
def score(staged):
    return Scorer(staged["staging"], staged["truth"], staged["raw"], staged["docs"]).run()


# ---------------------------------------------------------------- privacy
def test_no_personal_columns_in_staging(staged):
    banned = {"name", "surname", "first_name", "phone", "national_id", "dob", "contact_person", "email", "reg_no"}
    for path in staged["staging"].glob("*.parquet"):
        if path.name.startswith("ref_"):        # programme/project reference lists: "name" is a project name
            continue
        assert not banned & set(pd.read_parquet(path).columns), path.name


def test_no_names_phones_or_ids_in_any_staged_value(staged):
    people = pd.read_csv(staged["truth"] / "SYNTHETIC_truth_people.csv", dtype=str)
    names = {f"{s} {g}".casefold() for s, g in zip(people["surname"], people["given_name"])}
    # Every real phone and ID number, in every form it was written (with/without 0, last digit lost).
    secrets = set()
    for phone in people["phone"]:
        secrets |= {phone, phone[1:]}
    for nid in people["national_id"]:
        secrets |= {nid, nid[:15] + "0"}
    for path in staged["staging"].glob("*.parquet"):
        df = pd.read_parquet(path)
        for col in df.columns:
            for value in df[col].dropna().astype(str):
                digits = re.sub(r"\D", "", value)
                assert not any(d in secrets for d in re.findall(r"\d{9,16}", re.sub(r"[\s+-]", "", value))),                     (path.name, col, value)
                assert digits not in secrets, (path.name, col, value)
                assert value.casefold() not in names, (path.name, col)


def test_individual_donors_are_pseudonymised(staged):
    donors = staged["tables"]["donor"]
    individuals = donors[donors["donor_type"] == "individual"]
    assert len(individuals) == 6
    assert individuals["donor_name"].str.fullmatch(r"Individual donor #\d{3}").all()


def test_every_registration_has_hashed_keys(staged):
    regs = staged["tables"]["registration"]
    assert regs["beneficiary_key"].str.startswith("BEN-").all()
    assert regs["registration_key"].is_unique
    assert regs["beneficiary_key"].nunique() < len(regs)          # duplicates share a key


# ---------------------------------------------------------------- cleaning results
def test_all_rows_survive_and_layout_rows_are_removed(staged):
    issues = staged["tables"]["issues"]
    for code in ("blank_row_removed", "totals_row_removed", "header_preamble_row_removed", "exact_duplicate_row"):
        assert (issues["issue_code"] == code).any(), code
    acts = pd.read_csv(staged["truth"] / "SYNTHETIC_truth_activities.csv")
    assert len(staged["tables"]["activity"]) == len(acts)


@pytest.mark.parametrize("code", ["sum_mismatch", "female_exceeds_total", "negative_value", "late_entry",
                                  "status_completed_but_late", "accuracy_outlier", "missing_target",
                                  "percent_over_100", "date_outside_project_window", "district_province_mismatch",
                                  "sex_unmapped", "missing_required", "impossible_age", "report_missing",
                                  "possible_duplicate_person", "id_stored_as_number", "phone_invalid"])
def test_each_row_check_raises_flags(staged, code):
    issues = staged["tables"]["issues"]
    assert ((issues["issue_code"] == code) & (issues["action"] == "flagged")).any()


def test_cleaned_values_use_standard_codes(staged):
    acts, regs = staged["tables"]["activity"], staged["tables"]["registration"]
    assert set(acts["status"].dropna()) <= {"planned", "completed", "delayed", "cancelled"}
    assert set(regs["sex"].dropna()) == {"female", "male"}
    from common import district_to_province
    assert set(acts["district"].dropna()) <= set(district_to_province())


# ---------------------------------------------------------------- scoring (Phase 2 acceptance)
def test_genuine_errors_meet_the_95_percent_target(score):
    genuine = score["by_group"].set_index("group").loc["genuine_errors"]
    assert genuine["fixed_or_flagged_%"] >= 95


def test_no_error_type_below_90_percent(score):
    assert (score["by_type"]["fixed_or_flagged_%"] >= 90).all(), \
        score["by_type"][score["by_type"]["fixed_or_flagged_%"] < 90]


def test_no_clean_values_wrongly_changed(score):
    fc = score["false_corrections"]
    wrong = (fc["kind"] == "clean value wrongly changed").sum() if len(fc) else 0
    assert wrong <= 0.0005 * score["compared"]


def test_scorer_notices_a_wrongly_changed_value(staged, tmp_path):
    """Guard against a scorer that always says 'fine': corrupt one clean cell and expect it to be counted."""
    import shutil
    copy = tmp_path / "staging"
    shutil.copytree(staged["staging"], copy)
    acts = pd.read_parquet(copy / "clean_activity.parquet")
    log_cells = Scorer(copy, staged["truth"], staged["raw"], tmp_path).log_cells
    target = next(i for i, r in acts.iterrows() if pd.notna(r["participants_total"])
                  and not log_cells.get((r["source_file"], r["source_sheet"], int(r["source_row"]))))
    acts.loc[target, "participants_total"] += 7
    acts.to_parquet(copy / "clean_activity.parquet", index=False)
    fc, _ = Scorer(copy, staged["truth"], staged["raw"], tmp_path).false_corrections()
    assert len(fc) == 1 and fc.iloc[0]["field"] == "total"
    assert fc.iloc[0]["kind"] == "clean value wrongly changed"


def test_duplicate_matching_is_precise(score):
    configured = score["duplicates"][score["duplicates"]["configured"] == "yes"].iloc[0]  # first row = full rules
    assert configured["precision"] >= 0.95 and configured["recall"] >= 0.9
