"""Write docs/arde_sample_profile.md (what the ARDE/KUBAHO workbook holds and what the rules found) and
docs/arde_data_dictionary.md (the tables and columns of arde mode).

The profile quotes the data (codes, counts, amounts), so it is CONFIDENTIAL and gitignored. The data dictionary
holds only table and column names and their meanings, so it can be committed.

Run by src/arde_pipeline.py; not run on its own.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd

import arde_model as am

# The known problems in the team's instruction 21, section 3, in its order, with the rule codes that check them.
KNOWN = [
    (1, "Budget used % holds impossible values", ["budget_used_impossible", "budget_used_over_100"]),
    (2, "Approved budget is 0", ["budget_zero"]),
    (3, "Budgets and funds in several currencies", ["currency_converted", "activity_currency_converted"]),
    (4, "Units differ only by case or spelling", ["unit_variant", "reach_unit_variant"]),
    (5, "KPIs not recorded / not started", ["kpi_not_recorded"]),
    (6, "Projects past their end date still active; completed at low progress",
     ["past_end_still_active", "completed_low_progress"]),
    (7, "General Objectives with a placeholder parent", ["parent_placeholder"]),
    (8, "KPIs achieved above 150% of target", ["kpi_over_150"]),
    (9, "Activities with funds of 0", ["activity_funds_zero"]),
    (10, "Reach mixes units; possible double counting",
     ["reach_mixed_units", "reach_possible_double_count", "reach_register_differs"]),
    (11, "Mixed languages in titles", ["title_not_english"]),
]

DESCRIPTIONS = {
    "dim_project": "One row per project (Projects sheet), every column of the sheet plus the fields below.",
    "dim_project_district": "One row per project and Rwandan district named in its location text.",
    "fact_result": "The results chain (Results sheet): General Objective > Specific Objective > Output.",
    "fact_kpi": "One row per KPI, from the working register ('Results & KPIs'), with dashboard updates applied.",
    "fact_project_activity": "One row per activity (Activities sheet), linked to an output.",
    "fact_reach": "Reach by project and category (Beneficiaries sheet). Never added across units.",
    "fact_contribution": "Partner contributions, financial and in-kind (Stakeholders sheet).",
    "dq_rule_results": "One row per record flagged by a data-quality rule (config/arde_format.yaml: rules).",
    "dq_rule_summary": "One row per rule: records checked, flagged, pass rate.",
    "source_of_truth_comparison": "The working register compared field by field with the KPIs and Results sheets.",
    "workbook_figures_comparison": "The workbook's Dashboard and Data Quality figures next to ours.",
    "kpi_change_history": "Every change made on the KPI update page: who, when, old and new value.",
    "run_info": "When the figures were built, from which workbook, the data-quality score.",
    "sheet_inventory": "The workbook's sheets, rows read and whether each was imported or compared only.",
}
COLUMN_NOTES = {
    "budget_rwf_estimate": "Approved budget converted to RWF with the rate for the start year (an ESTIMATE).",
    "fx_rate_used": "RWF per unit of currency used for the estimate (settings: arde.exchange_rates_rwf_per_unit).",
    "fx_rate_year": "Year of the exchange rate used.",
    "budget_used_valid": "Budget used % if possible (0 to 150%), else empty: shown as 'invalid, check'.",
    "budget_used_check": "'invalid, check' or 'over 100%, check' when the budget used % needs checking.",
    "progress_valid": "Progress % if between 0 and 100%, else empty.",
    "districts": "Rwandan districts found in the location text, separated by ';'.",
    "district_count": "Number of districts found (0 = flagged for review).",
    "outside_rwanda": "True if the location also names a place outside Rwanda (e.g. Goma).",
    "title_language": "English, French or Kinyarwanda, by marker words. Titles are never changed.",
    "parent_is_valid": "True if the parent result is a real result code (General Objectives use a placeholder).",
    "kpi_count": "Number of KPIs attached to the result.",
    "unit_original": "The unit exactly as written in the workbook.",
    "unit": "The unit normalised (lower case, one spelling: config/arde_format.yaml unit_aliases).",
    "unit_type": "people, households, organisations or other (config/arde_format.yaml unit_types).",
    "achievement": "Achieved / target, recomputed (empty when there is no target).",
    "band": "Our performance band: Achieved, On track, Needs attention, Not recorded or No target.",
    "achievement_workbook": "Achievement % as calculated in the working register.",
    "band_workbook": "Performance band as calculated in the working register.",
    "achievement_kpis_sheet": "Achievement % as typed in the KPIs sheet (rounded; may be out of date).",
    "band_kpis_sheet": "Performance band in the KPIs sheet (its formula differs from the register's).",
    "kpis_sheet_row": "The KPI's row in the KPIs sheet.",
    "achieved_workbook": "Achieved value in the workbook, before any dashboard update.",
    "status_workbook": "KPI status in the workbook, before any dashboard update.",
    "updated_by": "Staff code of the person who updated the KPI on the dashboard (empty = workbook value).",
    "updated_at": "When the KPI was updated on the dashboard.",
    "update_id": "The update's number (KU0001...).",
    "funds_rwf_estimate": "Funds converted to RWF with the rate for the activity's start year (an ESTIMATE).",
    "is_headline_people": "True if the unit is exactly 'people' (the only rows in the headline people reach).",
    "currency": "EUR, RWF or USD when the value is money; empty for in-kind values in other units.",
    "value_rwf_estimate": "Money value converted to RWF (an ESTIMATE); empty for non-money values.",
    "is_money": "True if the value is an amount of money.",
    "source_file": "Lineage: the workbook file the row came from.",
    "source_sheet": "Lineage: the sheet.",
    "source_row": "Lineage: the row number as seen in Excel.",
    "workbook_source_row": "ARDE's own 'Source Row' reference in the Beneficiaries sheet, kept as it is.",
}


def _md(df: pd.DataFrame, max_rows: int | None = None) -> str:
    if not len(df):
        return "_None._\n"
    shown = df.head(max_rows) if max_rows else df
    head = "| " + " | ".join(str(c) for c in shown.columns) + " |\n|" + "---|" * len(shown.columns) + "\n"
    body = "".join("| " + " | ".join("" if (v is None or (isinstance(v, float) and pd.isna(v))) else
                                       (f"{v:,.2f}" if isinstance(v, float) and not float(v).is_integer() else
                                        (f"{int(v):,}" if isinstance(v, float) else str(v).replace("|", "/")))
                                       for v in row) + " |\n" for row in shown.itertuples(index=False))
    more = f"\n_{len(df) - max_rows} more rows in the database._\n" if max_rows and len(df) > max_rows else ""
    return head + body + more


def write(run: dict, tables: dict, target: Path) -> None:
    t, flags, summary = run["tables"], run["flags"], run["summary"]
    p, k, a, b, c = (t["dim_project"], t["fact_kpi"], t["fact_project_activity"], t["fact_reach"],
                     t["fact_contribution"])
    info = tables["run_info"].iloc[0]
    L = ["# ARDE/KUBAHO sample workbook: profile", "",
         "> **CONFIDENTIAL. ARDE/KUBAHO data, for project use only. This file is gitignored: never commit, push or "
         "share it outside the project team.**", "",
         f"Written by `src/arde_pipeline.py` on {dt.datetime.now():%d %B %Y, %H:%M} from `{info['workbook']}` "
         f"({info['workbook_uploaded_at']}). Checks dated as of {info['as_of']}. Dashboard KPI updates applied: "
         f"{info['kpi_updates_applied']}.", "",
         "## 1. Sheet inventory", "",
         "Every sheet has a title block; the column headings are on row 6 and the data starts on row 7. The workbook "
         "is read in read-only mode (a doughnut chart on the Dashboard sheet stops openpyxl's normal mode).", "",
         _md(tables["sheet_inventory"]), ""]

    sot = run["source_of_truth"]
    L += ["## 2. Source of truth", "",
          "The working register ('Results & KPIs') was compared row by row with the KPIs and Results sheets:", "",
          _md(sot), "",
          "**Decision.** KPI values come from the **working register**: every input (codes, target, achieved, unit, "
          "status, responsible, evidence) is identical in both sheets, but the register recalculates Achievement % "
          "and the band from target and achieved, while the KPIs sheet's Achievement % is typed in (rounded, and out "
          "of date where the 'rounding only' line does not explain the difference). The **results chain** comes from "
          "the **Results sheet**: it agrees with the register on every shared result, and it also holds the results "
          "that have no KPI (which the register cannot show) and the descriptions, assumptions and order. Logged in "
          "docs/decision_log.md (10 November 2026).", ""]

    L += ["## 3. Data-quality rules", "",
          f"Data-quality score: **{run['score']:.1f}%** (average pass rate of the held-back and review rules; info "
          "rules are reported but not scored). Rules flag; none changes a value.", "",
          "### The known problems (instruction 21, section 3)", ""]
    for number, title, rules in KNOWN:
        L.append(f"**{number}. {title}.**")
        for rule in rules:
            row = summary[summary["rule"] == rule].iloc[0]
            examples = ", ".join(str(x) for x in flags.loc[flags["rule"] == rule, "record_key"].head(5))
            L.append(f"- `{rule}` ({row['level']}): {row['flagged']} of {row['checked']} flagged. "
                     + (f"Examples: {examples}." if examples else ""))
        if number == 1:
            vals = p.loc[p["budget_used_check"] == "invalid, check", "budget_used_pct"]
            L.append(f"- Values: {', '.join(f'{v:,.2f}' for v in vals)}. Not used; shown as \"invalid, check\".")
        if number == 3:
            L.append("- Approved budgets by currency (never added across currencies): "
                     + "; ".join(f"{cur} {v:,.0f}" for cur, v in am.sum_by_currency(p, "approved_budget").items())
                     + f". RWF estimate of all budgets: RWF {p['budget_rwf_estimate'].sum():,.0f} (estimate; "
                     "approximate annual rates, to be confirmed).")
            L.append("- Activity funds by currency: "
                     + "; ".join(f"{cur} {v:,.0f}" for cur, v in am.sum_by_currency(a, "funds").items()) + ".")
        if number == 4:
            forms = am.variant_forms(pd.concat([k[["unit_original", "unit"]], b[["unit_original", "unit"]]]))
            L.append(f"- {len(forms)} units are written in more than one way (KPIs and Beneficiaries sheets). Each is "
                     "normalised to one spelling (lower case, plus config/arde_format.yaml unit_aliases); the "
                     "original is kept in unit_original:")
            L.append("")
            L.append(_md(pd.DataFrame({"Normalised": list(forms), "Written as": list(forms.values())})))
        if number == 5:
            wb_nr = int((k["band_workbook"] == "Not recorded").sum())
            L.append(f"- Our count: {int((k['band'] == 'Not recorded').sum())} KPIs with status "
                     f"{' / '.join(am.arde_settings()['not_recorded_statuses'])} and nothing achieved "
                     f"(the KPIs sheet's band says 'Not recorded' for {int((k['band_kpis_sheet'] == 'Not recorded').sum())}).")
            L.append(f"- The workbook's Data Quality sheet says {wb_nr}. **Why they differ:** its check counts the "
                     "register's band 'Not recorded', and the register's formula gives 'Not recorded' only when the "
                     "target is 0 or blank or Achieved is blank. A KPI that is Not started with 0 achieved gets 0% "
                     "and the band 'Needs attention' in the register, so it is not counted. The KPIs sheet uses a "
                     "different formula (0% = 'Not recorded'). Both counts are reported; the dashboard uses ours.")
        if number == 10:
            direct = b[b["reach_type"] == "Direct"]
            L.append(f"- Direct rows of the Beneficiaries sheet added regardless of unit (meaningless, shown only to "
                     f"explain the gap): {direct['count'].sum():,.0f}.")
            L.append(f"- The Dashboard's direct beneficiaries ({p['direct_beneficiaries'].sum():,.0f}) is "
                     "the SUM of the Projects sheet's Direct Beneficiaries column, not the "
                     "Beneficiaries sheet. **Rule found.** Whether that column counts people only is an open "
                     "question (docs/partner_questions.md).")
            tot = am.totals_by_unit(b)
            L.append("- Totals per unit (the only totals the dashboard shows):")
            L.append("")
            L.append(_md(tot.rename(columns={"reach_type": "Reach", "unit_type": "Unit type", "unit": "Unit",
                                             "count": "Total"})))
        L.append("")

    L += ["### Every rule", "", _md(summary.assign(pass_rate=summary["pass_rate"].round(1))), ""]
    L += ["## 4. The workbook's Dashboard and Data Quality figures", "",
          "Which of their figures we could rebuild from the data sheets (\"yes\" = same number):", "",
          _md(run["workbook_figures"]), ""]
    rebuilt = run["workbook_figures"]
    L.append(f"Rebuilt {int((rebuilt['rebuilt'] == 'yes').sum())} of {int(rebuilt['workbook_value'].notna().sum())} "
             "figures that have a value in the workbook. Figures we could not rebuild are explained in the 'how' "
             "column. The Dashboard's charts were not read (charts are not data).")
    L += ["", "## 5. Places", "",
          f"Districts found in the location text for {int((p['district_count'] > 0).sum())} of {len(p)} projects; "
          f"{int((p['district_count'] > 1).sum())} name more than one district; {int(p['outside_rwanda'].sum())} also "
          "name a place outside Rwanda. Reach is never split between districts (the workbook does not say how).", "",
          _md(t["dim_project_district"].groupby(["province", "district"]).size().reset_index(name="projects")), "",
          "## 6. Staff names", "",
          "Manager, Personnel and Responsible are stored in full in the database (under data/real/ only). On the "
          "dashboard they are shown through the roles-only filter: names listed in data/real/staff_names_hidden.yaml "
          "become \"[name]\" and \"Name - Role\" becomes \"Role\".", "",
          "## 7. Open questions", "", "See docs/partner_questions.md, section \"ARDE/KUBAHO sample workbook\".", ""]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(L), encoding="utf-8")


def write_dictionary(tables: dict, target: Path) -> None:
    """Table and column names with their meanings: no data values."""
    L = ["# Data dictionary: ARDE/KUBAHO workbook mode", "",
         "_Generated by `src/arde_pipeline.py` from the database schema. Column names and meanings only, no data. "
         "The database itself is `data/real/warehouse/arde_workbook.duckdb` (gitignored)._", "",
         "Columns copied from the workbook keep the workbook's meaning (headings mapped in "
         "`config/arde_format.yaml`). Added columns are described below. Every fact row has its lineage "
         "(source_file, source_sheet, source_row).", ""]
    for name, df in tables.items():
        L += [f"## {name}", "", DESCRIPTIONS.get(name, ""), "", "| Column | Type | Meaning |", "|---|---|---|"]
        for col, dtype in df.dtypes.items():
            L.append(f"| {col} | {dtype} | {COLUMN_NOTES.get(col, '')} |")
        L.append("")
    target.write_text("\n".join(L), encoding="utf-8")
