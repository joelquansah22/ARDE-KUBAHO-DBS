"""Build the star schema in DuckDB, export it for Power BI and write the data dictionary.

WHAT THIS SCRIPT DOES
---------------------
1. Builds the warehouse data/warehouse/arde.duckdb (a single file; no server) from the
   cleaned tables in data/staging/:
     dimensions  dim_programme, dim_project, dim_activity, dim_location, dim_indicator,
                 dim_date, dim_beneficiary, dim_donor
     facts       fact_activity, fact_beneficiary_service, fact_indicator_result,
                 fact_opportunity
     data quality dq_results, dq_dimension_scores, dq_by_source_file, dq_by_field_officer,
                 quarantine, review_queue, skipped_sheets, dq_info_measures, report_completeness
   Every fact row keeps its lineage (source_file, source_sheet, source_row), so any number
   can be traced back to the Excel row it came from. Rows in the quarantine table are NOT
   in the fact tables.
2. Checks the model before saving it: unique keys, every link points to an existing row,
   no personal-data columns, lineage on every fact row. If a check fails, it stops with a
   message rather than save a broken model.
3. Exports every table to data/exports/ as CSV (opens in Excel) and Parquet (for Power BI),
   with model_relationships.csv listing how the tables link.
4. Writes docs/data_dictionary.md from config/data_dictionary.yaml and the real schema.

HOW TO RUN
    python src/model.py      (after validate.py; pipeline.py runs everything in order)
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import duckdb
import pandas as pd

from common import district_to_province, fiscal_year_label, load_settings, load_yaml, resolve_path

POSITION = ["source_file", "source_sheet", "source_row"]
# Column names that would mean personal data had leaked into the warehouse.
PERSONAL_COLUMNS = {"name", "surname", "first_name", "phone", "national_id", "dob", "date_of_birth",
                    "contact_person", "email", "reg_no"}
# Tables whose "name" column names a thing (a programme, project or indicator), not a person.
NAMED_THINGS = {"dim_programme", "dim_project", "dim_indicator"}


class ModelError(Exception):
    """Raised when the model fails a check; nothing is saved."""


def _dates(series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce").dt.date


def _drop_quarantined(df: pd.DataFrame, quarantined: set) -> pd.DataFrame:
    keep = [(f, s, int(r)) not in quarantined for f, s, r in zip(df["source_file"], df["source_sheet"], df["source_row"])]
    return df[keep].copy()


class ModelBuilder:
    def __init__(self, staging=None):
        self.staging = Path(staging or resolve_path("staging"))
        self.settings = load_settings()
        self.dictionary = load_yaml("data_dictionary.yaml")
        read = lambda name: pd.read_parquet(self.staging / f"{name}.parquet")
        self.read = read
        q = read("dq_quarantine")
        self.quarantined = {(f, s, int(r)) for f, s, r in zip(q["source_file"], q["source_sheet"], q["source_row"])}
        self.review = read("dq_review_queue")
        # Worst severity of the problems on each kept row: warning > info > ok (critical rows are quarantined).
        issues = read("issues")
        issues = issues[issues["severity"].isin(["info", "warning"]) & issues["source_row"].notna()]
        rank = issues.assign(rank=issues["severity"].map({"info": 1, "warning": 2}))
        worst = rank.groupby(POSITION)["rank"].max()
        self.quality = {(f, s, int(r)): {1: "info", 2: "warning"}[v] for (f, s, r), v in worst.items()}

    def quality_flag(self, df: pd.DataFrame) -> list[str]:
        return [self.quality.get((f, s, int(r)), "ok")
                for f, s, r in zip(df["source_file"], df["source_sheet"], df["source_row"])]

    # ================================================================ dimensions
    def dim_programme(self) -> pd.DataFrame:
        df = self.read("ref_programme")
        donors = self.read("ingested_donor")
        key_of = dict(zip(donors["donor_id"], donors["donor_key"]))
        return pd.DataFrame(dict(
            programme_id=df["programme_id"], name=df["name"], thematic_area=df["thematic_area"],
            funder_id=df["funder_id"].map(key_of), start_date=_dates(df["start_date"]),
            end_date=_dates(df["end_date"]), status=df["status"]))

    def dim_project(self) -> pd.DataFrame:
        df = self.read("ref_project")
        return pd.DataFrame(dict(
            project_id=df["project_id"], programme_id=df["programme_id"], name=df["name"],
            budget_rwf=pd.to_numeric(df["budget_rwf"]), start_date=_dates(df["start_date"]),
            end_date=_dates(df["end_date"])))

    def dim_activity(self) -> pd.DataFrame:
        df = self.read("ref_activity")
        return df[["activity_id", "project_id", "activity_name", "activity_type"]].copy()

    def dim_location(self) -> pd.DataFrame:
        villages = self.read("ref_location")[["location_id", "province", "district", "sector", "cell", "village"]]
        villages = villages.assign(location_level="village")
        d2p = district_to_province()
        districts = sorted(set(villages["district"]) | set(self.read("clean_indicator_result")["district"].dropna()))
        district_rows = pd.DataFrame(dict(location_id=[f"DIST-{d}" for d in districts],
                                          province=[d2p[d] for d in districts], district=districts,
                                          sector=None, cell=None, village=None, location_level="district"))
        return pd.concat([villages, district_rows], ignore_index=True)

    def dim_indicator(self) -> pd.DataFrame:
        rows = []
        for i, ind in enumerate(load_yaml("indicator_catalogue.yaml")["indicators"], 1):
            rows.append(dict(indicator_id=i, code=ind["code"], name=ind["name"], level=ind.get("level"),
                             unit=ind.get("unit"), higher_is_better=bool(ind.get("higher_is_better")),
                             disaggregation=ind.get("disaggregation"), frequency=ind.get("frequency"),
                             owner=ind.get("owner"), data_source=ind.get("data_source") or ind.get("source"),
                             availability=ind.get("availability", "available")))
        return pd.DataFrame(rows)

    def dim_date(self, facts: dict) -> pd.DataFrame:
        window = self.settings["reporting_window"]
        candidates = [window["start"], window["end"]]
        for df, col in ((facts["fact_activity"], "date"), (facts["fact_activity"], "planned_date"),
                        (facts["fact_activity"], "entry_date"), (facts["fact_beneficiary_service"], "date"),
                        (facts["fact_indicator_result"], "period_date"), (facts["fact_opportunity"], "deadline"),
                        (facts["fact_opportunity"], "next_action_date")):
            candidates += [d for d in df[col].dropna()]
        start = dt.date(min(candidates).year, 1, 1)
        end = dt.date(max(candidates).year, 12, 31)
        days = pd.date_range(start, end, freq="D")
        return pd.DataFrame(dict(date=days.date, month=days.month, quarter=days.quarter, year=days.year,
                                 fiscal_year=[fiscal_year_label(d) for d in days.date]))

    def dim_beneficiary(self, services: pd.DataFrame) -> pd.DataFrame:
        regs = self.read("clean_registration")
        regs["quarantined"] = [(f, s, int(r)) in self.quarantined
                               for f, s, r in zip(regs["source_file"], regs["source_sheet"], regs["source_row"])]
        # Details from the person's earliest registration that passed the checks.
        good = regs[~regs["quarantined"]].sort_values(["registration_date", "source_file", "source_row"],
                                                      na_position="last").drop_duplicates("beneficiary_key")
        pending = self.read("dq_people_pending_review")
        pending_keys = set(pending.loc[pending["pending_duplicate_review"], "beneficiary_key"])
        dim = pd.DataFrame(dict(beneficiary_key=good["beneficiary_key"], sex=good["sex"], age_band=good["age_band"],
                                household_size=good["household_size"].astype("Int64"),
                                disability_flag=good["disability"].map({"yes": True, "no": False}),
                                location_id=good["location_id"]))
        # Village missing but district known: link to the district (so the person still counts in their district).
        district_only = dim["location_id"].isna() & good["district"].notna().values
        dim.loc[district_only, "location_id"] = "DIST-" + good.loc[district_only.values, "district"].values
        # People whose only registrations were quarantined still need a row, so that links work.
        others = (set(regs["beneficiary_key"]) | set(services["beneficiary_key"].dropna())) - set(dim["beneficiary_key"])
        if others:
            dim = pd.concat([dim, pd.DataFrame(dict(beneficiary_key=sorted(others)))], ignore_index=True)
        dim["pending_duplicate_review"] = dim["beneficiary_key"].isin(pending_keys)
        return dim.reset_index(drop=True)

    def dim_donor(self) -> pd.DataFrame:
        df = self.read("clean_donor")
        return df[["donor_key", "donor_name", "donor_type", "country", "thematic_interests"]].copy()

    # ================================================================ facts
    def fact_activity(self) -> pd.DataFrame:
        df = _drop_quarantined(self.read("clean_activity"), self.quarantined)
        # Counts are whole numbers (a fraction is a critical problem, so such rows are already quarantined;
        # astype fails loudly if one ever gets through).
        for col in ("participants_total", "participants_female", "participants_male"):
            df[col] = df[col].astype("Int64")
        df["quality_flag"] = self.quality_flag(df)
        df["on_time"] = df["on_time"].astype("boolean")
        return df[["activity_id", "location_id", "date", "participants_total", "participants_female",
                   "participants_male", "cost_rwf", "planned_date", "entry_date", "status", "on_time",
                   "officer_code", "quality_flag"] + POSITION].copy()

    def fact_beneficiary_service(self) -> pd.DataFrame:
        df = _drop_quarantined(self.read("clean_service"), self.quarantined)
        return df[["beneficiary_key", "activity_id", "date", "service_type"] + POSITION].copy()

    def fact_indicator_result(self, indicators: pd.DataFrame) -> pd.DataFrame:
        df = _drop_quarantined(self.read("clean_indicator_result"), self.quarantined)
        id_of = dict(zip(indicators["code"], indicators["indicator_id"]))

        return pd.DataFrame(dict(
            indicator_id=df["indicator_code"].map(id_of), project_id=df["project_id"],
            location_id="DIST-" + df["district"], period_date=df["period"], target_value=df["target_value"],
            actual_value=df["actual_value"], disaggregation_key=df["disaggregation_key"],
            source_file=df["source_file"], source_sheet=df["source_sheet"], source_row=df["source_row"],
            entered_by=df["entered_by"], officer_code=df["officer_code"], quality_flag=self.quality_flag(df)))

    def fact_opportunity(self) -> pd.DataFrame:
        df = _drop_quarantined(self.read("clean_opportunity"), self.quarantined)
        return df[["opportunity_id", "donor_key", "title", "thematic_fit", "stage", "deadline",
                   "requested_amount_rwf", "awarded_amount_rwf", "probability", "owner", "next_action",
                   "next_action_date"] + POSITION].copy()

    # ================================================================ build
    def tables(self) -> dict[str, pd.DataFrame]:
        dims = dict(dim_programme=self.dim_programme(), dim_project=self.dim_project(),
                    dim_activity=self.dim_activity(), dim_location=self.dim_location(),
                    dim_indicator=self.dim_indicator(), dim_donor=self.dim_donor())
        facts = dict(fact_activity=self.fact_activity(), fact_beneficiary_service=self.fact_beneficiary_service(),
                     fact_indicator_result=self.fact_indicator_result(dims["dim_indicator"]),
                     fact_opportunity=self.fact_opportunity())
        dims["dim_date"] = self.dim_date(facts)
        dims["dim_beneficiary"] = self.dim_beneficiary(facts["fact_beneficiary_service"])
        dq = dict(dq_results=self.read("dq_results"), dq_dimension_scores=self.read("dq_dimension_scores"),
                  dq_rule_results_by_file=self.read("dq_rule_results_by_file"),
                  dq_by_source_file=self.read("dq_by_source_file"), dq_by_field_officer=self.read("dq_by_field_officer"),
                  quarantine=self.read("dq_quarantine"), review_queue=self.read("dq_review_queue"),
                  skipped_sheets=self.read("dq_skipped_sheets"), dq_info_measures=self.read("dq_info_measures"),
                  report_completeness=self.read("clean_report_completeness"))
        out = {**dims, **facts, **dq}
        # Keep exactly the columns (and order) described in the data dictionary.
        for name, df in out.items():
            cols = list(self.dictionary["tables"][name]["columns"])
            missing = [c for c in cols if c not in df.columns]
            if missing:
                raise ModelError(f"{name} is missing columns described in the data dictionary: {missing}")
            extra = [c for c in df.columns if c not in cols]
            if extra:
                raise ModelError(f"{name} has columns not described in config/data_dictionary.yaml: {extra}")
            out[name] = df[cols].reset_index(drop=True)
        return out

    # ================================================================ checks
    def check(self, tables: dict[str, pd.DataFrame]) -> list[str]:
        """Return a list of problems (empty if the model is sound)."""
        problems = []
        for name, spec in self.dictionary["tables"].items():
            if name not in tables:          # built by a later step (e.g. indicators.py)
                continue
            df = tables[name]
            key = spec["key"] if isinstance(spec["key"], list) else [spec["key"]]
            if len(df) and df.duplicated(key).any():
                problems.append(f"{name}: key {key} is not unique ({int(df.duplicated(key).sum())} repeats)")
            if spec["kind"] == "fact" and len(df) and df[[c for c in POSITION if c in df]].isna().any().any():
                problems.append(f"{name}: some rows have no lineage")
            banned = PERSONAL_COLUMNS - ({"name"} if name in NAMED_THINGS else set())
            leaked = banned & set(df.columns)
            if leaked:
                problems.append(f"{name}: personal-data columns present: {sorted(leaked)}")
        # A fact table links to ONE level of location only, so a district total can never add a district
        # row to its own villages (data_dictionary.yaml: location_level on the fact table).
        levels = dict(zip(tables["dim_location"]["location_id"], tables["dim_location"]["location_level"]))
        for name, spec in self.dictionary["tables"].items():
            if spec.get("location_level") and name in tables:
                found = {levels.get(v) for v in tables[name]["location_id"].dropna()}
                if found - {spec["location_level"]}:
                    problems.append(f"{name}: links to location level(s) {sorted(found)}, "
                                    f"expected only {spec['location_level']}")
        for child, parent in self.dictionary["relationships"]:
            ct, cc = child.split(".")
            pt, pc = parent.split(".")
            if ct not in tables or pt not in tables:
                continue
            values = set(tables[ct][cc].dropna())
            known = set(tables[pt][pc].dropna())
            orphans = values - known
            if orphans:
                problems.append(f"{child} has {len(orphans)} value(s) not found in {parent}, e.g. {sorted(map(str, orphans))[:3]}")
        return problems


def save_warehouse(tables: dict[str, pd.DataFrame], path: Path) -> None:
    """Write all tables to a fresh DuckDB file (the old file is replaced)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".building.duckdb")
    for p in (tmp, Path(str(tmp) + ".wal")):
        if p.exists():
            p.unlink()
    con = duckdb.connect(str(tmp))
    try:
        for name, df in tables.items():
            con.register("frame", df)
            con.execute(f"CREATE TABLE {name} AS SELECT * FROM frame")
            con.unregister("frame")
    finally:
        con.close()
    for p in (path, Path(str(path) + ".wal")):
        if p.exists():
            p.unlink()
    tmp.replace(path)


