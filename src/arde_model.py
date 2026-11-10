"""ARDE/KUBAHO workbook mode: build the results-chain (logframe) tables and run this format's data-quality rules.

WHAT THIS FILE DOES
-------------------
From the sheets read by arde_reader.py it builds, each row with its lineage (source_file, source_sheet,
source_row):

  dim_project            every Projects column, plus an RWF estimate of the budget (dated exchange rates in
                         config/settings.yaml: arde), the districts found in the location text, and the budget-used
                         and progress values that can be used (impossible ones are NULL and shown "invalid, check")
  dim_project_district   one row per project and district (a project in two districts has two rows)
  fact_result            the results chain: General Objective > Specific Objective > Output, from the Results sheet
  fact_kpi               the KPIs, from the working register ('Results & KPIs'), with the unit normalised, our own
                         achievement % and performance band, and the workbook's values next to them
  fact_project_activity  activities with funds in their own currency and an RWF estimate
  fact_reach             reach by project and category, with the unit normalised and its unit type
  fact_contribution      partner contributions (financial and in-kind)

Then it runs the rules in config/arde_format.yaml. Rules FLAG; they never change a value.

THE RULES IN ONE LINE EACH
  money is never added across currencies: each amount keeps its currency and gets a separate "RWF estimate";
  reach is never added across units: each row keeps its unit, and totals are only ever per unit.

HOW TO RUN
    python src/arde_pipeline.py   (runs this together with the reader, the comparisons and the exports)
"""

from __future__ import annotations

import datetime as dt
import re
from functools import lru_cache

import pandas as pd

from common import district_to_province, load_settings, load_yaml, resolve_path


# ---------------------------------------------------------------- settings
def arde_settings() -> dict:
    return load_settings()["arde"]


@lru_cache(maxsize=None)
def fmt() -> dict:
    """config/arde_format.yaml (read once per run), plus the workbook-specific word lists in
    data/real/arde_local.yaml (gitignored: partner and project names and title words come from the confidential
    workbook, so they are never committed). Lists in the local file are added to the same lists in config."""
    import yaml
    from common import PROJECT_ROOT
    spec = load_yaml("arde_format.yaml")
    local = PROJECT_ROOT / "data" / "real" / "arde_local.yaml"
    if local.exists():
        extra = yaml.safe_load(local.read_text(encoding="utf-8")) or {}
        spec["not_personal_names"] = spec["not_personal_names"] + extra.get("not_personal_names", [])
        for language, words in (extra.get("language_markers") or {}).items():
            spec["language_markers"][language] = spec["language_markers"].get(language, []) + words
    return spec


def as_of() -> dt.date:
    value = arde_settings().get("as_of_date")
    if value:
        return value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value))
    return dt.date.today()


# ---------------------------------------------------------------- money
def fx_rate(currency, year) -> tuple[float | None, int | None]:
    """RWF per one unit of the currency in that year (config/settings.yaml: arde.exchange_rates_rwf_per_unit).
    A year that is not listed uses the nearest listed year. Unknown currency: (None, None)."""
    rates = arde_settings()["exchange_rates_rwf_per_unit"]
    cur = str(currency).strip().upper() if currency is not None else ""
    if cur not in rates:
        return None, None
    table = {int(k): float(v) for k, v in rates[cur].items()}
    if cur == "RWF":
        return 1.0, None
    if year is None or pd.isna(year):
        return None, None
    nearest = min(table, key=lambda y: (abs(y - int(year)), -y))
    return table[nearest], nearest


def to_rwf(amount, currency, when) -> tuple[float | None, float | None, int | None]:
    """(RWF estimate, rate used, rate year). Never adds currencies together: one amount at a time."""
    if amount is None or pd.isna(amount):
        return None, None, None
    year = pd.Timestamp(when).year if when is not None and not pd.isna(when) else None
    rate, rate_year = fx_rate(currency, year)
    if rate is None:
        return None, None, None
    return float(amount) * rate, rate, rate_year


def sum_by_currency(df: pd.DataFrame, amount: str, currency: str = "currency") -> dict:
    """Totals PER CURRENCY ({"EUR": ..., "RWF": ...}). The only way this module adds money in its own currency."""
    return {c: float(v) for c, v in df.groupby(currency)[amount].sum().items()}


# ---------------------------------------------------------------- units
def unit_key(unit) -> str:
    return re.sub(r"\s+", " ", str(unit).strip().lower()) if unit is not None and not pd.isna(unit) else ""


