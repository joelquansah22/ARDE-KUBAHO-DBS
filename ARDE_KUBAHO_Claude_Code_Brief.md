# Build Brief for Claude Code: ARDE/KUBAHO MEAL and Donor Analytics Prototype

**How to use this file:** save it as `CLAUDE.md` in an empty project folder, open Claude Code in that folder, and start with the prompt in Section 12 ("Kick-off prompt"). Then work through the phases one at a time using the phase prompts. Do not ask Claude Code to build everything in one go.

---

## 1. Context

We are a team of three MS Business Analytics students (Arizona State University, W. P. Carey) doing an eight-week applied capstone project with **ARDE/KUBAHO**, a Rwandan nonprofit working in water, sanitation and hygiene (WASH), community livelihoods, sustainable agriculture and environmental protection.

Problems identified in early discussions (still to be validated with the partner):

1. Information is fragmented across Excel files and paper records.
2. There is no integrated monitoring, evaluation, accountability and learning (MEAL) system.
3. Donor and fundraising information is not managed in a structured way.

**What we are building:** a scoped, working data-to-decision prototype for one pilot programme. It is not an organisation-wide MIS and not a production CRM.

The prototype must show:

- a reproducible pipeline that takes messy Excel and digitised paper records and produces a clean, documented dataset;
- a MEAL indicator catalogue with clear definitions and calculation rules;
- an interactive dashboard (programme performance, target versus actual, geography, data quality);
- a small donor/opportunity tracking module;
- before/after evidence that the prototype improves data quality and reporting time.

## 2. Hard constraints

- **Low cost and maintainable by NGO staff with Excel skills.** Free and open-source tools only. No paid cloud services. Must run on an ordinary Windows laptop.
- **Excel stays the front door.** Staff keep entering data in standardised Excel templates. The pipeline reads those templates. Do not make staff learn a database.
- **No real data yet.** Partner data access is pending. Build everything on **synthetic data that is clearly labelled as synthetic** (in file names, dashboard banner and docs). The pipeline must be designed so real files can be dropped in later with no code changes beyond a config file.
- **Privacy by design.** Beneficiary and donor names, phone numbers and national ID numbers must never reach the dashboard. Pseudonymise at ingestion with salted hashes. Treat Rwanda's Law No. 058/2021 on the protection of personal data and privacy as the governing standard, and note in the docs that the team must confirm obligations with the partner and the university.
- **Power BI compatibility.** The proposal names Power BI as the preferred dashboard tool. Build the working prototype dashboard in **Streamlit** (free, scriptable, testable), and also export a clean star schema as CSV/Parquet so the same model can be loaded into Power BI if the partner prefers it. Include a short guide for that.
- **British English** in all user-facing text and documentation.
- **Currency** in Rwandan francs (RWF), with optional USD display using a configurable exchange rate.

## 3. Technical stack

| Layer | Tool |
|---|---|
| Language | Python 3.11+ |
| Data processing | pandas, openpyxl |
| Storage / SQL | DuckDB (single file, no server) |
| Validation | pandera (or plain pandas checks if simpler) |
| Dashboard | Streamlit + Plotly |
| Maps | Plotly choropleth or scatter on Rwanda district boundaries (use a public GeoJSON if available offline; otherwise fall back to a bar chart by district) |
| Tests | pytest |
| Packaging | `requirements.txt`, plus a one-click `run_dashboard.bat` for Windows and `run_dashboard.sh` for Mac/Linux |

Keep dependencies minimal. No Docker requirement.

## 4. Repository structure

