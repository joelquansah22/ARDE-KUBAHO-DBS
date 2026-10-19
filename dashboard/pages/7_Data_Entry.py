"""Data entry: activity records and monthly indicator reports, typed in on the dashboard (saved to data/app/entries.db).

Each entry is checked with the same rules the cleaner uses for Excel rows (src/entry_checks.py): an entry that would
be held back is not saved, and the page says why in plain words; one that would go to the review queue is saved, with
a note. Every change is recorded with the staff code of the person who made it, and a dated backup is kept after each
save. The pipeline reads these entries next to the Excel files, so they appear on the other pages after the figures
are updated (button at the bottom of this page).

Records that came from Excel files are read-only here: they are corrected in the Excel file, which is then uploaded
again (Upload Excel page). That way each record has one place where it is kept.
"""

import datetime as dt

import pandas as pd
import streamlit as st

import ui                 # first: it makes src/ importable
import app_store          # noqa: E402

f = ui.filters(sex_applies=False)
ui.page_header("Data entry", "data_entry")
ui.how_to_read("data_entry")
today = app_store.today()
staging = ui.resolve_path("staging")

who, labels, ready = ui.staff_picker("entering or changing anything")
st.caption("**Records from Excel files are read-only here.** To correct one, change the Excel file and upload it again "
           "on the **Upload Excel** page (choose to replace the earlier file). Records entered on this page can be "
           "changed on the 'Change an entry' tab.")


@st.cache_data(show_spinner=False)
def _lists(stamp: float) -> dict:
    """The programme master's lists (projects, activities, places, officers), as prepared by the pipeline."""
    read = lambda n: pd.read_parquet(staging / f"{n}.parquet")
    return dict(projects=read("ref_project"), activities=read("ref_activity"), places=read("ref_location"),
                officers=read("ref_officer"))


@st.cache_data(show_spinner=False, max_entries=2)
def _backup_workbook(db_stamp: float) -> bytes:
    return app_store.export_workbook()


def _stamp(path) -> float:
    return path.stat().st_mtime if path.exists() else 0.0


L = _lists(_stamp(staging / "ref_location.parquet"))
projects = L["projects"].set_index("project_id")
reported = [c for c, i in ui.catalogue().items()
            if i.get("availability") == "available" and "reported" in (i.get("calculation") or {})]
STATUSES = ui.SETTINGS["activity_status_values"]


def _split(text) -> list[str]:
    return [x.strip() for x in str(text or "").split(",") if x.strip()]


def _index(options: list, value, default: int = 0) -> int:
    return options.index(value) if value in options else default


def _date(v):
    return dt.date.fromisoformat(v[:10]) if isinstance(v, str) and v else (v or None)


def _num(v, kind=int):
    """A stored number as the form needs it (whole numbers for people, decimals for money and values), or empty."""
    return None if v is None or (isinstance(v, float) and pd.isna(v)) else kind(v)


def project_label(p: str) -> str:
    return f"{p} {projects.loc[p, 'name']}"


