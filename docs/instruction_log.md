# Instruction log

Every instruction message from the team, saved word for word and dated, BEFORE the work on it starts (team instruction, 15 October 2026).

> **Note:** some earlier instructions may have been lost to context limits. Entries 1 to 9 were recovered on 15 October 2026 from the saved Claude Code session transcript (`d4dc3c5e...jsonl`); they are the complete text of the messages found there. The original kick-off prompt (CLAUDE.md Section 12) and anything sent in an earlier session are not in that transcript. The decision log (`docs/decision_log.md`) records what was done with each instruction.

## 1. 14 October 2026, 11:28 UTC (recovered from the transcript)

```text
Answers to your questions:

1. Setup: I have moved the project to a folder outside OneDrive. Copy the brief to CLAUDE.md and build directly in this folder. Yes, run git init. Commit at the end of each phase with a clear message.

2. OneDrive: resolved by the move. Still keep the salt outside the repo and keep data/ outputs in .gitignore.

3. Libraries: approved: PyYAML, pyarrow, rapidfuzz, fpdf2. Do not use kaleido. If the PDF report needs charts, use matplotlib to make static images. Add each one to requirements.txt with a pinned version and log it in the decision log.

4. Traceability: yes, add source_file and source_row to all fact tables.

5. Timeliness and on-time indicator: approved. Add entry_date, planned_date and status (planned, completed, delayed, cancelled) to fact_activity, and generate them in the synthetic data. Inject some late entries and late activities so the rules have something to catch.

6. Duplicates: approved. Do fuzzy matching in ingest.py before hashing and store only the hashed cluster ID. Log the matching threshold in config so we can tune it.

7. Individual donors: approved. Pseudonymise them as "Individual donor #NNN".

8. Sex coded as 1: approved. Treat it as unmapped and flag it for review. Make the mapping configurable.

Your listed assumptions are all accepted: fictional donor names, FY July 2023 to June 2026, stub indicator catalogue in Phase 1, the extra folders and docs, the greyed-out sex filter, and geoBoundaries GeoJSON subject to a licence check in Phase 5.

Your Phase 1 plan is approved, including the ground-truth answer key. Go ahead with Phase 1. Stop when it's done and report back as planned.
```

## 2. 14 October 2026, 12:05 UTC (recovered from the transcript)

```text
Phase 1 approved. Answers:

1. source_sheet: yes, add it to the lineage columns on all fact tables.

2. Phase 2 scoring: exclude the 5 undetectable problems, but do not report one headline percentage. Report:
   a. Fixed / flagged / missed by error type, as a table.
   b. Separate totals for "officer habits" (consistent formatting conventions) and "genuine errors" (duplicates, sum mismatches, negatives, outliers, typos, missing values, late entries).
   c. False corrections: compare every cleaned cell against the ground truth, not only injected cells. Count clean values the pipeline wrongly changed. This must be close to zero.
   d. For duplicates: precision and recall at the configured threshold (88), plus what happens at 80, 85 and 92, so we can justify the threshold.
   The 95% target applies to genuine errors on their own, not just the combined total. If any error type is below 90%, flag it.

3. Synthetic data: keep data/ gitignored. Add a check that confirms a regenerated dataset matches the expected one (e.g. a checksum in the docs), so teammates know their copy is identical.

4. Partner items: keep 7 days for on-time and 30 days for late entry as configurable defaults, marked "to be confirmed" in the decision log.

Go ahead with Phase 2 as written in CLAUDE.md, with the scoring above. Stop when it's done and report back.
```

## 3. 14 October 2026, 13:28 UTC (recovered from the transcript)

