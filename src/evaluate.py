"""Before/after evidence: data-quality measures on the RAW files versus the CLEANED data, for the same records.

WHAT THIS SCRIPT DOES
---------------------
For every row read from the Excel files (identified by source_file, source_sheet and source_row), it compares the
value as typed in the file ("raw", from the ingest step, before any cleaning) with the value after cleaning. Four
measures, the ones promised in the proposal:

  completeness       required fields that hold a USABLE value. Raw: anything typed (generous to the raw files).
                     Cleaned: a value the pipeline could read (an unreadable date becomes empty, so this can go DOWN).
  invalid values     non-blank cells that are NOT in a standard form a report can use directly: dates that are not
                     real Excel dates, sex/status/district not exactly in the code lists, numbers typed as text with
                     "RWF" or commas, negative or impossible numbers.
  consistency        activity rows where women + men differ from the total, or women exceed the total. Cleaned: only
                     the rows USED in reporting (quarantined rows are set aside until corrected).
  duplicates         activity rows typed twice; and how far a simple count of register rows overstates the number of
                     different people, against the true number of people (known from the synthetic answer key).

Results: docs/evaluation_before_after.md and evaluation/before_after.csv, for the main synthetic set and the
Phase 7 final held-out set (if it has been scored). Rules (code lists, required fields) come from config.

HOW TO RUN
    python src/evaluate.py          (after python src/pipeline.py; the final set after score_cleaning.py --final)
"""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

import pandas as pd

from common import PROJECT_ROOT, load_admin, load_settings, load_yaml, resolve_path

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}( 00:00:00)?$")
PLAIN_NUMBER = re.compile(r"^-?\d+(\.\d+)?$")
MONTH_LABEL = re.compile(r"^[A-Z][a-z]{2}-\d{2}$")          # "Jul-23", the report sheets' own month format

# raw column -> (cleaned column, kind of check). The raw names are the standard fields from source_mappings.yaml.
FIELDS = {
    "activity": {
        "date": ("date", "date"), "planned_date": ("planned_date", "date"), "entry_date": ("entry_date", "date"),
        "project": ("project_id", "project"), "activity": ("activity_id", "activity"),
        "district": ("district", "district"), "village": ("village", "text"), "status": ("status", "status"),
        "female": ("participants_female", "count"), "male": ("participants_male", "count"),
        "total": ("participants_total", "count"), "cost": ("cost_rwf", "amount")},
    "registration": {
        "sex": ("sex", "sex"), "age": ("age", "age"), "household_size": ("household_size", "household"),
        "district": ("district", "district"), "village": ("village", "text"), "project": ("project_id", "project"),
        "reg_date": ("registration_date", "date")},
    "indicator_result": {
        "project": ("project_id", "project"), "district": ("district", "district"),
        "period": ("period", "period"), "indicator": ("indicator_code", "text"),
        "target": ("target_value", "amount"), "actual": ("actual_value", "amount")},
}
LABELS = {"activity": "Activity records", "registration": "Beneficiary registrations",
          "indicator_result": "Indicator reports"}


def blank(v) -> bool:
    return v is None or (isinstance(v, float) and pd.isna(v)) or (isinstance(v, str) and not v.strip())


class Rules:
    """The standard forms, from config (settings.yaml, the admin reference and the programme master)."""

    def __init__(self, staging: Path):
        s = load_settings()
        self.districts = {d for ds in load_admin()["provinces"].values() for d in ds}
        self.sexes = {"female", "male", "Female", "Male"}             # the template's dropdown, either case
        self.statuses = set(s["activity_status_values"]) | {x.title() for x in s["activity_status_values"]}
        projects = pd.read_parquet(staging / "ref_project.parquet")
        activities = pd.read_parquet(staging / "ref_activity.parquet")
        self.projects = set(projects["project_id"]) | set(projects["name"])
        self.activities = set(activities["activity_id"]) | set(activities["activity_name"])

    def raw_valid(self, kind: str, v) -> bool:
        v = str(v).strip()
        if kind == "date":
            return bool(ISO_DATE.match(v))
        if kind == "period":
            return bool(ISO_DATE.match(v) or MONTH_LABEL.match(v))
        if kind in ("count", "amount"):
            return bool(PLAIN_NUMBER.match(v)) and float(v) >= 0
        if kind == "age":
            return bool(PLAIN_NUMBER.match(v)) and 0 <= float(v) <= 110
        if kind == "household":
            return bool(PLAIN_NUMBER.match(v)) and 1 <= float(v) <= 30
        if kind == "district":
            return v in self.districts
        if kind == "sex":
            return v in self.sexes
        if kind == "status":
            return v in self.statuses
        if kind == "project":
            return v in self.projects
        if kind == "activity":
            return v in self.activities
        return True

    @staticmethod
    def clean_valid(kind: str, v) -> bool:
        if blank(v):
            return False
        if kind in ("count", "amount"):
            return float(v) >= 0
        if kind == "age":
            return 0 <= float(v) <= 110
        if kind == "household":
            return 1 <= float(v) <= 30
        return True


