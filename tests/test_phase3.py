"""Phase 3: data-quality rules, quarantine, the DuckDB star schema, exports and the data dictionary."""

import datetime as dt
import re
import shutil

import duckdb
import pandas as pd
import pytest

import clean
import ingest
import model
import pipeline
import validate
from common import load_yaml

DICTIONARY = load_yaml("data_dictionary.yaml")
RULES = load_yaml("dq_rules.yaml")["rules"]


def build(raw, root, monkeypatch_env):
    staging, docs = root / "staging", root / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    ingest.run(raw, staging)
    clean.run(staging)
    dq = validate.run(staging, docs)
    tables = model.run(staging, root / "warehouse" / "arde.duckdb", root / "exports", docs)
    return dict(staging=staging, docs=docs, dq=dq, tables=tables, db=root / "warehouse" / "arde.duckdb",
                exports=root / "exports")


@pytest.fixture(scope="module")
def built(synthetic, tmp_path_factory):
    root = tmp_path_factory.mktemp("phase3")
    mp = pytest.MonkeyPatch()
    mp.setenv("ARDE_SALT_FILE", str(root.parent / "phase3_salt.txt"))
    out = build(synthetic["raw"], root, mp)
    mp.undo()
    out.update(truth=synthetic["truth"], raw=synthetic["raw"])
    return out


def positions(df):
    return {(f, s, int(r)) for f, s, r in zip(df["source_file"], df["source_sheet"], df["source_row"])}


# ---------------------------------------------------------------- data-quality rules
@pytest.mark.parametrize("rule", [r["id"] for r in RULES if r["id"] != "COM-01"])
def test_each_rule_catches_problems_in_the_synthetic_data(built, rule):
    results = built["dq"]["dq_results"].set_index("rule_id")
    assert results.loc[rule, "records_failed"] > 0
    assert 0 <= results.loc[rule, "score"] <= 100


def test_every_dimension_is_scored_and_averaged(built):
    dims = built["dq"]["dq_dimension_scores"].set_index("dimension")
    assert set(dims.index) == {"completeness", "validity", "consistency", "uniqueness", "timeliness",
                               "accuracy", "overall"}
    assert dims.loc["overall", "score"] == pytest.approx(dims.drop("overall")["score"].mean(), abs=0.1)


def test_rule_failures_match_the_flags(built):
    issues = pd.read_parquet(built["staging"] / "issues.parquet")
    flagged = issues[(issues["issue_code"].isin(["sum_mismatch", "female_exceeds_total"]))
                     & (issues["entity"] == "activity")]
    expected = len(positions(flagged))
    assert built["dq"]["dq_results"].set_index("rule_id").loc["CON-01", "records_failed"] == expected


def test_skipped_sheet_is_scored_and_shown_first_in_the_report(built, tmp_path, monkeypatch):
    raw = tmp_path / "raw"
    shutil.copytree(built["raw"], raw)
    from openpyxl import Workbook
    wb = Workbook()
    wb.active.title = "Activities"
    wb.active.append(["Event date", "Type of activity", "District", "Village", "Status", "Total"])
    wb.active.append(["12 Mar 24", "Hygiene promotion session", "Huye", "Kabona", "Completed", 12])
    wb.save(raw / "SYNTHETIC_activity_monitoring_EXTRA.xlsx")
    monkeypatch.setenv("ARDE_SALT_FILE", str(tmp_path.parent / "phase3_salt.txt"))
    out = build(raw, tmp_path, monkeypatch)
    rule = out["dq"]["dq_results"].set_index("rule_id").loc["COM-01"]
    assert rule["records_failed"] == 1 and rule["critical_failures"] == 1
    report = (out["docs"] / "data_quality_report.md").read_text(encoding="utf-8")
    first_section = report.split("## ")[1]
    assert first_section.startswith("1. Sheets that could not be read") and "SYNTHETIC_activity_monitoring_EXTRA" in first_section
    assert len(out["tables"]["skipped_sheets"]) == 1


# ---------------------------------------------------------------- quarantine and review queue
def test_every_critical_row_is_quarantined_with_a_reason(built):
    issues = pd.read_parquet(built["staging"] / "issues.parquet")
    critical = positions(issues[(issues["severity"] == "critical") & issues["source_row"].notna()])
    q = built["dq"]["quarantine"]
    assert positions(q) == critical
    assert q["reasons"].str.len().gt(0).all()


def test_quarantined_rows_are_not_in_any_fact_table(built):
    q = positions(built["tables"]["quarantine"])
    for name in ("fact_activity", "fact_beneficiary_service", "fact_indicator_result", "fact_opportunity"):
        assert not positions(built["tables"][name]) & q, name


