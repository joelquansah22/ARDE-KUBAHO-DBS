"""The known problems of ARDE/KUBAHO's real sample workbook (team instruction 21, section 3), checked on the real
file. SKIPPED on any computer without it: the workbook and the expected counts (data/real/expected_counts.yaml)
are confidential and never committed, so this file holds no figures from them.
"""

import datetime as dt
from pathlib import Path

import pytest
import yaml

import arde_model as am
import arde_pipeline
from common import PROJECT_ROOT, load_settings

WORKBOOK = PROJECT_ROOT / load_settings()["arde"]["workbook"]
EXPECTED = PROJECT_ROOT / "data" / "real" / "expected_counts.yaml"
pytestmark = pytest.mark.skipif(not (WORKBOOK.exists() and EXPECTED.exists()),
                                reason="the confidential ARDE/KUBAHO workbook is not on this computer")


@pytest.fixture(scope="module")
def real():
    expected = yaml.safe_load(EXPECTED.read_text(encoding="utf-8"))
    as_of = expected["as_of"] if isinstance(expected["as_of"], dt.date) else dt.date.fromisoformat(expected["as_of"])
    saved, am.as_of = am.as_of, (lambda: as_of)
    try:
        run = arde_pipeline.build(WORKBOOK, WORKBOOK.name, with_updates=False)
    finally:
        am.as_of = saved
    return run, expected


def test_rows_per_sheet(real):
    run, expected = real
    for sheet, n in expected["rows"].items():
        assert len(run["sheets"][sheet]) == n, sheet


def test_known_problems_are_flagged_at_the_known_counts(real):
    run, expected = real
    got = run["summary"].set_index("rule")["flagged"]
    for rule, n in expected["rules"].items():
        assert got[rule] == n, rule


def test_the_workbooks_own_figures_are_rebuilt(real):
    run, expected = real
    figs = run["workbook_figures"].set_index("figure")
    assert figs.loc["Direct beneficiaries", "our_value"] == expected["workbook"]["direct_beneficiaries_dashboard"]
    assert figs.loc["KPIs not recorded", "workbook_value"] == expected["workbook"]["dq_kpis_not_recorded"]
    assert (figs["rebuilt"] != "no").all()
    b = run["tables"]["fact_reach"]
    assert b.loc[b["reach_type"] == "Direct", "count"].sum() == expected["workbook"]["direct_rows_all_units"]


def test_currencies(real):
    run, expected = real
    assert sorted(run["tables"]["dim_project"]["currency"].unique()) == expected["currencies"]


def test_the_original_file_is_unchanged_by_reading():
    import hashlib
    before = hashlib.sha256(WORKBOOK.read_bytes()).hexdigest()
    arde_pipeline.build(WORKBOOK, WORKBOOK.name, with_updates=False)
    assert hashlib.sha256(WORKBOOK.read_bytes()).hexdigest() == before