def normalise_unit(unit) -> str:
    """'People' -> 'people', 'Cooperative' -> 'cooperatives' (config/arde_format.yaml: unit_aliases)."""
    key = unit_key(unit)
    return fmt()["unit_aliases"].get(key, key)


def unit_type(normalised: str) -> str:
    """people, households, organisations or other (config/arde_format.yaml: unit_types)."""
    for kind, units in fmt()["unit_types"].items():
        if normalised in units:
            return kind
    return "other"


def variant_forms(units: pd.DataFrame) -> dict[str, str]:
    """Normalised units written in more than one way: {'cooperatives': "Cooperative, Cooperatives, cooperatives"}.
    units: columns unit_original and unit."""
    u = units.assign(unit_original=units["unit_original"].map(lambda v: str(v).strip()))
    groups = u.groupby("unit")["unit_original"].agg(lambda x: sorted(set(x)))
    return {unit: ", ".join(f) for unit, f in groups.items() if len(f) > 1}


def totals_by_unit(reach: pd.DataFrame, value: str = "count") -> pd.DataFrame:
    """Reach totals, one row per reach type and NORMALISED UNIT. There is deliberately no function that adds
    across units: a total of "people + households + cooperatives" has no meaning."""
    return (reach.groupby(["reach_type", "unit_type", "unit"], as_index=False)[value].sum()
            .sort_values(["reach_type", "unit_type", value], ascending=[True, True, False]))


# ---------------------------------------------------------------- places, names, languages
def extract_districts(text) -> list[str]:
    """Rwandan districts named in a free-text location, in the order of the official list.
    'Huye District, Southern Province' -> ['Huye']. Matching ignores case; whole words only."""
    if text is None or pd.isna(text):
        return []
    found = []
    for district in district_to_province():
        if re.search(rf"\b{re.escape(district)}\b", str(text), flags=re.IGNORECASE):
            found.append(district)
    return found


def outside_rwanda(text) -> bool:
    return bool(re.search(r"\b(Goma|Democratic Republic of the Congo|DRC|North Kivu)\b", str(text or ""),
                          flags=re.IGNORECASE))


def load_hidden_names(path=None) -> list[str]:
    """Personal names to hide on screen (data/real/staff_names_hidden.yaml, never committed)."""
    import yaml
    path = path or resolve_path_arde("staff_names_file")
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return sorted({str(n) for n in data.get("names", []) if str(n).strip()}, key=len, reverse=True)


def roles_only(text, names: list[str]) -> str:
    """Show a role, not a person: every listed name becomes "[name]", and "[name] - Role" or "[name] / Org"
    becomes "Role" / "Org". 'DUPONT Jean - Executive Director' -> 'Executive Director'."""
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return ""
    out = str(text)
    for name in names:
        out = re.sub(re.escape(name), "[name]", out, flags=re.IGNORECASE)
    for name in possible_names(out):                 # safety net: anything that looks like a name but is not listed
        out = out.replace(name, "[name]")
    out = re.sub(r"^\s*\[name\]\s*[-–—/:]\s*", "", out)                 # "[name] - Role" -> "Role"
    out = re.sub(r"\s*[-–—/]\s*\[name\]\s*$", "", out)                  # "Org / [name]" -> "Org"
    out = re.sub(r"(institutional contact|contact)\s*:\s*\[name\]", r"\1 (name hidden)", out, flags=re.IGNORECASE)
    out = re.sub(r"\s{2,}", " ", out).strip(" ;,")
    return out


def possible_names(text) -> list[str]:
    """Words that LOOK like personal names in a staff column (an UPPER-CASE surname next to a capitalised first
    name, e.g. 'DUPONT Jean', 'Jean DUPONT'), excluding organisations listed in config. Used to suggest
    entries for the hidden-names file; never shown on screen."""
    skip = {w.upper() for w in fmt()["not_personal_names"]}
    out = []
    pattern = r"\b([A-Z][a-z]+(?: [A-Z]\.)?(?: [A-Z][a-z]+)? [A-Z]{3,}(?: [A-Z][a-z]+)*|[A-Z]{3,}(?: [A-Z]\.)?(?: [A-Z][a-z]+)+)\b"
    for match in re.findall(pattern, str(text or "")):
        caps = [w for w in match.split() if w.isupper() and len(w) > 2]
        if caps and not any(w.strip(".") in skip for w in caps):
            out.append(match)
    return out


