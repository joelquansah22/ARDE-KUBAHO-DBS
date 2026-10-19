"""Donor entry: add donors and opportunities, update them, mark next actions done (saved to data/app/entries.db).

The entries are checked when they are saved (src/app_store.py) and every change is recorded with the staff code of
the person who made it. The pipeline reads them next to the Excel donor tracker, so they appear on the Donor pipeline
page after the figures are updated (button at the bottom of this page).
"""

import datetime as dt
import subprocess
import sys

import pandas as pd
import streamlit as st

import ui                 # first: it makes src/ importable
import app_store          # noqa: E402
import ingest             # noqa: E402

f = ui.filters(sex_applies=False)
ui.page_header("Donor entry", "donor_entry")
ui.how_to_read("donor_entry")
S = ui.SETTINGS["donor_pipeline"]
today = app_store.today()

# ------------------------------------------------------------------ who is entering data
people = app_store.staff()
labels = {p["code"]: f"{p['code']} ({p['role']})" for p in people}
who = st.selectbox("You are", ["Choose your name..."] + list(labels), format_func=lambda c: labels.get(c, c),
                   key=ui._remember("entry_staff", "Choose your name..."),
                   help="There is no login: pick yourself. Every change is recorded with this code.")
ready = who in labels
if not ready:
    st.info("Choose your name above before adding or changing anything.")

app_donors = pd.DataFrame(app_store.table("donors"))
app_opps = pd.DataFrame(app_store.table("opportunities"))


def donor_choices() -> dict:
    """Donors to pick from: those added here, and those already in the Excel tracker (by their pseudonymous key)."""
    choices = {}
    for r in app_donors.itertuples() if len(app_donors) else []:
        name = r.donor_name if isinstance(r.donor_name, str) else "Individual donor (added here)"
        choices[f"id:{r.donor_id}"] = f"{name} [{r.donor_id}]"
    app_keys = {ingest.pseudonym(ingest.load_salt(), "DON", d) for d in (app_donors["donor_id"] if len(app_donors) else [])}
    tracker = ui.query("SELECT donor_key, donor_name FROM dim_donor ORDER BY donor_name")
    for r in tracker.itertuples():
        if r.donor_key not in app_keys:
            choices[f"key:{r.donor_key}"] = r.donor_name
    return choices


def theme_options() -> list[str]:
    themes = S["themes"]
    return themes + ["; ".join(pair) for pair in zip(themes, themes[1:])]


def save(action, *args) -> bool:
    try:
        result = action(*args)
    except app_store.EntryError as e:
        st.error(str(e))
        return False
    st.session_state["entry_message"] = f"Saved{': ' + result if isinstance(result, str) else ''}. It appears on the " \
                                        "Donor pipeline page after the figures are updated (bottom of this page)."
    st.rerun()
    return True


if "entry_message" in st.session_state:
    st.success(st.session_state.pop("entry_message"))

st.caption(ui.donor_sources_note())
tabs = st.tabs(["New opportunity", "Update an opportunity", "Next actions", "New donor", "Change history",
                "Import from the Excel tracker", "Backup"])

# ------------------------------------------------------------------ new opportunity
with tabs[0]:
    donors = donor_choices()
    with st.form("new_opportunity", clear_on_submit=False):
        c1, c2 = st.columns(2)
        title = c1.text_input("Title *", placeholder="e.g. Safe water for schools - Kayonza")
        donor = c2.selectbox("Donor *", list(donors), format_func=donors.get,
                             help="Not in the list? Add it on the 'New donor' tab first.")
        theme = c1.selectbox("Thematic fit *", theme_options())
        stage = c2.selectbox("Stage *", S["stages"])
        deadline = c1.date_input("Deadline *", value=today + dt.timedelta(days=30), min_value=today + dt.timedelta(days=1),
                                 format="DD/MM/YYYY")
        owner = c2.selectbox("Owner *", list(labels), format_func=labels.get)
        requested = c1.number_input("Amount requested (RWF) *", min_value=0, step=1_000_000, value=0)
        awarded = c2.number_input("Amount awarded (RWF)", min_value=0, step=1_000_000, value=0,
                                  help="Only when the stage is Awarded.")
        probability = c1.slider("Probability of success (%) *", 0, 100, 30, step=5)
        next_action = c2.text_input("Next action", placeholder="e.g. Send concept note")
        next_date = c2.date_input("Next action due", value=None, format="DD/MM/YYYY")
        if st.form_submit_button("Save opportunity", type="primary", disabled=not ready):
            kind, ref = donor.split(":", 1)
            save(app_store.add_opportunity, dict(
                title=title, donor_id=ref if kind == "id" else None, donor_key=ref if kind == "key" else None,
                thematic_fit=theme, stage=stage, deadline=deadline, owner=owner, requested_amount_rwf=requested,
                awarded_amount_rwf=awarded or None, probability=probability / 100, next_action=next_action,
                next_action_date=next_date), who)
    st.caption("* required. Amounts in RWF, numbers only. The deadline must be in the future.")

