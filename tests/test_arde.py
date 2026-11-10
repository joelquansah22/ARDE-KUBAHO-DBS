"""ARDE/KUBAHO workbook mode (team instruction 21): the reader, every new rule, unit normalisation, currency
conversion, the no-adding-across-units rule, the KPI update store, the register export, and the new pages.

All tests use a small MADE-UP workbook in ARDE's layout (tests/arde_fixture.py). The confidential workbook is never
needed; tests/test_arde_real.py checks the real file's known counts only on a computer that has it.
"""

import datetime as dt
import hashlib
import re
import sys
from pathlib import Path

import pandas as pd
import pytest

import arde_fixture
import arde_model as am
import arde_pipeline
import arde_reader
import arde_register
import arde_store

ROOT = Path(__file__).resolve().parent.parent
TODAY = dt.date(2026, 11, 10)


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr(am, "as_of", lambda: TODAY)


@pytest.fixture(scope="module")
def workbook(tmp_path_factory):
    return arde_fixture.build(tmp_path_factory.mktemp("arde") / "TEST_MEAL_workbook.xlsx")


@pytest.fixture(scope="module")
def sheets(workbook):
    return arde_reader.read_workbook(workbook)


@pytest.fixture()
def run(workbook):
    return arde_pipeline.build(workbook, workbook.name, with_updates=False)


def flagged(run, rule) -> set:
    return set(run["flags"].loc[run["flags"]["rule"] == rule, "record_key"])


# ---------------------------------------------------------------- reader
def test_reader_finds_headings_on_row_6_and_keeps_excel_row_numbers(sheets):
    assert len(sheets["Projects"]) == 4 and len(sheets["Results & KPIs"]) == 6 and len(sheets["Results"]) == 13
    first = sheets["Projects"].iloc[0]
    assert first["project_code"] == "TP-A" and first["source_row"] == 7 and first["source_sheet"] == "Projects"
    assert sheets["Results & KPIs"]["source_row"].tolist() == list(range(7, 13))
    assert "_compare" in sheets and "Dashboard" in sheets["_compare"]


def test_reader_never_changes_the_original_and_reads_uploaded_bytes(workbook):
    before = hashlib.sha256(workbook.read_bytes()).hexdigest()
    by_path = arde_reader.read_workbook(workbook)
    by_bytes = arde_reader.read_workbook(workbook.read_bytes(), "upload.xlsx")
    assert hashlib.sha256(workbook.read_bytes()).hexdigest() == before
    assert len(by_path["KPIs"]) == len(by_bytes["KPIs"]) and by_bytes["KPIs"]["source_file"].iloc[0] == "upload.xlsx"


def test_reader_recognises_the_workbook_by_its_sheet_names(tmp_path):
    from openpyxl import Workbook
    other = tmp_path / "other.xlsx"
    wb = Workbook()
    wb.active.title = "Activities"
    wb.save(other)
    assert not arde_reader.is_arde_workbook(arde_reader.sheet_names(other))
    with pytest.raises(arde_reader.WorkbookError, match="sheets are missing"):
        arde_reader.read_workbook(other)


def test_reader_stops_with_a_plain_message_when_a_heading_is_missing(tmp_path, workbook):
    from openpyxl import load_workbook
    broken = tmp_path / "broken.xlsx"
    wb = load_workbook(workbook)
    wb["KPIs"]["G6"] = "Goal"                                 # "Target" renamed
    wb.save(broken)
    with pytest.raises(arde_reader.WorkbookError, match="KPIs.*Target"):
        arde_reader.read_workbook(broken)


# ---------------------------------------------------------------- units, money, places, names
@pytest.mark.parametrize("written, normalised", [("People", "people"), (" people ", "people"),
                                                 ("Cooperative", "cooperatives"), ("Cooperatives", "cooperatives"),
                                                 ("Households", "households"), ("Women", "women"), ("km", "kilometres"),
                                                 ("Organizations", "organisations")])
def test_unit_normalisation(written, normalised):
    assert am.normalise_unit(written) == normalised


