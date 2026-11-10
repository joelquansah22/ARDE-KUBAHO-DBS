"""KPI updates made on the dashboard, and workbook uploads, for ARDE/KUBAHO mode (a small SQLite file).

WHAT THIS FILE DOES
-------------------
The "KPI update" page replaces editing the amber cells of the workbook's 'Results & KPIs' sheet. Staff pick a
project, a result and a KPI, and record the new achieved value and status. This module stores those updates in
data/real/app/kpi_updates.db (gitignored, like everything under data/real/):

  kpi_updates      one row per update: the KPI, the new achieved value and status, a note, who and when, and the
                   values it replaced. The newest update of each KPI is the one used in the figures.
  change_history   one row per field changed (old value, new value, who, when), the same pattern as donor entry.
  uploads          each newer copy of the workbook added on the Upload Excel page (kept in data/real/uploads/).

WHICH VALUE WINS: an update made on the dashboard is used until a NEWER workbook is uploaded; from then on the
workbook's value is used (the upload page warns how many updates that affects, and "Download register" puts the
updates into a workbook first, so nothing is lost).

BACKUPS: after every save, and once each time the dashboard starts, a dated copy goes to data/real/app/backups/
(the newest settings.app_backups_keep are kept). restore() puts one back.

HOW TO RUN (maintenance)
    python src/arde_store.py --list-backups
    python src/arde_store.py --backup
    python src/arde_store.py --restore data/real/app/backups/kpi_updates_20261110-101500_save.db
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import shutil
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

from common import PROJECT_ROOT, load_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS kpi_updates (
    row_id INTEGER PRIMARY KEY AUTOINCREMENT,
    update_id TEXT NOT NULL UNIQUE,                      -- KU0001...
    kpi_code TEXT NOT NULL,
    achieved REAL NOT NULL CHECK (achieved >= 0),
    kpi_status TEXT NOT NULL,
    note TEXT,
    previous_achieved REAL,
    previous_status TEXT,
    updated_by TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS change_history (
    row_id INTEGER PRIMARY KEY AUTOINCREMENT,
    changed_at TEXT NOT NULL,
    changed_by TEXT NOT NULL,
    table_name TEXT NOT NULL,
    record_id TEXT NOT NULL,
    action TEXT NOT NULL,
    field TEXT,
    old_value TEXT,
    new_value TEXT
);
CREATE TABLE IF NOT EXISTS uploads (
    row_id INTEGER PRIMARY KEY AUTOINCREMENT,
    upload_id TEXT NOT NULL UNIQUE,                      -- WB001...
    original_name TEXT NOT NULL,
    stored_file TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    uploaded_by TEXT NOT NULL,
    uploaded_at TEXT NOT NULL,
    kpis INTEGER, projects INTEGER, held_back INTEGER, to_review INTEGER
);
"""

KPI_STATUSES = ["Achieved", "On track", "In progress", "Needs attention", "Not started"]


class EntryError(Exception):
    """A plain-language reason why an update was refused."""


def _path(key: str) -> Path:
    return PROJECT_ROOT / load_settings()["arde"][key]


def db_path() -> Path:
    return _path("app_store")


def now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


@contextmanager
def connect(path: Path | None = None):
    path = Path(path or db_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    try:
        yield con
        con.commit()
    finally:
        con.close()


def table(name: str, path: Path | None = None) -> list[dict]:
    if not Path(path or db_path()).exists():
        return []
    with connect(path) as con:
        return [dict(r) for r in con.execute(f"SELECT * FROM {name} ORDER BY row_id")]


def _next_id(con, table_name: str, column: str, prefix: str, width: int) -> str:
    n = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0] + 1
    return f"{prefix}{n:0{width}d}"


def _history(con, by, table_name, record_id, action, field=None, old=None, new=None) -> None:
    con.execute("INSERT INTO change_history (changed_at, changed_by, table_name, record_id, action, field, old_value, "
                "new_value) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (now(), by, table_name, record_id, action, field, None if old is None else str(old),
                 None if new is None else str(new)))


def validate_update(kpi: dict, achieved, status: str, by: str) -> list[str]:
    """Reasons to refuse an update (empty list = fine). kpi: the KPI's current row (code, target, unit...)."""
    problems = []
    if not by:
        problems.append("Choose your name first.")
    if achieved is None or pd.isna(achieved):
        problems.append("Enter the achieved value.")
    elif float(achieved) < 0:
        problems.append("The achieved value cannot be negative.")
    elif str(kpi.get("unit", "")).strip() == "%" and float(achieved) > 100:
        problems.append("This KPI is a percentage: the achieved value cannot be above 100.")
    if status not in KPI_STATUSES:
        problems.append(f"Choose a status ({', '.join(KPI_STATUSES)}).")
    if status == "Not started" and achieved is not None and float(achieved) > 0:
        problems.append("A KPI with an achieved value above 0 cannot be 'Not started'.")
    return problems


