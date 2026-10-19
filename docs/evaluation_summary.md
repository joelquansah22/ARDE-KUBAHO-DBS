# Evaluation summary

For the team, the supervisors and ARDE/KUBAHO: what the evaluation shows so far on the **five measures of success
defined in our proposal**, what is still waiting for human testing, and what can only be confirmed with real
ARDE/KUBAHO data.

> **No numeric targets.** Our proposal states: *"Targets will be negotiated after the baseline audit; numerical
> improvements are not promised before the data are examined."* This summary therefore **reports results**; it does
> not measure them against promised targets. Every figure here comes from **synthetic data**.

*Status on 19 October 2026 (v1.2: v1.0 plus donor entry, data entry and upload, and the visual design).*

| Proposal measure | What the proposal measures | How the proposal assesses it | Status |
|---|---|---|---|
| 1. Data quality | Completeness, duplicates, invalid values | Before/after comparison on the same pilot records | Measured on synthetic records; pilot records pending |
| 2. Reporting efficiency | Minutes to produce a selected report | Timed baseline versus prototype workflow | Protocol ready; human timing pending (machine time measured) |
| 3. MEAL readiness | Share of pilot indicators with full definitions | Indicator catalogue audit | Measured: 100% filled in, 0% agreed yet |
| 4. Usability | Task completion and staff feedback | Small user acceptance test | Protocol ready; test pending |
| 5. Sustainability | Reproducible refresh and documentation | Handover walkthrough | Documentation and refresh ready; walkthrough pending |

---

## 1. Data quality

**Proposal:** completeness, duplicates and invalid values, assessed as a before/after comparison on the same pilot
records.

**Result on synthetic records** (`src/evaluate.py`, `docs/evaluation_before_after.md`): the same rows compared as
typed in the files and after the pipeline.

| Main synthetic set | Raw files | After cleaning |
|---|---|---|
| **Completeness:** required fields usable, activities / registrations / reports | 98.7% / 99.4% / 100% | 97.4% / 99.4% / 100% |
| **Duplicates:** activity rows typed twice | 1.4% | 0.0% |
| **Duplicates:** people counted more than once (against the true number) | 4.4% | 0.6% |
| **Invalid values:** cells not in a standard form, activities | 17.8% | 1.5% |
| **Invalid values:** registrations | 18.6% | 0.3% |
| **Invalid values:** indicator reports | 10.2% | 0.1% |

The final held-out set shows the same pattern. Completeness falls slightly after cleaning because an unreadable value
is set aside, not guessed.

**How far to trust the cleaner on new files: two held-out rounds, read together**

| Round | What it tests | Genuine errors fixed or flagged |
|---|---|---|
| **Held-out 2** (first score, frozen v2) | Kinds of mess the cleaner had **never seen**: new date styles, district variants, initials and extra names in duplicates, a partly unreadable layout | **92.9%** |
| **Final round** (Phase 7, frozen) | The **same kinds of mess as held-out 2**, on **fresh data**, after the cleaner had been fixed against them | **98.1%** |

- **Held-out 2 (92.9%) measures robustness to new kinds of mess.** It is the figure to expect when real files bring
  problems nobody has seen.
- **The final round (98.1%) shows the fixes generalise to new records.** It does **not** show that they cover new
  kinds of mess.
- **Report both figures together;** neither stands alone. Both rounds made 0 false corrections, and duplicate merges
  were always correct (precision 1.0).

**Reconciliation of reports against records** (final round): 29 of the 30 planted discrepancies of at least 5 people
are caught (96.7%), with 0 unexplained false alarms. Discrepancies under 5 people are not detected (a known
limitation).

**Still to do with real data:** the same before/after on the **pilot records** once ARDE/KUBAHO shares them (see
`docs/real_data_checklist.md`).

## 2. Reporting efficiency

**Proposal:** minutes to produce a selected report, assessed by timing the baseline against the prototype workflow.

**Measured:** the machine part only. The donor report is generated in a median of 0.15 s
(`evaluation/report_generation_log.csv`). On 15 October all dashboard pages loaded in under 3 s; on 19 October the laptop was short of memory and the
browser times were not representative (the earlier version was equally slow): re-measure with other programs
closed (`docs/screenshots/page_load_times.md`).

**Pending:** the timed task with people. The same quarterly report is made by hand from the raw files and with the
dashboard button, and both are timed step by step, including the human steps. Errors are counted against the
reference answers. Everything is ready in `docs/evaluation_protocol.md` and `evaluation/`. The real baseline needs
ARDE/KUBAHO staff and their current way of reporting.

## 3. MEAL readiness

**Proposal:** share of pilot indicators with full definitions, assessed by an indicator catalogue audit.

**Measured** (`docs/indicator_catalogue_audit.md`, calculated from `config/indicator_catalogue.yaml`). A full
definition has all 15 fields of the brief: code, name, definition, level, unit, numerator, denominator, calculation
rule, disaggregation, target-setting rule, frequency, data source, owner, direction and notes.

