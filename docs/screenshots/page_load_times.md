# Dashboard page load times

*Measured by `tools/capture_screenshots.py` on 15 October 2026 01:26, Google Chrome (headless) at 1366 x 768, main synthetic set, dashboard running on the same laptop.*

Load time = from opening the page address until the page title is shown and Streamlit has finished running the page. **Cold** = first visit after the dashboard starts (queries not yet cached); **warm** = second visit (cached). Target: under 3 seconds.

| Page | Cold (s) | Warm (s) | Under 3 s | Fits 1366 x 768 without scrolling |
|---|---|---|---|---|
| Executive summary | 4.16 | 1.96 | NO | yes |
| Programme overview | 3.64 | 1.37 | NO | no (page is 1822 px tall) |
| Indicators | 1.49 | 2.43 | yes | no (page is 3580 px tall) |
| Geography | 1.05 | 2.51 | yes | no (page is 1292 px tall) |
| Data quality | 1.46 | 2.32 | yes | no (page is 4824 px tall) |
| Donor pipeline | 1.20 | 1.83 | yes | no (page is 2013 px tall) |

Screenshots: `<page>_1366x768.png` (what a 1366 x 768 screen shows) and `<page>_full.png` (the whole page).

**Note (15 October 2026, Phase 6):** this run was taken while the laptop was busy with other programs. The previous
version of the dashboard (commit 96aff77), measured straight afterwards on the same laptop, was just as slow (Executive
summary 3.57 s, Programme overview 3.63 s first visit), against 1.1 s and 1.0 s earlier the same day. Measured inside
Python without the browser, every page runs in 0.6 to 1.6 s on its first visit and 0.1 to 0.7 s afterwards. Re-measure
on a quiet laptop before quoting these figures (Phase 7 evaluation).
