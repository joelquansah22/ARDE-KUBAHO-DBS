"""Clean and standardise the staged records.

WHAT THIS SCRIPT DOES
---------------------
Reads the tables written by ingest.py (data/staging/ingested_*.parquet), and for
every cell:
  - turns dates typed in any format into real dates,
  - turns district, village, sex, status, stage and other codes into one standard spelling,
  - turns numbers typed as text ("1,250,000 RWF", "45 people") into numbers,
  - links each row to the project, activity and village lists in the programme master.

It then runs row checks (female + male = total, negatives, late entries, outliers,
missing values...). Problems that cannot be safely corrected are FLAGGED, never guessed.

Every change and every flag is written to data/staging/issues.parquet, so each
cleaned value can be traced back to what was typed. Phase 3 (validate.py) turns
these flags into the formal data-quality rules and the quarantine table.

HOW TO RUN
    python src/clean.py      (after python src/ingest.py)
"""

from __future__ import annotations

import calendar
import datetime as dt
import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache

import pandas as pd
from rapidfuzz import fuzz, process

from common import district_to_province, load_admin, load_settings, load_yaml, resolve_path

MONTHS = {name.lower(): i for i, name in enumerate(calendar.month_name) if name}
MONTHS.update({name.lower(): i for i, name in enumerate(calendar.month_abbr) if name})
MONTHS["sept"] = 9

FIXED, FLAGGED, REMOVED = "fixed", "flagged", "removed"


# ======================================================================================
# Small text helpers
# ======================================================================================
def is_blank(value) -> bool:
    return value is None or (isinstance(value, float) and pd.isna(value)) or str(value).strip() == ""


def norm_text(value) -> str | None:
    """Trim spaces and collapse double spaces. Blank becomes None."""
    if is_blank(value):
        return None
    return re.sub(r"\s+", " ", str(value)).strip()


def norm_key(value) -> str:
    """Lower-case, accent-free, no full stops, single spaces: used to compare labels."""
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", text.replace(".", " ")).strip().casefold()


# ======================================================================================
# Dates
# ======================================================================================
@dataclass
class DateResult:
    value: dt.date | None = None
    code: str | None = None        # what was done, e.g. "date_text_converted"
    action: str | None = None      # fixed / flagged / None (nothing needed)
    approx: bool = False           # True when only the month is known


def _month_from_name(text: str) -> int | None:
    return MONTHS.get(text.lower())


def _parse_text_date(text: str, rules: dict) -> dt.date | None:
    """Read day-month-year dates written with a month name ("12 Mar 24", "12th March 2024").

    The accepted styles are listed in settings.yaml (cleaning: date_text_formats). A 2-digit
    year is placed in the 2000s up to two_digit_year_pivot, otherwise in the 1900s.
    """
    if not re.search(r"[A-Za-z]", text) or not re.match(r"\d", text):
        return None
    suffixes = "|".join(rules.get("ordinal_suffixes", []))
    cleaned = re.sub(rf"^(\d{{1,2}})({suffixes})\b", r"\1", text, flags=re.IGNORECASE) if suffixes else text
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    for fmt in rules.get("date_text_formats", []):
        try:
            d = dt.datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
        if "%y" in fmt:
            yy = d.year % 100
            d = d.replace(year=(2000 if yy <= rules.get("two_digit_year_pivot", 30) else 1900) + yy)
        return d
    return None


def parse_date(raw, settings: dict | None = None, period: bool = False) -> DateResult:
    """Read a date typed in any of the formats seen in the files.

    Accepted: 2024-03-12, 12/03/2024 (day first), 45363 (Excel serial number),
    March 2024 / Mar-24 / 2024-03 (month only). With period=True (monthly reports)
    a month on its own is normal and is not flagged.
    """
    settings = settings or load_settings()
    rules = settings["cleaning"]
    if is_blank(raw):
        return DateResult()
    text = str(raw).strip()
    text = re.sub(r"[ T]00:00(:00)?$", "", text)   # a real Excel date read as "2024-03-12 00:00:00"
    try:
        m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", text)
        if m:
            d = dt.date(int(m[1]), int(m[2]), int(m[3]))
            if period and d.day != 1:
                return DateResult(d.replace(day=1), "period_set_to_month_start", FIXED, True)
            return DateResult(d, None, None, period)
        m = re.fullmatch(r"(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})", text)
        if m:
            first, second = int(m[1]), int(m[2])
            day, month = (first, second) if rules["date_day_first"] else (second, first)
            d = dt.date(int(m[3]), month, day)
            return DateResult(d.replace(day=1) if period else d, "date_text_converted", FIXED, period)
        m = re.fullmatch(r"(\d+)(\.0+)?", text)
        if m:
            lo, hi = rules["excel_serial_range"]
            serial = int(m[1])
            if lo <= serial <= hi:
                d = dt.date(1899, 12, 30) + dt.timedelta(days=serial)
                return DateResult(d.replace(day=1) if period else d, "date_serial_converted", FIXED, period)
            return DateResult(None, "date_unreadable", FLAGGED)
        d = _parse_text_date(text, rules)
        if d:
            return DateResult(d.replace(day=1) if period else d, "date_text_converted", FIXED, period)
        m = re.fullmatch(r"([A-Za-z]+)[\s\-/,]+(\d{2}|\d{4})", text)
        if m and _month_from_name(m[1]):
            year = int(m[2]) + (2000 if len(m[2]) == 2 else 0)
            d = dt.date(year, _month_from_name(m[1]), 1 if period else rules["month_only_day"])
            if period:
                return DateResult(d, "period_text_converted", FIXED, True)
            return DateResult(d, "date_day_unknown", FLAGGED, True)
        m = re.fullmatch(r"(\d{4})-(\d{1,2})", text)
        if m:
            d = dt.date(int(m[1]), int(m[2]), 1)
            return DateResult(d, "period_text_converted" if period else "date_day_unknown",
                              FIXED if period else FLAGGED, True)
    except ValueError:            # e.g. 31/02/2024
        pass
    return DateResult(None, "date_unreadable", FLAGGED)