def test_unit_types():
    assert am.unit_type("people") == am.unit_type("women") == "people"
    assert am.unit_type("households") == "households"
    assert am.unit_type("cooperatives") == am.unit_type("schools") == "organisations"
    assert am.unit_type("work opportunities") == "other"


def test_unit_mapping_is_listed_in_config():
    aliases = am.fmt()["unit_aliases"]
    assert aliases["cooperative"] == "cooperatives" and aliases["organizations"] == "organisations"


def with_rates(monkeypatch, rates: dict, confirmed: bool = False):
    """Settings with these BNR rates entered (made-up numbers, for the test only)."""
    import copy
    real = am.arde_settings()
    patched = copy.deepcopy(real)
    patched["exchange_rates"] = {"source": "test", "confirmed": confirmed, **rates}
    monkeypatch.setattr(am, "arde_settings", lambda: patched)


def test_no_self_set_rates_the_bnr_table_is_blank_with_a_source_field():
    rates = am.arde_settings()["exchange_rates"]
    assert "source" in rates and rates["confirmed"] is False
    for cur in ("EUR", "USD"):
        assert set(rates[cur]) >= set(range(2013, 2027)) and all(v is None for v in rates[cur].values())
    assert am.to_rwf(1000, "EUR", dt.date(2018, 5, 1)) == (None, None, None)     # no rate: not converted
    assert am.to_rwf(1000, "RWF", dt.date(2018, 5, 1))[0] == 1000


def test_currency_conversion_uses_the_rate_for_that_year_only(monkeypatch):
    with_rates(monkeypatch, {"EUR": {2018: 1000.0, 2019: None}, "USD": {2018: 900.0}})
    assert am.to_rwf(10, "EUR", dt.date(2018, 5, 1)) == (10000.0, 1000.0, 2018)
    assert am.to_rwf(10, "EUR", dt.date(2019, 5, 1)) == (None, None, None)       # blank year: no guessing
    assert am.to_rwf(10, "EUR", dt.date(2020, 5, 1)) == (None, None, None)       # missing year: no nearest year
    assert am.to_rwf(10, "GBP", dt.date(2018, 5, 1)) == (None, None, None)
    assert am.to_rwf(None, "EUR", dt.date(2018, 5, 1)) == (None, None, None)
    assert not am.rates_confirmed()


def test_rwf_estimates_are_marked_unconfirmed_until_confirmed(monkeypatch):
    sys.path.insert(0, str(ROOT / "dashboard"))
    import ui
    with_rates(monkeypatch, {"EUR": {2018: 1000.0}})
    assert ui.rwf_estimate(1_500_000).endswith("(unconfirmed rate)")
    assert ui.rwf_estimate(None) == "no rate yet"
    with_rates(monkeypatch, {"EUR": {2018: 1000.0}}, confirmed=True)
    assert ui.rwf_estimate(1_500_000) == "≈ RWF 1.5m"


def test_data_mode_default_is_synthetic_and_arde_comes_from_a_local_file(monkeypatch, tmp_path):
    import common
    monkeypatch.delenv("ARDE_DATA_MODE", raising=False)
    monkeypatch.setattr(common, "LOCAL_SETTINGS", tmp_path / "local.yaml")
    assert common.load_settings()["data_mode"] == "synthetic"                   # the repository default
    assert common.requested_mode() == "synthetic"
    (tmp_path / "local.yaml").write_text("data_mode: arde\n", encoding="utf-8")
    assert common.requested_mode() == "arde"
    monkeypatch.setenv("ARDE_DATA_MODE", "synthetic")                           # the session wins
    assert common.requested_mode() == "synthetic"
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "config/local.yaml" in gitignore


def test_arde_mode_without_the_workbook_falls_back_to_synthetic_with_a_message(monkeypatch):
    import common
    monkeypatch.setenv("ARDE_DATA_MODE", "arde")
    monkeypatch.setattr(common, "arde_workbook_available", lambda: False)
    assert common.data_mode() == "synthetic"
    assert "not in data/real/" in common.mode_notice() and "demonstration data" in common.mode_notice()
    monkeypatch.setattr(common, "arde_workbook_available", lambda: True)
    assert common.data_mode() == "arde" and common.mode_notice() == ""


