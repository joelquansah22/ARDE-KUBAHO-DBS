"""Geography (ARDE/KUBAHO workbook mode): in which districts the projects work.

Districts are read from each project's free-text location (src/arde_model.py: extract_districts). A project naming
two districts counts in both. Reach is NOT mapped: the workbook does not say how a project's reach splits between
its districts, and reach is never added across units.
"""

import json

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import ui                # first: it makes src/ importable

f = ui.arde_filters()
ui.page_header("Geography", "arde_geography")
ui.how_to_read("arde_geography")
codes = f.project_codes
if not codes:
    ui.no_data()
    st.stop()
IN = ui.in_list(codes)
d = ui.query(f"""SELECT b.*, p.status, p.intervention_area, p.outside_rwanda, p.location FROM dim_project_district b
                 JOIN dim_project p USING (project_code) WHERE b.project_code IN {IN}""", *codes)
missing = ui.query(f"SELECT project_code, location FROM dim_project WHERE district_count = 0 AND project_code IN {IN}",
                   *codes)
if not len(d):
    st.info("No Rwandan district could be read from the locations of the projects in this selection, so there is "
            "nothing to map. The locations are listed on the Data quality page.")
    st.stop()

GEOJSON = ui.ROOT / "config" / "reference" / "geo" / "geoBoundaries-RWA-ADM2_simplified.geojson"


def _clockwise(ring: list) -> list:
    """Plotly's map drawing wants each outer edge clockwise; GeoJSON runs it the other way (see 3_Geography.py)."""
    area = sum(x1 * y2 - x2 * y1 for (x1, y1, *_), (x2, y2, *_) in zip(ring, ring[1:] + ring[:1]))
    return ring[::-1] if area > 0 else ring


@st.cache_data(show_spinner=False)
def districts_geojson():
    if not GEOJSON.exists():
        return None
    geo = json.loads(GEOJSON.read_text(encoding="utf-8"))
    for feature in geo["features"]:
        g = feature["geometry"]
        for polygon in ([g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]):
            polygon[0] = _clockwise(polygon[0])
            for i in range(1, len(polygon)):
                polygon[i] = _clockwise(polygon[i])[::-1]
    return geo


per = d.groupby(["province", "district"], as_index=False).agg(projects=("project_code", "nunique"))
all_districts = pd.DataFrame({"district": [x for ds in ui.load_yaml("reference/rwanda_admin.yaml")["provinces"].values()
                                           for x in ds]})
shown = all_districts.merge(per, on="district", how="left")
geo = districts_geojson()
c1, c2 = st.columns([3, 2])
with c1:
    if geo:
        base = go.Choropleth(geojson=geo, locations=shown["district"], z=[0] * len(shown),
                             featureidkey="properties.shapeName",
                             colorscale=[[0, ui.COLOURS["map_no_data"]], [1, ui.COLOURS["map_no_data"]]],
                             showscale=False, marker_line_color="#999", marker_line_width=0.5,
                             hovertemplate="%{location}: no project<extra></extra>")
        with_data = shown[shown["projects"].notna()]
        layer = go.Choropleth(geojson=geo, locations=with_data["district"], z=with_data["projects"],
                              featureidkey="properties.shapeName",
                              colorscale=[[0, ui.COLOURS["map_low"]], [1, ui.CHART[0]]], marker_line_color="#666",
                              marker_line_width=0.6,
                              colorbar=dict(title=dict(text="Projects", side="right"), thickness=12),
                              hovertemplate="%{location}: %{z:,.0f} projects<extra></extra>")
        fig = go.Figure([base, layer])
        fig.update_geos(fitbounds="locations", visible=False)
        fig.update_layout(height=420, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, width="stretch")
        st.caption("Grey districts have no project in this selection. District boundaries: geoBoundaries "
                   "(Runfola et al. 2020), from Open Data Rwanda / NISR, CC BY 4.0.")
    else:
        st.info("District boundaries are not available, so only the ranked chart is shown.")
with c2:
    fig = px.bar(per.sort_values("projects"), x="projects", y="district", orientation="h", text="projects",
                 labels={"projects": "Projects", "district": ""}, height=300)
    fig.update_traces(marker_color=ui.CHART[0])
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    outside = d.loc[d["outside_rwanda"], "project_code"].unique()
    if len(outside):
        st.caption(f"{len(outside)} project(s) also work outside Rwanda (Goma, DR Congo): "
                   f"{', '.join(outside)}. Only the Rwandan district is mapped.")

ui.table(pd.DataFrame({"Project": d["project_code"], "District": d["district"], "Province": d["province"],
                       "Districts in project": d["districts_in_project"], "Area": d["intervention_area"],
                       "Status": d["status"], "Location (as written)": d["location"]}), "projects_by_district")
if len(missing):
    st.warning(f"{len(missing)} project(s) name no Rwandan district in their location: "
               + ", ".join(missing["project_code"]) + ". They are listed on the Data quality page.")
ui.footer()
