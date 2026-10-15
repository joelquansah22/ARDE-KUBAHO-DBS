"""Phase 7: before/after evaluation, SUS scoring, the frozen final scorecard, first-run set-up."""

import hashlib
import sys

import pytest

from common import PROJECT_ROOT, resolve_path

sys.path.insert(0, str(PROJECT_ROOT / "evaluation"))
import summarise  # noqa: E402


# ---------------------------------------------------------------- SUS scoring
def test_sus_score_follows_the_standard_formula():
    assert summarise.sus_score([5, 1] * 5) == 100.0          # best possible
    assert summarise.sus_score([1, 5] * 5) == 0.0            # worst possible
    assert summarise.sus_score([3] * 10) == 50.0             # neutral
    assert summarise.sus_score([4, 2, 4, 2, 4, 2, 4, 2, 4, 2]) == 75.0


@pytest.mark.parametrize("answers", [[3] * 9, [3] * 9 + [6], [3] * 9 + ["x"], [3] * 9 + [None]])
def test_sus_score_rejects_incomplete_or_impossible_answers(answers):
    assert summarise.sus_score(answers) is None


def test_summary_runs_on_empty_templates(tmp_path, monkeypatch):
    for name in ("sus_results_template.csv", "task_results_template.csv", "timing_record_sheet.csv"):
        (tmp_path / name).write_text((PROJECT_ROOT / "evaluation" / name).read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(summarise, "HERE", tmp_path)
    out = summarise.summarise()
    assert "No results yet" in out.read_text(encoding="utf-8")


def test_summary_scores_filled_in_sheets_by_participant_type(tmp_path, monkeypatch):
    header = (PROJECT_ROOT / "evaluation" / "sus_results_template.csv").read_text(encoding="utf-8").strip()
    rows = ["P1,MEAL officer,ARDE staff,yes,2026-11-01,4,2,4,2,4,2,4,2,4,2,",
            "P2,Programme manager,student role-play,yes,2026-11-01,3,3,3,3,3,3,3,3,3,3,"]
    (tmp_path / "sus_results_template.csv").write_text("\n".join([header] + rows) + "\n", encoding="utf-8")
    monkeypatch.setattr(summarise, "HERE", tmp_path)
    text = summarise.summarise().read_text(encoding="utf-8")
    assert "75.0" in text and "50.0" in text and "student role-play" in text
    assert "Fewer than 3 participants" in text


# ---------------------------------------------------------------- before / after
@pytest.fixture(scope="module")
def before_after():
    if not (resolve_path("staging") / "ingested_activity.parquet").exists():
        pytest.skip("Run python src/pipeline.py first")
    import evaluate
    return evaluate.evaluate_set("main", resolve_path("staging"), resolve_path("ground_truth")).set_index(
        ["records", "measure"])


def test_cleaning_lowers_invalid_values_and_duplicates(before_after):
    for (records, measure), r in before_after.iterrows():
        if measure.startswith(("Invalid values", "Duplicates", "Consistency")):
            assert r["after_cleaning"] < r["raw_files"], (records, measure)


def test_before_after_covers_the_four_proposal_measures(before_after):
    measures = {m.split(":")[0] for _, m in before_after.index}
    assert measures == {"Completeness", "Invalid values", "Consistency failures", "Duplicates"}


# ---------------------------------------------------------------- final held-out scorecard is frozen
def test_final_held_out_scorecard_is_frozen():
    path = PROJECT_ROOT / "docs" / "phase7_final_holdout_scorecard.md"
    content = path.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(content).hexdigest() == "4cdbac6714fab1bee00d8ae1a8d2081a524721bd46507b3b94da47d75db05494"


def test_final_round_refuses_to_overwrite_its_scorecard():
    import score_cleaning
    with pytest.raises(SystemExit):
        score_cleaning.final_round()


# ---------------------------------------------------------------- first run
def test_first_run_does_nothing_when_everything_is_ready():
    if not resolve_path("warehouse").exists():
        pytest.skip("Run python src/pipeline.py first")
    import first_run
    assert first_run.main() == 0


def test_dashboard_only_accepts_connections_from_this_laptop():
    assert 'address = "127.0.0.1"' in (PROJECT_ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
