"""Start the dashboard, time every page in a real browser, and save screenshots for the report.

Uses Playwright with the Google Chrome already installed on the computer (no browser download).
Install once with:  python -m pip install -r requirements-dev.txt

HOW TO RUN
    python tools/capture_screenshots.py              one timing run, plus screenshots
    python tools/capture_screenshots.py --runs 3     three timing runs (the median is reported), plus screenshots

For load times worth quoting, close other programs first (browsers, Office, music, video calls). The file records
which programs had a window open, the CPU load and the free memory at the start, so readers can judge.

Writes docs/screenshots/*.png and docs/screenshots/page_load_times.md.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import socket
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "screenshots"
PORT = 8599
PAGES = [("executive_summary", "", "Executive summary"), ("programme_overview", "overview", "Programme overview"),
         ("indicators", "indicators", "Indicators"), ("geography", "geography", "Geography"),
         ("data_quality", "data-quality", "Data quality"), ("donor_pipeline", "donor-pipeline", "Donor pipeline"),
         ("donor_entry", "donor-entry", "Donor entry")]
WIDTH, HEIGHT = 1366, 768


def wait_for_port(port: int, timeout: float = 60) -> None:
    end = time.time() + timeout
    while time.time() < end:
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.3)
    raise RuntimeError("The dashboard did not start.")


def wait_until_loaded(page, title: str) -> None:
    """Loaded = the page title is shown and Streamlit has finished running the page script."""
    page.wait_for_selector(f"h1:has-text('{title}')", timeout=60_000)
    page.wait_for_function("""() => {
        const s = document.querySelector('[data-testid="stStatusWidget"]');
        return !s || !s.innerText.toLowerCase().includes('running');
    }""", timeout=60_000)
    page.wait_for_function("""() => document.querySelectorAll('[data-testid="stSkeleton"]').length === 0""",
                           timeout=60_000)


def machine_state() -> dict:
    """Programs with an open window, CPU load and free memory (Windows; empty elsewhere)."""
    if sys.platform != "win32":
        return {}
    script = ("$p = Get-Process | Where-Object { $_.MainWindowTitle -ne '' } | Select-Object -ExpandProperty Name | "
              "Sort-Object -Unique; $c = (Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage "
              "-Average).Average; $o = Get-CimInstance Win32_OperatingSystem; "
              "@{programs=@($p); cpu=$c; free_gb=[math]::Round($o.FreePhysicalMemory/1MB,1); "
              "total_gb=[math]::Round($o.TotalVisibleMemorySize/1MB,1)} | ConvertTo-Json")
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True, text=True,
                             timeout=60).stdout
        return json.loads(out)
    except Exception:  # noqa: BLE001 - the state is a note only; never stop the measurement for it
        return {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Time every dashboard page and save screenshots.")
    parser.add_argument("--runs", type=int, default=1, help="timing runs (each starts the dashboard afresh)")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    state = machine_state()
    all_runs = [timing_run(PORT + 1 + i) for i in range(max(1, args.runs) - 1)]   # a new port each run
    results = timing_run(PORT, screenshots=True)
    all_runs.append(results)
    write_times(all_runs, state)
    return 0


def timing_run(port: int, screenshots: bool = False) -> list[dict]:
    """Start the dashboard, visit every page twice (cold, then warm), close the dashboard."""
    server = subprocess.Popen([sys.executable, "-m", "streamlit", "run", str(ROOT / "dashboard" / "app.py"),
                               "--server.port", str(port), "--server.headless", "true"],
                              cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    results = []
    try:
        wait_for_port(port)
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True)
            context = browser.new_context(viewport={"width": WIDTH, "height": HEIGHT})
            page = context.new_page()
            for name, path, title in PAGES:
                url = f"http://127.0.0.1:{port}/{path}"
                timings = []
                for attempt in ("cold", "warm"):      # first visit fills the cache; the second uses it
                    start = time.perf_counter()
                    page.goto(url)
                    wait_until_loaded(page, title)
                    timings.append(time.perf_counter() - start)
                if not screenshots:
                    results.append(dict(page=title, cold=timings[0], warm=timings[1], fits=None, height=None))
                    continue
                page.wait_for_timeout(1500)           # let charts and tables finish drawing before measuring
                fits = page.evaluate("""() => {
                    const m = document.querySelector('[data-testid="stMain"]') ||
                              document.querySelector('[data-testid="stAppViewContainer"]');
                    return {scroll: m.scrollHeight, view: m.clientHeight};
                }""")
                page.screenshot(path=str(OUT / f"{name}_1366x768.png"))
                # A tall window to capture the whole page in one image.
                page.set_viewport_size({"width": WIDTH, "height": max(HEIGHT, fits["scroll"] + 60)})
                page.wait_for_timeout(800)
                page.screenshot(path=str(OUT / f"{name}_full.png"))
                page.set_viewport_size({"width": WIDTH, "height": HEIGHT})
                results.append(dict(page=title, cold=timings[0], warm=timings[1],
                                    fits=fits["scroll"] <= fits["view"] + 2, height=fits["scroll"]))
            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=30)
    return results


def write_times(all_runs: list[list[dict]], state: dict) -> None:
    import statistics
    results = []
    for i, r in enumerate(all_runs[-1]):
        cold = [run[i]["cold"] for run in all_runs]
        warm = [run[i]["warm"] for run in all_runs]
        results.append(dict(r, cold=statistics.median(cold), warm=statistics.median(warm),
                            cold_max=max(cold), warm_max=max(warm)))

    lines = ["# Dashboard page load times", "",
             f"*Measured by `tools/capture_screenshots.py` on {dt.datetime.now():%d %B %Y %H:%M}, Google Chrome "
             f"(headless) at {WIDTH} x {HEIGHT}, main synthetic set, dashboard running on the same laptop.*", "",
             "Load time = from opening the page address until the page title is shown and Streamlit has finished "
             "running the page. **Cold** = first visit after the dashboard starts (queries not yet cached); "
             "**warm** = second visit (cached). Target: under 3 seconds.", "",
             f"Runs: **{len(all_runs)}** (each starts the dashboard afresh); the table shows the **median**, and the "
             "slowest run in brackets.", ""]
    if state:
        lines += [f"Laptop at the start: CPU load {state.get('cpu')}%, free memory {state.get('free_gb')} of "
                  f"{state.get('total_gb')} GB; programs with an open window: "
                  f"{', '.join(state.get('programs') or []) or 'none'}.", ""]
    lines += ["| Page | Cold (s) | Warm (s) | Under 3 s | Fits 1366 x 768 without scrolling |", "|---|---|---|---|---|"]
    for r in results:
        lines.append(f"| {r['page']} | {r['cold']:.2f} ({r['cold_max']:.2f}) | {r['warm']:.2f} ({r['warm_max']:.2f}) | "
                     f"{'yes' if max(r['cold'], r['warm']) < 3 else 'NO'} | "
                     f"{'yes' if r['fits'] else 'no (page is ' + str(r['height']) + ' px tall)'} |")
    lines += ["", "Screenshots: `<page>_1366x768.png` (what a 1366 x 768 screen shows) and `<page>_full.png` "
              "(the whole page)."]
    (OUT / "page_load_times.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