def date_bounds(result: DateResult) -> tuple[dt.date | None, dt.date | None]:
    """Earliest and latest possible date (they differ when only the month is known)."""
    if result.value is None:
        return None, None
    if not result.approx:
        return result.value, result.value
    last = calendar.monthrange(result.value.year, result.value.month)[1]
    return result.value.replace(day=1), result.value.replace(day=last)


# ======================================================================================
# Codes and names
# ======================================================================================
@dataclass
class CodeResult:
    value: str | None = None
    code: str | None = None
    action: str | None = None
    detail: str = ""


def recode(raw, mapping: dict[str, list], name: str) -> CodeResult:
    """Map a typed value onto a standard code using a list of accepted spellings.

    Example: recode("Gore", {"female": ["Female", "F", "Gore"], ...}, "sex") -> "female".
    A value not in the list is FLAGGED and left empty: it is never guessed.
    """
    if is_blank(raw):
        return CodeResult()
    key = norm_key(raw)
    for standard, spellings in mapping.items():
        if key in {norm_key(s) for s in spellings} | {norm_key(standard)}:
            changed = norm_key(raw) != norm_key(standard) or str(raw).strip() != str(raw)
            return CodeResult(standard, f"{name}_recoded" if changed else None, FIXED if changed else None)
    return CodeResult(None, f"{name}_unmapped", FLAGGED, f"'{norm_text(raw)}' is not in the {name} list")


