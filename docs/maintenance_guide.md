# Maintenance guide

For the person at ARDE/KUBAHO who **looks after** the tool (suggested: the MEAL officer, with help from someone
comfortable with files and folders). You need Excel skills and a text editor; **no programming**. Almost everything
is changed in the plain-text files in `config/`, never in the code.

> Before changing anything: copy the `config/` folder somewhere safe (for example `config_backup_2026-10-15`). If
> something goes wrong, copy it back.

**Editing a `.yaml` file:** open it with Notepad (right-click > Open with > Notepad) or VS Code. Rules: keep the
spaces at the start of each line exactly as they are (spaces, never tabs); text after `#` is a comment; put text
containing a colon in "double quotes". After saving, run the pipeline: if the file has a mistake, it says which line.

---

## 1. Opening a command window

Open the project folder in File Explorer, click the address bar, type `cmd`, press Enter. Then always type first:

```
.venv\Scripts\activate
```

(The line now starts with `(.venv)`.) All commands below are typed in this window.

## 2. Rerunning the pipeline

```
python src/pipeline.py
```

Do this after adding or correcting any Excel file in `data/raw/`, or after changing anything in `config/`. It takes
under a minute and prints each step:

```
[run ] Ingest and pseudonymise ...
...
Data quality: overall 96.3%; 235 rows quarantined, 282 rows for review, 0 sheets skipped.
Production pipeline finished in 18.4s
```

Then reload the dashboard page in the browser (F5). The dashboard never needs restarting for new data.

If it stops with an error, read the **last lines**: they say what is wrong in plain words (for example a YAML line
number, or a file that is open in Excel: close it and run again).

## 3. Reading a SKIPPED message

When a sheet's columns are not recognised, the pipeline does **not** guess or read it partly. It skips the whole
sheet, prints a message and shows it in a red box at the top of the Data quality page:

```
SKIPPED SYNTHETIC_activity_monitoring_FO06.xlsx / Activities: required field(s) not found: date, activity, status.
Unrecognised column headers: Event date, Target date, Data entry date, Project title, Type of activity,
Implementation status, Females, Males, Expenditure (Frw), Recorded by. Add them to config/source_mappings.yaml and
run the pipeline again.
```

How to read it:

| Part | Meaning |
|---|---|
| `SYNTHETIC_activity_monitoring_FO06.xlsx / Activities` | The file and the sheet that were skipped. **None of its rows are counted** until fixed |
| `required field(s) not found: date, activity, status` | The standard fields the pipeline needs and could not find (the list per kind of sheet is `required_fields` at the end of `config/source_mappings.yaml`) |
| `Unrecognised column headers: ...` | The column names in the sheet that the pipeline does not know yet. Usually these are the same fields with new names |

What to do: match each unrecognised header to a standard field and add it (section 4). Here: `Event date` is
`date`, `Type of activity` is `activity`, `Implementation status` is `status`, `Females` is `female`, and so on.
Then rerun. If the sheet is something else entirely (a notes sheet), it can be ignored.

The list of every sheet read, its kind and any unrecognised columns is in `data/staging/sheet_inventory.csv`.

## 4. Adding a new file layout (new column names)

Open `config/source_mappings.yaml`.

**New column names in a known kind of file** (the most common case): find the kind of record under `fields:`
(`activity`, `registration`, `service`, `indicator_result`, `donor`, `opportunity`) and add the new name to the
list of the standard field it means. Upper or lower case, extra spaces and full stops do not matter.

```yaml
fields:
  activity:
    date: [Date, Activity date, "Itariki y'igikorwa", Date of activity, Event date]      # <- added
    activity: [Activity, Activity type, Activity name, Type of activity]                  # <- added
```

**A new kind of file name:** under `files:`, add a pattern (the `*` matches anything) and say which sheet holds which
kind of record. Example for a new officer's register called `Kirehe_register_2027.xlsx`:

```yaml
files:
  - pattern: "*register*.xlsx"
    sheets: {Register: registration, Services: service}
```

Rerun the pipeline and check that the SKIPPED message has gone and the Data quality page shows the file under
"By source file". Keep a note in `docs/decision_log.md`.

