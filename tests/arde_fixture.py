"""A small MADE-UP workbook in the layout of ARDE/KUBAHO's MEAL workbook, for the tests.

Nothing here comes from ARDE's file: codes (TP-A...), names and figures are invented. It has the same sheets, the
title block, the headings on row 6 and data from row 7, and one known example of each problem the rules look for:

  TP-A  EUR, budget used typed as 5123.45 (impossible); KPI at 200% of target; a KPI not started; women rows next
        to people rows (possible double counting); a General Objective with no KPI; staff name in Manager
  TP-B  RWF, approved budget 0; Completed at 50% progress; KPI with target 0; activity funds 0; Nyagatare + Goma
  TP-C  USD; ended 2020 but still On track; no district in the location; unit 'Cooperative'
  TP-D  RWF; Active, ends 2030; unit 'cooperatives'; activity funds 0
Every General Objective has the placeholder parent "47", as in ARDE's file.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from openpyxl import Workbook

D = dt.datetime
PROJECTS = [
    # code, title, area, donor, location, manager, start, end, budget, currency, used, progress, status, verif, direct, indirect
    ["TP-A", "Projet de promotion socio-économique des coopératives", "Water, Sanitation and Hygiene (WASH)",
     "Donor One", "Huye District, Southern Province, Rwanda", "TESTNAME Alice - Project Manager",
     D(2018, 1, 1), D(2020, 12, 31), 100000, "EUR", 5123.45, 1, "Completed", "Pending verification", 500, 100],
    ["TP-B", "Clean water for schools", "Community Livelihood & Humanitarian Actions", "Donor Two",
     "Nyagatare District, Rwanda and Goma, Democratic Republic of the Congo", "ARDE/KUBAHO project team",
     D(2021, 1, 1), D(2022, 12, 31), 0, "RWF", 0, 0.5, "Completed", "Verified", 300, 0],
    ["TP-C", "Farmers' cooperatives", "Sustainable Agriculture & Environmental Protection", "Donor Three",
     "Several villages (to be confirmed)", "Executive Director", D(2019, 1, 1), D(2020, 12, 31), 5000, "USD", 0.4,
     0.6, "On track", "Pending verification", 0, 0],
    ["TP-D", "Agroforestry", "Sustainable Agriculture & Environmental Protection", "Donor Four",
     "Karongi District, Western Province, Rwanda", "Project Manager", D(2025, 1, 1), D(2030, 12, 31), 1000000, "RWF",
     0.2, 0.3, "Active", "Pending verification", 50, 0],
]
RESULTS = [  # code, project, level, parent, statement, description, assumptions, status, order
    ["TPA-GO1", "TP-A", "General Objective", "47", "Communities have water", "d", "a", "Achieved", 1],
    ["TPA-GO2", "TP-A", "General Objective", "47", "A goal with no KPI", "d", "a", "Achieved", 2],
    ["TPA-SO1", "TP-A", "Specific Objective", "TPA-GO1", "Boreholes work", "d", "a", "Achieved", 1],
    ["TPA-O1", "TP-A", "Output", "TPA-SO1", "Boreholes repaired", "d", "a", "Achieved", 1],
    ["TPB-GO1", "TP-B", "General Objective", "47", "Schools have water", "d", "a", "Achieved", 1],
    ["TPB-SO1", "TP-B", "Specific Objective", "TPB-GO1", "Tanks", "d", "a", "Achieved", 1],
    ["TPB-O1", "TP-B", "Output", "TPB-SO1", "Tanks built", "d", "a", "Achieved", 1],
    ["TPC-GO1", "TP-C", "General Objective", "47", "Farmers earn more", "d", "a", "In progress", 1],
    ["TPC-SO1", "TP-C", "Specific Objective", "TPC-GO1", "Cooperatives", "d", "a", "In progress", 1],
    ["TPC-O1", "TP-C", "Output", "TPC-SO1", "Cooperatives formed", "d", "a", "In progress", 1],
    ["TPD-GO1", "TP-D", "General Objective", "47", "Trees", "d", "a", "In progress", 1],
    ["TPD-SO1", "TP-D", "Specific Objective", "TPD-GO1", "Planting", "d", "a", "In progress", 1],
    ["TPD-O1", "TP-D", "Output", "TPD-SO1", "Trees planted", "d", "a", "In progress", 1],
]
# kpi, project, result, level, indicator, baseline, target, achieved, unit, freq, responsible, status, evidence,
# typed achievement % in the KPIs sheet (K3 deliberately stale)
KPIS = [
    ["K1", "TP-A", "TPA-GO1", "General Objective", "Completion", 0, 100, 100, "%", "Endline", "M&E team", "Achieved", "report", 1.0],
    ["K2", "TP-A", "TPA-O1", "Output", "People trained", 0, 10, 20, "People", "Endline", "TESTNAME Alice", "Achieved", "list", 2.0],
    ["K3", "TP-A", "TPA-O1", "Output", "People served", 0, 10, 0, "people", "Annual", "M&E team", "Not started", "", 0.9],
    ["K4", "TP-B", "TPB-O1", "Output", "Tanks", 0, 0, 0, "Tanks", "Once", "Engineer", "Achieved", "photos", 1.0],
    ["K5", "TP-C", "TPC-SO1", "Specific Objective", "Cooperatives", 0, 100, 80, "Cooperative", "Annual", "Field Officer", "On track", "", 0.8],
    ["K6", "TP-D", "TPD-O1", "Output", "Cooperatives trained", 0, 100, 50, "cooperatives", "Annual", "Field Officer", "In progress", "", 0.5],
]
ACTIVITIES = [  # code, project, output, activity, description, n, personnel, funds, currency, materials, resp, start, end, progress, status
    ["A1", "TP-A", "TPA-O1", "Repair", "d", 2, "Technicians", 1000, "EUR", "parts", "Engineer", D(2018, 2, 1), D(2018, 3, 1), 1, "Completed"],
    ["A2", "TP-B", "TPB-O1", "Build", "d", 0, "Team", 0, "RWF", "", "Engineer", D(2021, 2, 1), D(2021, 3, 1), 1, "Completed"],
    ["A3", "TP-C", "TPC-O1", "Train", "d", 1, "Trainer", 500, "USD", "", "Officer", D(2019, 2, 1), D(2019, 3, 1), 0.5, "In progress"],
    ["A4", "TP-D", "TPD-O1", "Plant", "d", 3, "Team", 0, "RWF", "", "Officer", D(2025, 2, 1), D(2025, 3, 1), 0.2, "In progress"],
]
REACH = [  # project, category, reach type, count, unit, source row
    ["TP-A", "Community members", "Direct", 400, "People", 2],
    ["TP-A", "Women members", "Direct", 250, "Women", 3],
    ["TP-A", "Households served", "Direct", 50, "Households", 4],
    ["TP-A", "Neighbours", "Indirect", 100, "People", 5],
    ["TP-B", "Pupils", "Direct", 300, "People", 6],
    ["TP-D", "Cooperatives", "Direct", 3, "Cooperatives", 7],
]
STAKEHOLDERS = [
    ["TP-A", "Donor One", "Bilateral donor", "Financial", "Grant", 5000, "EUR", "agreement", ""],
    ["TP-B", "District", "Government / local authority", "In-kind", "Coordination", 0, "Not quantified", "report", ""],
]

HEADINGS = {
    "Projects": ["Project Code", "Project Title", "Intervention Area", "Donor / Partner", "Location", "Manager",
                 "Start Date", "End Date", "Approved Budget", "Currency", "Budget Used %", "Progress %", "Status",
                 "Verification", "Direct Beneficiaries", "Indirect Beneficiaries", "Total Reach", "Female", "Male",
                 "Youth", "Disability", "Direct Jobs", "Indirect Jobs"],
    "Results": ["Result Code", "Project Code", "Level", "Parent Result", "Statement", "Description", "Assumptions",
                "Status", "Order"],
    "KPIs": ["KPI Code", "Project Code", "Result Code", "Result Level", "Indicator", "Baseline", "Target", "Achieved",
             "Achievement %", "Performance Band", "Unit", "Frequency", "Responsible", "Status", "Evidence / Source"],
    "Results & KPIs": ["Project Code", "Project Title", "Intervention Area", "Result Code", "Result Level",
                       "Parent Result", "Result Statement", "Result Status", "KPI Code", "Indicator", "Unit",
                       "Baseline", "Target", "Achieved", "Achievement %", "Performance Band", "Frequency",
                       "Responsible", "KPI Status", "Evidence / Source", "Last Update", "Notes"],
    "Activities": ["Activity Code", "Project Code", "Output Code", "Activity", "Description", "Personnel Count",
                   "Personnel", "Funds", "Currency", "Materials / Inputs", "Responsible", "Start Date", "End Date",
                   "Progress %", "Status"],
    "Beneficiaries": ["Project Code", "Category", "Reach Type", "Count", "Unit", "Source Row"],
    "Stakeholders": ["Project Code", "Stakeholder", "Stakeholder Type", "Nature", "Contribution Type", "Value",
                     "Currency / Unit", "Evidence", "Notes"],
}


def register_band(target, achieved):
    """The register's own formula (column P)."""
    if not target or achieved is None:
        return "-", "Not recorded"
    ratio = achieved / target
    return ratio, "Achieved" if ratio >= 1 else "On track" if ratio >= 0.75 else "Needs attention"