def evaluate_set(name: str, staging: Path, truth: Path | None) -> pd.DataFrame:
    staging = Path(staging)
    rules = Rules(staging)
    required = load_yaml("source_mappings.yaml")["required_fields"]
    quarantine = pd.read_parquet(staging / "dq_quarantine.parquet")
    q_keys = set(zip(quarantine["source_file"], quarantine["source_sheet"], quarantine["source_row"].astype(int)))
    rows = []

    def add(entity, measure, raw, cleaned, how, n):
        rows.append(dict(set=name, records=LABELS.get(entity, entity), measure=measure, raw_files=raw,
                         after_cleaning=cleaned, records_compared=n, how_measured=how))

    for entity, fields in FIELDS.items():
        raw = pd.read_parquet(staging / f"ingested_{entity}.parquet")
        clean = pd.read_parquet(staging / f"clean_{entity}.parquet")
        key = ["source_file", "source_sheet", "source_row"]
        both = raw.merge(clean, on=key, how="left", suffixes=("", "__clean"), indicator=True)
        kept = both["_merge"] == "both"
        n = len(both)
        # --- completeness of the required fields
        req = [f if isinstance(f, str) else f[0] for f in required.get(entity, [])]
        req = [f for f in req if f in fields]
        filled_raw = sum((~both[f].map(blank)).sum() for f in req)
        filled_clean = 0
        for f in req:
            col = fields[f][0]
            col = col + "__clean" if col in raw.columns else col
            filled_clean += (kept & ~both[col].map(blank)).sum()
        total = n * len(req)
        add(entity, "Completeness: required fields usable (%)", round(100 * filled_raw / total, 1),
            round(100 * filled_clean / total, 1),
            f"{', '.join(req)}: raw = anything typed; cleaned = a value the pipeline could read", n)
        # --- invalid values among the non-blank cells
        checked = bad_raw = bad_clean = 0
        for f, (col, kind) in fields.items():
            if f not in both:
                continue
            col = col + "__clean" if col in raw.columns else col
            present = ~both[f].map(blank)
            checked += present.sum()
            bad_raw += sum(not rules.raw_valid(kind, v) for v in both.loc[present, f])
            bad_clean += sum(not (k and rules.clean_valid(kind, v))
                             for v, k in zip(both.loc[present, col], kept[present]))
        add(entity, "Invalid values: non-blank cells not in a standard form (%)", round(100 * bad_raw / checked, 1),
            round(100 * bad_clean / checked, 1),
            "raw = not a real date, not exactly in the code list, a number typed with text, or impossible; "
            "cleaned = still unreadable, not mapped, or impossible", n)
        if entity == "activity":
            num = lambda s: pd.to_numeric(s.astype(str).str.strip(), errors="coerce")
            f_, m_, t_ = num(both["female"]), num(both["male"]), num(both["total"])
            parsed = f_.notna() & m_.notna() & t_.notna()
            fail_raw = parsed & (((f_ + m_) != t_) | (f_ > t_))
            used = kept & ~pd.Series([k in q_keys for k in zip(both["source_file"], both["source_sheet"],
                                                                both["source_row"].astype(int))], index=both.index)
            cf, cm, ct = both["participants_female"], both["participants_male"], both["participants_total"]
            cparsed = used & cf.notna() & cm.notna() & ct.notna()
            fail_clean = cparsed & (((cf + cm) != ct) | (cf > ct))
            add(entity, "Consistency failures: women + men differ from total, or women > total (% of rows)",
                round(100 * fail_raw.sum() / parsed.sum(), 1), round(100 * fail_clean.sum() / max(cparsed.sum(), 1), 1),
                f"raw: rows whose three numbers can be read ({parsed.sum():,}); cleaned: rows used in reporting "
                f"({cparsed.sum():,}; {int((kept & ~used).sum())} quarantined until corrected). A mismatch is not "
                "corrected (which number is wrong is unknown): the row stays in use and goes to the review queue", n)
            content = [c for c in raw.columns if c not in key + ["row_no"]]
            dup_raw = raw.duplicated(content).sum()
            ccontent = [c for c in clean.columns if c not in key]
            dup_clean = clean.duplicated(ccontent).sum()
            add(entity, "Duplicates: activity rows typed twice (%)", round(100 * dup_raw / len(raw), 1),
                round(100 * dup_clean / len(clean), 1),
                f"identical rows apart from their position in the file: raw {dup_raw}, cleaned {dup_clean}", n)
        if entity == "registration" and truth is not None and (truth / "SYNTHETIC_truth_registrations.csv").exists():
            t = pd.read_csv(truth / "SYNTHETIC_truth_registrations.csv", dtype=str)
            t["source_row"] = pd.to_numeric(t["source_row"]).astype("Int64")
            t = t.merge(raw[key].astype({"source_row": "Int64"}), on=key, how="inner")
            true_people = t["person_id"].nunique()
            counted_raw = len(raw)
            counted_clean = clean["beneficiary_key"].nunique()
            add(entity, "Duplicates: people counted more than once (% over the true number of people)",
                round(100 * (counted_raw - true_people) / true_people, 1),
                round(100 * (counted_clean - true_people) / true_people, 1),
                f"true people on these registrations: {true_people:,} (answer key). Raw = counting register rows "
                f"({counted_raw:,}); cleaned = different people after duplicate matching ({counted_clean:,}). "
                "Real data has no answer key: there, only the pending-review count is known.", n)
    return pd.DataFrame(rows)


