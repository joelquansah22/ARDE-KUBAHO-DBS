# Demo script: 10-minute walkthrough for the final presentation

For the presenter(s). The demonstration follows the executive director's three questions, then traces one data
problem from the dashboard back to the Excel row it came from. Figures below are from the main synthetic set on
15 October 2026; **check them on the day** (they change if the data is regenerated).

## Before the presentation (15 minutes, the day before and again an hour before)

- [ ] Laptop plugged in, other programs closed (load times are better), screen at 1366 × 768 or larger, browser zoom
      100%.
- [ ] `python src/pipeline.py` run; dashboard started with `run_dashboard.bat`; every page opened once (so the first
      visits are fast during the talk).
- [ ] Filters at their defaults (all programmes, all projects, all districts, 01/07/2023 to 30/06/2026, sex All, RWF).
- [ ] `data/raw/SYNTHETIC_indicator_reports_WASH.xlsx` open in Excel on the **FY2025-26** sheet, scrolled to the top.
- [ ] Backup: the screenshots in `docs/screenshots/` and a PDF donor report in case the laptop fails.

## The walkthrough

| Time | Show | Say (in your own words) |
|---|---|---|
| 0:00 to 1:00 | Executive summary, pointing at the yellow banner | "ARDE/KUBAHO keeps its records in Excel and on paper, spread over many files. This prototype reads those files as they are, checks and cleans them, and answers the director's questions on one screen. Everything you see is **synthetic**: invented records with deliberately realistic mistakes, because we have not received real data." |
| 1:00 to 2:30 | **Question 1: "Are we on track this quarter?"** The three tiles and the list | "1 of 11 indicators is on track, 2 at risk, 1 off track. The off-track one is people with access to improved water: 68% of target. Every status has a symbol and a word, never colour alone. And one project is flagged: Hygiene Behaviour Change is over budget by RWF 14.7 million, 10%." Click **See all indicators**, point at one row's "Compared with records" column, then come back |
| 2:30 to 4:00 | **Question 2: "Can we trust these numbers?"** | "The data-quality score is 96%; the weakest dimension is timeliness. This quarter, 4 of 13 comparisons between the monthly reports and the activity records disagree by more than 10% and at least 5 people. 26 records wait for review, about 20 minutes of the MEAL officer's time a month. Records with serious problems, 235 of them, are quarantined, not silently dropped or guessed." |
| 4:00 to 5:30 | **Question 3: "What funding is coming up?"** | "10 deadlines in the next 90 days, a weighted open pipeline of RWF 2.45 billion, and 13 follow-up actions overdue. The pipeline gap compares the annual budget of projects ending within 12 months with the weighted pipeline for their theme: a draft definition we will agree with ARDE/KUBAHO." Click **See the donor pipeline** and show the stage bars briefly |
| 5:30 to 8:30 | **Trace one problem to its Excel row** (below) | |
| 8:30 to 9:30 | Programme overview, **Generate donor report** for PRJ01, FY2025/26 Q4; open the PDF | "The quarterly donor report takes under a second. In the evaluation we will time how long the same report takes by hand from the raw files." |
| 9:30 to 10:00 | Close | "Free tools, one laptop, Excel stays the front door, no names leave the reading step. Next: real data on one pilot programme, a co-design session for the indicators, and a usability test with staff." |

### Tracing one data problem (5:30 to 8:30)

1. **Indicators** page, scroll to **Reported versus records**. In the indicator box choose *Number of people with
   access to improved water sources*.
2. Point at the chart: "Reported (blue) and what the activity records show (orange), month by month."
3. In **Gaps to follow up** (most recent first), the top row: **June 2026, PRJ01, Kayonza: reported 35, records 28,
   "Reported 7 more than the records (20% of the report)"**, and the column **Report to check:
   SYNTHETIC_indicator_reports_WASH.xlsx, FY2025-26: row 32**.
4. Switch to **Excel**, row 32: `PRJ01 | KAYONZA | 2026-06 | WASH-01 | ... | 32  | 35 | FO01`. "Here is the
   officer's report: 35 people. Notice the district typed in capitals and the target typed as text with a space: the
   pipeline handled both without changing the officer's file."
5. "The water-point activity records for Kayonza in June add up to 28 people. Either the report is inflated, or some
   activities were never recorded. The tool does not decide which: it gives the MEAL officer the exact row to ask
   FO01 about. Every figure on the dashboard can be traced back like this, to a file, a sheet and a row."
6. (If time) **Data quality** page, **Work lists**, choose **FO01**, and show the download button: "the officer's own
   list of records to correct."

*(In the synthetic answer key this is a planted over-report: the true figure was 28. Say this only if asked.)*

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

**"Did you meet your targets?"**
"Our proposal deliberately set no numeric targets: targets are to be negotiated after the baseline audit, and
improvements were not promised before the data are examined. We report results on the five measures in the proposal;
`docs/evaluation_summary.md` shows what is measured, what still needs human testing, and what needs real data."

**"What about personal data?"**
"Names, phone numbers and ID numbers are used once, to find people registered twice, and then replaced by a coded
key with a secret salt kept outside the project. They never reach the warehouse, the dashboard or the reports, and
the model refuses to save if a personal column appears. The dashboard only accepts connections from the laptop it
runs on."

**"Why Streamlit if the proposal named Power BI?"**
"Streamlit is free, scriptable and testable, which let us write 360-odd automatic tests, including cross-page
consistency checks. Every table is also exported as Parquet with a Power BI guide, so ARDE/KUBAHO can choose."

**"What does not work yet?"**
"Month-first dates are not read until staff confirm they use them; nicknames and initials wait for review instead of
being merged; discrepancies under 5 people are not flagged; all indicators are drafts; and the human tests (timing,
usability, handover) are still to run. They are listed in `docs/limitations_and_roadmap.md`."
