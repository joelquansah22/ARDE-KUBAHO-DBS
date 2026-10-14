"""Score data quality, build the quarantine table and write the data-quality report.

WHAT THIS SCRIPT DOES
---------------------
The checks themselves run while the data is cleaned: clean.py and ingest.py raise a
flag on every problem they find, and each flag has a severity (config/settings.yaml,
flag_severity):
    critical  the row is QUARANTINED (kept aside, not used in results)
    warning   the row is used, but goes to the REVIEW QUEUE
    info      the problem is only counted, as a data-quality measure

This script turns those flags into results:
  1. works out the data-quality MEASURES defined once in config/dq_metrics.yaml (timeliness,
     reporting completeness...). Everything else uses these numbers, so a measure never shows two
     different values in two places;
  2. groups the flags into the RULES in config/dq_rules.yaml and scores each rule (overall and per
     source file) and each of the six dimensions;
  3. builds the QUARANTINE table (every row with a critical problem, with the reasons) and the
     REVIEW QUEUE (every row with warnings only), and lists people pending a duplicate review;
  4. scores each source file and each field officer;
  5. writes everything to data/staging/dq_*.parquet (model.py loads it into the warehouse) and
     writes the report docs/data_quality_report.md.

Nothing is deleted: quarantined rows are kept in the quarantine table with their reasons.

HOW TO RUN
    python src/validate.py      (after ingest.py and clean.py; pipeline.py runs all of them)
"""

from __future__ import annotations

import datetime as dt
import re

import pandas as pd

from common import load_settings, load_yaml, resolve_path

ENTITIES = ["activity", "registration", "service", "indicator_result", "donor", "opportunity"]
POSITION = ["source_file", "source_sheet", "source_row"]
DUPLICATE_REVIEW_CODES = ["possible_duplicate_person", "possible_duplicate_initials"]


