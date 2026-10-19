"""Records: read and search every stored table, and see where each record came from.

Tables: activities, indicator results, donors, opportunities, records held back for correction, and the review
queue. Filters: project, district and date range (sidebar), plus officer, status, source (Excel file or entered in
the app) and a free-text search on this page. Each record shows its origin: the Excel file, sheet and row (and who
uploaded the file, and when, if it came through the Upload Excel page), or the app entry with who made it and when.
The filtered view can be exported to Excel.

Read-only. No beneficiary names, phone numbers or ID numbers are shown here (or anywhere on the dashboard): people
are not listed on this page at all, and held-back register rows show only where they are and why.
"""

import datetime as dt
from io import BytesIO

import pandas as pd
import streamlit as st

import ui                 # first: it makes src/ importable
import app_store          # noqa: E402

f = ui.filters(sex_applies=False)
ui.page_header("Records", "records")
ui.how_to_read("records")
staging = ui.resolve_path("staging")
APP = "entries.db"


def _stamp(path) -> float:
    return path.stat().st_mtime if path.exists() else 0.0


@st.cache_data(show_spinner=False, max_entries=2)
def _origins(db_stamp: float) -> tuple[dict, dict]:
    """Who entered each app record and when, and who uploaded each Excel file and when (data/app/entries.db)."""
    entered = {}
    for table, id_col in (("activities", "record_id"), ("indicator_reports", "record_id"), ("donors", "donor_id"),
                          ("opportunities", "opportunity_id")):
        for r in app_store.table(table):
            text = f"Entered in the app: {r[id_col]} by {r['created_by']} on {_when(r['created_at'])}"
            if r.get("origin_file"):
                text += f" (moved from {r['origin_file']}, row {r['origin_row']})"
            if r.get("updated_by"):
                text += f"; last changed by {r['updated_by']} on {_when(r['updated_at'])}"
            entered[(table, int(r["row_id"]))] = text
    uploaded = {u["stored_file"]: f"uploaded by {u['uploaded_by']} on {_when(u['uploaded_at'])} ({u['upload_id']})"
                for u in app_store.table("uploads")}
    return entered, uploaded


def _when(iso: str) -> str:
    return dt.datetime.fromisoformat(iso).strftime("%d %b %Y %H:%M") if iso else ""


def origin(df: pd.DataFrame) -> pd.DataFrame:
    """Add Source (Excel file / Entered in the app) and Origin (where exactly) to a table with lineage columns."""
    entered, uploaded = _origins(_stamp(app_store.db_path()))
    app = df["source_file"] == APP
    df = df.copy()
    df["Source"] = app.map({True: "Entered in the app", False: "Excel file"})
    df["Origin"] = [entered.get((s, int(r)), f"Entered in the app ({s}, row {int(r)})") if a else
                    f"{fl}, sheet {s}, row {int(r)}" + (f"; {uploaded[fl]}" if fl in uploaded else "")
                    for a, fl, s, r in zip(app, df["source_file"], df["source_sheet"], df["source_row"])]
    return df.drop(columns=["source_file", "source_sheet", "source_row"])


def _staged(entity: str) -> pd.DataFrame:
    """Project and district of each cleaned row (including held-back rows, which the warehouse leaves out)."""
    path = staging / f"clean_{entity}.parquet"
    if not path.exists():
        return pd.DataFrame(columns=["source_file", "source_sheet", "source_row"])
    cols = [c for c in ("source_file", "source_sheet", "source_row", "project_id", "district")
            if c in pd.read_parquet(path, columns=None).columns]
    return pd.read_parquet(path, columns=cols)


def flagged(table: str) -> pd.DataFrame:
    q = ui.query(f"SELECT entity, source_file, source_sheet, source_row, month, reasons, details, field_officer "
                 f"FROM {table}")
    parts = []
    for entity, rows in q.groupby("entity"):
        staged = _staged(entity)
        parts.append(rows.merge(staged, on=["source_file", "source_sheet", "source_row"], how="left"))
    q = pd.concat(parts, ignore_index=True) if parts else q.assign(project_id=None, district=None)
    for c in ("project_id", "district"):
        q[c] = q[c] if c in q else None
    q = origin(q)
    return pd.DataFrame({
        "Record type": q["entity"].map(ui.entity_label), "Project": q["project_id"], "District": q["district"],
        "Month": q["month"], "Date": pd.to_datetime(q["month"] + "-01", errors="coerce"),
        "Status": [ui.issues_in_words(r) for r in q["reasons"]], "Details": [ui.details_in_words(d) for d in q["details"]],
        "Officer": q["field_officer"], "Source": q["Source"], "Origin": q["Origin"]})


