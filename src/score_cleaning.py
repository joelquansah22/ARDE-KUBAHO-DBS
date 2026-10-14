"""Score the cleaning against the synthetic answer key (synthetic data only).

This is a TESTING tool, not part of the production pipeline: it is the only script
allowed to read data/ground_truth/. It answers four questions:

  a. For each kind of injected problem: how many were fixed, flagged or missed?
  b. Totals for officer habits and for genuine errors, kept separate
     (target: at least 95% of genuine errors fixed or flagged; any type below 90% is marked).
  c. False corrections: comparing EVERY cleaned cell with the true value, how many
     clean values did the pipeline wrongly change?
  d. Duplicate beneficiaries: precision and recall at several matching thresholds.

It scores three things, each with the same tables:
  - the main synthetic set (data/raw, already cleaned by the pipeline);
  - the HELD-OUT set (data/holdout/raw): a different seed plus mess the cleaner has never
    seen. The pipeline is run on it unchanged; if it crashes, the crash is reported and
    files it could not read are set aside and counted as missed;
  - hand-made files from teammates (data/holdout/manual), when there are any.
It also reports flag severity: the size of the monthly review queue and the info-level measures.

Results go to docs/phase2_cleaning_scorecard.md and score_*.csv in each staging folder.

HOW TO RUN
    python src/score_cleaning.py      (after ingest.py and clean.py)
"""

from __future__ import annotations

import datetime as dt
import math
import shutil
import traceback
from collections import defaultdict
from math import comb

import pandas as pd
from rapidfuzz import fuzz

import clean
import ingest
from clean import is_blank, norm_key
from common import load_settings, load_yaml, resolve_path

# For each source field: (column in the cleaned table, column in the answer key, how to compare)
COMPARE = {
    "activity": {
        "date": ("date", "date", "date"), "planned_date": ("planned_date", "planned_date", "date"),
        "entry_date": ("entry_date", "entry_date", "date"), "project": ("project_id", "project_id", "text"),
        "activity": ("activity_id", "activity_id", "text"), "province": ("province", "province", "text"),
        "district": ("district", "district", "text"), "sector": ("sector", "sector", "text"),
        "cell": ("cell", "cell", "text"), "village": ("location_id", "location_id", "text"),
        "status": ("status", "status", "text"),
        "female": ("participants_female", "participants_female", "num"),
        "male": ("participants_male", "participants_male", "num"),
        "total": ("participants_total", "participants_total", "num"), "cost": ("cost_rwf", "cost_rwf", "num"),
        "officer": ("officer_code", "field_officer", "text"),
    },
    "registration": {
        "sex": ("sex", "sex", "text"), "age": ("age", "age", "num"), "dob": ("age", "age_from_dob", "num"),
        "household_size": ("household_size", "household_size", "num"),
        "disability": ("disability", "disability", "text"), "province": ("province", "province", "text"),
        "district": ("district", "district", "text"), "sector": ("sector", "sector", "text"),
        "cell": ("cell", "cell", "text"), "village": ("location_id", "location_id", "text"),
        "project": ("project_id", "project_id", "text"), "reg_date": ("registration_date", "registration_date", "date"),
    },
    "service": {"date": ("date", "date", "date"), "activity": ("activity_id", "activity_id", "text")},
    "indicator_result": {
        "project": ("project_id", "project_id", "text"), "district": ("district", "district", "text"),
        "period": ("period", "period", "date"), "indicator": ("indicator_code", "indicator_code", "text"),
        "sex": ("sex", "sex", "text"), "target": ("target_value", "target_value", "num"),
        "actual": ("actual_value", "actual_value", "num"), "entered_by": ("entered_by", "entered_by", "text"),
    },
    "donor": {"donor_type": ("donor_type", "donor_type", "text")},
    "opportunity": {
        "stage": ("stage", "stage", "text"), "deadline": ("deadline", "deadline", "date"),
        "requested": ("requested_amount_rwf", "requested_amount_rwf", "num1pct"),
        "awarded": ("awarded_amount_rwf", "awarded_amount_rwf", "num1pct"),
        "probability": ("probability", "probability", "num"),
        "next_action_date": ("next_action_date", "next_action_date", "date"),
        "owner": ("owner", "owner", "text"), "thematic_fit": ("thematic_fit", "thematic_fit", "text"),
        "donor": ("donor_key", "donor_key", "text"),
    },
}
# A wrong value in one of these fields can make another field wrong too ("knock-on").
DEPENDS_ON = {"village": {"district", "village", "sector"}, "sector": {"district", "village", "sector"},
              "cell": {"district", "village", "sector"}, "province": {"district", "province"},
              "project": {"project", "activity"}, "age": {"age", "dob"},
              # An age worked out from the date of birth also needs the registration date.
              "dob": {"dob", "reg_date"}}
# Problems where the cell value is right and only a flag is the correct response.
FLAG_ONLY = {"late_entry"}
LAYOUT_ROW_CODES = {"blank_row": "blank_row_removed", "totals_row": "totals_row_removed",
                    "duplicate_activity_row": "exact_duplicate_row"}


def equal(clean, truth, kind) -> bool:
    if is_blank(clean) and is_blank(truth):
        return True
    if is_blank(clean) or is_blank(truth):
        return False
    if kind == "date":
        return str(clean)[:10] == str(truth)[:10]
    if kind in ("num", "num1pct", "age1"):
        try:
            c, t = float(clean), float(truth)
        except (TypeError, ValueError):
            return False
        if kind == "age1":
            return abs(c - t) <= 1
        return math.isclose(c, t, rel_tol=0.01 if kind == "num1pct" else 1e-9, abs_tol=1e-6)
    return norm_key(clean) == norm_key(truth)


