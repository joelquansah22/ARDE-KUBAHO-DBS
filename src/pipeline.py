"""Run the production pipeline with one command: read the Excel files through to the exports.

HOW TO RUN
    python src/pipeline.py            production run: ingest, clean, validate, model, indicators
    python src/pipeline.py --score    the same, then score the cleaning against the synthetic
                                      answer keys (main and held-out sets; testing only)

Other jobs have their own commands and are NOT part of the production run:
    python src/generate_synthetic.py             create the synthetic demonstration data
    python src/generate_synthetic.py --holdout   create the held-out test set
    python src/build_templates.py                rebuild the Excel entry templates
    python src/score_cleaning.py                 score the cleaning on its own

A step that has not been built yet is listed and skipped, so you can always see how far
the prototype has got.
"""

from __future__ import annotations

import argparse
import importlib
import sys
import time

from common import load_settings, resolve_path

# (step name, module in src/, function to call, phase in which it is built)
STEPS = [
    ("Ingest and pseudonymise", "ingest", "main", 2),
    ("Clean and standardise", "clean", "main", 2),
    ("Validate data quality", "validate", "main", 3),
    ("Build star schema and exports", "model", "main", 3),
    ("Compute indicators", "indicators", "main", 4),
]


def run_step(name: str, module_name: str, func_name: str, phase: int) -> None:
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as err:
        if err.name == module_name:
            print(f"[todo] {name}: not built yet (Phase {phase})")
            return
        raise
    t0 = time.perf_counter()
    print(f"[run ] {name} ...")
    getattr(module, func_name)()
    print(f"[done] {name} in {time.perf_counter() - t0:.1f}s")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the ARDE/KUBAHO MEAL pipeline.")
    parser.add_argument("--score", action="store_true",
                        help="after the production run, score the cleaning against the synthetic answer keys")
    args = parser.parse_args(argv)

    raw = resolve_path("raw")
    if not any(raw.glob("*.xlsx")):
        print(f"No Excel files in {raw}. For the demonstration data run: python src/generate_synthetic.py")
        return 1

    started = time.perf_counter()
    for step in STEPS:
        run_step(*step)
    print(f"Production pipeline finished in {time.perf_counter() - started:.1f}s")

    if args.score:
        if not load_settings()["synthetic_mode"]:
            print("Scoring needs the synthetic answer keys; synthetic_mode is off, so scoring is skipped.")
        else:
            t0 = time.perf_counter()
            importlib.import_module("score_cleaning").main([])
            print(f"Scoring finished in {time.perf_counter() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
