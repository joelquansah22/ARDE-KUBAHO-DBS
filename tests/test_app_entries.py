"""Scope extension: donor tracking entered on the dashboard (data/app/entries.db)."""

import datetime as dt
import sqlite3
from pathlib import Path

import pandas as pd
import pytest

import app_store
from app_store import EntryError

TODAY = app_store.today()
SOON = TODAY + dt.timedelta(days=40)


@pytest.fixture
def db(tmp_path):
    return tmp_path / "entries.db"


def opportunity(**kw):
    base = dict(title="Safe water for schools", donor_key="DON-abc", thematic_fit="WASH", stage="Concept note",
                deadline=SOON, owner="PM01", requested_amount_rwf=150_000_000, probability=0.3)
    return {**base, **kw}


# ---------------------------------------------------------------- validation on entry
@pytest.mark.parametrize("change, message", [
    (dict(title=""), "Title is required"),
    (dict(donor_key=None), "Donor is required"),
    (dict(probability=1.2), "between 0% and 100%"),
    (dict(probability=-0.1), "between 0% and 100%"),
    (dict(deadline=TODAY), "must be in the future"),
    (dict(deadline=None), "Deadline is required"),
    (dict(requested_amount_rwf=-5), "cannot be negative"),
    (dict(stage="Awarded"), "needs the amount awarded"),
    (dict(next_action="Send concept note"), "Give the date"),
    (dict(stage="Maybe"), "Stage must be one of"),
])
def test_opportunity_rules_are_checked_on_entry(db, change, message):
    with pytest.raises(EntryError, match=message):
        app_store.add_opportunity(opportunity(**change), "PM01", db)


def test_staff_must_be_chosen(db):
    with pytest.raises(EntryError, match="Choose your name"):
        app_store.add_opportunity(opportunity(), "Somebody", db)


def test_a_valid_opportunity_is_saved_with_its_author(db):
    opp_id = app_store.add_opportunity(opportunity(), "PM01", db)
    assert opp_id == "APP-O001"
    row = app_store.table("opportunities", db)[0]
    assert (row["created_by"], row["probability"], row["deadline"]) == ("PM01", 0.3, SOON.isoformat())
    assert app_store.table("change_history", db)[0]["action"] == "added"


# ---------------------------------------------------------------- individual donors and personal data
def test_individual_donors_are_never_named(db):
    problems = app_store.validate_donor({"donor_type": "individual", "donor_name": "Jane Doe"})
    assert any("Do not enter an individual donor's name" in p for p in problems)
    app_store.add_donor({"donor_type": "individual", "donor_name": "Jane Doe"}, "ED01", db)   # the name is dropped
    assert app_store.table("donors", db)[0]["donor_name"] is None
    donor_id = app_store.table("donors", db)[0]["donor_id"]
    # Even writing straight to the database cannot store a name for an individual.
    with sqlite3.connect(db) as con, pytest.raises(sqlite3.IntegrityError):
        con.execute("INSERT INTO donors (donor_id, donor_name, donor_type, created_by, created_at) "
                    "VALUES ('X', 'Jane Doe', 'individual', 'ED01', 'now')")
    assert donor_id == "APP-D001"


def test_an_organisation_needs_its_name(db):
    with pytest.raises(EntryError, match="Donor name is required"):
        app_store.add_donor({"donor_type": "foundation", "donor_name": " "}, "ED01", db)


def test_the_database_holds_no_personal_data_columns(db):
    from model import PERSONAL_COLUMNS
    app_store.add_donor({"donor_type": "foundation", "donor_name": "Example Foundation"}, "ED01", db)
    with sqlite3.connect(db) as con:
        columns = {c[1] for t in ("donors", "opportunities", "change_history")
                   for c in con.execute(f"PRAGMA table_info({t})")}
    banned = (PERSONAL_COLUMNS - {"name"}) | {"email", "phone", "contact_person", "national_id"}
    assert not columns & banned


