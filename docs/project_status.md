# Project status: ARDE/KUBAHO MEAL and Donor Analytics Prototype

*For the supervisors. Version 1.1, 19 October 2026; feature freeze. Everything runs on **synthetic data**: no
ARDE/KUBAHO data has been received.*

## What was built

A free tool for one laptop that reads ARDE/KUBAHO's Excel (and paper-typed) files as they are, removes names, phones
and ID numbers at the first step, cleans and checks the records, and shows the results:

- **Pipeline** (one command): reading messy layouts through configuration, cleaning (dates, district spellings,
  Kinyarwanda codes, duplicates), 14 data-quality rules with a quarantine and a review queue, a star-schema warehouse
  with every figure traceable to its file, sheet and row, exports for Power BI.
- **MEAL indicators:** 13 draft indicators (all fields defined), reported values compared with the activity and
  register records.
- **Dashboard** (7 pages): an executive summary answering the director's three questions, programme overview,
  indicators, geography, data quality, donor pipeline, and **donor entry** (donor data recorded directly, with a
  change history, automatic backups and a one-time import of the Excel tracker). One-click quarterly **donor report**
  (Excel and PDF).
- **KoboToolbox** forms for activity and indicator data on phones, read like the Excel files.
- **Documentation for NGO staff** (user and maintenance guides, privacy note, Power BI and Kobo guides, real-data
  checklist, data request pack) and **406 automated tests**. Every team instruction is in `docs/instruction_log.md`;
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
| Kobo import (automated check) | Synthetic exports in both formats read 100% correctly; repeated submissions removed |

## Waiting on human testing (ready to run)

| Test | Status | Materials |
|---|---|---|
| Timed reporting task: the quarterly report by hand from raw files versus the dashboard button | Not run | `docs/evaluation_protocol.md`, recording sheet and reference answers in `evaluation/` |
| Usability test: 3 to 5 participants, 8 tasks across the three roles, SUS questionnaire | Not run; university approval for testing with staff to be confirmed | Same, with consent note and SUS scoring script |
| Fresh install on another Windows laptop using only the README | Not run | `docs/fresh_install_test.md` |
| Kobo forms on a real KoboToolbox account and an Android phone | Not run (forms checked with pyxform only) | `docs/kobo_guide.md` |
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
5. **Before handover:** the KoboToolbox server (global or EU) and where data may be stored (F8); real staff codes
   for donor entry (F7); permission to use the logo and brand colours (F6); who maintains the tool, and on which
   laptop (F1).

Known limitations (35) and the roadmap are in `docs/limitations_and_roadmap.md`. The steps for switching to real
data are in `docs/real_data_checklist.md`.