# ------------------------------------------------------------------ update an opportunity
with tabs[1]:
    st.caption("Opportunities added on this page can be updated here. Those in the Excel tracker are updated in the "
               "Excel file, so that each opportunity has one place where it is kept.")
    if not len(app_opps):
        st.info("No opportunity has been added on this page yet.")
    else:
        opp_id = st.selectbox("Opportunity", list(app_opps["opportunity_id"]),
                              format_func=lambda i: f"{i}: {app_opps.set_index('opportunity_id').loc[i, 'title']}",
                              key="entry_edit_opp")
        o = app_opps.set_index("opportunity_id").loc[opp_id]
        with st.form("edit_opportunity"):
            c1, c2 = st.columns(2)
            stage = c1.selectbox("Stage", S["stages"], index=S["stages"].index(o["stage"]))
            owner = c2.selectbox("Owner", list(labels), index=list(labels).index(o["owner"]) if o["owner"] in labels else 0,
                                 format_func=labels.get)
            requested = c1.number_input("Amount requested (RWF)", min_value=0, step=1_000_000,
                                        value=int(o["requested_amount_rwf"]))
            awarded = c2.number_input("Amount awarded (RWF)", min_value=0, step=1_000_000,
                                      value=int(o["awarded_amount_rwf"]) if pd.notna(o["awarded_amount_rwf"]) else 0)
            probability = c1.slider("Probability of success (%)", 0, 100, int(round(100 * o["probability"])), step=5)
            deadline = c2.date_input("Deadline", value=dt.date.fromisoformat(o["deadline"]) if o["deadline"] else None,
                                     format="DD/MM/YYYY")
            next_action = c1.text_input("Next action", value=o["next_action"] or "")
            next_date = c2.date_input("Next action due", format="DD/MM/YYYY",
                                      value=dt.date.fromisoformat(o["next_action_date"]) if o["next_action_date"] else None)
            if st.form_submit_button("Save changes", type="primary", disabled=not ready):
                save(app_store.update_opportunity, opp_id, dict(
                    stage=stage, owner=owner, requested_amount_rwf=requested, awarded_amount_rwf=awarded or None,
                    probability=probability / 100, deadline=deadline, next_action=next_action,
                    next_action_date=next_date), who)

# ------------------------------------------------------------------ next actions
with tabs[2]:
    pending = app_opps[app_opps["next_action"].notna()] if len(app_opps) else app_opps
    if not len(pending):
        st.info("No next action is waiting among the opportunities added on this page.")
    else:
        for r in pending.sort_values("next_action_date").itertuples():
            due = dt.date.fromisoformat(r.next_action_date)
            late = f" **(overdue by {(today - due).days} days)**" if due < today else ""
            c1, c2 = st.columns([4, 1])
            c1.markdown(f"**{r.opportunity_id}** {r.title}: {r.next_action}, due {due:%d %b %Y}{late} · owner {r.owner}")
            if c2.button("Mark done", key=f"done_{r.opportunity_id}", disabled=not ready):
                save(app_store.mark_next_action_done, r.opportunity_id, who)
    st.caption("Marking an action done keeps it in the change history and clears it; then add the next action on "
               "the 'Update an opportunity' tab.")

# ------------------------------------------------------------------ new donor
with tabs[3]:
    with st.form("new_donor"):
        c1, c2 = st.columns(2)
        dtype = c1.selectbox("Donor type *", list(S["donor_type_mapping"]))
        name = c2.text_input("Organisation name * (leave empty for an individual)",
                             help="Individual donors are never named here: they appear as 'Individual donor #NNN'.")
        country = c1.text_input("Country")
        interests = c2.text_input("Thematic interests", placeholder="e.g. WASH; climate")
        if st.form_submit_button("Save donor", type="primary", disabled=not ready):
            save(app_store.add_donor, dict(donor_type=dtype, donor_name=name, country=country,
                                           thematic_interests=interests), who)
    st.caption("No contact names, emails or phone numbers are stored here: keep them in your own address book.")