def test_money_is_totalled_per_currency_never_across(run):
    p = run["tables"]["dim_project"]
    totals = am.sum_by_currency(p, "approved_budget")
    assert totals == {"EUR": 100000, "RWF": 1000000, "USD": 5000}
    assert p.loc[p["currency"] == "RWF", "budget_rwf_estimate"].tolist() == [0, 1000000]
    assert p.loc[p["currency"] != "RWF", "budget_rwf_estimate"].isna().all()       # no BNR rates entered yet


def test_districts_are_read_from_the_location_text():
    assert am.extract_districts("Huye District, Southern Province, Rwanda") == ["Huye"]
    assert am.extract_districts("Southern Province: Nyanza District and Gisagara District") == ["Gisagara", "Nyanza"]
    assert am.extract_districts("Several villages") == []
    assert am.outside_rwanda("Karongi District, Rwanda and Goma, Democratic Republic of the Congo")


def test_roles_not_names():
    assert am.roles_only("TESTNAME Alice - Project Manager", []) == "Project Manager"
    assert am.roles_only("Executive Director", []) == "Executive Director"
    assert am.roles_only("Jean DUPONT / ARDE-KUBAHO", []) == "ARDE-KUBAHO"
    assert am.roles_only("Marie Claire Exemple (partner), with ARDE/KUBAHO", ["Marie Claire Exemple"]) == \
        "[name] (partner), with ARDE/KUBAHO"
    assert am.roles_only("ARDE/KUBAHO and partner MEAL team", []) == "ARDE/KUBAHO and partner MEAL team"
    assert am.roles_only("School WASH Club", []) == "School WASH Club"


def test_titles_keep_their_language_and_are_only_counted(run):
    p = run["tables"]["dim_project"]
    assert p.loc[p["project_code"] == "TP-A", "project_title"].iloc[0] == \
        "Projet de promotion socio-économique des coopératives"
    assert flagged(run, "title_not_english") == {"TP-A"}


# ---------------------------------------------------------------- bands
@pytest.mark.parametrize("target, achieved, status, band", [
    (100, 100, "Achieved", "Achieved"), (10, 20, "Achieved", "Achieved"), (100, 80, "On track", "On track"),
    (100, 75, "On track", "On track"), (100, 74, "In progress", "Needs attention"),
    (10, 0, "Not started", "Not recorded"), (10, 0, "In progress", "Needs attention"), (0, 0, "Achieved", "No target"),
    (None, 5, "Achieved", "No target")])
def test_band_uses_the_workbooks_thresholds(target, achieved, status, band):
    assert am.band(target, achieved, status) == band


# ---------------------------------------------------------------- every rule (instruction 21, section 3)
def test_rule_1_budget_used_impossible_is_held_back_not_guessed(run):
    p = run["tables"]["dim_project"].set_index("project_code")
    assert flagged(run, "budget_used_impossible") == {"TP-A"}
    assert pd.isna(p.loc["TP-A", "budget_used_valid"]) and p.loc["TP-A", "budget_used_pct"] == 5123.45
    assert p.loc["TP-A", "budget_used_check"] == "invalid, check"


def test_rule_2_budget_zero(run):
    assert flagged(run, "budget_zero") == {"TP-B"}


def test_rule_3_other_currencies_are_flagged_as_estimates(run):
    assert flagged(run, "currency_converted") == {"TP-A", "TP-C"}
    assert flagged(run, "activity_currency_converted") == {"A1", "A3"}


def test_rule_4_units_written_more_than_one_way_keep_their_original(run):
    k = run["tables"]["fact_kpi"].set_index("kpi_code")
    assert flagged(run, "unit_variant") == {"K2", "K3", "K5", "K6"}           # People/people, Cooperative/cooperatives
    assert (k.loc["K5", "unit_original"], k.loc["K5", "unit"]) == ("Cooperative", "cooperatives")


