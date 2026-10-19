"""Checks for activity records and indicator reports entered on the dashboard, using the cleaner's own rules.

An entry is turned into the same form as a row read from Excel and passed through the cleaner (clean.py), then the
flags are given their severity (settings.yaml: flag_severity). So an entry is judged exactly as an Excel row is:

  problems   would hold the row back (critical), plus the rules the app enforces more strictly
             (settings.yaml: app_entry.refuse, e.g. women + men must equal the total): the entry is NOT saved,
             and the person sees each problem in plain words;
  warnings   would send the row to the review queue: the entry is saved, and the person is told.

On top of the cleaner's rules, the app checks what a form can know: the activity belongs to the chosen project,
dates are not in the future, the officer code exists, a sex is given only for indicators broken down by sex, and the
entry does not repeat one already entered (on the page or in an Excel file).
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd

from common import load_settings, load_yaml, resolve_path

APP = "entries.db"


def _label(code: str, settings: dict) -> str:
    return settings["labels"]["issue"].get(code, code.replace("_", " ").capitalize())


def _iso(v):
    return v.isoformat() if isinstance(v, (dt.date, dt.datetime)) else v


def raw_record(kind: str, rec: dict, entry_date: str | None = None, sheet: str = "check", row: int = 1) -> dict:
    """An entry in the form of a row read from Excel (the standard field names of source_mappings.yaml)."""
    base = dict(source_file=APP, source_sheet=sheet, source_row=row)
    if kind == "activity":
        return dict(base, date=_iso(rec.get("date")), planned_date=_iso(rec.get("planned_date")), entry_date=entry_date,
                    project=rec.get("project_id"), activity=rec.get("activity_id"), district=rec.get("district"),
                    sector=rec.get("sector"), cell=rec.get("cell"), village=rec.get("village"), status=rec.get("status"),
                    female=rec.get("participants_female"), male=rec.get("participants_male"),
                    total=rec.get("participants_total"), cost=rec.get("cost_rwf"), officer=rec.get("officer"))
    return dict(base, project=rec.get("project_id"), district=rec.get("district"), period=_iso(rec.get("period")),
                indicator=rec.get("indicator_code"), sex=rec.get("sex"), target=rec.get("target_value"),
                actual=rec.get("actual_value"), entered_by=rec.get("entered_by"))


def check(kind: str, rec: dict, entry_date: str | None, others: list[dict], staging: Path | None = None
          ) -> tuple[list[str], list[str]]:
    """(problems, warnings) for one entry. others = the other entries of the same kind already on the page."""
    import clean
    settings = load_settings()
    staging = Path(staging or resolve_path("staging"))
    if not (staging / "ref_project.parquet").exists():
        return ["The programme lists are not ready: run the pipeline once first (python src/pipeline.py)."], []
    cleaner = clean.Cleaner(staging, settings)
    frame = pd.DataFrame([raw_record(kind, rec, entry_date)]).astype(object)
    cleaned = (cleaner.clean_activities(frame) if kind == "activity" else cleaner.clean_indicator_results(frame))
    issues = clean.assign_severity(cleaner.log.frame(), settings)
    refuse = set(settings.get("app_entry", {}).get("refuse", []))
    problems, warnings = [], []
    for r in issues[issues["severity"].isin(["critical", "warning"])].itertuples():
        text = _label(r.issue_code, settings) + (f" ({r.detail})" if isinstance(r.detail, str) and r.detail else "")
        if r.severity == "critical" or r.issue_code in refuse:
            problems.append(text + ".")
        else:
            warnings.append(text + ": it will go to the MEAL officer's review queue.")
    today = _today(settings)
    if kind == "activity":
        project_of = dict(zip(cleaner.ref.activities["activity_id"], cleaner.ref.activities["project_id"]))
        if rec.get("activity_id") and project_of.get(rec["activity_id"]) not in (None, rec.get("project_id")):
            problems.append(f"That activity belongs to project {project_of[rec['activity_id']]}, not "
                            f"{rec.get('project_id')}.")
        if rec.get("date") and rec["date"] > today:
            problems.append(f"The activity date cannot be in the future (after {today:%d %b %Y}).")
        officers = set(pd.read_parquet(staging / "ref_officer.parquet")["officer_code"])
        if rec.get("officer") and rec["officer"] not in officers:
            problems.append(f"Officer {rec['officer']} is not in the programme master's officer list.")
        if rec.get("status") in ("completed", "delayed"):
            for f, name in (("participants_female", "women"), ("participants_male", "men")):
                if rec.get(f) is None:
                    problems.append(f"Give the number of {name} (0 if none).")
        row = cleaned.iloc[0] if len(cleaned) else None
        problems_d, warnings_d = _duplicate_activity(rec, row, others, staging)
    else:
        catalogue = {i["code"]: i for i in load_yaml("indicator_catalogue.yaml")["indicators"]}
        ind = catalogue.get(rec.get("indicator_code"), {})
        if ind.get("disaggregation") == "sex" and rec.get("sex") not in ("female", "male"):
            problems.append("This indicator is reported separately for women and men: choose the sex (one entry each).")
        if ind and ind.get("disaggregation") != "sex" and rec.get("sex"):
            problems.append("This indicator is not broken down by sex: leave the sex empty.")
        if "reported" not in (ind.get("calculation") or {}):
            problems.append("This indicator is not reported monthly (it is worked out from the records).")
        if rec.get("period") and rec["period"] > today.replace(day=1):
            problems.append("The month cannot be in the future.")
        problems_d, warnings_d = _duplicate_report(rec, others, staging)
    return problems + problems_d, warnings + warnings_d


def _today(settings: dict) -> dt.date:
    return settings.get("as_of_date") or dt.date.today()


def _duplicate_activity(rec, row, others, staging) -> tuple[list, list]:
    key = (rec.get("project_id"), rec.get("activity_id"), _iso(rec.get("date")), rec.get("district"), rec.get("village"))
    warnings = []
    for o in others:
        if (o["project_id"], o["activity_id"], o["date"], o["district"], o["village"]) == key and key[2]:
            warnings.append(f"The same activity, date and village was already entered here as {o['record_id']}: "
                            "check it is not the same activity.")
    excel = _excel_rows(staging, "clean_activity")
    if row is not None and key[2] and len(excel):
        same = excel[(excel["project_id"] == rec.get("project_id")) & (excel["activity_id"] == rec.get("activity_id"))
                     & (excel["date"].astype(str).str[:10] == key[2]) & (excel["location_id"] == row.get("location_id"))]
        for r in same.head(3).itertuples():
            warnings.append(f"An Excel record looks the same ({r.source_file}, {r.source_sheet}, row {int(r.source_row)}): "
                            "if it is the same activity, do not enter it here (it would be counted twice).")
    return [], warnings


def _duplicate_report(rec, others, staging) -> tuple[list, list]:
    key = (rec.get("project_id"), rec.get("district"), _iso(rec.get("period")), rec.get("indicator_code"), rec.get("sex"))
    problems = [f"This report is already entered as {o['record_id']}: change that entry instead."
                for o in others if (o["project_id"], o["district"], o["period"], o["indicator_code"], o["sex"]) == key]
    excel = _excel_rows(staging, "clean_indicator_result")
    if len(excel) and key[2]:
        same = excel[(excel["project_id"] == key[0]) & (excel["district"] == key[1])
                     & (excel["period"].astype(str).str[:10] == key[2]) & (excel["indicator_code"] == key[3])
                     & (excel["sex"].fillna("").astype(str) == (key[4] or ""))]
        for r in same.head(1).itertuples():
            problems.append(f"This report is already in an Excel file ({r.source_file}, {r.source_sheet}, row "
                            f"{int(r.source_row)}): correct it in that file instead, so it is not counted twice.")
    return problems, []


def _excel_rows(staging: Path, name: str) -> pd.DataFrame:
    path = staging / f"{name}.parquet"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_parquet(path)
    return df[df["source_file"] != APP]
