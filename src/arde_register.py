"""Download register: the current ARDE/KUBAHO data as an Excel file with the same sheets and columns as ARDE's
own MEAL workbook (data_mode: arde).

The file has the same title block, the column headings on row 6, the data from row 7, and the same formulas as
ARDE's workbook for the calculated cells (Achievement % and Performance Band in 'Results & KPIs', Total Reach in
Projects, and the Dashboard and Data Quality sheets), so it behaves the same way when opened in Excel. KPI updates
made on the dashboard are included (achieved value, status, and the date in "Last Update").

The file can be uploaded again on the Upload Excel page: it is read exactly like ARDE's workbook.
Charts are not copied (the Dashboard sheet's charts are ARDE's own; their figures are rebuilt here as formulas).
"""

from __future__ import annotations

import datetime as dt
import io

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from common import load_yaml

TITLES = {
    "Results & KPIs": ("Results and KPIs Working Register",
                       "Edit amber cells only. Achievement and performance formulas update automatically."),
    "Projects": ("Projects", "Portfolio register with delivery, budget, reach and verification information"),
    "Results": ("Results Chain", "Goals, outcomes and outputs linked to each project"),
    "KPIs": ("Results and KPIs", "Indicators with baselines, targets, achievements, units and accountability"),
    "Activities": ("Activities and Resources",
                   "Implementation activities linked to outputs, personnel, funds and delivery progress"),
    "Beneficiaries": ("Beneficiary Records", "Reach by project, beneficiary category and measurement unit"),
    "Stakeholders": ("Stakeholder Contributions", "Partners and stakeholders, contribution type, value and evidence"),
}
SHEET_ORDER = ["Dashboard", "Results & KPIs", "Projects", "Results", "KPIs", "Activities", "Beneficiaries",
               "Stakeholders", "Data Quality"]
AMBER = PatternFill("solid", fgColor="FFE699")
BLUE_GREY = PatternFill("solid", fgColor="D9E1F2")
HEAD = PatternFill("solid", fgColor="1F4E78")
HEADER_ROW = 6


def _value(v):
    if v is None or (isinstance(v, float) and pd.isna(v)) or v is pd.NaT:
        return None
    if isinstance(v, pd.Timestamp):
        return v.to_pydatetime()
    if hasattr(v, "item"):
        return v.item()
    return v


