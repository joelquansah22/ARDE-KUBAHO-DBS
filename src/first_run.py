"""Get a fresh copy of the project ready to show the dashboard (used by run_dashboard.bat and .sh).

1. In synthetic (demonstration) mode, if data/raw/ has no Excel files yet, create the synthetic files.
   With real data (synthetic_mode: false) it never does this: it says where the files should go.
2. If the figures have not been prepared yet (no data warehouse), run the pipeline.

HOW TO RUN
    python src/first_run.py        (the launch scripts do this for you)
"""

from __future__ import annotations

import sys

from common import load_settings, resolve_path


def main() -> int:
    settings = load_settings()
    raw = resolve_path("raw")
    has_files = raw.exists() and any(raw.glob("*.xlsx"))
    if not has_files:
        if settings.get("synthetic_mode"):
            print("No Excel files in data/raw yet: creating the synthetic demonstration files (about a minute)...")
            import generate_synthetic
            generate_synthetic.generate(quiet=True)
        else:
            print(f"There are no Excel files in {raw}. Copy the monthly Excel files there, then start again.")
            return 1
    if not resolve_path("warehouse").exists():
        print("Preparing the figures from the Excel files (about a minute)...")
        import pipeline
        return pipeline.main([])
    return 0


if __name__ == "__main__":
    sys.exit(main())
