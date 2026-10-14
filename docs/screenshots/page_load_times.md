# Dashboard page load times

*Measured by `tools/capture_screenshots.py` on 15 October 2026 00:03, Google Chrome (headless) at 1366 x 768, main synthetic set, dashboard running on the same laptop.*

Load time = from opening the page address until the page title is shown and Streamlit has finished running the page. **Cold** = first visit after the dashboard starts (queries not yet cached); **warm** = second visit (cached). Target: under 3 seconds.

| Page | Cold (s) | Warm (s) | Under 3 s | Fits 1366 x 768 without scrolling |
|---|---|---|---|---|
| Executive summary | 1.08 | 0.48 | yes | yes |
| Programme overview | 1.30 | 0.47 | yes | no (page is 1352 px tall) |
| Indicators | 0.51 | 0.65 | yes | no (page is 2274 px tall) |
| Geography | 0.41 | 0.77 | yes | no (page is 1213 px tall) |
| Data quality | 0.57 | 0.70 | yes | no (page is 2744 px tall) |
| Donor pipeline | 0.52 | 0.67 | yes | no (page is 1517 px tall) |

Screenshots: `<page>_1366x768.png` (what a 1366 x 768 screen shows) and `<page>_full.png` (the whole page).
