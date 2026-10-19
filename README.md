# ARDE/KUBAHO MEAL and Donor Analytics Prototype

A small, free tool that turns ARDE/KUBAHO's Excel and paper records into a clean, checked dataset, MEAL indicators,
a dashboard and a one-page donor report. Staff keep working in Excel and upload their files on the dashboard, or
type records in directly; donor data is recorded on the dashboard too.

> **Demonstration data.** Everything currently runs on **synthetic records, not ARDE/KUBAHO data**. Synthetic files
> always start with `SYNTHETIC_`, and every dashboard page says so in a yellow banner.

**Status:** version 1.2 (v1.0 at the end of Phase 8; v1.1 added donor entry and the ARDE/KUBAHO look; v1.2 added
Excel upload, data entry forms for activities and monthly reports, and the Records page, and removed KoboToolbox);
feature freeze. Summary for supervisors: **`docs/project_status.md`**. Built by three ASU MS Business Analytics
students as a capstone prototype; it is not a production system. Moving to real ARDE/KUBAHO data:
**`docs/real_data_checklist.md`**.

---

## 1. First-time set-up on Windows (about 20 minutes, once per laptop)

You need an internet connection for step 1 and step 4 only.

1. **Install Python 3.11 or newer** from https://www.python.org/downloads/ . On the first screen of the installer,
   **tick "Add python.exe to PATH"**, then click "Install Now".
2. **Put the project folder somewhere simple**, for example `C:\ARDE\arde-meal-prototype`. Avoid OneDrive or other
   synced folders (they can lock files while the tool writes them).
3. **Open a command window in the folder:** open the folder in File Explorer, click the address bar, type `cmd`
   and press Enter. A black window opens, already in the right folder.
4. **Type these three lines**, pressing Enter after each one and waiting for it to finish (the last one takes a
   few minutes):

   ```
   python -m venv .venv
   .venv\Scripts\activate
   python -m pip install -r requirements.txt
   ```

   If `python` is "not recognised", Python was installed without step 1's tick: install it again with the tick.
5. **Start the dashboard:** close the black window and double-click **`run_dashboard.bat`** in the project folder.
   The first time, it creates the demonstration files and prepares the figures (about one minute), then your
   browser opens the dashboard at http://localhost:8501 . If the browser does not open by itself, type that
   address into it. Keep the black window open while you use the dashboard; close it to stop.
6. **Back up the secret "salt" file.** The first run created `C:\Users\<your name>\.arde_meal\pseudonymisation_salt.txt`.
   It protects people's identities (see `docs/privacy_and_governance.md`). Copy it to a safe place that is **not**
   shared (for example an encrypted USB key kept by the MEAL officer). Without it, new records will not link to
   old ones. Never put it in the project folder, email it, or upload it.

On Mac or Linux the same steps apply with `python3`, `source .venv/bin/activate` and `./run_dashboard.sh`.

## 2. Everyday use

- **Look at the figures:** double-click `run_dashboard.bat`. The first page is the **Executive summary**; the menu on
  the left opens the other pages. Each page has a **"How to read this page"** section at the top.
- **New monthly data:** upload each filled Excel template on the **Upload Excel** page (it shows what is accepted,
  held back for correction and sent for review before anything is added, and prepares the figures), or type records
  in on the **Data entry** page. Blank templates can be downloaded from the Upload Excel page (also in `templates/`).
  See the user guide, "How to enter this month's data". Files can still be saved in `data/raw/` by hand; then
  prepare the figures again (below).
- **Find a record:** the **Records** page lists every stored record with where it came from (file, sheet and row, or
  who entered it and when), with filters, a search and an Excel export.
- **Prepare the figures again** (after any new or corrected file): in a command window in the project folder,

  ```
  .venv\Scripts\activate
  python src/pipeline.py
  ```

  It takes under a minute and then reports what it found. Reload the dashboard page in the browser to see the new
  figures. A file whose columns are not recognised is **SKIPPED** with a message: see
  `docs/maintenance_guide.md`, "Reading a SKIPPED message".
- **Donor report:** Programme overview page, "Generate donor report": choose the project and quarter, click the
  button, download the Excel or PDF.
- **Donor data:** the **Donor entry** page (choose your name first): add and update opportunities and donors, mark
  next actions done. Dated backups are kept automatically; download the Excel backup from the Backup tab each month.
  The Excel donor template is only an offline fallback.

The full guide for staff is **`docs/user_guide.md`** (with a glossary). The guide for whoever looks after the tool
is **`docs/maintenance_guide.md`**.

## 3. Documents