```text
Phase 2 approved, with changes before Phase 3.

1. Undetectable cases: accepted (19). Record them in the scorecard as a known limitation. Add a recommendation to the decision log: the paper activity form should gain a "planned date" field.

2. Generator changes D52 to D55: confirm in the decision log that each one fixed a generator bug (an error that was logged but not actually present, or the reverse), and that none of them removed a real error the cleaner was missing. Rerun the scorecard and confirm the numbers.

3. Held-out test (do this before Phase 3):
   a. Generate a second dataset with a different seed, saved to data/holdout/. Do not tune the cleaner on it.
   b. Add new mess the cleaner has not seen: a fifth field-officer layout with different column names, district misspellings not in the current variant list, a new date style (e.g. "12 Mar 24"), and duplicate people whose names are spelt differently in harder ways (swapped first and last names, missing letters, nicknames).
   c. Make the duplicates harder to tell apart: some different people with the same name in the same district, and some true duplicates with a missing phone number.
   d. Run the pipeline unchanged on it and add a held-out section to the scorecard with the same tables (a to d). Report it alongside the main results, even if it's lower. Do not fix the cleaner until I have seen the held-out results.
   e. Also create data/holdout/manual/ with a README asking a teammate to drop in hand-made messy files. The scorer should handle these later.

4. Flag severity: use three levels, not two.
   - Critical (row quarantined): impossible values, missing required fields, codes that can't be mapped (including districts).
   - Warning (goes to the human review queue): suspected duplicates below certain-match level, outliers above 3x target, sum mismatches that couldn't be fixed.
   - Info (logged and counted, no human action): dates with unknown day, IDs stored as numbers, on-time not verifiable, late entries. Show these as data-quality metrics on the dashboard (e.g. "timeliness: 89% of records entered within 30 days"), not as rows to review.
   Report the size of the review queue per month under this scheme. It should be small enough for one MEAL officer to clear in about an hour a month. If it isn't, tell me which rule is driving it.

5. IDs stored as numbers: add a template recommendation to the decision log (ID and phone columns formatted as text, which build_templates.py already does). Note that the lost last digit can't be recovered.

6. Template churn: yes, rebuild only when templates.yaml changes.

When 1 to 6 are done, report back with the held-out results and the review queue size. Don't start Phase 3 until I reply.
```

## 4. 14 October 2026, 15:39 UTC (recovered from the transcript)

```text
Good work. Decisions:

1. Freeze the current results. Save the scorecard as docs/phase2_scorecard_v1_holdout1.md and record the commit hash. These are the "before" figures for the report. Do not overwrite them.

2. Fix these, using general rules, not fixes tailored to this held-out file:
   a. Unrecognised layout: don't crash and don't guess. Skip the file, log a clear message listing the unrecognised column headers, and carry on with the other files. Report skipped files in the data-quality report.
   b. Header detection: require several known header names to match before a row counts as the header, so a single "No" can't trigger it.
   c. Dates: read "12 Mar 24", "12 March 2024" and similar day-month-year text styles. Keep the parsing rules in config.
   d. Ages: if the reference date can't be read, flag the age as not computable (info level). Never fall back silently to the as-of date.
   e. Duplicates: a name-only match with no phone or ID goes to review, never auto-merge. Nicknames stay a known limitation; no nickname list.
   f. Old district names: add config/district_legacy_map.yaml. Map only clear one-to-one cases, flag the rest for review, and mark the file "to be confirmed with partner".
   g. Totals rows: find out why 12.5% were missed and fix the general rule.

3. Missing target: change it from critical to warning. Keep the row. The indicator shows "no target set" instead of a % achieved.

4. Speed: separate scoring from the production pipeline. pipeline.py runs ingest to export only; scoring runs with a --score flag or its own command. Speed up the village lookups and confirm the output is identical against the scorecard. Target: the production pipeline in under 60 seconds.

5. Re-score on three sets and report them side by side:
   - Main set
   - Held-out 1, run twice: as is (FO05 skipped gracefully), and with an FO05 mapping entry added to config. The second run shows what a maintainer's quick config fix achieves.
   - Held-out 2: a new seed with fresh mess, generated after the fixes and never used for tuning. This is the headline figure.
   Use the same tables as before, plus false corrections and review queue per month.

Report back when done. Don't start Phase 3 until I reply.
```

## 5. 14 October 2026, 20:44 UTC (recovered from the transcript)

```text
Good. We stop tuning the cleaner on synthetic data after this round. Decisions:

1. Partly readable layouts: if any required field for a sheet is unmapped, skip the sheet and print the same SKIPPED message as for unreadable layouts, listing the unmapped required fields and the unrecognised headers. Show skipped sheets prominently in the data-quality report. No silent partial reads.

2. Dates: add 2024.03.12 (year.month.day) to the config list. Leave month-first formats (Mar 12, 2024) out; add them to the partner questions in the decision log.

3. Initials: add a rule that matches initials to full names (J. C. Uwimana vs Jean Claude Uwimana), with surname, district and age checks. These are review-only candidates, never auto-merged. Report the change in review queue size on the main set.

4. Scorer corrections: log both answer-key corrections in the decision log with the evidence (rows checked, what was wrong). Note that they were found after seeing results.

5. Reporting: held-out 2's headline stays 92.9%. In the scorecard, add a short explanation of FO06 and show what fix 1 plus an FO06 config mapping recovers, as you did for FO05. Do not replace the headline with the "without FO06" figure.

6. No new held-out round now. Rerun only the main set and the existing tests to confirm nothing broke. Plan a final held-out round (fresh seed plus any files in data/holdout/manual/) for Phase 7 and note it in the decision log.

Then start Phase 3 as written in CLAUDE.md: validate.py (using the three severity tiers already agreed), the quarantine table, model.py building the star schema in DuckDB with full lineage (source_file, source_sheet, source_row), the auto-generated data dictionary, the CSV/Parquet exports for Power BI, and pipeline.py running ingest to export in one command. Stop when Phase 3 is done and report back.
```