def _strip_noise(text: str, words: list[str]) -> str:
    for word in sorted(words, key=len, reverse=True):
        text = re.sub(rf"\b{re.escape(word)}\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()


@lru_cache(maxsize=None)
def load_legacy_districts() -> dict:
    """Old district names (config/district_legacy_map.yaml), keyed by their normalised spelling."""
    cfg = load_yaml("district_legacy_map.yaml")
    return {"one_to_one": {norm_key(k): v for k, v in (cfg.get("one_to_one") or {}).items()},
            "ambiguous": {norm_key(k): v["candidates"] for k, v in (cfg.get("ambiguous") or {}).items()}}


def standardise_district(raw, settings: dict | None = None) -> CodeResult:
    """Return the official district name for 'NYAGATARE', 'Nyagatare District', 'Nyagatre', ..."""
    settings = settings or load_settings()
    if is_blank(raw):
        return CodeResult()
    districts = list(district_to_province())
    lookup = {d.casefold(): d for d in districts}
    text = _strip_noise(norm_key(raw), settings["cleaning"]["district_noise_words"])
    if text in lookup:
        changed = str(raw) != lookup[text]
        return CodeResult(lookup[text], "district_standardised" if changed else None, FIXED if changed else None)
    legacy = load_legacy_districts()
    if text in legacy["one_to_one"]:
        new = legacy["one_to_one"][text]
        return CodeResult(new, "district_legacy_name_mapped", FIXED, f"old name '{norm_text(raw)}' = {new}")
    if text in legacy["ambiguous"]:
        candidates = legacy["ambiguous"][text]
        return CodeResult(None, "district_legacy_name_ambiguous", FLAGGED,
                          f"old name '{norm_text(raw)}' could be {', '.join(candidates)}")
    best = process.extract(text, list(lookup), scorer=fuzz.ratio, limit=2)
    min_score = settings["cleaning"]["district_fuzzy_min_score"]
    if best and best[0][1] >= min_score and (len(best) == 1 or best[0][1] - best[1][1] >= 5):
        return CodeResult(lookup[best[0][0]], "district_typo_corrected", FIXED,
                          f"'{norm_text(raw)}' read as {lookup[best[0][0]]} (score {best[0][1]:.0f})")
    return CodeResult(None, "district_unrecognised", FLAGGED, f"'{norm_text(raw)}' is not a district")


def standardise_province(raw) -> CodeResult:
    if is_blank(raw):
        return CodeResult()
    admin = load_admin()
    mapping = {p: [p, f"{p} Province"] + admin["province_aliases"].get(p, []) for p in admin["provinces"]}
    return recode(raw, mapping, "province")


# ======================================================================================
# Numbers
# ======================================================================================
@dataclass
class NumberResult:
    value: float | None = None
    code: str | None = None
    action: str | None = None
    currency: str = "RWF"
    detail: str = ""


def parse_number(raw, settings: dict | None = None) -> NumberResult:
    """Read '1,250,000 RWF', 'RWF 1 250 000', '45 people', '12 ha', '72%', 'USD 3,000', '3O' ...

    Thousands separators, currency words and units are removed. Letters typed for
    digits on paper forms (O for 0, l for 1) are corrected. Anything still not a
    number is FLAGGED.
    """
    settings = settings or load_settings()
    rules = settings["cleaning"]
    if is_blank(raw):
        return NumberResult()
    text = str(raw).strip()
    try:
        return NumberResult(float(text))
    except ValueError:
        pass
    work = text.casefold()
    currency = "RWF"
    for marker in rules["usd_markers"]:
        if marker in work:
            currency = "USD"
            work = work.replace(marker, " ")
    work = _strip_noise(work, rules["number_noise_words"]).replace("%", "")
    work = re.sub(r"(?<=\d)[,\s'](?=\d{3}\b)", "", work).replace(",", "").replace(" ", "")
    code = "number_text_converted"
    try:
        value = float(work)
    except ValueError:
        fixed = "".join(rules["letter_digit_fixes"].get(ch, ch) for ch in str(raw).strip())
        fixed = re.sub(r"(?<=\d)[,\s](?=\d{3}\b)", "", fixed)
        try:
            value = float(fixed)
            code = "number_letter_typo_fixed"
        except ValueError:
            return NumberResult(None, "number_unreadable", FLAGGED, detail=f"'{text}' is not a number")
    return NumberResult(value, code, FIXED, currency)


# ======================================================================================
# Issue log
# ======================================================================================
@dataclass
class IssueLog:
    """Collects every change and flag. Personal fields never have their values logged."""

    rows: list = field(default_factory=list)

    def add(self, entity, rec, fld, code, action, raw=None, clean=None, detail=""):
        if code is None:
            return
        self.rows.append(dict(entity=entity, source_file=rec["source_file"], source_sheet=rec["source_sheet"],
                              source_row=None if rec.get("source_row") is None else int(rec["source_row"]),
                              field=fld, issue_code=code, action=action,
                              raw_value=None if raw is None else str(raw),
                              clean_value=None if clean is None else str(clean), detail=detail))

    def frame(self) -> pd.DataFrame:
        cols = ["entity", "source_file", "source_sheet", "source_row", "field", "issue_code", "action",
                "raw_value", "clean_value", "detail"]
        return pd.DataFrame(self.rows, columns=cols)


# ======================================================================================
# Reference data (programme master)
# ======================================================================================
class Reference:
    """Projects, activities and villages from the programme master, for linking rows."""

    def __init__(self, staging):
        self.projects = pd.read_parquet(staging / "ref_project.parquet")
        self.activities = pd.read_parquet(staging / "ref_activity.parquet")
        self.locations = pd.read_parquet(staging / "ref_location.parquet")
        self.project_by_key = {}
        for p in self.projects.itertuples():
            self.project_by_key[norm_key(p.project_id)] = p.project_id
            self.project_by_key[norm_key(p.name)] = p.project_id
        self.project_window = {p.project_id: (dt.date.fromisoformat(str(p.start_date)[:10]),
                                              dt.date.fromisoformat(str(p.end_date)[:10]))
                               for p in self.projects.itertuples()}
        self.activity_by_key = {(norm_key(a.activity_name)): a.activity_id for a in self.activities.itertuples()}
        self.activity_project = dict(zip(self.activities.activity_id, self.activities.project_id))
        # Villages by district, with their spellings already normalised, so each row is a quick
        # dictionary lookup rather than a search through the whole table.
        self.locs_by_district = {
            d: [dict(r, _sector=norm_key(r["sector"]), _village=norm_key(r["village"]))
                for r in g.to_dict("records")]
            for d, g in self.locations.groupby("district")}
        self.districts_of_village: dict[str, set] = {}
        for r in self.locations.to_dict("records"):
            self.districts_of_village.setdefault(norm_key(r["village"]), set()).add(r["district"])
        catalogue = load_yaml("indicator_catalogue.yaml")["indicators"]
        self.indicators = {i["code"]: i for i in catalogue}
        self.indicator_by_key = {}
        for i in catalogue:
            self.indicator_by_key[norm_key(i["code"])] = i["code"]
            self.indicator_by_key[norm_key(i["name"])] = i["code"]

    def project(self, raw) -> CodeResult:
        if is_blank(raw):
            return CodeResult()
        pid = self.project_by_key.get(norm_key(raw))
        if pid:
            return CodeResult(pid)          # a lookup, not a correction: nothing to log
        return CodeResult(None, "project_unrecognised", FLAGGED, f"'{norm_text(raw)}' is not a known project")

    def activity(self, raw) -> CodeResult:
        if is_blank(raw):
            return CodeResult()
        aid = self.activity_by_key.get(norm_key(raw))
        if aid:
            return CodeResult(aid)
        return CodeResult(None, "activity_unrecognised", FLAGGED, f"'{norm_text(raw)}' is not a known activity")

    def location(self, district, sector, cell, village, settings) -> tuple[dict | None, CodeResult]:
        """Find the village in the stated district (exact, then closest spelling)."""
        if district is None or is_blank(village) or district not in self.locs_by_district:
            return None, CodeResult()
        locs = self.locs_by_district[district]
        if not is_blank(sector):
            same_sector = [loc for loc in locs if loc["_sector"] == norm_key(sector)]
            if same_sector:
                locs = same_sector
        wanted = norm_key(village)
        exact = [loc for loc in locs if loc["_village"] == wanted]
        if len(exact) == 1:
            return exact[0], CodeResult(exact[0]["location_id"])
        best = process.extract(wanted, [loc["_village"] for loc in locs], scorer=fuzz.ratio, limit=2)
        min_score = settings["cleaning"]["village_fuzzy_min_score"]
        if best and best[0][1] >= min_score and (len(best) == 1 or best[0][1] - best[1][1] >= 5):
            row = locs[best[0][2]]
            return row, CodeResult(row["location_id"], "village_spelling_corrected", FIXED,
                                   f"'{norm_text(village)}' read as {row['village']} (score {best[0][1]:.0f})")
        return None, CodeResult(None, "village_unrecognised", FLAGGED,
                                f"'{norm_text(village)}' is not a village in {district}")


# ======================================================================================
# Cleaning each kind of record
# ======================================================================================
class Cleaner:
    def __init__(self, staging, settings: dict | None = None):
        self.staging = staging
        self.s = settings or load_settings()
        self.dq = self.s["data_quality"]
        self.ref = Reference(staging)
        self.log = IssueLog()
        self.d2p = district_to_province()

    # ---------------------------------------------------------------- shared steps
    def _date(self, entity, rec, fld, period=False) -> DateResult:
        result = parse_date(rec.get(fld), self.s, period=period)
        self.log.add(entity, rec, fld, result.code, result.action, rec.get(fld),
                     result.value.isoformat() if result.value else None)
        return result

    def _code(self, entity, rec, fld, result: CodeResult) -> str | None:
        self.log.add(entity, rec, fld, result.code, result.action, rec.get(fld), result.value, result.detail)
        return result.value

    def _number(self, entity, rec, fld, kind="count") -> float | None:
        result = parse_number(rec.get(fld), self.s)
        if result.currency == "USD" and result.value is not None:
            rate = self.s["currency"]["usd_to_rwf"]
            self.log.add(entity, rec, fld, "usd_converted_to_rwf", FIXED, rec.get(fld), result.value * rate,
                         f"converted at {rate} RWF per USD")
            return result.value * rate
        self.log.add(entity, rec, fld, result.code, result.action, rec.get(fld), result.value, result.detail)
        return result.value

    def _required(self, entity, rec, fld, value, raw_present=None):
        if value is None and (is_blank(rec.get(fld)) if raw_present is None else not raw_present):
            self.log.add(entity, rec, fld, "missing_required", FLAGGED, detail=f"{fld} is empty")

    def _location(self, entity, rec, district):
        row, result = self.ref.location(district, rec.get("sector"), rec.get("cell"), rec.get("village"), self.s)
        self._code(entity, rec, "village", result)
        if row is None:
            return dict(location_id=None, sector=norm_text(rec.get("sector")), cell=norm_text(rec.get("cell")),
                        village=norm_text(rec.get("village")))
        return dict(location_id=row["location_id"], sector=row["sector"], cell=row["cell"], village=row["village"])

    def _district(self, entity, rec, has_province: bool):
        result = standardise_district(rec.get("district"), self.s)
        district = self._code(entity, rec, "district", result)
        if result.code == "district_legacy_name_ambiguous" and not is_blank(rec.get("village")):
            candidates = load_legacy_districts()["ambiguous"][
                _strip_noise(norm_key(rec["district"]), self.s["cleaning"]["district_noise_words"])]
            found = self.ref.districts_of_village.get(norm_key(rec["village"]), set()) & set(candidates)
            if len(found) == 1:
                district = next(iter(found))
                self.log.add(entity, rec, "district", "district_legacy_resolved_by_village", FIXED, rec.get("district"),
                             district, f"village {rec['village']} is in {district}; please confirm")
        elif district is None and not is_blank(rec.get("village")):
            # Work out the district from the village when that village name exists in only one
            # district. The original problem (missing or unrecognised district) stays flagged.
            candidates = self.ref.districts_of_village.get(norm_key(rec["village"]), set())
            if len(candidates) == 1:
                district = next(iter(candidates))
                self.log.add(entity, rec, "district", "district_filled_from_village", FIXED, rec.get("district"),
                             district, f"village {rec['village']} is only in {district}")
        province = None
        if has_province:
            province = self._code(entity, rec, "province", standardise_province(rec.get("province")))
            if province and district and self.d2p[district] != province:
                self.log.add(entity, rec, "province", "district_province_mismatch", FLAGGED, rec.get("province"),
                             province, f"{district} is in {self.d2p[district]}, not {province}")
        return district, (province if province else (self.d2p.get(district) if district else None))

    def _count_checks(self, entity, rec, female, male, total):
        for fld, value in (("female", female), ("male", male), ("total", total)):
            if value is not None and value < 0:
                self.log.add(entity, rec, fld, "negative_value", FLAGGED, rec.get(fld), value)
            elif value is not None and value != int(value):
                self.log.add(entity, rec, fld, "not_whole_number", FLAGGED, rec.get(fld), value)
        if female is not None and total is not None and total >= 0 and female > total:
            self.log.add(entity, rec, "female", "female_exceeds_total", FLAGGED, rec.get("female"), female,
                         f"{female:.0f} women out of {total:.0f} participants")
        if None not in (female, male, total) and female + male != total:
            self.log.add(entity, rec, "total", "sum_mismatch", FLAGGED, rec.get("total"), total,
                         f"female {female:.0f} + male {male:.0f} = {female + male:.0f}, not {total:.0f}")

    # ---------------------------------------------------------------- activities
    def clean_activities(self, df: pd.DataFrame) -> pd.DataFrame:
        entity, out = "activity", []
        df = self.remove_exact_duplicates(entity, df)
        has_province = "province" in df.columns
        for rec in df.to_dict("records"):
            date = self._date(entity, rec, "date")
            planned = self._date(entity, rec, "planned_date")
            entry = self._date(entity, rec, "entry_date")
            project_id = self._code(entity, rec, "project", self.ref.project(rec.get("project")))
            activity_id = self._code(entity, rec, "activity", self.ref.activity(rec.get("activity")))
            if project_id is None and activity_id:
                project_id = self.ref.activity_project[activity_id]
            district, province = self._district(entity, rec, has_province)
            loc = self._location(entity, rec, district)
            status = self._code(entity, rec, "status",
                                recode(rec.get("status"), self.s["activity_status_mapping"], "status"))
            female, male, total = (self._number(entity, rec, f) for f in ("female", "male", "total"))
            cost = self._number(entity, rec, "cost")
            if cost is not None and cost < 0:
                self.log.add(entity, rec, "cost", "negative_value", FLAGGED, rec.get("cost"), cost)
            self._count_checks(entity, rec, female, male, total)

            # Required values. A cancelled or not-yet-done activity has no date or participants.
            done = status in ("completed", None) or (status == "delayed" and not is_blank(rec.get("total")))
            for fld, value in (("district", district), ("activity", activity_id), ("village", loc["location_id"]),
                               ("status", status)):
                self._required(entity, rec, fld, value)
            if done:
                self._required(entity, rec, "date", date.value)
                self._required(entity, rec, "total", total)

            # Dates inside the project window (with a grace period for slips at the edges).
            grace = dt.timedelta(days=self.dq["date_window_grace_days"])
            if date.value and project_id in self.ref.project_window:
                start, end = self.ref.project_window[project_id]
                if not (start - grace <= date.value <= end + grace):
                    self.log.add(entity, rec, "date", "date_outside_project_window", FLAGGED, rec.get("date"),
                                 date.value.isoformat(), f"project runs {start} to {end}")

            # Timeliness: late entry and "completed" activities that were actually late.
            d_lo, d_hi = date_bounds(date)
            e_lo, _ = date_bounds(entry)
            p_lo, p_hi = date_bounds(planned)
            late_days = self.dq["late_entry_days"]
            if d_lo and e_lo and status != "planned":
                if (e_lo - d_hi).days > late_days:
                    self.log.add(entity, rec, "entry_date", "late_entry", FLAGGED, rec.get("entry_date"),
                                 entry.value.isoformat(), f"entered {(e_lo - d_hi).days} days after the activity")
                elif (e_lo - d_lo).days > late_days:
                    self.log.add(entity, rec, "entry_date", "late_entry_possible", FLAGGED, rec.get("entry_date"),
                                 entry.value.isoformat(), "activity day unknown; may be a late entry")
                if (e_lo - d_hi).days < 0 and not date.approx and not entry.approx:
                    self.log.add(entity, rec, "entry_date", "entry_before_activity", FLAGGED, rec.get("entry_date"),
                                 entry.value.isoformat())
            tolerance = self.dq["on_time_tolerance_days"]
            if status == "completed" and d_lo and p_hi and (d_lo - p_hi).days > tolerance:
                self.log.add(entity, rec, "status", "status_completed_but_late", FLAGGED, rec.get("status"),
                             status, f"done {(d_lo - p_hi).days} days after the planned date")
            elif status == "completed" and d_hi and p_lo and (d_hi - p_lo).days > tolerance                     and (date.approx or planned.approx):
                self.log.add(entity, rec, "status", "on_time_unverifiable", FLAGGED, rec.get("status"), status,
                             "only the month is known, so 'completed on time' cannot be checked")
            on_time = None
            if status in ("completed", "delayed", "cancelled") and planned.value:
                on_time = bool(status == "completed" and d_hi and p_lo and (d_hi - p_lo).days <= tolerance) \
                    if not (date.approx or planned.approx) else None

            out.append(dict(
                source_file=rec["source_file"], source_sheet=rec["source_sheet"], source_row=rec["source_row"],
                activity_id=activity_id, project_id=project_id, location_id=loc["location_id"],
                province=province, district=district, sector=loc["sector"], cell=loc["cell"], village=loc["village"],
                date=date.value, date_is_approximate=date.approx, planned_date=planned.value,
                planned_date_is_approximate=planned.approx, entry_date=entry.value, status=status,
                participants_female=female, participants_male=male, participants_total=total, cost_rwf=cost,
                entry_lag_days=(entry.value - date.value).days if entry.value and date.value else None,
                on_time=on_time, field_officer=(norm_text(rec.get("officer")) or "").upper() or None,
                entered_by=rec.get("entered_by")))
        return pd.DataFrame(out)

    def remove_exact_duplicates(self, entity, df: pd.DataFrame) -> pd.DataFrame:
        """Drop rows that repeat an earlier row of the same sheet cell for cell."""
        value_cols = [c for c in df.columns if c not in ("source_file", "source_sheet", "source_row", "row_no",
                                                         "entered_by")]
        dup = df.duplicated(["source_file", "source_sheet"] + value_cols, keep="first")
        first_rows = df[~dup].set_index(["source_file", "source_sheet"] + value_cols)["source_row"]
        for rec in df[dup].to_dict("records"):
            key = tuple([rec["source_file"], rec["source_sheet"]] + [rec[c] for c in value_cols])
            original = first_rows.get(key)
            original = original.iloc[0] if isinstance(original, pd.Series) else original
            self.log.add(entity, rec, None, "exact_duplicate_row", REMOVED, detail=f"same as row {original}")
        return df[~dup]

    # ---------------------------------------------------------------- registrations and services
    def clean_registrations(self, df: pd.DataFrame) -> pd.DataFrame:
        entity, out = "registration", []
        has_province = "province" in df.columns
        bands = self.dq["age_bands"]
        for rec in df.to_dict("records"):
            sex = self._code(entity, rec, "sex", recode(rec.get("sex"), self.s["sex_mapping"], "sex"))
            age_field = "dob" if rec.get("age_source") == "dob" else "age"
            age = parse_number(rec.get("age"), self.s).value
            if age is not None and not (self.dq["age_min"] <= age <= self.dq["age_max"]):
                self.log.add(entity, rec, age_field, "impossible_age", FLAGGED, rec.get("age"), age,
                             f"age {age:.0f} outside {self.dq['age_min']} to {self.dq['age_max']}")
                age = None if age < 0 else age
            hh = self._number(entity, rec, "household_size")
            if hh is not None and not (self.dq["household_size_min"] <= hh <= self.dq["household_size_max"]):
                self.log.add(entity, rec, "household_size", "impossible_household_size", FLAGGED,
                             rec.get("household_size"), hh)
            disability = self._code(entity, rec, "disability",
                                    recode(rec.get("disability"), self.s["disability_mapping"], "disability"))
            district, province = self._district(entity, rec, has_province)
            loc = self._location(entity, rec, district)
            project_id = self._code(entity, rec, "project", self.ref.project(rec.get("project")))
            reg_date = self._date(entity, rec, "reg_date")
            for fld, value in (("sex", sex), ("district", district), ("village", loc["location_id"])):
                self._required(entity, rec, fld, value)
            self._required(entity, rec, age_field, age, raw_present=not is_blank(rec.get("age")))
            band = None
            if age is not None and age >= 0:
                lower = max(b for b in bands if b <= age)
                upper = next((b for b in bands if b > lower), None)
                band = f"{lower}-{upper - 1}" if upper else f"{lower}+"
            out.append(dict(
                source_file=rec["source_file"], source_sheet=rec["source_sheet"], source_row=rec["source_row"],
                beneficiary_key=rec["beneficiary_key"], registration_key=rec["registration_key"], sex=sex,
                age=age, age_band=band, household_size=hh, disability=disability, province=province,
                district=district, location_id=loc["location_id"], sector=loc["sector"], cell=loc["cell"],
                village=loc["village"], project_id=project_id, registration_date=reg_date.value,
                registration_date_is_approximate=reg_date.approx,
                has_national_id=rec.get("has_national_id") == "True",
                id_stored_as_text=rec.get("id_stored_as_text") == "True"))
        return pd.DataFrame(out)

    def clean_services(self, df: pd.DataFrame) -> pd.DataFrame:
        entity, out = "service", []
        for rec in df.to_dict("records"):
            date = self._date(entity, rec, "date")
            activity_id = self._code(entity, rec, "activity", self.ref.activity(rec.get("activity")))
            self._required(entity, rec, "date", date.value)
            out.append(dict(
                source_file=rec["source_file"], source_sheet=rec["source_sheet"], source_row=rec["source_row"],
                beneficiary_key=rec.get("beneficiary_key"), registration_key=rec.get("registration_key"),
                activity_id=activity_id, date=date.value, date_is_approximate=date.approx,
                service_type=norm_text(rec.get("service_type"))))
        return pd.DataFrame(out)

    # ---------------------------------------------------------------- indicator reports
    def clean_indicator_results(self, df: pd.DataFrame) -> pd.DataFrame:
        entity, out = "indicator_result", []
        ratio = self.dq["accuracy_outlier_ratio"]
        for rec in df.to_dict("records"):
            project_id = self._code(entity, rec, "project", self.ref.project(rec.get("project")))
            district, _ = self._district(entity, rec, False)
            period = self._date(entity, rec, "period", period=True)
            code = self.ref.indicator_by_key.get(norm_key(rec.get("indicator") or ""))
            if code is None:
                self.log.add(entity, rec, "indicator", "indicator_unrecognised", FLAGGED, rec.get("indicator"))
            elif code != rec.get("indicator"):
                self.log.add(entity, rec, "indicator", "indicator_name_to_code", FIXED, rec.get("indicator"), code)
            sex = self._code(entity, rec, "sex", recode(rec.get("sex"), self.s["sex_mapping"], "sex"))
            target = self._number(entity, rec, "target")
            actual = self._number(entity, rec, "actual")
            unit = self.ref.indicators.get(code, {}).get("unit")
            if unit == "percent" and actual is not None and 0 < actual <= self.s["cleaning"]["percent_fraction_max"]:
                self.log.add(entity, rec, "actual", "percent_fraction_converted", FIXED, rec.get("actual"),
                             actual * 100, "0.72 read as 72%")
                actual = round(actual * 100, 6)
            if target is None:
                self.log.add(entity, rec, "target", "missing_target", FLAGGED, detail="no target given")
            if actual is None:
                self._required(entity, rec, "actual", actual)
            elif actual < 0:
                self.log.add(entity, rec, "actual", "negative_value", FLAGGED, rec.get("actual"), actual)
            elif unit == "percent" and actual > 100:
                self.log.add(entity, rec, "actual", "percent_over_100", FLAGGED, rec.get("actual"), actual)
            elif target and actual > ratio * target:
                self.log.add(entity, rec, "actual", "accuracy_outlier", FLAGGED, rec.get("actual"), actual,
                             f"actual is {actual / target:.1f} x the target")
            for fld, value in (("project", project_id), ("district", district), ("period", period.value)):
                self._required(entity, rec, fld, value)
            out.append(dict(
                source_file=rec["source_file"], source_sheet=rec["source_sheet"], source_row=rec["source_row"],
                indicator_code=code, project_id=project_id, district=district, period=period.value,
                sex=sex, disaggregation_key=f"sex={sex}" if sex else "total", target_value=target,
                actual_value=actual, entered_by=norm_text(rec.get("entered_by")),
                comment=norm_text(rec.get("comment"))))
        return pd.DataFrame(out)

    def report_completeness(self, results: pd.DataFrame) -> pd.DataFrame:
        """List every monthly report that should exist and whether it was received."""
        start = self.s["reporting_window"]["start"]
        end = self.s["reporting_window"]["end"]
        due_months = {"monthly": range(1, 13), "quarterly": (3, 6, 9, 12), "semi-annual": (6, 12),
                      "annual": (6,)}
        submitted = set(zip(results["project_id"], results["district"], results["period"]))
        rows = []
        for p in self.ref.projects.itertuples():
            p_start, p_end = self.ref.project_window[p.project_id]
            codes = [c.strip() for c in str(p.indicators).split(",") if c.strip()]
            for district in [d.strip() for d in str(p.districts).split(",")]:
                month = dt.date(max(start, p_start).year, max(start, p_start).month, 1)
                while month <= min(end, p_end):
                    due = [c for c in codes if month.month in due_months[self.ref.indicators[c]["frequency"]]]
                    if due:
                        rows.append(dict(project_id=p.project_id, district=district, period=month,
                                         indicators_due=", ".join(due),
                                         submitted=(p.project_id, district, month) in submitted))
                    month = dt.date(month.year + (month.month == 12), month.month % 12 + 1, 1)
        return pd.DataFrame(rows)

    # ---------------------------------------------------------------- donors and opportunities
    def clean_donors(self, df: pd.DataFrame) -> pd.DataFrame:
        entity, out = "donor", []
        for rec in df.to_dict("records"):
            dtype = self._code(entity, rec, "donor_type",
                               recode(rec.get("donor_type"), self.s["donor_pipeline"]["donor_type_mapping"], "donor_type"))
            out.append(dict(
                source_file=rec["source_file"], source_sheet=rec["source_sheet"], source_row=rec["source_row"],
                donor_key=rec["donor_key"], donor_name=rec["donor_name"], donor_type=dtype,
                country=norm_text(rec.get("country")), thematic_interests=norm_text(rec.get("thematic_interests"))))
        return pd.DataFrame(out)

    def clean_opportunities(self, df: pd.DataFrame) -> pd.DataFrame:
        entity, out = "opportunity", []
        words = {w.casefold() for w in self.s["cleaning"]["probability_words_flag"]}
        for rec in df.to_dict("records"):
            stage = self._code(entity, rec, "stage",
                               recode(rec.get("stage"), self.s["donor_pipeline"]["stage_mapping"], "stage"))
            deadline = self._date(entity, rec, "deadline")
            next_date = self._date(entity, rec, "next_action_date")
            requested = self._number(entity, rec, "requested")
            awarded = self._number(entity, rec, "awarded")
            raw_p = rec.get("probability")
            probability = None
            if not is_blank(raw_p) and norm_key(raw_p) in words:
                self.log.add(entity, rec, "probability", "probability_word", FLAGGED, raw_p,
                             detail="a word cannot be used in the weighted pipeline; enter a percentage")
            elif not is_blank(raw_p):
                result = parse_number(raw_p, self.s)
                probability = result.value
                if probability is not None and (probability > 1 or "%" in str(raw_p)):
                    probability = probability / 100
                    self.log.add(entity, rec, "probability", "probability_to_fraction", FIXED, raw_p, probability)
                if probability is None or not 0 <= probability <= 1:
                    self.log.add(entity, rec, "probability", "probability_out_of_range", FLAGGED, raw_p)
                    probability = None
            if rec.get("donor_key") is None:
                self.log.add(entity, rec, "donor", "donor_not_in_donor_list", FLAGGED)
            out.append(dict(
                source_file=rec["source_file"], source_sheet=rec["source_sheet"], source_row=rec["source_row"],
                opportunity_id=norm_text(rec.get("opportunity_id")), donor_key=rec.get("donor_key"),
                title=norm_text(rec.get("title")), thematic_fit=norm_text(rec.get("thematic_fit")), stage=stage,
                deadline=deadline.value, requested_amount_rwf=requested, awarded_amount_rwf=awarded,
                probability=probability, owner=norm_text(rec.get("owner")), next_action=norm_text(rec.get("next_action")),
                next_action_date=next_date.value))
        return pd.DataFrame(out)


# ======================================================================================
# Severity, review queue and info-level measures
# ======================================================================================
def assign_severity(issues: pd.DataFrame, settings: dict) -> pd.DataFrame:
    """Give every flag a severity: critical (row quarantined), warning (review queue) or info.

    Changes and removals made automatically have no severity (they need no one's attention).
    """
    rules = settings["flag_severity"]
    level = {code: sev for sev in ("critical", "warning", "info") for code in rules[sev]}
    issues = issues.copy()
    flagged = issues["action"] == FLAGGED
    issues["severity"] = None
    issues.loc[flagged, "severity"] = issues.loc[flagged, "issue_code"].map(level).fillna("warning")
    # A critical district problem that the pipeline resolved from the village becomes a warning.
    row_key = (issues["source_file"].astype(str) + "|" + issues["source_sheet"].astype(str) + "|"
               + issues["source_row"].astype(str))
    for code, resolver in rules.get("downgrade_when_resolved", {}).items():
        resolved_rows = set(row_key[issues["issue_code"] == resolver])
        mask = (flagged & (issues["issue_code"] == code) & row_key.isin(resolved_rows)
                & (issues["field"] == "district"))
        issues.loc[mask, "severity"] = "warning"
    return issues


# Which date decides the month in which a row reaches the MEAL officer.
ROW_MONTH = {
    "activity": ["entry_date", "date", "planned_date"], "registration": ["registration_date"],
    "service": ["date"], "indicator_result": ["period"], "opportunity": ["next_action_date", "deadline"],
    "donor": [],
}


def row_status(tables: dict, issues: pd.DataFrame) -> pd.DataFrame:
    """One line per source row with a critical or warning flag.

    status = quarantine (any critical flag) or review (warnings only). A quarantined row is
    corrected in the source file, so it is not also counted in the review queue.
    """
    flagged = issues[issues["severity"].isin(["critical", "warning"]) & issues["source_row"].notna()]
    rows = []
    for (entity, f, sh, r), g in flagged.groupby(["entity", "source_file", "source_sheet", "source_row"]):
        critical = sorted(set(g.loc[g["severity"] == "critical", "issue_code"]))
        warning = sorted(set(g.loc[g["severity"] == "warning", "issue_code"]))
        rows.append(dict(entity=entity, source_file=f, source_sheet=sh, source_row=int(r),
                         status="quarantine" if critical else "review",
                         critical_codes=", ".join(critical), warning_codes=", ".join(warning)))
    out = pd.DataFrame(rows, columns=["entity", "source_file", "source_sheet", "source_row", "status",
                                      "critical_codes", "warning_codes"])
    month = {}
    for entity, cols in ROW_MONTH.items():
        df = tables.get(entity)
        if df is None or not len(df):
            continue
        for rec in df.to_dict("records"):
            d = next((rec[c] for c in cols if c in rec and not is_blank(rec[c])), None)
            month[(entity, rec["source_file"], rec["source_sheet"], int(rec["source_row"]))] = \
                f"{d.year}-{d.month:02d}" if d else None
    out["month"] = [month.get((e, f, sh, r)) for e, f, sh, r in
                    zip(out["entity"], out["source_file"], out["source_sheet"], out["source_row"])]
    return out


def info_metrics(tables: dict, issues: pd.DataFrame, settings: dict) -> pd.DataFrame:
    """Data-quality measures shown on the dashboard instead of rows to review."""
    acts, regs = tables["activity"], tables["registration"]
    late = settings["data_quality"]["late_entry_days"]
    rows = []

    def add(metric, num, den, note):
        rows.append(dict(metric=metric, numerator=int(num), denominator=int(den),
                         percent=round(100 * num / den, 1) if den else None, note=note))

    timed = acts[acts["entry_lag_days"].notna() & ~acts["date_is_approximate"].astype(bool)]
    add(f"Timeliness: activity records entered within {late} days", (timed["entry_lag_days"] <= late).sum(),
        len(timed), "activities with an exact date and an entry date")
    dated = acts[acts["date"].notna()]
    add("Activity dates with a known day", (~dated["date_is_approximate"].astype(bool)).sum(), len(dated),
        "the rest were typed as a month only")
    judged = acts[acts["status"].isin(["completed", "delayed", "cancelled"])]
    add("Activities whose on-time status can be checked", judged["on_time"].notna().sum(), len(judged),
        "needs exact activity and planned dates")
    with_id = regs[regs["has_national_id"].astype(bool)]
    add("National IDs typed as text (all 16 digits kept)", with_id["id_stored_as_text"].astype(bool).sum(),
        len(with_id), "an ID stored as a number loses its last digit, which cannot be recovered")
    rc = tables["report_completeness"]
    add("Reporting completeness: expected monthly reports received", rc["submitted"].sum(), len(rc),
        "indicator CC-04")
    return pd.DataFrame(rows)


def run(staging=None) -> dict:
    """Clean every staged table. Returns the cleaned tables (used by tests and scoring)."""
    staging = staging or resolve_path("staging")
    cleaner = Cleaner(staging)
    def read(name):
        # A column that a sheet does not have arrives empty (None), never as NaN.
        df = pd.read_parquet(staging / f"ingested_{name}.parquet")
        return df.astype(object).where(df.notna(), None)
    tables = {
        "activity": cleaner.clean_activities(read("activity")),
        "registration": cleaner.clean_registrations(read("registration")),
        "service": cleaner.clean_services(read("service")),
        "indicator_result": cleaner.clean_indicator_results(read("indicator_result")),
        "donor": cleaner.clean_donors(read("donor")),
        "opportunity": cleaner.clean_opportunities(read("opportunity")),
    }
    tables["report_completeness"] = cleaner.report_completeness(tables["indicator_result"])
    for row in tables["report_completeness"][~tables["report_completeness"]["submitted"]].itertuples():
        cleaner.log.rows.append(dict(entity="indicator_report", source_file=None, source_sheet=None,
                                     source_row=None, field=None, issue_code="report_missing", action=FLAGGED,
                                     raw_value=None, clean_value=f"{row.project_id}|{row.district}|{row.period}",
                                     detail=f"no report for {row.project_id} {row.district} {row.period:%b %Y}"))
    ingest_issues = pd.read_parquet(staging / "ingest_issues.parquet")
    issues = assign_severity(pd.concat([ingest_issues, cleaner.log.frame()], ignore_index=True), cleaner.s)
    tables["issues"] = issues
    tables["row_status"] = row_status(tables, issues)
    tables["dq_info_metrics"] = info_metrics(tables, issues, cleaner.s)
    for name, df in tables.items():
        df.to_parquet(staging / (f"clean_{name}.parquet" if name != "issues" else "issues.parquet"), index=False)
    return tables


def main():
    tables = run()
    issues = tables["issues"]
    print(f"Cleaned {sum(len(t) for n, t in tables.items() if n not in ('issues', 'report_completeness'))} rows; "
          f"{(issues['action'] == FIXED).sum()} values fixed, {(issues['action'] == FLAGGED).sum()} flagged, "
          f"{(issues['action'] == REMOVED).sum()} rows removed")


if __name__ == "__main__":
    main()
