"""ARDE/KUBAHO workbook mode: the whole run with one command (data_mode: arde).

WHAT THIS SCRIPT DOES
---------------------
1. Finds the workbook in use: the newest one added on the Upload Excel page, or the file named in
   config/settings.yaml (arde.workbook). Reads a COPY of it (src/arde_reader.py); the original is never changed.
2. Applies the KPI updates made on the dashboard since that workbook was added (src/arde_store.py).
3. Builds the results-chain tables and runs this format's data-quality rules (src/arde_model.py).
4. Compares the working register with the KPIs and Results sheets (source of truth), and the workbook's own
   Dashboard and Data Quality figures with ours.
5. Saves everything in data/real/warehouse/arde_workbook.duckdb, exports CSV/Parquet to data/real/exports/, and
   writes docs/arde_sample_profile.md (gitignored: it quotes the data) and docs/arde_data_dictionary.md (column
   names and meanings only; no data).

Everything written from the data stays under data/real/ or in the gitignored profile. Nothing here is committed.

HOW TO RUN
    python src/pipeline.py          (runs this when data_mode is arde)
    python src/arde_pipeline.py     (the same, directly)
"""

from __future__ import annotations

import datetime as dt
import sys
import time
from pathlib import Path

import pandas as pd

import arde_model as am
import arde_reader
import arde_store
from common import PROJECT_ROOT, load_settings
from model import export, save_warehouse

KEYS = {"dim_project": ["project_code"], "fact_result": ["result_code"], "fact_kpi": ["kpi_code"],
        "fact_project_activity": ["activity_code"]}
RELATIONSHIPS = [("dim_project_district.project_code", "dim_project.project_code"),
                 ("fact_result.project_code", "dim_project.project_code"),
                 ("fact_kpi.project_code", "dim_project.project_code"),
                 ("fact_kpi.result_code", "fact_result.result_code"),
                 ("fact_project_activity.project_code", "dim_project.project_code"),
                 ("fact_project_activity.output_code", "fact_result.result_code"),
                 ("fact_reach.project_code", "dim_project.project_code"),
                 ("fact_contribution.project_code", "dim_project.project_code")]


def path(key: str) -> Path:
    return PROJECT_ROOT / load_settings()["arde"][key]


def check(t: dict[str, pd.DataFrame]) -> list[str]:
    """Unique codes and lineage on every row. Problems stop the run (nothing is saved)."""
    problems = []
    for name, cols in KEYS.items():
        dup = t[name].duplicated(cols, keep=False)
        if dup.any():
            problems.append(f"{name}: {int(dup.sum())} rows share a code ({', '.join(t[name].loc[dup, cols[0]].head(3))}).")
    for name, df in t.items():
        if name.startswith(("fact_", "dim_project")) and name != "dim_project_district":
            for col in ("source_file", "source_sheet", "source_row"):
                if col not in df or df[col].isna().any():
                    problems.append(f"{name}: lineage column {col} is missing or blank.")
    return problems


def build(source, source_file: str | None = None, uploaded_at: str | None = None, with_updates: bool = True) -> dict:
    """Read, model and check a workbook. Returns everything the save and the upload check need."""
    sheets = arde_reader.read_workbook(source, source_file)
    updates = arde_store.current_updates(since=uploaded_at) if with_updates else None
    t = am.build_tables(sheets, updates)
    flags, summary = am.run_rules(t)
    return {"sheets": sheets, "tables": t, "flags": flags, "summary": summary, "score": am.dq_score(summary),
            "source_of_truth": am.compare_register(sheets), "workbook_figures": am.workbook_figures(sheets, t),
            "updates_applied": 0 if updates is None else len(updates), "problems": check(t)}


def warehouse_tables(run: dict, workbook: Path, uploaded_at: str | None) -> dict[str, pd.DataFrame]:
    t = dict(run["tables"])
    t["dq_rule_results"] = run["flags"]
    t["dq_rule_summary"] = run["summary"]
    t["source_of_truth_comparison"] = run["source_of_truth"]
    t["workbook_figures_comparison"] = run["workbook_figures"].astype({"workbook_value": float, "our_value": float})
    t["kpi_change_history"] = pd.DataFrame(arde_store.table("change_history"),
                                           columns=["row_id", "changed_at", "changed_by", "table_name", "record_id",
                                                    "action", "field", "old_value", "new_value"])
    t["run_info"] = pd.DataFrame([{"workbook": workbook.name, "workbook_uploaded_at": uploaded_at or "as received",
                                   "built_at": dt.datetime.now().isoformat(timespec="seconds"),
                                   "as_of": am.as_of().isoformat(), "dq_score": run["score"],
                                   "kpi_updates_applied": run["updates_applied"]}])
    t["sheet_inventory"] = pd.DataFrame(
        [{"sheet": s, "rows": len(run["sheets"][s]) if s in run["sheets"] and isinstance(run["sheets"][s], pd.DataFrame)
          else None, "role": ("compare only (calculated)" if s in am.fmt()["compare_only_sheets"] else "imported")}
         for s in run["sheets"]["_sheet_list"]])
    return t


def main(argv: list[str] | None = None) -> int:
    started = time.perf_counter()
    workbook, uploaded_at = arde_store.current_workbook()
    if not workbook.exists():
        print(f"STOPPED: the ARDE/KUBAHO workbook was not found at {workbook}. Copy it into data/real/ (see "
              "docs/real_data_checklist.md), or set data_mode: synthetic in config/settings.yaml for the demo.")
        return 1
    print(f"[run ] Reading a copy of {workbook.name} ...")
    run = build(workbook, workbook.name, uploaded_at)
    if run["problems"]:
        print("STOPPED: " + " ".join(run["problems"]))
        return 1
    tables = warehouse_tables(run, workbook, uploaded_at)
    save_warehouse(tables, path("warehouse"))
    export({k: v for k, v in tables.items() if k.startswith(("dim_", "fact_"))}, path("exports"), RELATIONSHIPS)
    import arde_profile
    arde_profile.write(run, tables, PROJECT_ROOT / load_settings()["arde"]["profile_doc"])
    arde_profile.write_dictionary(tables, PROJECT_ROOT / "docs" / "arde_data_dictionary.md")
    s = run["summary"]
    print(f"[done] {len(run['tables']['dim_project'])} projects, {len(run['tables']['fact_kpi'])} KPIs; "
          f"{int(s.loc[s['level'] == 'held_back', 'flagged'].sum())} values held back, "
          f"{int(s.loc[s['level'] == 'review', 'flagged'].sum())} for review; data-quality score {run['score']:.1f}%; "
          f"{run['updates_applied']} dashboard KPI updates applied. ({time.perf_counter() - started:.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
