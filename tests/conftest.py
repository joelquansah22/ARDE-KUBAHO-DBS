"""Shared test set-up: make src/ importable and generate synthetic data once per test run."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


@pytest.fixture(scope="session")
def synthetic(tmp_path_factory):
    """Generate the synthetic files into a temporary folder (the real data/ folder is untouched)."""
    import generate_synthetic

    root = tmp_path_factory.mktemp("synthetic")
    result = generate_synthetic.generate(root / "raw", root / "truth", quiet=True)
    result["raw"], result["truth"] = root / "raw", root / "truth"
    return result