| Document | For whom | What it covers |
|---|---|---|
| `docs/user_guide.md` | All staff | Using the dashboard, the donor report, the monthly routine, problems, glossary |
| `docs/maintenance_guide.md` | The person looking after the tool | New file layouts, indicators, district spellings, settings, rerunning, tests |
| `docs/power_bi_guide.md` | Anyone preferring Power BI | Loading the exported star schema into Power BI Desktop |
| `docs/privacy_and_governance.md` | Management, MEAL officer | Personal data, pseudonymisation, the salt, roles, Rwanda's Law No. 058/2021 |
| `docs/indicator_reference_sheets.md` (and `.xlsx`) | MEAL officer, co-design session | Every draft indicator, with its definition and calculation |
| `docs/data_dictionary.md` | Analysts | Every table and column |
| `docs/data_quality_report.md` | MEAL officer | The latest data-quality checks (written by the pipeline) |
| `docs/real_data_checklist.md` | MEAL officer, maintainer | Switching from synthetic to real files, and the first real run |
| `docs/data_request_pack.md` | ARDE/KUBAHO management | What data the pilot needs, how to share it safely, points for a data-sharing agreement |
| `docs/partner_questions.md` | Meeting with ARDE/KUBAHO | Every open question, by topic and priority |
| `docs/limitations_and_roadmap.md` | Everyone | Known limitations; what to do now, in 3 months and later, and who owns it |
| `docs/evaluation_summary.md` | Team, supervisors, partner | Results on the proposal's five measures; what still needs human testing |
| `docs/evaluation_before_after.md`, `docs/indicator_catalogue_audit.md` | Team, supervisors | Data quality before and after cleaning; MEAL readiness audit |
| `docs/phase2_cleaning_scorecard.md`, `docs/phase7_final_holdout_scorecard.md` | Team, supervisors | How well the cleaning works on the synthetic test sets (the held-out rounds explained) |
| `docs/project_status.md` | Supervisors | One page: what was built, results so far, what waits on testing and on the partner |
| `docs/demo_script.md` | Presenters | The 10-minute demonstration for the final presentation |
| `docs/evaluation_protocol.md`, `docs/fresh_install_test.md` | Team | How to run the timed task, the usability test and the install test |
| `docs/decision_log.md`, `docs/instruction_log.md` | Team, supervisors | Every decision and assumption; every team instruction, word for word |

## 4. Commands (for the team)

| Command | What it does |
|---|---|
| `python src/pipeline.py` | **Production run**: read `data/raw/`, pseudonymise, clean, check, build the warehouse, exports and indicators |
| `streamlit run dashboard/app.py` | Start the dashboard without the launcher |
| `python src/donor_report.py PRJ01 "FY2025/26 Q4"` | Make a donor report from the command line |
| `python src/generate_synthetic.py` | Create the synthetic demonstration files (`--verify` checks your copy against the documented fingerprint) |
| `python src/build_templates.py` | Rebuild the Excel entry templates (only if their settings changed) |
| `python src/theme.py` | Apply the colours in `config/theme.yaml` and check their contrast |
| `python src/score_cleaning.py` | Score the cleaning against the synthetic answer keys (testing only) |
| `python src/evaluate.py` | Before/after data-quality comparison (`docs/evaluation_before_after.md`) |
| `python evaluation/summarise.py` | Summarise the usability and timing sheets (`evaluation/evaluation_results.md`) |
| `python tools/capture_screenshots.py --runs 3` | Page load times and screenshots (needs `requirements-dev.txt`) |
| `python src/app_store.py --list-backups` / `--restore <file>` | List or restore backups of the donor entries (maintenance guide, 8b-2) |
| `python src/reset_demo.py` | Demonstration only: fresh synthetic data, dashboard entries and uploads cleared, figures prepared (refuses with real data) |
| `python tools/make_demo_upload.py` | Demonstration only: the filled template used in the demo's upload step |
| `python -m pytest` | All automatic checks (about 5 to 10 minutes) |

## 5. Where things are

| Folder | What it holds |
|---|---|
| `config/` | Every setting and rule, in plain text files you can edit (no code). See the maintenance guide |
| `templates/` | Standard Excel entry templates for staff |
| `assets/` | The ARDE/KUBAHO logo shown in the dashboard |
| `data/app/` | What is entered on the dashboard (`entries.db`: donors, opportunities, activity records, monthly reports, the list of uploads, the change history), its backups, and files replaced by a corrected upload |
| `data/raw/` | The Excel files the pipeline reads, including uploaded ones (synthetic for now) |
| `data/staging/` | Cleaned tables with no names, phones or ID numbers, plus the log of every change and flag |
| `data/warehouse/` | The data warehouse (`arde.duckdb`, one file) |
| `data/exports/` | CSV (opens in Excel) and Parquet (for Power BI) copies of every table; donor reports |
| `data/ground_truth/` | Answer key for the synthetic data (testing only; never read by the pipeline) |
| `src/` | The Python scripts. `dashboard/`: the dashboard. `tests/`: automatic checks |
| `evaluation/` | Sheets for the usability and timing tests, and their summary |
| `docs/` | Guides, decision log, generated reports |

Nothing under `data/` is ever put into git: real partner data must never leave the agreed storage.
