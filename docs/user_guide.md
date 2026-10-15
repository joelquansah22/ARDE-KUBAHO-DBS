# User guide

For ARDE/KUBAHO staff who **use** the dashboard: the executive director, programme managers, the MEAL officer and
field officers. No Python needed. The person who looks after the tool also needs `docs/maintenance_guide.md`.

> The tool currently shows **synthetic (invented) records**, not ARDE/KUBAHO data. The yellow banner on every page
> says so. All indicators are **drafts, for co-design with ARDE/KUBAHO staff**.

---

## 1. What the tool does

```
 Field officers' Excel files  ──►  the pipeline  ──►  checked, cleaned data  ──►  dashboard and donor report
   (data/raw/)                     (one command)      (no names, phones or IDs)
```

1. Staff keep entering data in the **standard Excel templates** (`templates/`).
2. The **pipeline** reads every file, removes names, phone numbers and ID numbers (it keeps a coded key instead),
   corrects what it safely can (date formats, district spellings, "F"/"Gore" for female, numbers typed with "RWF"),
   and **checks** everything else.
3. Rows with a serious problem are **quarantined** (kept aside, not counted) until the Excel file is corrected; rows
   with a smaller doubt go to the **review queue** (counted, but a person should check them).
4. The **dashboard** shows the results; the **donor report** button makes a one-page quarterly summary.

## 2. Opening the dashboard

