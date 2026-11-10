"""Partners and funding (ARDE/KUBAHO workbook mode): financial and in-kind contributions by stakeholder type and
project. This is the "funding history" linked from the Donor pipeline page.

Money is never added across currencies: totals are per currency, with an RWF estimate (≈) next to them. In-kind
contributions valued in other units (people, roles, schools...) are listed, never added to money.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

import ui                # first: it makes src/ importable

f = ui.arde_filters()
ui.page_header("Partners and funding", "partners_funding")
ui.how_to_read("partners_funding")
codes = f.project_codes
if not codes:
    ui.no_data()
    st.stop()
IN = ui.in_list(codes)
c = ui.query(f"""SELECT c.*, p.intervention_area FROM fact_contribution c JOIN dim_project p USING (project_code)
                 WHERE c.project_code IN {IN}""", *codes)
p = ui.query(f"SELECT project_code, donor_partner FROM dim_project WHERE project_code IN {IN} ORDER BY 1", *codes)
if not len(c):
    ui.no_data()
    st.stop()

money = c[c["is_money"] & (c["value"].fillna(0) > 0)]
cur = money.groupby("currency")["value"].sum()
tiles = [("Contributions recorded", f"{len(c):,}",
          f"{int((c['nature'] == 'Financial').sum())} financial · {int((c['nature'] == 'In-kind').sum())} in-kind")]
tiles += [(f"Valued contributions in {k}", ui.native_money(v, k), f"{int((money['currency'] == k).sum())} entries")
          for k, v in cur.items()]
tiles.append(("All valued contributions, RWF estimate", ui.rwf_estimate(money["value_rwf_estimate"].sum()),
              "approximate rates for each project's start year"))
ui.tiles(tiles[:5])

left, right = st.columns(2)
with left:
    st.markdown("#### Contributions by stakeholder type")
    by = c.groupby(["stakeholder_type", "nature"]).size().reset_index(name="Contributions")
    top = by.groupby("stakeholder_type")["Contributions"].sum().nlargest(12).index
    fig = px.bar(by[by["stakeholder_type"].isin(top)], y="stakeholder_type", x="Contributions", color="nature",
                 orientation="h", labels={"stakeholder_type": "", "nature": ""}, height=380)
    fig.update_yaxes(automargin=True, categoryorder="total ascending")
    ui.legend_on_top(fig)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.caption("The 12 most frequent stakeholder types (counts of contributions, not amounts). All are in the table "
               "below.")
with right:
    st.markdown("#### Valued contributions by project (RWF estimate)")
    if len(money):
        bym = money.groupby(["project_code", "nature"], as_index=False)["value_rwf_estimate"].sum()
        fig = px.bar(bym, y="project_code", x="value_rwf_estimate", color="nature", orientation="h",
                     labels={"project_code": "", "value_rwf_estimate": "RWF estimate (≈)", "nature": ""},
                     height=380)
        fig.update_yaxes(automargin=True, categoryorder="total ascending")
        ui.legend_on_top(fig)
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        st.caption("Each bar is converted from its own currency at an approximate rate (≈); the table gives the "
                   "amount in its own currency.")
    else:
        st.markdown("No contribution in this selection is valued in money.")

st.markdown("#### Every contribution")
ui.table(pd.DataFrame({
    "Project": c["project_code"], "Stakeholder": c["stakeholder"], "Type": c["stakeholder_type"],
    "Financial / in-kind": c["nature"], "Contribution": c["contribution_type"],
    "Value (as written)": [ui.native_money(v, cu) if m else (f"{v:,.0f} {u}" if pd.notna(v) and v else str(u))
                           for v, cu, u, m in zip(c["value"], c["currency"], c["currency_or_unit"], c["is_money"])],
    "RWF estimate": [ui.rwf_estimate(v) if m and cu != "RWF" else "" for v, cu, m in
                     zip(c["value_rwf_estimate"], c["currency"], c["is_money"])],
    "Evidence": c["evidence"], "Stakeholders row": c["source_row"]}), "contributions", height=360)

st.markdown("#### Donors and partners named in the Projects sheet")
ui.table(p.rename(columns={"project_code": "Project", "donor_partner": "Donor / partner (as written)"}),
         "project_donors")
ui.footer()
