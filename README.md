# ARDE/KUBAHO MEAL and Donor Analytics Prototype

A small, free tool that turns ARDE/KUBAHO's Excel and paper records into a clean, documented
dataset, MEAL indicators and a dashboard.

> **Demonstration data.** Everything in this prototype currently runs on synthetic records,
> not ARDE/KUBAHO data. Synthetic files always start with `SYNTHETIC_`.

**Status: Phase 1 of 8** (folders, settings, Excel templates and synthetic data). The dashboard
comes in Phase 5. A full user guide for staff comes in Phase 7.

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

This builds the Excel templates and creates the synthetic data. Later phases will add
cleaning, data-quality checks, indicators and the dashboard to the same command.

## Where things are

| Folder | What it holds |
|---|---|
| `config/` | All settings and rules, in plain text you can edit (no code) |
| `templates/` | Standard Excel entry templates for staff |
| `data/raw/` | Input Excel files (synthetic for now) |
| `data/ground_truth/` | Answer key for the synthetic data (testing only) |
| `src/` | The Python scripts |
| `docs/` | Decision log and guides |
| `tests/` | Automatic checks (`python -m pytest`) |

See `docs/synthetic_data.md` for what the synthetic files contain and `docs/decision_log.md`
for every assumption made so far.