Double-click **`run_dashboard.bat`** in the project folder. A black window opens (leave it open) and then the
dashboard in your browser (http://localhost:8501). To stop, close the black window.

If the page says **"The figures have not been prepared yet"**, follow the steps on that page (it means the
pipeline has not been run on this computer).

## 3. The filters (left side)

| Filter | What it does |
|---|---|
| Programme, Project | Show one programme or one project. Choosing a programme limits the project list |
| District | Show one district. People are counted where they **registered**; activities where they **took place** |
| Date range | The period for people, activities and spending. Budgets always use the whole project |
| Sex | Women only or men only, where people are counted. Greyed out on pages where it does not apply |
| Currency | RWF or USD (at the rate in the settings, shown when you hover over the "?") |

Filters stay the same when you move between pages. If a selection has no data, the page says so in plain words
("Nothing was recorded ...") instead of showing empty charts.

At the bottom of every page: **when the data was last updated** and from how many files; the list of files is
under "Source files" in the sidebar.

## 4. The pages

Every page starts with a collapsed **"How to read this page"**: open it the first few times.

### Executive summary (the first page)
Three questions on one screen, for the current fiscal quarter:
- **Are we on track?** How many indicators are on track, at risk or off track (with a symbol and words, never colour
  alone), the indicators that are off track or at risk, and any project that is **over budget**.
- **Can we trust these numbers?** The data-quality score, the gaps between reports and records, records to review,
  people who may be registered twice, and records quarantined.
- **Funding: the next 90 days.** Deadlines, the weighted pipeline, pipeline gaps (draft definition) and overdue
  follow-up actions.
Each block has a link to the page with the details.

### Programme overview
- Four tiles: different people reached, activities completed, % women, activity spending.
- **Budget by project**: spending to date against each whole budget. **▲ Warning: over budget by RWF X (Y%)** means
  activity costs already exceed the budget.
- **Target versus actual** for one indicator and fiscal year. A hatched bar is the target for only the months that
  have one.
- **Cost per person reached** by programme (draft measure).
- **Trend** of activities and people served per month.
- **Generate donor report** (section 5 below).

### Indicators
- One row per indicator, for the chosen quarter, year or month: target, actual, % achieved, status.
- **"(worked out)"** after an actual means it is calculated from the activity, register and report files rather than
  typed in a monthly report.
- **"Compared with records"**: what the records say for the same thing, e.g. "Records show 235 (10% lower)".
- **Indicator definitions** (draft): open the section under the table.
- **Drill-down by month** for one indicator; an open diamond ◇ marks a month that includes records still being
  reviewed.
- **Reported versus records**: where reports and records disagree by more than 10% **and** at least 5, the gap is
  listed under "Gaps to follow up", with the row of the Excel report to check.

### Geography
A map and a ranked bar chart by district. "Unknown district" (bar chart and table only) is people whose registration
records are all quarantined.

### Data quality
The overall score and the six dimensions, which checks lower the score, results by file and by field officer,
quarantined records by reason, the review queue per month, and the **work lists**: choose a field officer to see and
download only their records to correct. This page covers all records, so the filters do not apply.

### Donor pipeline
Open opportunities by stage (count, amount requested and weighted value), outcomes (awarded, declined), pipeline gaps
by theme (draft), deadlines in the next 30, 60 and 90 days, overdue next actions, and all opportunities.

Every table has a **Download** button (CSV, opens in Excel).

## 5. Making a donor report

1. Open **Programme overview** and scroll to **Generate donor report**.
2. Choose the **project** and the **quarter**.
3. Click **Generate donor report**. "Report ready" appears in about a second.
4. Click **Download PDF** (one A4 page) or **Download Excel**.
5. **Check it before sending**: the yellow synthetic-data line is on every report while the tool uses invented data;
   indicators marked "target incomplete" or "no target set" need a sentence of explanation for the donor.

## 6. The monthly routine (suggested; to be agreed with ARDE/KUBAHO)

| When | Who | What |
|---|---|---|
| By the 5th | Field officers | Send the month's activity, register and indicator-report files (standard templates) |
| By the 7th | MEAL officer | Save the files in `data/raw/`, run the pipeline (maintenance guide, section 2) |
| By the 10th | MEAL officer | Data quality page: send each officer their work list; check the review queue (about 20 minutes a month on the demonstration data) |
| By the 15th | Officers, MEAL officer | Correct the Excel files; run the pipeline again |
| Monthly meeting | Managers, director | Executive summary and Indicators pages; donor reports as due |

Printing: use the browser's Print (Ctrl+P). Pages print on **A4 landscape** without the sidebar and buttons.

## 7. Problems and what to do

| What you see | What it means | What to do |
|---|---|---|
| "The figures have not been prepared yet" | The pipeline has not been run on this computer | Double-click `run_dashboard.bat`, or run `python src/pipeline.py` (maintenance guide) |
| The browser does not open | The dashboard started but the browser was not told | Type http://localhost:8501 into the browser |
| "Nothing was recorded ..." | The filters select a period, project or district with no data | Widen the date range or clear a filter |
| A file's records are missing | The pipeline **skipped** a sheet it could not read | Data quality page, red box at the top; the maintenance guide explains the fix |
| A number looks wrong | It may come from a record in the review queue, or a quarantined record is missing | Indicators drill-down (◇ months) and the Data quality work lists; check the Excel row shown |
| Figures did not change after correcting a file | The pipeline was not run again, or the page was not reloaded | Run the pipeline, then press F5 in the browser |
| "python is not recognised" | Python is not installed, or installed without "Add to PATH" | Reinstall Python with the tick (README, step 1) |

## 8. Glossary

| Term | Meaning |
|---|---|
| **Activity record** | One row in an activity monitoring file: one activity (training, meeting, construction...) in one village on one date |
| **As-of date** | The date the figures are "as of" (30 June 2026 for the demonstration data) |
| **At risk / off track / on track** | Status of an indicator: on track at 90% or more of target, at risk 70 to 89%, off track below 70% (settings) |
| **Attendance** | Participants counted at each activity; the same person attending twice counts twice. Different from people reached |
| **Coverage** | How much of the data a figure could be worked out from, e.g. "74% of the data" when some activities had no planned date |
| **Data-quality score** | The average of six checks: completeness, validity, consistency, uniqueness, timeliness, accuracy |
| **Derived / worked out** | Calculated by the tool from the activity, register and report files, rather than typed in a monthly report |
| **Disaggregation** | A breakdown, e.g. by sex |
| **Fiscal year / quarter** | July to June. Q1 = July to September, Q2 = October to December, Q3 = January to March, Q4 = April to June |
| **Gap (reported versus records)** | A month or quarter where the monthly report and the records differ by more than 10% and at least 5 |
| **Indicator** | A defined measure of progress, e.g. "Number of farmers trained" (all are drafts for co-design) |
| **MEAL** | Monitoring, evaluation, accountability and learning |
| **Over budget** | Activity spending to date above the project's whole budget (activity costs only, not staff or overheads) |
| **Pending duplicate review** | A person who may be registered twice; they are counted until someone checks |
| **People reached** | Different people (each counted once), not attendance |
| **Pipeline (donor)** | Funding opportunities not yet decided: identified, qualified, concept note, proposal submitted |
| **Pipeline gap** | Draft: the annual budget of projects ending within 12 months minus the weighted pipeline for their theme |
| **Pipeline (data)** | The program that reads the Excel files and prepares the figures (`python src/pipeline.py`) |
| **Pseudonymised** | Names, phones and ID numbers replaced by a coded key that cannot be turned back into the name without the secret salt |
| **Quarantined** | A record set aside, not counted, until its Excel file is corrected (a serious problem, e.g. a required field blank) |
| **Reconciliation** | Comparing the monthly reports with the activity and register records for the same thing |
| **Review queue** | Records that are counted but should be checked by a person (e.g. women + men do not equal the total) |
| **Salt** | A secret random value used to make the coded keys; kept outside the project folder and backed up |
| **SKIPPED** | A sheet the pipeline could not read because a required column was not recognised; none of its rows are used |
| **Source file** | The Excel file a record came from; every figure can be traced back to its file, sheet and row |
| **Synthetic data** | Invented records used to build and test the tool; never ARDE/KUBAHO data |
| **Target incomplete** | Some months in the period have no target; the % is shown for the months that do, without a traffic-light colour |
| **Weighted value** | Amount requested × probability of success: a planning figure, not money expected for certain |
