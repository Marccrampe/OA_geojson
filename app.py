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

# ---------- Tabs ----------
tabs = st.tabs(["🖊️ Draw Tool", "📤 Upload from File"])

# ----------------------- TAB 1: DRAW TOOL ---------------------------
with tabs[0]:
    col1, col2 = st.columns([1, 1])
    with col1:
        clear_map = st.button("🗑️ Clear Map")
    with col2:
        locate_me = st.button("📍 Center on My Location")

    if "map_center" not in st.session_state:
        st.session_state.map_center = [20, 0]
        st.session_state.zoom = 2
    if "drawings" not in st.session_state:
        st.session_state.drawings = []

    if locate_me:
        st.session_state.map_center = [0, 0]
        st.session_state.zoom = 12

    if clear_map:
        st.session_state.drawings = []

    st.subheader("🗺️ Draw your area")

    m = folium.Map(
        location=st.session_state.map_center,
        zoom_start=st.session_state.zoom,
        control_scale=True,
        tiles=None
    )

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

    Geocoder(add_marker=False, collapsed=True).add_to(m)
    LayerControl().add_to(m)
    LocateControl().add_to(m)

    output = st_folium(m, height=700, width=1200, returned_objects=["last_active_drawing", "all_drawings"])

    if output and output.get("last_active_drawing") and not clear_map:
        st.session_state.drawings = [output["last_active_drawing"]]

    st.subheader("✅ Geometry Validation")

    file_name_input = st.text_input("Name your file (without extension):", value="your_area")
    geojson_str = ""
    geojson_placeholder = st.empty()

    if st.session_state.drawings:
        try:
            geojson_obj = {
                "type": "FeatureCollection",
                "features": st.session_state.drawings
            }
            geom = shape(st.session_state.drawings[0]["geometry"])
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

# ---------------------- TAB 2: UPLOAD & COMPARE ---------------------
with tabs[1]:
    st.subheader("📂 Upload and Compare")

    uploaded_file = st.file_uploader("Upload an Excel (.xlsx), CSV (.csv), or GeoJSON file", type=["xlsx", "csv", "geojson", "json"])
    file_name_input = st.text_input("Name your exported file (without extension):", value="uploaded_area")

    modify_mode = st.checkbox("✏️ Modify the polygon after upload?")

    if uploaded_file:
        try:
            gdf = None
            if uploaded_file.name.endswith(".xlsx"):
                df = pd.read_excel(uploaded_file)
                coords = df[['longitude', 'latitude']].values.tolist()
                if len(coords) >= 3:
                    coords.append(coords[0])
                    poly = Polygon(coords)
                    gdf = gpd.GeoDataFrame(index=[0], crs='EPSG:4326', geometry=[poly])
            elif uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
                coords = df[['longitude', 'latitude']].values.tolist()
                if len(coords) >= 3:
                    coords.append(coords[0])
                    poly = Polygon(coords)
                    gdf = gpd.GeoDataFrame(index=[0], crs='EPSG:4326', geometry=[poly])
            elif uploaded_file.name.endswith(".geojson") or uploaded_file.name.endswith(".json"):
                gdf = gpd.read_file(uploaded_file)

            if gdf is not None:
                st.success("File loaded successfully.")
                geojson_str = gdf.to_json(indent=2)

                bounds = gdf.total_bounds
                center = [
                    (bounds[1] + bounds[3]) / 2,
                    (bounds[0] + bounds[2]) / 2
                ]
                zoom = 16 if (bounds[2] - bounds[0] < 0.1 and bounds[3] - bounds[1] < 0.1) else 12

                if modify_mode:
                    col1, col2 = st.columns(2)
                    for col, color, title in zip([col1, col2], ["red", "green"], ["**Original Polygon** (Red)", "**Draw New Polygon** (Green)"]):
                        col.markdown(title)
                        map_obj = folium.Map(location=center, zoom_start=zoom, control_scale=True, tiles=None)
                        folium.TileLayer('https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', name='Google Satellite', attr='Google').add_to(map_obj)
                        folium.TileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', name='Labels (OSM)', attr='© OpenStreetMap contributors', opacity=0.3).add_to(map_obj)
                        if color == "red":
                            folium.GeoJson(gdf, name="Original", style_function=lambda x: {"color": "red"}).add_to(map_obj)
                            st_folium(map_obj, height=500, width=550)
                        else:
                            Draw(
                                export=True,
                                filename='modified.geojson',
                                draw_options={
                                    'polygon': True,
                                    'rectangle': True,
                                    'polyline': False,
                                    'circle': False,
                                    'marker': False,
                                    'circlemarker': False
                                }
                            ).add_to(map_obj)
                            LayerControl().add_to(map_obj)
                            LocateControl().add_to(map_obj)
                            output_new = st_folium(map_obj, height=500, width=550, returned_objects=["last_active_drawing"])

                    final_geojson = geojson_str
                    if output_new and output_new.get("last_active_drawing"):
                        new_geojson_obj = {
                            "type": "FeatureCollection",
                            "features": [output_new["last_active_drawing"]]
                        }
                        final_geojson = json.dumps(new_geojson_obj, indent=2)
                        st.success("New polygon drawn. You can now export it.")

                    st.download_button(
                        "📥 Download Final GeoJSON",
                        data=final_geojson,
                        file_name=f"{file_name_input}_final.geojson",
                        mime="application/geo+json",
                        use_container_width=True
                    )

                    with st.expander("📄 View Final GeoJSON content"):
                        st.code(final_geojson, language='json')
                else:
                    map_obj = folium.Map(location=center, zoom_start=zoom, control_scale=True, tiles=None)
                    folium.TileLayer('https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', name='Google Satellite', attr='Google').add_to(map_obj)
                    folium.TileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', name='Labels (OSM)', attr='© OpenStreetMap contributors', opacity=0.3).add_to(map_obj)
                    folium.GeoJson(gdf, name="Uploaded", style_function=lambda x: {"color": "blue"}).add_to(map_obj)
                    st_folium(map_obj, height=600, width=1100)

                    st.download_button(
                        "📥 Download GeoJSON",
                        data=geojson_str,
                        file_name=f"{file_name_input}.geojson",
                        mime="application/geo+json",
                        use_container_width=True
                    )

                    with st.expander("📄 View GeoJSON content"):
                        st.code(geojson_str, language='json')

        except Exception as e:
            st.error(f"Error processing the file: {e}")
