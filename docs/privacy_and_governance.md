# Privacy and governance

For ARDE/KUBAHO management, the MEAL officer, and anyone who will handle real beneficiary or donor records with this
tool. It says what the prototype does to protect personal data, what it cannot do, and what must be decided before
real data is used.

> **Not legal advice.** The governing standard is **Rwanda's Law No. 058/2021 of 13/10/2021 relating to the protection
> of personal data and privacy**. What follows is the student team's reading for a prototype. ARDE/KUBAHO's actual
> obligations **must be confirmed with the partner (and, where needed, a lawyer or the supervisory authority) and with
> Arizona State University** before any real personal data is shared with the team or processed by the tool.

---

## 1. What personal data the tool sees

| Record | Personal data in the Excel files | What the tool keeps |
|---|---|---|
| Beneficiary register | Names, phone numbers, national ID numbers, dates of birth, sex, age, household size, disability, village | A **coded key** per person; sex, age band, household size, disability yes/no, village. **No name, phone, ID number or date of birth** |
| Service records | Registration number, activity, date | The coded key, activity, date |
| Activity records | Officer code, numbers of participants | Officer code (staff, not beneficiaries), counts |
| Dashboard entries database (`data/app/entries.db`, entered on the dashboard) | None by design: no contact details are asked for; an individual donor's name is refused by the database; activity records and monthly reports hold counts only (women, men, total), never people | Organisation donors' names, opportunities, activity records, monthly indicator reports, the list of uploads (file name, staff code, date), staff **codes** (who made each change) and the change history. Individual donors appear as "Individual donor #NNN". Backups in `data/app/backups/` and the downloaded Excel backup hold the same |
| Uploaded Excel files (`data/raw/`, Upload Excel page; replaced ones in `data/app/replaced_files/`) | An uploaded **beneficiary register holds names, phones and ID numbers**, like any register | Kept with the other raw files and treated the same way: never leaves the laptop, pseudonymised by the pipeline. The upload check reads a scratch copy inside `data/app/`, deleted afterwards. The Records page never lists people |
| Donor file | Donor organisation, contact person, email, phone | Organisation name and type. **Contact details are dropped.** Individual donors appear only as "Individual donor #NNN" |

**Disability is health-related information,** which the law treats as sensitive personal data. The tool keeps only a
yes/no flag and never shows it per person; whether ARDE/KUBAHO may record it, and on what basis (for example
consent), is **to be confirmed with the partner**.

## 2. How the tool protects it (privacy by design)

1. **Pseudonymisation at the first step.** When the files are read (`src/ingest.py`), names, phone numbers, ID
   numbers and dates of birth are used only to (a) find people registered twice and (b) make a coded key with a
   **salted hash** (HMAC-SHA256, shortened to 12 characters). They are then dropped: they never reach `data/staging/`, the warehouse, the exports,
   the dashboard or the donor report. The model checks this on every run and refuses to save if a personal-data column
   appears (`src/model.py`).
2. **The salt** is a secret random value stored **outside the project folder**
   (`C:\Users\<name>\.arde_meal\pseudonymisation_salt.txt`). Without it the coded keys cannot be recreated from names.
   It is never put in git, exported or emailed. Losing it breaks the link between old and new records; leaking it,
   together with the raw files, would let someone re-identify people. **Keep one offline backup, held by the MEAL
   officer.**
3. **Small numbers.** The dashboard shows counts and percentages, never individual beneficiaries. Very small counts
   (for example one woman with a disability in one village) could still point to a person: **to be agreed with the
   partner** whether counts under a threshold (for example 5) should be hidden in reports shared outside ARDE/KUBAHO.
4. **Lineage without identity.** Every figure can be traced to a file, sheet and row of the original Excel file, so
   staff with access to that file can check it, but the dashboard itself never shows the person.
