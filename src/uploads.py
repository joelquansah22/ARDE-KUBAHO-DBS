"""Excel uploads from the dashboard (Upload Excel page): check a filled template, then add it to the data.

WHAT THIS FILE DOES
-------------------
check()    reads the uploaded file exactly as the pipeline would (ingest and clean, on a scratch copy inside
           data/app/upload_check/, which is not in git) and summarises it in plain words: rows accepted, rows held
           back for correction (with the row number and the reason), rows sent for review, and any SKIPPED message.
           It also warns if the same file was uploaded before, or if its records are already in another file.
accept()   keeps the file in data/raw/ under a name that says what it is, when and who uploaded it (e.g.
           activity_monitoring_upload_20261019-1030_MEAL01_june.xlsx), records it in the uploads table of
           data/app/entries.db, optionally replaces an earlier file whose records it repeats (the earlier file is
           kept in data/app/replaced_files/), and prepares the figures again (the pipeline).

Personal data: an uploaded register holds names like any register; it is stored with the other raw files in data/,
which never leaves the laptop, and the pipeline pseudonymises it as usual.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import re
import shutil
from io import BytesIO
from pathlib import Path

import pandas as pd

from common import load_settings, resolve_path

KINDS = {   # kind token (must appear in the stored file name, see source_mappings.yaml) -> what staff see
    "activity_monitoring": "Activity monitoring",
    "beneficiary_register": "Beneficiary register",
    "indicator_report": "Monthly indicator report",
    "donor_opportunity": "Donor and opportunity tracker",
}
TEMPLATES = {"activity_monitoring": "activity_monitoring_template.xlsx",
             "beneficiary_register": "beneficiary_register_template.xlsx",
             "indicator_report": "indicator_report_template.xlsx",
             "donor_opportunity": "donor_opportunity_template.xlsx"}
DUPLICATE_KEYS = {
    "activity": ["project_id", "activity_id", "date", "location_id", "participants_total"],
    "indicator_result": ["project_id", "district", "period", "indicator_code", "disaggregation_key"],
    "registration": ["beneficiary_key", "registration_date"],
    "opportunity": ["opportunity_id"],
    "donor": ["donor_key"],
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def guess_kind(data: bytes) -> str | None:
    """Guess the kind of file from its sheet names (the templates' sheets)."""
    from openpyxl import load_workbook
    try:
        names = {s.lower() for s in load_workbook(BytesIO(data), read_only=True).sheetnames}
    except Exception:  # noqa: BLE001 - not a readable Excel file: the check will say so
        return None
    if {"donors", "opportunities"} & names:
        return "donor_opportunity"
    if "register" in names:
        return "beneficiary_register"
    if "activities" in names:
        return "activity_monitoring"
    if {"report", "reports"} & names or any(n.startswith("fy") for n in names):
        return "indicator_report"
    return None


def _prefix() -> str:
    return "SYNTHETIC_" if load_settings().get("synthetic_mode") else ""


def _safe(name: str) -> str:
    stem = re.sub(r"^SYNTHETIC_", "", Path(name).stem)       # the stored name already says so, once
    return re.sub(r"[^A-Za-z0-9-]+", "_", stem).strip("_")[:40] or "file"


def stored_name(kind: str, original: str, by: str, when: dt.datetime | None = None) -> str:
    when = when or dt.datetime.now()
    return f"{_prefix()}{kind}_upload_{when:%Y%m%d-%H%M%S}_{by}_{_safe(original)}.xlsx"


def _key_text(v) -> str:
    """One way of writing a value, so the same record compares equal whether it was just read or saved before
    (dates as 2024-03-12, numbers without a trailing .0, blanks as empty)."""
    if v is None or (isinstance(v, float) and v != v) or v is pd.NaT:
        return ""
    if isinstance(v, (dt.date, dt.datetime, pd.Timestamp)):
        return str(v)[:10]
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    text = str(v)
    return text[:10] if re.match(r"^\d{4}-\d{2}-\d{2}[ T]", text) else text


def check(data: bytes, original: str, kind: str, raw: Path | None = None, staging: Path | None = None,
          entries: Path | None = None) -> dict:
    """Read the file as the pipeline would and summarise it. Nothing is added to the data."""
    import app_store
    import clean
    import ingest
    raw, staging = Path(raw or resolve_path("raw")), Path(staging or resolve_path("staging"))
    if kind not in KINDS:
        raise ValueError(kind)
    if not load_settings().get("synthetic_mode") and Path(original).name.startswith("SYNTHETIC_"):
        return dict(error="This is a synthetic (demonstration) file: it cannot be added to real data.")
    work = (Path(entries).parent if entries else app_store.db_path().parent) / "upload_check"   # inside data/
    shutil.rmtree(work, ignore_errors=True)
    (work / "raw").mkdir(parents=True)
    for master in raw.glob("*programme_master*.xlsx"):               # the lists every file is checked against
        shutil.copy(master, work / "raw" / master.name)
    name = f"{_prefix()}{kind}_upload_check.xlsx"
    (work / "raw" / name).write_bytes(data)
    try:
        ingest.run(work / "raw", work / "staging")
        tables = clean.run(work / "staging")
    except Exception as e:  # noqa: BLE001 - shown to the person; the data is unchanged
        shutil.rmtree(work, ignore_errors=True)
        return dict(error=f"The file could not be read: {e}")
    st = work / "staging"
    inventory = pd.read_csv(st / "sheet_inventory.csv", dtype=str, keep_default_na=False)
    inventory = inventory[inventory["source_file"] == name]
    skipped = pd.read_csv(st / "skipped_sheets.csv", dtype=str, keep_default_na=False)
    skipped = skipped[skipped["source_file"] == name]
    status = tables["row_status"]
    status = status[status["source_file"] == name]
    issues = tables["issues"]
    removed = int(((issues["source_file"] == name) & (issues["issue_code"] == "exact_duplicate_row")).sum())
    rows_read = 0
    for entity in list(DUPLICATE_KEYS) + ["service"]:
        path = st / f"ingested_{entity}.parquet"
        if path.exists():
            df = pd.read_parquet(path)
            rows_read += int((df["source_file"] == name).sum()) if "source_file" in df else 0
    held = status[status["status"] == "quarantine"]
    review = status[status["status"] == "review"]
    settings = load_settings()
    label = lambda codes: "; ".join(settings["labels"]["issue"].get(c, c.replace("_", " ")) for c in str(codes).split(", ") if c)
    detail = issues[(issues["source_file"] == name) & issues["severity"].isin(["critical", "warning"])]
    details = detail.groupby(["source_sheet", "source_row"])["detail"].apply(
        lambda d: "; ".join(x for x in d if isinstance(x, str) and x)).to_dict()
    def listing(df):
        return pd.DataFrame({"Sheet": df["source_sheet"], "Row": df["source_row"].astype(int),
                             "Record type": [settings["labels"]["entity"].get(e, e) for e in df["entity"]], "Problem": [label(c) for c in
                                                                     df["critical_codes"].where(df["status"] == "quarantine",
                                                                                                df["warning_codes"])],
                             "Details": [details.get((s, r), "") for s, r in zip(df["source_sheet"], df["source_row"])]})
    # Already uploaded? The same file, or the same records in another file.
    digest = sha256(data)
    same_file = [u for u in app_store.table("uploads", entries) if u["sha256"] == digest and u["status"] == "active"]
    overlaps = {}
    for entity, key in DUPLICATE_KEYS.items():
        mine, theirs = tables.get(entity), staging / f"clean_{entity}.parquet"
        if mine is None or not len(mine) or not theirs.exists():
            continue
        mine = mine[mine["source_file"] == name]
        theirs = pd.read_parquet(theirs)
        theirs = theirs[theirs["source_file"] != "entries.db"]
        if not len(mine) or not set(key) <= set(theirs.columns):
            continue
        k = lambda df: df[key].apply(lambda col: col.map(_key_text)).agg("|".join, axis=1)
        hit = theirs[k(theirs).isin(set(k(mine)))]
        for f, n in hit.groupby("source_file").size().items():
            overlaps[f] = overlaps.get(f, 0) + int(n)
    shutil.rmtree(work, ignore_errors=True)
    return dict(error=None, kind=kind, sha256=digest, rows_read=rows_read, removed=removed,
                held_back=len(held), to_review=len(review), accepted=rows_read - len(held) - removed,
                held_list=listing(held), review_list=listing(review),
                skipped=[str(m).replace(name, original) for m in skipped.get("message", pd.Series(dtype=str))],
                sheets=list(inventory.loc[inventory["entity"].ne(""), "source_sheet"]), same_file=same_file,
                overlaps=dict(sorted(overlaps.items(), key=lambda x: -x[1])))


def accept(data: bytes, original: str, kind: str, by: str, summary: dict, replace: list[str] = (),
           raw: Path | None = None, entries: Path | None = None, run_pipeline: bool = True) -> dict:
    """Keep the file, record who uploaded it and when, replace earlier files if asked, prepare the figures."""
    import app_store
    app_store._check_staff(by)
    raw = Path(raw or resolve_path("raw"))
    name = stored_name(kind, original, by)
    (raw / name).write_bytes(data)
    replaced_dir = Path(entries).parent / "replaced_files" if entries else app_store.db_path().parent / "replaced_files"
    with app_store.connect(entries) as con:
        upload_id = app_store._next_id(con, "uploads", "upload_id", "UP")
        con.execute("INSERT INTO uploads (upload_id, stored_file, original_name, kind, sha256, uploaded_by, "
                    "uploaded_at, rows_read, accepted, held_back, to_review, skipped_sheets) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (upload_id, name, original, kind, summary["sha256"], by, app_store.now(), summary["rows_read"],
                     summary["accepted"], summary["held_back"], summary["to_review"], len(summary["skipped"])))
        app_store._history(con, by, "uploads", upload_id, "uploaded", None, None, f"{original} -> {name}")
        for old in replace:
            if (raw / old).exists():
                replaced_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(raw / old), str(replaced_dir / old))
            con.execute("UPDATE uploads SET status = 'replaced', replaced_by = ? WHERE stored_file = ?", (upload_id, old))
            app_store._history(con, by, "uploads", upload_id, "replaced an earlier file", None, old, name)
    app_store.backup(entries, "upload")
    ok = True
    if run_pipeline:
        import pipeline
        ok = pipeline.main([]) == 0
    return dict(upload_id=upload_id, stored_file=name, pipeline_ok=ok)