# ------------------------------------------------------------------ change history
with tabs[4]:
    history = pd.DataFrame(app_store.table("change_history"))
    if not len(history):
        st.info("Nothing has been entered on this page yet.")
    else:
        history = history.sort_values("id", ascending=False)
        ui.table(pd.DataFrame({
            "When": pd.to_datetime(history["changed_at"]).dt.strftime("%d %b %Y %H:%M"), "Who": history["changed_by"],
            "Record": history["record_id"], "What": history["action"], "Field": history["field"],
            "Before": history["old_value"], "After": history["new_value"]}), "donor_entry_change_history")

# ------------------------------------------------------------------ one home: import the Excel tracker (once)
with tabs[5]:
    st.markdown("Move the donors and opportunities from the Excel donor tracker into this page, **once**, so donor "
                "data has one home. IDs are kept, and each record keeps a note of the Excel file, sheet and row it "
                "came from. After the import the pipeline no longer reads those Excel rows; the Excel donor template "
                "stays only as an **offline fallback** for new opportunities (see the user guide).")
    try:
        preview = app_store.import_preview()
    except app_store.EntryError as e:
        preview = None
        st.info(str(e))
    if preview is not None:
        d, o, problems = preview["donors"], preview["opportunities"], preview["problems"]
        if not len(d) and not len(o) and not len(problems):
            st.success("Nothing left to import: the Excel tracker's records are already kept here.")
        else:
            st.markdown(f"**Preview:** {len(d)} donors and {len(o)} opportunities will be moved; {len(problems)} "
                        "opportunities must be corrected in the Excel file first (they stay in Excel until then).")
            if len(o):
                ui.table(pd.DataFrame({
                    "Opportunity": o["opportunity_id"] + " " + o["title"], "Stage": o["stage"],
                    "Requested": [ui.money(x) for x in o["requested_amount_rwf"]],
                    "Probability": [f"{p:.0%}" for p in o["probability"]], "Owner": o["owner"],
                    "From": o["source_file"] + " / row " + o["source_row"].astype(int).astype(str)}),
                    "import_preview_opportunities", height=240)
            if len(problems):
                st.markdown("**To correct in Excel first**")
                ui.table(problems.rename(columns={"opportunity_id": "Opportunity", "where": "Excel row",
                                                  "problem": "Why"}), "import_preview_problems")
            agree = st.checkbox("I have checked the preview and want to move these records to this page.",
                                key="import_agree")
            if st.button("Import now", type="primary", disabled=not (ready and agree and (len(d) or len(o)))):
                save(lambda by: f"{app_store.import_tracker(by)['opportunities']} opportunities imported", who)

# ------------------------------------------------------------------ backup
with tabs[6]:
    backups = app_store.list_backups()
    st.markdown(f"A dated copy is kept automatically after every save and each time the dashboard starts "
                f"(in `data/app/backups/`, the newest {ui.SETTINGS.get('app_backups_keep', 30)}). "
                f"{len(backups)} copies now" + (f"; the newest: {backups[0].name}." if backups else "."))
    st.download_button("⬇ Download backup (Excel: donors, opportunities, change history)",
                       app_store.export_workbook() if app_store.db_path().exists() else b"",
                       file_name=f"donor_entries_backup_{dt.date.today():%Y-%m-%d}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       disabled=not app_store.db_path().exists(), key="dl_entries_backup")
    st.caption("Keep the downloaded file somewhere safe (not shared). To put a backup back, see the maintenance "
               "guide, \"Restoring donor entries\".")

# ------------------------------------------------------------------ entries and refresh
st.markdown("### Entries made on this page")
if len(app_opps):
    ui.table(pd.DataFrame({
        "Opportunity": app_opps["opportunity_id"] + " " + app_opps["title"], "Stage": app_opps["stage"],
        "Deadline": app_opps["deadline"], "Requested": [ui.money(x) for x in app_opps["requested_amount_rwf"]],
        "Probability": [f"{p:.0%}" for p in app_opps["probability"]], "Owner": app_opps["owner"],
        "Next action": app_opps["next_action"], "Due": app_opps["next_action_date"]}), "donor_entry_opportunities")
else:
    st.caption("None yet.")
st.markdown("**Update the dashboard figures** so the entries appear on the Donor pipeline and Executive summary "
            "pages (about 20 seconds).")
if st.button("Update the figures now", disabled=not ready):
    with st.spinner("Preparing the figures..."):
        r = subprocess.run([sys.executable, str(ui.ROOT / "src" / "pipeline.py")], cwd=ui.ROOT, capture_output=True,
                           text=True)
    if r.returncode == 0:
        st.success("The figures are up to date.")
    else:
        st.error("The figures could not be updated. Ask the MEAL officer to run the pipeline (maintenance guide):\n\n"
                 + (r.stdout + r.stderr)[-800:])

ui.footer()
