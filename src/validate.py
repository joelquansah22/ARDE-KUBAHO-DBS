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
  1. groups them into the rules in config/dq_rules.yaml and scores each rule and each of the
     six dimensions (completeness, validity, consistency, uniqueness, timeliness, accuracy);
  2. builds the QUARANTINE table (every row with a critical problem, with the reasons) and the
     REVIEW QUEUE (every row with warnings only);
  3. scores each source file and each field officer;
  4. writes everything to data/staging/dq_*.parquet (model.py loads it into the warehouse) and
     writes the report docs/data_quality_report.md.

Nothing is deleted: quarantined rows are kept in the quarantine table with their reasons.

HOW TO RUN
    python src/validate.py      (after ingest.py and clean.py; pipeline.py runs all of them)
"""

from __future__ import annotations

import datetime as dt

import pandas as pd

from common import load_settings, load_yaml, resolve_path

ENTITIES = ["activity", "registration", "service", "indicator_result", "donor", "opportunity"]
POSITION = ["source_file", "source_sheet", "source_row"]


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


class Validator:
    def __init__(self, staging=None):
        self.staging = staging or resolve_path("staging")
        self.settings = load_settings()
        self.rules = load_yaml("dq_rules.yaml")
        read = lambda name: pd.read_parquet(self.staging / f"{name}.parquet")
        self.tables = {e: read(f"clean_{e}") for e in ENTITIES}
        self.issues = read("issues")
        self.status = read("clean_row_status")
        self.completeness = read("clean_report_completeness")
        self.info = read("clean_dq_info_metrics")
        self.inventory = pd.read_csv(self.staging / "sheet_inventory.csv", dtype=str, keep_default_na=False)
        skipped = self.staging / "skipped_sheets.csv"
        self.skipped = pd.read_csv(skipped, dtype=str, keep_default_na=False) if skipped.exists() else pd.DataFrame(
            columns=["source_file", "source_sheet", "entity", "reason", "missing_required", "headers_found"])
        self.officer_of_row = self._officers()

    # ---------------------------------------------------------------- helpers
    def _officers(self) -> dict:
        """Officer code for each source row, where the record says who it belongs to."""
        out = {}
        for entity, col in (("activity", "field_officer"), ("indicator_result", "entered_by")):
            df = self.tables[entity]
            for f, s, r, o in zip(df["source_file"], df["source_sheet"], df["source_row"], df[col]):
                out[(f, s, int(r))] = o
        return out

    def flagged_rows(self, entity_list, codes, actions=("flagged",)) -> pd.DataFrame:
        sel = self.issues[self.issues["issue_code"].isin(codes) & self.issues["action"].isin(actions)
                          & self.issues["entity"].isin(entity_list) & self.issues["source_row"].notna()]
        return sel

    # ---------------------------------------------------------------- 1. rules and dimensions
    def rule_results(self) -> pd.DataFrame:
        rows = []
        for rule in self.rules["rules"]:
            codes = rule["flags"]
            special = rule.get("special")
            if special == "sheets":
                sheets = self.inventory[self.inventory["entity"].isin(ENTITIES)]
                checked, failed = len(sheets), len(self.skipped)
                sev = dict(critical=failed, warning=0, info=0)
            elif special == "expected_reports":
                checked, failed = len(self.completeness), int((~self.completeness["submitted"].astype(bool)).sum())
                sev = dict(critical=0, warning=0, info=failed)
            else:
                ents = rule["entities"]
                checked = sum(len(self.tables[e]) for e in ents)
                actions = ("flagged", "removed")
                hits = self.flagged_rows(ents, codes, actions)
                if "exact_duplicate_row" in codes:          # removed copies were records too
                    checked += int((hits["issue_code"] == "exact_duplicate_row").sum())
                per_row = hits.groupby(["entity"] + POSITION)["severity"].agg(
                    lambda s: "critical" if "critical" in set(s) else "warning" if "warning" in set(s) else "info")
                failed = len(per_row)
                sev = {k: int((per_row == k).sum()) for k in ("critical", "warning", "info")}
            score = round(100 * (1 - failed / checked), 1) if checked else None
            rows.append(dict(rule_id=rule["id"], dimension=rule["dimension"], description=rule["description"],
                             records_checked=int(checked), records_failed=int(failed), score=score,
                             critical_failures=sev["critical"], warning_failures=sev["warning"],
                             info_failures=sev["info"]))
        return pd.DataFrame(rows)

    def dimension_scores(self, results: pd.DataFrame) -> pd.DataFrame:
        dims = (results.groupby("dimension", sort=False)
                .agg(score=("score", "mean"), rules=("rule_id", "count"))
                .reindex(self.rules["dimensions"]).reset_index())
        dims["score"] = dims["score"].round(1)
        overall = pd.DataFrame([dict(dimension="overall", score=round(dims["score"].mean(), 1), rules=int(dims["rules"].sum()))])
        return pd.concat([dims, overall], ignore_index=True)

    # ---------------------------------------------------------------- 2. quarantine and review queue
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

    # ---------------------------------------------------------------- 3. by file and by officer
    def by_source_file(self, quarantine, review) -> pd.DataFrame:
        rows = []
        q = quarantine.groupby(["source_file", "source_sheet"]).size()
        rv = review.groupby(["source_file", "source_sheet"]).size()
        for inv in self.inventory[self.inventory["entity"].isin(ENTITIES)].itertuples():
            key = (inv.source_file, inv.source_sheet)
            skipped = inv.note.startswith("skipped")
            table = self.tables[inv.entity]
            mine = table[(table["source_file"] == inv.source_file) & (table["source_sheet"] == inv.source_sheet)]
            officers = {self.officer_of_row.get((f, s, int(r))) for f, s, r in
                        zip(mine["source_file"], mine["source_sheet"], mine["source_row"])} - {None}
            read = len(mine)
            nq, nr = int(q.get(key, 0)), int(rv.get(key, 0))
            rows.append(dict(source_file=inv.source_file, source_sheet=inv.source_sheet, entity=inv.entity,
                             field_officer=next(iter(officers)) if len(officers) == 1 else None,
                             rows_read=read, rows_quarantined=nq, rows_for_review=nr, rows_clean=read - nq - nr,
                             score=round(100 * (read - nq - nr) / read, 1) if read else None, skipped=skipped))
        return pd.DataFrame(rows)

    def by_field_officer(self, quarantine, review) -> pd.DataFrame:
        late = self.issues[self.issues["issue_code"].isin(["late_entry", "late_entry_possible"])]
        late_rows = {(f, s, int(r)) for f, s, r in zip(late["source_file"], late["source_sheet"], late["source_row"])}
        q = {(f, s, int(r)) for f, s, r in zip(quarantine["source_file"], quarantine["source_sheet"], quarantine["source_row"])}
        rv = {(f, s, int(r)) for f, s, r in zip(review["source_file"], review["source_sheet"], review["source_row"])}
        stats: dict[str, dict] = {}
        for pos, officer in self.officer_of_row.items():
            if not officer:
                continue
            st = stats.setdefault(officer, dict(rows=0, rows_quarantined=0, rows_for_review=0, late_entries=0))
            st["rows"] += 1
            st["rows_quarantined"] += pos in q
            st["rows_for_review"] += pos in rv
            st["late_entries"] += pos in late_rows
        out = pd.DataFrame([dict(field_officer=o, **v) for o, v in sorted(stats.items())])
        if len(out):
            out["score"] = (100 * (out["rows"] - out["rows_quarantined"] - out["rows_for_review"]) / out["rows"]).round(1)
        return out

    # ---------------------------------------------------------------- run
    def run(self, docs=None) -> dict:
        results = self.rule_results()
        dims = self.dimension_scores(results)
        quarantine, review = self.row_lists()
        tables = dict(
            dq_results=results, dq_dimension_scores=dims, quarantine=quarantine, review_queue=review,
            dq_by_source_file=self.by_source_file(quarantine, review),
            dq_by_field_officer=self.by_field_officer(quarantine, review),
            skipped_sheets=self.skipped[["source_file", "source_sheet", "entity", "reason", "missing_required",
                                         "headers_found"]].copy() if len(self.skipped) else pd.DataFrame(
                columns=["source_file", "source_sheet", "entity", "reason", "missing_required", "headers_found"]),
            dq_info_measures=self.info[["metric", "percent", "numerator", "denominator", "note"]].copy())
        for name, df in tables.items():
            df.to_parquet(self.staging / f"dq_{name}.parquet" if not name.startswith("dq_")
                          else self.staging / f"{name}.parquet", index=False)
        write_report(tables, self.settings, docs or resolve_path("docs"))
        return tables


def write_report(t: dict, settings: dict, docs) -> None:
    """docs/data_quality_report.md, written for programme managers and the MEAL officer."""
    dims = t["dq_dimension_scores"]
    overall = dims.loc[dims["dimension"] == "overall", "score"].iloc[0]
    skipped, quarantine, review = t["skipped_sheets"], t["quarantine"], t["review_queue"]
    window = pd.period_range(settings["reporting_window"]["start"], settings["reporting_window"]["end"],
                             freq="M").astype(str)
    monthly = review.groupby("month").size().reindex(window, fill_value=0)
    per_row, budget = settings["review_minutes_per_row"], settings["review_budget_minutes_per_month"]

    def reason_counts(df):
        if not len(df):
            return pd.DataFrame(columns=["reason", "rows"])
        return (df.assign(reason=df["reasons"].str.split(", ")).explode("reason")
                .groupby("reason").size().sort_values(ascending=False).rename("rows").reset_index())

    lines = ["# Data-quality report", ""]
    if settings.get("synthetic_mode"):
        lines += [f"> **{settings['synthetic_banner']}**", ""]
    lines += [f"*Generated by `src/validate.py` on {dt.date.today():%d %B %Y}. Do not edit by hand.*", ""]
    # ---- skipped sheets first: they are the biggest risk to the numbers
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
              "## 3. Rules", "",
              "Each rule's score is the percentage of the records it applies to that do not break it. Whether a "
              "failure quarantines a row, sends it for review or is only counted is shown in the last three columns.",
              "", md_table(t["dq_results"].rename(columns={"score": "score %"})), "",
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
              "By reason:", "", md_table(reason_counts(review)), "",
              "## 6. Data-quality measures (no action needed on individual rows)", "",
              md_table(t["dq_info_measures"].rename(columns={"percent": "%"})), "",
              "## 7. By source file", "", md_table(t["dq_by_source_file"]), "",
              "## 8. By field officer (activity records and indicator reports)", "",
              md_table(t["dq_by_field_officer"]), "",
              "## How the scores are worked out", "",
              "- Rule score = % of the records the rule applies to that do not break it (config/dq_rules.yaml).",
              "- Dimension score = average of its rules. Overall score = average of the six dimensions.",
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