```
arde-meal-prototype/
├── CLAUDE.md                     # this brief
├── README.md                     # how to install and run, written for NGO staff
├── config/
│   ├── settings.yaml             # paths, pilot programme, exchange rate, salt location
│   └── indicator_catalogue.yaml  # MEAL indicator definitions (source of truth)
├── templates/                    # standardised Excel entry templates for staff
│   ├── activity_monitoring_template.xlsx
│   ├── beneficiary_register_template.xlsx
│   └── donor_opportunity_template.xlsx
├── data/
│   ├── raw/                      # messy input (synthetic for now)
│   ├── staging/                  # after cleaning, before modelling
│   ├── warehouse/arde.duckdb     # modelled data
│   └── exports/                  # CSV/Parquet star schema for Power BI
├── src/
│   ├── generate_synthetic.py     # creates realistic messy test data
│   ├── ingest.py                 # read Excel files, pseudonymise, stage
│   ├── clean.py                  # standardise dates, codes, names, units
│   ├── validate.py               # data-quality rules, writes DQ report
│   ├── model.py                  # build star schema in DuckDB
│   ├── indicators.py             # compute MEAL indicators from catalogue
│   ├── evaluate.py               # before/after data-quality metrics
│   └── pipeline.py               # runs everything end to end
├── dashboard/
│   ├── app.py
│   └── pages/
│       ├── 1_Programme_Overview.py
│       ├── 2_Indicators.py
│       ├── 3_Geography.py
│       ├── 4_Data_Quality.py
│       └── 5_Donor_Pipeline.py
├── docs/
│   ├── data_dictionary.md
│   ├── indicator_reference_sheets.md
│   ├── data_quality_report.md    # auto-generated
│   ├── user_guide.md
│   ├── maintenance_guide.md
│   ├── power_bi_guide.md
│   └── privacy_and_governance.md
└── tests/
```

## 5. Data model

Build a simple star schema in DuckDB.

**Dimensions**

- `dim_programme` (programme_id, name, thematic_area [WASH, Livelihoods, Agriculture, Environment], funder_id, start_date, end_date, status)
- `dim_project` (project_id, programme_id, name, budget_rwf, start_date, end_date)
- `dim_activity` (activity_id, project_id, activity_name, activity_type)
- `dim_location` (location_id, province, district, sector, cell, village). Use Rwanda's real administrative hierarchy: 5 provinces (Kigali City, Northern, Southern, Eastern, Western) and their 30 districts. Sector and below can be synthetic.
- `dim_indicator` (indicator_id, code, name, level [output, outcome], unit, direction [higher_is_better], disaggregation, frequency, owner, data_source)
- `dim_date` (date, month, quarter, year, Rwanda fiscal year July to June)
- `dim_beneficiary` (beneficiary_key [hashed], sex, age_band, household_size, disability_flag, location_id). No names, phones or ID numbers.
- `dim_donor` (donor_key, donor_name [organisations only, not individuals], donor_type [bilateral, multilateral, foundation, government, private, individual], country, thematic_interests)

**Facts**

- `fact_indicator_result` (indicator_id, project_id, location_id, period_date, target_value, actual_value, disaggregation_key, source_file, source_row, entered_by, quality_flag)
- `fact_activity` (activity_id, location_id, date, participants_total, participants_female, participants_male, cost_rwf)
- `fact_beneficiary_service` (beneficiary_key, activity_id, date, service_type)
- `fact_opportunity` (opportunity_id, donor_key, title, thematic_fit, stage, deadline, requested_amount_rwf, awarded_amount_rwf, probability, owner, next_action, next_action_date)

Every fact row must keep lineage (`source_file`, `source_row`) so any number on the dashboard can be traced back to its original record.

## 6. Synthetic data (critical for the demo)

`generate_synthetic.py` must create data that looks like what a small Rwandan NGO actually holds, including the mess, so the pipeline has something real to fix. Use a fixed random seed.

Create:

- 2 programmes (one WASH, one sustainable agriculture/climate resilience), 4 to 6 projects, 3 years of monthly records, 6 to 8 districts.
- About 1,500 beneficiaries, about 3,000 activity records, about 25 donors and 30 opportunities.
- Several Excel files with **inconsistent layouts** across "field officers" (different column names, merged header rows, totals rows at the bottom, extra blank rows).

Deliberately inject these problems at known rates, and log the injected counts so we can check the pipeline catches them:

- mixed date formats (`12/03/2024`, `2024-03-12`, `March 2024`, Excel serial numbers)
- district name variants and typos (`Nyagatare`, `NYAGATARE`, `Nyagatare District`, `Nyagatre`)
- sex coded as `F`, `Female`, `Gore`, `f`, `1` (include Kinyarwanda variants: `Gabo` = male, `Gore` = female)
- duplicate beneficiaries with slightly different spellings
- missing targets, negative or impossible values (for example, 120% female participation)
- numbers stored as text, thousands separators, `RWF` suffixes
- a "digitised paper records" file with higher missingness and transcription errors