def activity_fields(key: str, cur: dict | None = None) -> dict:
    """The activity form. The lists depend on each other (project -> activity; district -> sector -> cell ->
    village), so they are ordinary widgets that update as soon as a choice is made."""
    cur = cur or {}
    c1, c2 = st.columns(2)
    plist = list(projects.index)
    project = c1.selectbox("Project *", plist, index=_index(plist, cur.get("project_id")), format_func=project_label,
                           key=f"{key}_project")
    acts = L["activities"][L["activities"]["project_id"] == project]
    alist = list(acts["activity_id"])
    names = dict(zip(acts["activity_id"], acts["activity_name"]))
    activity = c2.selectbox("Activity *", alist, index=_index(alist, cur.get("activity_id")),
                            format_func=lambda a: f"{a} {names[a]}", key=f"{key}_activity_{project}")
    places = L["places"]
    dlist = _split(projects.loc[project, "districts"])
    c1, c2, c3, c4 = st.columns(4)
    district = c1.selectbox("District *", dlist, index=_index(dlist, cur.get("district")), key=f"{key}_district_{project}",
                            help="Only the districts where this project works (programme master).")
    here = places[places["district"] == district]
    slist = sorted(here["sector"].unique())
    sector = c2.selectbox("Sector *", slist, index=_index(slist, cur.get("sector")), key=f"{key}_sector_{district}")
    here = here[here["sector"] == sector]
    clist = sorted(here["cell"].unique())
    cell = c3.selectbox("Cell *", clist, index=_index(clist, cur.get("cell")), key=f"{key}_cell_{district}_{sector}")
    vlist = sorted(here[here["cell"] == cell]["village"].unique())
    village = c4.selectbox("Village *", vlist, index=_index(vlist, cur.get("village")),
                           key=f"{key}_village_{district}_{sector}_{cell}")
    start, end = _date(projects.loc[project, "start_date"]), _date(projects.loc[project, "end_date"])
    c1, c2, c3 = st.columns(3)
    status = c1.selectbox("Status *", STATUSES, index=_index(STATUSES, cur.get("status"), _index(STATUSES, "completed")),
                          format_func=str.capitalize, key=f"{key}_status")
    date = c2.date_input("Date done", value=_date(cur.get("date")), max_value=today, format="DD/MM/YYYY",
                         key=f"{key}_date", help=f"Within the project ({start:%d/%m/%Y} to {end:%d/%m/%Y}), not in "
                                                  "the future. Leave empty if not done yet.")
    planned = c3.date_input("Planned date", value=_date(cur.get("planned_date")), format="DD/MM/YYYY",
                            key=f"{key}_planned")
    c1, c2, c3, c4 = st.columns(4)
    female = c1.number_input("Women", min_value=0, step=1, value=_num(cur.get("participants_female")), key=f"{key}_f")
    male = c2.number_input("Men", min_value=0, step=1, value=_num(cur.get("participants_male")), key=f"{key}_m")
    total = c3.number_input("Total participants", min_value=0, step=1, value=_num(cur.get("participants_total")),
                            key=f"{key}_t", help="Must equal women + men.")
    cost = c4.number_input("Cost (RWF)", min_value=0.0, step=10_000.0, format="%.0f", value=_num(cur.get("cost_rwf"), float),
                           key=f"{key}_cost")
    olist = list(L["officers"]["officer_code"])
    officer = st.selectbox("Field officer *", olist, index=_index(olist, cur.get("officer"), _index(olist, who)),
                           key=f"{key}_officer")
    return dict(project_id=project, activity_id=activity, district=district, sector=sector, cell=cell, village=village,
                status=status, date=date, planned_date=planned, participants_female=female, participants_male=male,
                participants_total=total, cost_rwf=cost, officer=officer)


def months(project: str) -> list[dt.date]:
    start = _date(projects.loc[project, "start_date"]).replace(day=1)
    last = min(_date(projects.loc[project, "end_date"]), today).replace(day=1)
    out = list(pd.date_range(start, last, freq="MS").date)
    return out[::-1]                                  # the most recent month first


