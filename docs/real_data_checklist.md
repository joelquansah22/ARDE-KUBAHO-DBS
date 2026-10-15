# Real-data switch checklist

How to move the prototype from synthetic records to ARDE/KUBAHO's real files. Follow the steps **in order**, tick
each one, and write the date and initials. Do not skip the first-real-run procedure (section 6): **no dashboard figure
is trusted until it is done.**

> Before starting: the privacy checklist in `docs/privacy_and_governance.md` (section 6) must be complete, and the data
> request pack (`docs/data_request_pack.md`) agreed. The real files are processed **on an ARDE/KUBAHO laptop**, by
> ARDE/KUBAHO staff or under a written agreement.

---

## 1. Prepare a clean copy of the tool

- [ ] Copy the whole project folder to the ARDE/KUBAHO laptop (or clone it), and set it up as in the README.
- [ ] Run `python -m pytest` once **before** switching: it should pass on the synthetic data. Keep this copy as a
      reference ("demo copy") if a demonstration is still needed.
- [ ] Work in a **second copy** of the folder for real data (for example `C:\ARDE\meal-real`). Never put real files
      into the demo copy.

## 2. A new salt (never reuse the synthetic one)

The salt makes the coded keys for people. The salt used with the synthetic data must not be reused for real people.

- [ ] On the ARDE/KUBAHO laptop, if `C:\Users\<name>\.arde_meal\pseudonymisation_salt.txt` exists, rename it to
      `pseudonymisation_salt_SYNTHETIC_DO_NOT_USE.txt` (or delete it if the demo copy is not on this laptop).
- [ ] The first real run (section 6) creates a new salt automatically. **Immediately back it up offline** (MEAL
      officer). Nobody outside ARDE/KUBAHO, including the student team, ever receives it.

## 3. Settings (`config/settings.yaml`)