## 6. 14 October 2026, 21:04 UTC (recovered from the transcript)

```text
Phase 3 approved. Changes first:

1. Data model: approved.
   a. Add officer_code to fact_activity and fact_indicator_result where the source has it.
   b. Add quality_flag to fact_activity (worst severity among kept rows: ok / info / warning), matching fact_indicator_result.
   c. Add location_level (district / village) to dim_location. Make sure no aggregation sums across levels, and add a test for it.
   d. Add an optional officer code column to the beneficiary register template, and add "can registers carry an officer code?" to the partner questions.
   Regenerate the data dictionary and exports.

2. Beneficiary count: explain why there are 1,509 people when the truth has 1,500. If the cause is pending review duplicates, store the pending count so the dashboard can show "includes N records pending duplicate review". Log this in the decision log.

3. Metric consistency: timeliness was 88.8% in the info metrics and 86.5% in the data-quality scores. Reconcile them: one definition per metric, held in config and used everywhere (scores, dashboard, report). Do the same check for any other metric that appears in more than one place.

4. Data-quality reporting: keep the six dimension scores, but also store rule-level scores and record counts so the dashboard can show which rule is driving a low score.

Then start Phase 4 (indicators):

a. Fill config/indicator_catalogue.yaml with the 12 indicators in Section 7. Each needs the full fields listed there, marked "Draft, for co-design with ARDE/KUBAHO staff".
b. indicators.py computes each indicator by project, district and period (month, quarter, fiscal year), with target, actual, % achieved and RAG status, using thresholds from config. A missing target shows "no target set", never 0% or 100%.
c. Two calculation sources:
   - Reported: values from indicator reports.
   - Derived: values computed from activity and beneficiary records, where possible (e.g. farmers trained, % women, cost per beneficiary).
   Where both exist, produce a reconciliation table: reported vs derived, difference and % difference, with a configurable tolerance. Flag gaps above the tolerance. This is a key MEAL check.
d. Outcome indicators (handwashing practice, yield increase) need survey data we don't have. Do not invent it. Mark them "data source not yet available" in the catalogue and leave them out of calculations. Note them as a recommendation for ARDE.
e. Coverage: where an indicator can only be computed on part of the data (e.g. on-time completion is verifiable for about 74% of activities), store the coverage % next to the value so the dashboard can show it.
f. Beneficiary counts use unique pseudonymised people, not activity attendance, so the same person isn't counted twice. Document the counting rule for each indicator.
g. Traceability: every indicator value links back to the fact rows that produced it.
h. Generate docs/indicator_reference_sheets.md from the YAML, plus an Excel version (one row per indicator, with a blank "staff comments" column) to use in the co-design session with ARDE staff.
i. Tests for every indicator calculation, the reconciliation, missing targets and the no-double-counting rule.

Stop when Phase 4 is done and report back, including the reconciliation results.
```

## 7. 14 October 2026, 21:35 UTC (recovered from the transcript)