def report_fields(key: str, cur: dict | None = None) -> dict | None:
    """The monthly report form; None if the chosen project has no indicator reported monthly."""
    cur = cur or {}
    c1, c2 = st.columns(2)
    plist = list(projects.index)
    project = c1.selectbox("Project *", plist, index=_index(plist, cur.get("project_id")), format_func=project_label,
                           key=f"{key}_project")
    dlist = _split(projects.loc[project, "districts"])
    district = c2.selectbox("District *", dlist, index=_index(dlist, cur.get("district")), key=f"{key}_district_{project}")
    ilist = [c for c in _split(projects.loc[project, "indicators"]) if c in reported]
    if not ilist:
        st.info(f"{project} has no indicator reported monthly: its indicators are worked out from the records, or wait "
                "for a data source (Indicators page). Nothing to enter here.")
        return None
    missing = ui.query("SELECT period FROM report_completeness WHERE project_id = ? AND district = ? AND NOT submitted "
                       "ORDER BY period DESC", project, district)
    if len(missing) and not cur:
        st.caption("Monthly reports still missing here: "
                   + ", ".join(f"{pd.Timestamp(p):%b %Y}" for p in missing["period"]) + ".")
    mlist = months(project)
    period = c1.selectbox("Month *", mlist, index=_index(mlist, _date(cur.get("period"))),
                          format_func=lambda d: f"{d:%B %Y}", key=f"{key}_period_{project}")
    code = c2.selectbox("Indicator *", ilist, index=_index(ilist, cur.get("indicator_code")),
                        format_func=lambda c: f"{c} {ui.catalogue()[c]['name']}", key=f"{key}_indicator_{project}")
    sex = None
    if ui.catalogue()[code].get("disaggregation") == "sex":
        sex = c1.radio("Sex *", ["female", "male"], index=_index(["female", "male"], cur.get("sex")), horizontal=True,
                       format_func=str.capitalize, key=f"{key}_sex_{code}",
                       help="This indicator is reported separately for women and men: one entry each.")
    unit = ui.catalogue()[code].get("unit", "")
    target = c1.number_input(f"Monthly target ({unit})", min_value=0.0, step=1.0, value=_num(cur.get("target_value"), float),
                             key=f"{key}_target", help="Leave empty if there is no target for this month.")
    actual = c2.number_input(f"Achieved ({unit}) *", min_value=0.0, step=1.0, value=_num(cur.get("actual_value"), float),
                             key=f"{key}_actual")
    return dict(project_id=project, district=district, period=period, indicator_code=code, sex=sex,
                target_value=target, actual_value=actual)


def save(action, *args) -> None:
    """Save, then show the result at the top of the page; problems are shown in plain words and nothing is saved."""
    try:
        record_id, warnings = action(*args)
    except app_store.EntryError as e:
        st.error("Not saved. " + str(e))
        return
    st.session_state["data_entry_message"] = (record_id, warnings)
    st.rerun()


if "data_entry_message" in st.session_state:
    record_id, warnings = st.session_state.pop("data_entry_message")
    st.success(f"Saved: {record_id}. It appears on the other pages after the figures are updated (bottom of this page).")
    for w in warnings:
        st.warning(w)

tabs = st.tabs(["New activity record", "New monthly indicator report", "Change an entry", "Change history", "Backup"])
app_acts = pd.DataFrame(app_store.table("activities"))
app_reps = pd.DataFrame(app_store.table("indicator_reports"))

with tabs[0]:
    rec = activity_fields("new_act")
    if st.button("Save activity record", type="primary", disabled=not ready, key="save_activity"):
        save(app_store.add_activity, rec, who)
    st.caption("Fields marked * are required. Women and men are needed once the activity is completed or delayed, and women + men must "
               "equal the total. The date must fall within the project and not be in the future.")

with tabs[1]:
    rec = report_fields("new_rep")
    if st.button("Save monthly report", type="primary", disabled=not (ready and rec), key="save_report"):
        save(app_store.add_indicator_report, rec, who)
    st.caption("Fields marked * are required. A report already in an Excel file, or already entered here, is refused (it would be "
               "counted twice): correct the Excel file, or change the earlier entry instead.")

