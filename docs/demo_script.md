# Demo script: 10-minute walkthrough for the final presentation

For the presenter(s). The demonstration follows the executive director's three questions, traces one data problem
from the dashboard back to the Excel row it came from, then shows data entry: an Excel upload, a form entry appearing
on the dashboard, and donor data.
Figures below are from the main synthetic set on 19 October 2026; **check them on the day** (they change if the
data is regenerated).

## Before the presentation (20 minutes, the day before and again an hour before)

- [ ] **Reset the demonstration:** `python src/reset_demo.py --yes`. It regenerates the synthetic data, deletes the
      donor entries and their backups, and prepares the figures, so the donor data is back in the Excel tracker and the
      import can be shown live. (After the talk, the state is kept; run it again before the next demonstration.)
- [ ] Laptop plugged in, other programs closed (load times are better), screen at 1366 × 768 or larger, browser zoom
      100%.
- [ ] Dashboard started with `run_dashboard.bat`; every page opened once (so the first visits are fast during the
      talk), then back to **Home**, where the demonstration starts.
- [ ] Filters at their defaults (all programmes, all projects, all districts, 01/07/2023 to 30/06/2026, sex All, RWF).
- [ ] Donor entry page: **You are** set to **MEAL01** (the same choice is used on Data entry and Upload Excel).
- [ ] **The file for the upload step:** `python tools/make_demo_upload.py` writes
      `data/exports/SYNTHETIC_june_report_PRJ01.xlsx`, the blank monthly report template with **two rows**: a report
      missing from the data (PRJ01, Nyagatare, February 2026, WASH-01) and one deliberately wrong (PRJ01, Kayonza,
      August 2024, achieved typed as "about 30"). Run it after the reset.
- [ ] Data entry page, **New monthly indicator report**, PRJ01, Bugesera: the line under the form lists the missing
      months; **May 2025** is the one used in the demonstration.
- [ ] `data/raw/SYNTHETIC_indicator_reports_WASH.xlsx` open in Excel on the **FY2025-26** sheet, scrolled to the top.
- [ ] Backup: the screenshots in `docs/screenshots/` and a PDF donor report in case the laptop fails.

## The walkthrough (10 minutes)

| Time | Show | Say (in your own words) |
|---|---|---|
| 0:00 to 0:45 | **Home**, pointing at the yellow banner, then the key figures, "Needs attention" and the tiles; click the **Executive summary** tile | "ARDE/KUBAHO keeps its records in Excel and on paper, spread over many files. This prototype reads those files as they are, checks and cleans them, and puts everything on one screen: the key figures, what needs attention today, and every page, grouped as insights, data and donors. Everything you see is **synthetic**: invented records with realistic mistakes, because we have not received real data." |
| 0:45 to 1:45 | **Question 1: "Are we on track this quarter?"** | "1 of 11 indicators is on track, 2 at risk, 1 off track: people with access to improved water, 68% of target. Every status has a symbol and a word, never colour alone. One project is over budget: Hygiene Behaviour Change, by RWF 14.7 million, 10%." |
| 1:45 to 2:45 | **Question 2: "Can we trust these numbers?"** | "Data quality 96%; the weakest dimension is timeliness. This quarter, 4 of 13 comparisons between monthly reports and activity records disagree by more than 10% and at least 5 people. Records with serious problems are quarantined, not dropped or guessed." |
| 2:45 to 3:30 | **Question 3: "What funding is coming up?"** | "10 deadlines in 90 days, a weighted open pipeline of RWF 2.45 billion, 13 follow-up actions overdue." Click **See the donor pipeline**; point at the line under the title: "right now the donor data still comes from an Excel tracker." |
| 3:30 to 5:30 | **Trace one problem to its Excel row** (below) | |
| 5:30 to 6:30 | **Upload and form entry** (below) | |
| 6:30 to 8:30 | **Donor entry** (below) | |
| 8:30 to 9:15 | Programme overview, **Generate donor report** for PRJ01, FY2025/26 Q4; open the PDF | "The quarterly donor report takes under a second. In the evaluation we will time the same report made by hand from the raw files." |
| 9:15 to 10:00 | Close | "Free tools, one laptop, Excel uploads and the app's forms as the front door, no names leave the reading step. Next: real data on one pilot programme, a co-design session for the indicators, and the usability, timing and phone tests with staff." |

### Tracing one data problem (3:30 to 5:30)

1. **Indicators** page, **Reported versus records**: choose *Number of people with access to improved water sources*.
   "Reported (blue) against what the activity records show (gold), month by month."
2. **Gaps to follow up**, top row: **June 2026, PRJ01, Kayonza: reported 35, records 28, "Reported 7 more than the
   records (20% of the report)"**, and **Report to check: SYNTHETIC_indicator_reports_WASH.xlsx, FY2025-26: row 32**.
3. Switch to **Excel**, row 32: `PRJ01 | KAYONZA | 2026-06 | WASH-01 | ... | 32  | 35 | FO01`. "The officer's report
   says 35. The district in capitals and the target typed as text were handled without changing the officer's file."
4. "The water-point records for Kayonza in June add up to 28. The tool does not decide who is right: it gives the MEAL
   officer the exact row to ask FO01 about. Every figure can be traced like this, to a file, a sheet and a row."