```text
Phase 4 approved, with fixes before Phase 5.

1. Reconciliation: like-for-like comparisons.
   For each indicator with both sources, define in the catalogue exactly what the derived side counts so it matches the reported definition. WASH-01 (people with improved water) should be compared with people-served figures from activity records, not with registered beneficiaries. AGR-01 (farmers trained) compares with unique registered training participants. If no like-for-like derived value is possible, mark the indicator "reported only" and leave it out of the reconciliation.

2. Generator: realistic reconciliation scenario.
   Change generate_synthetic.py so indicator reports come from the same underlying truth as the activity and register data, plus planted discrepancies at known rates: e.g. two officers over-reporting by 15 to 30%, some months under-reported, small rounding differences that should fall within tolerance. Log every planted discrepancy in the ground truth.
   Score the reconciliation: what share of planted discrepancies were flagged, and how many flags were false alarms. Add this to the scorecard.
   Regenerate the main set, record the new fingerprint, rerun the cleaning scorecard and report any change. Leave frozen scorecards v1 and v2 as they are (historical, tied to their commits). Don't regenerate the held-out sets.

3. Targets: no placeholder targets. Derived indicators stay "no target set" until the co-design session.

4. Partly missing targets: keep the "target incomplete" status with no RAG colour, and also show % achieved on the months that have targets, labelled e.g. "partial: 9 of 12 months".

5. Aggregation method: add an aggregation field to every indicator in the catalogue: sum (running totals such as people trained), latest (snapshots such as functional committees), or average/ratio (percentages, cost per person). indicators.py must use it for every quarter and year rollup. WASH-04 defaults to latest until the partner confirms. Add tests for each method.

Then start Phase 5 (dashboard) as in Section 9 of CLAUDE.md, with these additions:

a. Landing page: "Executive summary", answering three questions on one screen, without scrolling at 1366 x 768:
   - Are we on track against our targets this quarter, and where are we off track?
   - Can we trust these numbers? (overall data quality, reconciliation flags, records pending review)
   - What funding deadlines and pipeline gaps are coming up in the next 90 days?
   Each answer links to the detailed page.
b. Keep the five pages from Section 9. Add reconciliation to the Indicators page (reported vs derived, flagged gaps).
c. Show coverage next to any indicator computed on partial data, and show "includes N people pending duplicate review" under beneficiary counts.
d. RAG status must never rely on colour alone: use text labels or icons as well.
e. Synthetic-data banner on every page. British English throughout.
f. Donor report button: one-page quarterly summary per project, Excel and PDF (use matplotlib for any PDF charts). Record how long it takes to generate; this is the timed task.
g. Map: check the geoBoundaries licence and record it in the decision log. Fall back to a ranked bar chart if needed.
h. Every page loads in under 3 seconds on the main set. Cache the queries.
i. When done, use Playwright with the pre-installed Chromium to save a screenshot of each page to docs/screenshots/ for the report.

Stop when Phase 5 is done and report back with the screenshots list and page load times.
```

## 8. 14 October 2026, 22:28 UTC (recovered from the transcript)

```text
I reviewed the Phase 5 screenshots. Add these to Phase 6. Fix the consistency items first, before any polish.

A. Consistency (critical: the dashboard's purpose is trustworthy numbers)
1. "People pending duplicate review" shows 27 (Programme overview), 26 (Geography) and 33 (Data quality) under the same filters. Use one calculation in one place. If figures legitimately differ by scope, say so on the page.
2. People reached is 1,504 on Programme overview, but the Geography districts sum to 1,446. Explain the 58. If they have no district, show an "Unknown district" row.
3. Weighted pipeline by theme (1,257.8m + 699.4m = 1,957.2m) exceeds the total (1,438.4m). Find the double counting and fix it. Every theme breakdown must sum to its total.
4. Reconciliation cards: 69 + 137 does not equal 223. Add a card for the remainder (reported only / records only).
5. "Different people reached in the month" rises steadily from 0 to 300. Check whether it is cumulative. If so, either fix it or relabel it.
6. Donor pipeline "Current project budgets" and the Executive summary's "projects ending within 12 months" show the same figures. Check which is right and label them consistently.
7. Add a test suite that checks cross-page consistency: every total shown on more than one page matches, and every breakdown sums to its total, under several filter combinations.

B. Clarity
8. Executive summary: use indicator names, not codes, in the off-track list. Label the counts, e.g. "9 of 17 indicator results on track".
9. Indicators table: one row per indicator, with a column comparing against records (e.g. "Records show 247 (6% lower)"). No truncated columns at 1366 px; wrap text or shorten the labels.
10. Drill-down charts: mark values that are in the review queue with a distinct marker and a note.
11. Reconciliation: flag a gap only if it is above 10% AND above a minimum absolute difference (default 5, in config). Describe differences in words ("reported 18 more than records") instead of signed numbers.
12. Donor pipeline: replace the funnel with a bar chart of open stages (count and value). Show Awarded and Declined separately as outcomes.
13. Programme overview target vs actual: when targets are incomplete, show the partial target for the months that have one, labelled, instead of no target bar.
14. Data quality page: no raw column or rule names in tables (rows_quarantined, missing_required, source_file, entity, etc.). Use plain headers.
15. Axis labels: "Number of people", not "number". Fix the clipped x-axis date labels.

After the budget recalibration, check that cost per beneficiary is now plausible and report the value.

Retake screenshots at the end and report the results of the consistency tests.
```

## 9. 14 October 2026, 23:01 UTC (recovered from the transcript)

