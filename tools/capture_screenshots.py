"""Start the dashboard, time every page in a real browser, and save screenshots for the report.

Uses Playwright with the Google Chrome already installed on the computer (no browser download).
Install once with:  python -m pip install -r requirements-dev.txt

HOW TO RUN
    python tools/capture_screenshots.py

Writes docs/screenshots/*.png and docs/screenshots/page_load_times.md.
"""

from __future__ import annotations

import datetime as dt
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
         ("data_quality", "data-quality", "Data quality"), ("donor_pipeline", "donor-pipeline", "Donor pipeline")]
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


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    server = subprocess.Popen([sys.executable, "-m", "streamlit", "run", str(ROOT / "dashboard" / "app.py"),
                               "--server.port", str(PORT), "--server.headless", "true"],
                              cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    results = []
    try:
        wait_for_port(PORT)
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True)
            context = browser.new_context(viewport={"width": WIDTH, "height": HEIGHT})
            page = context.new_page()
            for name, path, title in PAGES:
                url = f"http://127.0.0.1:{PORT}/{path}"
                timings = []
                for attempt in ("cold", "warm"):      # first visit fills the cache; the second uses it
                    start = time.perf_counter()
                    page.goto(url)
                    wait_until_loaded(page, title)
                    timings.append(time.perf_counter() - start)
                page.wait_for_timeout(800)            # let charts finish drawing before the screenshot
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

    lines = ["# Dashboard page load times", "",
             f"*Measured by `tools/capture_screenshots.py` on {dt.datetime.now():%d %B %Y %H:%M}, Google Chrome "
             f"(headless) at {WIDTH} x {HEIGHT}, main synthetic set, dashboard running on the same laptop.*", "",
             "Load time = from opening the page address until the page title is shown and Streamlit has finished "
             "running the page. **Cold** = first visit after the dashboard starts (queries not yet cached); "
             "**warm** = second visit (cached). Target: under 3 seconds.", "",
             "| Page | Cold (s) | Warm (s) | Under 3 s | Fits 1366 x 768 without scrolling |", "|---|---|---|---|---|"]
    for r in results:
        lines.append(f"| {r['page']} | {r['cold']:.2f} | {r['warm']:.2f} | "
                     f"{'yes' if max(r['cold'], r['warm']) < 3 else 'NO'} | "
                     f"{'yes' if r['fits'] else 'no (page is ' + str(r['height']) + ' px tall)'} |")
    lines += ["", "Screenshots: `<page>_1366x768.png` (what a 1366 x 768 screen shows) and `<page>_full.png` "
              "(the whole page)."]
    (OUT / "page_load_times.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
