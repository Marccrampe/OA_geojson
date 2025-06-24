import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw, LocateControl, Geocoder
from folium import LayerControl, MacroElement
from jinja2 import Template
import json
from shapely.geometry import shape
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
tabs = st.tabs(["🖊️ Draw Tool", "📄 Upload from File"])

# ----------------------- TAB 1: DRAW TOOL ---------------------------
with tabs[0]:
    if "drawings" not in st.session_state:
        st.session_state.drawings = []

    st.subheader("🗺️ Draw your area")

    m = folium.Map(
        location=[20, 0],
        zoom_start=2,
        control_scale=True,
        tiles=None
    )

    folium.raster_layers.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
        name='Google Satellite',
        attr='Google',
        overlay=False,
        control=True
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

    Geocoder().add_to(m)
    LayerControl().add_to(m)
    LocateControl(auto_start=False).add_to(m)

    # Custom locate button
    locate_js = Template("""
        {% macro script(this, kwargs) %}
        var locateBtn = L.control({position: 'topleft'});
        locateBtn.onAdd = function(map) {
            var div = L.DomUtil.create('div', 'leaflet-bar leaflet-control leaflet-control-custom');
            div.innerHTML = '<button title="Center map on your location">📍 Center</button>';
            div.style.backgroundColor = 'white';
            div.style.padding = '5px';
            div.style.cursor = 'pointer';
            div.onclick = function(){
                map.eachLayer(function(layer){
                    if(layer._event === 'locationfound'){ return; }
                    if(layer._locateOptions){
                        layer.start();
                    }
                });
            };
            return div;
        }
        locateBtn.addTo({{this._parent.get_name()}});
        {% endmacro %}
    """)

    # Custom clear button
    clear_js = Template("""
        {% macro script(this, kwargs) %}
        var clearBtn = L.control({position: 'topleft'});
        clearBtn.onAdd = function(map) {
            var div = L.DomUtil.create('div', 'leaflet-bar leaflet-control leaflet-control-custom');
            div.innerHTML = '<button title="Clear all drawings">🗑️ Clear</button>';
            div.style.backgroundColor = 'white';
            div.style.padding = '5px';
            div.style.cursor = 'pointer';
            div.onclick = function(){
                map.eachLayer(function(layer){
                    if(layer instanceof L.FeatureGroup){
                        layer.clearLayers();
                    }
                });
            };
            return div;
        }
        clearBtn.addTo({{this._parent.get_name()}});
        {% endmacro %}
    """)

    class CustomJSControl(MacroElement):
        def __init__(self, template):
            super().__init__()
            self._template = template

    m.get_root().add_child(CustomJSControl(locate_js))
    m.get_root().add_child(CustomJSControl(clear_js))

    output = st_folium(m, height=700, width=1200, returned_objects=["last_active_drawing", "all_drawings"])

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
                    "📅 Download GeoJSON",
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