# ---------------------------------------------------------------- updates and history
def test_updates_record_who_changed_what_and_when(db):
    opp_id = app_store.add_opportunity(opportunity(), "PM01", db)
    changed = app_store.update_opportunity(opp_id, dict(stage="Proposal submitted", probability=0.5), "MEAL01", db)
    assert set(changed) == {"stage", "probability"}
    history = pd.DataFrame(app_store.table("change_history", db))
    edits = history[history["action"] == "changed"].set_index("field")
    assert edits.loc["stage", "old_value"] == "Concept note" and edits.loc["stage", "new_value"] == "Proposal submitted"
    assert (edits["changed_by"] == "MEAL01").all() and edits["changed_at"].notna().all()
    assert app_store.update_opportunity(opp_id, dict(stage="Proposal submitted"), "MEAL01", db) == []   # no change


def test_updates_are_validated_too(db):
    opp_id = app_store.add_opportunity(opportunity(), "PM01", db)
    with pytest.raises(EntryError, match="needs the amount awarded"):
        app_store.update_opportunity(opp_id, dict(stage="Awarded"), "PM01", db)
    with pytest.raises(EntryError, match="cannot be changed here"):
        app_store.update_opportunity(opp_id, dict(title="New title"), "PM01", db)


def test_marking_a_next_action_done_keeps_it_in_the_history(db):
    opp_id = app_store.add_opportunity(opportunity(next_action="Send concept note", next_action_date=SOON), "PM01", db)
    app_store.mark_next_action_done(opp_id, "PM01", db)
    row = app_store.table("opportunities", db)[0]
    assert row["next_action"] is None and row["next_action_date"] is None
    done = [h for h in app_store.table("change_history", db) if h["action"] == "next action done"]
    assert "Send concept note" in done[0]["old_value"]
    with pytest.raises(EntryError, match="no next action"):
        app_store.mark_next_action_done(opp_id, "PM01", db)


# ---------------------------------------------------------------- the pipeline reads both sources
def test_pipeline_reads_entries_next_to_the_excel_tracker(synthetic, tmp_path):
    import ingest
    db = tmp_path / "entries.db"
    individual = app_store.add_donor({"donor_type": "individual"}, "ED01", db)
    foundation = app_store.add_donor({"donor_type": "foundation", "donor_name": "Example Foundation"}, "ED01", db)
    app_store.add_opportunity(opportunity(donor_key=None, donor_id=foundation), "PM01", db)
    without = ingest.run(synthetic["raw"], tmp_path / "staging_without")["tables"]
    both = ingest.run(synthetic["raw"], tmp_path / "staging_with", app_entries=db)["tables"]
    assert len(both["opportunity"]) == len(without["opportunity"]) + 1
    app_opp = both["opportunity"][both["opportunity"]["source_file"] == "entries.db"].iloc[0]
    assert app_opp["donor_key"] == ingest.pseudonym(ingest.load_salt(), "DON", foundation)
    # Excel individuals keep their numbers; the one added on the dashboard comes after them.
    excel = without["donor"].set_index("donor_key")["donor_name"]
    after = both["donor"].set_index("donor_key")["donor_name"]
    assert (after.loc[excel.index] == excel).all()
    app_label = both["donor"].loc[both["donor"]["donor_id"] == individual, "donor_name"].iloc[0]
    assert app_label.startswith("Individual donor #")
    assert app_label not in set(excel)


def test_entries_are_never_read_into_a_scoring_run(synthetic, tmp_path, monkeypatch):
    import ingest
    db = tmp_path / "entries.db"
    app_store.add_donor({"donor_type": "foundation", "donor_name": "Example Foundation"}, "ED01", db)
    monkeypatch.setattr(app_store, "db_path", lambda: db)
    tables = ingest.run(synthetic["raw"], tmp_path / "staging")["tables"]      # a test-set run: raw_dir given
    assert "entries.db" not in set(tables["donor"]["source_file"])


# ---------------------------------------------------------------- the page
def test_donor_entry_page_runs(tmp_path, monkeypatch):
    from common import resolve_path
    if not resolve_path("warehouse").exists():
        pytest.skip("Build the warehouse first")
    from streamlit.testing.v1 import AppTest
    db = tmp_path / "entries.db"
    app_store.add_opportunity(opportunity(next_action="Call donor", next_action_date=SOON), "PM01", db)
    monkeypatch.setattr(app_store, "db_path", lambda: db)
    at = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "dashboard" / "app.py"), default_timeout=120)
    at.switch_page("pages/6_Donor_Entry.py")
    at.session_state["entry_staff"] = "PM01"
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("APP-O001" in m.value for m in at.markdown)            # listed under next actions
