# Power BI guide

The proposal names Power BI as the preferred dashboard tool. The working prototype dashboard is built in Streamlit
(free and testable), and **every table behind it is also exported** so the same model can be loaded into
**Power BI Desktop** (free for Windows). Which tool ARDE/KUBAHO uses after handover is still **to be confirmed with
the partner**.

> The exports contain **no names, phone numbers or ID numbers**: people appear only as coded keys. Do not publish a
> Power BI report to the web ("Publish to web") or share it outside ARDE/KUBAHO: see `docs/privacy_and_governance.md`.
> While the tool runs on synthetic data, keep the words "Demonstration data. Synthetic records, not ARDE/KUBAHO data."
> on every report page.

## 1. Where the files are

After every pipeline run (`python src/pipeline.py`), `data/exports/` holds each table twice:

- `<table>.parquet`: **use these in Power BI** (column types are kept: dates are dates, numbers are numbers);
- `<table>.csv`: the same data for Excel;
- `model_relationships.csv`: the list of relationships between the tables (below).

What each table and column means: `docs/data_dictionary.md`.

## 2. Load the tables (Power BI Desktop)

1. **Home > Get data > More... > Parquet** (or "Folder" to load them all at once and pick the ones you need).
2. Paste the full path of a file, for example `C:\ARDE\arde-meal-prototype\data\exports\fact_activity.parquet`.
3. Load at least these tables (the star schema):

| Kind | Tables |
|---|---|
| Facts (one row per event) | `fact_activity`, `fact_beneficiary_service`, `fact_indicator_result`, `fact_opportunity` |
| Dimensions (lookups) | `dim_date`, `dim_location`, `dim_programme`, `dim_project`, `dim_activity`, `dim_indicator`, `dim_beneficiary`, `dim_donor` |
| Ready-made results | `indicator_values` (indicator results by project, district and period, with target, % achieved, status), `indicator_reconciliation`, `dq_dimension_scores`, `dq_results`, `quarantine`, `review_queue` |

`indicator_values` is the simplest starting point for an indicator report: the calculation rules (aggregation, partial
targets, coverage) are already applied, the same as on the dashboard.

## 3. Relationships (Model view)

Power BI may guess some relationships; check them against `model_relationships.csv` and create the missing ones by
dragging the column from the first table onto the second. All are **many-to-one, single direction** (from the fact
to the dimension):

| From (many) | To (one) |
|---|---|
| `fact_activity[activity_id]` | `dim_activity[activity_id]` |
| `fact_activity[location_id]` | `dim_location[location_id]` |
| `fact_activity[date]` | `dim_date[date]` |
| `fact_beneficiary_service[beneficiary_key]` | `dim_beneficiary[beneficiary_key]` |
| `fact_beneficiary_service[activity_id]` | `dim_activity[activity_id]` |
| `fact_beneficiary_service[date]` | `dim_date[date]` |
| `fact_indicator_result[indicator_id]` | `dim_indicator[indicator_id]` |
| `fact_indicator_result[project_id]` | `dim_project[project_id]` |
| `fact_indicator_result[location_id]` | `dim_location[location_id]` |
| `fact_indicator_result[period_date]` | `dim_date[date]` |
| `fact_opportunity[donor_key]` | `dim_donor[donor_key]` |
| `dim_activity[project_id]` | `dim_project[project_id]` |
| `dim_project[programme_id]` | `dim_programme[programme_id]` |
| `dim_beneficiary[location_id]` | `dim_location[location_id]` |
| `indicator_values[indicator_id]` | `dim_indicator[indicator_id]` |

Mark `dim_date` as the date table (**Table tools > Mark as date table**, column `date`). Its `fiscal_year` column
follows ARDE/KUBAHO's July-to-June year.

## 4. Measures that match the dashboard

Create these with **New measure**. They follow the same definitions as the dashboard (`src/measures.py`); if a
definition changes there, change it here too.

```DAX
People reached = DISTINCTCOUNT ( fact_beneficiary_service[beneficiary_key] )

Activities completed =
CALCULATE ( COUNTROWS ( fact_activity ), fact_activity[status] IN { "completed", "delayed" } )

Activity spending (RWF) =
CALCULATE ( SUM ( fact_activity[cost_rwf] ), fact_activity[status] IN { "completed", "delayed" } )

% women =
DIVIDE (
    CALCULATE ( [People reached], dim_beneficiary[sex] = "female" ),
    CALCULATE ( [People reached], NOT ISBLANK ( dim_beneficiary[sex] ) )
)

People pending duplicate review =
CALCULATE ( [People reached], dim_beneficiary[pending_duplicate_review] = TRUE () )

Weighted pipeline (RWF) =
SUMX (
    FILTER ( fact_opportunity, fact_opportunity[stage] IN { "Identified", "Qualified", "Concept note", "Proposal submitted" } ),
    fact_opportunity[requested_amount_rwf] * fact_opportunity[probability]
)
```

Notes:
- **People are counted with DISTINCTCOUNT, never summed**: adding district totals of people is right only because
  each person has one registration district.
- **Indicator results:** use `indicator_values` filtered to one `period_type` (month, quarter or fiscal_year), one
  `source` (reported or derived), one `disaggregation` (usually "total"), and `district` = "All" for project totals.
  Do not add up quarters to get a year: the year rows are already worked out with the right aggregation (sum, latest,
  average or ratio).
- **Statuses** are words in `indicator_values[status]` (on track, at risk, off track, target incomplete, no target
  set, no data). Show the word next to any colour.
- An opportunity tagged "WASH; Agriculture" belongs to both themes: to split values by theme as the dashboard does,
  give each theme half (or build a small bridge table).

## 5. Refreshing

After each pipeline run, open the Power BI file and click **Home > Refresh**. The file paths must stay the same; if
the project folder moves, update them under **Transform data > Data source settings**.

## 6. What is not exported

Names, phone numbers, ID numbers and dates of birth never leave the reading step; the salt is never exported. The
staging folder's change log (`data/staging/issues.parquet`) and the synthetic answer key are for testing and should
not be loaded into a report for staff or donors.