Label every synthetic file with the prefix `SYNTHETIC_` and add a banner on every dashboard page: "Demonstration data. Synthetic records, not ARDE/KUBAHO data."

## 7. MEAL indicator catalogue

Store indicators in `config/indicator_catalogue.yaml` so staff can add or edit indicators without touching code. Each entry has: code, name, definition, level, unit, numerator, denominator, calculation rule, disaggregation, target-setting rule, frequency, data source, owner, direction, and notes.

Seed it with around 10 to 12 plausible indicators, for example:

**WASH**
- Number of people with access to improved water sources (output)
- Number of household latrines constructed or rehabilitated (output)
- % of trained households practising handwashing with soap (outcome)
- Number of water user committees established and functional (output)

**Agriculture / climate resilience**
- Number of farmers trained in climate-smart agriculture, disaggregated by sex (output)
- Hectares under solar-powered or improved irrigation (output)
- % of supported farmers reporting yield increase (outcome)
- Number of cooperatives formed or strengthened (output)

**Cross-cutting**
- % of participants who are women
- % of planned activities completed on time
- Cost per beneficiary reached (RWF)
- Reporting completeness: % of expected monthly reports submitted

Mark these clearly as **draft, for co-design with ARDE/KUBAHO staff**. `docs/indicator_reference_sheets.md` must be generated from the YAML.

## 8. Data-quality framework

`validate.py` runs rules and writes results to a `dq_results` table and `docs/data_quality_report.md`. Rules must cover the six standard dimensions:

| Dimension | Example rules |
|---|---|
| Completeness | required fields present; % of expected monthly reports received |
| Validity | dates in project window; sex in allowed set; percentages 0 to 100; non-negative counts |
| Consistency | female + male = total participants; district belongs to the stated province |
| Uniqueness | no duplicate beneficiaries after fuzzy matching; no duplicate activity rows |
| Timeliness | days between activity date and data entry date |
| Accuracy (proxy) | actual > 3x target flagged for review |

Rows that fail critical rules go to a **quarantine** table with the reason, not silently dropped. The dashboard must show how many records were quarantined and why.

## 9. Dashboard requirements

Audience: programme managers, the executive director and the MEAL officer. Assume low bandwidth and modest laptops. Keep it fast, clear and printable.

Global filters in the sidebar: programme, project, district, date range, sex.

1. **Programme Overview:** headline KPI cards (beneficiaries reached, activities completed, % women, budget spent), target versus actual by project, trend over time.
2. **Indicators:** one row per indicator with target, actual, % achieved, a traffic-light status (on track ≥ 90%, at risk 70 to 89%, off track < 70%, thresholds configurable), and a drill-down chart. Show the indicator definition on hover or in an expander.
3. **Geography:** results by district (map if boundaries are available, otherwise ranked bar chart).
4. **Data Quality:** overall quality score, score by dimension, by source file and by field officer, quarantined records, before/after comparison.
5. **Donor Pipeline:** opportunities by stage (funnel), upcoming deadlines in the next 30/60/90 days, weighted pipeline value (amount × probability), thematic fit with current programmes, overdue next actions.

Also provide:

- a **"Generate donor report"** button that produces a one-page quarterly progress summary (Excel and PDF) for a selected project. This is the task we will time before and after.
- a **download button** on every table.

## 10. Evaluation support

The proposal promises before/after evidence. Build tooling for it:

- `evaluate.py` computes data-quality metrics on the raw data (baseline) and on the cleaned data (prototype) for the same records and writes a comparison table: completeness, duplicate rate, invalid value rate, consistency failures.
- `docs/evaluation_protocol.md`: a script for timing the reporting task (manual Excel process versus prototype), and a short user-acceptance test with 5 to 8 tasks and a System Usability Scale (SUS) questionnaire.
- An `evaluation/` folder with blank templates for recording timings and SUS scores, and a small script that summarises them.

## 11. Working rules for Claude Code