def test_rule_5_not_recorded_reports_ours_and_the_workbooks(run):
    assert flagged(run, "kpi_not_recorded") == {"K3"}
    figures = run["workbook_figures"].set_index("figure")
    assert figures.loc["KPIs not recorded", "workbook_value"] == 1        # the register's band: target 0 only (K4)
    assert figures.loc["KPIs not recorded", "rebuilt"] == "yes"


def test_rule_6_past_end_still_active_and_completed_at_low_progress(run):
    assert flagged(run, "past_end_still_active") == {"TP-C"}
    assert flagged(run, "completed_low_progress") == {"TP-B"}


def test_rule_7_general_objectives_with_a_placeholder_parent(run):
    assert flagged(run, "parent_placeholder") == {"TPA-GO1", "TPA-GO2", "TPB-GO1", "TPC-GO1", "TPD-GO1"}


def test_rule_8_kpis_over_150_percent_go_to_review(run):
    assert flagged(run, "kpi_over_150") == {"K2"}
    assert run["summary"].set_index("rule").loc["kpi_over_150", "level"] == "review"


def test_rule_9_activities_with_funds_of_0(run):
    assert flagged(run, "activity_funds_zero") == {"A2", "A4"}


def test_rule_10_reach_units_and_possible_double_counting(run):
    assert flagged(run, "reach_possible_double_count") == {"TP-A / Women members"}
    assert "TP-A / Households served" in flagged(run, "reach_mixed_units")
    assert flagged(run, "reach_register_differs") == {"TP-A", "TP-D"}      # 500 vs 400 people; 50 vs 0 people


def test_rule_11_and_districts(run):
    assert flagged(run, "district_not_found") == {"TP-C"}


def test_rules_never_change_a_value(sheets):
    before = {n: df.copy() for n, df in sheets.items() if isinstance(df, pd.DataFrame)}
    t = am.build_tables(sheets)
    am.run_rules(t)
    for n, df in before.items():
        pd.testing.assert_frame_equal(df, sheets[n])
    assert t["fact_kpi"]["achieved"].tolist() == [100, 20, 0, 0, 80, 50]


def test_every_rule_in_config_is_run_and_scored(run):
    assert set(run["summary"]["rule"]) == set(am.fmt()["rules"])
    s = run["summary"]
    scored = s[s["level"].isin(["held_back", "review"])]
    assert run["score"] == pytest.approx(scored["pass_rate"].mean())


# ---------------------------------------------------------------- no adding across units
def test_reach_totals_are_only_ever_per_unit(run):
    tot = am.totals_by_unit(run["tables"]["fact_reach"])
    assert set(tot.columns) == {"reach_type", "unit_type", "unit", "count"}
    direct = tot[tot["reach_type"] == "Direct"].set_index("unit")["count"]
    assert direct.to_dict() == {"people": 700, "women": 250, "households": 50, "cooperatives": 3}
    assert not tot.duplicated(["reach_type", "unit"]).any()
    assert 1003 not in tot["count"].tolist()                      # 700 + 250 + 50 + 3 would be meaningless


def test_the_headline_people_figure_counts_people_rows_only(run):
    b = run["tables"]["fact_reach"]
    headline = b[b["is_headline_people"] & (b["reach_type"] == "Direct")]["count"].sum()
    assert headline == 700                                        # women (250) are not added: they may overlap


def test_no_function_adds_reach_across_units():
    source = (ROOT / "src" / "arde_model.py").read_text(encoding="utf-8")
    assert re.search(r'groupby\(\["reach_type", "unit_type", "unit"\]', source)
    assert not re.search(r'fact_reach.*\]\["count"\]\.sum\(\)', source)


# ---------------------------------------------------------------- source of truth and the workbook's own figures
def test_source_of_truth_comparison_finds_the_stale_achievement(run):
    sot = run["source_of_truth"].set_index("field")
    assert sot.loc["kpi_code", "differ"] == 0 and sot.loc["achieved", "differ"] == 0
    assert "K3" in sot.loc["achievement_pct", "examples"]          # typed 0.9 in the KPIs sheet, 0 in the register
    results = run["source_of_truth"].query("comparison == 'Register vs Results sheet' and field == 'result_code'")
    assert results["differ"].iloc[0] == 8 and "TPA-GO2" in results["examples"].iloc[0]


