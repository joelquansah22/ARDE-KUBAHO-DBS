"""Donor entry (ARDE/KUBAHO workbook mode): add donors and funding opportunities, update them, mark next actions done.

The same checks, change history and backups as the demo's Donor entry (src/app_store.py), but in a separate file
under data/real/app/ (settings: arde.donor_store), so demonstration donors never mix with ARDE/KUBAHO's. Individual
donors are never named. Opportunities appear at once on the Donor pipeline and Executive summary pages.
"""

import datetime as dt

import pandas as pd
import streamlit as st

import ui                 # first: it makes src/ importable
import app_store          # noqa: E402
import arde_funding       # noqa: E402

f = ui.arde_filters()
ui.page_header("Donor entry", "arde_donor_entry")
ui.how_to_read("arde_donor_entry")
who, labels, ready = ui.staff_picker("adding or changing anything")
today = app_store.today()
settings = ui.SETTINGS["donor_pipeline"]
areas = sorted(ui.query("SELECT DISTINCT intervention_area FROM dim_project")["intervention_area"].dropna())


def save(action, *args) -> None:
    try:
        result = action(*args, who)
        st.success(f"Saved ({result}). A backup was made." if result else "Saved. A backup was made.")
    except app_store.EntryError as err:
        st.error(str(err))


donors = pd.DataFrame(app_store.table("donors"))
opps = arde_funding.opportunities()
tab_opp, tab_update, tab_donor, tab_history = st.tabs(["New opportunity", "Update an opportunity", "New donor",
                                                       "Change history and backups"])

with tab_opp:
    if not len(donors):
        st.info("Add the donor first (tab \"New donor\"), then come back here.")
    else:
        names = {r.donor_id: (r.donor_name or f"Individual donor ({r.donor_id})") for r in donors.itertuples()}
        with st.form("arde_new_opportunity"):
            a, b = st.columns(2)
            donor_id = a.selectbox("Donor *", list(names), format_func=names.get)
            title = b.text_input("Title *", max_chars=200)
            fit = a.selectbox("Fits which intervention area *", areas)
            stage = b.selectbox("Stage *", settings["open_stages"])
            deadline = a.date_input("Deadline *", value=today + dt.timedelta(days=30), min_value=today,
                                    format="DD/MM/YYYY")
            amount = b.number_input("Amount requested (RWF) *", min_value=0.0, step=1_000_000.0, format="%.0f")
            probability = a.slider("Chance of success (%) *", 0, 100, 50)
            owner = b.selectbox("Owner *", list(labels), format_func=labels.get)
            action = a.text_input("Next action", max_chars=200)
            action_date = b.date_input("Next action due", value=None, format="DD/MM/YYYY")
            if st.form_submit_button("Save the opportunity", type="primary", disabled=not ready):
                save(app_store.add_opportunity, dict(
                    donor_id=donor_id, title=title, thematic_fit=fit, stage=stage, deadline=deadline,
                    requested_amount_rwf=amount, probability=probability / 100, owner=owner,
                    next_action=action or None, next_action_date=action_date))

with tab_update:
    if not len(opps):
        st.markdown("No funding opportunities recorded yet. Add your first one on the \"New opportunity\" tab.")
    else:
        opp_id = st.selectbox("Opportunity", list(opps["opportunity_id"]),
                              format_func=lambda i: f"{i}: {opps.set_index('opportunity_id').loc[i, 'title']}")
        row = opps.set_index("opportunity_id").loc[opp_id]
        with st.form("arde_update_opportunity"):
            a, b = st.columns(2)
            stage = a.selectbox("Stage", settings["stages"], index=settings["stages"].index(row["stage"]))
            probability = b.slider("Chance of success (%)", 0, 100, int(round(100 * (row["probability"] or 0))))
            amount = a.number_input("Amount requested (RWF)", min_value=0.0, value=float(row["requested_amount_rwf"] or 0),
                                    format="%.0f")
            awarded = b.number_input("Amount awarded (RWF)", min_value=0.0,
                                     value=float(row["awarded_amount_rwf"] or 0), format="%.0f")
            action = a.text_input("Next action", value=row["next_action"] or "")
            action_date = b.date_input("Next action due", value=row["next_action_date"], format="DD/MM/YYYY")
            if st.form_submit_button("Save the changes", type="primary", disabled=not ready):
                save(lambda by: ", ".join(app_store.update_opportunity(opp_id, dict(
                    stage=stage, probability=probability / 100, requested_amount_rwf=amount,
                    awarded_amount_rwf=awarded or None, next_action=action or None,
                    next_action_date=action_date), by)) or "nothing changed")
        if row["next_action"] and st.button("Mark the next action done", disabled=not ready, key="arde_action_done"):
            save(app_store.mark_next_action_done, opp_id)

with tab_donor:
    with st.form("arde_new_donor"):
        a, b = st.columns(2)
        dtype = a.selectbox("Donor type *", list(settings["donor_type_mapping"]))
        name = b.text_input("Organisation name (leave empty for an individual) *", max_chars=200)
        country = a.text_input("Country", max_chars=100)
        interests = b.multiselect("Interested in", areas)
        if st.form_submit_button("Save the donor", type="primary", disabled=not ready):
            save(app_store.add_donor, dict(donor_type=dtype, donor_name=name, country=country,
                                           thematic_interests="; ".join(interests)))
    if len(donors):
        ui.table(pd.DataFrame({"Donor": donors["donor_id"], "Name": donors["donor_name"].fillna("(individual)"),
                               "Type": donors["donor_type"], "Country": donors["country"]}), "arde_donors")

with tab_history:
    history = pd.DataFrame(app_store.table("change_history"))
    if not len(history):
        st.caption("Nothing recorded yet.")
    else:
        ui.table(pd.DataFrame({"When": history["changed_at"].str.replace("T", " "), "Who": history["changed_by"],
                               "Record": history["record_id"], "What": history["action"], "Field": history["field"],
                               "Old": history["old_value"], "New": history["new_value"]}).iloc[::-1],
                 "arde_donor_history")
    backups = app_store.list_backups()
    st.caption(f"{len(backups)} backups kept in {app_store.backup_folder()} (newest {ui.SETTINGS['app_backups_keep']}).")
ui.footer()