```text
Good work on the consistency fixes. Decisions:

1. Reconciliation level: make the comparison level configurable per indicator in the catalogue (e.g. district-month total, district-quarter total). For AGR-01, compare district totals without the sex breakdown. If monthly numbers are still mostly under the minimum, compare quarterly. Keep the 10% AND minimum-difference rule (minimum 5, in config), applied at the comparison level. Keep sex-split figures visible for information, but don't flag them.
   Rescore and report: planted discrepancies caught at the new level, false alarms, and how many planted discrepancies are too small to detect at any level (list them as a known limitation).
   Log this in the decision log as a change made after seeing results, next to D153. Add reconciliation to the Phase 7 final held-out round so this rule is tested on unseen data.

2. Cost per beneficiary (CC-03): do not enlarge the register. Redefine it as cost divided by people reached as reported in indicator reports, by programme, with the definition shown on the dashboard and marked "Draft, for co-design". If a programme has no reported reach, show "not available" instead of a figure. Optionally keep cost per registered participant for training activities only (AGR-01), clearly labelled. Report the new values.

3. Pipeline gap: confirm it uses the annualised budget (budget divided by project length in years) as agreed in the Phase 5 decisions. If not, fix it. It stays labelled as a draft definition and remains on the partner questions list.

Then finish Phase 6: the busy-programme-manager review of the whole dashboard and the donor Excel template. Report the changes from the user reviews (executive director, programme manager, MEAL officer) as a list. Retake screenshots and stop.
```

## 10. 15 October 2026, 12:49 UTC (saved before acting on it)

```text
Phase 6 approved. Before Phase 7:

1. Instruction log: create docs/instruction_log.md. From now on, save each of my instruction messages there verbatim, dated, before acting on it. Add a short note at the top that some earlier instructions may have been lost to context limits.

2. Check these items from my Phase 5 decisions message. Report each as done / not done, and do any not done:
   a. One project deliberately over budget by about 10%, with "over budget by RWF X (Y%)" shown with a warning status, and a test. (Currently every project is at 55 to 82%, so this looks missed. Regenerate, record the new fingerprint, rerun the scorecards.)
   b. Scorecard: reconciliation flags reported as planted discrepancies caught / genuine data errors caught / unexplained false alarms.
   c. Scorecard: one section listing every answer-key correction or scoring change made after seeing results, one line each (D90, D91, D136, D153, D162 and any others).
   d. Phase 6 items: "Data last updated" with source files on every page; plain messages for empty filter results; a friendly message if the pipeline hasn't been run; a collapsed "How to read this page" section on each page; A4 landscape printing; a glossary in the user guide.

Then start Phase 7 (evaluation and documentation) as in CLAUDE.md, plus:

A. Final held-out round: a fresh seed with the reconciliation scenario switched on (D167), plus any files in data/holdout/manual/. Run the current pipeline unchanged. Report the cleaning, duplicate and reconciliation results next to the earlier rounds. No fixes after seeing these results; any weaknesses go in as limitations.

B. Before/after comparison (evaluate.py): raw versus cleaned data-quality measures on the same records, for the main set and the final held-out set.

C. Evaluation summary: docs/evaluation_summary.md, mapping results to the five measures of success in our proposal (data quality, reporting efficiency, MEAL readiness, usability, sustainability). Show what is measured, what is still pending human testing, and what can only be confirmed with real ARDE data.

D. Timed reporting task: write the protocol for the manual baseline. A person produces the same quarterly donor report by hand from the raw messy Excel files, versus with the dashboard button. Provide the recording sheet. The prototype side already logs generation time; the protocol must also time the human steps (opening the dashboard, choosing filters, checking the report).

E. Usability test: a protocol for 3 to 5 participants with 6 to 8 tasks based on the three user roles, the SUS questionnaire, a consent note, and a results template with a script that calculates SUS scores. Participants may be ARDE staff or students role-playing ARDE staff; the template must record which.

F. Fresh-install test: write a checklist for a teammate to set up the project on a different Windows laptop using only the README, timing each step and noting every point where they got stuck. Fix the README based on the result later.

G. Load times: re-measure on a quiet laptop (close other programs and say so in the file). Report cold and warm times.

H. Documentation: README, user guide (with glossary), maintenance guide (how to add a new file layout, a new indicator, a new district spelling; how to rerun; how to read the SKIPPED message), Power BI guide, privacy and governance note.

Stop when Phase 7 is done. Report the final held-out results, the checklist status for item 2, and what is waiting on human testing.
```

## 11. 15 October 2026, 13:49 UTC (saved before acting on it)