**Better still:** ask officers to use the standard templates in `templates/` (their column names are already known).

## 5. Adding a new district spelling

Most spellings are handled already: upper/lower case, extra spaces, "District" / "Akarere ka" in front, and small
typing mistakes (for example `Nyagatre`) are corrected and logged. A spelling that is too different (for example a
nickname or an old name) is flagged **"District name not recognised"** and the row is quarantined.

1. **A word that is often added to district names** (like "Akarere"): add it to `district_noise_words` in
   `config/settings.yaml` (lower case).
2. **A spelling or old name that always means one district** (confirmed with the officer who wrote it): add it to
   `one_to_one` in `config/district_legacy_map.yaml`:

   ```yaml
   one_to_one:
     "Nyaga tare": Nyagatare
     "Umutara Nyagatare": Nyagatare
   ```

   The district on the right must be spelt exactly as in `config/reference/rwanda_admin.yaml`.
3. **An old name that could mean several districts** (for example `Byumba`): leave it under `ambiguous`. The pipeline
   never guesses; it uses the village if the village exists in only one of the candidate districts, and sends the row
   to the review queue either way.

Rerun the pipeline. The change is logged in `data/staging/issues.parquet` ("district_legacy_name_mapped").

**New villages** come from the "Locations" sheet of the programme master file: add the village there (with its
sector, cell and district), not in the config.

## 6. Adding a new indicator

Open `config/indicator_catalogue.yaml`. Copy a similar indicator's whole block (from `- code:` down to its
`notes:`) and paste it at the end of the list. Change:

| Field | What to write |
|---|---|
| `code` | A new, unique code, e.g. `WASH-05` |
| `name`, `definition`, `numerator`, `denominator`, `calculation_rule`, `counting_rule` | Plain words. Keep the status `Draft, for co-design with ARDE/KUBAHO staff` until agreed |
| `unit` | `number`, `percent`, `hectares` or `RWF` |
| `axis_label` | The chart axis title, e.g. `Number of schools` |
| `level` | `output` or `outcome` |
| `disaggregation` | `none` or `sex` |
| `frequency` | `monthly` or `quarterly` |
| `aggregation` | How months add up: `sum` (people trained), `latest` (functional committees today), `average`, or `ratio` |
| `higher_is_better` | `true` or `false` |
| `availability` | `available`, or `data source not yet available` (it is then listed but not calculated) |
| `calculation` | `reported: {}` if officers report it in the monthly indicator report |

For a **reported** indicator, officers must also be able to type it: add the indicator's exact name to the indicator
report template and make sure each monthly report sheet has it (the pipeline matches the code or the name). Targets
are typed in the same report. Rerun the pipeline: the indicator appears on the Indicators page, and
`docs/indicator_reference_sheets.md` and `.xlsx` are rewritten automatically.

A **worked-out** (derived) indicator needs a calculation method written in `src/indicators.py`: that is a job for
someone who knows Python. The existing methods can be reused with new activity codes without programming (for
example `unique_people` with a different `activity_ids` list).

## 7. Other settings (`config/settings.yaml`)

| Setting | What it changes |
|---|---|
| `as_of_date` | The date the figures are "as of" (leave empty to use today) |
| `currency.usd_to_rwf` | The exchange rate for the USD display (update from the BNR rate) |
| `traffic_light` | The on-track (90) and at-risk (70) thresholds |
| `budget_monitoring.over_budget_pct` | When a project is "over budget" (100 = more than its whole budget) |
| `indicators.reconciliation_tolerance_pct`, `reconciliation_min_difference` | When a report and the records "disagree" (10% and 5) |
| `data_quality.late_entry_days` | When an activity counts as entered late (30 days) |
| `duplicate_matching.threshold` | How similar two names must be to be suspected duplicates (88 of 100) |
| `donor_pipeline.stages`, `themes`, `ending_within_months` | Donor pipeline stages, themes and the pipeline-gap window |
| `sex_mapping`, `activity_status_mapping` | Which words mean female/male, completed/cancelled... (add new spellings here) |
| `synthetic_mode`, `synthetic_banner` | Switch off when real data is used (Phase 8 checklist) |

