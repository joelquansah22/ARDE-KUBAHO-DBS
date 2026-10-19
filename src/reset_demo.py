"""Reset the demonstration: fresh synthetic data, no donor entries, figures prepared (DEMONSTRATION ONLY).

WHAT THIS SCRIPT DOES
---------------------
1. Regenerates the main synthetic set (data/raw/, the answer key), exactly reproducible (documented fingerprint).
2. Deletes the donor entries database (data/app/entries.db) and all its backups (data/app/backups/).
3. Runs the pipeline, so the dashboard shows the synthetic figures with the donor data still in the Excel tracker.

So the one-time "Import from the Excel tracker" (Donor entry page) can be shown live, again and again.
With --import it also runs that import (as MEAL01) and the pipeline again: the state after the demonstration.

SAFETY: it refuses to run unless synthetic_mode is true in config/settings.yaml, so real donor entries can never be
deleted by it. It asks for confirmation unless --yes is given.

HOW TO RUN
    python src/reset_demo.py              (asks "Type RESET to continue")
    python src/reset_demo.py --yes        (no question, e.g. just before a presentation)
    python src/reset_demo.py --yes --import
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from common import load_settings


def clear_entries(db: Path) -> list[Path]:
    """Delete the entries database and its backups folder; returns what was deleted."""
    import app_store
    removed = []
    for path in (db, Path(str(db) + "-journal")):
        if path.exists():
            path.unlink()
            removed.append(path)
    folder = app_store.backup_folder(db)
    if folder.exists():
        shutil.rmtree(folder)
        removed.append(folder)
    return removed


def reset(do_import: bool = False, db: Path | None = None) -> dict:
    if not load_settings().get("synthetic_mode"):
        raise SystemExit("STOPPED: synthetic_mode is off. reset_demo.py only works on the demonstration data and would "
                         "delete real donor entries.")
    import app_store
    import generate_synthetic
    import pipeline
    db = Path(db or app_store.db_path())
    print("1/3 Regenerating the synthetic demonstration data...")
    generate_synthetic.generate(quiet=True)
    print("2/3 Clearing the donor entries and their backups...")
    removed = clear_entries(db)
    print("   " + (", ".join(p.name for p in removed) if removed else "nothing to clear"))
    print("3/3 Preparing the figures...")
    if pipeline.main([]) != 0:
        raise SystemExit("The pipeline did not finish: see the messages above.")
    result = dict(removed=[str(p) for p in removed])
    if do_import:
        print("Importing the Excel tracker (as MEAL01) and preparing the figures again...")
        result["import"] = app_store.import_tracker("MEAL01", path=db)
        print(f"   {result['import']}")
        pipeline.main([])
    print("Demo ready." + ("" if do_import else " The donor data is in the Excel tracker: show the import live on the "
                                                "Donor entry page."))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--yes", action="store_true", help="do not ask for confirmation")
    parser.add_argument("--import", dest="do_import", action="store_true", help="also run the tracker import")
    args = parser.parse_args(argv)
    if not args.yes and input("This deletes all donor entries and regenerates the demonstration data. "
                              "Type RESET to continue: ").strip() != "RESET":
        print("Nothing changed.")
        return 1
    reset(args.do_import)
    return 0


if __name__ == "__main__":
    sys.exit(main())
