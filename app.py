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
from geopy.geocoders import Nominatim
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

logo_base64 = get_base64_of_bin_file("open-atlas-logo.png")

# ---------- Page config ----------
st.set_page_config(page_title="OpenAtlas GeoJSON Tool", layout="wide")

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

# ---------- Sidebar search ----------
st.sidebar.subheader("📍 Locate your area")
geocode_input = st.sidebar.text_input("Search a place (optional):")
lat, lon = 20, 0
zoom = 2

if geocode_input:
    geolocator = Nominatim(user_agent="openatlas_locator")
    location = geolocator.geocode(geocode_input)
    if location:
        lat, lon = location.latitude, location.longitude
        zoom = 12
    else:
        st.sidebar.warning("Place not found.")

# ---------- Draw and map section ----------
st.subheader("🗺️ Draw your area")

clear_map = st.button("🗑️ Clear Map")

m = folium.Map(
    location=[lat, lon],
    zoom_start=zoom,
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
    opacity=0.2
).add_to(m)

if not clear_map:
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
LocateControl().add_to(m)

output = st_folium(m, height=650, width=1100, returned_objects=["last_active_drawing", "all_drawings"])

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
            df = pd.read_excel(uploaded_file, engine="openpyxl")
            if {'latitude', 'longitude'}.issubset(df.columns):
                coords = list(zip(df['longitude'], df['latitude']))
                if coords[0] != coords[-1]:
                    coords.append(coords[0])
                polygon = Polygon(coords)
                gdf = gpd.GeoDataFrame(index=[0], geometry=[polygon], crs='EPSG:4326')
            else:
                st.warning("Excel must have 'latitude' and 'longitude' columns.")
        elif uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
            if {'latitude', 'longitude'}.issubset(df.columns):
                coords = list(zip(df['longitude'], df['latitude']))
                if coords[0] != coords[-1]:
                    coords.append(coords[0])
                polygon = Polygon(coords)
                gdf = gpd.GeoDataFrame(index=[0], geometry=[polygon], crs='EPSG:4326')
            else:
                st.warning("CSV must have 'latitude' and 'longitude' columns.")
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
            m = folium.Map(location=[gdf.geometry[0].centroid.y, gdf.geometry[0].centroid.x],
                           zoom_start=14, control_scale=True, tiles=None)
            folium.raster_layers.TileLayer(
                tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
                name='Google Satellite',
                attr='Google',
                overlay=False,
                control=True,
                opacity=1.0
            ).add_to(m)
            folium.raster_layers.TileLayer(
                tiles='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
                name='Labels (OSM)',
                attr='© OpenStreetMap contributors',
                overlay=True,
                control=True,
                opacity=0.4
            ).add_to(m)
            folium.GeoJson(data=geojson_str, name="Uploaded Geometry").add_to(m)
            LayerControl().add_to(m)
            st_folium(m, height=650, width=1100)
            with st.expander("📄 View GeoJSON content"):
                geojson_placeholder.code(geojson_str, language='json')
    except Exception as e:
        st.error(f"Error processing the file: {e}")
