"""Shared test set-up: make src/ importable and generate synthetic data once per test run."""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

# The existing tests check the SYNTHETIC demo (dashboard pages, warehouse figures). The ARDE/KUBAHO workbook mode is
# tested in tests/test_arde_*.py on a small MADE-UP workbook in ARDE's layout (tests/arde_fixture.py), so no test
# needs or reads the confidential file. Run the whole suite in synthetic mode unless told otherwise.
os.environ.setdefault("ARDE_DATA_MODE", "synthetic")


@pytest.fixture(scope="session")
def synthetic(tmp_path_factory):
    """Generate the synthetic files into a temporary folder (the real data/ folder is untouched)."""
    import generate_synthetic

    root = tmp_path_factory.mktemp("synthetic")
    result = generate_synthetic.generate(root / "raw", root / "truth", quiet=True)
    result["raw"], result["truth"] = root / "raw", root / "truth"
    return result


# Tests that check the figures of the SYNTHETIC warehouse (data/warehouse), e.g. that PRJ03 is over budget. With real
# data (synthetic_mode: false) they are skipped; the rest still run on synthetic data generated in a temporary folder.
SYNTHETIC_WAREHOUSE_TESTS = {"test_dashboard.py", "test_consistency.py", "test_phase6_items.py"}


def pytest_collection_modifyitems(config, items):
    from common import load_settings
    if load_settings().get("synthetic_mode"):
        return
    skip = pytest.mark.skip(reason="checks the synthetic warehouse; synthetic_mode is off (real data)")
    for item in items:
        if item.fspath.basename in SYNTHETIC_WAREHOUSE_TESTS or "before_after" in item.name or                 item.name == "test_first_run_does_nothing_when_everything_is_ready":
            item.add_marker(skip)
