# Dashboard page load times

*Measured by `tools/capture_screenshots.py` on 15 October 2026 15:26, Google Chrome (headless) at 1366 x 768, main synthetic set, dashboard running on the same laptop.*

Load time = from opening the page address until the page title is shown and Streamlit has finished running the page. **Cold** = first visit after the dashboard starts (queries not yet cached); **warm** = second visit (cached). Target: under 3 seconds.

Runs: **3** (each starts the dashboard afresh); the table shows the **median**, and the slowest run in brackets.

Laptop at the start: CPU load 6%, free memory 2 of 15.6 GB; programs with an open window: ApplicationFrameHost, chrome, Code, EXCEL, mc-webview-cnt, Spotify, SystemSettings, TextInputHost, WINWORD.

| Page | Cold (s) | Warm (s) | Under 3 s | Fits 1366 x 768 without scrolling |
|---|---|---|---|---|
| Executive summary | 1.16 (1.58) | 0.52 (0.90) | yes | yes |
| Programme overview | 3.43 (3.51) | 1.11 (1.23) | NO | no (page is 2259 px tall) |
| Indicators | 1.78 (1.89) | 2.05 (2.16) | yes | no (page is 3672 px tall) |
| Geography | 1.29 (1.58) | 2.17 (2.61) | yes | no (page is 1384 px tall) |
| Data quality | 1.69 (1.82) | 1.89 (1.94) | yes | no (page is 4916 px tall) |
| Donor pipeline | 1.29 (1.62) | 1.58 (1.90) | yes | no (page is 2105 px tall) |

Screenshots: `<page>_1366x768.png` (what a 1366 x 768 screen shows) and `<page>_full.png` (the whole page).
