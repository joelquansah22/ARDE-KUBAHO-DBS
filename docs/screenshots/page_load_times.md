# Dashboard page load times

*Measured by `tools/capture_screenshots.py` on 15 October 2026 16:44, Google Chrome (headless) at 1366 x 768, main synthetic set, dashboard running on the same laptop.*

Load time = from opening the page address until the page title is shown and Streamlit has finished running the page. **Cold** = first visit after the dashboard starts (queries not yet cached); **warm** = second visit (cached). Target: under 3 seconds.

Runs: **3** (each starts the dashboard afresh); the table shows the **median**, and the slowest run in brackets.

Laptop at the start: CPU load 20%, free memory 1.9 of 15.6 GB; programs with an open window: ApplicationFrameHost, chrome, Code, EXCEL, Spotify, SystemSettings, TextInputHost, WindowsTerminal, WINWORD, Zoom.

| Page | Cold (s) | Warm (s) | Under 3 s | Fits 1366 x 768 without scrolling |
|---|---|---|---|---|
| Executive summary | 2.24 (2.80) | 0.52 (0.68) | yes | yes |
| Programme overview | 2.73 (2.75) | 0.73 (0.74) | yes | no (page is 2366 px tall) |
| Indicators | 0.93 (0.95) | 1.06 (1.15) | yes | no (page is 3681 px tall) |
| Geography | 0.96 (1.18) | 0.88 (1.05) | yes | no (page is 1391 px tall) |
| Data quality | 1.04 (1.19) | 1.36 (1.37) | yes | no (page is 4927 px tall) |
| Donor pipeline | 1.00 (1.38) | 0.94 (1.08) | yes | no (page is 2114 px tall) |
| Donor entry | 1.57 (2.19) | 0.48 (0.50) | yes | no (page is 1295 px tall) |

Screenshots: `<page>_1366x768.png` (what a 1366 x 768 screen shows) and `<page>_full.png` (the whole page).