def kpis_sheet_band(ratio):
    """The KPIs sheet's own formula (column J)."""
    return "Achieved" if ratio >= 1 else "On track" if ratio >= 0.75 else "Needs attention" if ratio > 0 else "Not recorded"


def rows(name):
    projects = {p[0]: p for p in PROJECTS}
    results = {r[0]: r for r in RESULTS}
    if name == "Projects":
        return [p + [p[14] + p[15], 0, 0, 0, 0, 0, 0] for p in PROJECTS]
    if name == "Results":
        return RESULTS
    if name == "KPIs":
        return [k[:8] + [k[13], kpis_sheet_band(k[13])] + k[8:13] for k in KPIS]
    if name == "Results & KPIs":
        out = []
        for k in KPIS:
            p, r = projects[k[1]], results[k[2]]
            ratio, band = register_band(k[6], k[7])
            out.append([k[1], p[1], p[2], k[2], k[3], r[3], r[4], r[7], k[0], k[4], k[8], k[5], k[6], k[7], ratio, band,
                        k[9], k[10], k[11], k[12], None, None])
        return out
    return {"Activities": ACTIVITIES, "Beneficiaries": REACH, "Stakeholders": STAKEHOLDERS}[name]


def build(path: Path) -> Path:
    wb = Workbook()
    wb.remove(wb.active)
    dash = wb.create_sheet("Dashboard")
    dash["A2"] = "Test MEAL Portfolio Dashboard"
    for col, label, value in [("A", "Projects", len(PROJECTS)), ("C", "Results", len(RESULTS)),
                              ("E", "KPIs", len(KPIS)), ("G", "Activities", len(ACTIVITIES))]:
        dash[f"{col}8"], dash[f"{col}9"] = label, value
    reg = rows("Results & KPIs")
    for col, label, value in [("A", "Direct beneficiaries", sum(p[14] for p in PROJECTS)),
                              ("C", "Indirect beneficiaries", sum(p[15] for p in PROJECTS)),
                              ("E", "Average progress", sum(p[11] for p in PROJECTS) / len(PROJECTS)),
                              ("G", "KPIs achieved", sum(1 for r in reg if r[15] == "Achieved"))]:
        dash[f"{col}11"], dash[f"{col}12"] = label, value
    for name in HEADINGS:
        ws = wb.create_sheet(name)
        ws["A2"], ws["A3"] = name, "Test sheet"
        for j, h in enumerate(HEADINGS[name], start=1):
            ws.cell(6, j, h)
        for i, row in enumerate(rows(name), start=7):
            for j, v in enumerate(row, start=1):
                ws.cell(i, j, v)
        for i in range(7 + len(rows(name)), 7 + len(rows(name)) + 3):      # formatted blank rows at the end
            ws.cell(i, 1, None)
    dq = wb.create_sheet("Data Quality")
    dq["A2"] = "Data Quality Review"
    for j, h in enumerate(["Check", "Result", "Status", "Required Action"], start=1):
        dq.cell(6, j, h)
    dq["A7"], dq["B7"] = "KPIs not recorded", sum(1 for r in reg if r[15] == "Not recorded")
    wb.save(path)
    return path
