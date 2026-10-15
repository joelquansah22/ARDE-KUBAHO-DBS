# Limitations and roadmap

Everything known to be limited about the prototype, in one place, then a prioritised roadmap. Owners are **roles at
ARDE/KUBAHO, suggested by the team and to be confirmed with the partner** (`docs/partner_questions.md`, F1).

---

## 1. Known limitations

### Evidence

| # | Limitation | Where it shows | Ref |
|---|---|---|---|
| L1 | **Synthetic data only.** No figure describes ARDE/KUBAHO; the synthetic files and the cleaner were written by the same team | Everywhere (banner) | Brief §2 |
| L2 | **Robustness to new kinds of mess is 92.9%** (held-out 2). The final round's 98.1% shows the fixes generalise to new records of known kinds of mess, not to new kinds | Scorecards | D173 |
| L3 | **No human evaluation yet:** the timed reporting task, the usability test (SUS), the fresh-install test and the handover walkthrough are prepared but not run | `docs/evaluation_summary.md` | D175 |
| L4 | **Page load times** were measured with other programs open; the Programme overview's first visit took 3.4 s (target 3 s) | `docs/screenshots/page_load_times.md` | D179 |

### Reading and cleaning

| # | Limitation | Ref |
|---|---|---|
| L5 | **Month-first dates** (`Aug 16, 2023`) are not read until staff confirm they use them; such rows are quarantined | D69, D173 |
| L6 | **Unknown layouts are skipped**, never read partly: their records are missing until a maintainer adds the column names | D87 |
| L7 | **Duplicates written with nicknames, initials, hyphens or extra names** are not merged automatically; they go to the review queue. Final round: 44% of true duplicates merged automatically, 87% merged or flagged, 0 wrong merges | D84, D173 |
| L8 | **An ID number stored as a number in Excel** has lost its 16th digit: flagged, but it cannot be recovered | Scorecard |
| L9 | **Old district names** that cover several current districts are never guessed; the village is used if it settles the question, otherwise the row is reviewed | D72 |
| L10 | **19 kinds of injected problem cannot be detected** from the files at all (e.g. a misspelt name with nothing to compare against, "completed late" on paper forms with no planned date) | D54 |
| L11 | **Women + men not equal to the total** is flagged, not corrected (which number is wrong is unknown): 3.1% of used activity rows stay in the review queue | D174 |

### Indicators and reconciliation

| # | Limitation | Ref |
|---|---|---|
| L12 | **All 13 indicators are drafts;** none is agreed (owners and most targets "to be confirmed") | Catalogue audit |
| L13 | **Two outcome indicators** (handwashing WASH-03, yield AGR-03) have no data source: they need surveys | D117 |
| L14 | **Reconciliation cannot detect a discrepancy of under 5 people:** 39 of 66 planted report rows in the final round | D162, D173 |
| L15 | **Cost per person reached** covers only projects that report a people-reached indicator (1 of 3 WASH, 1 of 2 agriculture projects); AGR-01 counts farmers trained only | D163 |
| L16 | **WASH-04** is treated as a snapshot (latest month) until ARDE/KUBAHO says whether it counts new or all functional committees | D139 |
| L17 | **Budgets:** the over-budget warning compares activity costs only with the whole project budget (staff and overheads are not in the files) | D168 |
| L18 | **Pipeline gap** is a draft definition of the team's | D141, D164 |

### Platform and governance

