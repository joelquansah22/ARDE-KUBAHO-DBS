from openpyxl import load_workbook

import build_templates
from common import load_yaml, resolve_path


def test_templates_have_headers_and_dropdowns():
    build_templates.main()
    cfg = load_yaml("templates.yaml")["templates"]
    for file_name, spec in cfg.items():
        wb = load_workbook(resolve_path("templates") / file_name)
        assert wb["Lists"].sheet_state == "hidden"
        for sheet, columns in spec["sheets"].items():
            ws = wb[sheet]
            assert [c.value for c in ws[1]] == [c["header"] for c in columns]
            if any("list" in c for c in columns):
                assert ws.data_validations.dataValidation, f"{file_name}/{sheet} has no dropdowns"


def test_sex_dropdown_has_no_numeric_codes():
    values = build_templates.resolve_list(load_yaml("templates.yaml")["lists"]["sex"])
    assert values == ["Female", "Male"]


def test_templates_are_not_rebuilt_when_nothing_changed():
    build_templates.main()
    assert build_templates.main() is False


def test_donor_template_is_finished():
    build_templates.main()
    wb = load_workbook(resolve_path("templates") / "donor_opportunity_template.xlsx")
    ws = wb["Opportunities"]
    formulas = [dv.formula1 for dv in ws.data_validations.dataValidation]
    assert any("Donors" in f for f in formulas if f)                 # donor is picked from the Donors sheet
    assert ws["I2"].number_format == "0%"                             # probability as a percentage
    assert len(ws.conditional_formatting) == 3                       # overdue, deadline soon, awarded without amount
    intro = " ".join(str(c.value) for row in wb["Instructions"].iter_rows() for c in row if c.value)
    assert "Phase 1 draft" not in intro and "Individual donor #001" in intro
    assert "Example rows" in intro


def test_example_donor_rows_are_not_read_as_data():
    """The examples are on the Instructions sheet, which the pipeline does not read for the donor file."""
    files = load_yaml("source_mappings.yaml")["files"]
    donor = next(f for f in files if f["pattern"] == "*donor_opportunity*.xlsx")
    assert "Instructions" not in donor["sheets"]
    assert set(donor["sheets"]) == {"Donors", "Opportunities"}
