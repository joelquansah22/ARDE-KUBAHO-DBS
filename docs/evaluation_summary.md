# Evaluation summary

For the team, the supervisors and ARDE/KUBAHO: what the evaluation shows so far against the **five measures of
success in our proposal**, what is still waiting for human testing, and what can only be confirmed with real
ARDE/KUBAHO data.

*Status on 15 October 2026 (end of Phase 7). Every figure here comes from **synthetic data**. The proposal's numeric
targets for each measure are to be copied in by the team from the proposal; this summary does not restate them.*

| Measure | Measured now (synthetic data) | Waiting for human testing | Only with real ARDE/KUBAHO data |
|---|---|---|---|
| 1. Data quality | Yes | No | Yes |
| 2. Reporting efficiency | Machine side only | Yes (timed task) | Yes |
| 3. MEAL readiness | Partly | Yes (co-design session) | Yes |
| 4. Usability | Automated checks only | Yes (SUS and tasks) | Staff testing |
| 5. Sustainability | Partly | Yes (fresh-install test) | Handover |

---

## 1. Data quality

**Measured (synthetic):**

- **Before/after on the same records** (`docs/evaluation_before_after.md`, `src/evaluate.py`):

  | Main set | Raw files | After cleaning |
  |---|---|---|
  | Activity records: cells not in a standard form | 17.8% | 1.5% |
  | Registrations: cells not in a standard form | 18.6% | 0.3% |
  | Indicator reports: cells not in a standard form | 10.2% | 0.1% |
  | Activities where women + men differ from the total | 4.8% | 3.1% (all in the review queue) |
  | Activity rows typed twice | 1.4% | 0.0% |
  | People counted more than once (against the true number) | 4.4% | 0.6% |
  | Required fields usable (activities / registrations) | 98.7% / 99.4% | 97.4% / 99.4% |

  The final held-out set shows the same pattern (19.9% to 1.8%, 19.6% to 0.5%, 11.1% to 0.4%; duplicates of people
  3.9% to 2.2%). Completeness falls slightly after cleaning because unreadable values are not guessed.
- **Cleaning accuracy against the answer key** (scorecards):

  | Set | Genuine errors fixed or flagged | False corrections |
  |---|---|---|
  | Held-out 2 (headline, first score) | 92.9% | 0 |
  | Final held-out round (frozen, unseen data) | **98.1%** | **0 of 60,332 cells** |

  - **Duplicate merges are always correct** (precision 1.0). Of the true duplicates, 44% are merged automatically
    and 87% are merged or sent for review.
- **Reconciliation of reports against records** (final round): 29 of the 30 planted discrepancies of at least 5 are
  caught (96.7%), with **0 unexplained false alarms**. 39 planted discrepancies are under 5 people on their own and
  cannot be detected (a known limitation).
- **Data-quality score** on the main set: 96.3% overall. The weakest dimension is timeliness (88.4%).
- **Review queue:** about 8 to 10 records a month on the synthetic sets, about 20 minutes of the MEAL officer's time.
  No month exceeds one hour.

**Only with real data:** the real error rates and kinds of mess, the real review-queue load, and whether the rules
fit ARDE/KUBAHO's files. The synthetic files and the cleaner were written by the same team; the final held-out round
reduces this bias but does not remove it.

## 2. Reporting efficiency

**Measured (synthetic):**

- The donor report is generated in a median of **0.15 s** (slowest 0.35 s; `evaluation/report_generation_log.csv`).
- **Dashboard pages load in 0.86 s or less on the server.** In Chrome on the team laptop, with other programs open,
  the median load times are below 3 s for every page except the first visit to the Programme overview (3.4 s; it also loads the chart library once per session).
  See `docs/screenshots/page_load_times.md`.

**Waiting for human testing:**

- The **timed reporting task**: the same quarterly report made by hand from the raw files versus with the dashboard
  button, timed step by step, with errors counted against reference answers. The protocol, recording sheet and
  reference answers are ready (`docs/evaluation_protocol.md`, `evaluation/`).
- The machine time is not the task time. The human steps (opening the dashboard, choosing the report, checking it)
  are timed in the protocol.

**Only with real data:** how long ARDE/KUBAHO's current reporting really takes, and the monthly cycle from field
files to report.

## 3. MEAL readiness

**Measured:**

- **Indicator catalogue:** 13 draft indicators with full reference sheets (Markdown, and Excel with a staff comments
  column). 11 are calculated; 2 outcome indicators wait for survey data.
- **Traceability:** every value is traceable to its file, sheet and row.
- **Methods:** a declared aggregation for each indicator, partial targets shown honestly, and coverage shown next to
  partial values.
- **Reconciliation:** reports are compared with records at a level set per indicator.
- **Data-quality framework:** the six dimensions, 14 rules, a quarantine and a review queue.

**Waiting for human testing:** the **co-design session** with ARDE/KUBAHO staff. The indicators, their definitions,
the targets, the cost-per-person reach indicators and the pipeline-gap definition are all drafts.

**Only with real data:** whether the indicators can be calculated from what ARDE/KUBAHO actually records, and the
real targets.

## 4. Usability

**Measured (automated, no people):**

- Every page runs with no errors under many filter combinations.
- Statuses always show a symbol and words, never colour alone.
- The Executive summary fits 1366 × 768 without scrolling.
- Every page has "How to read this page", plain messages for empty selections and a download on every table.
- The text is in British English, and pages print on A4 landscape.
- 54 cross-page consistency tests confirm the same figure on every page.

**Waiting for human testing:** the **usability test** with 3 to 5 participants, 8 tasks across the three roles and
the **System Usability Scale**. The protocol, consent note, results templates and scoring script are ready. The
participant type (ARDE/KUBAHO staff or student role-play) is recorded and reported separately.

**Only with ARDE/KUBAHO staff:** usability for the real users. Student role-play results cannot stand in for them.

## 5. Sustainability

**Measured:**

- **Cost and setup:** free and open-source tools only, on one laptop, with no server and no cloud.
- **Configuration:** business rules, file layouts, district spellings, indicators, labels and help texts live in
  plain configuration files.
- **Guides:** written for staff (user guide with glossary, maintenance guide, Power BI guide, privacy note).
- **Automatic checks:** 362 tests (about 4 minutes), plus a first-run script that prepares a fresh copy.

**Waiting for human testing:** the **fresh-install test**. A teammate sets up the tool on another Windows laptop
using only the README, timing each step and noting where they got stuck. The checklist is ready in
`docs/fresh_install_test.md`; the README will be corrected from its results.

**Only at handover:** who at ARDE/KUBAHO maintains the tool, on which laptop, and whether they can rerun the pipeline
and add a file layout unaided.

---

## Limitations to state in the report

- **Synthetic data only.** No figure here describes ARDE/KUBAHO.
- **Duplicates:** nicknames, initials and very different spellings of the same person are not merged automatically.
  They wait for review (final round: 44% of duplicates merged automatically, 87% merged or flagged).
- **Month-first dates** (`Mar 12, 2024`) are not read until the partner confirms whether staff use them. In the final
  round they were the main cause of quarantined rows (296 of 521).
- **Small discrepancies are not flagged:** reconciliation cannot detect a discrepancy of under 5 people (39 of 66
  planted rows in the final round).
- **Unknown file layouts are skipped**, never read partly, until a maintainer adds their column names.
- **Cost per person reached** covers only projects that report a people-reached indicator (1 of 3 WASH projects and
  1 of 2 agriculture projects).
- **Page load times** were measured with other programs open; a quiet-laptop measurement is still to be done.
