import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw, LocateControl, Geocoder
from folium import LayerControl, MacroElement
from jinja2 import Template
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
        geoloc_trigger = st.button("📍 Center on My Location")

    if "map_center" not in st.session_state:
        st.session_state.map_center = [20, 0]
        st.session_state.zoom = 2
    if "drawings" not in st.session_state:
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

    draw_plugin = Draw(
        export=True,
        filename='drawn.geojson',
        draw_options={
            'polygon': True,
            'rectangle': True,
            'polyline': False,
            'circle': False,
            'marker': False,
            'circlemarker': False
        },
        edit_options={'edit': True, 'remove': True}
    )
    draw_plugin.add_to(m)

    Geocoder().add_to(m)
    LayerControl().add_to(m)
    LocateControl().add_to(m)

    # Inject JS to simulate click on clear all (no refresh)
    if clear_map:
        class ClearDrawJS(MacroElement):
            _template = Template("""
                {% macro script(this, kwargs) %}
                setTimeout(function() {
                    const removeBtn = document.querySelector('.leaflet-draw-edit-remove');
                    if (removeBtn) removeBtn.click();
                    if (window._leaflet_drawnItems) {
                        window._leaflet_drawnItems.clearLayers();
                    }
                }, 300);
                {% endmacro %}
            """)
        m.add_child(ClearDrawJS())

    # Inject JS to simulate click on LocateControl
    if geoloc_trigger:
        class ClickLocateControlJS(MacroElement):
            _template = Template("""
                {% macro script(this, kwargs) %}
                setTimeout(function() {
                    let locateBtn = document.querySelector('.leaflet-control-locate a');
                    if (locateBtn) locateBtn.click();
                }, 300);
                {% endmacro %}
            """)
        m.add_child(ClickLocateControlJS())

    output = st_folium(
        m,
        height=700,
        width=1200,
        returned_objects=["last_active_drawing", "all_drawings"]
    )

    if output and output.get("last_active_drawing"):
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