def write(results: pd.DataFrame, docs: Path, out_csv: Path) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(out_csv, index=False, encoding="utf-8-sig")
    lines = ["# Before and after: raw files versus cleaned data", "",
             f"*Generated by `src/evaluate.py` on {dt.date.today():%d %B %Y}. Synthetic data only. Do not edit by hand.*",
             "", "The same records are compared: every row read from the Excel files, identified by file, sheet and "
             "row, as typed (**raw files**) and after the pipeline (**after cleaning**). A raw figure is what a person "
             "would face if they reported straight from the files. Lower is better for invalid values, consistency "
             "failures and duplicates; higher is better for completeness.", "",
             "Completeness can fall after cleaning: a date the pipeline cannot read is treated as empty (and the row "
             "goes to quarantine or the review queue) rather than guessed. Raw completeness counts anything typed, "
             "even an unreadable value.", ""]
    for name, g in results.groupby("set", sort=False):
        lines += [f"## {name}", "", "| Records | Measure | Raw files | After cleaning | Records compared | How measured |",
                  "|---|---|---|---|---|---|"]
        for r in g.itertuples():
            lines.append(f"| {r.records} | {r.measure} | {r.raw_files} | {r.after_cleaning} | {r.records_compared:,} | "
                         f"{r.how_measured} |")
        lines.append("")
    lines += ["## Limits", "",
              "- Synthetic data, with problems injected at chosen rates: the size of the improvement depends on those "
              "rates. The real before/after must be measured on ARDE/KUBAHO files (Phase 8).",
              "- 'Raw' is generous: blank rows, totals rows and merged headers are already removed by the reading step, "
              "and 'completeness' counts any typed value as present.",
              "- The duplicate measure for people uses the synthetic answer key; with real data the true number of "
              "people is unknown.", ""]
    (docs / "evaluation_before_after.md").write_text("\n".join(lines), encoding="utf-8")


# ======================================================================================
# MEAL readiness: indicator catalogue audit
# ======================================================================================
# The fields every indicator needs for a FULL definition (brief Section 7; proposal: "share of pilot indicators with
# full definitions"). "higher_is_better" is the direction.
DEFINITION_FIELDS = ["code", "name", "definition", "level", "unit", "numerator", "denominator", "calculation_rule",
                     "disaggregation", "target_setting_rule", "frequency", "data_source", "owner", "higher_is_better",
                     "notes"]
OPEN_WORDING = re.compile(r"to be (confirmed|agreed)", re.I)


