# ARDE/KUBAHO MEAL and Donor Analytics Prototype

A small, free tool that turns ARDE/KUBAHO's Excel and paper records into a clean, documented
dataset, MEAL indicators and a dashboard.

> **Demonstration data.** Everything in this prototype currently runs on synthetic records,
> not ARDE/KUBAHO data. Synthetic files always start with `SYNTHETIC_`.

**Status: Phase 4 of 8** (templates, synthetic data, reading, cleaning and pseudonymising the
records, data-quality checks, the data warehouse, exports for Power BI, and the MEAL indicators).
The dashboard comes in Phase 5. A full user guide for staff comes in Phase 7.

## First-time set-up (Windows)

1. Install Python 3.11 or newer from python.org (tick "Add Python to PATH").
2. Open this folder, click the address bar, type `cmd` and press Enter.
3. Type these commands one at a time:

```
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Everyday use

```
.venv\Scripts\activate
python src/pipeline.py
```

This is the production run. It reads every Excel file in `data/raw/`, pseudonymises and cleans the
records, checks data quality, and builds the warehouse. It takes about 15 seconds and produces:

- `docs/data_quality_report.md`: skipped sheets, scores, quarantined records and the review queue;
- `data/warehouse/arde.duckdb`: the data warehouse (one file);
- `data/exports/`: every table as CSV (opens in Excel) and Parquet (for Power BI);
- `docs/data_dictionary.md`: what every table and column means;
- the indicator values, the reported-versus-derived reconciliation, and the indicator reference sheets
  (`docs/indicator_reference_sheets.md`, plus an Excel version with a Staff comments column for the
  co-design session).
 A file whose columns are not recognised is **skipped** with a message
listing its column names; add them to `config/source_mappings.yaml` and run it again.

Other commands (not part of the production run):

| Command | What it does |
|---|---|
| `python src/generate_synthetic.py` | Create the synthetic demonstration data (`--verify` checks your copy) |
| `python src/build_templates.py` | Rebuild the Excel entry templates (only if their settings changed) |
| `python src/pipeline.py --score` | Production run, then score the cleaning against the synthetic answer keys |
| `python src/score_cleaning.py` | Score the cleaning on the main and held-out test sets (testing only) |

The first run creates a secret "salt" file in your user folder (`.arde_meal\pseudonymisation_salt.txt`)
that protects people's identities. **Back it up**: without it, new records will not link to old ones.

## Where things are

| Folder | What it holds |
|---|---|
| `config/` | All settings and rules, in plain text you can edit (no code). New file layouts: `source_mappings.yaml` |
| `templates/` | Standard Excel entry templates for staff |
| `data/raw/` | Input Excel files (synthetic for now) |
| `data/staging/` | Cleaned tables with no names, phones or ID numbers, plus the log of every change and flag |
| `data/warehouse/` | The data warehouse (`arde.duckdb`) |
| `data/exports/` | CSV and Parquet copies of every warehouse table, for Excel and Power BI |
| `data/ground_truth/` | Answer key for the synthetic data (testing only) |
| `src/` | The Python scripts |
| `docs/` | Decision log and guides |
| `tests/` | Automatic checks (`python -m pytest`) |

See `docs/synthetic_data.md` for what the synthetic files contain and `docs/decision_log.md`
for every assumption made so far.