| Setting | Change to | Done |
|---|---|---|
| `synthetic_mode` | `false`. This removes the yellow banner from every page, report and document, removes the `SYNTHETIC_` prefix from donor report file names, and makes the pipeline refuse any `SYNTHETIC_` file | [ ] |
| `as_of_date` | `null` (use today's date), or the reporting date agreed with the MEAL officer | [ ] |
| `reporting_window` | First and last day of the pilot period (section 1 of the data request pack) | [ ] |
| `currency.usd_to_rwf` | The current BNR rate, or the rate ARDE/KUBAHO uses in donor reports | [ ] |
| `traffic_light`, `budget_monitoring`, `indicators.reconciliation_*` | Leave as they are unless the co-design session changed them | [ ] |
| `donor_pipeline.themes` | ARDE/KUBAHO's real themes (matching `thematic_area` in the programme master) | [ ] |
| `data_quality.late_entry_days`, `on_time_tolerance_days` | As agreed with the MEAL officer (now 30 and 7 days) | [ ] |

`synthetic_banner` can stay; it is only shown in synthetic mode.

## 4. Remove every synthetic file

- [ ] Delete everything in `data/raw/`, `data/staging/`, `data/warehouse/`, `data/exports/` (including
      `data/exports/donor_reports/`) and `data/ground_truth/`. The held-out folders (`data/holdout*`, `data/final_holdout`)
      are only needed in the demo copy: delete them here. Also delete `data/app/entries.db` (donor entries made during
      demonstrations) and `data/kobo_test/` (synthetic Kobo exports).
- [ ] In a command window in the project folder: `dir /s /b SYNTHETIC_*`. It must list **nothing** (no `.xlsx`,
      `.csv`, `.parquet` or `.pdf` file whose name starts with `SYNTHETIC_`).
- [ ] The pipeline double-checks: with `synthetic_mode: false` it **stops** if any `SYNTHETIC_` file is in `data/raw/`,
      and with synthetic mode on it stops if a non-synthetic file is there (`src/pipeline.py`, `mode_problems`).

## 5. Map the real files

**Programme master.** The pipeline needs one `*programme_master*.xlsx` file with five sheets: Programmes, Projects,
Activities, Locations, Field officers. Their columns are those of `data/raw/SYNTHETIC_programme_master.xlsx` in the
demo copy (`programme_id, name, thematic_area, funder_id, start_date, end_date, status`; `project_id, programme_id,
name, budget_rwf, start_date, end_date, districts, indicators`; `activity_id, project_id, activity_name,
activity_type`; `location_id, province, district, sector, cell, village`; `officer_code, districts`).

- [ ] Build it from ARDE/KUBAHO's project documents (data request pack, item 1) and save it as
      `data/raw/ARDE_programme_master.xlsx`.
- [ ] Every village used in the registers is in the Locations sheet, spelt as staff usually write it.

**Monthly files.**

- [ ] Copy the real files into `data/raw/` with names that match a pattern in `config/source_mappings.yaml` (for example
      `..._activity_monitoring_...xlsx`, `..._beneficiary_register_...xlsx`, `..._indicator_report_...xlsx`,
      `..._donor_opportunity_...xlsx`), or add a pattern for their names (maintenance guide, section 4).
- [ ] Run `python src/pipeline.py`. For every **SKIPPED** message, add the column names to
      `config/source_mappings.yaml` (maintenance guide, section 3) and run again, until no sheet is skipped that should
      be read.
- [ ] Check `data/staging/sheet_inventory.csv`: every sheet has the right kind, and no important column is listed as
      unrecognised.

**Codes used in the configuration.** These now hold synthetic codes and must be changed to the real ones:

| File | Entry | Done |
|---|---|---|
| `config/indicator_catalogue.yaml` | WASH-01 `activity_ids: [ACT01]` and AGR-01 / CC-05 `activity_ids: [ACT10]`: the real activity codes for water points and farmer training | [ ] |
| `config/indicator_catalogue.yaml` | CC-03 `reach_indicators: {PRG01: [WASH-01], PRG02: [AGR-01]}`: the real programme codes and their people-reached indicators | [ ] |
| `config/indicator_catalogue.yaml` | The indicator list itself, as agreed at the co-design session (names exactly as typed in the monthly reports) | [ ] |
| `config/templates.yaml` | `projects`, `activities`, `officers` lists: replace `{from: synthetic_...}` with the real lists, then `python src/build_templates.py --force` | [ ] |
| `config/district_legacy_map.yaml` | Old names confirmed with the field officers | [ ] |
| `config/staff.yaml` | ARDE/KUBAHO's real staff codes for the Donor entry page | [ ] |
| `forms/` | After the first real run: `python src/build_kobo_forms.py`, then upload the forms to ARDE/KUBAHO's own KoboToolbox account (`docs/kobo_guide.md`) | [ ] |
| `config/theme.yaml` | Brand colours and logo confirmed with ARDE/KUBAHO | [ ] |
| `config/settings.yaml` | `sex_mapping`, `activity_status_mapping`: any new spellings staff use | [ ] |
| `config/settings.yaml` | Month-first dates: whether staff write `Mar 12, 2024` (partner question) | [ ] |

## 6. First real run (before trusting any figure)

Work on a **copy** of ARDE/KUBAHO's files, never the originals: if anything goes wrong, the originals are untouched.

1. - [ ] **Copy, do not move:** the files in `data/raw/` are copies; the originals stay where ARDE/KUBAHO keeps them.
2. - [ ] **Run** `python src/pipeline.py` and keep its printed output (copy it into a text file with the date).
3. - [ ] **Record counts.** For each file, compare the rows read (`data/staging/sheet_inventory.csv` and the Data
         quality page, "By source file") with the number of records ARDE/KUBAHO expects (the officer's own count, or the
         number of filled rows in Excel). Any difference must be explained (blank rows, totals rows, duplicates removed).
4. - [ ] **Key totals.** For one recent quarter and each pilot project, compare with ARDE/KUBAHO's own figures (the last
         donor report, or the MEAL officer's spreadsheet): people reached, activities completed, activity spending,
         and each reported indicator. Write each pair side by side in a table, with the reason for any difference.
5. - [ ] **SKIPPED sheets.** Go through **every** SKIPPED message with the MEAL officer: fix the mapping or agree that the
         sheet is not needed. None may remain unexplained.
6. - [ ] **Quarantine.** Go through the quarantine list (Data quality page, Work lists) with the MEAL officer. For each
         reason, check a few rows in the Excel file: is the rule right for ARDE/KUBAHO's data? If a rule is wrong (for
         example a date style staff really use), change the configuration, not the data, and run again.
7. - [ ] **Review queue and duplicates.** Look at the review queue and the people pending duplicate review: is the load
         manageable (about an hour a month at most)?
8. - [ ] **Reconciliation.** Look at the gaps between reports and records: are the like-for-like definitions right for the
         real activities?
9. - [ ] **Sign-off.** Only when steps 3 to 8 are done and the MEAL officer agrees, the dashboard figures may be used in a
          meeting. Write the date, the names and any figures still known to be wrong in `docs/decision_log.md`.

Then run the **before/after comparison on the pilot records** (`python src/evaluate.py`; the "people counted twice"
line needs the synthetic answer key and is left out with real data) and copy the results into
`docs/evaluation_summary.md`.

## 7. After the switch

- [ ] `python -m pytest`: tests that check the synthetic warehouse are skipped automatically when `synthetic_mode` is
      false; all others must pass.
- [ ] Every page, report and document no longer shows the synthetic banner; the Executive summary still fits the screen.
- [ ] `docs/data_quality_report.md` and `docs/data_dictionary.md` are regenerated (they are, by the pipeline).
- [ ] Nothing under `data/` is committed to git or uploaded anywhere (it is excluded by `.gitignore`).
- [ ] The salt backup is in place (section 2).

| Step | Date | Initials |
|---|---|---|
| 1. Clean copy | | |
| 2. New salt | | |
| 3. Settings | | |
| 4. Synthetic files removed | | |
| 5. Files mapped | | |
| 6. First real run signed off | | |
| 7. After the switch | | |