def load(name: str) -> pd.DataFrame:
    """One table, with the standard filter columns Project, District, Officer, Date, Status, Source."""
    if name == "Activities":
        q = origin(ui.query("""
            SELECT a.project_id, f.activity_id, a.activity_name, l.district, l.sector, l.cell, l.village, f.date,
                   f.planned_date, f.status, f.participants_female, f.participants_male, f.participants_total,
                   f.cost_rwf, f.officer_code, f.quality_flag, f.source_file, f.source_sheet, f.source_row
            FROM fact_activity f JOIN dim_activity a USING (activity_id) LEFT JOIN dim_location l USING (location_id)
            ORDER BY f.date DESC NULLS LAST"""))
        return pd.DataFrame({
            "Project": q["project_id"], "Activity": q["activity_id"] + " " + q["activity_name"], "District": q["district"],
            "Sector": q["sector"], "Cell": q["cell"], "Village": q["village"], "Date": pd.to_datetime(q["date"]),
            "Planned date": pd.to_datetime(q["planned_date"]), "Status": q["status"].str.capitalize(),
            "Women": q["participants_female"], "Men": q["participants_male"], "Total": q["participants_total"],
            "Cost (RWF)": q["cost_rwf"], "Officer": q["officer_code"],
            "Quality": q["quality_flag"].map({"ok": "OK", "warning": "For review", "info": "Note"}),
            "Source": q["Source"], "Origin": q["Origin"]})
    if name == "Indicator results":
        q = origin(ui.query("""
            SELECT f.project_id, i.code, i.name, l.district, f.period_date, f.disaggregation_key, f.target_value,
                   f.actual_value, f.officer_code, f.entered_by, f.quality_flag, f.source_file, f.source_sheet,
                   f.source_row
            FROM fact_indicator_result f JOIN dim_indicator i USING (indicator_id)
            LEFT JOIN dim_location l USING (location_id) ORDER BY f.period_date DESC"""))
        return pd.DataFrame({
            "Project": q["project_id"], "Indicator": q["code"] + " " + q["name"], "District": q["district"],
            "Month": pd.to_datetime(q["period_date"]).dt.strftime("%b %Y"), "Date": pd.to_datetime(q["period_date"]),
            "Breakdown": q["disaggregation_key"].replace({"total": ""}).str.capitalize(), "Target": q["target_value"],
            "Achieved": q["actual_value"], "Officer": q["officer_code"].fillna(q["entered_by"]),
            "Status": q["quality_flag"].map({"ok": "OK", "warning": "For review", "info": "Note"}),
            "Source": q["Source"], "Origin": q["Origin"]})
    if name == "Donors":
        q = origin(pd.read_parquet(staging / "clean_donor.parquet"))        # individuals: "Individual donor #NNN"
        return pd.DataFrame({"Donor": q["donor_name"], "Status": q["donor_type"].str.capitalize(),
                             "Country": q["country"], "Thematic interests": q["thematic_interests"],
                             "Source": q["Source"], "Origin": q["Origin"]})
    if name == "Opportunities":
        q = origin(ui.query("""
            SELECT o.opportunity_id, o.title, d.donor_name, o.thematic_fit, o.stage, o.deadline,
                   o.requested_amount_rwf, o.awarded_amount_rwf, o.probability, o.owner, o.next_action,
                   o.next_action_date, o.source_file, o.source_sheet, o.source_row
            FROM fact_opportunity o LEFT JOIN dim_donor d USING (donor_key) ORDER BY o.deadline"""))
        return pd.DataFrame({
            "Opportunity": q["opportunity_id"] + " " + q["title"], "Donor": q["donor_name"],
            "Thematic fit": q["thematic_fit"], "Status": q["stage"], "Date": pd.to_datetime(q["deadline"]),
            "Requested (RWF)": q["requested_amount_rwf"], "Awarded (RWF)": q["awarded_amount_rwf"],
            "Probability": q["probability"], "Officer": q["owner"], "Next action": q["next_action"],
            "Next action due": pd.to_datetime(q["next_action_date"]), "Source": q["Source"], "Origin": q["Origin"]})
    if name == "Held back for correction":
        return flagged("quarantine")
    return flagged("review_queue")


TABLES = ["Activities", "Indicator results", "Donors", "Opportunities", "Held back for correction", "Review queue"]
DATE_MEANING = {"Activities": "activity date", "Indicator results": "reporting month",
                "Held back for correction": "month", "Review queue": "month"}
STATUS_MEANING = {"Activities": "Status", "Indicator results": "Quality", "Donors": "Donor type",
                  "Opportunities": "Stage", "Held back for correction": "Reason", "Review queue": "Reason"}

name = st.radio("Table", TABLES, horizontal=True, key=ui._remember("records_table", "Activities"))
df = load(name)