def language_of(title) -> str:
    """English, French or Kinyarwanda, by marker words (config/arde_format.yaml: language_markers). Only used to
    COUNT titles; titles are never changed."""
    words = set(re.findall(r"[\w'’-]+", str(title or "").lower()))
    best, hits = "English", 0
    for language, markers in fmt()["language_markers"].items():
        n = sum(1 for m in markers if m in words or (" " in m and m in str(title).lower()))
        if n > hits:
            best, hits = language, n
    return best if hits >= 2 else "English"


def resolve_path_arde(key: str):
    from common import PROJECT_ROOT
    return PROJECT_ROOT / arde_settings()[key]


# ---------------------------------------------------------------- performance bands
def achievement(target, achieved) -> float | None:
    if target is None or pd.isna(target) or float(target) == 0 or achieved is None or pd.isna(achieved):
        return None
    return float(achieved) / float(target)


def band(target, achieved, status) -> str:
    """Our performance band, with the workbook's own thresholds (settings: arde.band):
    No target -> "No target"; status Not started/Not recorded with nothing achieved -> "Not recorded";
    then Achieved (>= 100%), On track (>= 75%), Needs attention."""
    s = arde_settings()
    ratio = achievement(target, achieved)
    if ratio is None:
        return "No target"
    if str(status).strip() in s["not_recorded_statuses"] and (achieved is None or float(achieved) == 0):
        return "Not recorded"
    if ratio >= s["band"]["achieved_min"]:
        return "Achieved"
    if ratio >= s["band"]["on_track_min"]:
        return "On track"
    return "Needs attention"


BAND_ORDER = ["Achieved", "On track", "Needs attention", "Not recorded", "No target"]


