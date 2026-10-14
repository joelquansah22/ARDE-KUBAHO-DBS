# Synthetic data guide

**Everything described here is invented.** It is demonstration data, not ARDE/KUBAHO data.

## How to create it

```
python src/generate_synthetic.py
```

It takes about 6 seconds. The seed is fixed (`config/synthetic.yaml`), so every run gives identical files.
The script deletes and recreates the `SYNTHETIC_*` files each time.

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
| Mixed date formats | `date_dmy_text`, `date_excel_serial`, `date_month_year_text`, `date_out_of_window` | 3,947 / 2,202 / 604 / 22 |
| District variants and typos | `district_variant`, `district_typo`, `district_wrong_province`, `province_variant` | 755 / 192 / 22 / 1,175 |
| Sex coding | `sex_variant` (F, f, Female, Gore, Gabo...), `sex_ambiguous_code_1` | 1,020 / 13 |
| Duplicate beneficiaries | `duplicate_beneficiary` (spelling, name order, phone changes) | 66 |
| Missing targets, impossible values | `missing_target`, `negative_value`, `female_exceeds_total`, `percent_over_100`, `sum_mismatch`, `accuracy_outlier`, `impossible_age`, `impossible_household_size` | 46 / 28 / 36 / 4 / 102 / 5 / 7 / 10 |
| Numbers as text, separators, RWF suffixes | `number_as_text`, `amount_in_usd`, `percent_as_fraction`, `phone_leading_zero_lost`, `id_stored_as_number` | 1,612 / 3 / 5 / 277 / 277 |
| Paper records | `missing_required` (all files), `transcription_error` | 141 / 43 |
| Timeliness (added) | `late_entry`, `status_completed_but_late`, `missing_monthly_report` | 337 / 100 / 16 |
| Layout | `title_row`, `merged_header_row`, `totals_row`, `blank_row`, `duplicate_activity_row` | 14 / 1 / 7 / 85 / 55 |
| Personal data to remove | `personal_data_individual_donor`, `personal_data_contact` | 6 / 25 |

Total: 15,093 logged problems (13,018 fix, 1,247 flag, 823 fix-or-flag, 5 undetectable).
The exact counts are rewritten to `SYNTHETIC_injected_errors_summary.csv` on every run.