```text
Phase 7 approved. Before Phase 8:

1. Evaluation summary: our proposal sets no numeric targets. It says: "Targets will be negotiated after the baseline audit; numerical improvements are not promised before the data are examined." Use these five measures exactly as the proposal defines them:
   - Data quality: completeness, duplicates, invalid values. Assessed as a before/after comparison on the same pilot records.
   - Reporting efficiency: minutes to produce a selected report. Assessed as timed baseline vs prototype workflow.
   - MEAL readiness: share of pilot indicators with full definitions. Assessed by an indicator catalogue audit. Calculate this from the catalogue (fields complete per indicator) and report it.
   - Usability: task completion and staff feedback. Assessed by a small user acceptance test.
   - Sustainability: reproducible refresh and documentation. Assessed by a handover walkthrough.
   Add the proposal's statement about targets to the summary, so it's clear we are reporting results rather than measuring against promised targets.

2. Held-out reporting: in the evaluation summary and scorecard, explain the rounds clearly:
   - Held-out 2 (92.9%) tested kinds of mess the cleaner had never seen. This is the measure of robustness to new mess.
   - The final round (98.1%) used the same kinds of mess as held-out 2 on fresh data, after the cleaner had been fixed against them. This shows the fixes generalise to new records, not to new kinds of mess.
   Report both. Do not present 98.1% alone.

Then Phase 8 (real-data switch and handover), as in CLAUDE.md, plus:

A. Real-data switch checklist (docs/real_data_checklist.md): config changes, mapping new column layouts, removing the synthetic banner and the SYNTHETIC_ prefix checks, generating a new salt, and confirming no synthetic files remain. Include a "first real run" procedure: work on a copy of ARDE's files; compare record counts and key totals against ARDE's own figures; review every SKIPPED message and the quarantine list with the MEAL officer before trusting any dashboard figure.

B. Data request pack for ARDE (docs/data_request_pack.md): which files we need for the pilot, the minimum fields, the time period, and how files should be transferred and stored securely. Add a short list of points for a data-sharing agreement, in line with Law No. 058/2021 (purpose, access, storage, retention, deletion). Mark these "to be confirmed with ARDE and the university".

C. Partner questions: collect every open partner question from the decision log into one document (docs/partner_questions.md), grouped by topic and ordered by priority, ready for a meeting.

D. Limitations and roadmap (docs/limitations_and_roadmap.md): all known limitations in one place, then a prioritised roadmap (now / next 3 months / later) with rough effort and who at ARDE would own each item.

E. Demo script (docs/demo_script.md): a 10-minute walkthrough for the final presentation. Follow the three executive-director questions, then show one data problem traced from the dashboard back to its source Excel row. Include what to say if a supervisor asks about synthetic data or the evaluation rounds.

F. Final repository review: remove dead code and unused files, check every doc link works, run the full test suite, and tag the release v1.0.

Stop when Phase 8 is done and report back.
```

## 12. 15 October 2026, 14:08 UTC (saved before acting on it; two pasted parts in one message)

```text
Scope extension (agreed with supervisors): add data entry so staff can record data, not only view it.

1. Donor tracking forms in the dashboard:
   - Add a new donor and a new opportunity; edit stage, amounts, probability, deadline, next action and owner; mark next actions as done.
   - Save to a separate SQLite file (data/app/entries.db) with a change history: who changed what and when, using a simple staff name picker (no login system).
   - The pipeline reads these entries the same way it reads the donor Excel tracker; both sources must work.
   - Validation on entry (required fields, probability 0 to 100%, deadlines in the future when created).
   - Individual donors stay pseudonymised.

2. Field data collection with KoboToolbox:
   - Design XLSForm files (forms/) for activity monitoring and indicator reporting, based on our templates: dropdowns for districts, activity types and officer codes; date pickers; constraints (female + male = total, no negative values).
   - Add an import adapter: the pipeline reads Kobo XLSX exports as another source layout, using config mappings.
   - Generate synthetic Kobo exports to test the import, then add them to the scorecard.
   - Write docs/kobo_guide.md: how ARDE creates a free account, uploads the forms, installs KoboCollect on phones and exports data.

3. Beneficiary registration stays in Excel/Kobo. Do not store names, phones or IDs in the app database.

4. Update the decision log, user guide and tests. Stop and report back before starting anything else.

5. Visual design: the dashboard looks too plain. Give it ARDE/KUBAHO's look.
   a. Brand colours: take the palette from assets/arde_logo.png (extract the main colours and report the hex codes to me). If the file is missing, fetch the logo from https://arde-kubahorwanda.org/ instead. Store all colours in config/theme.yaml so they can be swapped without touching code. Add an "ARDE/KUBAHO brand colours, to be confirmed with partner" note to the decision log.
   b. Apply the theme through .streamlit/config.toml and a small custom CSS file: the brand primary colour for the sidebar, headings, buttons and active menu item; a light tint of it for page backgrounds and cards. Keep text dark on light backgrounds for readability.
   c. Logo at the top of the sidebar, with the organisation name. Only if the file exists; no logo otherwise.
   d. KPI cards: coloured top border or icon in the brand colour, larger numbers, a small trend arrow or sparkline where there is a time series.
   e. Charts: one consistent palette from the brand colours for categories. Status colours stay separate and fixed (green on track, amber at risk, red off track, grey no target), always with the symbol and word as now. Check every colour pair for contrast (WCAG AA) and report any that fail.
   f. Page headers: a coloured band with the page title and a one-line description of what the page answers.
   g. Keep the yellow synthetic-data banner exactly as it is. It must stay the most visible element on every page.
   h. Do not slow the pages down. Re-measure load times and retake the screenshots afterwards.
```

