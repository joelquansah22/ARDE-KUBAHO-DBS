"""Read ARDE/KUBAHO's MEAL workbook (data_mode: arde) into tables, with the sheet and row of every value.

WHAT THIS FILE DOES
-------------------
1. Copies the workbook to a temporary folder and reads the COPY (team rule: never touch the original).
2. Opens it with openpyxl in read-only mode with data_only=True. The workbook cannot be opened in normal mode: a
   doughnut chart on the Dashboard sheet has an invalid hole size and openpyxl refuses it. read_only mode does not
   load charts, and data_only gives the values Excel last calculated instead of the formulas.
3. Finds each sheet's heading row by its FIRST column name (config/arde_format.yaml: header_starts_with), because
   every sheet has a title block above the headings.
4. Renames the headings to database names (config/arde_format.yaml: columns) and adds lineage to every row:
   source_file, source_sheet and source_row (the row number you see in Excel).

Nothing is cleaned or corrected here: the values are exactly as in the workbook.

HOW TO RUN (to look at a workbook)
    python src/arde_reader.py data/real/ARDE-KUBAHO_MEAL_Important_Data_Editable.xlsx
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import openpyxl
import pandas as pd

from common import load_yaml


class WorkbookError(Exception):
    """The file is not an ARDE/KUBAHO MEAL workbook, or a sheet's layout has changed. The message is for staff."""


def layout() -> dict:
    return load_yaml("arde_format.yaml")


def _open(source) -> tuple[openpyxl.Workbook, Path | None]:
    """Open a COPY of the workbook (a path or the bytes of an uploaded file). Returns the workbook and the temporary
    folder to delete afterwards."""
    tmp = Path(tempfile.mkdtemp(prefix="arde_copy_"))
    copy = tmp / "copy.xlsx"
    if isinstance(source, (bytes, bytearray)):
        copy.write_bytes(source)
    else:
        shutil.copy2(source, copy)               # the original is only ever read by this copy command
    try:
        wb = openpyxl.load_workbook(copy, read_only=True, data_only=True)
    except Exception as err:  # noqa: BLE001 - any failure here means "not a readable workbook"
        shutil.rmtree(tmp, ignore_errors=True)
        raise WorkbookError(f"The file could not be opened as an Excel workbook ({err}).") from err
    return wb, tmp


def sheet_names(source) -> list[str]:
    wb, tmp = _open(source)
    try:
        return list(wb.sheetnames)
    finally:
        wb.close()
        shutil.rmtree(tmp, ignore_errors=True)


def is_arde_workbook(names: list[str]) -> bool:
    """Recognised by its sheet names (all the required sheets present)."""
    return set(layout()["required_sheets"]) <= set(names)


def _read_sheet(ws, name: str, spec: dict, source_file: str) -> pd.DataFrame:
    rows = list(ws.iter_rows(values_only=True))
    first = spec["header_starts_with"]
    header_at = next((i for i, r in enumerate(rows) if r and isinstance(r[0], str) and r[0].strip() == first), None)
    if header_at is None:
        raise WorkbookError(f"Sheet '{name}': no heading row starting with '{first}' was found in column A.")
    header = [str(c).strip() if c is not None else None for c in rows[header_at]]
    missing = [h for h in spec["columns"] if h not in header]
    if missing:
        raise WorkbookError(f"Sheet '{name}': these column headings are missing: {', '.join(missing)}. "
                            "Check the headings, or update config/arde_format.yaml.")
    keep = [i for i, h in enumerate(header) if h]
    records = []
    for offset, row in enumerate(rows[header_at + 1:], start=1):
        values = [row[i] if i < len(row) else None for i in keep]
        if all(v is None or (isinstance(v, str) and not v.strip()) for v in values):
            continue                                      # empty rows (the sheets end with formatted blank rows)
        records.append(values + [header_at + 1 + offset])  # the Excel row number
    names = [spec["columns"].get(header[i], header[i]) for i in keep]
    df = pd.DataFrame(records, columns=names + ["source_row"])
    df.insert(0, "source_sheet", name)
    df.insert(0, "source_file", source_file)
    for col in df.columns:                                 # tidy text: strip spaces at either end only
        if df[col].dtype == object:
            df[col] = df[col].map(lambda v: v.strip() if isinstance(v, str) else v)
    return df


def _compare_sheet(ws) -> list[list]:
    """A calculated sheet (Dashboard, Data Quality) as a list of non-empty rows, each with its Excel row number."""
    out = []
    for i, row in enumerate(ws.iter_rows(values_only=True), start=1):
        cells = [(j, v) for j, v in enumerate(row) if v is not None]
        if cells:
            out.append([i, cells])
    return out


def read_workbook(source, source_file: str | None = None) -> dict:
    """Read every sheet listed in config/arde_format.yaml. Returns {sheet name: DataFrame}, plus "_compare" with the
    calculated sheets as raw cells, and "_sheet_rows" with the number of rows read from each sheet.
    source: a path, or the bytes of an uploaded file (then give source_file, the name to record as lineage)."""
    spec = layout()
    if source_file is None:
        source_file = Path(source).name
    wb, tmp = _open(source)
    try:
        if not is_arde_workbook(wb.sheetnames):
            missing = sorted(set(spec["required_sheets"]) - set(wb.sheetnames))
            raise WorkbookError("This is not an ARDE/KUBAHO MEAL workbook: these sheets are missing: "
                                + ", ".join(missing) + ".")
        out = {name: _read_sheet(wb[name], name, s, source_file) for name, s in spec["sheets"].items()}
        out["_compare"] = {name: _compare_sheet(wb[name]) for name in spec["compare_only_sheets"]
                           if name in wb.sheetnames}
        out["_sheet_list"] = list(wb.sheetnames)
        return out
    finally:
        wb.close()
        shutil.rmtree(tmp, ignore_errors=True)


def compare_cells(sheet_cells: list[list]) -> dict:
    """Label -> value pairs from a calculated sheet: a label cell with its value in the cell BELOW (Dashboard
    cards) or to the RIGHT (Data Quality and the Dashboard's small tables). Used to compare their figures."""
    grid = {(r, c): v for r, cells in sheet_cells for c, v in cells}
    pairs = {}
    for (r, c), v in grid.items():
        if not isinstance(v, str):
            continue
        right, below = grid.get((r, c + 1)), grid.get((r + 1, c))
        if isinstance(right, (int, float)):
            pairs.setdefault(v, right)
        elif isinstance(below, (int, float)):
            pairs.setdefault(v, below)
    return pairs


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 1
    data = read_workbook(Path(argv[0]))
    for name, df in data.items():
        if isinstance(df, pd.DataFrame):
            print(f"{name}: {len(df)} rows, columns: {', '.join(df.columns)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

