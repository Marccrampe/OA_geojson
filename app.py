import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw, LocateControl, Geocoder
from folium import LayerControl
import geopandas as gpd
import pandas as pd
import io
import json
from shapely.geometry import shape, Polygon
from shapely.validation import explain_validity
import base64
import os

# ---------- Load and encode logo ----------
def get_base64_of_bin_file(bin_file_path):
    if os.path.exists(bin_file_path):
        with open(bin_file_path, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    else:
        return None

logo_base64 = get_base64_of_bin_file("openatlas_logo.png")

# ---------- Page config ----------
st.set_page_config(page_title="OpenAtlas GeoJSON Tool", layout="wide")

# ---------- Session state init ----------
if "clear_trigger" not in st.session_state:
    st.session_state.clear_trigger = False

# ---------- Header ----------
if logo_base64:
    st.markdown(f"""
        <div style='display: flex; align-items: center;'>
            <img src='data:image/png;base64,{logo_base64}' style='height: 60px; margin-right: 20px;'>
            <h2 style='margin: 0;'>Draw or Upload Your Land Area (EUDR-compliant)</h2>
        </div>
        <p>Draw your territory, or upload an Excel/GeoJSON file, and get a validated GeoJSON file.</p>
    """, unsafe_allow_html=True)
else:
    st.markdown("## Draw or Upload Your Land Area (EUDR-compliant)")

# ---------- Controls ----------
col1, col2 = st.columns([1, 3])
with col1:
    if st.button("🗑️ Clear Map"):
        st.session_state.clear_trigger = True
with col2:
    st.markdown("📍 Use the locator button on the map to center on your location.")

# ---------- Draw and map section ----------
st.subheader("🗺️ Draw your area")

m = folium.Map(
    location=[20, 0],
    zoom_start=2,
    control_scale=True,
    tiles=None
)

# Add satellite imagery
folium.raster_layers.TileLayer(
    tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
    name='Google Satellite',
    attr='Google',
    overlay=False,
    control=True,
    opacity=1.0
).add_to(m)

# Add transparent OSM label layer
folium.raster_layers.TileLayer(
    tiles='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    name='Labels (OSM)',
    attr='© OpenStreetMap contributors',
    overlay=True,
    control=True,
    opacity=0.4
).add_to(m)

Draw(
    export=True,
    filename='drawn.geojson',
    draw_options={
        'polygon': True,
        'rectangle': True,
        'polyline': False,
        'circle': False,
        'marker': False,
        'circlemarker': False
    }
).add_to(m)

Geocoder().add_to(m)
LayerControl().add_to(m)
LocateControl(auto_start=False).add_to(m)

output = st_folium(m, height=700, width=1200, returned_objects=["last_active_drawing", "all_drawings"])

if st.session_state.clear_trigger:
    output = {"last_active_drawing": None, "all_drawings": []}
    st.session_state.clear_trigger = False

# Zoom on drawn geometry if present
if output and output.get("last_active_drawing"):
    try:
        feature = output["last_active_drawing"]
        geom = shape(feature["geometry"])
        bounds = geom.bounds
        m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])
    except Exception as e:
        st.warning("Could not zoom to geometry.")

# ---------- Geometry validation ----------
st.subheader("✅ Geometry Validation")

file_name_input = st.text_input("Name your file (without extension):", value="your_area")
geojson_str = ""
geojson_placeholder = st.empty()

if output and output.get("last_active_drawing"):
    try:
        geojson_obj = {
            "type": "FeatureCollection",
            "features": [output["last_active_drawing"]]
        }
        geom = shape(output["last_active_drawing"]["geometry"])
        if geom.is_valid:
            st.success("Geometry is valid!")
            geojson_str = json.dumps(geojson_obj, indent=2)
            st.download_button(
                "📥 Download GeoJSON",
                data=geojson_str,
                file_name=f"{file_name_input}.geojson",
                mime="application/geo+json",
                use_container_width=True
            )
            with st.expander("📄 View GeoJSON content"):
                geojson_placeholder.code(geojson_str, language='json')
        else:
            st.error(f"Invalid geometry: {explain_validity(geom)}")
    except Exception as e:
        st.error(f"Could not parse geometry: {e}")
else:
    st.info("Draw a polygon or rectangle above to enable validation.")

# ---------- File upload ----------
st.markdown("---")
st.subheader("📂 Or upload your file")

uploaded_file = st.file_uploader("Upload an Excel (.xlsx), CSV (.csv), or GeoJSON file", type=["xlsx", "csv", "geojson", "json"])

if uploaded_file:
    try:
        gdf = None
        if uploaded_file.name.endswith(".xlsx"):
            df = pd.read_excel(uploaded_file)
            if {'latitude', 'longitude'}.issubset(df.columns):
                gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.longitude, df.latitude), crs='EPSG:4326')
            else:
                coords = df[['longitude', 'latitude']].values.tolist()
                if len(coords) >= 3:
                    coords.append(coords[0])
                    poly = Polygon(coords)
                    gdf = gpd.GeoDataFrame(index=[0], crs='EPSG:4326', geometry=[poly])
                else:
                    st.warning("Not enough points to form a polygon.")

        elif uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
            if {'latitude', 'longitude'}.issubset(df.columns):
                gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.longitude, df.latitude), crs='EPSG:4326')
            else:
                coords = df[['longitude', 'latitude']].values.tolist()
                if len(coords) >= 3:
                    coords.append(coords[0])
                    poly = Polygon(coords)
                    gdf = gpd.GeoDataFrame(index=[0], crs='EPSG:4326', geometry=[poly])
                else:
                    st.warning("Not enough points to form a polygon.")

        elif uploaded_file.name.endswith(".geojson") or uploaded_file.name.endswith(".json"):
            gdf = gpd.read_file(uploaded_file)

        if gdf is not None:
            st.success("File loaded successfully.")
            geojson_str = gdf.to_json(indent=2)
            st.download_button(
                "📥 Download Cleaned GeoJSON",
                data=geojson_str,
                file_name=f"{file_name_input}_converted.geojson",
                mime="application/geo+json",
                use_container_width=True
            )
            with st.expander("📄 View GeoJSON content"):
                geojson_placeholder.code(geojson_str, language='json')
    except Exception as e:
        st.error(f"Error processing the file: {e}")
