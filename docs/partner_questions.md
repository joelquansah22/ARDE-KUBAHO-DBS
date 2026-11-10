# Questions for ARDE/KUBAHO

Every open question from the decision log (`docs/decision_log.md`, "Open items") and the documents, in one place, for
a meeting with ARDE/KUBAHO. Grouped by topic; within each topic, the most urgent first.

**Priority:** **1** = needed before any real data is used · **2** = needed before handover · **3** = can wait.
The reference in brackets is the decision-log entry with the background.

| Meeting | Date | ARDE/KUBAHO | Team |
|---|---|---|---|
| | | | |

---

## A. Data access, privacy and law (all priority 1)

| # | Question | Ref | Answer |
|---|---|---|---|
| A1 | May the student team see any real data at all? If yes, only pseudonymised exports, or the raw files? (We prefer that ARDE/KUBAHO runs the tool itself; see the data request pack) | Brief §15 | |
| A2 | On what legal basis are beneficiaries' data collected (consent at registration, contract, other)? Do the registration forms explain how data will be used? | D180 | |
| A3 | Is ARDE/KUBAHO registered as a data controller with the National Cyber Security Authority, as Law No. 058/2021 requires? | D180 | |
| A4 | Disability is sensitive data: is it collected with consent, and is it needed in the analysis? | D180 | |
| A5 | Where may data be stored? Is any copy kept in a cloud service (OneDrive, Google Drive), possibly outside Rwanda? | D180 | |
| A6 | Who signs a data-sharing agreement for ARDE/KUBAHO (purpose, access, storage, retention, deletion; `docs/data_request_pack.md`, section 4)? | Brief §15 | |
| A7 | Who would notify the authority and the people affected if a laptop or file with personal data were lost? | D180 | |
| A8 | How long are registers kept after a project ends (retention)? | D180 | |
| A9 | Should small counts (for example under 5 people) be hidden in reports shared outside ARDE/KUBAHO? | D180 | |
| A10 | (For ASU) What human-subjects approval is needed to test the tool with ARDE/KUBAHO staff (usability and timed tests)? | D175 | |

## B. Pilot scope and data sources

| # | Question | Priority | Ref | Answer |
|---|---|---|---|---|
| B1 | Which programme is the pilot: WASH or agriculture/climate resilience? | 1 | Brief §15 | |
| B2 | Which files exist for it (activity monitoring, registers, service lists, monthly indicator reports, donor tracking), in what format, and roughly how many records? | 1 | Brief §15 | |
| B3 | In which districts (and sectors) does ARDE/KUBAHO work? | 1 | D18 | |
| B4 | The project list with budgets, dates, activity types, villages and officer codes (to build the programme master) | 1 | `real_data_checklist.md` §5 | |
| B5 | What share of records exists only on paper, and is any digitisation planned? | 2 | Brief §14 | |
| B6 | How are monthly indicator reports scheduled and submitted (who, by when)? | 2 | D25 | |

## C. How staff write the data (for the cleaning rules)

| # | Question | Priority | Ref | Answer |
|---|---|---|---|---|
| C1 | Do staff ever write dates **month first** ("Mar 12, 2024", "Aug 16, 2023")? They are not read until confirmed; in the final test round they were the main cause of quarantined rows | 1 | D69, D173 | |
| C2 | Which Kinyarwanda column names and values are used (e.g. "Gore"/"Gabo" for female/male, "Itariki")? | 1 | D23, D36 | |
| C3 | Which old district names (Butare, Byumba, Kibungo...) do staff still use, and which current district does each mean in their area? | 2 | D72 | |
| C4 | Can registers carry an officer code (an optional column is in the template)? | 2 | D99, D112 | |
| C5 | Can the paper activity form add a **planned date**, so on-time delivery can be checked? | 2 | D56 | |
| C6 | Is the duplicate-matching threshold right? To check on a small hand-labelled sample of real registrations | 2 | D43 | |

## D. Indicators (co-design session)

| # | Question | Priority | Ref | Answer |
|---|---|---|---|---|
| D1 | Agree the indicator list, definitions, owners and targets (`docs/indicator_reference_sheets.xlsx`, with a Staff comments column). All 13 are drafts; none is agreed (`docs/indicator_catalogue_audit.md`) | 1 | D128 | |
| D2 | Where a reported and a worked-out value differ, which is official, and what gap is acceptable (now 10% and at least 5)? | 2 | D128, D162 | |
| D3 | WASH-04: do reports count **new** committees (to be added up) or **all functional** committees (a snapshot)? Treated as a snapshot until confirmed | 2 | D139 | |
| D4 | Cost per person reached: which reported indicators count "people reached" for each programme? Sanitation, hygiene and irrigation projects have none yet | 2 | D163 | |
| D5 | What does "trained" mean for AGR-01: one session, or the full course? | 2 | Catalogue | |
| D6 | "On time" (within 7 days of the plan) and "late entry" (more than 30 days after the activity): are these ARDE/KUBAHO's definitions? | 2 | D10, D11 | |
| D7 | Recommendation: baseline and follow-up surveys for handwashing (WASH-03) and yield (AGR-03), which have no data source yet | 3 | D117 | |

