"""Synthetic KoboToolbox exports, to test the Kobo import adapter (testing only).

WHAT THIS SCRIPT DOES
---------------------
Builds a test set in data/kobo_test/: a copy of the main synthetic raw files in which two officers' sources are
replaced by KoboToolbox exports made from the same TRUE records (the main set's answer key):

  FO01's activity monitoring file  ->  an export of forms/activity_monitoring_kobo.xlsx, "XML values and headers"
  the WASH indicator report file   ->  an export of forms/indicator_report_kobo.xlsx, "Labels" (headers and values)

So both export settings are tested. The forms' checks (dropdowns, dates not in the future, women + men = total, no
negative values) mean the Excel kinds of mess cannot occur; what Kobo cannot prevent is injected instead, at the
rates in config/synthetic.yaml (kobo:) and logged in the answer key:
  - the same form submitted twice (identical answers, a new submission ID): should be removed as a duplicate;
  - the optional cost left blank: should stay blank, never be guessed.
Kobo's own columns (start, end, _id, _uuid, _submission_time, _validation_status...) are included, as in a real export.

Answer key: data/kobo_test/ground_truth/SYNTHETIC_kobo_truth_*.csv (one row per export row, with the true values).

HOW TO RUN
    python src/generate_kobo_exports.py      (after python src/generate_synthetic.py)
"""

from __future__ import annotations

import datetime as dt
import random
import shutil
import uuid
from pathlib import Path

import pandas as pd
from openpyxl import Workbook

from common import load_yaml, resolve_path

PREFIX = "SYNTHETIC_"
STAMP = "2026-06-30-17-00-00"
ACTIVITY_FILE = f"{PREFIX}ARDE_activity_monitoring_-_all_versions_-_xml_values_-_{STAMP}.xlsx"
INDICATOR_FILE = f"{PREFIX}ARDE_indicator_report_WASH_-_all_versions_-_labels_-_{STAMP}.xlsx"
REPLACED = ["SYNTHETIC_activity_monitoring_FO01.xlsx", "SYNTHETIC_indicator_reports_WASH.xlsx"]
META = ["__version__", "_id", "_uuid", "_submission_time", "_validation_status", "_notes", "_status",
        "_submitted_by", "_tags", "_index"]


def _iso(v) -> str | None:
    return None if v is None or (isinstance(v, float) and pd.isna(v)) or v == "" else str(v)[:10]


def _num(v):
    return None if v is None or (isinstance(v, float) and pd.isna(v)) or v == "" else float(v)


def write_export(path: Path, sheet: str, header: list, rows: list[list]) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = sheet[:31]
    ws.append(header)
    for r in rows:
        ws.append(r)
    wb.save(path)


def activity_export(truth: pd.DataFrame, cfg: dict, rnd: random.Random) -> tuple[list, list, list]:
    acts = truth[truth["source_file"] == REPLACED[0]].sort_values(["entry_date", "record_id"])
    header = ["start", "end", "entry_date", "officer", "project", "activity", "status", "planned_date", "date",
              "district", "sector", "cell", "village", "female", "male", "total", "cost", "comment"] + META
    rows, key, n = [], [], 0
    for r in acts.itertuples():
        done = r.status in ("completed", "delayed")
        blank_cost = r.status != "planned" and rnd.random() < cfg["optional_cost_blank_rate"]
        cost = None if r.status == "planned" or blank_cost else _num(r.cost_rwf)
        answers = [r.entry_date, r.field_officer, r.project_id, r.activity_id, r.status, _iso(r.planned_date),
                   _iso(r.date), r.district, r.sector, r.cell, r.village,
                   int(r.participants_female) if done else None, int(r.participants_male) if done else None,
                   int(r.participants_total) if done else None, cost, None]
        truth_row = dict(record_id=r.record_id, date=_iso(r.date), planned_date=_iso(r.planned_date),
                         entry_date=_iso(r.entry_date), project_id=r.project_id, activity_id=r.activity_id,
                         district=r.district, village=r.village, status=r.status,
                         participants_female=_num(r.participants_female) if done else None,
                         participants_male=_num(r.participants_male) if done else None,
                         participants_total=_num(r.participants_total) if done else None,
                         cost_rwf=cost, injected="optional cost left blank" if blank_cost else "")
        copies = 2 if rnd.random() < cfg["duplicate_submission_rate"] else 1
        for c in range(copies):
            n += 1
            submitted = dt.datetime.fromisoformat(str(r.entry_date)[:10]) + dt.timedelta(hours=9 + c, minutes=rnd.randint(0, 59))
            meta = ["v1", 100000 + n, str(uuid.UUID(int=rnd.getrandbits(128))), submitted.isoformat(), "", "",
                    "submitted_via_web", r.field_officer.lower(), "", n]
            start = submitted - dt.timedelta(minutes=rnd.randint(3, 15))
            rows.append([start.isoformat() + "+02:00", submitted.isoformat() + "+02:00", *answers, *meta])
            key.append(dict(source_file=ACTIVITY_FILE, source_row=len(rows) + 1, **truth_row,
                            duplicate_of_row=(len(rows)) if c else None))
    return header, rows, key