def test_nothing_is_silently_dropped(built):
    # Every cleaned activity row is either a fact or in quarantine.
    cleaned = positions(pd.read_parquet(built["staging"] / "clean_activity.parquet"))
    facts = positions(built["tables"]["fact_activity"])
    quarantined = positions(built["tables"]["quarantine"][built["tables"]["quarantine"]["entity"] == "activity"])
    assert cleaned == facts | quarantined and not facts & quarantined


def test_review_rows_are_not_quarantined(built):
    assert not positions(built["dq"]["review_queue"]) & positions(built["dq"]["quarantine"])


def test_missing_target_rows_are_kept_with_a_quality_flag(built):
    f = built["tables"]["fact_indicator_result"]
    no_target = f[f["target_value"].isna()]
    assert len(no_target) > 0 and no_target["quality_flag"].str.contains("no target set").all()


# ---------------------------------------------------------------- the star schema
def test_warehouse_has_every_table_in_the_dictionary(built):
    con = duckdb.connect(str(built["db"]), read_only=True)
    names = set(con.execute("SELECT table_name FROM duckdb_tables()").df()["table_name"])
    con.close()
    assert names == set(DICTIONARY["tables"])


def test_every_fact_row_has_lineage(built):
    for name, spec in DICTIONARY["tables"].items():
        if spec["kind"] == "fact":
            df = built["tables"][name]
            assert df[["source_file", "source_sheet", "source_row"]].notna().all().all(), name


def test_keys_are_unique_and_links_are_complete(built):
    assert model.ModelBuilder(built["staging"]).check(built["tables"]) == []


def test_a_broken_link_stops_the_build(built):
    tables = {k: v.copy() for k, v in built["tables"].items()}
    tables["fact_activity"].loc[tables["fact_activity"].index[0], "activity_id"] = "ACT99"
    problems = model.ModelBuilder(built["staging"]).check(tables)
    assert any("fact_activity.activity_id" in p for p in problems)


def test_dim_date_uses_the_rwanda_fiscal_year(built):
    d = built["tables"]["dim_date"].set_index("date")
    assert d.loc[dt.date(2024, 6, 30), "fiscal_year"] == "FY2023/24"
    assert d.loc[dt.date(2024, 7, 1), "fiscal_year"] == "FY2024/25"


def test_district_level_locations_exist_for_indicator_results(built):
    loc = built["tables"]["dim_location"]
    district_rows = loc[loc["location_id"].str.startswith("DIST-")]
    assert len(district_rows) == loc["district"].nunique() and district_rows["village"].isna().all()


def test_individual_donors_are_pseudonymised_in_the_warehouse(built):
    donors = built["tables"]["dim_donor"]
    individuals = donors[donors["donor_type"] == "individual"]
    assert individuals["donor_name"].str.fullmatch(r"Individual donor #\d{3}").all()


# ---------------------------------------------------------------- exports and privacy
def test_every_table_is_exported_as_csv_and_parquet(built):
    for name in DICTIONARY["tables"]:
        assert (built["exports"] / f"{name}.csv").exists() and (built["exports"] / f"{name}.parquet").exists()
    rel = pd.read_csv(built["exports"] / "model_relationships.csv", encoding="utf-8-sig")
    assert len(rel) == len(DICTIONARY["relationships"])


def test_no_personal_data_in_exports(built):
    people = pd.read_csv(built["truth"] / "SYNTHETIC_truth_people.csv", dtype=str)
    names = {f"{s} {g}".casefold() for s, g in zip(people["surname"], people["given_name"])}
    secrets = set(people["phone"]) | set(people["phone"].str[1:]) | set(people["national_id"])
    for path in built["exports"].glob("*.csv"):
        df = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
        allowed_name = path.stem in model.NAMED_THINGS
        banned = model.PERSONAL_COLUMNS - ({"name"} if allowed_name else set())
        assert not banned & set(df.columns), path.name
        for col in df.columns:
            for value in df[col].dropna():
                assert value.casefold() not in names, (path.name, col)
                assert not any(d in secrets for d in re.findall(r"\d{9,16}", value)), (path.name, col)


# ---------------------------------------------------------------- data dictionary and pipeline
def test_data_dictionary_describes_every_table_and_column(built):
    text = (built["docs"] / "data_dictionary.md").read_text(encoding="utf-8")
    for name, spec in DICTIONARY["tables"].items():
        assert f"## `{name}`" in text
        for col in spec["columns"]:
            assert f"| `{col}` |" in text, (name, col)


def test_pipeline_runs_ingest_to_export_in_order():
    modules = [m for _, m, _, _ in pipeline.STEPS]
    assert modules[:4] == ["ingest", "clean", "validate", "model"]