## E. Money and the donor module

| # | Question | Priority | Ref | Answer |
|---|---|---|---|---|
| E1 | Is the donor module part of the assessed scope (and of what ARDE/KUBAHO wants)? | 2 | Brief §15 | |
| E2 | **Pipeline gap** (draft): the annual budget of projects ending within 12 months minus the weighted open pipeline for the theme. Is this useful, and is it the right definition? | 2 | D141, D164 | |
| E3 | Which USD to RWF rate should reports use (now 1,450)? | 2 | Settings | |
| E4 | Do project budgets include staff and overheads? The tool compares **activity costs only** with the whole budget for the over-budget warning | 2 | D168 | |
| E5 | How does ARDE/KUBAHO track funding opportunities today (stages, probability)? | 3 | Brief §5 | |

## G. ARDE/KUBAHO sample workbook (from the November 2026 sample)

The figures and examples behind each question are in `docs/arde_sample_profile.md` (confidential, not in the shared
repository; ask the team lead). Codes are given there, not here.

| # | Question | Priority | Ref | Answer |
|---|---|---|---|---|
| G1 | **Budget used %**: in some projects this column holds what look like amounts, not percentages. What should it hold, and can the values be corrected? Until then they are shown as "invalid, check" and not used. | 1 | D238 | |
| G2 | **Direct beneficiaries**: your Dashboard adds the Projects sheet's Direct Beneficiaries column. Does that column count **people only**? The Beneficiaries sheet also counts households, cooperatives, schools and so on, and its rows do not add up to the Projects figure for every project. Which source is official? | 1 | D237 | |
| G3 | In the Beneficiaries sheet, do the "Women"/"Men" rows **overlap** the "People" rows of the same project (part of them), or are they extra people? | 1 | D235 | |
| G4 | **KPIs not started**: your Data Quality sheet counts only KPIs with no target as "not recorded", while the KPIs sheet calls every KPI at 0% "Not recorded". Which do you mean? We count KPIs "Not started" with nothing achieved. | 2 | D236 | |
| G5 | The KPIs sheet's **Achievement %** is typed in and differs from the working register's in a few rows. Can it become a formula, or be removed, so the register is the only source? | 2 | D232 | |
| G6 | Some projects are **past their end date but still "On track"/"Active"**, and one is "Completed" at partial progress. Please confirm their status. | 2 | D238 | |
| G7 | **Approved budget 0** for some projects (one has activity funds above 0): unknown, or really zero? | 2 | D238 | |
| G8 | Every General Objective has the same **parent result**, which is not a result code. Is it a placeholder (for example a programme or strategy code)? | 3 | D238 | |
| G9 | **Exchange rates** for the RWF estimates: which rates should be used (BNR annual average, the rate on the agreement date, the donor's rate)? We use approximate annual averages for now. | 2 | D234 | |
| G10 | **Activities with funds of 0**: not funded separately, or not yet entered? | 3 | D238 | |
| G11 | Some KPIs are **above 150% of target**: correct, or a target/achieved typo? | 3 | D238 | |
| G12 | Do you keep a list of **funding opportunities** being applied for (deadlines, amounts, stage)? The workbook holds funding received; the Donor pipeline page has nothing to show without it. | 3 | D240 | |
| G13 | **Staff names** in Manager, Personnel and Responsible: may they appear in internal exports (the register download)? The dashboard shows roles only. | 1 | D239 | |
| G14 | Will staff keep editing the workbook, or use the dashboard's **KPI update** form? If both, which one wins when they differ (we use the newest)? | 2 | D241 | |

## F. Handover

| # | Question | Priority | Ref | Answer |
|---|---|---|---|---|
| F1 | Who at ARDE/KUBAHO will maintain the tool, and on which laptop? | 2 | Brief §15 | |
| F2 | Preferred dashboard tool after handover: Streamlit (as built), Power BI (exports ready), or both? | 2 | Brief §15 | |
| F3 | When can the handover walkthrough take place (the sustainability test: the maintainer refreshes the data and adds a file layout using only the guides)? | 2 | Proposal | |
| F4 | Is the suggested monthly routine (`docs/user_guide.md`, section 6) workable? How many minutes per review-queue row (now assumed 2)? | 3 | D60 | |
| F6 | May the tool use the ARDE/KUBAHO logo, and are the brand colours right (`config/theme.yaml`)? | 3 | D196 | |
| F7 | **Real staff codes and roles** for the entry pages (Donor entry, Data entry, Upload Excel). Placeholders now in `config/staff.yaml`: ED01 Executive director, PM01 Programme manager (WASH), PM02 Programme manager (agriculture), MEAL01 MEAL officer, FIN01 Finance officer, FO01 to FO04 field officers. Codes, or names? | 2 | D188, D219 | |
| F8 | **Who enters the month's data on the laptop?** Do field officers come to the laptop to upload their files and type in records, or do they send files (e.g. by email) for the MEAL officer to upload? Who checks the upload summaries and corrects held-back rows? | 2 | D212, D218 | |
| F5 | Who would take part in the usability test (3 to 5 people across director, programme manager and MEAL officer roles)? | 2 | D175 | |
