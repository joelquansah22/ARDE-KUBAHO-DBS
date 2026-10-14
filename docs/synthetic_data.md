# Synthetic data guide

**Everything described here is invented.** It is demonstration data, not ARDE/KUBAHO data.

## How to create it

```
python src/generate_synthetic.py
```

It takes about 6 seconds. The seed is fixed (`config/synthetic.yaml`), so every run gives identical files.
The script deletes and recreates the `SYNTHETIC_*` files each time.

## Is my copy identical to everyone else's?

The data is not stored in git, so each teammate generates their own copy. To check it:

```
python src/generate_synthetic.py --verify
```

It prints `OK` if your files match this content fingerprint (SHA-256):

```
d62680eec7338d7b664106c890deefea7403d310dcb4ba16c2d82dc3673bdd5a
```

The fingerprint covers every cell of every `SYNTHETIC_*.xlsx` file and every answer-key CSV.
It ignores the save time that Excel stores inside each file, which is why the file bytes can differ
while the contents are identical. If you see `MISMATCH`, regenerate and check that you installed
`requirements.txt` exactly (the generator depends on the numpy version). The expected value is
also stored as `expected_fingerprint` in `config/synthetic.yaml`, and a test fails if they drift apart.

## What it creates

### `data/raw/`: the messy Excel files (what the pipeline reads)

| File | Contents | How it is messy |
|---|---|---|
| `SYNTHETIC_programme_master.xlsx` | Programmes, projects, activity list, villages, field officers | Clean. This is the reference list the MEAL officer keeps. |
| `SYNTHETIC_activity_monitoring_FO01.xlsx` | Activities, Nyagatare and Kayonza | Mostly real Excel dates with some `dd/mm/yyyy` text; some numbers typed as text, e.g. costs like `RWF 5,598,000`; `TOTAL` row at the bottom |
| `SYNTHETIC_activity_monitoring_FO02.xlsx` | Activities, Bugesera and Kirehe | Title row, **two-row merged header**, project codes, ISO text dates with some `March 2024`, a Province column (sometimes wrong) |
| `SYNTHETIC_activity_monitoring_FO03.xlsx` | Activities, Nyamagabe and Huye | **Kinyarwanda headers**, dates as Excel serial numbers (`45363`), costs always text with `RWF`, statuses `Done`/`Late`, `IGITERANYO` totals row |
| `SYNTHETIC_activity_monitoring_FO04.xlsx` | Activities, Rulindo and Karongi | **One sheet per fiscal year**, title row above the header, columns in a different order, `March 2024` dates |
| `SYNTHETIC_beneficiary_register_FO0n.xlsx` (4 files) | Register sheet (one row per registration) and Services sheet | Each officer writes names, sex, phones and dates differently: e.g. FO02 splits surname/first name and uses date of birth; FO03 uses `Gore`/`Gabo` and `Yego`/`Oya`; FO04 stores phones and IDs as numbers, so the leading zero and the last ID digit are lost |
| `SYNTHETIC_digitised_paper_records.xlsx` | Activities, Registrations and Services typed from paper forms | Higher missingness, every date format, `O` typed for `0`, swapped digits, misspelt villages and names, sex coded `1` |
| `SYNTHETIC_indicator_reports_WASH.xlsx`, `..._AGRI.xlsx` | Monthly indicator reports, one sheet per fiscal year | Column names change between years; indicator names in FY2023/24, codes later; missing targets; an extra zero typed; percentages above 100 or typed as fractions; some monthly reports never submitted |
| `SYNTHETIC_donor_opportunity_tracker.xlsx` | Donors and Opportunities | Individual donors' names, contact details, stage spellings (`CN submitted`, `Won`), amounts in USD or with `RWF`, probabilities as `60%`, `60`, `0.6` or `High` |

Volumes: 2,894 activity records, 1,500 people (1,566 registrations including 66 duplicates),
4,475 services, 615 indicator report rows (417 reports expected, 16 not submitted),
25 donors (6 individuals) and 30 opportunities.

### `data/ground_truth/`: the answer key (the pipeline must NEVER read this)

| File | Use |
|---|---|
| `SYNTHETIC_injected_errors_log.csv` | One line per injected problem: file, sheet, Excel row, column, true value, messy value, error type and expected handling |
| `SYNTHETIC_injected_errors_summary.csv` | Counts by entity, error type and expected handling |
| `SYNTHETIC_injected_errors_by_file.csv` | Counts by file and error type |
| `SYNTHETIC_truth_*.csv` | The true, clean version of every table, each row with the file, sheet and Excel row it was written to |