## 13. 15 October 2026, 15:14 UTC (saved before acting on it; two pasted parts: the follow-ups, then a copy of entry 11)

```text
Scope extension approved. Follow-ups:

1. Backup: entries.db is now the only copy of donor entries. Add an automatic backup: on every save, and on every dashboard start, keep dated copies in data/app/backups/ (keep the last 30). Add a "Download backup" button on the Donor entry page that exports all donor tables and the change history to one Excel file. Add a restore procedure to the maintenance guide and test it.

2. One home for donor data: make the app the single home. Add a one-time "Import from Excel tracker" step (with a preview and confirmation) that moves existing opportunities into entries.db, keeping their IDs and lineage. After import, the pipeline stops reading the Excel tracker for those records and the dashboard says so. Keep the donor Excel template only as a fallback for offline use, documented as such.

3. Limitations: add to docs/limitations_and_roadmap.md:
   - No login: anyone can pick any staff name; the change history records who people say they are. Real user accounts are needed before multi-user use.
   - Single laptop: entries.db is not shared over a network; one person enters at a time.
   - Kobo forms are unchecked on a real account and phone until our team tests them.

4. pyxform: add it to requirements-dev.txt and validate the Kobo forms in the tests.

5. Kobo server and staff codes: add both to docs/partner_questions.md (global vs EU server and where data is stored; real staff codes and roles). Keep the current placeholders.

6. Check docs/instruction_log.md: has my Phase 8 message been received? If not, say so; I'll send it next.

Do 1 to 6, then stop and report back.

Phase 7 approved. Before Phase 8:

1. Evaluation summary: our proposal sets no numeric targets. It says: "Targets will be negotiated after the baseline audit; numerical improvements are not promised before the data are examined." Use these five measures exactly as the proposal defines them:
   - Data quality: completeness, duplicates, invalid values. Assessed as a before/after comparison on the same pilot records.
   - Reporting efficiency: minutes to produce a selected report. Assessed as timed baseline vs prototype workflow.
   - MEAL readiness: share of pilot indicators with full definitions. Assessed by an indicator catalogue audit. Calculate this from the catalogue (fields complete per indicator) and report it.
   - Usability: task completion and staff feedback. Assessed by a small user acceptance test.
   - Sustainability: reproducible refresh and documentation. Assessed by a handover walkthrough.
   Add the proposal's statement about targets to the summary, so it's clear we are reporting results rather than measuring against promised targets.

2. Held-out reporting: in the evaluation summary and scorecard, explain the rounds clearly:
   - Held-out 2 (92.9%) tested kinds of mess the cleaner had never seen. This is the measure of robustness to new mess.
   - The final round (98.1%) used the same kinds of mess as held-out 2 on fresh data, after the cleaner had been fixed against them. This shows the fixes generalise to new records, not to new kinds of mess.
   Report both. Do not present 98.1% alone.

Then Phase 8 (real-data switch and handover), as in CLAUDE.md, plus:

A. Real-data switch checklist (docs/real_data_checklist.md): config changes, mapping new column layouts, removing the synthetic banner and the SYNTHETIC_ prefix checks, generating a new salt, and confirming no synthetic files remain. Include a "first real run" procedure: work on a copy of ARDE's files; compare record counts and key totals against ARDE's own figures; review every SKIPPED message and the quarantine list with the MEAL officer before trusting any dashboard figure.

B. Data request pack for ARDE (docs/data_request_pack.md): which files we need for the pilot, the minimum fields, the time period, and how files should be transferred and stored securely. Add a short list of points for a data-sharing agreement, in line with Law No. 058/2021 (purpose, access, storage, retention, deletion). Mark these "to be confirmed with ARDE and the university".

C. Partner questions: collect every open partner question from the decision log into one document (docs/partner_questions.md), grouped by topic and ordered by priority, ready for a meeting.

D. Limitations and roadmap (docs/limitations_and_roadmap.md): all known limitations in one place, then a prioritised roadmap (now / next 3 months / later) with rough effort and who at ARDE would own each item.

E. Demo script (docs/demo_script.md): a 10-minute walkthrough for the final presentation. Follow the three executive-director questions, then show one data problem traced from the dashboard back to its source Excel row. Include what to say if a supervisor asks about synthetic data or the evaluation rounds.

F. Final repository review: remove dead code and unused files, check every doc link works, run the full test suite, and tag the release v1.0.

Stop when Phase 8 is done and report back.
```