def catalogue_audit() -> pd.DataFrame:
    """One row per indicator: how many of the definition fields are filled in, and how many are still open
    ("to be confirmed" / "to be agreed" with ARDE/KUBAHO). Read from config/indicator_catalogue.yaml."""
    rows = []
    for ind in load_yaml("indicator_catalogue.yaml")["indicators"]:
        filled = [f for f in DEFINITION_FIELDS if not blank(ind.get(f)) and ind.get(f) != []]
        open_ = [f for f in DEFINITION_FIELDS if OPEN_WORDING.search(str(ind.get(f, "")))]
        rows.append(dict(code=ind["code"], indicator=ind["name"], theme=ind.get("thematic_area"),
                         status=ind.get("status"), availability=ind.get("availability"),
                         fields_filled=len(filled), fields_required=len(DEFINITION_FIELDS),
                         all_fields_filled=len(filled) == len(DEFINITION_FIELDS),
                         fields_still_open=", ".join(open_), fully_agreed=not open_ and "draft" not in
                         str(ind.get("status", "")).lower()))
    return pd.DataFrame(rows)


def write_catalogue_audit(audit: pd.DataFrame, docs: Path) -> None:
    n = len(audit)
    filled, agreed = int(audit["all_fields_filled"].sum()), int(audit["fully_agreed"].sum())
    calculable = int((audit["availability"] == "available").sum())
    lines = ["# Indicator catalogue audit (MEAL readiness)", "",
             f"*Generated by `src/evaluate.py` on {dt.date.today():%d %B %Y} from `config/indicator_catalogue.yaml`. "
             "Do not edit by hand.*", "",
             "Proposal measure: **share of pilot indicators with full definitions**, assessed by an indicator catalogue "
             f"audit. A full definition has all {len(DEFINITION_FIELDS)} fields of the brief (Section 7): "
             + ", ".join(f"`{f}`" for f in DEFINITION_FIELDS) + ".", "",
             "The pilot programme is not chosen yet (to be confirmed with ARDE/KUBAHO), so every indicator in the "
             "catalogue is audited, with its theme.", "",
             "| Result | Indicators | Share |", "|---|---|---|",
             f"| All definition fields filled in | {filled} of {n} | {100 * filled / n:.0f}% |",
             f"| Fully agreed with ARDE/KUBAHO (no field still open, status no longer draft) | {agreed} of {n} | "
             f"{100 * agreed / n:.0f}% |",
             f"| Can be calculated from the data now | {calculable} of {n} | {100 * calculable / n:.0f}% |", "",
             "All indicators are **drafts for co-design**: the fields are written, but their owners and most targets "
             "must be agreed with ARDE/KUBAHO staff. The second figure is the one that should rise after the "
             "co-design session.", "",
             "| Code | Indicator | Theme | Fields filled | Still open | Calculable now |", "|---|---|---|---|---|---|"]
    for r in audit.itertuples():
        lines.append(f"| {r.code} | {r.indicator} | {r.theme} | {r.fields_filled} of {r.fields_required} | "
                     f"{r.fields_still_open or '-'} | {'yes' if r.availability == 'available' else 'no: ' + r.availability} |")
    lines.append("")
    (docs / "indicator_catalogue_audit.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> pd.DataFrame:
    sets = [("Main synthetic set (seed 2023)", resolve_path("staging"), resolve_path("ground_truth"))]
    final = resolve_path("final_staging")
    if (final / "ingested_activity.parquet").exists():
        sets.append(("Final held-out set (seed 6151)", final, resolve_path("final_ground_truth")))
    results = pd.concat([evaluate_set(*s) for s in sets], ignore_index=True)
    write(results, resolve_path("docs"), PROJECT_ROOT / "evaluation" / "before_after.csv")
    audit = catalogue_audit()
    write_catalogue_audit(audit, resolve_path("docs"))
    print(f"Catalogue audit: {int(audit['all_fields_filled'].sum())} of {len(audit)} indicators have every definition "
          f"field filled; {int(audit['fully_agreed'].sum())} fully agreed. Written: docs/indicator_catalogue_audit.md")
    print(results[["set", "records", "measure", "raw_files", "after_cleaning"]].to_string(index=False))
    print("Written: docs/evaluation_before_after.md and evaluation/before_after.csv")
    return results


if __name__ == "__main__":
    main()