Expected handling means:

- **fix**: the pipeline should correct it automatically (e.g. `Gore` → female, `45363` → 12/03/2024).
- **flag**: the pipeline should send it for review (e.g. sex `1`, 120% female participation).
- **fix_or_flag**: either is acceptable (e.g. a district typo, `March 2024` with no day).
- **undetectable**: cannot be caught without the paper form (e.g. a misspelt name). Excluded from the 95% target.

## Injected problems (current seed)

| Brief Section 6 problem | Error types in the log | Count |
|---|---|---|
| Mixed date formats | `date_dmy_text`, `date_excel_serial`, `date_month_year_text`, `date_out_of_window` | 3,949 / 2,203 / 605 / 22 |
| District variants and typos | `district_variant`, `district_typo`, `district_wrong_province`, `province_variant` | 753 / 191 / 22 / 1,175 |
| Sex coding | `sex_variant` (F, f, Female, Gore, Gabo...), `sex_ambiguous_code_1` | 1,020 / 13 |
| Duplicate beneficiaries | `duplicate_beneficiary` (spelling, name order, phone changes) | 66 |
| Missing targets, impossible values | `missing_target`, `negative_value`, `female_exceeds_total`, `percent_over_100`, `sum_mismatch`, `accuracy_outlier`, `impossible_age`, `impossible_household_size` | 46 / 28 / 36 / 4 / 102 / 5 / 7 / 10 |
| Numbers as text, separators, RWF suffixes | `number_as_text`, `amount_in_usd`, `percent_as_fraction`, `phone_leading_zero_lost`, `id_stored_as_number` | 1,612 / 3 / 5 / 277 / 277 |
| Paper records | `missing_required` (all files), `transcription_error` | 141 / 43 |
| Timeliness (added) | `late_entry`, `status_completed_but_late`, `missing_monthly_report` | 328 / 100 / 16 |
| Layout | `title_row`, `merged_header_row`, `totals_row`, `blank_row`, `duplicate_activity_row` | 14 / 1 / 7 / 85 / 55 |
| Personal data to remove | `personal_data_individual_donor`, `personal_data_contact` | 6 / 25 |

Total: 15,085 logged problems (13,019 fix, 1,224 flag, 823 fix-or-flag, 19 undetectable).
The 19 undetectable ones are 5 misspelt names in the paper file and 14 activities in the paper file
marked "completed" although they were late: the paper form has no planned date, so lateness cannot be seen.
The exact counts are rewritten to `SYNTHETIC_injected_errors_summary.csv` on every run.

The error log has a `field` column naming the standard field (e.g. `total`, `district`) each problem is in,
so the scoring script can compare it with the cleaned table.

## How the cleaning is scored

`python src/score_cleaning.py` (also run by `pipeline.py` while `synthetic_mode` is on) compares the
cleaned tables with the answer key and writes `docs/phase2_cleaning_scorecard.md`. Problems are grouped
in `config/synthetic.yaml` (`error_groups`) into **officer habits**, **genuine errors** and **privacy**.

## Held-out test set

```
python src/generate_synthetic.py --holdout            # create it in data/holdout/
python src/generate_synthetic.py --holdout --verify   # check your copy
```

Expected content fingerprint: `1f90c10f3c03ff3426aeb3851de7077dc27ed15649b376fdf07bf48a73674928`.

`config/synthetic_holdout.yaml` starts from the main settings with a different seed (7919) and adds
mess the cleaner was not built for: a fifth officer (FO05, Huye) with column names the pipeline has
never seen; dates like `12 Mar 24`, `12 March 2024`, `12.03.2024`; new district spellings (`Rurindo`,
`Gayonza`, `Nyag.`, `Dist. Huye`, old names such as `Butare`); harder duplicates (names swapped between
columns, letters missing, nicknames such as `Jado`, `Manu`, `JC`, mostly without phone or ID); and 61
different people who share a name, district and sex. None of this changes the main set: its fingerprint
is the same as before.

**Rule:** do not change the cleaner or the mappings because of what this set contains until the team has
reviewed the results (decision log D64). The pipeline step `score_cleaning.py` runs the unchanged pipeline
on it and reports it next to the main set in `docs/phase2_cleaning_scorecard.md`.

## Hand-made test files

See `data/holdout/manual/README.md`. Teammates add their own messy files and an answer key; the scorer
picks them up automatically.
