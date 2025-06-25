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
import streamlit.components.v1 as components


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
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');

        html, body, .stApp {
            background-color: #121212;
            font-family: 'Inter', sans-serif;
            color: white;
        }

        h1, h2, h3, h4 {
            color: white;
            font-weight: 600;
        }

        .stButton>button,
        .stDownloadButton>button {
            background-color: #4A90E2 !important; /* light blue */
            color: white;
            border: none;
            border-radius: 12px;
            padding: 0.75em 1.5em;
            font-weight: 600;
            transition: background-color 0.3s ease;
        }
        .stButton>button:hover,
        .stDownloadButton>button:hover {
            background-color: #357ABD !important;
        }

        .stTextInput>div>div>input {
            border: 1px solid #cccccc;
            border-radius: 8px;
            padding: 0.5em;
            color: black;
        }

        .stTabs [data-baseweb="tab"] {
            font-size: 16px;
            font-weight: 600;
            color: #4A1CFC;
        }

        .css-1cpxqw2, .css-1d391kg, .stColumn {
            background-color: #1e1e1e;
            border-radius: 12px;
            padding: 1rem;
        }

        .stExpanderHeader {
            font-weight: 600;
        }

        /* White top banner */
        .top-banner {
            width: 100%;
            background-color: white;
            padding: 1.2rem 2rem;
            margin-bottom: 1.5rem;
            color: #4A1CFC;
            font-size: 22px;
            font-weight: 700;
            text-align: left;
            border-radius: 0 0 12px 12px;
            display: flex;
            align-items: center;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        .stTextInput input {
        color: white !important;
        background-color: #1e1e1e !important;
        border: 1px solid #4A90E2 !important;
}

    </style>
""", unsafe_allow_html=True)

# ---------- Top Banner ----------
st.markdown(f"""
    <div class='top-banner'>
        <img src='data:image/png;base64,{logo_base64}' style='height: 40px; margin-right: 15px;'>
        OpenAtlas GeoJSON Tool – Define, Edit and Validate Land Parcels
    </div>
""", unsafe_allow_html=True)

# ---------- Header ----------
if logo_base64:
    st.markdown(f"""
        <div style='background-color: #1e1e1e; padding: 1.5rem; border-radius: 12px;'>
            <h2 style='margin-top: 0;'>What is the OpenAtlas GeoJSON Tool?</h2>
            <p style='font-size: 16px; line-height: 1.6;'>
                The OpenAtlas GeoJSON Tool allows users to easily define, draw, or upload land parcels in a structured GeoJSON format.
                This interface is part of the OpenAtlas VANTAGE suite and is specifically designed to support EUDR compliance workflows.
                Whether you're mapping agricultural plots, forest boundaries, or land concessions, this tool ensures your geometries are validated and exportable in a standard format.
            </p>
        </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("## Define, Edit and Validate Land Areas for EUDR Compliance")

# ---------- Tabs ----------

st.markdown("""
    <style>
        .stTabs [data-baseweb="tab"] {
            font-size: 24px !important;
            font-weight: 900 !important;
            color: #4A90E2 !important;
            padding: 1.5rem 2.5rem !important;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 8px solid transparent;
        }
        .stTabs [data-baseweb="tab"]:hover {
            background-color: #1e1e1e !important;
            color: #4A90E2 !important;
        }
        .stTabs [aria-selected="true"] {
            color: #ffffff !important;
            background-color: #4A90E2 !important;
            border-bottom: 8px solid #4A90E2 !important;
        }
    </style>
""", unsafe_allow_html=True)

tabs = st.tabs(["🖊️ Draw Tool", "📤 Upload from File", "📘 User Guide"])

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

    if clear_map:
        st.session_state.drawings = []

    st.subheader("🗺️ Draw your area")

    m = folium.Map(
        location=st.session_state.map_center if isinstance(st.session_state.map_center, list) else [20, 0],
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
            'polygon': {
                'shapeOptions': {
                    'color': 'green',  # Change polygon stroke color here
                    'fillColor': 'green',
                    'fillOpacity': 0.3
                }
            },
            'rectangle': {
                'shapeOptions': {
                    'color': 'green',
                    'fillColor': 'green',
                    'fillOpacity': 0.3
                }
            },
            'polyline': False,
            'circle': False,
            'marker': False,
            'circlemarker': False
        },
        edit_options={"edit": False, "remove": False}  # prevent multi-edit/removal
    ).add_to(m)

    Geocoder(add_marker=False, collapsed=True).add_to(m)
    LayerControl().add_to(m)

    # Inject custom JS only once to locate if needed
    if st.session_state.map_center == "locate":
        class JSLocateInit(MacroElement):
            _template = Template("""
            {% macro script(this, kwargs) %}
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(function(pos) {
                    const map = window.map;
                    if (map) {
                        map.setView([pos.coords.latitude, pos.coords.longitude], 15);
                    }
                });
            }
            {% endmacro %}
            """)
        m.add_child(JSLocateInit())
        st.session_state.map_center = [20, 0]  # Reset after locate
    if locate_me:
        st.session_state.map_center = "locate"

    output = st_folium(m, height=700, width=1200, returned_objects=["last_active_drawing"])

    if output and output.get("last_active_drawing"):
        st.session_state.drawings = [output["last_active_drawing"]]
        # Replace previous drawing only
        # (no rerun to preserve current map state)

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

                    with col1:
                        st.markdown("**Original Polygon** (Red)")
                        map_orig = folium.Map(location=center, zoom_start=zoom, control_scale=True, tiles=None)
                        folium.TileLayer('https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', name='Google Satellite', attr='Google').add_to(map_orig)
                        folium.TileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', name='Labels (OSM)', attr='© OpenStreetMap contributors', opacity=0.3).add_to(map_orig)
                        folium.GeoJson(gdf, name="Original", style_function=lambda x: {"color": "red"}).add_to(map_orig)
                        st_folium(map_orig, height=500, width=550)

                    with col2:
                        st.markdown("**Draw New Polygon** (Green)")
                        map_draw = folium.Map(location=center, zoom_start=zoom, control_scale=True, tiles=None)
                        folium.TileLayer('https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', name='Google Satellite', attr='Google').add_to(map_draw)
                        folium.TileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', name='Labels (OSM)', attr='© OpenStreetMap contributors', opacity=0.3).add_to(map_draw)
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
                        ).add_to(map_draw)
                        LayerControl().add_to(map_draw)
                        LocateControl().add_to(map_draw)
                        output_new = st_folium(map_draw, height=500, width=550, returned_objects=["last_active_drawing"])

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
        except Exception as e:
            st.error(f"Error processing the file: {e}")


    
# ---- Tab 3: User Guide ----
with tabs[2]:
    st.markdown("### 📘 OpenAtlas User Guide – Full Viewer")

    pdf_raw_url = "https://raw.githubusercontent.com/Marccrampe/OA_geojson/main/Geojson_guide.pdf"
    viewer_url = f"https://mozilla.github.io/pdf.js/web/viewer.html?file={pdf_raw_url}"

    st.components.v1.html(
        f'<iframe src="{viewer_url}" width="100%" height="800px" style="border: none;"></iframe>',
        height=800
    )

    st.download_button("📥 Download the full User Guide (PDF)", pdf_raw_url, file_name="Geojson_guide.pdf")


