# Dashboard page load times

*Measured by `tools/capture_screenshots.py` on 15 October 2026 00:57, Google Chrome (headless) at 1366 x 768, main synthetic set, dashboard running on the same laptop.*

Load time = from opening the page address until the page title is shown and Streamlit has finished running the page. **Cold** = first visit after the dashboard starts (queries not yet cached); **warm** = second visit (cached). Target: under 3 seconds.

| Page | Cold (s) | Warm (s) | Under 3 s | Fits 1366 x 768 without scrolling |
|---|---|---|---|---|
| Executive summary | 1.11 | 0.46 | yes | yes |
| Programme overview | 0.99 | 0.64 | yes | no (page is 1480 px tall) |
| Indicators | 0.48 | 0.62 | yes | no (page is 3592 px tall) |
| Geography | 0.40 | 0.70 | yes | no (page is 1292 px tall) |
| Data quality | 0.50 | 0.67 | yes | no (page is 4629 px tall) |
| Donor pipeline | 0.46 | 0.64 | yes | no (page is 1763 px tall) |

Screenshots: `<page>_1366x768.png` (what a 1366 x 768 screen shows) and `<page>_full.png` (the whole page).
