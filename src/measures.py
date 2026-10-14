"""The dashboard's figures, each worked out in ONE place.

Every number that appears on more than one page (people reached, people pending duplicate review, activities,
spending, the weighted pipeline and its themes, reconciliation counts, indicator statuses) comes from a function
here, so the pages cannot disagree. tests/test_consistency.py checks that totals match across pages and that
every breakdown adds up to its total, under several filter combinations.

Each function takes `run`, a function that runs a SQL query on the warehouse and returns a table
(ui.query on the dashboard; a plain DuckDB connection in the tests), and the filter choices.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

UNKNOWN_DISTRICT = "Unknown district"


def in_list(values: list) -> str:
    """SQL placeholders for an IN (...) list."""
    return "(" + ", ".join("?" for _ in values) + ")" if values else "(NULL)"


# ---------------------------------------------------------------- people
def people_by_district(run, project_ids: list, start, end, district: str | None = None,
                       sex: str | None = None) -> pd.DataFrame:
    """Different people who received a service in the date range, by the district where they REGISTERED.

    People whose registration has no usable location are shown as "Unknown district", so the districts always
    add up to the total. Each person has one registration district, so no one is counted in two districts.
    Columns: district, people, pending (pending duplicate review), women, known_sex.
    """
    clauses, params = [], []
    if district:
        clauses.append("AND l.district = ?")
        params.append(district)
    if sex:
        clauses.append("AND b.sex = ?")
        params.append(sex)
    return run(f"""
        SELECT COALESCE(l.district, '{UNKNOWN_DISTRICT}') AS district,
               COUNT(DISTINCT s.beneficiary_key) AS people,
               COUNT(DISTINCT CASE WHEN b.pending_duplicate_review THEN s.beneficiary_key END) AS pending,
               COUNT(DISTINCT CASE WHEN b.sex = 'female' THEN s.beneficiary_key END) AS women,
               COUNT(DISTINCT CASE WHEN b.sex IS NOT NULL THEN s.beneficiary_key END) AS known_sex
        FROM fact_beneficiary_service s JOIN dim_activity a USING (activity_id)
        JOIN dim_beneficiary b USING (beneficiary_key) LEFT JOIN dim_location l ON l.location_id = b.location_id
        WHERE a.project_id IN {in_list(project_ids)} AND s.date BETWEEN ? AND ? {' '.join(clauses)}
        GROUP BY 1 ORDER BY 1""", *project_ids, start, end, *params)


def people_reached(run, project_ids: list, start, end, district: str | None = None, sex: str | None = None) -> dict:
    """Totals of people_by_district (so the total and the district breakdown always agree)."""
    d = people_by_district(run, project_ids, start, end, district, sex)
    total = {c: int(d[c].sum()) for c in ("people", "pending", "women", "known_sex")}
    total["unknown_district"] = int(d.loc[d["district"] == UNKNOWN_DISTRICT, "people"].sum())
    return total


def pending_in_register(run) -> int:
    """People in the WHOLE register pending duplicate review (any project, any date: filters do not apply)."""
    n = run("SELECT SUM(CASE WHEN pending_duplicate_review THEN 1 ELSE 0 END) AS n FROM dim_beneficiary")["n"].iloc[0]
    return int(n or 0)


def people_by_month(run, project_ids: list, start, end, district: str | None = None,
                    sex: str | None = None) -> pd.DataFrame:
    """Different people who received a service in each month (NOT cumulative: a person served in March and in
    April counts once in each month)."""
    clauses, params = [], []
    if district:
        clauses.append("AND l.district = ?")
        params.append(district)
    if sex:
        clauses.append("AND b.sex = ?")
        params.append(sex)
    return run(f"""
        SELECT date_trunc('month', s.date) AS month, COUNT(DISTINCT s.beneficiary_key) AS people
        FROM fact_beneficiary_service s JOIN dim_activity a USING (activity_id) JOIN dim_beneficiary b USING (beneficiary_key)
        LEFT JOIN dim_location l ON l.location_id = b.location_id
        WHERE a.project_id IN {in_list(project_ids)} AND s.date BETWEEN ? AND ? {' '.join(clauses)}
        GROUP BY 1 ORDER BY 1""", *project_ids, start, end, *params)


# ---------------------------------------------------------------- activities and spending
def activities_by_district(run, project_ids: list, start, end, district: str | None = None) -> pd.DataFrame:
    """Activities completed (on time or late) in the date range, by the district where they TOOK PLACE.
    Columns: district, activities, spend (RWF), attendance."""
    clause, params = ("AND l.district = ?", [district]) if district else ("", [])
    return run(f"""
        SELECT COALESCE(l.district, '{UNKNOWN_DISTRICT}') AS district, COUNT(*) AS activities,
               COALESCE(SUM(f.cost_rwf), 0) AS spend, COALESCE(SUM(f.participants_total), 0) AS attendance
        FROM fact_activity f JOIN dim_activity a USING (activity_id) LEFT JOIN dim_location l USING (location_id)
        WHERE a.project_id IN {in_list(project_ids)} AND f.status IN ('completed', 'delayed')
          AND f.date BETWEEN ? AND ? {clause}
        GROUP BY 1 ORDER BY 1""", *project_ids, start, end, *params)


def activities_total(run, project_ids: list, start, end, district: str | None = None) -> dict:
    d = activities_by_district(run, project_ids, start, end, district)
    return dict(activities=int(d["activities"].sum()), spend=float(d["spend"].sum()),
                attendance=int(d["attendance"].sum()))


def budget_total(run, project_ids: list) -> float:
    b = run(f"SELECT SUM(budget_rwf) AS b FROM dim_project WHERE project_id IN {in_list(project_ids)}",
            *project_ids)["b"].iloc[0]
    return float(b or 0)


# ---------------------------------------------------------------- donor pipeline
def opportunities(run, settings: dict) -> pd.DataFrame:
    """Every opportunity, with the weighted value (requested x probability) and whether it is still open."""
    opps = run("""SELECT o.*, d.donor_name, d.donor_type FROM fact_opportunity o LEFT JOIN dim_donor d USING (donor_key)""")
    for c in ("deadline", "next_action_date"):
        opps[c] = pd.to_datetime(opps[c])
    opps["weighted"] = opps["requested_amount_rwf"] * opps["probability"]
    opps["is_open"] = opps["stage"].isin(settings["donor_pipeline"]["open_stages"])
    return opps


def theme_shares(thematic_fit, themes: list) -> dict:
    """How an opportunity's value is shared between themes (settings: multi_theme_allocation = split_equally).

    "WASH; Agriculture" gives {WASH: 0.5, Agriculture: 0.5}; a theme not in the list goes to "Other themes";
    a blank goes to "No theme recorded". The shares always add up to 1, so no value is counted twice.
    """
    if thematic_fit is None or (isinstance(thematic_fit, float) and np.isnan(thematic_fit)) or not str(thematic_fit).strip():
        return {"No theme recorded": 1.0}
    parts = [p.strip() for p in str(thematic_fit).replace(",", ";").split(";") if p.strip()]
    named = [p if p in themes else "Other themes" for p in parts]
    shares: dict[str, float] = {}
    for p in named:
        shares[p] = shares.get(p, 0) + 1 / len(named)
    return shares


def pipeline_by_theme(opps: pd.DataFrame, settings: dict) -> pd.DataFrame:
    """Open opportunities' weighted and requested value by theme. The themes add up to the open pipeline.
    Columns: theme, weighted, requested, opportunities (an opportunity split between two themes counts 0.5 in each)."""
    themes = settings["donor_pipeline"]["themes"]
    rows = []
    for r in opps[opps["is_open"]].itertuples():
        for theme, share in theme_shares(r.thematic_fit, themes).items():
            rows.append(dict(theme=theme, weighted=(r.weighted or 0) * share,
                             requested=(r.requested_amount_rwf or 0) * share, opportunities=share))
    out = pd.DataFrame(rows, columns=["theme", "weighted", "requested", "opportunities"])
    out = out.groupby("theme", as_index=False).sum()
    order = {t: i for i, t in enumerate(themes)}
    return out.sort_values("theme", key=lambda s: s.map(lambda t: order.get(t, 99))).reset_index(drop=True)


def ending_projects(run, as_of: dt.date, settings: dict) -> tuple[pd.DataFrame, dt.date]:
    """Projects ending within the configured number of months of the as-of date (donor_pipeline.ending_within_months),
    with their budgets and theme. Returns (table, the cut-off date)."""
    months = settings["donor_pipeline"]["ending_within_months"]
    cutoff = (pd.Timestamp(as_of) + pd.DateOffset(months=months)).date()
    ending = run("""SELECT p.project_id, p.name, p.budget_rwf, p.end_date, g.thematic_area AS theme
                    FROM dim_project p JOIN dim_programme g USING (programme_id)
                    WHERE p.end_date <= ? ORDER BY p.end_date""", cutoff)
    return ending, cutoff


def pipeline_gaps(run, opps: pd.DataFrame, as_of: dt.date, settings: dict) -> tuple[pd.DataFrame, dt.date]:
    """Pipeline gap by theme = budgets of projects ending within N months - weighted open pipeline for that theme.
    (Our definition, to be confirmed with partner.) Columns: theme, projects, ending_budget, weighted, gap."""
    ending, cutoff = ending_projects(run, as_of, settings)
    by_theme = pipeline_by_theme(opps, settings).set_index("theme")
    rows = []
    for theme in settings["donor_pipeline"]["themes"]:
        e = ending[ending["theme"] == theme]
        weighted = float(by_theme["weighted"].get(theme, 0.0))
        rows.append(dict(theme=theme, projects=len(e), ending_budget=float(e["budget_rwf"].sum()),
                         weighted=weighted, gap=float(e["budget_rwf"].sum()) - weighted))
    return pd.DataFrame(rows), cutoff


def deadlines_within(opps: pd.DataFrame, as_of: dt.date, days: int) -> pd.DataFrame:
    """Open opportunities with a deadline from the as-of date to `days` days later."""
    o = opps[opps["is_open"]]
    return o[(o["deadline"] >= pd.Timestamp(as_of)) &
             (o["deadline"] <= pd.Timestamp(as_of + dt.timedelta(days=days)))].sort_values("deadline")


def overdue_actions(opps: pd.DataFrame, as_of: dt.date) -> pd.DataFrame:
    o = opps[opps["is_open"]]
    return o[o["next_action_date"] < pd.Timestamp(as_of)]


# ---------------------------------------------------------------- reconciliation
RECONCILIATION_GROUPS = ["within tolerance", "gap above tolerance", "derived only"]


def reconciliation(run, project_ids: list, start, end, district: str | None = None,
                   sex: str | None = None) -> pd.DataFrame:
    """Month-by-month reported-versus-records comparisons (by project and district) in the selection.
    Totals only, or one sex when the sex filter is set."""
    clause, params = ("AND district = ?", [district]) if district else ("", [])
    rec = run(f"""SELECT * FROM indicator_reconciliation WHERE district <> 'All' AND project_id IN {in_list(project_ids)}
                  AND period_start BETWEEN ? AND ? {clause}""", *project_ids, start, end, *params)
    return rec[rec["disaggregation"] == (f"sex={sex}" if sex else "total")]


def reconciliation_counts(rec: pd.DataFrame) -> dict:
    """Months compared and how many in each status. The statuses add up to the months compared."""
    counts = {s: int((rec["status"] == s).sum()) for s in RECONCILIATION_GROUPS}
    counts["compared"] = len(rec)
    return counts


def difference_in_words(reported, derived) -> str:
    """'Reported 18 more than the records', 'Reported 12 fewer than the records', or 'Same as the records'."""
    if pd.isna(reported):
        return f"No report; the records show {derived:,.0f}"
    diff = reported - derived
    if abs(diff) < 1e-9:
        return "Same as the records"
    word = "more" if diff > 0 else "fewer"
    pct = f" ({abs(diff) / reported:.0%} of the report)" if reported else ""
    return f"Reported {abs(diff):,.0f} {word} than the records{pct}"


# ---------------------------------------------------------------- indicators
def indicator_scope(f) -> tuple[list, str, bool]:
    """Which stored values to show for the filters. Values exist for each project and district, each project across
    districts, and all projects together. Returns (project list, district, one row per project?)."""
    district = f.district or "All"
    if f.project_id:
        return [f.project_id], district, False
    if f.programme_id or f.district:
        return list(f.project_ids), district, True
    return ["All"], district, False


def indicator_rows(run, catalogue: dict, period_type: str, period: str, f) -> pd.DataFrame:
    """One row per indicator (and per project, when a programme or a district is chosen without a project).

    The headline value is the REPORTED value where the indicator is reported, otherwise the value worked out from
    the records. For indicators where the two count the same thing (like_for_like), the records' value is added
    so the row can say "Records show 247 (6% lower)".
    """
    plist, district, per_project = indicator_scope(f)
    v = run(f"""SELECT v.*, i.name FROM indicator_values v JOIN dim_indicator i USING (indicator_id)
                WHERE v.period_type = ? AND v.period = ? AND v.district = ? AND v.project_id IN {in_list(plist)}""",
            period_type, period, district, *plist)
    by_sex = v["indicator_code"].map(lambda c: catalogue[c]["disaggregation"] == "sex")
    want = np.where(by_sex & bool(f.sex), f"sex={f.sex}", "total")
    v = v[v["disaggregation"] == want]
    keys = ["indicator_code", "project_id"]
    rep = v[v["source"] == "reported"].set_index(keys)
    der = v[v["source"] == "derived"].set_index(keys)
    head = pd.concat([rep, der[~der.index.isin(rep.index)]])
    like = {c for c, i in catalogue.items() if i.get("calculation", {}).get("derived", {}).get("like_for_like")}
    records = der["actual"].rename("records_value")
    head = head.join(records, how="left")
    head.loc[~head.index.get_level_values(0).isin(like) | (head["source"] != "reported"), "records_value"] = np.nan
    head = head.reset_index()
    order = {c: i for i, c in enumerate(catalogue)}
    head = head.sort_values(["indicator_code", "project_id"], key=lambda s: s.map(order) if s.name == "indicator_code"
                            else s).reset_index(drop=True)
    head["per_project"] = per_project
    return head


def records_comparison(reported, records) -> str:
    """'Records show 247 (6% lower)' for the indicator table."""
    if pd.isna(records) or pd.isna(reported):
        return ""
    if reported == 0:
        return f"Records show {records:,.0f}"
    pct = 100 * (records - reported) / reported
    if abs(pct) < 0.5:
        return f"Records show {records:,.0f} (the same)"
    return f"Records show {records:,.0f} ({abs(pct):.0f}% {'higher' if pct > 0 else 'lower'})"


def status_counts(rows: pd.DataFrame) -> dict:
    """How many indicator rows are in each status; the counts add up to the number of rows."""
    counts = rows["status"].value_counts().to_dict()
    counts["total"] = len(rows)
    return counts