def md_table(df: pd.DataFrame) -> str:
    """A Markdown table (no extra libraries needed)."""
    if df is None or not len(df):
        return "None."
    cols = list(df.columns)
    lines = ["| " + " | ".join(str(c) for c in cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for row in df.itertuples(index=False):
        cells = ["" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v) for v in row]
        lines.append("| " + " | ".join(c.replace("|", "/") for c in cells) + " |")
    return "\n".join(lines)


# ======================================================================================
# Measures (config/dq_metrics.yaml): one definition, one calculation
# ======================================================================================
def _setting(path: str, settings: dict):
    value = settings
    for part in path.split("."):
        value = value[part]
    return value


def condition_mask(df: pd.DataFrame, conditions: dict, settings: dict) -> pd.Series:
    """Rows of df meeting every condition (see the header of config/dq_metrics.yaml)."""
    mask = pd.Series(True, index=df.index)
    for col, test in (conditions or {}).items():
        values = df[col]
        if test == "notnull":
            mask &= values.notna()
        elif test == "null":
            mask &= values.isna()
        elif test is True or test is False:
            mask &= values.fillna(not test).astype(bool) == test
        elif isinstance(test, list):
            mask &= values.isin(test)
        elif isinstance(test, str) and re.fullmatch(r"<= setting:[\w.]+", test):
            mask &= pd.to_numeric(values, errors="coerce") <= _setting(test.split(":", 1)[1], settings)
        else:
            raise ValueError(f"Unknown condition '{test}' for column {col} in config/dq_metrics.yaml")
    return mask


def measure(df: pd.DataFrame, spec: dict, settings: dict) -> tuple[int, int]:
    """(numerator, denominator) of one measure on a table (or part of a table)."""
    den = condition_mask(df, spec.get("denominator"), settings)
    num = den & condition_mask(df, spec.get("numerator"), settings)
    return int(num.sum()), int(den.sum())


class Validator:
    def __init__(self, staging=None):
        self.staging = staging or resolve_path("staging")
        self.settings = load_settings()
        self.rules = load_yaml("dq_rules.yaml")
        self.metric_specs = load_yaml("dq_metrics.yaml")["metrics"]
        read = lambda name: pd.read_parquet(self.staging / f"{name}.parquet")
        self.tables = {e: read(f"clean_{e}") for e in ENTITIES}
        self.issues = read("issues")
        self.status = read("clean_row_status")
        self.completeness = read("clean_report_completeness")
        self.inventory = pd.read_csv(self.staging / "sheet_inventory.csv", dtype=str, keep_default_na=False)
        skipped = self.staging / "skipped_sheets.csv"
        self.skipped = pd.read_csv(skipped, dtype=str, keep_default_na=False) if skipped.exists() else pd.DataFrame(
            columns=["source_file", "source_sheet", "entity", "reason", "missing_required", "headers_found"])
        self.people = self.people_pending_review()
        self.measure_tables = {**self.tables, "report_completeness": self.completeness, "people": self.people}
        self.officer_of_row = self._officers()

    # ---------------------------------------------------------------- helpers
    def _officers(self) -> dict:
        """Officer code for each source row, where the record says who it belongs to."""
        out = {}
        for entity in ("activity", "indicator_result", "registration"):
            df = self.tables[entity]
            if "officer_code" not in df:
                continue
            for f, s, r, o in zip(df["source_file"], df["source_sheet"], df["source_row"], df["officer_code"]):
                if o:
                    out[(f, s, int(r))] = o
        return out

    def flagged_rows(self, entity_list, codes, actions=("flagged",)) -> pd.DataFrame:
        return self.issues[self.issues["issue_code"].isin(codes) & self.issues["action"].isin(actions)
                           & self.issues["entity"].isin(entity_list) & self.issues["source_row"].notna()]

    def people_pending_review(self) -> pd.DataFrame:
        """One row per person (beneficiary_key): is any of their records waiting for a duplicate review?"""
        regs = self.tables["registration"]
        flagged = self.flagged_rows(["registration"], DUPLICATE_REVIEW_CODES)
        pos = {(f, s, int(r)) for f, s, r in zip(flagged["source_file"], flagged["source_sheet"], flagged["source_row"])}
        regs = regs.assign(pending=[(f, s, int(r)) in pos for f, s, r in
                                    zip(regs["source_file"], regs["source_sheet"], regs["source_row"])])
        people = regs.groupby("beneficiary_key")["pending"].any().rename("pending_duplicate_review").reset_index()
        return people

    # ---------------------------------------------------------------- 1. measures
    def metrics(self, tables: dict | None = None) -> pd.DataFrame:
        tables = tables or self.measure_tables
        rows = []
        for mid, spec in self.metric_specs.items():
            num, den = measure(tables[spec["table"]], spec, self.settings)
            rows.append(dict(metric_id=mid, metric=spec["name"], percent=round(100 * num / den, 1) if den else None,
                             numerator=num, denominator=den, note=" ".join(spec["note"].split()),
                             show_on_dashboard=bool(spec.get("show_on_dashboard"))))
        return pd.DataFrame(rows)

    # ---------------------------------------------------------------- 2. rules and dimensions
    def _rule_on(self, rule: dict, tables: dict, issues: pd.DataFrame, sheets_part=None) -> dict:
        """Score one rule on a set of tables (all of them, or one source file's share)."""
        codes = rule["flags"]
        if rule.get("metric"):
            spec = self.metric_specs[rule["metric"]]
            num, den = measure(tables[spec["table"]], spec, self.settings)
            failed = den - num
            sev = dict(critical=0, warning=0, info=failed)
            checked = den
        elif rule.get("special") == "sheets":
            sheets = self.inventory[self.inventory["entity"].isin(ENTITIES)] if sheets_part is None else sheets_part
            checked = len(sheets)
            failed = int(sheets["note"].str.startswith("skipped").sum())
            sev = dict(critical=failed, warning=0, info=0)
        else:
            ents = rule["entities"]
            checked = sum(len(tables[e]) for e in ents)
            hits = issues[issues["issue_code"].isin(codes) & issues["action"].isin(["flagged", "removed"])
                          & issues["entity"].isin(ents) & issues["source_row"].notna()]
            if "exact_duplicate_row" in codes:          # removed copies were records too
                checked += int((hits["issue_code"] == "exact_duplicate_row").sum())
            per_row = hits.groupby(["entity"] + POSITION)["severity"].agg(
                lambda s: "critical" if "critical" in set(s) else "warning" if "warning" in set(s) else "info")
            failed = len(per_row)
            sev = {k: int((per_row == k).sum()) for k in ("critical", "warning", "info")}
        return dict(records_checked=int(checked), records_failed=int(failed),
                    score=round(100 * (1 - failed / checked), 1) if checked else None,
                    critical_failures=sev["critical"], warning_failures=sev["warning"], info_failures=sev["info"])

    def rule_results(self) -> pd.DataFrame:
        rows = [dict(rule_id=r["id"], dimension=r["dimension"], description=r["description"],
                     **self._rule_on(r, self.measure_tables, self.issues)) for r in self.rules["rules"]]
        out = pd.DataFrame(rows)
        # How many points each rule takes off its dimension score (the dimension is the average of its rules).
        n = out.groupby("dimension")["rule_id"].transform("count")
        out["dimension_impact"] = ((100 - out["score"].fillna(100)) / n).round(1)
        return out

    def rule_results_by_file(self) -> pd.DataFrame:
        """Every rule scored on each source sheet separately, to show which rule drives a low file score."""
        rows = []
        inv = self.inventory[self.inventory["entity"].isin(ENTITIES)]
        for sheet in inv.itertuples():
            part = {k: v[(v["source_file"] == sheet.source_file) & (v["source_sheet"] == sheet.source_sheet)]
                    if "source_file" in v else v.iloc[0:0] for k, v in self.measure_tables.items()}
            issues = self.issues[(self.issues["source_file"] == sheet.source_file)
                                 & (self.issues["source_sheet"] == sheet.source_sheet)]
            for rule in self.rules["rules"]:
                applies = (rule.get("special") == "sheets"
                           or (rule.get("metric") and self.metric_specs[rule["metric"]]["table"] == sheet.entity)
                           or sheet.entity in rule.get("entities", []))
                if not applies:
                    continue
                res = self._rule_on(rule, part, issues, sheets_part=inv[(inv["source_file"] == sheet.source_file)
                                                                        & (inv["source_sheet"] == sheet.source_sheet)])
                if res["records_checked"]:
                    rows.append(dict(source_file=sheet.source_file, source_sheet=sheet.source_sheet,
                                     rule_id=rule["id"], dimension=rule["dimension"], **res))
        return pd.DataFrame(rows)

    def dimension_scores(self, results: pd.DataFrame) -> pd.DataFrame:
        dims = (results.groupby("dimension", sort=False)
                .agg(score=("score", "mean"), rules=("rule_id", "count"))
                .reindex(self.rules["dimensions"]).reset_index())
        dims["score"] = dims["score"].round(1)
        overall = pd.DataFrame([dict(dimension="overall", score=round(dims["score"].mean(), 1), rules=int(dims["rules"].sum()))])
        return pd.concat([dims, overall], ignore_index=True)

    # ---------------------------------------------------------------- 3. quarantine and review queue
    def row_lists(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        flagged = self.issues[self.issues["severity"].isin(["critical", "warning"]) & self.issues["source_row"].notna()]
        detail = (flagged.assign(text=flagged["issue_code"] + ": " + flagged["detail"].fillna(""))
                  .groupby(["source_file", "source_sheet", "source_row", "severity"])["text"]
                  .agg(lambda t: "; ".join(sorted(set(x.rstrip(": ") for x in t)))))

        def build(status, codes_col, severity):
            df = self.status[self.status["status"] == status].copy()
            df["reasons"] = df[codes_col]
            df["details"] = [detail.get((f, s, float(r), severity), detail.get((f, s, r, severity), ""))
                             for f, s, r in zip(df["source_file"], df["source_sheet"], df["source_row"])]
            df["field_officer"] = [self.officer_of_row.get((f, s, int(r))) for f, s, r in
                                   zip(df["source_file"], df["source_sheet"], df["source_row"])]
            return df[["entity", "source_file", "source_sheet", "source_row", "month", "reasons", "details",
                       "field_officer"]].reset_index(drop=True)

        return build("quarantine", "critical_codes", "critical"), build("review", "warning_codes", "warning")

    # ---------------------------------------------------------------- 4. by file and by officer
    def by_source_file(self, quarantine, review) -> pd.DataFrame:
        rows = []
        q = quarantine.groupby(["source_file", "source_sheet"]).size()
        rv = review.groupby(["source_file", "source_sheet"]).size()
        for inv in self.inventory[self.inventory["entity"].isin(ENTITIES)].itertuples():
            key = (inv.source_file, inv.source_sheet)
            table = self.tables[inv.entity]
            mine = table[(table["source_file"] == inv.source_file) & (table["source_sheet"] == inv.source_sheet)]
            officers = {self.officer_of_row.get((f, s, int(r))) for f, s, r in
                        zip(mine["source_file"], mine["source_sheet"], mine["source_row"])} - {None}
            read = len(mine)
            nq, nr = int(q.get(key, 0)), int(rv.get(key, 0))
            rows.append(dict(source_file=inv.source_file, source_sheet=inv.source_sheet, entity=inv.entity,
                             field_officer=next(iter(officers)) if len(officers) == 1 else None,
                             rows_read=read, rows_quarantined=nq, rows_for_review=nr, rows_clean=read - nq - nr,
                             score=round(100 * (read - nq - nr) / read, 1) if read else None,
                             skipped=inv.note.startswith("skipped")))
        return pd.DataFrame(rows)

    def by_field_officer(self, quarantine, review) -> pd.DataFrame:
        late = self.issues[self.issues["issue_code"].isin(["late_entry"])]
        late_rows = {(f, s, int(r)) for f, s, r in zip(late["source_file"], late["source_sheet"], late["source_row"])}
        q = {(f, s, int(r)) for f, s, r in zip(quarantine["source_file"], quarantine["source_sheet"], quarantine["source_row"])}
        rv = {(f, s, int(r)) for f, s, r in zip(review["source_file"], review["source_sheet"], review["source_row"])}
        stats: dict[str, dict] = {}
        for pos, officer in self.officer_of_row.items():
            st = stats.setdefault(officer, dict(rows=0, rows_quarantined=0, rows_for_review=0, late_entries=0))
            st["rows"] += 1
            st["rows_quarantined"] += pos in q
            st["rows_for_review"] += pos in rv
            st["late_entries"] += pos in late_rows
        out = pd.DataFrame([dict(field_officer=o, **v) for o, v in sorted(stats.items())],
                           columns=["field_officer", "rows", "rows_quarantined", "rows_for_review", "late_entries"])
        out["score"] = (100 * (out["rows"] - out["rows_quarantined"] - out["rows_for_review"]) / out["rows"]).round(1)
        return out

    # ---------------------------------------------------------------- run
    def run(self, docs=None) -> dict:
        metrics = self.metrics()
        results = self.rule_results()
        dims = self.dimension_scores(results)
        quarantine, review = self.row_lists()
        tables = dict(
            dq_results=results, dq_dimension_scores=dims, quarantine=quarantine, review_queue=review,
            dq_rule_results_by_file=self.rule_results_by_file(),
            dq_by_source_file=self.by_source_file(quarantine, review),
            dq_by_field_officer=self.by_field_officer(quarantine, review),
            skipped_sheets=self.skipped.reindex(columns=["source_file", "source_sheet", "entity", "reason",
                                                         "missing_required", "headers_found"]),
            dq_info_measures=metrics[metrics["show_on_dashboard"]][
                ["metric_id", "metric", "percent", "numerator", "denominator", "note"]].reset_index(drop=True),
            people_pending_review=self.people)
        for name, df in tables.items():
            file_name = name if name.startswith("dq_") else f"dq_{name}"
            df.to_parquet(self.staging / f"{file_name}.parquet", index=False)
        write_report(tables, self.settings, docs or resolve_path("docs"))
        return tables


def review_queue_monthly(review: pd.DataFrame, settings: dict) -> pd.Series:
    """Rows to review per month over the reporting window (one definition, used by the report and scorer)."""
    window = pd.period_range(settings["reporting_window"]["start"], settings["reporting_window"]["end"],
                             freq="M").astype(str)
    return review.groupby("month").size().reindex(window, fill_value=0)


def write_report(t: dict, settings: dict, docs) -> None:
    """docs/data_quality_report.md, written for programme managers and the MEAL officer."""
    dims = t["dq_dimension_scores"]
    overall = dims.loc[dims["dimension"] == "overall", "score"].iloc[0]
    skipped, quarantine, review = t["skipped_sheets"], t["quarantine"], t["review_queue"]
    monthly = review_queue_monthly(review, settings)
    per_row, budget = settings["review_minutes_per_row"], settings["review_budget_minutes_per_month"]
    pending = int(t["people_pending_review"]["pending_duplicate_review"].sum())

    def reason_counts(df):
        if not len(df):
            return pd.DataFrame(columns=["reason", "rows"])
        return (df.assign(reason=df["reasons"].str.split(", ")).explode("reason")
                .groupby("reason").size().sort_values(ascending=False).rename("rows").reset_index())

    worst = t["dq_results"].sort_values("dimension_impact", ascending=False).head(3)
    lines = ["# Data-quality report", ""]
    if settings.get("synthetic_mode"):
        lines += [f"> **{settings['synthetic_banner']}**", ""]
    lines += [f"*Generated by `src/validate.py` on {dt.date.today():%d %B %Y}. Do not edit by hand.*", ""]
    lines += ["## 1. Sheets that could not be read", ""]
    if len(skipped):
        lines += [f"**{len(skipped)} sheet(s) were SKIPPED. None of their records are in any result.** Add the "
                  "column names below to `config/source_mappings.yaml` and run the pipeline again.", "",
                  md_table(skipped.rename(columns={"headers_found": "unrecognised column headers"})), ""]
    else:
        lines += ["All sheets were read. None was skipped.", ""]
    lines += ["## 2. Overall data-quality score", "",
              f"**Overall score: {overall}%** (the average of the six dimension scores below).", "",
              md_table(dims[dims["dimension"] != "overall"].rename(columns={"score": "score %"})), "",
              "Rules pulling their dimension down the most (points taken off the dimension score):", "",
              md_table(worst[["rule_id", "dimension", "description", "score", "dimension_impact"]]), "",
              "## 3. Rules", "",
              "Each rule's score is the percentage of the records it applies to that do not break it. Rules marked "
              "with a measure use the single definition in `config/dq_metrics.yaml`, the same number shown in "
              "section 6. Whether a failure quarantines a row, sends it for review or is only counted is shown in "
              "the severity columns. Scores per source file are in the `dq_rule_results_by_file` table.", "",
              md_table(t["dq_results"].rename(columns={"score": "score %"})), "",
              "## 4. Quarantined records", "",
              f"**{len(quarantine)} rows are quarantined.** They broke a critical rule, so they are not used in any "
              "result. They are kept, with their reasons, in the `quarantine` table of the warehouse: correct them "
              "in the source Excel file and run the pipeline again.", "",
              "By reason (a row can have more than one):", "", md_table(reason_counts(quarantine)), "",
              "By kind of record:", "",
              md_table(quarantine.groupby("entity").size().rename("rows").reset_index()), "",
              "## 5. Review queue", "",
              f"**{len(review)} rows** have warnings but no critical problem: they are used in results and listed in "
              f"the `review_queue` table for the MEAL officer to check. Per month: average {monthly.mean():.1f} rows, "
              f"busiest month {int(monthly.max())} ({monthly.idxmax()}). At {per_row} minutes a row that is about "
              f"{monthly.mean() * per_row:.0f} minutes a month on average; months over the {budget}-minute budget: "
              f"{int((monthly * per_row > budget).sum())}.", "",
              f"**People count:** {pending} people have records pending a duplicate review, so the number of people "
              "reached may be slightly too high until that review is done.", "",
              "By reason:", "", md_table(reason_counts(review)), "",
              "## 6. Data-quality measures (no action needed on individual rows)", "",
              "Each is defined once, in `config/dq_metrics.yaml`.", "",
              md_table(t["dq_info_measures"].rename(columns={"percent": "%"})), "",
              "## 7. By source file", "", md_table(t["dq_by_source_file"]), "",
              "## 8. By field officer", "",
              "Activity records, indicator reports and registers that carry an officer code.", "",
              md_table(t["dq_by_field_officer"]), "",
              "## How the scores are worked out", "",
              "- Rule score = % of the records the rule applies to that do not break it (config/dq_rules.yaml).",
              "- A rule linked to a measure uses that measure's single definition (config/dq_metrics.yaml).",
              "- Dimension score = average of its rules. Overall score = average of the six dimensions.",
              "- Dimension impact = points a rule takes off its dimension score.",
              "- Source-file and officer scores = % of rows with no critical or warning problem.",
              "- Severity levels are set in config/settings.yaml (flag_severity).",
              "- The before/after comparison (raw files versus cleaned data) is added in Phase 7 (evaluate.py).", ""]
    (docs / "data_quality_report.md").write_text("\n".join(lines), encoding="utf-8")


def run(staging=None, docs=None) -> dict:
    return Validator(staging).run(docs)


def main():
    t = run()
    dims = t["dq_dimension_scores"]
    print(f"Data quality: overall {dims.iloc[-1]['score']}%; {len(t['quarantine'])} rows quarantined, "
          f"{len(t['review_queue'])} rows for review, {len(t['skipped_sheets'])} sheets skipped. "
          "Report: docs/data_quality_report.md")


if __name__ == "__main__":
    main()
