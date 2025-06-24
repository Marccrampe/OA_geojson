import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw
from folium import LayerControl
import geopandas as gpd
import pandas as pd
import io
import json
from shapely.geometry import shape
from shapely.validation import explain_validity
from geopy.geocoders import Nominatim
import base64

# ---------- Load and encode logo ----------
def get_base64_of_bin_file(bin_file_path):
    with open(bin_file_path, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

logo_base64 = get_base64_of_bin_file("openatlas_logo.png")

# ---------- Page config ----------
st.set_page_config(page_title="OpenAtlas GeoJSON Tool", layout="wide")

# ---------- Header ----------
st.markdown(f"""
    <div style='display: flex; align-items: center;'>
        <img src='data:image/png;base64,{logo_base64}' style='height: 60px; margin-right: 20px;'>
        <h2 style='margin: 0;'>Draw or Upload Your Land Area (EUDR-compliant)</h2>
    </div>
    <p>Draw your territory, or upload an Excel/GeoJSON file, and get a validated GeoJSON file.</p>
""", unsafe_allow_html=True)

# ---------- Sidebar search ----------
st.sidebar.subheader("📍 Locate your area")
geocode_input = st.sidebar.text_input("Search a place (optional):")
lat, lon = 0, 0
zoom = 2

if geocode_input:
    geolocator = Nominatim(user_agent="openatlas_locator")
    location = geolocator.geocode(geocode_input)
    if location:
        lat, lon = location.latitude, location.longitude
        zoom = 15
    else:
        st.sidebar.warning("Place not found.")

# ---------- Draw on map ----------
st.subheader("🗺️ Draw your area")

col1, col2 = st.columns([2, 1])

with col1:
    m = folium.Map(
        location=[lat, lon],
        zoom_start=zoom,
        tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
        attr='Google Satellite'
    )

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

    LayerControl().add_to(m)

    output = st_folium(m, height=600, width=1000, returned_objects=["last_active_drawing", "all_drawings"])

# ---------- Geometry validation ----------
st.markdown("---")
st.subheader("✅ Geometry Validation")

file_name_input = st.text_input("Name your file (without extension):", value="your_area")
geojson_str = ""

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
                use_container_width=True,
                type="primary"
            )
        else:
            st.error(f"Invalid geometry: {explain_validity(geom)}")
    except Exception as e:
        st.error(f"Could not parse geometry: {e}")
else:
    st.info("Draw a polygon or rectangle above to enable validation.")

with col2:
    st.markdown("### ✏️ GeoJSON Preview")
    if geojson_str:
        st.code(geojson_str, language='json')

# ---------- File upload ----------
st.markdown("---")
st.subheader("📂 Or upload your file")

uploaded_file = st.file_uploader("Upload an Excel (.xlsx), CSV (.csv), or GeoJSON file", type=["xlsx", "csv", "geojson", "json"])

if uploaded_file:
    try:
        if uploaded_file.name.endswith(".xlsx"):
            df = pd.read_excel(uploaded_file)
        elif uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith(".geojson") or uploaded_file.name.endswith(".json"):
            gdf = gpd.read_file(uploaded_file)
            st.success("GeoJSON file loaded.")
            st.map(gdf)
            geojson_str = gdf.to_json(indent=2)
            st.code(geojson_str, language='json')
            st.download_button(
                "📥 Download Cleaned GeoJSON",
                data=geojson_str,
                file_name=f"{file_name_input}_converted.geojson",
                mime="application/geo+json",
                use_container_width=True
            )
        else:
            st.warning("Unsupported file format.")

        if 'df' in locals():
            if {'latitude', 'longitude'}.issubset(df.columns):
                gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.longitude, df.latitude), crs='EPSG:4326')
                st.map(gdf)
                geojson_str = gdf.to_json(indent=2)
                st.code(geojson_str, language='json')
                st.success("Coordinates loaded and converted to GeoJSON.")
                st.download_button(
                    "📥 Download GeoJSON",
                    data=geojson_str,
                    file_name=f"{file_name_input}_converted.geojson",
                    mime="application/geo+json",
                    use_container_width=True
                )
            else:
                st.warning("Excel or CSV must have 'latitude' and 'longitude' columns.")
    except Exception as e:
        st.error(f"Error processing the file: {e}")