*(In the synthetic answer key this is a planted over-report: the true figure was 28. Say this only if asked.)*

### Upload and form entry (5:30 to 6:30)

1. **Upload Excel** page (0:25): choose `SYNTHETIC_june_report_PRJ01.xlsx`, **Check the file**. "It reads the file
   exactly as the pipeline would, before anything is added: 1 row accepted, 1 held back: row 3, 'about 30' is not a
   number." Correcting means fixing row 3 in Excel and uploading again.
   Tick, **Add this file**. "The file is kept with the date and who uploaded it, and the figures are prepared again."
2. **Data entry** page (0:20), **New monthly indicator report**: PRJ01, Bugesera, May 2025, WASH-01, target 120,
   achieved 96. **Save monthly report**. (If asked: save it a second time: it is refused, "already entered".)
3. **Records** page (0:15), table **Indicator results**, Source **Entered in the app**: "Here it is, with who entered
   it and when; the uploaded row shows its file and row, and who uploaded it. Export to Excel is one click."
   *(The upload already prepared the figures; for the form entry, the **Update the figures now** button takes about
   20 seconds: press it before going to Records, or show Records after the Donor entry part.)*

### Donor entry (6:30 to 8:30)

1. **Donor entry** page (You are: MEAL01). **Import from the Excel tracker** tab (0:25): "Donor data had two homes.
   This moves it here, once." Show the preview (25 donors, 30 opportunities, nothing to correct), tick the box, click
   **Import now**. "IDs are kept, and each record remembers the Excel row it came from. Individual donors stay
   unnamed."
2. **New opportunity** tab (0:35): title "Safe water for schools - Kayonza", donor **Kestrel Impact Partners**, WASH,
   stage Identified, a deadline next month, RWF 150,000,000, 30%, next action "Send concept note" with a date. Click
   **Save opportunity**. (If asked: try a probability of 120% or a past deadline first: the page refuses and says why.)
3. **Update an opportunity** tab (0:20): choose the new APP-O001, change the stage to **Concept note**, save.
4. **Change history** tab (0:20): "Who changed what, from what to what, and when: the import, the new opportunity, the
   stage change, all under MEAL01."
5. **Backup** tab (0:20): "A dated copy after every save and each start; one button downloads everything to Excel."
6. (Optional, only with time to spare: **Update the figures now** takes about 20 seconds; afterwards the Donor
   pipeline page says the data is kept on this page.)

## If a supervisor asks...

**"Why synthetic data? How do we know it works on real files?"**
"Partner data access was still pending, and we would not develop on real personal data before an agreement under
Rwanda's data protection law. So we built synthetic files that copy the mess a small NGO really has: mixed date
formats, district misspellings, Kinyarwanda codes, duplicates with spelling changes, numbers typed as text, a paper
file with more gaps. Every injected problem is logged, so we can score the cleaner exactly. The limit is that we
wrote both the mess and the cleaner. That is why we ran held-out rounds, and why the real-data checklist makes the
MEAL officer compare our totals with ARDE/KUBAHO's own figures before any number is trusted."

**"What do the evaluation rounds show? Which figure is the real one?"**
"Two figures, and we always quote them together. Held-out 2 used kinds of mess the cleaner had **never seen**: it
fixed or flagged 92.9% of genuine errors. That is the measure of robustness to new mess. We then fixed the cleaner
against those kinds of mess and ran a final round on **fresh data with the same kinds of mess**: 98.1%. That shows
the fixes generalise to new records, not that they cover new kinds of mess. In both rounds it made no false
corrections, and every duplicate it merged was a true duplicate. We froze both scorecards before looking at the
results and made no changes afterwards."

**"Who can change the data?"**
"Anyone using the laptop: there is no login, on the Donor entry, Data entry and Upload Excel pages alike. Staff pick their code, and the change history records who people say
they are. That is acceptable on one protected laptop, and it is listed as a limitation: real user accounts are
needed before several people use it."

**"Did you meet your targets?"**
"Our proposal deliberately set no numeric targets: targets are to be negotiated after the baseline audit, and
improvements were not promised before the data are examined. We report results on the five measures in the proposal;
`docs/evaluation_summary.md` shows what is measured, what still needs human testing, and what needs real data."

**"What about personal data?"**
"Names, phone numbers and ID numbers are used once, to find people registered twice, and then replaced by a coded
key with a secret salt kept outside the project. They never reach the warehouse, the dashboard, the reports or the
donor entries database, and the model refuses to save if a personal column appears. Individual donors are never
named. The dashboard only accepts connections from the laptop it runs on."

**"Why Streamlit if the proposal named Power BI?"**
"Streamlit is free, scriptable and testable, which let us write about 400 automatic tests, including cross-page
consistency checks, and add data entry. Every table is also exported as Parquet with a Power BI guide, so
ARDE/KUBAHO can choose."

**"What does not work yet?"**
"Month-first dates are not read until staff confirm they use them; nicknames and initials wait for review instead of
being merged; discrepancies under 5 people are not flagged; all indicators are drafts; there is no login; and the
human tests (timing, usability, fresh install) are still to run. They are listed in
`docs/limitations_and_roadmap.md`."
