# Dashboard page load times

*Measured by `tools/capture_screenshots.py` on 19 October 2026 12:17, Google Chrome (headless) at 1366 x 768, main synthetic set, dashboard running on the same laptop.*

Load time = from opening the page address until the page title is shown and Streamlit has finished running the page. **Cold** = first visit after the dashboard starts (queries not yet cached); **warm** = second visit (cached). Target: under 3 seconds.

Runs: **3** (each starts the dashboard afresh); the table shows the **median**, and the slowest run in brackets.

Laptop at the start: CPU load 11%, free memory 1.8 of 15.6 GB; programs with an open window: ApplicationFrameHost, chrome, Code, EXCEL, Spotify, SystemSettings, TextInputHost, WindowsTerminal, WINWORD.

| Page | Cold (s) | Warm (s) | Under 3 s | Fits 1366 x 768 without scrolling |
|---|---|---|---|---|
| Executive summary | 7.04 (7.90) | 3.96 (4.92) | NO | yes |
| Programme overview | 2.51 (2.79) | 7.36 (9.22) | NO | no (page is 2366 px tall) |
| Indicators | 3.34 (3.55) | 5.04 (7.10) | NO | no (page is 3681 px tall) |
| Geography | 1.89 (4.03) | 1.95 (2.82) | yes | no (page is 1355 px tall) |
| Data quality | 3.97 (4.07) | 3.38 (3.55) | NO | no (page is 4787 px tall) |
| Donor pipeline | 4.53 (6.92) | 5.10 (6.30) | NO | no (page is 2027 px tall) |
| Donor entry | 3.48 (5.04) | 4.36 (5.23) | NO | no (page is 1608 px tall) |

Screenshots: `<page>_1366x768.png` (what a 1366 x 768 screen shows) and `<page>_full.png` (the whole page).

**Note (19 October 2026, v1.1):** this run is far slower than on 15 October (every page under 3 s then). The laptop was
short of memory (1.8 of 15.6 GB free; several Chrome windows of 0.3 to 0.7 GB each). The previous version (commit
9d580e9, which met the target on 15 October), measured straight afterwards on the same laptop, was just as slow
(Executive summary 13.99 s first visit, 3.24 s afterwards), so the slowdown is the laptop's state, not this version.
Measured inside Python without the browser, the pages take 1.5 to 3.3 s on their first visit and 0.08 to 0.6 s
afterwards (Donor entry 1.66 s and 0.39 s, after its preview and Excel backup were cached). **Re-measure with other
programs closed before quoting load times** (`python tools/capture_screenshots.py --runs 3`).
