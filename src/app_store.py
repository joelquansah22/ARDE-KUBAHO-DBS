"""Donor tracking entered in the dashboard: a small SQLite file (data/app/entries.db) with a change history.

WHAT THIS FILE DOES
-------------------
Staff can add donors and funding opportunities, update them and mark next actions as done on the dashboard's
"Donor entry" page. This module stores those entries and checks them:

  donors           one row per donor added in the dashboard (IDs APP-D001...). An INDIVIDUAL donor's name is never
                   stored: the database refuses it, and the pipeline shows such a donor as "Individual donor #NNN".
  opportunities    one row per opportunity added in the dashboard (IDs APP-O001...). The donor is either a donor
                   added here (donor_id) or a donor already in the Excel tracker (its pseudonymous donor_key).
  change_history   who changed what and when: one row per field changed, with the old and the new value.

There are no names, phone numbers, emails or ID numbers of people in this database (team rule): staff are recorded
by their staff code from config/staff.yaml, and donor contact details are not asked for.

The pipeline reads these entries next to the Excel donor tracker (src/ingest.py, read_app_entries), so both sources
work together; entries keep lineage (source_file "entries.db", the table, and the row number).

ONE HOME FOR DONOR DATA: import_tracker() moves the Excel tracker's donors and opportunities into this database once
(keeping their IDs, and their original file, sheet and row in origin_*). From then on the pipeline no longer reads
those rows from Excel; the Excel donor template remains only as an offline fallback for NEW opportunities.

BACKUPS: after every save, and once each time the dashboard starts, a dated copy is kept in data/app/backups/ (the
newest settings.app_backups_keep, 30). restore() puts a backup back (the current file is backed up first).

HOW TO RUN (maintenance)
    python src/app_store.py --list-backups
    python src/app_store.py --backup
    python src/app_store.py --restore data/app/backups/entries_20261019-101500_save.db
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from common import load_settings, load_yaml, resolve_path

SCHEMA = """
CREATE TABLE IF NOT EXISTS donors (
    row_id INTEGER PRIMARY KEY AUTOINCREMENT,
    donor_id TEXT NOT NULL UNIQUE,
    donor_name TEXT,
    donor_type TEXT NOT NULL,
    country TEXT,
    thematic_interests TEXT,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    origin_file TEXT, origin_sheet TEXT, origin_row INTEGER,       -- set when imported from the Excel tracker
    CHECK (donor_type <> 'individual' OR donor_name IS NULL),      -- individuals are never named here
    CHECK (donor_type = 'individual' OR donor_name IS NOT NULL)
);
CREATE TABLE IF NOT EXISTS opportunities (
    row_id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_id TEXT NOT NULL UNIQUE,
    donor_id TEXT REFERENCES donors(donor_id),
    donor_key TEXT,
    title TEXT NOT NULL,
    thematic_fit TEXT NOT NULL,
    stage TEXT NOT NULL,
    deadline TEXT,
    requested_amount_rwf REAL NOT NULL CHECK (requested_amount_rwf >= 0),
    awarded_amount_rwf REAL CHECK (awarded_amount_rwf IS NULL OR awarded_amount_rwf >= 0),
    probability REAL NOT NULL CHECK (probability >= 0 AND probability <= 1),
    owner TEXT NOT NULL,
    next_action TEXT,
    next_action_date TEXT,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_by TEXT,
    updated_at TEXT,
    origin_file TEXT, origin_sheet TEXT, origin_row INTEGER,       -- set when imported from the Excel tracker
    CHECK (donor_id IS NOT NULL OR donor_key IS NOT NULL)
);
CREATE TABLE IF NOT EXISTS activities (
    row_id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id TEXT NOT NULL UNIQUE,                                -- APP-A001...
    project_id TEXT NOT NULL,
    activity_id TEXT NOT NULL,
    district TEXT NOT NULL, sector TEXT NOT NULL, cell TEXT NOT NULL, village TEXT NOT NULL,
    date TEXT, planned_date TEXT, entry_date TEXT NOT NULL,
    status TEXT NOT NULL,
    participants_female INTEGER CHECK (participants_female IS NULL OR participants_female >= 0),
    participants_male INTEGER CHECK (participants_male IS NULL OR participants_male >= 0),
    participants_total INTEGER CHECK (participants_total IS NULL OR participants_total >= 0),
    cost_rwf REAL CHECK (cost_rwf IS NULL OR cost_rwf >= 0),
    officer TEXT NOT NULL,
    created_by TEXT NOT NULL, created_at TEXT NOT NULL, updated_by TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS indicator_reports (
    row_id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id TEXT NOT NULL UNIQUE,                                -- APP-R001...
    project_id TEXT NOT NULL,
    district TEXT NOT NULL,
    period TEXT NOT NULL,                                          -- first day of the month
    indicator_code TEXT NOT NULL,
    sex TEXT CHECK (sex IS NULL OR sex IN ('female', 'male')),
    target_value REAL CHECK (target_value IS NULL OR target_value >= 0),
    actual_value REAL NOT NULL CHECK (actual_value >= 0),
    created_by TEXT NOT NULL, created_at TEXT NOT NULL, updated_by TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS uploads (
    row_id INTEGER PRIMARY KEY AUTOINCREMENT,
    upload_id TEXT NOT NULL UNIQUE,                                -- UP001...
    stored_file TEXT NOT NULL,
    original_name TEXT NOT NULL,
    kind TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    uploaded_by TEXT NOT NULL,
    uploaded_at TEXT NOT NULL,
    rows_read INTEGER, accepted INTEGER, held_back INTEGER, to_review INTEGER, skipped_sheets INTEGER,
    status TEXT NOT NULL DEFAULT 'active',                         -- active, or replaced by a corrected file
    replaced_by TEXT
);
CREATE TABLE IF NOT EXISTS change_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    changed_at TEXT NOT NULL,
    changed_by TEXT NOT NULL,
    table_name TEXT NOT NULL,
    record_id TEXT NOT NULL,
    action TEXT NOT NULL,
    field TEXT,
    old_value TEXT,
    new_value TEXT
);
"""

DONOR_FIELDS = ["donor_name", "donor_type", "country", "thematic_interests"]
OPPORTUNITY_FIELDS = ["donor_id", "donor_key", "title", "thematic_fit", "stage", "deadline", "requested_amount_rwf",
                      "awarded_amount_rwf", "probability", "owner", "next_action", "next_action_date"]
EDITABLE = ["stage", "requested_amount_rwf", "awarded_amount_rwf", "probability", "deadline", "next_action",
            "next_action_date", "owner"]


class EntryError(ValueError):
    """An entry that breaks a rule; the message lists every problem in plain words."""


def db_path() -> Path:
    return resolve_path("app_entries")


def staff() -> list[dict]:
    """Staff who may enter data (config/staff.yaml): code and role, no personal names needed."""
    return load_yaml("staff.yaml")["staff"]


def today() -> dt.date:
    """'Today' for the checks: the configured as-of date (so synthetic demonstrations behave), else the real date."""
    return load_settings().get("as_of_date") or dt.date.today()


def now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


@contextmanager
def connect(path: Path | None = None):
    path = Path(path or db_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA)
    for table_name in ("donors", "opportunities"):                  # files made before the import step existed
        have = {c[1] for c in con.execute(f"PRAGMA table_info({table_name})")}
        for col, kind in (("origin_file", "TEXT"), ("origin_sheet", "TEXT"), ("origin_row", "INTEGER")):
            if col not in have:
                con.execute(f"ALTER TABLE {table_name} ADD COLUMN {col} {kind}")
    try:
        yield con
        con.commit()
    finally:
        con.close()


def _blank(v) -> bool:
    return v is None or (isinstance(v, str) and not v.strip())


def _check_staff(code: str) -> None:
    if code not in {s["code"] for s in staff()}:
        raise EntryError("Choose your name (staff code) from the list before saving.")


# ---------------------------------------------------------------- validation
def validate_donor(d: dict) -> list[str]:
    s = load_settings()["donor_pipeline"]
    problems = []
    types = list(s["donor_type_mapping"])
    if d.get("donor_type") not in types:
        problems.append(f"Donor type is required ({', '.join(types)}).")
    if d.get("donor_type") == "individual":
        if not _blank(d.get("donor_name")):
            problems.append("Do not enter an individual donor's name: individual donors are recorded without a name "
                            "and shown as 'Individual donor #NNN'. Keep their details in your own records.")
    elif _blank(d.get("donor_name")):
        problems.append("Donor name is required (the organisation's name).")
    return problems


def validate_opportunity(o: dict, creating: bool) -> list[str]:
    s = load_settings()["donor_pipeline"]
    problems = []
    for field, label in (("title", "Title"), ("thematic_fit", "Thematic fit"), ("stage", "Stage"), ("owner", "Owner")):
        if _blank(o.get(field)):
            problems.append(f"{label} is required.")
    if _blank(o.get("donor_id")) and _blank(o.get("donor_key")):
        problems.append("Donor is required (pick one, or add the donor first).")
    if not _blank(o.get("stage")) and o["stage"] not in s["stages"]:
        problems.append(f"Stage must be one of: {', '.join(s['stages'])}.")
    if o.get("requested_amount_rwf") is None:
        problems.append("Amount requested (RWF) is required.")
    elif o["requested_amount_rwf"] < 0:
        problems.append("Amount requested cannot be negative.")
    if o.get("awarded_amount_rwf") is not None and o["awarded_amount_rwf"] < 0:
        problems.append("Amount awarded cannot be negative.")
    if o.get("stage") == "Awarded" and o.get("awarded_amount_rwf") in (None, 0):
        problems.append("An awarded opportunity needs the amount awarded.")
    p = o.get("probability")
    if p is None:
        problems.append("Probability is required (0% to 100%).")
    elif not 0 <= p <= 1:
        problems.append("Probability must be between 0% and 100%.")
    deadline = o.get("deadline")
    if creating:
        if deadline is None:
            problems.append("Deadline is required.")
        elif deadline <= today():
            problems.append(f"The deadline must be in the future (after {today():%d %b %Y}).")
    if not _blank(o.get("next_action")) and o.get("next_action_date") is None:
        problems.append("Give the date by which the next action is due.")
    if o.get("next_action_date") is not None and _blank(o.get("next_action")):
        problems.append("Describe the next action, or remove its date.")
    return problems


def _store(v):
    return v.isoformat() if isinstance(v, (dt.date, dt.datetime)) else v


def _next_id(con, table: str, column: str, prefix: str) -> str:
    n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] + 1
    while con.execute(f"SELECT 1 FROM {table} WHERE {column} = ?", (f"{prefix}{n:03d}",)).fetchone():
        n += 1
    return f"{prefix}{n:03d}"


def _history(con, by: str, table: str, record_id: str, action: str, field=None, old=None, new=None) -> None:
    con.execute("INSERT INTO change_history (changed_at, changed_by, table_name, record_id, action, field, old_value, "
                "new_value) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (now(), by, table, record_id, action, field, None if old is None else str(_store(old)),
                 None if new is None else str(_store(new))))


# ---------------------------------------------------------------- saving
def add_donor(d: dict, by: str, path: Path | None = None) -> str:
    _check_staff(by)
    d = {k: (None if _blank(d.get(k)) else d.get(k)) for k in DONOR_FIELDS}
    if d.get("donor_type") == "individual":
        d["donor_name"] = None
    problems = validate_donor(d)
    if problems:
        raise EntryError(" ".join(problems))
    with connect(path) as con:
        donor_id = _next_id(con, "donors", "donor_id", "APP-D")
        con.execute(f"INSERT INTO donors (donor_id, {', '.join(DONOR_FIELDS)}, created_by, created_at) "
                    f"VALUES (?, {', '.join('?' for _ in DONOR_FIELDS)}, ?, ?)",
                    (donor_id, *[d[k] for k in DONOR_FIELDS], by, now()))
        _history(con, by, "donors", donor_id, "added")
    backup(path, "save")
    return donor_id


def _normalise_opportunity(o: dict) -> dict:
    o = {k: (None if _blank(o.get(k)) else o.get(k)) for k in OPPORTUNITY_FIELDS}
    for k in ("deadline", "next_action_date"):
        if isinstance(o.get(k), str):
            o[k] = dt.date.fromisoformat(o[k])
    for k in ("requested_amount_rwf", "awarded_amount_rwf", "probability"):
        if o.get(k) is not None:
            o[k] = float(o[k])
    return o


def add_opportunity(o: dict, by: str, path: Path | None = None) -> str:
    _check_staff(by)
    o = _normalise_opportunity(o)
    problems = validate_opportunity(o, creating=True)
    if problems:
        raise EntryError(" ".join(problems))
    with connect(path) as con:
        if o["donor_id"] and not con.execute("SELECT 1 FROM donors WHERE donor_id = ?", (o["donor_id"],)).fetchone():
            raise EntryError("That donor was not found among the donors added here.")
        opp_id = _next_id(con, "opportunities", "opportunity_id", "APP-O")
        con.execute(f"INSERT INTO opportunities (opportunity_id, {', '.join(OPPORTUNITY_FIELDS)}, created_by, created_at)"
                    f" VALUES (?, {', '.join('?' for _ in OPPORTUNITY_FIELDS)}, ?, ?)",
                    (opp_id, *[_store(o[k]) for k in OPPORTUNITY_FIELDS], by, now()))
        _history(con, by, "opportunities", opp_id, "added")
    backup(path, "save")
    return opp_id


def update_opportunity(opportunity_id: str, changes: dict, by: str, path: Path | None = None) -> list[str]:
    """Change some of the EDITABLE fields; returns the fields that really changed (each one is in the history)."""
    _check_staff(by)
    unknown = set(changes) - set(EDITABLE)
    if unknown:
        raise EntryError(f"These fields cannot be changed here: {', '.join(sorted(unknown))}.")
    with connect(path) as con:
        row = con.execute("SELECT * FROM opportunities WHERE opportunity_id = ?", (opportunity_id,)).fetchone()
        if row is None:
            raise EntryError(f"Opportunity {opportunity_id} was not found.")
        current = _normalise_opportunity(dict(row))
        new = _normalise_opportunity({**current, **changes})
        problems = validate_opportunity(new, creating=False)
        if problems:
            raise EntryError(" ".join(problems))
        changed = [k for k in EDITABLE if new[k] != current[k]]
        for k in changed:
            con.execute(f"UPDATE opportunities SET {k} = ? WHERE opportunity_id = ?", (_store(new[k]), opportunity_id))
            _history(con, by, "opportunities", opportunity_id, "changed", k, current[k], new[k])
        if changed:
            con.execute("UPDATE opportunities SET updated_by = ?, updated_at = ? WHERE opportunity_id = ?",
                        (by, now(), opportunity_id))
    if changed:
        backup(path, "save")
    return changed


def mark_next_action_done(opportunity_id: str, by: str, path: Path | None = None) -> None:
    """The next action is done: it is kept in the change history and cleared, ready for the next one."""
    _check_staff(by)
    with connect(path) as con:
        row = con.execute("SELECT next_action, next_action_date FROM opportunities WHERE opportunity_id = ?",
                          (opportunity_id,)).fetchone()
        if row is None or _blank(row["next_action"]):
            raise EntryError("This opportunity has no next action to mark as done.")
        _history(con, by, "opportunities", opportunity_id, "next action done", "next_action",
                 f"{row['next_action']} (due {row['next_action_date']})", None)
        con.execute("UPDATE opportunities SET next_action = NULL, next_action_date = NULL, updated_by = ?, "
                    "updated_at = ? WHERE opportunity_id = ?", (by, now(), opportunity_id))
    backup(path, "save")


# ---------------------------------------------------------------- reading
TABLES = ("donors", "opportunities", "activities", "indicator_reports", "uploads", "change_history")


def table(name: str, path: Path | None = None) -> list[dict]:
    if name not in TABLES:
        raise ValueError(name)
    path = Path(path or db_path())
    if not path.exists():
        return []
    with connect(path) as con:
        return [dict(r) for r in con.execute(f"SELECT * FROM {name} ORDER BY 1")]


# ---------------------------------------------------------------- backups
def backup_folder(path: Path | None = None) -> Path:
    return Path(path or db_path()).parent / "backups"


def backup(path: Path | None = None, reason: str = "manual") -> Path | None:
    """A dated, consistent copy of the database in data/app/backups/; only the newest N are kept
    (settings.app_backups_keep). Returns the copy, or None if there is no database yet."""
    path = Path(path or db_path())
    if not path.exists():
        return None
    folder = backup_folder(path)
    folder.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    target = folder / f"entries_{stamp}_{reason}.db"
    src, dst = sqlite3.connect(path), sqlite3.connect(target)
    try:
        src.backup(dst)                                   # SQLite's own copy: safe even while the file is in use
    finally:
        dst.close()
        src.close()
    keep = int(load_settings().get("app_backups_keep", 30))
    for old in list_backups(path)[keep:]:
        old.unlink()
    return target


def list_backups(path: Path | None = None) -> list[Path]:
    """Backups, newest first."""
    folder = backup_folder(path)
    return sorted(folder.glob("entries_*.db"), reverse=True) if folder.exists() else []


def restore(backup_file: Path, path: Path | None = None) -> Path | None:
    """Put a backup back as the database. The current database is backed up first ("before-restore"), so a restore
    can itself be undone. Returns that safety copy."""
    path, backup_file = Path(path or db_path()), Path(backup_file)
    if not backup_file.exists():
        raise EntryError(f"Backup not found: {backup_file}")
    with sqlite3.connect(backup_file) as check:                   # refuse a file that is not an entries database
        tables = {r[0] for r in check.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    if not {"donors", "opportunities", "change_history"} <= tables:
        raise EntryError(f"{backup_file.name} is not a donor entries backup.")
    safety = backup(path, "before-restore")
    src, dst = sqlite3.connect(backup_file), sqlite3.connect(path)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    return safety


def export_workbook(path: Path | None = None) -> bytes:
    """All donor tables and the change history in one Excel file (the "Download backup" button)."""
    import io

    from openpyxl import Workbook
    from openpyxl.styles import Font
    wb = Workbook()
    info = wb.active
    info.title = "About"
    info.append(["Donor entries backup (ARDE/KUBAHO MEAL dashboard)"])
    info["A1"].font = Font(bold=True, size=13)
    info.append([f"Exported {dt.datetime.now():%d %B %Y %H:%M} from {Path(path or db_path()).name}"])
    if load_settings().get("synthetic_mode"):
        info.append([load_settings()["synthetic_banner"]])
    info.append(["No names, phone numbers, emails or ID numbers of people are stored in this database."])
    for name, title in (("donors", "Donors"), ("opportunities", "Opportunities"), ("activities", "Activities"),
                        ("indicator_reports", "Indicator reports"), ("uploads", "Uploads"),
                        ("change_history", "Change history")):
        rows = table(name, path)
        ws = wb.create_sheet(title)
        columns = list(rows[0]) if rows else []
        if not columns:
            with connect(path) as con:
                columns = [c[1] for c in con.execute(f"PRAGMA table_info({name})")]
        ws.append(columns)
        for c in ws[1]:
            c.font = Font(bold=True)
        for r in rows:
            ws.append([r[c] for c in columns])
        ws.freeze_panes = "A2"
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


# ---------------------------------------------------------------- one home: import the Excel tracker
def import_preview(staging: Path | None = None, path: Path | None = None) -> dict:
    """What import_tracker would move from the Excel donor tracker, as the pipeline last cleaned it
    (data/staging). Returns donors, opportunities (ready to import) and problems (rows that must be corrected in
    the Excel file first). Rows already imported, quarantined rows and rows entered on the dashboard are left out."""
    import pandas as pd
    staging = Path(staging or resolve_path("staging"))
    if not (staging / "clean_opportunity.parquet").exists():
        raise EntryError("Run the pipeline first (python src/pipeline.py): the import uses its cleaned tracker.")
    lineage = ["source_file", "source_sheet", "source_row"]
    clean_d, clean_o = pd.read_parquet(staging / "clean_donor.parquet"), pd.read_parquet(staging / "clean_opportunity.parquet")
    ingested_d = pd.read_parquet(staging / "ingested_donor.parquet")[lineage + ["donor_id"]]
    quarantine = pd.read_parquet(staging / "dq_quarantine.parquet")
    q_keys = set(zip(quarantine["source_file"], quarantine["source_sheet"], quarantine["source_row"].astype(int)))
    donors = clean_d[clean_d["source_file"] != "entries.db"].merge(ingested_d, on=lineage, how="left")
    opps = clean_o[clean_o["source_file"] != "entries.db"].copy()
    present_d = {r["donor_id"] for r in table("donors", path)}
    present_o = {r["opportunity_id"] for r in table("opportunities", path)}
    donors = donors[~donors["donor_id"].isin(present_d)]
    id_of_key = dict(zip(clean_d["donor_key"], clean_d.merge(ingested_d, on=lineage, how="left")["donor_id"]))
    problems, ready = [], []
    for r in opps.to_dict("records"):
        where = f"{r['source_file']} / {r['source_sheet']} / row {int(r['source_row'])}"
        if r["opportunity_id"] in present_o:
            continue
        if (r["source_file"], r["source_sheet"], int(r["source_row"])) in q_keys:
            problems.append(dict(opportunity_id=r["opportunity_id"], where=where,
                                 problem="Quarantined by the data-quality checks: correct it in the Excel file first."))
            continue
        o = {k: (None if isinstance(v, float) and v != v else v) for k, v in r.items()}
        o["donor_id"] = id_of_key.get(o.get("donor_key"))
        for k in ("deadline", "next_action_date"):
            if o.get(k) is not None:
                o[k] = pd.Timestamp(o[k]).date()
        issues = validate_opportunity({**o, "donor_key": None}, creating=False)
        if issues:
            problems.append(dict(opportunity_id=o["opportunity_id"], where=where, problem=" ".join(issues)))
            continue
        ready.append(o)
    return dict(donors=donors.sort_values("donor_id").reset_index(drop=True),
                opportunities=pd.DataFrame(ready), problems=pd.DataFrame(problems, columns=["opportunity_id", "where",
                                                                                            "problem"]))


def import_tracker(by: str, staging: Path | None = None, path: Path | None = None) -> dict:
    """Move the Excel tracker's donors and opportunities into the database, ONCE, keeping their IDs and their
    original file, sheet and row. Individual donors are stored without a name (their label is kept by numbering
    them in the same order as before). Rows with problems are left in Excel (see import_preview)."""
    _check_staff(by)
    preview = import_preview(staging, path)
    donors, opps = preview["donors"], preview["opportunities"]
    with connect(path) as con:
        for d in donors.to_dict("records"):
            individual = d["donor_type"] == "individual"
            con.execute("INSERT INTO donors (donor_id, donor_name, donor_type, country, thematic_interests, created_by, "
                        "created_at, origin_file, origin_sheet, origin_row) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (d["donor_id"], None if individual else d["donor_name"], d["donor_type"],
                         d.get("country"), d.get("thematic_interests"), by, now(), d["source_file"],
                         d["source_sheet"], int(d["source_row"])))
            _history(con, by, "donors", d["donor_id"], "imported from the Excel tracker", None, None,
                     f"{d['source_file']} / {d['source_sheet']} / row {int(d['source_row'])}")
        for o in opps.to_dict("records") if len(opps) else []:
            con.execute(f"INSERT INTO opportunities (opportunity_id, {', '.join(OPPORTUNITY_FIELDS)}, created_by, "
                        f"created_at, origin_file, origin_sheet, origin_row) VALUES "
                        f"(?, {', '.join('?' for _ in OPPORTUNITY_FIELDS)}, ?, ?, ?, ?, ?)",
                        (o["opportunity_id"], *[_store({**o, "donor_key": None}.get(k)) for k in OPPORTUNITY_FIELDS],
                         by, now(), o["source_file"], o["source_sheet"], int(o["source_row"])))
            _history(con, by, "opportunities", o["opportunity_id"], "imported from the Excel tracker", None, None,
                     f"{o['source_file']} / {o['source_sheet']} / row {int(o['source_row'])}")
    backup(path, "import")
    return dict(donors=len(donors), opportunities=len(opps), left_in_excel=len(preview["problems"]))


def imported_ids(path: Path | None = None) -> tuple[set, set]:
    """IDs of donors and opportunities that were imported from the Excel tracker (the pipeline stops reading those
    rows from Excel)."""
    donors = {r["donor_id"] for r in table("donors", path) if r.get("origin_file")}
    opps = {r["opportunity_id"] for r in table("opportunities", path) if r.get("origin_file")}
    return donors, opps


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Donor entries database: backups and restore.")
    parser.add_argument("--list-backups", action="store_true")
    parser.add_argument("--backup", action="store_true")
    parser.add_argument("--restore", type=Path, metavar="BACKUP_FILE")
    args = parser.parse_args()
    if args.backup:
        print(f"Backup written: {backup(reason='manual')}")
    if args.restore:
        safety = restore(args.restore)
        print(f"Restored {args.restore.name}. The database as it was just before is kept in {safety}.")
    if args.list_backups or not (args.backup or args.restore):
        for b in list_backups():
            print(f"{b.name}  ({b.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()


# ======================================================================================
# Programme data entered on the dashboard: activity records and monthly indicator reports
# ======================================================================================
ACTIVITY_FIELDS = ["project_id", "activity_id", "district", "sector", "cell", "village", "date", "planned_date",
                   "status", "participants_female", "participants_male", "participants_total", "cost_rwf", "officer"]
REPORT_FIELDS = ["project_id", "district", "period", "indicator_code", "sex", "target_value", "actual_value"]


def _clean_values(rec: dict, fields: list) -> dict:
    out = {}
    for k in fields:
        v = rec.get(k)
        if isinstance(v, str):
            v = v.strip() or None
        if k in ("date", "planned_date", "period") and isinstance(v, str):
            v = dt.date.fromisoformat(v[:10])
        if k in ("participants_female", "participants_male", "participants_total") and v is not None:
            v = int(v) if float(v) == int(float(v)) else float(v)
        if k in ("cost_rwf", "target_value", "actual_value") and v is not None:
            v = float(v)
        out[k] = v
    if out.get("period"):
        out["period"] = out["period"].replace(day=1)
    return out


def _save_programme_entry(kind: str, rec: dict, by: str, path: Path | None, record_id: str | None,
                          staging: Path | None) -> tuple[str, list[str]]:
    """Check an entry with the cleaner's own rules (entry_checks.py), then add it (record_id None) or change it.
    Returns (record ID, warnings). Problems that would hold the row back raise EntryError in plain words."""
    import entry_checks
    _check_staff(by)
    table_name, fields, prefix = (("activities", ACTIVITY_FIELDS, "APP-A") if kind == "activity"
                                  else ("indicator_reports", REPORT_FIELDS, "APP-R"))
    with connect(path) as con:
        current = None
        if record_id:
            row = con.execute(f"SELECT * FROM {table_name} WHERE record_id = ?", (record_id,)).fetchone()
            if row is None:
                raise EntryError(f"{record_id} was not found.")
            current = _clean_values(dict(row), fields)
        new = _clean_values({**(current or {}), **rec}, fields)
        entry_date = dict(row)["entry_date"] if (record_id and kind == "activity") else today().isoformat()
        others = [dict(r) for r in con.execute(f"SELECT * FROM {table_name}") if r["record_id"] != record_id]
        problems, warnings = entry_checks.check(kind, new, entry_date, others, staging)
        if problems:
            raise EntryError(" ".join(problems))
        if record_id is None:
            record_id = _next_id(con, table_name, "record_id", prefix)
            cols = fields + (["entry_date"] if kind == "activity" else [])
            values = [_store(new[k]) for k in fields] + ([entry_date] if kind == "activity" else [])
            con.execute(f"INSERT INTO {table_name} (record_id, {', '.join(cols)}, created_by, created_at) "
                        f"VALUES (?, {', '.join('?' for _ in cols)}, ?, ?)", (record_id, *values, by, now()))
            _history(con, by, table_name, record_id, "added")
        else:
            changed = [k for k in fields if new[k] != current[k]]
            for k in changed:
                con.execute(f"UPDATE {table_name} SET {k} = ? WHERE record_id = ?", (_store(new[k]), record_id))
                _history(con, by, table_name, record_id, "changed", k, current[k], new[k])
            if not changed:
                return record_id, warnings
            con.execute(f"UPDATE {table_name} SET updated_by = ?, updated_at = ? WHERE record_id = ?",
                        (by, now(), record_id))
    backup(path, "save")
    return record_id, warnings


def add_activity(rec: dict, by: str, path: Path | None = None, staging: Path | None = None) -> tuple[str, list[str]]:
    return _save_programme_entry("activity", rec, by, path, None, staging)


def update_activity(record_id: str, changes: dict, by: str, path: Path | None = None,
                    staging: Path | None = None) -> tuple[str, list[str]]:
    return _save_programme_entry("activity", changes, by, path, record_id, staging)


def add_indicator_report(rec: dict, by: str, path: Path | None = None,
                         staging: Path | None = None) -> tuple[str, list[str]]:
    return _save_programme_entry("indicator_report", rec, by, path, None, staging)


def update_indicator_report(record_id: str, changes: dict, by: str, path: Path | None = None,
                            staging: Path | None = None) -> tuple[str, list[str]]:
    return _save_programme_entry("indicator_report", changes, by, path, record_id, staging)
