"""Donor pipeline (ARDE/KUBAHO workbook mode).

ARDE's MEAL workbook holds funding that has been received (the Stakeholders sheet), not opportunities still being
pursued, so there is no pipeline to show in this mode: one plain line says so, with a link to the funding history
(Partners and funding). The donor opportunity tracker of the demonstration data stays in synthetic mode.
"""

import streamlit as st

import ui                # first: it makes src/ importable

f = ui.arde_filters()
ui.page_header("Donor pipeline", "arde_donor_pipeline")
st.markdown("ARDE/KUBAHO's MEAL workbook has no funding opportunities (deadlines, stages, amounts requested), so "
            "there is no pipeline to show yet. Past and current funding is under **funding history**:")
page = ui.menu_page("partners_funding")
st.page_link(page["file"], label="Funding history: Partners and funding", icon=page["icon"])
st.caption("Whether ARDE/KUBAHO keeps a list of opportunities it is applying for is an open question "
           "(docs/partner_questions.md). The demonstration donor tracker is still available in synthetic mode.")
ui.footer()
