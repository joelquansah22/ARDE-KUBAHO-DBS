# Dashboard page load times

*Measured by `tools/capture_screenshots.py` on 19 October 2026 13:35, Google Chrome (headless) at 1366 x 768, main synthetic set, dashboard running on the same laptop.*

Load time = from opening the page address until the page title is shown and Streamlit has finished running the page. **Cold** = first visit after the dashboard starts (queries not yet cached); **warm** = second visit (cached). Target: under 3 seconds.

Runs: **3** (each starts the dashboard afresh); the table shows the **median**, and the slowest run in brackets.

Laptop at the start: CPU load 18%, free memory 1.8 of 15.6 GB; programs with an open window: ApplicationFrameHost, chrome, Code, EXCEL, SnippingTool, Spotify, SystemSettings, TextInputHost, WindowsTerminal, WINWORD.

| Page | Cold (s) | Warm (s) | Under 3 s | Fits 1366 x 768 without scrolling |
|---|---|---|---|---|
| Executive summary | 2.10 (2.13) | 1.46 (1.57) | yes | yes |
| Programme overview | 3.41 (3.67) | 1.15 (3.70) | NO | no (page is 2366 px tall) |
| Indicators | 1.63 (1.72) | 1.87 (2.20) | yes | no (page is 3681 px tall) |
| Geography | 1.78 (1.88) | 1.88 (2.01) | yes | no (page is 1391 px tall) |
| Data quality | 1.78 (1.92) | 1.84 (1.92) | yes | no (page is 5161 px tall) |
| Donor pipeline | 1.51 (1.87) | 1.57 (2.02) | yes | no (page is 2175 px tall) |
| Donor entry | 2.36 (2.50) | 2.05 (2.12) | yes | no (page is 1795 px tall) |
| Data entry | 1.86 (1.97) | 1.84 (2.05) | yes | no (page is 1550 px tall) |
| Upload Excel | 2.63 (2.68) | 0.66 (0.68) | yes | no (page is 933 px tall) |
| Records | 1.32 (2.01) | 1.51 (1.90) | yes | no (page is 1083 px tall) |

Screenshots: `<page>_1366x768.png` (what a 1366 x 768 screen shows) and `<page>_full.png` (the whole page).

**Note (19 October 2026, v1.2):** the laptop was again short of memory (1.8 of 15.6 GB free, other programs open).
Nine of ten pages loaded in under 3 s. **Programme overview took 3.41 s on its first visit** (median of 3 runs;
1.15 s afterwards); that page did not change in v1.2 (on 15 October, with more memory free, it met the target). The
three new pages (Data entry, Upload Excel, Records) met the target. Checking an uploaded file is separate: about
0.6 s for a two-row report, and adding it, which prepares the figures again, about 13 s on the demonstration data.
**Re-measure with other programs closed before quoting load times** (`python tools/capture_screenshots.py --runs 3`).