# ---------------------------------------------------------------- the tables
def _dates(series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce")


def _num(series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def build_tables(sheets: dict, kpi_updates: pd.DataFrame | None = None) -> dict[str, pd.DataFrame]:
    """The results-chain tables from the sheets (see the module docstring). kpi_updates: the latest update per KPI
    made on the dashboard (arde_store.current_updates()); it replaces the achieved value and status, with lineage."""
    s = arde_settings()
    province = district_to_province()

    # ---- dim_project
    p = sheets["Projects"].copy()
    for c in ("start_date", "end_date"):
        p[c] = _dates(p[c])
    for c in ("approved_budget", "budget_used_pct", "progress_pct", "direct_beneficiaries", "indirect_beneficiaries",
              "total_reach", "female", "male", "youth", "disability", "direct_jobs", "indirect_jobs"):
        p[c] = _num(p[c])
    conv = [to_rwf(a, c, d) for a, c, d in zip(p["approved_budget"], p["currency"], p["start_date"])]
    p["budget_rwf_estimate"] = [c[0] for c in conv]
    p["fx_rate_used"] = [c[1] for c in conv]
    p["fx_rate_year"] = [c[2] for c in conv]
    p["budget_used_valid"] = p["budget_used_pct"].where(p["budget_used_pct"].between(0, s["budget_used_max_fraction"]))
    p["budget_used_check"] = p["budget_used_pct"].map(
        lambda v: "invalid, check" if pd.notna(v) and not 0 <= v <= s["budget_used_max_fraction"] else
        ("over 100%, check" if pd.notna(v) and v > 1 else ""))
    p["progress_valid"] = p["progress_pct"].where(p["progress_pct"].between(0, s["progress_max_fraction"]))
    p["districts"] = p["location"].map(lambda t: "; ".join(extract_districts(t)))
    p["district_count"] = p["location"].map(lambda t: len(extract_districts(t)))
    p["outside_rwanda"] = p["location"].map(outside_rwanda)
    p["title_language"] = p["project_title"].map(language_of)
    p["start_year"] = p["start_date"].dt.year
    p["end_year"] = p["end_date"].dt.year
    lineage = ["source_file", "source_sheet", "source_row"]
    p = p[[c for c in p.columns if c not in lineage] + lineage]

    bridge = pd.DataFrame([{"project_code": r.project_code, "district": d, "province": province.get(d),
                            "districts_in_project": r.district_count}
                           for r in p.itertuples() for d in extract_districts(r.location)],
                          columns=["project_code", "district", "province", "districts_in_project"])

    # ---- fact_result (Results sheet: the complete chain, with descriptions)
    r = sheets["Results"].copy()
    r["result_order"] = _num(r["result_order"])
    r["parent_result"] = r["parent_result"].map(lambda v: None if v is None or pd.isna(v) else str(v).strip())
    codes = set(r["result_code"])
    r["parent_is_valid"] = r["parent_result"].isin(codes)
    kpi_counts = sheets["Results & KPIs"].groupby("result_code").size()
    r["kpi_count"] = r["result_code"].map(kpi_counts).fillna(0).astype(int)
    r = r[[c for c in r.columns if c not in lineage] + lineage]

    # ---- fact_kpi (working register, with the KPIs sheet's own values next to ours)
    rk = sheets["Results & KPIs"].copy()
    k = sheets["KPIs"].set_index("kpi_code")
    for c in ("baseline", "target", "achieved"):
        rk[c] = _num(rk[c])
    rk = rk.rename(columns={"achievement_pct": "achievement_workbook", "performance_band": "band_workbook",
                            "unit": "unit_original"})
    rk["achievement_workbook"] = _num(rk["achievement_workbook"])          # '-' (no target) becomes empty
    rk["achievement_kpis_sheet"] = _num(rk["kpi_code"].map(k["achievement_pct"]))
    rk["band_kpis_sheet"] = rk["kpi_code"].map(k["performance_band"])
    rk["kpis_sheet_row"] = rk["kpi_code"].map(k["source_row"])
    rk["achieved_workbook"] = rk["achieved"]
    rk["status_workbook"] = rk["kpi_status"]
    rk["updated_by"], rk["updated_at"], rk["update_id"] = None, None, None
    if kpi_updates is not None and len(kpi_updates):
        upd = kpi_updates.set_index("kpi_code")
        hit = rk["kpi_code"].isin(upd.index)
        rk.loc[hit, "achieved"] = rk.loc[hit, "kpi_code"].map(upd["achieved"]).astype(float)
        rk.loc[hit, "kpi_status"] = rk.loc[hit, "kpi_code"].map(upd["kpi_status"])
        for col in ("updated_by", "updated_at", "update_id"):
            rk.loc[hit, col] = rk.loc[hit, "kpi_code"].map(upd[col])
    rk["unit"] = rk["unit_original"].map(normalise_unit)
    rk["unit_type"] = rk["unit"].map(unit_type)
    rk["achievement"] = [achievement(t, a) for t, a in zip(rk["target"], rk["achieved"])]
    rk["band"] = [band(t, a, st) for t, a, st in zip(rk["target"], rk["achieved"], rk["kpi_status"])]
    rk = rk[[c for c in rk.columns if c not in lineage] + lineage]

    # ---- fact_project_activity
    a = sheets["Activities"].copy()
    for c in ("start_date", "end_date"):
        a[c] = _dates(a[c])
    for c in ("personnel_count", "funds", "progress_pct"):
        a[c] = _num(a[c])
    conv = [to_rwf(f, c, d) for f, c, d in zip(a["funds"], a["currency"], a["start_date"])]
    a["funds_rwf_estimate"] = [c[0] for c in conv]
    a["fx_rate_used"] = [c[1] for c in conv]
    a["fx_rate_year"] = [c[2] for c in conv]
    a = a[[c for c in a.columns if c not in lineage] + lineage]

    # ---- fact_reach
    b = sheets["Beneficiaries"].copy()
    b["count"] = _num(b["count"])
    b = b.rename(columns={"unit": "unit_original"})
    b["unit"] = b["unit_original"].map(normalise_unit)
    b["unit_type"] = b["unit"].map(unit_type)
    b["is_headline_people"] = b["unit"] == fmt()["headline_people_unit"]
    b = b[[c for c in b.columns if c not in lineage] + lineage]

    # ---- fact_contribution
    c = sheets["Stakeholders"].copy()
    c["value"] = _num(c["value"])
    starts = p.set_index("project_code")["start_date"]
    c["currency"] = c["currency_or_unit"].map(
        lambda v: str(v).strip().upper() if str(v).strip().upper() in arde_settings()["exchange_rates_rwf_per_unit"]
        else None)
    conv = [to_rwf(v, cur, starts.get(code)) if cur else (None, None, None)
            for v, cur, code in zip(c["value"], c["currency"], c["project_code"])]
    c["value_rwf_estimate"] = [x[0] for x in conv]
    c["fx_rate_used"] = [x[1] for x in conv]
    c["is_money"] = c["currency"].notna()
    c = c[[col for col in c.columns if col not in lineage] + lineage]

    return {"dim_project": p, "dim_project_district": bridge, "fact_result": r, "fact_kpi": rk,
            "fact_project_activity": a, "fact_reach": b, "fact_contribution": c}


# ---------------------------------------------------------------- rules
def _flag(rule: str, df: pd.DataFrame, key: str, detail) -> list[dict]:
    spec = fmt()["rules"][rule]
    out = []
    for _, row in df.iterrows():
        out.append({"rule": rule, "level": spec["level"], "label": spec["label"], "record_key": row[key],
                    "project_code": row.get("project_code"), "source_sheet": row.get("source_sheet"),
                    "source_row": row.get("source_row"), "detail": detail(row) if callable(detail) else detail})
    return out


def run_rules(t: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Every rule in config/arde_format.yaml. Returns (one row per flag, one row per rule with checked/flagged).
    Nothing is changed: values that cannot be used are already NULL in the *_valid columns."""
    s = arde_settings()
    today = pd.Timestamp(as_of())
    p, r, k, a, b = t["dim_project"], t["fact_result"], t["fact_kpi"], t["fact_project_activity"], t["fact_reach"]
    flags: list[dict] = []
    checked: dict[str, int] = {}

    def add(rule, rows, key, detail, n_checked):
        flags.extend(_flag(rule, rows, key, detail))
        checked[rule] = int(n_checked)

    # 1. Budget used % impossible (an amount typed into a % column) / above 100%
    bu = p["budget_used_pct"]
    add("budget_used_impossible", p[bu.notna() & ~bu.between(0, s["budget_used_max_fraction"])], "project_code",
        lambda x: f"Budget used % = {x.budget_used_pct:,.2f} (as a fraction; 1 = 100%). Not used; check the workbook.",
        bu.notna().sum())
    add("budget_used_over_100", p[bu.between(1, s["budget_used_max_fraction"], inclusive="right")], "project_code",
        lambda x: f"Budget used {x.budget_used_pct:.0%}", bu.notna().sum())
    # 2. Approved budget 0
    add("budget_zero", p[p["approved_budget"].fillna(0) == 0], "project_code",
        lambda x: f"Approved budget {x.approved_budget} {x.currency}", len(p))
    # 3. Currencies: converted amounts are estimates (info)
    add("currency_converted", p[p["currency"].str.upper() != "RWF"], "project_code",
        lambda x: f"{x.approved_budget:,.0f} {x.currency} ≈ RWF {x.budget_rwf_estimate:,.0f} at {x.fx_rate_used:,.0f} "
                  f"({x.fx_rate_year})" if pd.notna(x.budget_rwf_estimate) else f"No rate for {x.currency}", len(p))
    add("activity_currency_converted", a[a["currency"].str.upper() != "RWF"], "activity_code",
        lambda x: f"{x.funds:,.0f} {x.currency}", len(a))
    # 4. Units written differently: a normalised unit written in more than one way anywhere in the workbook
    forms = variant_forms(pd.concat([k[["unit_original", "unit"]], b[["unit_original", "unit"]]]))
    kv = k[k["unit"].isin(forms)]
    add("unit_variant", kv, "kpi_code", lambda x: f"'{x.unit_original}' -> '{x.unit}' (written as: {forms[x.unit]})",
        len(k))
    b_key = b.assign(reach_key=b["project_code"] + " / " + b["category"].astype(str))
    add("reach_unit_variant", b_key[b["unit"].isin(forms)], "reach_key",
        lambda x: f"'{x.unit_original}' -> '{x.unit}' (written as: {forms[x.unit]})", len(b))
    # 5. KPIs not recorded / not started
    nr = k[k["band"] == "Not recorded"]
    add("kpi_not_recorded", nr, "kpi_code",
        lambda x: f"Status '{x.kpi_status}', achieved {x.achieved:g}. Workbook register band: '{x.band_workbook}'; "
                  f"KPIs sheet band: '{x.band_kpis_sheet}'.", len(k))
    # 6. Past end date but still active; completed below 100%
    late = p[(p["end_date"] < today) & p["status"].isin(s["active_statuses"])]
    add("past_end_still_active", late, "project_code",
        lambda x: f"Ended {x.end_date:%d %b %Y}, status '{x.status}'", len(p))
    done_low = p[p["status"].isin(s["completed_statuses"]) & (p["progress_pct"] < s["completed_min_progress"])]
    add("completed_low_progress", done_low, "project_code",
        lambda x: f"Status '{x.status}' at {x.progress_pct:.0%} progress", len(p))
    # 7. General Objectives whose parent is not a result code
    go = r[r["level"] == "General Objective"]
    add("parent_placeholder", go[~go["parent_is_valid"]], "result_code",
        lambda x: f"Parent result '{x.parent_result}' is not a result code", len(go))
    # 8. KPIs above 150% of target; KPIs with no target
    over = k[k["achievement"] > s["kpi_over_target_review"]]
    add("kpi_over_150", over, "kpi_code",
        lambda x: f"Achieved {x.achieved:g} against target {x.target:g} ({x.achievement:.0%})", len(k))
    add("kpi_no_target", k[k["band"] == "No target"], "kpi_code",
        lambda x: f"Target {x.target}, achieved {x.achieved}", len(k))
    # 9. Activities with funds of 0
    add("activity_funds_zero", a[a["funds"].fillna(0) == 0], "activity_code", "Funds 0", len(a))
    # 10. Reach: other units; possible double counting; Projects sheet against Beneficiaries sheet
    add("reach_mixed_units", b_key[~b_key["is_headline_people"]], "reach_key",
        lambda x: f"{x['count']:,.0f} {x.unit} ({x.unit_type}), {x.reach_type}", len(b))
    sub_units = set(fmt()["people_subgroup_units"])
    has_people = set(zip(b.loc[b["is_headline_people"], "project_code"], b.loc[b["is_headline_people"], "reach_type"]))
    dbl = b_key[b_key["unit"].isin(sub_units)
                & pd.Series(list(zip(b["project_code"], b["reach_type"])), index=b.index).isin(has_people)]
    add("reach_possible_double_count", dbl, "reach_key",
        lambda x: f"{x['count']:,.0f} {x.unit} ({x.reach_type}) next to 'people' rows in the same project", len(b))
    people = (b[b["is_headline_people"] & (b["reach_type"] == "Direct")].groupby("project_code")["count"].sum())
    cmp = p.assign(people_rows=p["project_code"].map(people).fillna(0))
    diff = cmp[cmp["direct_beneficiaries"].fillna(0) != cmp["people_rows"]]
    add("reach_register_differs", diff, "project_code",
        lambda x: f"Projects sheet {x.direct_beneficiaries:,.0f} direct; Beneficiaries sheet 'people' rows "
                  f"{x.people_rows:,.0f}", len(p))
    # Districts
    add("district_not_found", p[p["district_count"] == 0], "project_code",
        lambda x: f"Location: {x.location}", len(p))
    # 11. Languages (kept as written)
    add("title_not_english", p[p["title_language"] != "English"], "project_code",
        lambda x: f"{x.title_language}", len(p))
    # Our band against the workbook's
    bd = k[k["band"] != k["band_workbook"]]
    add("band_differs_from_workbook", bd, "kpi_code",
        lambda x: f"Ours '{x.band}', register '{x.band_workbook}', KPIs sheet '{x.band_kpis_sheet}'", len(k))
    # The working register and the KPIs sheet disagree on Achievement % (beyond the KPIs sheet's rounding)
    reg, typed = k["achievement_workbook"], k["achievement_kpis_sheet"]
    stale = k[~(((reg - typed).abs() <= 0.0005) | (reg.isna() & typed.isna()))]
    add("register_differs", stale, "kpi_code",
        lambda x: f"Register {x.achievement_workbook if pd.notna(x.achievement_workbook) else '-'}, KPIs sheet "
                  f"{x.achievement_kpis_sheet} (typed in; the register's value is used)", len(k))
    # Codes pointing nowhere
    projects = set(p["project_code"])
    results = set(r["result_code"])
    outputs = set(r.loc[r["level"] == "Output", "result_code"])
    orphans = pd.concat([
        k[~k["project_code"].isin(projects) | ~k["result_code"].isin(results)].assign(record_key=lambda x: x["kpi_code"]),
        a[~a["project_code"].isin(projects) | ~a["output_code"].isin(outputs)].assign(record_key=lambda x: x["activity_code"]),
        r[~r["project_code"].isin(projects)].assign(record_key=lambda x: x["result_code"]),
        b[~b["project_code"].isin(projects)].assign(record_key=lambda x: x["project_code"]),
        t["fact_contribution"][~t["fact_contribution"]["project_code"].isin(projects)].assign(
            record_key=lambda x: x["project_code"]),
    ])
    add("orphan_reference", orphans, "record_key", lambda x: f"{x.source_sheet} row {x.source_row}",
        len(k) + len(a) + len(r) + len(b) + len(t["fact_contribution"]))

    flag_df = pd.DataFrame(flags, columns=["rule", "level", "label", "record_key", "project_code", "source_sheet",
                                           "source_row", "detail"])
    spec = fmt()["rules"]
    summary = pd.DataFrame([{"rule": rule, "level": spec[rule]["level"], "label": spec[rule]["label"],
                             "table_name": spec[rule]["table"], "checked": n,
                             "flagged": int((flag_df["rule"] == rule).sum())} for rule, n in checked.items()])
    summary["pass_rate"] = (1 - summary["flagged"] / summary["checked"].where(summary["checked"] > 0)).fillna(1) * 100
    return flag_df, summary


def dq_score(summary: pd.DataFrame) -> float:
    """Average pass rate of the held-back and review rules (settings: arde.dq_score_levels)."""
    scored = summary[summary["level"].isin(arde_settings()["dq_score_levels"])]
    return float(scored["pass_rate"].mean()) if len(scored) else 100.0


# ---------------------------------------------------------------- source of truth and workbook figures
def compare_register(sheets: dict) -> pd.DataFrame:
    """Row by row: the working register ('Results & KPIs') against the KPIs and Results sheets. One row per field
    with the number of rows compared, how many differ, and example codes."""
    rk, k, r = sheets["Results & KPIs"], sheets["KPIs"], sheets["Results"]
    rows = []
    m = rk.merge(k, on="kpi_code", how="outer", suffixes=("_rk", "_k"), indicator=True)
    rows.append({"comparison": "KPI codes", "field": "kpi_code", "compared": len(m),
                 "differ": int((m["_merge"] != "both").sum()),
                 "examples": ", ".join(m.loc[m["_merge"] != "both", "kpi_code"].head(5)),
                 "note": "codes in one sheet and not the other"})
    both = m[m["_merge"] == "both"]
    same_order = list(rk["kpi_code"]) == list(k["kpi_code"])
    rows.append({"comparison": "KPI codes", "field": "row order", "compared": len(both), "differ": 0 if same_order else 1,
                 "examples": "", "note": "same order" if same_order else "different order"})
    fields = ["project_code", "result_code", "result_level", "indicator", "baseline", "target", "achieved",
              "achievement_pct", "performance_band", "unit", "frequency", "responsible", "kpi_status", "evidence"]
    for f in fields:
        x, y = both[f + "_rk"], both[f + "_k"]
        if f == "achievement_pct":
            xn, yn = pd.to_numeric(x, errors="coerce"), pd.to_numeric(y, errors="coerce")
            rounding = (xn - yn).abs() <= 0.0005
            differ = ~(rounding | (xn.isna() & yn.isna()))
            rows.append({"comparison": "Register vs KPIs sheet", "field": f + " (rounding only)", "compared": len(both),
                         "differ": int(((xn != yn) & rounding).sum()), "examples": ", ".join(
                             both.loc[(xn != yn) & rounding, "kpi_code"].head(3)),
                         "note": "KPIs sheet stores 3 decimals; same value"})
        else:
            differ = ~((x == y) | (x.isna() & y.isna()))
        rows.append({"comparison": "Register vs KPIs sheet", "field": f, "compared": len(both), "differ": int(differ.sum()),
                     "examples": ", ".join(both.loc[differ, "kpi_code"].head(5)), "note": ""})
    first = rk.drop_duplicates("result_code")
    mr = first.merge(r, on="result_code", how="outer", suffixes=("_rk", "_r"), indicator=True)
    only_r = mr[mr["_merge"] == "right_only"]
    rows.append({"comparison": "Register vs Results sheet", "field": "result_code", "compared": len(mr),
                 "differ": len(only_r), "examples": ", ".join(only_r["result_code"].head(5)),
                 "note": "results only in the Results sheet (no KPI): " + ", ".join(
                     f"{n} {lvl}" for lvl, n in only_r["level"].value_counts().items())})
    bm = mr[mr["_merge"] == "both"]
    for a_col, b_col in [("project_code_rk", "project_code_r"), ("result_level", "level"),
                         ("parent_result_rk", "parent_result_r"), ("statement_rk", "statement_r"),
                         ("result_status", "status")]:
        differ = ~((bm[a_col] == bm[b_col]) | (bm[a_col].isna() & bm[b_col].isna()))
        rows.append({"comparison": "Register vs Results sheet", "field": b_col.removesuffix("_r"), "compared": len(bm),
                     "differ": int(differ.sum()), "examples": ", ".join(bm.loc[differ, "result_code"].head(5)),
                     "note": ""})
    return pd.DataFrame(rows)


def workbook_figures(sheets: dict, t: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """The workbook's Dashboard and Data Quality figures next to ours, with whether we could rebuild each one."""
    from arde_reader import compare_cells
    p, k, r, a, b = t["dim_project"], t["fact_kpi"], t["fact_result"], t["fact_project_activity"], t["fact_reach"]
    rk = sheets["Results & KPIs"]
    dash = compare_cells(sheets["_compare"].get("Dashboard", []))
    dq = compare_cells(sheets["_compare"].get("Data Quality", []))
    rows = []

    def row(sheet, figure, theirs, ours, how):
        same = theirs is not None and ours is not None and abs(float(theirs) - float(ours)) < 1e-6
        rows.append({"sheet": sheet, "figure": figure, "workbook_value": theirs, "our_value": ours,
                     "rebuilt": "yes" if same else ("no" if theirs is not None else "not in workbook"), "how": how})

    row("Dashboard", "Projects", dash.get("Projects"), len(p), "count of Projects rows")
    row("Dashboard", "Results", dash.get("Results"), len(r), "count of Results rows")
    row("Dashboard", "KPIs", dash.get("KPIs"), len(k), "count of register KPI codes")
    row("Dashboard", "Activities", dash.get("Activities"), len(a), "count of Activities rows")
    row("Dashboard", "Direct beneficiaries", dash.get("Direct beneficiaries"), p["direct_beneficiaries"].sum(),
        "SUM of the Projects sheet's Direct Beneficiaries column (their formula). NOT the Beneficiaries sheet.")
    row("Dashboard", "Indirect beneficiaries", dash.get("Indirect beneficiaries"), p["indirect_beneficiaries"].sum(),
        "SUM of the Projects sheet's Indirect Beneficiaries column (their formula)")
    row("Dashboard", "Average progress", dash.get("Average progress"), p["progress_pct"].mean(),
        "simple average of Projects Progress % (not weighted by budget)")
    row("Dashboard", "KPIs achieved", dash.get("KPIs achieved"),
        int((pd.Series(rk["performance_band"]) == "Achieved").sum()),
        "count of register band 'Achieved' (their formula). Ours, recomputed: "
        f"{int((k['band'] == 'Achieved').sum())}")
    for status, n in p["status"].value_counts().items():
        row("Dashboard", f"Projects {status}", dash.get(status), n, "count by Projects Status")
    for area, g in p.groupby("intervention_area"):
        row("Dashboard", f"Direct reach: {area}", None, g["direct_beneficiaries"].sum(),
            "SUMIF of Projects Direct Beneficiaries by area (their formula; cell beside the area)")
    row("Data Quality", "Projects without intervention area", dq.get("Projects without intervention area"),
        int(p["intervention_area"].isna().sum()), "blank Intervention Area")
    row("Data Quality", "Projects without verification status", dq.get("Projects without verification status"),
        int(p["verification"].isna().sum()), "blank Verification")
    row("Data Quality", "KPIs without unit", dq.get("KPIs without unit"), int(rk["unit"].isna().sum()), "blank Unit")
    row("Data Quality", "KPIs without target", dq.get("KPIs without target"), int(rk["target"].isna().sum()),
        "BLANK target only (a target of 0 is not counted by their formula)")
    row("Data Quality", "KPIs not recorded", dq.get("KPIs not recorded"),
        int((rk["performance_band"] == "Not recorded").sum()),
        "register band 'Not recorded', which their formula gives only when the target is 0/blank or Achieved is "
        f"blank. Our rule (status Not started with nothing achieved): {int((k['band'] == 'Not recorded').sum())}")
    row("Data Quality", "Results/KPIs without status", dq.get("Results/KPIs without status"),
        int(rk["kpi_status"].isna().sum()), "blank KPI Status")
    out = pd.DataFrame(rows)
    # Area reach: the Dashboard's small table has the value two cells to the right of the area name.
    grid = {(rr, c): v for rr, cells in sheets["_compare"].get("Dashboard", []) for c, v in cells}
    for (rr, c), v in grid.items():
        if isinstance(v, str) and f"Direct reach: {v}" in set(out["figure"]):
            theirs = grid.get((rr, c + 2))
            i = out.index[out["figure"] == f"Direct reach: {v}"][0]
            out.loc[i, "workbook_value"] = theirs
            out.loc[i, "rebuilt"] = "yes" if theirs is not None and abs(float(theirs) - out.loc[i, "our_value"]) < 1e-6 else "no"
    return out