def test_the_workbooks_dashboard_figures_are_rebuilt(run):
    f = run["workbook_figures"].set_index("figure")
    assert f.loc["Direct beneficiaries", "our_value"] == 850 and f.loc["Direct beneficiaries", "rebuilt"] == "yes"
    assert f.loc["KPIs achieved", "rebuilt"] == "yes" and f.loc["Projects", "rebuilt"] == "yes"


# ---------------------------------------------------------------- KPI updates
def test_kpi_update_is_checked_recorded_and_backed_up(tmp_path):
    db = tmp_path / "kpi_updates.db"
    kpi = {"kpi_code": "K6", "achieved": 50, "kpi_status": "In progress", "unit": "cooperatives"}
    with pytest.raises(arde_store.EntryError, match="negative"):
        arde_store.add_update(kpi, -1, "In progress", "", "MEAL01", db)
    with pytest.raises(arde_store.EntryError, match="Nothing has changed"):
        arde_store.add_update(kpi, 50, "In progress", "", "MEAL01", db)
    with pytest.raises(arde_store.EntryError, match="Not started"):
        arde_store.add_update(kpi, 5, "Not started", "", "MEAL01", db)
    with pytest.raises(arde_store.EntryError, match="percentage"):
        arde_store.add_update(dict(kpi, unit="%"), 120, "Achieved", "", "MEAL01", db)
    uid = arde_store.add_update(kpi, 90, "On track", "field report", "MEAL01", db)
    assert uid == "KU0001"
    history = arde_store.table("change_history", db)
    assert [(h["field"], h["old_value"], h["new_value"]) for h in history] == [
        ("achieved", "50", "90"), ("status", "In progress", "On track"), ("note", None, "field report")]
    assert arde_store.list_backups(db)
    latest = arde_store.current_updates(db)
    assert latest.iloc[0]["achieved"] == 90
    assert not len(arde_store.current_updates(db, since="2999-01-01"))     # a newer workbook wins


def test_kpi_updates_reach_the_figures_with_lineage(sheets):
    updates = pd.DataFrame([{"kpi_code": "K6", "achieved": 90.0, "kpi_status": "On track", "updated_by": "MEAL01",
                             "updated_at": "2026-11-10T10:00:00", "update_id": "KU0001"}])
    k = am.build_tables(sheets, updates)["fact_kpi"].set_index("kpi_code")
    assert k.loc["K6", "achieved"] == 90 and k.loc["K6", "band"] == "On track"
    assert k.loc["K6", "achieved_workbook"] == 50 and k.loc["K6", "updated_by"] == "MEAL01"
    assert pd.isna(k.loc["K5", "updated_by"])


def test_kpi_store_backup_and_restore(tmp_path):
    db = tmp_path / "kpi_updates.db"
    kpi = {"kpi_code": "K6", "achieved": 50, "kpi_status": "In progress", "unit": "cooperatives"}
    arde_store.add_update(kpi, 60, "In progress", "", "MEAL01", db)
    first = arde_store.list_backups(db)[0]
    arde_store.add_update(dict(kpi, achieved=60), 70, "In progress", "", "MEAL01", db)
    arde_store.restore(first, db)
    assert [u["achieved"] for u in arde_store.table("kpi_updates", db)] == [60]


# ---------------------------------------------------------------- register export
def test_register_has_arde_sheets_and_columns_and_reads_back(run, tmp_path):
    data = arde_register.build(run["tables"])
    out = tmp_path / "register.xlsx"
    out.write_bytes(data)
    again = arde_reader.read_workbook(out)
    for name in ("Projects", "Results", "KPIs", "Results & KPIs", "Activities", "Beneficiaries", "Stakeholders"):
        assert len(again[name]) == len(run["sheets"][name]), name
    from openpyxl import load_workbook
    wb = load_workbook(out)
    assert wb.sheetnames == arde_register.SHEET_ORDER
    assert [c.value for c in wb["Results & KPIs"][6]] == arde_fixture.HEADINGS["Results & KPIs"]
    assert wb["Results & KPIs"]["O7"].value.startswith("=IF(OR(M7")
    assert wb["Dashboard"]["A12"].value.startswith("=SUM(Projects!O7")
    assert again["Results & KPIs"]["achieved"].tolist() == [100, 20, 0, 0, 80, 50]