def indicator_export(truth: pd.DataFrame, cfg: dict, rnd: random.Random, staging: Path) -> tuple[list, list, list]:
    reports = truth[(truth["source_file"] == REPLACED[1]) & (truth["submitted"].astype(str) == "True")]
    projects = pd.read_parquet(staging / "ref_project.parquet").set_index("project_id")["name"]
    names = {i["code"]: " ".join(str(i["name"]).split()) for i in load_yaml("indicator_catalogue.yaml")["indicators"]}
    # A "Labels" export: question labels as headers, choice labels as values.
    header = ["start", "end", "entry_date", "Officer", "Project", "District", "Reporting period", "Indicator", "Sex",
              "Monthly target", "Achieved", "Comments"] + META
    rows, key = [], []
    for n, r in enumerate(reports.sort_values(["period", "district", "indicator_code"]).itertuples(), 1):
        period = dt.date.fromisoformat(str(r.period)[:10])
        filled = (pd.Timestamp(period) + pd.offsets.MonthEnd(1)).date() + dt.timedelta(days=rnd.randint(1, 10))
        submitted = dt.datetime.combine(filled, dt.time(10, rnd.randint(0, 59)))
        sex = str(r.sex).capitalize() if isinstance(r.sex, str) and r.sex else None
        rows.append([(submitted - dt.timedelta(minutes=5)).isoformat() + "+02:00", submitted.isoformat() + "+02:00",
                     filled.isoformat(), r.entered_by, projects[r.project_id], r.district, period.isoformat(),
                     names[r.indicator_code], sex, _num(r.target_value), _num(r.actual_value), None,
                     "v1", 200000 + n, str(uuid.UUID(int=rnd.getrandbits(128))), submitted.isoformat(), "", "",
                     "submitted_via_web", str(r.entered_by).lower(), "", n])
        key.append(dict(source_file=INDICATOR_FILE, source_row=len(rows) + 1, result_id=r.result_id,
                        project_id=r.project_id, district=r.district, period=period.isoformat(),
                        indicator_code=r.indicator_code, sex=(r.sex.lower() if sex else None),
                        target_value=_num(r.target_value), actual_value=_num(r.actual_value)))
    return header, rows, key


def generate(raw: Path | None = None, truth: Path | None = None, out: Path | None = None) -> dict:
    raw, truth = Path(raw or resolve_path("raw")), Path(truth or resolve_path("ground_truth"))
    out = Path(out or resolve_path("kobo_test"))
    cfg = load_yaml("synthetic.yaml")["kobo"]
    rnd = random.Random(cfg["seed"])
    out_raw, out_truth = out / "raw", out / "ground_truth"
    for folder in (out_raw, out_truth):
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True)
    for f in raw.glob(f"{PREFIX}*.xlsx"):
        if f.name not in REPLACED:
            shutil.copy(f, out_raw / f.name)
    acts = pd.read_csv(truth / f"{PREFIX}truth_activities.csv")
    header, rows, key = activity_export(acts, cfg, rnd)
    write_export(out_raw / ACTIVITY_FILE, "ARDE activity monitoring", header, rows)
    pd.DataFrame(key).to_csv(out_truth / f"{PREFIX}kobo_truth_activities.csv", index=False)
    results = pd.read_csv(truth / f"{PREFIX}truth_indicator_results.csv", keep_default_na=False)
    h2, r2, k2 = indicator_export(results, cfg, rnd, resolve_path("staging"))
    write_export(out_raw / INDICATOR_FILE, "ARDE indicator report", h2, r2)
    pd.DataFrame(k2).to_csv(out_truth / f"{PREFIX}kobo_truth_indicator_results.csv", index=False)
    summary = dict(activity_rows=len(rows), duplicate_submissions=sum(1 for k in key if k["duplicate_of_row"]),
                   blank_costs=sum(1 for k in key if k["injected"]), indicator_rows=len(r2))
    print(f"Kobo test set in {out}: {summary}")
    return summary


if __name__ == "__main__":
    generate()
