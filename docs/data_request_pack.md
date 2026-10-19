# Data request pack for ARDE/KUBAHO

What the student team would need from ARDE/KUBAHO to test the prototype on **one pilot programme**, the minimum
fields, the period, and how files should be shared and kept. It is written to be discussed at a meeting, not sent as
a demand: **everything here is to be confirmed with ARDE/KUBAHO and Arizona State University.**

> **Preferred option: the team never receives personal data.** ARDE/KUBAHO runs the tool on its own laptop
> (`docs/real_data_checklist.md`), so names, phone numbers and ID numbers never leave ARDE/KUBAHO. The team then
> receives only pseudonymised outputs (the files in `data/exports/`, which contain no names, phones or IDs) and the
> data-quality report, if ARDE/KUBAHO agrees. The requests below are written for that option; section 4 covers the
> alternative.

---

## 1. Scope

| Item | Proposal (to be confirmed) |
|---|---|
| Pilot programme | **One** programme, chosen by ARDE/KUBAHO (WASH or agriculture/climate resilience) |
| Period | The **last 12 months of complete records**, plus the same quarter one year earlier if available (to compare) |
| Districts | All districts of the pilot programme |
| Volume | Whatever exists for that programme and period; record counts are not needed in advance |

## 2. Files we need (what the tool reads)

| # | File | Minimum fields | Nice to have |
|---|---|---|---|
| 1 | **Programme and project list** (any format; the team or the MEAL officer turns it into the programme master) | Programme name and theme; for each project: name, budget (RWF), start and end dates, districts; list of activity types; list of villages with sector, cell and district; field officer codes and their districts | Funder of each programme; the indicators each project reports |
| 2 | **Activity monitoring** files (one per officer or per month, as they are now) | Activity date, activity type, project, district, village, status (done, delayed, cancelled), number of participants (women, men, total), cost (RWF) | Planned date, date entered, officer code |
| 3 | **Beneficiary registers** | A registration number, name (or surname and first name), sex, age or date of birth, district, village, registration date, project | Phone number and national ID (used only to find people registered twice, then removed), household size, disability |
| 4 | **Service or attendance records** (who received which service, if kept) | Registration number, activity, date | Type of service |
| 5 | **Monthly indicator reports** | Project, district, month, indicator name, actual value, target | Breakdown by sex where reported, comments |
| 6 | **Donor and opportunity tracking** (if any) | Donor organisation, opportunity title, stage, deadline, amount requested | Probability, owner, next action and date, awarded amount |
| 7 | **The last donor report** for one pilot project | (For comparing totals in the first real run) | The MEAL officer's own working spreadsheet |
| 8 | **Scanned or photographed paper forms** (a small sample only) | (To see how paper records are kept; not digitised by the team) | |

**As the files are now.** Please do not clean or reformat anything first: the point is to test the tool on the files
as they really are. If a file mixes several projects, that is fine.

## 3. Transfer and storage (if any file with personal data must leave ARDE/KUBAHO)

| Point | Proposal |
|---|---|
| Who sends | One named person at ARDE/KUBAHO (suggested: the MEAL officer) |
| Who receives | One named team member; the files are not forwarded |
| How | An encrypted, password-protected archive (e.g. 7-Zip, AES-256) on the university's approved storage; **the password sent by a different channel** (e.g. by phone). Never by WhatsApp, personal email, or a public file-sharing link |
| Where kept | Only on ASU-approved encrypted storage, not on personal laptops or personal cloud accounts, not in git (the project's `data/` folder is excluded from git) |
| Who can open | Named team members only, for the purpose below |
| The salt | Created on ARDE/KUBAHO's laptop and **never** sent to the team |
| Personal data in reports | None: the capstone report and presentation use counts, percentages and synthetic examples only |

## 4. Points for a data-sharing agreement

These follow the principles of **Rwanda's Law No. 058/2021 on the protection of personal data and privacy** (see
`docs/privacy_and_governance.md`). They are a starting list for ARDE/KUBAHO, the team and the university, **to be
confirmed with ARDE/KUBAHO and the university** (and a lawyer if ARDE/KUBAHO wishes). They are not legal advice.

| Point | Proposal |
|---|---|
| **Purpose** | Only to test and evaluate the prototype for ARDE/KUBAHO's MEAL and donor reporting, and to report the results as anonymous figures in the ASU capstone report. No other use, no sale, no publication of records |
| **Data minimisation** | Only the fields in section 2, for the pilot programme and period; personal identifiers only if ARDE/KUBAHO cannot run the tool itself |
| **Legal basis** | ARDE/KUBAHO confirms it may share the data for this purpose (consent given at registration, or another basis under the law) |
| **Access** | Named team members and, if needed, the faculty supervisor; access ends when the project ends |
| **Storage** | Encrypted university storage (section 3); no storage outside the agreed place; whether storage outside Rwanda is allowed must be confirmed under the law |
| **Security** | Password-protected devices; no copies on phones or personal accounts; any loss reported to ARDE/KUBAHO **immediately** (the law sets a short deadline for notifying the authority) |
| **Retention** | Kept only until the final presentation and grading (date to be agreed) |
| **Deletion** | All copies deleted at the end, including backups and exports; the team confirms deletion in writing to ARDE/KUBAHO |
| **Rights of the people in the data** | Requests to see, correct or delete data go to ARDE/KUBAHO, which tells the team to act on them |
| **Outputs** | ARDE/KUBAHO may review the capstone report and presentation before they are shared, to check no person can be identified |
| **Contacts** | One contact at ARDE/KUBAHO, one in the team, one at ASU |
| **Dashboard entries database** | `data/app/entries.db` and its backups stay on ARDE/KUBAHO's laptop and are never sent to the team. They hold organisation donors' names, opportunities, activity records and monthly reports typed in on the dashboard, the list of uploads, staff codes and the change history; no contact details, no people, and no names of individual donors. Files uploaded on the dashboard are raw files like any other (section 3). If the team needs to check them, ARDE/KUBAHO may share the downloaded Excel backup, by the route in section 3 |

## 4b. Data entered on the dashboard (no request to the team)

This does **not** require sending anything to the team, but it is part of the same agreement:

- **Data entered on the dashboard** (donors, opportunities, activity records and monthly indicator reports) stays on
  ARDE/KUBAHO's laptop (`data/app/`), with automatic local backups. Uploaded Excel files are kept there too.
  The one-time import of the Excel donor tracker is done on that laptop by ARDE/KUBAHO staff.

**To be confirmed with ARDE/KUBAHO and the university.**

## 5. What ARDE/KUBAHO gets back

- The prototype set up on its own laptop, with the guides (README, user guide, maintenance guide).
- The data-quality report on its own files: which sheets could not be read, what was quarantined and why.
- The before/after comparison on the pilot records, and the indicator catalogue ready for the co-design session.
