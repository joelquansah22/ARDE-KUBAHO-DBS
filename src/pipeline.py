"""Run the whole prototype pipeline with one command.

HOW TO RUN
    python src/pipeline.py

Steps run in order. A step that has not been built yet is listed and skipped,
so you can always see how far the prototype has got.
"""

from __future__ import annotations

import importlib
import sys
import time

from common import load_settings

# (step name, module in src/, function to call, phase in which it is built)
STEPS = [
    ("Build Excel entry templates", "build_templates", "main", 1),
    ("Generate synthetic data", "generate_synthetic", "generate", 1),
    ("Ingest and pseudonymise", "ingest", "main", 2),
    ("Clean and standardise", "clean", "main", 2),
    ("Validate data quality", "validate", "main", 3),
    ("Build star schema", "model", "main", 3),
    ("Compute indicators", "indicators", "main", 4),
    ("Before/after evaluation", "evaluate", "main", 7),
]


def main() -> int:
    settings = load_settings()
    started = time.perf_counter()
    for name, module_name, func_name, phase in STEPS:
        if module_name == "generate_synthetic" and not settings["synthetic_mode"]:
            print(f"[skip] {name}: synthetic_mode is off")
            continue
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError as err:
            if err.name == module_name:
                print(f"[todo] {name}: not built yet (Phase {phase})")
                continue
            raise
        t0 = time.perf_counter()
        print(f"[run ] {name} ...")
        getattr(module, func_name)()
        print(f"[done] {name} in {time.perf_counter() - t0:.1f}s")
    print(f"Pipeline finished in {time.perf_counter() - started:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