# ------------------------------------------------------------------ filters
not_applied = []
if "Project" in df:
    df = df[df["Project"].isin(f.project_ids) | (df["Project"].isna() & (f.project_id is None) & (f.programme_id is None))]
elif f.project_id or f.programme_id:
    not_applied.append("project")
if "District" in df:
    df = df[(df["District"] == f.district)] if f.district else df
elif f.district:
    not_applied.append("district")
if "Date" in df and name != "Opportunities":         # deadlines are mostly in the future: not filtered by date
    inside = df["Date"].between(pd.Timestamp(f.start), pd.Timestamp(f.end))
    df = df[inside | df["Date"].isna()]               # undated records (e.g. planned activities) are kept
c1, c2, c3, c4 = st.columns([1, 1.3, 1, 1.6])
officers = sorted(df["Officer"].dropna().unique()) if "Officer" in df else []
officer = c1.selectbox("Officer / owner", ["All"] + officers, key="records_officer", disabled="Officer" not in df)
statuses = sorted(df["Status"].dropna().astype(str).unique())
status = c2.selectbox(STATUS_MEANING[name], ["All"] + statuses, key=f"records_status_{name}")
source = c3.selectbox("Source", ["All", "Excel file", "Entered in the app"], key="records_source")
search = c4.text_input("Search", placeholder="any word or code, e.g. Kayonza, ACT03, row 52", key="records_search")
if officer != "All":
    df = df[df["Officer"] == officer]
if status != "All":
    df = df[df["Status"].astype(str) == status]
if source != "All":
    df = df[df["Source"] == source]
if search.strip() and len(df):
    text = df.astype(object).fillna("").astype(str).agg(" ".join, axis=1).str.lower()
    df = df[[all(w in t for w in search.lower().split()) for t in text]]   # every word must appear

scope = [f.scope_text if "Project" in df or "District" in df else "",
         f"{DATE_MEANING[name]} {f.start:%d/%m/%Y} to {f.end:%d/%m/%Y}" if name in DATE_MEANING else ""]
st.markdown(" · ".join([f"**{len(df):,} records**"] + [x for x in scope if x]))
if name == "Opportunities":
    not_applied.append("date range")
if not_applied:
    st.caption(f"The {' and '.join(not_applied)} filter does not apply to this table"
               + (" (deadlines are mostly in the future; sort by Date instead)." if name == "Opportunities" else "."))
if name in ("Held back for correction", "Review queue"):
    st.caption("Register (people) rows are listed only by file, row and reason: no names, phones or ID numbers. "
               "Correct held-back rows in the Excel file and upload it again.")

shown = df.copy()
for c in shown.columns:
    if pd.api.types.is_datetime64_any_dtype(shown[c]):
        shown[c] = shown[c].dt.strftime("%d/%m/%Y")
if name in ("Indicator results", "Held back for correction", "Review queue"):
    shown = shown.drop(columns=["Date"])
if "Probability" in shown:
    shown["Probability"] = [f"{p:.0%}" if pd.notna(p) else "" for p in shown["Probability"]]
ui.table(shown, f"records_{name.lower().replace(' ', '_')}", height=420)


@st.cache_data(show_spinner=False, max_entries=4)
def _excel(frame: pd.DataFrame, title: str, about: tuple) -> bytes:
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as xl:
        frame.to_excel(xl, sheet_name=title[:31], index=False)
        pd.DataFrame({"About this export": list(about)}).to_excel(xl, sheet_name="About", index=False)
    return out.getvalue()


about = (f"{name}: {len(shown):,} records, exported {dt.datetime.now():%d %b %Y %H:%M}.",
         "Filters: " + "; ".join(x for x in scope + [f"officer {officer}", f"{STATUS_MEANING[name].lower()} {status}",
                                                     f"source {source}", f"search '{search}'" if search else ""] if x),
         ui.SETTINGS["synthetic_banner"] if ui.SETTINGS.get("synthetic_mode") else "ARDE/KUBAHO records.",
         "Read-only export. Correct Excel records in their file; app entries on the Data entry or Donor entry page.")
st.download_button(f"⬇ Export this view to Excel ({len(shown):,} row{'s' if len(shown) != 1 else ''})", _excel(shown, name, about),
                   file_name=f"{'SYNTHETIC_' if ui.SETTINGS.get('synthetic_mode') else ''}records_"
                             f"{name.lower().replace(' ', '_')}_{dt.date.today():%Y-%m-%d}.xlsx",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="records_excel",
                   type="primary")
st.caption("Records from Excel files are corrected in the Excel file and uploaded again (Upload Excel page). "
           "Records entered in the app are changed on the Data entry or Donor entry page.")

ui.footer()