5. **Local only.** The tool runs on an ordinary laptop; it sends nothing to a cloud service. Data comes in only
   through Excel files and the dashboard's own forms. The dashboard accepts
   connections only from that laptop (`address = "127.0.0.1"` in `.streamlit/config.toml`), not from other devices
   on the same network.
6. **Synthetic data until approved.** All development and testing used invented records, labelled `SYNTHETIC_` and
   bannered on every page. The team has not received any real ARDE/KUBAHO data.

7. **Donor entries:** the database has no columns for people's contact details (tested); it refuses a name for an
   individual donor; staff are recorded by code, not by name (`config/staff.yaml`). Its backups stay on the laptop.

## 3. What the tool cannot do (people and processes must)

- It does not protect the **raw Excel files** in `data/raw/` or on officers' laptops and phones: those hold names and
  IDs. They need the same care as paper registers (password-protected laptops, no sharing by WhatsApp or personal
  email, a clear place to keep them).
- It has **no user logins**: anyone who can use the laptop can open the dashboard. Keep the laptop and its account
  protected.
- It does not delete old records automatically (see retention, below).
- Paper forms remain paper: digitised copies and the originals both need safekeeping.

## 4. Points from Law No. 058/2021 to confirm with ARDE/KUBAHO

Our reading of the law raises these questions. None has been answered yet; each is on the partner list in
`docs/decision_log.md`.

| Topic | Question for ARDE/KUBAHO (and the university) |
|---|---|
| Legal basis and consent | On what basis are beneficiaries' data collected (consent, a contract, legitimate interest)? Do registration forms tell people how their data will be used, including analysis like this? |
| Registration | Is ARDE/KUBAHO registered as a data controller with the supervisory authority (the National Cyber Security Authority, NCSA), as the law requires of organisations processing personal data? |
| Sensitive data | Disability (and any health information) is sensitive: is its collection necessary and covered by consent? |
| Storage and transfers | Where may the data be stored? The law restricts storing or transferring personal data outside Rwanda; this tool stores everything locally. Any cloud copy (OneDrive, Google Drive) would need checking |
| Sharing with the student team | May the team see real data at all? If yes, only pseudonymised extracts, under a written data-sharing agreement with ASU, on encrypted university storage, deleted at project end |
| Data subjects' rights | How would a person's request to see, correct or delete their data be handled across the Excel files and the tool? |
| Breaches | Who notifies the authority and the people affected, and how fast, if a laptop or file with personal data is lost? (The law sets a short deadline; to be confirmed.) |
| Retention | How long are registers and the tool's data kept after a project ends? |
| Donor entries | Who may enter and change donor data (there is no login), and how long are entries and their backups kept? |

## 5. Roles (suggested; to be agreed)

| Role | Responsibility |
|---|---|
| Executive director | Owner of the data on behalf of ARDE/KUBAHO; approves sharing and retention |
| MEAL officer | Runs the pipeline; keeps the salt backup; first contact for data-quality and privacy questions |
| Programme managers | Use the dashboard and donor reports; check donor reports before sending |
| Field officers | Collect data with consent; keep raw files safe; correct their files from the work lists |
| Student team (until handover) | Synthetic data only, unless a written agreement says otherwise |

## 6. Before real data is used (checklist)

- [ ] Questions in section 4 answered and recorded
- [ ] Written agreement on what, if anything, the student team may see
- [ ] Salt created on the ARDE/KUBAHO laptop by ARDE/KUBAHO, backed up offline, never shared with the team
- [ ] Raw files stored on a protected laptop; `data/` excluded from any sync or backup service unless approved
- [ ] Small-number rule for shared reports agreed
- [ ] `synthetic_mode` switched off and the banner removed only after the above (Phase 8 checklist)
- [ ] Who may use the Donor entry, Data entry and Upload Excel pages agreed; monthly Excel backup kept offline
- [ ] Replaced upload files (`data/app/replaced_files/`) deleted on the same schedule as other raw files