def md_table(df: pd.DataFrame) -> str:
    """A Markdown table without needing extra libraries."""
    cols = list(df.columns)
    lines = ["| " + " | ".join(str(c) for c in cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for row in df.itertuples(index=False):
        lines.append("| " + " | ".join("" if (isinstance(v, float) and math.isnan(v)) else str(v) for v in row) + " |")
    return "\n".join(lines)


class Scorer:
    def __init__(self, staging=None, truth=None, raw=None, docs=None, overlays: tuple[str, ...] = ()):
        self.overlays = tuple(overlays)
        self.docs = docs or resolve_path("docs")
        self.staging = staging or resolve_path("staging")
        self.truth_dir = truth or resolve_path("ground_truth")
        self.raw = raw or resolve_path("raw")
        self.settings = load_settings()
        self.groups = load_yaml("synthetic.yaml")["error_groups"]
        self.log = pd.read_csv(self.truth_dir / "SYNTHETIC_injected_errors_log.csv", dtype=str, keep_default_na=False)
        self.issues = pd.read_parquet(self.staging / "issues.parquet")
        self.inventory = pd.read_csv(self.staging / "sheet_inventory.csv", dtype=str, keep_default_na=False)
        self.clean = {e: pd.read_parquet(self.staging / f"clean_{e}.parquet") for e in COMPARE}
        self.completeness = pd.read_parquet(self.staging / "clean_report_completeness.parquet")
        self._index()

    # ---------------------------------------------------------------- lookups
    @staticmethod
    def pos(file, sheet, row):
        return (file, sheet, int(float(row)))

    def _index(self):
        self.clean_rows = {e: {self.pos(r["source_file"], r["source_sheet"], r["source_row"]): r
                               for r in df.to_dict("records")} for e, df in self.clean.items()}
        self.flags = defaultdict(set)      # (pos, field) -> codes flagged
        self.codes_at = defaultdict(set)   # pos -> every code
        for r in self.issues.dropna(subset=["source_row"]).to_dict("records"):
            p = self.pos(r["source_file"], r["source_sheet"], r["source_row"])
            self.codes_at[p].add(r["issue_code"])
            if r["action"] == "flagged":
                self.flags[(p, r["field"])].add(r["issue_code"])
        self.missing_reports = set(self.issues.loc[self.issues["issue_code"] == "report_missing", "clean_value"])
        self.header_row = {(r.source_file, r.source_sheet): int(float(r.header_row))
                           for r in self.inventory.itertuples() if r.header_row}
        self.fields_in_sheet = {(r.source_file, r.source_sheet): set(r.fields_found.split(", "))
                                for r in self.inventory.itertuples()}
        self.log_cells = defaultdict(set)  # pos -> fields with an injected problem
        for r in self.log.itertuples():
            if r.source_row:
                self.log_cells[self.pos(r.source_file, r.source_sheet, r.source_row)].add(r.field)
        # Answer key, one dict per Excel row.
        t = lambda name: pd.read_csv(self.truth_dir / f"SYNTHETIC_truth_{name}.csv", dtype=str, keep_default_na=False)
        people, locs = t("people"), t("locations")
        regs = t("registrations").merge(
            people[["person_id", "sex", "household_size", "disability", "district", "location_id", "project_id",
                    "date_of_birth"]],
            on="person_id").merge(locs[["location_id", "province", "sector", "cell", "village"]], on="location_id")
        regs["disability"] = regs["disability"].map({"True": "yes", "False": "no"})
        # True age at THIS registration, worked out from the date of birth. (The answer key's "age"
        # column for a second registration copies the first one with a small random change, so it is
        # not the right comparison when a sheet gives a date of birth.)
        def age_at(dob, reg):
            if not dob or not reg:
                return ""
            b, r = dt.date.fromisoformat(dob[:10]), dt.date.fromisoformat(reg[:10])
            return str(r.year - b.year - ((r.month, r.day) < (b.month, b.day)))
        regs["age_from_dob"] = [age_at(b, r) for b, r in zip(regs["date_of_birth"], regs["registration_date"])]
        self.truth_regs = regs
        frames = {"activity": t("activities"), "registration": regs, "service": t("services"),
                  "indicator_result": t("indicator_results"), "donor": t("donors"), "opportunity": t("opportunities")}
        # The true donor of each opportunity, expressed as the donor_key the pipeline gave that donor.
        donors = frames["donor"]
        key_of = {}
        for r in donors.to_dict("records"):
            row = self.clean_rows["donor"].get(self.pos(r["source_file"], r["source_sheet"], r["source_row"]))
            key_of[r["donor_id"]] = row["donor_key"] if row else None
        frames["opportunity"]["donor_key"] = frames["opportunity"]["donor_id"].map(key_of)
        self.truth = {}
        for entity, df in frames.items():
            df = df[df["source_row"] != ""]
            self.truth[entity] = {self.pos(r["source_file"], r["source_sheet"], r["source_row"]): r
                                  for r in df.to_dict("records")}

    def staged_text(self) -> set[str]:
        """Every text value written to data/staging/, for the personal-data checks."""
        values = set()
        for path in self.staging.glob("*.parquet"):
            df = pd.read_parquet(path)
            for col in df.columns:
                if df[col].dtype == object or str(df[col].dtype).startswith("str"):
                    values.update(norm_key(v) for v in df[col].dropna().astype(str))
        return values

    # ---------------------------------------------------------------- (a) and (b)
    def outcome(self, r) -> tuple[str, str]:
        """Return (fixed | flagged | missed, note) for one injected problem."""
        etype = r.error_type
        if etype == "missing_monthly_report":
            return ("flagged", "") if r.record_id in self.missing_reports else ("missed", "")
        p = self.pos(r.source_file, r.source_sheet, r.source_row)
        if etype in ("title_row", "merged_header_row"):
            ok = self.header_row.get((r.source_file, r.source_sheet), 0) > p[2]
            return ("fixed", "") if ok else ("missed", "")
        if etype in LAYOUT_ROW_CODES:
            return ("fixed", "") if LAYOUT_ROW_CODES[etype] in self.codes_at[p] else ("missed", "")
        if etype == "duplicate_beneficiary":
            first = self.truth_regs[(self.truth_regs["person_id"] == r.true_value)
                                    & (self.truth_regs["is_duplicate"] == "False")].iloc[0]
            first_pos = self.pos(first["source_file"], first["source_sheet"], first["source_row"])
            a, b = self.clean_rows["registration"].get(p), self.clean_rows["registration"].get(first_pos)
            same = a is not None and b is not None and a["beneficiary_key"] == b["beneficiary_key"]
            if same:
                return "fixed", "merged"
            if {"possible_duplicate_person", "possible_duplicate_initials"} & self.flags.get((p, "name"), set()):
                return "flagged", "not merged; sent to review"
            return "missed", "not matched to first registration"
        if etype == "namesake_different_person":
            other = self.truth_regs[(self.truth_regs["person_id"] == r.true_value)
                                    & (self.truth_regs["is_duplicate"] == "False")].iloc[0]
            other_pos = self.pos(other["source_file"], other["source_sheet"], other["source_row"])
            a, b = self.clean_rows["registration"].get(p), self.clean_rows["registration"].get(other_pos)
            if a is None or b is None:
                return "missed", "row missing from cleaned table"
            if a["beneficiary_key"] == b["beneficiary_key"]:
                return "missed", "different people merged"
            reviewed = bool({"possible_duplicate_person", "possible_duplicate_initials"}
                            & self.flags.get((p, "name"), set()))
            return "fixed", "kept apart; sent to review" if reviewed else "kept apart"
        if etype == "personal_data_individual_donor":
            row = self.clean_rows["donor"].get(p)
            ok = row is not None and str(row["donor_name"]).startswith("Individual donor") \
                and norm_key(r.messy_value) not in self.staged
            return ("fixed", "") if ok else ("missed", "name still present")
        if etype == "personal_data_contact":
            return ("fixed", "") if norm_key(r.messy_value) not in self.staged else ("missed", "contact still present")
        if etype == "phone_leading_zero_lost":
            return ("fixed", "") if "phone_leading_zero_restored" in self.codes_at[p] else ("missed", "")
        if etype == "amount_in_usd":
            # The officer WROTE a USD amount; the right RWF value is that amount at the configured rate (the
            # answer key's RWF figure is the generator's value before it rounded the USD amount it wrote).
            import re
            written = float(re.sub(r"[^0-9.]", "", str(r.messy_value)))
            row = self.clean_rows["opportunity"].get(p)
            rate = self.settings["currency"]["usd_to_rwf"]
            ok = row is not None and math.isclose(float(row["requested_amount_rwf"]), written * rate, rel_tol=1e-9)
            return ("fixed", "") if ok else ("missed", "USD amount not converted at the configured rate")
        if etype == "id_stored_as_number":
            return ("flagged", "") if "id_stored_as_number" in self.flags[(p, "national_id")] else ("missed", "")
        entity = r.entity
        spec = COMPARE.get(entity, {}).get(r.field)
        clean_row = self.clean_rows.get(entity, {}).get(p)
        truth_row = self.truth.get(entity, {}).get(p)
        if spec and clean_row is not None and truth_row is not None and etype not in FLAG_ONLY:
            clean_col, truth_col, kind = spec
            if equal(clean_row.get(clean_col), truth_row.get(truth_col), kind):
                return "fixed", ""
        if self.flags.get((p, r.field)):
            return "flagged", ", ".join(sorted(self.flags[(p, r.field)]))
        if clean_row is None:
            return "missed", "row missing from cleaned table"
        if spec and not is_blank(clean_row.get(spec[0])):
            return "missed", f"wrong value: {clean_row.get(spec[0])} (true {truth_row.get(spec[1]) if truth_row else '?'})"
        return "missed", ""

    def score_injected(self) -> pd.DataFrame:
        self.staged = self.staged_text()
        log = self.log[self.log["expected_handling"] != "undetectable"].copy()
        results = [self.outcome(r) for r in log.itertuples()]
        log["outcome"] = [o for o, _ in results]
        log["outcome_note"] = [n for _, n in results]
        group_of = {t: g for g, types in self.groups.items() for t in types}
        log["group"] = log["error_type"].map(group_of).fillna("unclassified")
        self.scored = log
        return log

    @staticmethod
    def tally(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
        out = (df.pivot_table(index=by, columns="outcome", values="error_id", aggfunc="count", fill_value=0)
               .reindex(columns=["fixed", "flagged", "missed"], fill_value=0).reset_index())
        out["total"] = out[["fixed", "flagged", "missed"]].sum(axis=1)
        out["fixed_or_flagged_%"] = (100 * (out["fixed"] + out["flagged"]) / out["total"]).round(1)
        return out

    # ---------------------------------------------------------------- (c) false corrections
    def false_corrections(self) -> tuple[pd.DataFrame, int]:
        rows, compared = [], 0
        for entity, spec in COMPARE.items():
            raw = pd.read_parquet(self.staging / f"ingested_{entity}.parquet")
            raw_rows = {self.pos(r["source_file"], r["source_sheet"], r["source_row"]): r for r in raw.to_dict("records")}
            for p, clean_row in self.clean_rows[entity].items():
                truth_row = self.truth[entity].get(p)
                if truth_row is None:
                    continue
                present = self.fields_in_sheet.get((p[0], p[1]), set())
                injected = self.log_cells.get(p, set())
                for fld, (clean_col, truth_col, kind) in spec.items():
                    if fld not in present or fld in injected:
                        continue
                    if fld == "age" and "dob" in present:
                        continue
                    compared += 1
                    if not equal(clean_row.get(clean_col), truth_row.get(truth_col), kind):
                        knock_on = bool(DEPENDS_ON.get(fld, set()) & injected)
                        rows.append(dict(entity=entity, field=fld, source_file=p[0], source_sheet=p[1],
                                         source_row=p[2], raw_value=raw_rows.get(p, {}).get(fld),
                                         clean_value=clean_row.get(clean_col), true_value=truth_row.get(truth_col),
                                         kind="knock-on from an injected error on the same row" if knock_on
                                         else "clean value wrongly changed"))
        return pd.DataFrame(rows), compared

    def false_flags(self) -> pd.DataFrame:
        multi = set(self.truth_regs.loc[self.truth_regs["is_duplicate"] == "True", "person_id"])
        reg_person = {p: r["person_id"] for p, r in self.truth["registration"].items()}
        rows = []
        for (p, fld), codes in self.flags.items():
            if self.log_cells.get(p):
                continue
            for code in codes:
                if code == "possible_duplicate_person" and reg_person.get(p) in multi:
                    continue
                rows.append(dict(source_file=p[0], source_sheet=p[1], source_row=p[2], field=fld, issue_code=code))
        return pd.DataFrame(rows, columns=["source_file", "source_sheet", "source_row", "field", "issue_code"])

    def lost_and_spurious(self) -> tuple[int, int]:
        lost = sum(1 for e in COMPARE for p in self.truth[e] if p not in self.clean_rows[e])
        spurious = sum(1 for e in COMPARE for p in self.clean_rows[e] if p not in self.truth[e])
        return lost, spurious

    # ---------------------------------------------------------------- (d) duplicates
    def duplicate_matching(self) -> tuple[pd.DataFrame, list[float]]:
        ids = ingest.load_registration_identities(self.raw, self.settings, self.overlays)
        person = {p: r["person_id"] for p, r in self.truth["registration"].items()}
        ids["person_id"] = [person.get(self.pos(f, s, r)) for f, s, r in
                            zip(ids["source_file"], ids["source_sheet"], ids["source_row"])]
        # True pairs are counted over EVERY registration in the answer key, including files the
        # pipeline could not read, so unreadable files lower recall instead of being ignored.
        all_regs = self.truth_regs[self.truth_regs["source_row"] != ""]
        true_pairs = sum(comb(k, 2) for k in all_regs["person_id"].value_counts())
        people = pd.read_csv(self.truth_dir / "SYNTHETIC_truth_people.csv", dtype=str, keep_default_na=False)
        namesake_of = dict(zip(people["person_id"], people.get("namesake_of", pd.Series([""] * len(people)))))
        namesake_pairs = [(a, b) for a, b in namesake_of.items() if b]
        rows = []
        thresholds = sorted(set(self.settings["duplicate_matching"]["thresholds_to_compare"]
                                + [self.settings["duplicate_matching"]["name_similarity_threshold"]]))
        variants = [("full rules (as used by the pipeline)", True, True),
                    ("names + vetoes, no ID rule", False, True),
                    ("names only, no vetoes, no ID rule", False, False)]
        persons = ids["person_id"].tolist()
        for (variant, use_id, use_veto), t in [(v, t) for v in variants for t in thresholds]:
            review: list = []
            ids["cluster"] = ingest.cluster_identities(ids, t, self.settings, use_id, use_veto, review_pairs=review)
            if use_veto:
                review += ingest.initials_review_pairs(ids, self.settings)
            review = sorted({(i, j) for i, j in review if ids["cluster"].iat[i] != ids["cluster"].iat[j]})
            review_true = sum(1 for i, j in review if persons[i] and persons[i] == persons[j])
            namesake_set = {frozenset(x) for x in namesake_pairs}
            review_namesakes = sum(1 for i, j in review if frozenset((persons[i], persons[j])) in namesake_set)
            predicted = sum(comb(k, 2) for k in ids["cluster"].value_counts())
            tp = sum(comb(k, 2) for k in ids.groupby(["cluster", "person_id"]).size())
            merged_wrongly = int((ids.groupby("cluster")["person_id"].nunique() > 1).sum())
            clusters_of = ids.groupby("person_id")["cluster"].agg(set).to_dict()
            namesakes_merged = sum(1 for a, b in namesake_pairs if clusters_of.get(a, set()) & clusters_of.get(b, set()))
            rows.append(dict(rules=variant, threshold=t, configured="yes" if t == self.settings["duplicate_matching"][
                "name_similarity_threshold"] else "", true_pairs=true_pairs, pairs_found=predicted,
                             correct_pairs=tp, wrong_pairs=predicted - tp, missed_pairs=true_pairs - tp,
                             precision=round(tp / predicted, 3) if predicted else None,
                             recall=round(tp / true_pairs, 3) if true_pairs else None,
                             clusters_mixing_different_people=merged_wrongly,
                             pairs_sent_to_review=len(review), true_pairs_in_review=review_true,
                             recall_merged_or_reviewed=round((tp + review_true) / true_pairs, 3) if true_pairs else None,
                             namesake_pairs_merged=f"{namesakes_merged} of {len(namesake_pairs)}" if namesake_pairs
                             else "n/a",
                             namesake_pairs_reviewed=review_namesakes if namesake_pairs else "n/a"))
        # Name scores of the true duplicate pairs, to show where they fall against the thresholds.
        scores = []
        for _, g in ids.groupby("person_id"):
            names = g["name"].tolist()
            scores += [fuzz.token_sort_ratio(a, b) for i, a in enumerate(names) for b in names[i + 1:]]
        return pd.DataFrame(rows), sorted(scores)

    # ---------------------------------------------------------------- report
    def run(self) -> dict:
        scored = self.score_injected()
        by_type = self.tally(scored, ["group", "error_type"]).sort_values(["group", "fixed_or_flagged_%"])
        by_type["below_90%"] = by_type["fixed_or_flagged_%"].map(lambda v: "YES" if v < 90 else "")
        by_group = self.tally(scored, ["group"])
        false_corr, compared = self.false_corrections()
        false_flag = self.false_flags()
        lost, spurious = self.lost_and_spurious()
        dupes, dup_scores = self.duplicate_matching()
        out = self.staging
        by_type.to_csv(out / "score_by_error_type.csv", index=False)
        scored.to_csv(out / "score_injected_errors.csv", index=False)
        false_corr.to_csv(out / "score_false_corrections.csv", index=False)
        false_flag.to_csv(out / "score_false_flags.csv", index=False)
        dupes.to_csv(out / "score_duplicate_thresholds.csv", index=False)
        undetectable = self.log[self.log["expected_handling"] == "undetectable"]
        return dict(by_type=by_type, by_group=by_group, false_corrections=false_corr, compared=compared,
                    false_flags=false_flag, lost=lost, spurious=spurious, duplicates=dupes,
                    duplicate_scores=dup_scores, scored=scored, undetectable=undetectable)


# ======================================================================================
# Running the pipeline on a test set, and writing the scorecard
# ======================================================================================
def run_pipeline_on(raw, staging, overlays: tuple[str, ...] = ()) -> dict:
    """Run ingest + clean, unchanged, on a test set (optionally with extra mapping files).

    Sheets the pipeline cannot recognise are skipped by ingest.py itself and listed in
    skipped_sheets.csv. If the pipeline still crashes, the crash is recorded and the run is
    repeated with the skipped files set aside, so a score is always produced.
    """
    staging.mkdir(parents=True, exist_ok=True)
    try:
        ingest.run(raw, staging, mapping_overlays=overlays)
        clean.run(staging)
        crash = None
    except Exception:
        crash = traceback.format_exc(limit=3)
        inventory = pd.read_csv(staging / "sheet_inventory.csv", dtype=str, keep_default_na=False)
        bad = set(inventory.loc[inventory["note"].str.startswith("skipped"), "source_file"])
        readable = staging.parent / f"{staging.name}_readable_only"
        shutil.rmtree(readable, ignore_errors=True)
        readable.mkdir(parents=True)
        for path in raw.glob("*.xlsx"):
            if path.name not in bad:
                shutil.copy2(path, readable / path.name)
        ingest.run(readable, staging, mapping_overlays=overlays)
        clean.run(staging)
        raw = readable
    skipped = pd.read_csv(staging / "skipped_sheets.csv", dtype=str, keep_default_na=False)
    return dict(raw=raw, crash=crash, skipped=skipped, overlays=tuple(overlays))


def headline_lines(r: dict) -> list[str]:
    genuine = r["by_group"].set_index("group").loc["genuine_errors"]
    fc = r["false_corrections"]
    wrong = int((fc["kind"] == "clean value wrongly changed").sum()) if len(fc) else 0
    below = r["by_type"][r["by_type"]["below_90%"] == "YES"]
    return [
        f"- Genuine errors fixed or flagged: **{genuine['fixed_or_flagged_%']}%** "
        f"({int(genuine['fixed'] + genuine['flagged']):,} of {int(genuine['total']):,}). Target 95%: "
        f"**{'met' if genuine['fixed_or_flagged_%'] >= 95 else 'NOT met'}**.",
        f"- Error types below 90%: **{len(below)}**" + (f" ({', '.join(below['error_type'])})" if len(below) else "")
        + ".",
        f"- False corrections: **{wrong}** clean values wrongly changed, out of {r['compared']:,} clean cells "
        f"compared ({100 * wrong / max(1, r['compared']):.3f}%); {len(fc) - wrong} more were wrong only as a "
        "knock-on from an injected error on the same row.",
        f"- Rows in the answer key missing from the cleaned tables: {r['lost']}. "
        f"Rows that should not be there: {r['spurious']}.",
    ]


def section_lines(r: dict, title: str, level: str = "##") -> list[str]:
    """Tables (a) to (d) for one test set."""
    fc = r["false_corrections"]
    sub_level = level + "#"
    thresholds = load_settings()["duplicate_matching"]
    scores = r["duplicate_scores"]
    missed = r["scored"][r["scored"]["outcome"] == "missed"]
    lines = [f"{level} {title}", "", *headline_lines(r), "",
             f"{sub_level} (b) Totals by group", "", md_table(r["by_group"]), "",
             f"{sub_level} (a) Fixed, flagged and missed by error type", "", md_table(r["by_type"]), "",
             f"{sub_level} (c) False corrections", "",
             "Every cleaned cell that had no injected problem was compared with its true value.", ""]
    if len(fc):
        lines += [md_table(fc.groupby(["kind", "entity", "field"]).size().reset_index(name="cells")), "",
                  "Examples:", "", md_table(fc.head(10)[["entity", "field", "source_file", "source_row", "raw_value",
                                                        "clean_value", "true_value", "kind"]]), ""]
    else:
        lines += ["None found.", ""]
    ff = r["false_flags"]
    lines += ["Flags on rows with no injected problem at all (for information; a flag does not change a value):",
              "", md_table(ff.groupby("issue_code").size().reset_index(name="rows")) if len(ff) else "None.", "",
              f"{sub_level} (d) Duplicate beneficiaries: matching threshold", "",
              "Pairs of registrations of the same person. Precision = share of matched pairs that are right; "
              "recall = share of true pairs found. Same national ID = always matched; otherwise names must score at "
              "least the threshold, in the same district and of the same sex, and are kept apart if phones differ "
              f"by more than {thresholds['max_phone_digit_difference']} digit, IDs differ, or ages differ by more "
              f"than {thresholds['max_age_difference_years']} years. The two lower variants switch rules off only "
              "to show what each rule contributes.", "",
              md_table(r["duplicates"]), "",
              (f"Name scores of the {len(scores)} true duplicate pairs read by the pipeline: lowest {min(scores):.0f}, "
               + ", ".join(f"{sum(x < t for x in scores)} below {t}" for t in thresholds["thresholds_to_compare"])
               + ".") if scores else "", "",
              f"{sub_level} Missed problems", ""]
    if len(missed):
        summary = missed.groupby(["error_type", "outcome_note"]).size().reset_index(name="count") \
            .sort_values("count", ascending=False)
        lines += [md_table(summary.head(25)), "",
                  md_table(missed[["error_type", "source_file", "source_sheet", "source_row", "field", "true_value",
                                   "messy_value", "outcome_note"]].head(25)), ""]
        if len(missed) > 25:
            lines += [f"... {len(missed) - 25} more in score_injected_errors.csv.", ""]
    else:
        lines += ["None.", ""]
    return lines


def review_queue_lines(staging, title: str) -> list[str]:
    """Flag severity: monthly review-queue size, its drivers, quarantine and info measures."""
    s = load_settings()
    status = pd.read_parquet(staging / "clean_row_status.parquet")
    issues = pd.read_parquet(staging / "issues.parquet")
    import validate
    info = validate.Validator(staging).metrics()           # the single definitions (config/dq_metrics.yaml)
    per_row = s["review_minutes_per_row"]
    budget = s["review_budget_minutes_per_month"]
    review = status[status["status"] == "review"]
    import validate
    monthly = validate.review_queue_monthly(review, s)      # same definition as the data-quality report
    window = monthly.index
    over = monthly[monthly * per_row > budget]
    drivers = (review.assign(code=review["warning_codes"].str.split(", ")).explode("code")
               .groupby("code").size().sort_values(ascending=False))
    quarantine = status[status["status"] == "quarantine"]
    q_monthly = quarantine.groupby("month").size().reindex(window, fill_value=0)
    q_drivers = (quarantine.assign(code=quarantine["critical_codes"].str.split(", ")).explode("code")
                 .groupby("code").size().sort_values(ascending=False))
    sev = issues[issues["severity"].notna()].groupby("severity").size()
    lines = [f"## {title}", "",
             "Each flag has one of three levels (`flag_severity` in config/settings.yaml): **critical** = row "
             "quarantined until the source file is corrected; **warning** = row used, but goes to the MEAL "
             "officer's review queue; **info** = counted as a data-quality measure, no one acts on a row. A row "
             "with any critical flag is quarantined and not also counted in the review queue.", "",
             f"Flags by level: critical {sev.get('critical', 0):,}, warning {sev.get('warning', 0):,}, "
             f"info {sev.get('info', 0):,}.", "",
             "### Review queue (warnings) per month", "",
             f"At {per_row} minutes a row (an assumption to check with the MEAL officer), the budget of "
             f"{budget} minutes a month allows {budget // per_row} rows.", "",
             f"- Rows to review over {len(window)} months: **{int(monthly.sum())}**; per month: average "
             f"**{monthly.mean():.1f}**, median {monthly.median():.0f}, busiest month {int(monthly.max())} "
             f"({monthly.idxmax()}), about {monthly.mean() * per_row:.0f} minutes a month on average.",
             f"- Months over the one-hour budget: **{len(over)}**"
             + (f" ({', '.join(over.index)})" if len(over) else "") + ".",
             f"- Rows with no month (e.g. donor records): {int(review['month'].isna().sum())}.", "",
             "What drives the review queue (a row can have more than one reason):", "",
             md_table(drivers.rename("rows").reset_index().assign(
                 per_month=lambda d: (d["rows"] / len(window)).round(1))), "",
             "Rows to review by month:", "",
             md_table(pd.DataFrame({"month": monthly.index, "rows to review": monthly.values,
                                    "minutes": monthly.values * per_row,
                                    "quarantined": q_monthly.values})), "",
             "### Quarantined rows (critical)", "",
             f"- Rows quarantined: **{len(quarantine)}** (per month: average {q_monthly.mean():.1f}, "
             f"busiest {int(q_monthly.max())}). These are fixed in the source Excel file, not in the queue.", "",
             md_table(q_drivers.rename("rows").reset_index()), "",
             "### Info-level measures (for the dashboard, not for review)", "",
             md_table(info[["metric", "percent", "numerator", "denominator", "note"]]), ""]
    return lines


def manual_lines() -> list[str]:
    """Score hand-made files in data/holdout/manual/ against the answer key the teammate wrote."""
    folder = resolve_path("holdout_manual")
    raw = folder / "raw"
    key_file = folder / "answer_key.csv"
    files = [p for p in raw.glob("*.xlsx") if not p.name.startswith("~$")] if raw.exists() else []
    lines = ["## Hand-made test files (data/holdout/manual)", ""]
    if not files or not key_file.exists():
        return lines + ["No hand-made files yet. See data/holdout/manual/README.md.", ""]
    master = resolve_path("raw") / "SYNTHETIC_programme_master.xlsx"
    if not any("programme_master" in p.name for p in files) and master.exists():
        shutil.copy2(master, raw / master.name)
    staging = folder / "staging"
    run = run_pipeline_on(raw, staging)
    key = pd.read_csv(key_file, dtype=str, keep_default_na=False)
    inventory = pd.read_csv(staging / "sheet_inventory.csv", dtype=str, keep_default_na=False)
    entity_of = {(r.source_file, r.source_sheet): r.entity for r in inventory.itertuples()}
    issues = pd.read_parquet(staging / "issues.parquet")
    flags = defaultdict(set)
    for r in issues[issues["action"] == "flagged"].dropna(subset=["source_row"]).itertuples():
        flags[(r.source_file, r.source_sheet, int(r.source_row), r.field)].add(r.issue_code)
    tables = {e: pd.read_parquet(staging / f"clean_{e}.parquet") for e in COMPARE}
    rows = {e: {(r["source_file"], r["source_sheet"], int(r["source_row"])): r for r in df.to_dict("records")}
            for e, df in tables.items()}
    manual_compare = {e: {**spec, "village": ("village", None, "text")} for e, spec in COMPARE.items()}
    results = []
    for k in key.itertuples():
        pos = (k.source_file, k.source_sheet, int(float(k.source_row)))
        entity = entity_of.get((k.source_file, k.source_sheet))
        spec = manual_compare.get(entity, {}).get(k.field)
        row = rows.get(entity, {}).get(pos)
        same = bool(spec and row is not None and equal(row.get(spec[0]), k.true_value, spec[2]))
        flagged = bool(flags.get((*pos, k.field)))
        if not k.error_type:
            outcome = "unchanged (correct)" if same else "FALSE CORRECTION"
        else:
            outcome = "fixed" if same else "flagged" if flagged else "missed"
        results.append(dict(source_file=k.source_file, source_row=pos[2], field=k.field,
                            error_type=k.error_type or "(clean cell)", true_value=k.true_value,
                            clean_value=None if row is None or not spec else row.get(spec[0]), outcome=outcome))
    res = pd.DataFrame(results)
    res.to_csv(staging / "score_manual.csv", index=False)
    lines += [f"{len(files)} file(s), {len(key)} answer-key cells."]
    if run["crash"]:
        lines += ["", "**The pipeline crashed** on these files; see the error in the run log."]
    if len(run["skipped"]):
        lines += ["", f"Sheets skipped (layout not recognised): {', '.join(run['skipped']['source_file'])}."]
    lines += ["", md_table(res.groupby(["error_type", "outcome"]).size().reset_index(name="cells")), ""]
    return lines


def queue_summary(staging) -> dict:
    """Review-queue and quarantine figures for one test set (for the side-by-side table)."""
    settings = load_settings()
    status = pd.read_parquet(staging / "clean_row_status.parquet")
    import validate
    review = validate.review_queue_monthly(status[status["status"] == "review"], settings)
    budget = settings["review_budget_minutes_per_month"] // settings["review_minutes_per_row"]
    return dict(review_avg=round(review.mean(), 1), review_max=int(review.max()),
                months_over=int((review > budget).sum()),
                quarantined=int((status["status"] == "quarantine").sum()))


def frozen_v1_figures() -> dict:
    """Held-out-1 figures from the frozen v1 scorecard (the 'before' column)."""
    path = resolve_path("docs") / "phase2_scorecard_v1_holdout1.md"
    out = {}
    if not path.exists():
        return out
    import re
    text = path.read_text(encoding="utf-8")
    for group in ("genuine_errors", "officer_habits", "matching_traps", "privacy"):
        m = re.search(rf"\| {group} \| ([\d.]*) \| ([\d.]*) \|", text)
        if m:
            out[group] = m.group(2)
    m = re.search(r"### Held-out results in full.*?False corrections: \*\*(\d+)\*\*", text, re.S)
    if m:
        out["false_corrections"] = m.group(1)
    return out


def summary_row(name: str, r: dict, run: dict, staging) -> dict:
    groups = r["by_group"].set_index("group")["fixed_or_flagged_%"]
    fc = r["false_corrections"]
    wrong = int((fc["kind"] == "clean value wrongly changed").sum()) if len(fc) else 0
    configured = r["duplicates"][(r["duplicates"]["configured"] == "yes")].iloc[0]
    q = queue_summary(staging)
    below = r["by_type"][r["by_type"]["below_90%"] == "YES"]
    return {"set": name,
            "genuine errors %": groups.get("genuine_errors"),
            "officer habits %": groups.get("officer_habits"),
            "namesakes kept apart %": groups.get("matching_traps", "n/a"),
            "privacy %": groups.get("privacy"),
            "types below 90%": len(below),
            "false corrections": f"{wrong} of {r['compared']:,}",
            "rows missing": r["lost"],
            "duplicate precision": configured["precision"],
            "duplicate recall (merged)": configured["recall"],
            "duplicate recall (merged or reviewed)": configured["recall_merged_or_reviewed"],
            "review queue per month (avg / busiest)": f"{q['review_avg']} / {q['review_max']}",
            "months over 1 hour": q["months_over"],
            "rows quarantined": q["quarantined"],
            "sheets skipped": len(run["skipped"]),
            "crashed": "YES" if run["crash"] else "no"}


TEST_SETS = {
    # key: (name, raw folder key, answer key folder key, staging folder key, mapping overlays, generator config)
    "main": ("Main set (seed 2023)", "raw", "ground_truth", "staging", (), None),
    "holdout1": ("Held-out 1, as is (seed 7919)", "holdout_raw", "holdout_ground_truth", "holdout_staging", (),
                 "synthetic_holdout.yaml"),
    "holdout1_fo05": ("Held-out 1 + FO05 mapping in config", "holdout_raw", "holdout_ground_truth",
                      "holdout_fo05_staging", ("mapping_overlays/holdout1_fo05.yaml",), "synthetic_holdout.yaml"),
    "holdout2": ("Held-out 2 (seed 4243)", "holdout2_raw", "holdout2_ground_truth", "holdout2_staging", (),
                 "synthetic_holdout2.yaml"),
    "holdout2_fix1": ("Held-out 2 after this round's fixes (seen data)", "holdout2_raw", "holdout2_ground_truth",
                      "holdout2_fix1_staging", (), "synthetic_holdout2.yaml"),
    "holdout2_fo06": ("Held-out 2 after the fixes + FO06 mapping in config (seen data)", "holdout2_raw",
                      "holdout2_ground_truth", "holdout2_fo06_staging", ("mapping_overlays/holdout2_fo06.yaml",),
                      "synthetic_holdout2.yaml"),
}
DEFAULT_RUNS = ["main", "holdout2_fix1", "holdout2_fo06"]
FROZEN_V2 = "phase2_scorecard_v2_holdout2.md"
FROZEN_V2_COLUMNS = {   # column in the frozen v2 table -> column in the v3 side-by-side table
    "Held-out 1 + FO05 mapping in config": "Held-out 1 + FO05 mapping (v2, seen data)",
    "Held-out 2 (seed 4243, fresh mess) - HEADLINE": "HEADLINE: held-out 2 (v2, code 2754c99, never tuned on)",
}


def frozen_side_table(name: str) -> pd.DataFrame:
    """Read the side-by-side table from a frozen scorecard (index = measure)."""
    lines = (resolve_path("docs") / name).read_text(encoding="utf-8").splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith("| measure |"))
    rows = []
    for line in lines[start:]:
        if not line.startswith("|"):
            break
        rows.append([c.strip() for c in line.strip().strip("|").split("|")])
    header, body = rows[0], [r for r in rows[2:]]
    return pd.DataFrame(body, columns=header).set_index("measure")


def score_reconciliation(truth_dir, db) -> dict | None:
    """How well the reconciliation finds the discrepancies planted in the synthetic reports.

    Scored at the reporting grain (project, district, month and, for AGR-01, sex) for every report row that was
    submitted. Every flag on a row with no planted discrepancy is explained, where possible, by an injected data
    problem: on the report side (the cleaned reported value differs from what the officer meant to report), or on
    the records side (the derived value differs from the true value, e.g. because of quarantined rows).
    """
    import duckdb
    planted_file = truth_dir / "SYNTHETIC_planted_discrepancies.csv"
    if not planted_file.exists():
        return None
    truth = pd.read_csv(truth_dir / "SYNTHETIC_truth_indicator_results.csv", keep_default_na=False, dtype=str)
    truth = truth[(truth["discrepancy"].notna()) & truth["indicator_code"].isin(["WASH-01", "AGR-01"])
                  & (truth["submitted"] == "True")].copy()
    truth["disaggregation"] = truth["sex"].map(lambda x: f"sex={x.lower()}" if x else "total")
    truth["period"] = truth["period"].str[:7]
    con = duckdb.connect(str(db), read_only=True)
    rec = con.execute("""SELECT * FROM indicator_reconciliation
                         WHERE project_id <> 'All' AND district <> 'All'""").df()
    con.close()
    keys = ["indicator_code", "project_id", "district", "period", "disaggregation"]
    m = truth.merge(rec, on=keys, how="left")
    m["kind"] = m["discrepancy"].replace("", "none")
    for c in ("actual_value", "true_value"):
        m[c] = pd.to_numeric(m[c])
    m["flag"] = m["flag"].fillna(False).astype(bool)

    def outcome(r):
        if r.kind in ("over_report", "under_report"):
            if r.flag:
                return "caught"
            return "missed (report row quarantined)" if pd.isna(r.reported) else "missed"
        if not r.flag:
            return "correctly within tolerance"
        if not pd.isna(r.reported) and abs(r.reported - r.actual_value) > 1e-9:
            return "flag explained: report-side data error"
        if abs((0 if pd.isna(r.derived) else r.derived) - r.true_value) > 1e-9:
            return "flag explained: records-side data issue"
        return "false alarm (unexplained)"

    m["outcome"] = [outcome(r) for r in m.itertuples()]
    planted = m[m["kind"].isin(["over_report", "under_report"])]
    flags = m[m["flag"]]
    caught = int((planted["outcome"] == "caught").sum())
    unexplained = int((m["outcome"] == "false alarm (unexplained)").sum())
    rounding = m[m["kind"] == "rounding"]
    # Since Phase 6 a gap must also be at least reconciliation_min_difference apart (D153). Planted discrepancies
    # smaller than that are below the follow-up threshold BY DESIGN, so they are scored separately.
    min_diff = load_settings()["indicators"].get("reconciliation_min_difference", 0)
    size = (m["actual_value"] - m["true_value"]).abs()
    big = planted[size.loc[planted.index] >= min_diff]
    caught_big = int((big["outcome"] == "caught").sum())
    summary = dict(
        report_rows=len(m), planted=len(planted), caught=caught,
        catch_rate=round(100 * caught / len(planted), 1) if len(planted) else None,
        min_difference=min_diff, planted_at_least_min=len(big), caught_at_least_min=caught_big,
        catch_rate_at_least_min=round(100 * caught_big / len(big), 1) if len(big) else None,
        flags=len(flags), flags_on_planted=int(flags["kind"].isin(["over_report", "under_report"]).sum()),
        precision=round(100 * caught / len(flags), 1) if len(flags) else None,
        explained_flags=int(m["outcome"].str.startswith("flag explained").sum()), false_alarms=unexplained,
        rounding_planted=len(rounding),
        rounding_within=int((rounding["outcome"] == "correctly within tolerance").sum()))
    table = (m.groupby(["indicator_code", "kind", "outcome"]).size().rename("report rows").reset_index())
    m.to_csv(resolve_path("staging") / "score_reconciliation_rows.csv", index=False)
    return dict(summary=summary, table=table, rows=m)


def reconciliation_lines(r: dict) -> list[str]:
    s = r["summary"]
    return ["## Reconciliation scoring (main set)", "",
            "The main set's WASH-01 and AGR-01 reports are worked out from the same true data as the activity and "
            "register files, with discrepancies planted at known rates (decision log D132): two officers over-report "
            "15 to 30% of the time, some months are under-reported by 20 to 50%, and a few figures have 1 to 5% rounding "
            "differences that should stay within the tolerance. Scored on every submitted report row (project, district, "
            "month and, for AGR-01, sex).", "",
            f"- Planted discrepancies (over- and under-reporting) in submitted reports: **{s['planted']}**; flagged: "
            f"**{s['caught']} ({s['catch_rate']}%)**.",
            f"- Of these, **{s['planted_at_least_min']}** are at least {s['min_difference']} apart (the minimum difference "
            f"for a gap, settings: indicators.reconciliation_min_difference); flagged: **{s['caught_at_least_min']} "
            f"({s['catch_rate_at_least_min']}%)**. The other {s['planted'] - s['planted_at_least_min']} are smaller than "
            "the minimum, so they are not flagged by design (decision log D153).",
            f"- Flags raised: {s['flags']}; on a planted discrepancy: {s['flags_on_planted']} (precision {s['precision']}%).",
            f"- Other flags explained by an injected data problem (an extra zero in a report, quarantined or "
            f"duplicate records...): {s['explained_flags']}. **Unexplained false alarms: {s['false_alarms']}.**",
            f"- Planted rounding differences that stayed within the tolerance: {s['rounding_within']} of "
            f"{s['rounding_planted']}.", "",
            md_table(r["table"]), ""]


def score_set(key: str) -> dict:
    import generate_synthetic
    name, raw_key, truth_key, staging_key, overlays, config = TEST_SETS[key]
    raw, truth, staging = resolve_path(raw_key), resolve_path(truth_key), resolve_path(staging_key)
    if not (raw / "SYNTHETIC_programme_master.xlsx").exists():
        if config is None:
            raise SystemExit(f"{name}: no data in {raw}; run python src/generate_synthetic.py first.")
        print(f"{name}: generating it from config/{config} ...")
        generate_synthetic.generate(raw, truth, quiet=True, config_name=config)
    print(f"Scoring: {name}")
    run = run_pipeline_on(raw, staging, overlays)
    result = Scorer(staging, truth, run["raw"], overlays=overlays).run()
    reconciliation = None
    if key == "main":
        # The main set also goes through the rest of the production pipeline, to score the reconciliation.
        import indicators
        import model
        import validate
        validate.run(staging)
        model.run(staging)
        indicators.run()
        reconciliation = score_reconciliation(truth, resolve_path("warehouse"))
    return dict(key=key, name=name, run=run, result=result, staging=staging, reconciliation=reconciliation)


def main(argv: list[str] | None = None):
    import argparse
    parser = argparse.ArgumentParser(description="Score the cleaning against the synthetic answer keys.")
    parser.add_argument("--all", action="store_true",
                        help="re-score every test set, including the held-out sets (for the final round)")
    args = parser.parse_args(argv)
    settings = load_settings()
    if not settings["synthetic_mode"]:
        print("Scoring needs the synthetic answer key; synthetic_mode is off, so nothing to do.")
        return
    keys = list(TEST_SETS) if args.all else DEFAULT_RUNS
    results = [score_set(k) for k in keys]

    side = pd.DataFrame([summary_row(x["name"], x["result"], x["run"], x["staging"]) for x in results]).set_index("set").T
    side.index.name = "measure"
    if not args.all and (resolve_path("docs") / FROZEN_V2).exists():
        frozen = frozen_side_table(FROZEN_V2)
        for old, new in FROZEN_V2_COLUMNS.items():
            side.insert(1 if "FO05" in new else 2, new, frozen[old].reindex(side.index))
    undetectable = results[0]["result"]["undetectable"]
    lines = [
        "# Phase 2 cleaning scorecard v3 (synthetic data)", "",
        f"*Generated by `src/score_cleaning.py` on {dt.date.today():%d %B %Y}. Do not edit by hand. Earlier "
        "versions are frozen: v1 (`docs/phase2_scorecard_v1_holdout1.md`, before any held-out fix) and v2 "
        f"(`docs/{FROZEN_V2}`, which holds the held-out-2 headline).*", "",
        "**Fixed** = the cleaned value equals the true value. **Flagged** = the pipeline marked the cell or row "
        "for review. **Missed** = neither. Problems that cannot be detected from the files are excluded.", "",
        "## Side by side", "",
        "**The headline figure stays held-out 2 as first scored (v2): genuine errors 92.9%.** It was generated "
        "after the code was frozen and has never been used for tuning. Every other held-out column is on data that "
        "has now been seen, so it measures what the fixes recover, not how the cleaner does on new data. The "
        "columns marked v2 are copied from the frozen v2 scorecard; the others were re-scored now.", "",
        md_table(side.reset_index()), "",
        "## Why held-out 2 scored lower: officer FO06", "",
        "FO06's sheets were only **partly** recognisable. The activity sheet had five known column names (District, "
        "Sector, Cell, Village, Total), so in v2 it was read, but its activity date, activity, project, status, "
        "female/male and cost columns had names the pipeline did not know (`Event date`, `Type of activity`, "
        "`Implementation status`, `Females`...). Those rows arrived without their key values: 364 were quarantined "
        "and many injected problems could not be seen. FO06's register was read without its registration number "
        "and registration date. That one officer's files pulled genuine errors from 96.1% to 92.9% and habits "
        "from 100% to 87.5%.", "",
        "This round's fix 1 stops partial reads: a sheet missing any required field is now **skipped** with a "
        "message naming the missing fields and the unrecognised headers. The two right-hand columns show what that "
        "fix achieves alone, and then with the FO06 column names added to the config (`config/mapping_overlays/"
        "holdout2_fo06.yaml`, the lines a maintainer would paste into `source_mappings.yaml`). Neither replaces "
        "the headline.", "",
        "## Known limitations", "",
        f"- {len(undetectable)} problems in the main set cannot be detected from the files (accepted 14 October 2026):",
        "", md_table(undetectable.groupby(["error_type", "detail"]).size().reset_index(name="count")), "",
        "- Nicknames (e.g. `Jado` for Jean de Dieu) are not recognised; there is deliberately no nickname list.",
        "- Similar names, and initials matching a full name, are never merged without a phone or ID; they go to the "
        "review queue, so some true duplicates stay as two people until a person confirms them.",
        "- Month-first dates (`Mar 12, 2024`) are not read, on purpose, until the partner says whether staff use them.",
        "- An ID stored as a number in Excel has lost its 16th digit; it is flagged, but cannot be recovered.",
        "- A sheet with unknown column names, or missing a required field, is skipped and reported, never read "
        "partly: its records are missing until a maintainer adds the column names to `config/source_mappings.yaml`.",
        "- The synthetic data and the cleaner were written by the same team; real partner files are the real test.",
        "",
    ]
    for x in results:
        run = x["run"]
        lines += [f"## {x['name']}", ""]
        if run["overlays"]:
            lines += [f"Run with the extra mapping file `config/{run['overlays'][0]}` (no code change).", ""]
        if run["crash"]:
            lines += ["**The pipeline crashed.**", "", "```", run["crash"].strip(), "```", ""]
        if len(run["skipped"]):
            cols = [c for c in ("source_file", "source_sheet", "reason", "missing_required", "headers_found")
                    if c in run["skipped"].columns]
            lines += ["Sheets skipped (records counted as missed):", "", md_table(run["skipped"][cols]), ""]
        lines += section_lines(x["result"], f"Results: {x['name']}", level="###")
        queue = review_queue_lines(x["staging"], f"Review queue and quarantine: {x['name']}")
        lines += ["#" + l if l.startswith("## ") or l.startswith("### ") else l for l in queue]
    if results[0].get("reconciliation"):
        lines += reconciliation_lines(results[0]["reconciliation"])
    lines += manual_lines()
    (resolve_path("docs") / "phase2_cleaning_scorecard.md").write_text("\n".join(lines), encoding="utf-8")
    print(side.to_string())
    print("Scorecard written to docs/phase2_cleaning_scorecard.md")


if __name__ == "__main__":
    main()