# ---------------------------------------------------------------- the model's checks
def test_duplicate_codes_stop_the_run(sheets):
    t = am.build_tables(sheets)
    t["fact_kpi"] = pd.concat([t["fact_kpi"], t["fact_kpi"].head(1)])
    assert any("share a code" in p for p in arde_pipeline.check(t))


def test_every_fact_row_has_lineage(run):
    for name, df in run["tables"].items():
        if name != "dim_project_district":
            assert df["source_row"].notna().all() and df["source_sheet"].notna().all(), name


# ---------------------------------------------------------------- the pages (consistency), on the made-up workbook
@pytest.fixture(scope="module")
def arde_app(workbook, tmp_path_factory):
    """The dashboard in arde mode reading a warehouse built from the made-up workbook."""
    from model import save_warehouse
    from streamlit.testing.v1 import AppTest
    sys.path.insert(0, str(ROOT / "dashboard"))
    import ui
    am_today = am.as_of
    am.as_of = lambda: TODAY
    built = arde_pipeline.build(workbook, workbook.name, with_updates=False)
    db = tmp_path_factory.mktemp("arde_wh") / "arde_test.duckdb"
    save_warehouse(arde_pipeline.warehouse_tables(built, workbook, None), db)
    saved = (ui.ARDE, ui.MODE, ui.db_path)
    ui.ARDE, ui.MODE, ui.db_path = True, "arde", (lambda: db)
    import app_store                                    # donor entries: an empty file of the test's own
    entries = tmp_path_factory.mktemp("arde_entries") / "entries.db"
    saved_store = app_store.db_path
    app_store.db_path = lambda: entries

    def page(key: str):
        at = AppTest.from_file(str(ROOT / "dashboard" / "app.py"), default_timeout=180)
        at.run()
        if key != "start":
            at.switch_page(ui.menu_page(key)["file"])
            at.run()
        assert not at.exception, [e.value for e in at.exception]
        return at

    yield page, built
    ui.ARDE, ui.MODE, ui.db_path = saved
    app_store.db_path = saved_store
    am.as_of = am_today


def text_of(at) -> str:
    parts = [m.value for m in at.markdown] + [c.value for c in at.caption] + [w.value for w in at.warning]
    parts += [df.value.to_csv() for df in at.dataframe]
    return "\n".join(str(p) for p in parts)


def tile(at, label: str) -> str:
    html = next(m.value for m in at.markdown if f"<div class='tile-label'>{label}</div>" in m.value)
    return re.search(r"<div class='tile-value'>(.*?)</div>", html).group(1)


ARDE_PAGES = ["start", "home", "portfolio", "results_kpis", "reach", "geography", "data_quality", "kpi_update",
              "upload_excel", "records", "donor_pipeline", "donor_entry", "partners_funding"]


def test_every_arde_page_opens_shows_the_confidential_banner_and_no_staff_name(arde_app):
    page, _ = arde_app
    for key in ARDE_PAGES:
        at = page(key)
        text = text_of(at)
        assert "ARDE/KUBAHO data: confidential, for project use only" in text, key
        assert "TESTNAME" not in text, key                        # roles, not names


def test_arde_menu_keeps_the_adapted_pages_and_hides_only_monthly_data_entry():
    from common import load_yaml
    titles = [p["title"] for s in load_yaml("page_help.yaml")["menu_arde"] for p in s["pages"]]
    for kept in ("Executive summary", "Records", "Donor entry", "Donor pipeline", "Portfolio", "Results and KPIs",
                 "Reach", "Partners and funding", "KPI update", "Geography", "Data quality", "Upload Excel"):
        assert kept in titles
    for hidden in ("Programme overview", "Indicators", "Data entry"):
        assert hidden not in titles


