"""Summarise the evaluation sheets: SUS scores, usability tasks, manual-versus-prototype timings, report times.

The sheets in this folder are filled in during the sessions (see docs/evaluation_protocol.md):
    sus_results_template.csv      one line per participant: q1 to q10 answered 1 to 5
    task_results_template.csv     one line per participant and task
    timing_record_sheet.csv       one line per participant, method and step of the timed reporting task
    report_generation_log.csv     written automatically by the dashboard's "Generate donor report" button
Empty sheets are fine: the summary then says "no results yet".

HOW TO RUN (from the project folder)
    python evaluation/summarise.py                                   writes evaluation/evaluation_results.md
    python evaluation/summarise.py --reference PRJ03 "FY2025/26 Q4"  writes the reference answers for the timed task
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))


def sus_score(answers: list) -> float | None:
    """Standard SUS: odd items score (answer - 1), even items (5 - answer); the sum x 2.5 gives 0 to 100.
    Returns None unless all ten answers are whole numbers from 1 to 5."""
    try:
        a = [int(x) for x in answers]
    except (TypeError, ValueError):
        return None
    if len(a) != 10 or any(x < 1 or x > 5 for x in a):
        return None
    return 2.5 * sum((x - 1) if i % 2 == 0 else (5 - x) for i, x in enumerate(a))


def read(name: str) -> pd.DataFrame:
    path = HERE / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str).dropna(how="all")


def table(df: pd.DataFrame) -> str:
    if not len(df):
        return "_No results yet._"
    cols = list(df.columns)
    rows = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    rows += ["| " + " | ".join("" if pd.isna(v) else str(v) for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join(rows)


def summarise() -> Path:
    lines = ["# Evaluation results", "",
             f"*Written by `evaluation/summarise.py` on {dt.date.today():%d %B %Y} from the sheets in `evaluation/`. "
             "Do not edit by hand: correct the sheets and run it again. Results from ARDE/KUBAHO staff and from "
             "students role-playing staff are shown separately.*", ""]

    # ---------------------------------------------------------------- SUS
    sus = read("sus_results_template.csv")
    lines += ["## System Usability Scale (SUS)", ""]
    if len(sus):
        sus["sus_score"] = [sus_score([r[f"q{i}"] for i in range(1, 11)]) for _, r in sus.iterrows()]
        bad = sus[sus["sus_score"].isna()]
        ok = sus[sus["sus_score"].notna()]
        lines += [table(ok[["participant_id", "role", "participant_type", "sus_score"]]), ""]
        if len(ok):
            by = ok.groupby("participant_type")["sus_score"].agg(["count", "mean", "min", "max"]).round(1).reset_index()
            lines += ["By participant type:", "", table(by), "",
                      f"All participants: mean **{ok['sus_score'].mean():.1f}** (n = {len(ok)}). "
                      + ("Fewer than 3 participants: do not generalise." if len(ok) < 3 else ""), ""]
        if len(bad):
            lines += [f"{len(bad)} line(s) left out: not all ten answers are 1 to 5 ({', '.join(bad['participant_id'])}).",
                      ""]
    else:
        lines += ["_No results yet._", ""]

    # ---------------------------------------------------------------- tasks
    tasks = read("task_results_template.csv")
    lines += ["## Usability tasks", ""]
    if len(tasks):
        tasks["time_seconds"] = pd.to_numeric(tasks["time_seconds"], errors="coerce")
        g = tasks.groupby("task_id")
        summary = pd.DataFrame({
            "participants": g.size(),
            "completed alone": g["completed"].agg(lambda s: int((s.str.lower() == "yes").sum())),
            "with help": g["completed"].agg(lambda s: int((s.str.lower() == "with help").sum())),
            "not completed": g["completed"].agg(lambda s: int((s.str.lower() == "no").sum())),
            "median seconds": g["time_seconds"].median().round(0)}).reset_index()
        lines += [table(summary), ""]
    else:
        lines += ["_No results yet._", ""]

    # ---------------------------------------------------------------- timed reporting task
    timing = read("timing_record_sheet.csv")
    lines += ["## Timed reporting task: manual versus prototype", ""]
    if len(timing):
        timing["minutes"] = pd.to_numeric(timing["minutes"], errors="coerce")
        per = timing.groupby(["participant_id", "participant_type", "method"])["minutes"].sum().reset_index()
        totals = per.pivot_table(index=["participant_id", "participant_type"], columns="method",
                                 values="minutes").reset_index()
        lines += ["Total minutes per participant:", "", table(totals.round(1)), ""]
        steps = timing.groupby(["method", "step"])["minutes"].median().round(1).reset_index()
        lines += ["Median minutes per step:", "", table(steps), ""]
        for col in ("figures_total", "figures_wrong", "figures_missing"):
            timing[col] = pd.to_numeric(timing[col], errors="coerce")
        acc = timing.dropna(subset=["figures_total"]).groupby("method")[
            ["figures_total", "figures_wrong", "figures_missing"]].sum().reset_index()
        lines += ["Accuracy against the reference answers:", "", table(acc), ""]
    else:
        lines += ["_No results yet._", ""]

    # ---------------------------------------------------------------- machine time of the reports
    log = read("report_generation_log.csv")
    lines += ["## Donor report generation (machine time, logged automatically)", ""]
    if len(log):
        log["seconds"] = pd.to_numeric(log["seconds"], errors="coerce")
        lines += [f"{len(log)} reports generated; median {log['seconds'].median():.2f} s, slowest "
                  f"{log['seconds'].max():.2f} s.", ""]
    else:
        lines += ["_No results yet._", ""]

    out = HERE / "evaluation_results.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Written: {out}")
    return out


def reference(project_id: str, quarter: str) -> Path:
    """The figures the timed task should produce, from the prototype's own report calculations."""
    import donor_report
    from common import resolve_path
    d = donor_report.gather(resolve_path("warehouse"), project_id, quarter)
    rows = [("People reached (different registered people)", int(d["people"]["people"])),
            ("Activities completed in the quarter", int(d["acts"]["done"])),
            ("Activity spending in the quarter (RWF)", round(float(d["acts"]["spend"]))),
            ("Spending to date (RWF)", round(float(d["spend_to_date"]))),
            ("Budget (RWF)", round(float(d["project"]["budget_rwf"]))),
            ("Budget check", d["budget_check"]["message"])]
    for r in donor_report.indicator_rows(d["values"]):
        rows.append((f"{r[0]} {r[1]} ({r[2]}): target / actual / % achieved / status", " / ".join(map(str, r[3:7]))))
    out = HERE / f"reference_answers_{project_id}_{quarter.replace('/', '-').replace(' ', '_')}.csv"
    pd.DataFrame(rows, columns=["figure", "reference value"]).to_csv(out, index=False, encoding="utf-8-sig")
    print(f"Written: {out} (keep it away from participants)")
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--reference", nargs=2, metavar=("PROJECT", "QUARTER"),
                        help='write the reference answers, e.g. --reference PRJ03 "FY2025/26 Q4"')
    args = parser.parse_args()
    if args.reference:
        reference(*args.reference)
    else:
        summarise()
