import datetime as dt

from common import district_to_province, fiscal_year_label, load_admin, to_excel_serial


def test_rwanda_has_5_provinces_and_30_districts():
    provinces = load_admin()["provinces"]
    assert set(provinces) == {"Kigali City", "Northern", "Southern", "Eastern", "Western"}
    districts = district_to_province()
    assert len(districts) == 30
    assert districts["Nyagatare"] == "Eastern"
    assert districts["Huye"] == "Southern"


def test_fiscal_year_runs_july_to_june():
    assert fiscal_year_label(dt.date(2023, 7, 1)) == "FY2023/24"
    assert fiscal_year_label(dt.date(2024, 6, 30)) == "FY2023/24"
    assert fiscal_year_label(dt.date(2024, 7, 1)) == "FY2024/25"


def test_excel_serial_matches_excel():
    # In Excel, =DATEVALUE("12/03/2024") with dd/mm/yyyy gives 45363.
    assert to_excel_serial(dt.date(2024, 3, 12)) == 45363