def test_home_figures_match_the_tables(arde_app):
    page, built = arde_app
    at = page("start")
    k = built["tables"]["fact_kpi"]
    assert tile(at, "KPIs achieved") == f"{int((k['band'] == 'Achieved').sum())} of {len(k)}" == "2 of 6"
    assert tile(at, "Direct reach, people") == "700"                 # people rows only; never + women/households
    assert tile(at, "Data-quality score") == f"{built['score']:.1f}%"
    assert tile(at, "Projects") == "4"


def test_portfolio_shows_invalid_budget_used_and_native_currencies(arde_app):
    at = arde_app[0]("portfolio")
    text = text_of(at)
    assert "invalid, check (5,123 typed)" in text
    assert "EUR 100,000" in tile(at, "Approved budgets in EUR") or tile(at, "Approved budgets in EUR") == "EUR 100,000"
    assert tile(at, "Approved budgets in USD") == "USD 5,000"                     # side by side, per currency
    assert not any("All budgets, RWF estimate" in m.value for m in at.markdown)  # no rates: no RWF total
    assert "No RWF total is given until BNR exchange rates are entered" in text


def test_reach_page_never_shows_a_total_across_units(arde_app):
    at = arde_app[0]("reach")
    for df in at.dataframe:
        frame = df.value
        if "Total" in frame.columns:
            assert "Unit" in frame.columns and frame["Unit"].notna().all()
            assert 1003 not in frame["Total"].tolist() and 1000 not in frame["Total"].tolist()


def test_data_quality_page_counts_match_the_rule_table(arde_app):
    page, built = arde_app
    at = page("data_quality")
    f = built["flags"]
    assert tile(at, "Held back") == f"{int((f['level'] == 'held_back').sum()):,}"
    assert tile(at, "For review") == f"{int((f['level'] == 'review').sum()):,}"


def test_results_page_band_counts_match(arde_app):
    page, built = arde_app
    at = page("results_kpis")
    k = built["tables"]["fact_kpi"]
    assert tile(at, "✔ Achieved") == str(int((k["band"] == "Achieved").sum()))
    assert tile(at, "… Not recorded") == "1"


def test_donor_pipeline_empty_invites_the_first_opportunity_then_shows_it(arde_app):
    import app_store
    page, _ = arde_app
    at = page("donor_pipeline")
    assert "No funding opportunities recorded yet. Add your first one" in text_of(at)
    summary = page("home")
    assert "no funding opportunities recorded yet" in text_of(summary)
    donor = app_store.add_donor({"donor_type": "foundation", "donor_name": "Test Foundation"}, "MEAL01")
    app_store.add_opportunity({"donor_id": donor, "title": "Water grant", "thematic_fit": "WASH", "stage": "Qualified",
                               "deadline": dt.date(2030, 1, 31), "requested_amount_rwf": 10_000_000,
                               "probability": 0.5, "owner": "MEAL01"}, "MEAL01")
    at = page("donor_pipeline")
    assert tile(at, "Open opportunities") == "1" and tile(at, "Weighted open pipeline") == "RWF 5.0m"
    assert "Water grant" in text_of(at)
    assert "1 opportunities, weighted RWF 5.0m" in text_of(page("home"))


def test_geography_shows_cross_border_projects_separately_not_on_the_map(arde_app):
    at = arde_app[0]("geography")
    frames = {tuple(df.value.columns): df.value for df in at.dataframe}
    cross = next(v for k, v in frames.items() if "Label" in k)
    assert cross["Project"].tolist() == ["TP-B"] and "Goma" in cross["Label"].iloc[0]
    mapped = next(v for k, v in frames.items() if "Districts in project" in k)
    assert "TP-B" not in mapped["Project"].tolist() and set(mapped["Project"]) == {"TP-A", "TP-D"}


def test_records_page_offers_an_excel_export(arde_app):
    at = arde_app[0]("records")
    assert "Export this view to Excel" in str([e.proto for e in at.main])