- Work **phase by phase** (Section 13). At the end of each phase: run the tests, run the pipeline end to end, and give a short summary of what was built, what was assumed, and what needs a decision from us.
- **Ask before** adding any dependency not listed in Section 3, or changing the data model.
- Put every business rule (thresholds, allowed values, district lists, exchange rate) in config, not in code.
- Write docstrings and comments for a future maintainer who knows Excel but only a little Python.
- Keep a `docs/decision_log.md`: every assumption made, dated, with the reason.
- Never invent facts about ARDE/KUBAHO. Anything about the real organisation goes in the docs as "to be confirmed with partner".
- Write tests for: date parsing, district standardisation, sex recoding, duplicate detection, each data-quality rule, and each indicator calculation.

## 12. Kick-off prompt (paste this first)

> Read CLAUDE.md fully. Before writing any code, give me: (1) your understanding of the project in five bullet points, (2) any questions or conflicts you see in the brief, (3) a short plan for Phase 1. Wait for my go-ahead.

## 13. Build phases and prompts

Each phase maps to the eight-week plan in our proposal. Paste the prompt, review the output, then move on.

### Phase 1: Scaffold and synthetic data (supports Weeks 1 to 2)
> Set up the repository structure from Section 4, the requirements file and the config files. Then build `generate_synthetic.py` exactly as described in Section 6, including the injected-error log. Show me a sample of each messy file and the error counts.

**Done when:** the synthetic files open in Excel and look convincingly messy; error log exists.

### Phase 2: Ingestion, cleaning and pseudonymisation (Week 3)
> Build `ingest.py` and `clean.py`. Handle every mess type in Section 6. Pseudonymise beneficiary identifiers with a salted hash; the salt lives outside the repo. Write tests. Report how many of the injected errors were fixed, flagged or missed.

**Done when:** tests pass; at least 95% of injected errors are fixed or flagged; no personal identifiers in staging.

### Phase 3: Validation and data model (Week 4)
> Build `validate.py` (Section 8) with a quarantine table, and `model.py` to create the star schema in DuckDB (Section 5). Generate `docs/data_dictionary.md` automatically from the schema. Export the star schema to `data/exports/`. Build `pipeline.py` to run everything with one command.

**Done when:** `python src/pipeline.py` runs end to end in under a minute; data-quality report is generated.

### Phase 4: Indicators (Week 4 to 5)
> Build `indicator_catalogue.yaml` (Section 7) and `indicators.py`. Generate the indicator reference sheets. Each indicator must be traceable to the rows that produced it.

**Done when:** all seeded indicators compute; reference sheets generated; tests pass.

### Phase 5: Dashboard (Week 5)
> Build the Streamlit dashboard (Section 9), all five pages, global filters, synthetic-data banner and the donor report button. Keep page load under three seconds.

**Done when:** every page works with filters; donor report downloads as Excel and PDF.

### Phase 6: Donor module and polish (Week 6)
> Finish the Donor Pipeline page and the donor Excel template. Then review the whole dashboard as a busy programme manager would: remove clutter, fix labels, check British spelling, check it works on a 1366 × 768 screen.

### Phase 7: Evaluation tooling and documentation (Week 7)
> Build `evaluate.py` and the evaluation protocol (Section 10). Write the README, user guide, maintenance guide, Power BI guide and privacy and governance note. Write them for NGO staff, not developers.

### Phase 8: Real-data switch and handover (Week 8)
> Write a checklist for replacing synthetic data with real ARDE/KUBAHO files: which config entries to change, how to map new column names, how to rerun the pipeline, and how to remove the synthetic banner. Then do a final review of the whole repository and list known limitations and a prioritised roadmap.

## 14. Out of scope (do not build)

- Digitising all historical archives
- An organisation-wide MIS or user login system
- A production donor CRM, email integration or payment handling
- Causal impact estimates
- Predictive fundraising or forecasting models (unless we explicitly ask later, once we know the real sample size)

## 15. Open items to confirm with ARDE/KUBAHO and supervisors

These do not block the prototype, but record them in `docs/decision_log.md`:

- Which programme is the pilot
- Actual data sources, formats and record counts
- Data access authorisation and confidentiality terms
- Preferred dashboard tool (Streamlit, Power BI, or both)
- Whether the donor module is part of the assessed scope
- Where the prototype will be hosted after handover, and who maintains it
