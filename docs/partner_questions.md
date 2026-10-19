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

## F. Handover

| # | Question | Priority | Ref | Answer |
|---|---|---|---|---|
| F1 | Who at ARDE/KUBAHO will maintain the tool, and on which laptop? | 2 | Brief §15 | |
| F2 | Preferred dashboard tool after handover: Streamlit (as built), Power BI (exports ready), or both? | 2 | Brief §15 | |
| F3 | When can the handover walkthrough take place (the sustainability test: the maintainer refreshes the data and adds a file layout using only the guides)? | 2 | Proposal | |
| F4 | Is the suggested monthly routine (`docs/user_guide.md`, section 6) workable? How many minutes per review-queue row (now assumed 2)? | 3 | D60 | |
| F6 | May the tool use the ARDE/KUBAHO logo, and are the brand colours right (`config/theme.yaml`)? | 3 | D196 | |
| F7 | **Real staff codes and roles** for the Donor entry page. Placeholders now in `config/staff.yaml`: ED01 Executive director, PM01 Programme manager (WASH), PM02 Programme manager (agriculture), MEAL01 MEAL officer, FIN01 Finance officer. Codes, or names? | 2 | D188 | |
| F8 | **KoboToolbox server: global or EU, and where the data is stored.** Which organisational account? May ARDE/KUBAHO's field data (activities and indicator reports, no beneficiary names) be stored on KoboToolbox's servers outside Rwanda (see A5)? | 2 | D191 | |
| F5 | Who would take part in the usability test (3 to 5 people across director, programme manager and MEAL officer roles)? | 2 | D175 | |