def export(tables: dict[str, pd.DataFrame], folder: Path, relationships: list, clear: bool = True) -> None:
    """CSV (UTF-8 with BOM so Excel shows accents correctly) and Parquet copies of every table."""
    folder.mkdir(parents=True, exist_ok=True)
    if clear:
        for old in list(folder.glob("*.csv")) + list(folder.glob("*.parquet")):
            old.unlink()
    for name, df in tables.items():
        df.to_csv(folder / f"{name}.csv", index=False, encoding="utf-8-sig")
        df.to_parquet(folder / f"{name}.parquet", index=False)
    rel = pd.DataFrame([dict(from_table=c.split(".")[0], from_column=c.split(".")[1],
                             to_table=p.split(".")[0], to_column=p.split(".")[1], cardinality="many-to-one")
                        for c, p in relationships])
    rel.to_csv(folder / "model_relationships.csv", index=False, encoding="utf-8-sig")


def write_dictionary(path_db: Path, dictionary: dict, docs: Path) -> None:
    """docs/data_dictionary.md, from the real schema (types, row counts) and the descriptions."""
    con = duckdb.connect(str(path_db), read_only=True)
    try:
        schema = con.execute("SELECT table_name, column_name, data_type FROM information_schema.columns "
                             "ORDER BY table_name, ordinal_position").df()
        present = set(schema["table_name"])
        counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in dictionary["tables"] if t in present}
    finally:
        con.close()
    settings = load_settings()
    lines = ["# Data dictionary", ""]
    if settings.get("synthetic_mode"):
        lines += [f"> **{settings['synthetic_banner']}**", ""]
    lines += [f"*Generated by `src/model.py` on {dt.date.today():%d %B %Y} from the warehouse "
              "(`data/warehouse/arde.duckdb`) and `config/data_dictionary.yaml`. Do not edit by hand: change the "
              "YAML file instead.*", "",
              "The warehouse is a star schema: **fact** tables hold events and results; **dimension** tables "
              "describe them (what, where, when, who). Every fact row has `source_file`, `source_sheet` and "
              "`source_row`, so any number can be traced to the Excel row it came from. Rows that broke a critical "
              "data-quality rule are in `quarantine`, not in the facts. The same tables are exported to "
              "`data/exports/` as CSV and Parquet for Power BI.", "",
              "No table holds names, phone numbers or national ID numbers. People and donors are identified by "
              "salted hashes (`beneficiary_key`, `donor_key`).", "",
              "## Tables", "",
              "| Table | Kind | Rows | Key | Description |", "|---|---|---|---|---|"]
    for name, spec in dictionary["tables"].items():
        key = ", ".join(spec["key"]) if isinstance(spec["key"], list) else spec["key"]
        rows = f"{counts[name]:,}" if name in counts else "not built yet"
        lines.append(f"| `{name}` | {spec['kind']} | {rows} | {key} | {' '.join(spec['description'].split())} |")
    lines += ["", "## How the tables link", "", "| From | To |", "|---|---|"]
    lines += [f"| `{c}` | `{p}` |" for c, p in dictionary["relationships"]]
    for name, spec in dictionary["tables"].items():
        if name not in counts:
            continue
        cols = schema[schema["table_name"] == name]
        lines += ["", f"## `{name}`", "", " ".join(spec["description"].split()), "",
                  f"Rows: {counts[name]:,}. Key: {', '.join(spec['key']) if isinstance(spec['key'], list) else spec['key']}.", "",
                  "| Column | Type | Description |", "|---|---|---|"]
        for c in cols.itertuples():
            lines.append(f"| `{c.column_name}` | {c.data_type} | {spec['columns'][c.column_name]} |")
    (docs / "data_dictionary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(staging=None, warehouse=None, exports=None, docs=None) -> dict:
    builder = ModelBuilder(staging)
    tables = builder.tables()
    problems = builder.check(tables)
    if problems:
        raise ModelError("The model failed its checks, so nothing was saved:\n  - " + "\n  - ".join(problems))
    warehouse = Path(warehouse or resolve_path("warehouse"))
    save_warehouse(tables, warehouse)
    export(tables, Path(exports or resolve_path("exports")), builder.dictionary["relationships"])
    write_dictionary(warehouse, builder.dictionary, Path(docs or resolve_path("docs")))
    return tables


def main():
    tables = run()
    facts = {n: len(t) for n, t in tables.items() if n.startswith("fact_")}
    print("Warehouse built: " + ", ".join(f"{n} {c:,}" for n, c in facts.items())
          + f"; quarantined rows kept aside: {len(tables['quarantine']):,}. Exports in data/exports/.")


if __name__ == "__main__":
    main()
