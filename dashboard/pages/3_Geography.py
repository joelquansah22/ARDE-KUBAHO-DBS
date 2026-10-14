"""Geography: results by district, on a map of Rwanda's districts and as a ranked bar chart."""

import json

import pandas as pd
import plotly.express as px
import streamlit as st

import ui

f = ui.filters()
cat = ui.catalogue()
projects = f.project_ids
st.title("Geography")
st.markdown(f"<div class='muted'>{f.start:%d %b %Y} to {f.end:%d %b %Y} · {f.scope_text}</div>", unsafe_allow_html=True)

GEOJSON = ui.ROOT / "config" / "reference" / "geo" / "geoBoundaries-RWA-ADM2_simplified.geojson"


def _clockwise(ring: list) -> list:
    """Plotly's map drawing (d3) wants the outer edge of each shape to run clockwise; the GeoJSON standard
    (which geoBoundaries follows) runs it the other way, which leaves the map blank. Reverse when needed."""
    area = sum(x1 * y2 - x2 * y1 for (x1, y1, *_), (x2, y2, *_) in zip(ring, ring[1:] + ring[:1]))
    return ring[::-1] if area > 0 else ring


@st.cache_data(show_spinner=False)
def districts_geojson():
    if not GEOJSON.exists():
        return None
    geo = json.loads(GEOJSON.read_text(encoding="utf-8"))
    for feature in geo["features"]:
        g = feature["geometry"]
        polygons = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        for polygon in polygons:
            polygon[0] = _clockwise(polygon[0])                                  # outer edge
            for i in range(1, len(polygon)):                                     # holes run the other way
                polygon[i] = _clockwise(polygon[i])[::-1]
    return geo


reported = [c for c, i in cat.items() if "reported" in i.get("calculation", {}) and i["availability"] == "available"]
measures = ["People reached (different people, by registration district)", "Activities completed",
            "Activity spending"] + [f"{c}: {cat[c]['name']} (reported)" for c in reported]
measure = st.selectbox("Show", measures, key="geo_measure")
sex_clause, sex_params = ("AND b.sex = ?", [f.sex]) if f.sex else ("", [])

if measure.startswith("People"):
    data = ui.query(f"""SELECT l.district, COUNT(DISTINCT s.beneficiary_key) AS value,
                               COUNT(DISTINCT CASE WHEN b.pending_duplicate_review THEN s.beneficiary_key END) AS pending
                        FROM fact_beneficiary_service s JOIN dim_activity a USING (activity_id)
                        JOIN dim_beneficiary b USING (beneficiary_key) JOIN dim_location l ON l.location_id = b.location_id
                        WHERE a.project_id IN {ui.in_list(projects)} AND s.date BETWEEN ? AND ? {sex_clause}
                        GROUP BY 1""", *projects, f.start, f.end, *sex_params)
    label = "People reached"
    note = (f"Includes {int(data['pending'].sum())} people pending duplicate review." if data["pending"].sum() else "")
elif measure.startswith("Activities") or measure.startswith("Activity spending"):
    col = "COUNT(*)" if measure.startswith("Activities") else "SUM(f.cost_rwf)"
    data = ui.query(f"""SELECT l.district, {col} AS value FROM fact_activity f JOIN dim_activity a USING (activity_id)
                        JOIN dim_location l USING (location_id)
                        WHERE a.project_id IN {ui.in_list(projects)} AND f.status IN ('completed','delayed')
                          AND f.date BETWEEN ? AND ? GROUP BY 1""", *projects, f.start, f.end)
    label = "Activities completed" if measure.startswith("Activities") else "Spending (RWF)"
    note = ""
else:
    code = measure.split(":")[0]
    agg = cat[code].get("aggregation", "sum")
    data = ui.query(f"""SELECT district, project_id, period_start, actual FROM indicator_values
                        WHERE indicator_code = ? AND source = 'reported' AND period_type = 'month' AND district <> 'All'
                          AND project_id IN {ui.in_list(projects)} AND disaggregation = ?
                          AND period_start BETWEEN ? AND ?""",
                    code, *projects, f"sex={f.sex}" if f.sex and cat[code]["disaggregation"] == "sex" else "total",
                    f.start, f.end)
    if agg == "latest":      # a snapshot: the latest month for each project, then add the projects up
        data = data.sort_values("period_start").groupby(["district", "project_id"]).tail(1)
    data = data.groupby("district", as_index=False)["actual"].sum().rename(columns={"actual": "value"})
    label = cat[code]["name"]
    note = f"Monthly reported values {'(latest month)' if agg == 'latest' else 'added up'} over the date range."

all_districts = pd.DataFrame({"district": [d for ds in ui.load_yaml("reference/rwanda_admin.yaml")["provinces"].values()
                                           for d in ds]})
shown = all_districts.merge(data[["district", "value"]], on="district", how="left")
geo = districts_geojson()
c1, c2 = st.columns([3, 2])
with c1:
    if geo:
        import plotly.graph_objects as go
        base = go.Choropleth(geojson=geo, locations=shown["district"], z=[0] * len(shown),
                             featureidkey="properties.shapeName", colorscale=[[0, "#eeeeee"], [1, "#eeeeee"]],
                             showscale=False, marker_line_color="#999", marker_line_width=0.5,
                             hovertemplate="%{location}: no data<extra></extra>")
        with_data = shown[shown["value"].notna()]
        layer = go.Choropleth(geojson=geo, locations=with_data["district"], z=with_data["value"],
                              featureidkey="properties.shapeName", colorscale="Blues", marker_line_color="#666",
                              marker_line_width=0.6, colorbar=dict(title=dict(text=label, side="right"), thickness=12),
                              hovertemplate="%{location}: %{z:,.0f}<extra></extra>")
        fig = go.Figure([base, layer])
        fig.update_geos(fitbounds="locations", visible=False)
        fig.update_layout(height=430, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, width="stretch")
        st.caption("Grey districts have no data in this selection. District boundaries: geoBoundaries "
                   "(Runfola et al. 2020), from Open Data Rwanda / NISR, CC BY 4.0.")
    else:
        st.info("District boundaries are not available, so only the ranked chart is shown.")
with c2:
    ranked = data.sort_values("value", ascending=True)
    fig = px.bar(ranked, x="value", y="district", orientation="h", text="value", labels={"value": label, "district": ""})
    fig.update_traces(marker_color="#1f6f8b", texttemplate="%{text:,.0f}")
    fig.update_layout(height=430, margin=dict(l=0, r=10, t=10, b=0))
    st.plotly_chart(fig, width="stretch")
if note:
    st.caption(note)
ui.table(data.sort_values("value", ascending=False).rename(columns={"district": "District", "value": label}),
         "geography_by_district")