| # | Limitation | Ref |
|---|---|---|
| L19 | **No user logins** and no roles: anyone using the laptop sees everything. Acceptable on one protected laptop; not for a shared server | Brief §14 |
| L20 | **One laptop:** no multi-user editing, no automatic backup of the warehouse (it can always be rebuilt from the Excel files) | D148 |
| L21 | **The salt** must be backed up and never lost; losing it breaks the link between old and new records | Privacy note |
| L22 | **Legal obligations** under Law No. 058/2021 are not yet confirmed with ARDE/KUBAHO or the university | D180 |
| L23 | **A maintainer is needed** to add file layouts and spellings (no programming, but care with YAML files) | Maintenance guide |
| L24 | **Derived indicators** with a new kind of calculation need someone who can write Python | Maintenance guide §6 |
| L25 | **Donor entry has no login:** anyone using the laptop can choose any name; the history records the chosen name | D188 |
| L26 | **Opportunities from the Excel tracker cannot be updated on the dashboard** (only those added there) | D187 |
| L27 | **KoboToolbox forms are not yet deployed or used on a phone;** checked with pyxform only (ODK Validate not run) | D191 |
| L28 | **A Kobo export and an Excel file covering the same activities** would be counted twice | D192 |
| L29 | **Brand colours and logo** not yet confirmed with ARDE/KUBAHO; an opened dropdown in the green sidebar was not checked automatically | D196, D198 |

## 2. Roadmap

Effort: **S** = under a day · **M** = a few days · **L** = a few weeks. "Team" = the student team, before the end of
the capstone; after that, the ARDE/KUBAHO owner (suggested role, to be confirmed).

### Now (before or at handover)

| # | Item | Addresses | Effort | Owner |
|---|---|---|---|---|
| R1 | Partner meeting on the priority-1 questions (`docs/partner_questions.md`): pilot programme, data access, legal basis, date styles | L1, L5, L22 | S | Executive director, with the team |
| R2 | Data-sharing agreement, or decision that ARDE/KUBAHO runs the tool itself | L1, L22 | S to M | Executive director, ASU |
| R3 | Usability test (3 to 5 people), timed reporting task, fresh-install test | L3 | M | Team, with programme manager and MEAL officer |
| R4 | Re-measure load times on a quiet laptop; if the overview is still over 3 s, load the chart library on the first page | L4 | S | Team |
| R5b | Deploy the Kobo forms on a test account and fill them in on one phone; export and run the pipeline | L27 | S | MEAL officer, with the team |
| R5 | Handover walkthrough: the maintainer refreshes the data and adds a file layout using only the guides | L23 | S | MEAL officer (maintainer) |

### Next 3 months (first real data)

| # | Item | Addresses | Effort | Owner |
|---|---|---|---|---|
| R6 | First real run on the pilot (`docs/real_data_checklist.md`): map layouts, review every SKIPPED sheet and the quarantine, compare totals with ARDE/KUBAHO's own figures | L1, L2, L6 | M | MEAL officer |
| R7 | Co-design session: agree indicators, owners, targets, the official source where report and records differ, WASH-04, cost per person, pipeline gap | L12, L15, L16, L18 | M | Programme managers, MEAL officer |
| R8 | Add the date styles and district names staff really use (configuration only), after confirming them | L5, L9 | S | MEAL officer |
| R9 | Check the duplicate-matching threshold on a small hand-labelled sample of real registrations; agree how the review queue is cleared each month | L7 | S | MEAL officer |
| R10 | Ask officers to use the standard templates (with dropdowns and checks) and to add a planned date to paper forms | L6, L10, L11 | M | Programme managers, field officers |
| R11 | Before/after comparison on the pilot records; update the evaluation summary | L1 | S | MEAL officer (with the team if still available) |

### Later

| # | Item | Addresses | Effort | Owner |
|---|---|---|---|---|
| R12 | Baseline and follow-up surveys for handwashing and yield, so the outcome indicators can be calculated | L13 | L | Programme managers, MEAL officer |
| R13 | Extend to the second programme, then other programmes, one at a time | Scope | M per programme | MEAL officer |
| R14 | Decide on Power BI or Streamlit for the long term; if Power BI, build the report from the exports (`docs/power_bi_guide.md`) | Brief §2 | M | Executive director, MEAL officer |
| R15 | Budget data including staff and overheads, if finance can export it, for a full budget-versus-spend view | L17 | M | Finance officer |
| R16 | If the tool is used by several people: a shared, access-controlled location and backups (a server with logins is a different project) | L19, L20 | L | Executive director |
| R17 | A small "small numbers" rule for reports shared outside ARDE/KUBAHO, if agreed | Privacy | S | MEAL officer |