| Result | Indicators | Share |
|---|---|---|
| All 15 definition fields filled in | 13 of 13 | **100%** |
| Fully agreed with ARDE/KUBAHO (no field still "to be confirmed", status no longer draft) | 0 of 13 | **0%** |
| Can be calculated from the data now | 11 of 13 | 85% |

Every indicator has its owner still "to be confirmed", and 7 have a target-setting rule still to agree. The pilot
programme is not chosen yet, so all 13 are audited. The co-design session with ARDE/KUBAHO staff is what moves the
second figure.

## 4. Usability

**Proposal:** task completion and staff feedback, assessed by a small user acceptance test.

**Measured (automated, no people):**
- Every page runs under many filter combinations.
- Statuses always show a symbol and words.
- The Executive summary fits 1366 × 768.
- Every page has "How to read this page".
- An empty selection gives a plain message.
- 54 consistency tests confirm the same figure on every page.
- **Donor entry page (automated checks, not user testing):** every entry rule is enforced (required fields,
  probability 0 to 100%, future deadline, awarded amount, next-action date); individual donors cannot be named, even
  writing to the database directly; every change is in the change history with who and when; dated backups after
  every save, keeping the newest 30; restore puts a backup back and can be undone; the Excel backup holds every
  table; the one-time tracker import keeps IDs, lineage, donor keys and "Individual donor #NNN" labels, the pipeline
  then counts each opportunity once, and on the demonstration data the donor figures were identical before and after
  the import (30 opportunities, RWF 2.45bn weighted, 13 overdue actions).
- **Data entry and uploads (automated checks, not user testing, v1.2):** activity records and monthly reports
  typed in are checked with the cleaner's own rules (women + men = total, no negatives, dates in the project and not
  in the future, valid codes, the sex rule) and refused in plain words; a report already in Excel is refused with
  its file and row; changes are recorded and validated; the pipeline reads the entries with lineage and flags
  repeats of Excel records; an upload check gives the same counts as the pipeline, lists held-back rows with their
  row numbers, warns about a repeated file or repeated records, and a replaced file is kept; the Records page shows
  every record's origin and no personal data column.
- **Visual design (automated):** every colour pair in use passes WCAG AA contrast; status colours unchanged; the
  synthetic-data banner byte-for-byte unchanged; pages loaded in under 3 s after the redesign (15 October); on 19 October the laptop was short of memory and the browser times were not representative (see the load-times note).

**Pending:** the acceptance test with 3 to 5 participants: 8 tasks across the executive director, programme manager
and MEAL officer roles, plus the System Usability Scale and closing questions for feedback (`docs/evaluation_protocol.md`).
The participant type (ARDE/KUBAHO staff or student role-play) is recorded and reported separately; student results do
not stand in for staff feedback. The Donor entry, Data entry and Upload Excel pages are not yet in the task list: add
two tasks (upload a filled template and correct a held-back row; record a new opportunity and update its stage) when
the test is run.

## 5. Sustainability

**Proposal:** reproducible refresh and documentation, assessed by a handover walkthrough.

**Ready:**
- **Refresh:** one command (`python src/pipeline.py`), or one double-click on a fresh copy. The synthetic data is
  reproducible to a documented fingerprint.
- **Tests:** 435 automatic tests.
- **Donor data:** one home (the Donor entry page), with automatic backups, an Excel backup and a tested restore.
- **Data entry:** Excel uploads and forms on the dashboard, with the same checks as the pipeline, a record of who
  added what and when, and a Records page that traces every record to its origin.
- **Rules in config:** business rules, layouts, spellings and indicators are kept in plain configuration files.
- **Guides:** README, user guide with glossary, maintenance guide, Power BI guide, privacy note, and the real-data
  checklist.

**Pending:**
- **Fresh-install test** (`docs/fresh_install_test.md`).
- **Handover walkthrough** with the person at ARDE/KUBAHO who will maintain the tool: they rerun the refresh and add a
  file layout using only the guides.
- **Ownership:** who that person is, and on which laptop, is to be confirmed with the partner.

---

## Limitations (summary; full list in `docs/limitations_and_roadmap.md`)

- **Synthetic data only.** No figure here describes ARDE/KUBAHO.
- **Robustness to new kinds of mess** is 92.9% (held-out 2), not 98.1%.
- **Month-first dates** (`Aug 16, 2023`) are not read until the partner confirms them. They were 296 of the 521 rows
  quarantined in the final round.
- **Duplicates:** nicknames, initials and very different spellings wait for review instead of being merged. In the
  final round 44% were merged automatically and 87% merged or flagged.
- **Small discrepancies:** reconciliation cannot detect a discrepancy of under 5 people.
- **Draft indicators:** all are drafts, and none is agreed yet.