with tabs[2]:
    kind = st.radio("Which kind of entry?", ["Activity record", "Monthly indicator report"], horizontal=True,
                    key="edit_kind")
    rows = app_acts if kind == "Activity record" else app_reps
    if not len(rows):
        st.info("Nothing of this kind has been entered on this page yet. Records from Excel files are corrected in the "
                "Excel file and uploaded again.")
    else:
        rows = rows.set_index("record_id")
        describe = ((lambda r: f"{r}: {rows.loc[r, 'activity_id']} {rows.loc[r, 'district']} / {rows.loc[r, 'village']}, "
                               f"{rows.loc[r, 'date'] or 'not done yet'}") if kind == "Activity record" else
                    (lambda r: f"{r}: {rows.loc[r, 'indicator_code']} {rows.loc[r, 'project_id']} {rows.loc[r, 'district']}, "
                               f"{rows.loc[r, 'period'][:7]}"))
        record_id = st.selectbox("Entry", list(rows.index)[::-1], format_func=describe, key="edit_record")
        cur = rows.loc[record_id].to_dict()
        st.caption(f"Entered by {cur['created_by']} on {cur['created_at'][:16].replace('T', ' ')}"
                   + (f"; last changed by {cur['updated_by']} on {cur['updated_at'][:16].replace('T', ' ')}"
                      if cur.get("updated_by") else "") + ".")
        if kind == "Activity record":
            rec = activity_fields(f"edit_{record_id}", cur)
            action = app_store.update_activity
        else:
            rec = report_fields(f"edit_{record_id}", cur)
            action = app_store.update_indicator_report
        if st.button("Save changes", type="primary", disabled=not (ready and rec), key="save_edit"):
            save(action, record_id, rec, who)

with tabs[3]:
    history = pd.DataFrame(app_store.table("change_history"))
    if len(history):
        history = history[history["table_name"].isin(["activities", "indicator_reports"])]
    if not len(history):
        st.info("Nothing has been entered on this page yet.")
    else:
        history = history.sort_values("id", ascending=False)
        ui.table(pd.DataFrame({
            "When": pd.to_datetime(history["changed_at"]).dt.strftime("%d %b %Y %H:%M"), "Who": history["changed_by"],
            "Record": history["record_id"], "What": history["action"], "Field": history["field"],
            "Before": history["old_value"], "After": history["new_value"]}), "data_entry_change_history")

with tabs[4]:
    backups = app_store.list_backups()
    st.markdown(f"A dated copy is kept automatically after every save and each time the dashboard starts "
                f"(in `data/app/backups/`, the newest {ui.SETTINGS.get('app_backups_keep', 30)}). "
                f"{len(backups)} copies now" + (f"; the newest: {backups[0].name}." if backups else "."))
    st.download_button("⬇ Download backup (Excel: every entry made on the dashboard, uploads, change history)",
                       _backup_workbook(_stamp(app_store.db_path())) if app_store.db_path().exists() else b"",
                       file_name=f"dashboard_entries_backup_{dt.date.today():%Y-%m-%d}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       disabled=not app_store.db_path().exists(), key="dl_data_entries_backup")
    st.caption("Keep the downloaded file somewhere safe (not shared). To put a backup back, see the maintenance "
               "guide, \"Restoring dashboard entries\".")

st.markdown("### Entries made on this page")
if len(app_acts):
    ui.table(pd.DataFrame({
        "Record": app_acts["record_id"], "Project": app_acts["project_id"], "Activity": app_acts["activity_id"],
        "Place": app_acts["district"] + " / " + app_acts["sector"] + " / " + app_acts["village"],
        "Date": pd.to_datetime(app_acts["date"]).dt.strftime("%d/%m/%Y"), "Status": app_acts["status"].str.capitalize(),
        "Women": app_acts["participants_female"],
        "Men": app_acts["participants_male"], "Total": app_acts["participants_total"],
        "Cost (RWF)": app_acts["cost_rwf"], "Officer": app_acts["officer"], "Entered by": app_acts["created_by"]}),
        "data_entry_activities")
if len(app_reps):
    ui.table(pd.DataFrame({
        "Record": app_reps["record_id"], "Project": app_reps["project_id"], "District": app_reps["district"],
        "Month": pd.to_datetime(app_reps["period"]).dt.strftime("%b %Y"), "Indicator": app_reps["indicator_code"], "Sex": app_reps["sex"].fillna("").str.capitalize(),
        "Target": app_reps["target_value"], "Achieved": app_reps["actual_value"],
        "Entered by": app_reps["created_by"]}), "data_entry_reports")
if not len(app_acts) and not len(app_reps):
    st.caption("None yet.")
ui.update_figures_button(ready, "the Executive summary, Programme overview, Indicators and Geography pages")

ui.footer()