## 14. 19 October 2026, 09:51 UTC (saved before acting on it)

```text
Follow-ups approved. Final wrap-up round, then feature freeze:

1. Demo state: run the one-time tracker import on the synthetic demo data. Add a "reset demo" command (python src/reset_demo.py) that regenerates the main set, clears entries.db and its backups, and reruns the pipeline, so the import can be shown live. Document it in the demo script.

2. Bring the Phase 8 documents up to date with everything added after v1.0:
   - Demo script: add the Donor entry page (add an opportunity, update a stage, show the change history and backup) and one slide's worth on Kobo. Keep the total at 10 minutes.
   - Real-data checklist: entries.db, backups, staff.yaml, the Excel tracker import, the Kobo server choice, and the theme/logo permission.
   - Data request pack and privacy note: Kobo data storage and the donor entries database.
   - Evaluation summary: add the Kobo import results and the donor entry tests, labelled as automated checks, not user testing.
   - Limitations and roadmap: check it is complete after D187 to D205.
   - README and user guide: check every step still matches the app.

3. Full test suite, retake all screenshots, re-measure load times, check every doc link. Tag the release v1.1.

4. Write docs/project_status.md, one page for our supervisors: what was built; the evaluation results so far (held-out 2 and final round, explained as before); what is waiting on human testing (timed task, usability test, fresh install, Kobo phone test); and the open partner questions that block the real-data switch.

After this, no new features unless I ask. Stop and report back.
```

## 15. 19 October 2026, 10:36 UTC (saved before acting on it)

```text
Push the project to a private GitHub repository.

1. Before pushing, confirm: data/ and all its contents are gitignored, no salt file or entries.db is in the repo, no real data exists anywhere in the repo history, and .venv is excluded. Show me the list of files that will be pushed and wait for my confirmation.
2. After I confirm: create a private repository named arde-meal-prototype (if gh is not available or not logged in, give me exact steps to create it on github.com instead), push all commits and the v1.0 and v1.1 tags.
3. Add a short "For teammates" section to the README: how to clone, set up and run the demo.
4. Stop and report the repository URL.
```

## 16. 19 October 2026, 10:49 UTC (saved before acting on it)

```text
Before that do the following:

Lift the feature freeze for one extension. ARDE needs a database staff can work in, not only a dashboard. Data comes in through Excel and the app only. No Kobo.

1. Remove Kobo: remove the Kobo forms, the import adapter, its tests, the Kobo guide and every Kobo mention in the app and docs (demo script, limitations, partner questions, real-data checklist, privacy note, evaluation summary). It stays available in the v1.1 tag. Log this in the decision log.

2. Excel upload page:
   - Staff upload a filled Excel template in the app instead of copying files into data/raw.
   - After upload, show a plain summary: rows accepted, rows held back for correction (with reasons and row numbers), rows sent for review, and any SKIPPED message.
   - Keep each uploaded file with the date and who uploaded it. Warn if the same file, or one with the same records, was already uploaded.
   - Link to download the blank templates from the same page.

3. Records page (read and search):
   - Browse every stored table: activities, indicator results, donors, opportunities, records held back for correction, review queue.
   - Search and filter by project, district, officer, date range, status and source (Excel upload / entered in app).
   - Each record shows where it came from (file, sheet, row, or app entry with who and when).
   - Export the filtered view to Excel.
   - No beneficiary names, phones or IDs anywhere.

4. Entry forms for programme data, saving to entries.db:
   - Activity record: project, activity, district/sector/cell/village (cascading dropdowns), date, planned date, status, female/male/total participants, cost, officer.
   - Monthly indicator report: project, district, month, indicator, target, actual.
   - Reuse the cleaner's rules for validation on entry (female + male = total, no negatives, dates in the project window, valid codes). Show plain error messages.
   - Change history, automatic backups and the backup download, as for donors.
   - Records entered in the app can be edited in the app. Records from Excel are read-only in the app and corrected in the Excel file, then re-uploaded; the page says so.

5. The pipeline reads app entries as another source, with lineage. Warn when an app entry looks like a duplicate of an Excel record (same project, activity, date and place).

6. Tests, decision log, user guide (a short "how to enter this month's data" section covering both upload and forms), demo script (one minute showing an upload and a form entry appearing on the dashboard), limitations (single laptop and no login still apply). Retake screenshots.

7. Tag v1.2, then return to the feature freeze. Stop and report back.
```