The "How to read this page" texts are in `config/page_help.yaml`; the plain words for problems shown on the
Data quality page are under `labels:` at the end of `settings.yaml`.

## 8. The templates

The Excel entry templates in `templates/` are built from `config/templates.yaml` (columns, dropdown lists, checks,
instructions). After changing that file run `python src/build_templates.py`. Dropdown lists for projects, activities
and officers come from the settings and the programme master.

## 8b. Staff on the Donor entry page

The names people pick on the Donor entry page come from `config/staff.yaml` (a staff code and a role each). Add or
remove a line, keeping the spaces, and reload the page. Codes are recommended rather than full names. The entries
are in `data/app/entries.db` (SQLite): back it up with the Excel files; to inspect it, the free "DB Browser for
SQLite" opens it (read only, please).

## 8b-2. Restoring donor entries

Donor entries live only in `data/app/entries.db`. Copies are kept in `data/app/backups/` (after every save, each
time the dashboard starts, after an import; the newest 30, `app_backups_keep` in `settings.yaml`), each named with
its date and time, e.g. `entries_20261019-101500-123456_save.db`.

To put a backup back (for example after a mistaken change, or a damaged file):

1. Close the dashboard (close its black window) so nobody is entering data.
2. In a command window in the project folder (section 1), list the copies, newest first:
   ```
   python src/app_store.py --list-backups
   ```
3. Choose the copy from just before the problem (the time is in the name; the change history in the Downloaded
   Excel backups also shows what changed when), and restore it:
   ```
   python src/app_store.py --restore data/app/backups/entries_20261019-101500-123456_save.db
   ```
   The current file is first copied to a `..._before-restore.db` backup, so a restore can itself be undone the same
   way.
4. Start the dashboard, open **Donor entry**, check the entries and the change history, then click **Update the
   figures now**.

If every copy on the laptop is lost (for example a broken disk), the downloaded Excel backup holds the same data:
ask the person who maintains the tool to load it into a fresh database (each sheet is one table, with the same
column names). Restoring is tested automatically (`tests/test_app_entries.py`).

## 8c. KoboToolbox forms

The forms in `forms/` are built from the programme master and the indicator catalogue:

```
python src/build_kobo_forms.py
```

Run it after a new project, activity, officer or village is added to the programme master (and after the pipeline
has read it), then replace the form in KoboToolbox (`docs/kobo_guide.md`, section 3). If a Kobo export is SKIPPED, a
question was renamed or added: add its name to `config/source_mappings.yaml` as for any new column (section 4).
Kobo's own columns (start, end, _uuid...) are listed under `ignore_columns` there.

## 8d. Colours and logo

All colours are in `config/theme.yaml` (brand colours to be confirmed with ARDE/KUBAHO). After changing them:

```
python src/theme.py
```

It writes the Streamlit theme into `.streamlit/config.toml` and checks every colour pair for contrast (WCAG AA):
anything marked FAIL must be darkened before use. Restart the dashboard to see the change. The logo is
`assets/arde_logo.png` (no logo is shown if the file is missing). The yellow synthetic-data banner is not part of the
theme and must not be changed.

## 9. The salt (keep it safe)

`C:\Users\<name>\.arde_meal\pseudonymisation_salt.txt` turns names, phones and IDs into coded keys. **If it is lost,
new records get different keys and will not link to old ones.** If it leaks, someone with the raw files could link
keys back to people. Keep one backup copy offline, with the MEAL officer. When moving the tool to a new computer,
copy the salt file to the same place on the new computer **before** the first run. See
`docs/privacy_and_governance.md`.

## 10. Checking that everything still works

```
python -m pytest
```

About 5 to 10 minutes. It should end with "passed" and no "failed". Run it after any change to `config/` or the code. With
real data, some tests that check the synthetic answer key will be skipped or need the synthetic data; see the
Phase 8 checklist.

## 11. Where to get help

- `docs/decision_log.md`: why things are the way they are.
- `docs/data_dictionary.md`: every table and column.
- The ASU team's contact details: to be confirmed with partner at handover.
