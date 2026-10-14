# Hand-made test files: please add some mess we have not thought of

The cleaning pipeline has been tested on synthetic files that the same team wrote the cleaner for,
and on a held-out synthetic set. Neither is as unpredictable as a real person filling in Excel.
**This folder is for messy files made by hand by someone who did not write the cleaner.**

## What to do (about 30 minutes)

1. Open a file from `data/raw/` (for example `SYNTHETIC_activity_monitoring_FO01.xlsx` or a
   beneficiary register) or one of the blank templates in `templates/`.
2. Save a copy in `data/holdout/manual/raw/`. **Start the file name with `SYNTHETIC_MANUAL_`** and keep a
   recognisable kind of file in the name, e.g. `SYNTHETIC_MANUAL_activity_monitoring_JQ.xlsx` or
   `SYNTHETIC_MANUAL_beneficiary_register_JQ.xlsx` (the pipeline uses the name to know what the file holds).
3. Make it messy the way a busy field officer might. Ideas: rename columns, add notes in cells, write
   dates your own way, misspell districts and villages, merge cells, add subtotals, type "approx 40",
   leave things blank, register someone twice with a nickname. **Use invented people only.**
4. For every cell you changed, add a line to `answer_key.csv` in this folder (copy
   `answer_key_template.csv`). Also add a few lines for cells you did **not** change, with
   `error_type` left empty: these check that the pipeline does not "correct" good values.

## answer_key.csv columns

| Column | What to write |
|---|---|
| `source_file` | the file name, e.g. `SYNTHETIC_MANUAL_activity_monitoring_JQ.xlsx` |
| `source_sheet` | the sheet name, e.g. `Activities` |
| `source_row` | the Excel row number (the grey number on the left) |
| `field` | the standard field: `date`, `planned_date`, `entry_date`, `project`, `activity`, `district`, `sector`, `cell`, `village`, `status`, `female`, `male`, `total`, `cost`, `sex`, `age`, `household_size`, `disability`, `reg_date`, `target`, `actual`, `period`, `indicator` |
| `true_value` | what the cell **should** say, in standard form: dates `2024-03-12`; official district name; village name; project code `PRJ01`; activity code `ACT03`; sex `female`/`male`; status `completed`/`delayed`/`cancelled`/`planned`; plain numbers `1250000` |
| `error_type` | a short label of your choice, e.g. `nickname`, `odd_date`, `district_typo`; **empty** for an unchanged cell |
| `notes` | optional |

## What happens next

`python src/score_cleaning.py` picks these files up automatically and adds a "Hand-made test files"
section to `docs/phase2_cleaning_scorecard.md`: fixed / flagged / missed for each changed cell, and
any unchanged cell the pipeline wrongly altered. Nothing in this folder is ever committed to git
except this README and the template.