def _sheet_frames(t: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """The tables back in the workbook's own columns (database names from config/arde_format.yaml)."""
    k = t["fact_kpi"].copy()
    k["unit"] = k["unit_original"]
    k["performance_band"] = k["band_workbook"]
    k["achievement_pct"] = k["achievement"]
    k["last_update"] = k["updated_at"].where(k["updated_at"].notna(), k.get("last_update"))
    kp = k.copy()
    kp["performance_band"] = k["band_kpis_sheet"]
    b = t["fact_reach"].copy()
    b["unit"] = b["unit_original"]
    return {"Projects": t["dim_project"], "Results": t["fact_result"], "KPIs": kp, "Results & KPIs": k,
            "Activities": t["fact_project_activity"], "Beneficiaries": b, "Stakeholders": t["fact_contribution"]}


def build(t: dict[str, pd.DataFrame], note: str = "") -> bytes:
    """The workbook as bytes (for a download button)."""
    spec = load_yaml("arde_format.yaml")["sheets"]
    frames = _sheet_frames(t)
    wb = Workbook()
    wb.remove(wb.active)
    sizes = {}
    for name in SHEET_ORDER:
        ws = wb.create_sheet(name)
        if name in ("Dashboard", "Data Quality"):
            continue
        title, subtitle = TITLES[name]
        ws["A2"], ws["A3"] = title, subtitle
        ws["A2"].font = Font(bold=True, size=14)
        headings = list(spec[name]["columns"])
        fields = list(spec[name]["columns"].values())
        df = frames[name]
        for j, h in enumerate(headings, start=1):
            c = ws.cell(HEADER_ROW, j, h)
            c.font, c.fill = Font(bold=True, color="FFFFFF"), HEAD
            ws.column_dimensions[get_column_letter(j)].width = 18
        for i, row in enumerate(df[[f for f in fields if f in df.columns]].itertuples(index=False), start=HEADER_ROW + 1):
            values = dict(zip([f for f in fields if f in df.columns], row))
            for j, f in enumerate(fields, start=1):
                ws.cell(i, j, _value(values.get(f)))
        last = HEADER_ROW + len(df)
        sizes[name] = last
        if name == "Results & KPIs":
            ws["H2"], ws["H3"], ws["H4"] = "WORKING GUIDE", "Editable inputs: amber cells", "Protected calculations: blue-grey cells"
            for i in range(HEADER_ROW + 1, last + 1):
                ws[f"O{i}"] = f'=IF(OR(M{i}="",M{i}=0,N{i}=""),"-",N{i}/M{i})'
                ws[f"P{i}"] = (f'=IF(O{i}="-","Not recorded",IF(O{i}>=1,"Achieved",IF(O{i}>=0.75,"On track",'
                               f'"Needs attention")))')
                for col in "KLMNQRSTUV":
                    ws[f"{col}{i}"].fill = AMBER
                for col in "OP":
                    ws[f"{col}{i}"].fill = BLUE_GREY
        if name == "KPIs":
            for i in range(HEADER_ROW + 1, last + 1):
                ws[f"J{i}"] = f'=IF(I{i}>=1,"Achieved",IF(I{i}>=0.75,"On track",IF(I{i}>0,"Needs attention","Not recorded")))'
        if name == "Projects":
            for i in range(HEADER_ROW + 1, last + 1):
                ws[f"Q{i}"] = f"=O{i}+P{i}"

    p_end, r_end, k_end, a_end = sizes["Projects"], sizes["Results"], sizes["Results & KPIs"], sizes["Activities"]
    d = wb["Dashboard"]
    d["A2"], d["A3"] = "ARDE/KUBAHO MEAL Portfolio Dashboard", f"Exported from the MEAL dashboard on {dt.date.today():%Y-%m-%d}"
    d["A2"].font = Font(bold=True, size=14)
    d["A6"] = "Portfolio Summary"
    for col, label, formula in [
            ("A", "Projects", f"=COUNTA(Projects!A7:A{p_end})"), ("C", "Results", f"=COUNTA(Results!A7:A{r_end})"),
            ("E", "KPIs", f"=COUNTA('Results & KPIs'!I7:I{k_end})"), ("G", "Activities", f"=COUNTA(Activities!A7:A{a_end})")]:
        d[f"{col}8"], d[f"{col}9"] = label, formula
    for col, label, formula in [
            ("A", "Direct beneficiaries", f"=SUM(Projects!O7:O{p_end})"),
            ("C", "Indirect beneficiaries", f"=SUM(Projects!P7:P{p_end})"),
            ("E", "Average progress", f"=AVERAGE(Projects!L7:L{p_end})"),
            ("G", "KPIs achieved", f"=COUNTIF('Results & KPIs'!P7:P{k_end},\"Achieved\")")]:
        d[f"{col}11"], d[f"{col}12"] = label, formula
    d["A16"], d["B16"], d["D16"], d["E16"], d["F16"], d["G16"] = ("Project Status", "Projects", "Intervention Area",
                                                                  "Projects", "Direct Reach", "Average Progress")
    statuses = list(dict.fromkeys(t["dim_project"]["status"].dropna()))
    areas = list(dict.fromkeys(t["dim_project"]["intervention_area"].dropna()))
    for i, s in enumerate(statuses, start=17):
        d[f"A{i}"], d[f"B{i}"] = s, f"=COUNTIF(Projects!M7:M{p_end},A{i})"
    for i, a in enumerate(areas, start=17):
        d[f"D{i}"] = a
        d[f"E{i}"] = f"=COUNTIF(Projects!C7:C{p_end},D{i})"
        d[f"F{i}"] = f"=SUMIF(Projects!C7:C{p_end},D{i},Projects!O7:O{p_end})"
        d[f"G{i}"] = f"=AVERAGEIF(Projects!C7:C{p_end},D{i},Projects!L7:L{p_end})"
    if note:
        d["A40"] = note

    q = wb["Data Quality"]
    q["A2"], q["A3"] = "Data Quality Review", "Automatic completeness checks calculated from the editable Results and KPIs register"
    q["A2"].font = Font(bold=True, size=14)
    for j, h in enumerate(["Check", "Result", "Status", "Required Action"], start=1):
        c = q.cell(HEADER_ROW, j, h)
        c.font, c.fill = Font(bold=True, color="FFFFFF"), HEAD
    checks = [("Projects without intervention area", f"=COUNTBLANK(Projects!C7:C{p_end})", "Complete project classification"),
              ("Projects without verification status", f"=COUNTBLANK(Projects!N7:N{p_end})", "Record verification status"),
              ("KPIs without unit", f"=COUNTBLANK('Results & KPIs'!K7:K{k_end})", "Add the correct unit of measurement"),
              ("KPIs without target", f"=COUNTBLANK('Results & KPIs'!M7:M{k_end})", "Record KPI targets"),
              ("KPIs not recorded", f"=COUNTIF('Results & KPIs'!P7:P{k_end},\"Not recorded\")", "Record achieved values"),
              ("Results/KPIs without status", f"=COUNTBLANK('Results & KPIs'!S7:S{k_end})", "Assign KPI status")]
    for i, (label, formula, action) in enumerate(checks, start=HEADER_ROW + 1):
        q[f"A{i}"], q[f"B{i}"], q[f"D{i}"] = label, formula, action
        q[f"C{i}"] = f'=IF(B{i}=0,"Complete","Action required")'
    q.column_dimensions["A"].width = 40
    q.column_dimensions["D"].width = 40

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()