def add_update(kpi: dict, achieved: float, status: str, note: str, by: str, path: Path | None = None) -> str:
    """Record an update of one KPI. kpi: its current row (kpi_code, achieved, kpi_status, unit). Returns the id."""
    problems = validate_update(kpi, achieved, status, by)
    if problems:
        raise EntryError(" ".join(problems))
    if float(achieved) == float(kpi.get("achieved") or 0) and status == kpi.get("kpi_status") and not note:
        raise EntryError("Nothing has changed: the achieved value and status are the same as now.")
    with connect(path) as con:
        uid = _next_id(con, "kpi_updates", "update_id", "KU", 4)
        con.execute("INSERT INTO kpi_updates (update_id, kpi_code, achieved, kpi_status, note, previous_achieved, "
                    "previous_status, updated_by, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (uid, kpi["kpi_code"], float(achieved), status, note or None, kpi.get("achieved"),
                     kpi.get("kpi_status"), by, now()))
        _history(con, by, "kpi_updates", kpi["kpi_code"], f"updated ({uid})", "achieved", kpi.get("achieved"), achieved)
        if status != kpi.get("kpi_status"):
            _history(con, by, "kpi_updates", kpi["kpi_code"], f"updated ({uid})", "status", kpi.get("kpi_status"), status)
        if note:
            _history(con, by, "kpi_updates", kpi["kpi_code"], f"updated ({uid})", "note", None, note)
    backup(path, "save")
    return uid


def current_updates(path: Path | None = None, since: str | None = None) -> pd.DataFrame:
    """The newest update of each KPI, made AFTER `since` (the time the workbook in use was uploaded; None = all)."""
    rows = pd.DataFrame(table("kpi_updates", path))
    cols = ["kpi_code", "achieved", "kpi_status", "updated_by", "updated_at", "update_id"]
    if not len(rows):
        return pd.DataFrame(columns=cols)
    if since:
        rows = rows[rows["updated_at"] > since]
    return rows.sort_values("row_id").groupby("kpi_code").tail(1)[cols].reset_index(drop=True)


# ---------------------------------------------------------------- the workbook in use, and uploads
def current_workbook() -> tuple[Path, str | None]:
    """The workbook the pipeline reads: the newest upload, or the file in settings (arde.workbook) if there is none.
    Returns (path, uploaded_at or None)."""
    ups = table("uploads")
    if ups:
        last = ups[-1]
        return PROJECT_ROOT / last["stored_file"], last["uploaded_at"]
    return _path("workbook"), None


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def same_file_uploads(data: bytes) -> list[dict]:
    digest = sha256(data)
    original = _path("workbook")
    found = [u for u in table("uploads") if u["sha256"] == digest]
    if original.exists() and sha256(original.read_bytes()) == digest:
        found.insert(0, {"upload_id": "original", "original_name": original.name, "uploaded_by": "-",
                         "uploaded_at": "the workbook as received"})
    return found


def add_upload(data: bytes, original_name: str, by: str, summary: dict, path: Path | None = None) -> dict:
    """Keep the uploaded workbook in data/real/uploads/ and record it. The original workbook is never touched."""
    if not by:
        raise EntryError("Choose your name first.")
    folder = _path("uploads")
    folder.mkdir(parents=True, exist_ok=True)
    with connect(path) as con:
        uid = _next_id(con, "uploads", "upload_id", "WB", 3)
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        safe = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in Path(original_name).name)
        target = folder / f"{uid}_{stamp}_{by}_{safe}"
        target.write_bytes(data)
        stored = target.relative_to(PROJECT_ROOT).as_posix()
        con.execute("INSERT INTO uploads (upload_id, original_name, stored_file, sha256, uploaded_by, uploaded_at, kpis, "
                    "projects, held_back, to_review) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (uid, original_name, stored, sha256(data), by, now(), summary.get("kpis"),
                     summary.get("projects"), summary.get("held_back"), summary.get("to_review")))
        _history(con, by, "uploads", uid, "workbook uploaded", "file", None, original_name)
    backup(path, "upload")
    return {"upload_id": uid, "stored_file": stored}


# ---------------------------------------------------------------- backups
def backup_folder(path: Path | None = None) -> Path:
    return Path(path or db_path()).parent / "backups"


def backup(path: Path | None = None, reason: str = "manual") -> Path | None:
    path = Path(path or db_path())
    if not path.exists():
        return None
    folder = backup_folder(path)
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"kpi_updates_{dt.datetime.now():%Y%m%d-%H%M%S-%f}_{reason}.db"
    src, dst = sqlite3.connect(path), sqlite3.connect(target)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    keep = int(load_settings().get("app_backups_keep", 30))
    for old in list_backups(path)[keep:]:
        old.unlink()
    return target


def list_backups(path: Path | None = None) -> list[Path]:
    folder = backup_folder(path)
    return sorted(folder.glob("kpi_updates_*.db"), reverse=True) if folder.exists() else []


def restore(backup_file: Path, path: Path | None = None) -> Path | None:
    path, backup_file = Path(path or db_path()), Path(backup_file)
    if not backup_file.exists():
        raise EntryError(f"Backup not found: {backup_file}")
    with sqlite3.connect(backup_file) as check:
        tables = {r[0] for r in check.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    if not {"kpi_updates", "change_history"} <= tables:
        raise EntryError(f"{backup_file.name} is not a KPI updates backup.")
    safety = backup(path, "before-restore")
    shutil.copy2(backup_file, path)
    return safety


def main() -> None:
    parser = argparse.ArgumentParser(description="KPI updates database (ARDE mode): backups and restore.")
    parser.add_argument("--list-backups", action="store_true")
    parser.add_argument("--backup", action="store_true")
    parser.add_argument("--restore", type=Path, metavar="BACKUP_FILE")
    args = parser.parse_args()
    if args.backup:
        print(f"Backed up to {backup()}")
    elif args.restore:
        print(f"Restored. The previous file was kept as {restore(args.restore)}")
    else:
        for b in list_backups():
            print(b)


if __name__ == "__main__":
    main()
