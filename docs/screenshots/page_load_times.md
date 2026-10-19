# Dashboard page load times

*Measured by `tools/capture_screenshots.py` on 19 October 2026 17:23, Google Chrome (headless) at 1366 x 768, main synthetic set, dashboard running on the same laptop.*

Load time = from opening the page address until the page title is shown and Streamlit has finished running the page. **Cold** = first visit after the dashboard starts (queries not yet cached); **warm** = second visit (cached). Target: under 3 seconds.

Runs: **1** (each starts the dashboard afresh); the table shows the **median**, and the slowest run in brackets.

Laptop at the start: CPU load 1%, free memory 2.5 of 15.6 GB; programs with an open window: ApplicationFrameHost, chrome, Code, EXCEL, Spotify, SystemSettings, TextInputHost, WindowsTerminal, WINWORD.

| Page | Cold (s) | Warm (s) | Under 3 s | Fits 1366 x 768 without scrolling |
|---|---|---|---|---|
| Home | 16.71 (16.71) | 3.57 (3.57) | NO | yes |
| Executive summary | 7.82 (7.82) | 8.99 (8.99) | NO | yes |
| Programme overview | 11.67 (11.67) | 5.71 (5.71) | NO | no (page is 2381 px tall) |
| Indicators | 5.16 (5.16) | 9.25 (9.25) | NO | no (page is 3696 px tall) |
| Geography | 3.81 (3.81) | 10.59 (10.59) | NO | no (page is 1407 px tall) |
| Data quality | 9.96 (9.96) | 6.95 (6.95) | NO | no (page is 5175 px tall) |
| Donor pipeline | 10.94 (10.94) | 5.66 (5.66) | NO | no (page is 2190 px tall) |
| Donor entry | 8.40 (8.40) | 9.56 (9.56) | NO | no (page is 1811 px tall) |
| Data entry | 5.98 (5.98) | 6.15 (6.15) | NO | no (page is 1566 px tall) |
| Upload Excel | 8.33 (8.33) | 1.40 (1.40) | NO | no (page is 949 px tall) |
| Records | 9.46 (9.46) | 7.59 (7.59) | NO | no (page is 1099 px tall) |

Screenshots: `<page>_1366x768.png` (what a 1366 x 768 screen shows) and `<page>_full.png` (the whole page).

**Note (19 October 2026, redesign):** these times are **not representative and must not be quoted**. Since this
round, a page counts as loaded only when it has been drawn completely (a marker at the end of every page,
`dashboard/app.py`), which is stricter than before; the earlier rule let two screenshots be taken half-drawn. So the
times are not comparable with earlier rounds. The laptop was also slow throughout this round: earlier the same
day, with the earlier rule, every page loaded in under 3 s (Home 1.65 s on its first visit). During this round three
other copies of the dashboard were running on the laptop (started with `run_dashboard.bat`), with other programs
open. **Re-measure on a quiet laptop** (other dashboards and programs closed): `python tools/capture_screenshots.py
--runs 3`. The page heights and the "fits 1366 x 768" column are reliable: **Home and the Executive summary fit without
scrolling**.
