# Project status: ARDE/KUBAHO MEAL and Donor Analytics Prototype

*For the supervisors. Version 1.2, 19 October 2026; feature freeze. Everything runs on **synthetic data**: no
ARDE/KUBAHO data has been received.*

## What was built

A free tool for one laptop that reads ARDE/KUBAHO's Excel (and paper-typed) files as they are, removes names, phones
and ID numbers at the first step, cleans and checks the records, and shows the results:

- **Pipeline** (one command): reading messy layouts through configuration, cleaning (dates, district spellings,
  Kinyarwanda codes, duplicates), 14 data-quality rules with a quarantine and a review queue, a star-schema warehouse
  with every figure traceable to its file, sheet and row, exports for Power BI.
- **MEAL indicators:** 13 draft indicators (all fields defined), reported values compared with the activity and
  register records.
- **Dashboard** (11 pages, menu grouped as Insights, Data and Donors): a **Home** page (key figures, what needs attention, a tile for every page), an executive summary answering the director's three questions, programme overview,
  indicators, geography, data quality, donor pipeline, and **donor entry** (donor data recorded directly, with a
  change history, automatic backups and a one-time import of the Excel tracker). One-click quarterly **donor report**
  (Excel and PDF).
- **A database staff can work in (v1.2):** **Upload Excel** (a filled template is checked exactly as the pipeline
  would, with rows accepted, held back with row numbers and reasons, and sent for review, plus warnings about repeated
  files or records, before it is added with who and when); **Data entry** forms for activity records and monthly
  indicator reports, checked with the cleaner's rules; and a read-only **Records** page to search every stored record,
  see where it came from, and export it to Excel. KoboToolbox was removed (it stays in the v1.1 tag).
- **Documentation for NGO staff** (user and maintenance guides, privacy note, Power BI guide, real-data
  checklist, data request pack) and **445 automated tests**. Every team instruction is in `docs/instruction_log.md`;
  every decision in `docs/decision_log.md`.

## Evaluation results so far

The proposal sets no numeric targets ("targets will be negotiated after the baseline audit"), so these are results,
not scores against targets. Full detail: `docs/evaluation_summary.md`.

| Measure (proposal) | Result on synthetic data |
|---|---|
| Data quality (before/after, same records) | Cells not in a standard form: activities 17.8% to 1.5%, registrations 18.6% to 0.3%; people counted twice 4.4% to 0.6% |
| Cleaning on unseen files | **Held-out 2: 92.9%** of genuine errors fixed or flagged. It used kinds of mess the cleaner had never seen, so this is the measure of robustness to new mess. **Final round: 98.1%**, the same kinds of mess on fresh data after the cleaner was fixed against them: the fixes generalise to new records, not to new kinds of mess. Always quoted together. Both: 0 false corrections; every merged duplicate correct |
| Reports versus records | Final round: 29 of 30 planted discrepancies of 5 or more caught, 0 unexplained false alarms |
| MEAL readiness | 13 of 13 indicators fully defined (100%); 0 of 13 agreed with ARDE/KUBAHO yet |
| Reporting efficiency | Donor report generated in about 0.15 s (machine time only); pages loaded in under 3 s on 15 October; on 19 October the laptop was short of memory and the browser times were not representative (the earlier version was equally slow): to re-measure |

## Waiting on human testing (ready to run)

| Test | Status | Materials |
|---|---|---|
| Timed reporting task: the quarterly report by hand from raw files versus the dashboard button | Not run | `docs/evaluation_protocol.md`, recording sheet and reference answers in `evaluation/` |
| Usability test: 3 to 5 participants, 8 tasks across the three roles, SUS questionnaire | Not run; university approval for testing with staff to be confirmed | Same, with consent note and SUS scoring script |
| Fresh install on another Windows laptop using only the README | Not run | `docs/fresh_install_test.md` |
| Handover walkthrough with ARDE/KUBAHO's maintainer | Not run; maintainer not yet named | Maintenance guide |

## Open partner questions that block the real-data switch

From `docs/partner_questions.md` (priority 1, plus those needed before handover):

1. **Data access and law:** may the team see any real data, and on what terms (data-sharing agreement, legal basis
   for processing, registration with the National Cyber Security Authority under Law No. 058/2021)? The preferred
   route is that ARDE/KUBAHO runs the tool itself (A1 to A6).
2. **Pilot and files:** which programme is the pilot, which files exist, and the project list (budgets, activities,
   villages, officers) for the programme master (B1 to B4).
3. **How staff write the data:** month-first dates such as "Mar 12, 2024", and the Kinyarwanda column names and
   codes in use (C1, C2).
4. **Indicators:** the co-design session to agree definitions, owners and targets (D1).
5. **Before handover:** real staff codes
   for the entry pages (F7); permission to use the logo and brand colours (F6); who maintains the tool, and on which
   laptop (F1).

Known limitations (35) and the roadmap are in `docs/limitations_and_roadmap.md`. The steps for switching to real
data are in `docs/real_data_checklist.md`.
