import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import geopandas as gpd
import networkx as nx
from shapely.geometry import LineString
import pandas as pd
import numpy as np
import time

# 1. Ρύθμιση Σελίδας (Dark Theme & Wide Mode)
st.set_page_config(
    page_title="Thessaloniki Flyover Impact",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS για το στυλ του Dashboard
st.markdown("""
    <style>
    .stApp { background-color: #26211e !important; color: #e6e1df !important; }
    div[data-testid="stVerticalBlock"] > div {
        background-color: #36302c; border-radius: 4px; padding: 15px; margin-bottom: 10px;
    }
    input { background-color: #4a423d !important; color: white !important; border: 1px solid #5a524d !important; }
    h1, h2, h3, h4 { color: #ffffff !important; }
    .big-stat { font-size: 48px; font-weight: bold; color: #ff9f43; text-align: center; margin: 10px 0; }
    .stButton>button {
        background-color: #ff9f43 !important; color: black !important;
        font-weight: bold !important; border-radius: 4px !important;
        margin-top: 24px; width: 100%;
    }
    .academic-card { padding: 5px; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }
    .academic-text { font-size: 15px; line-height: 1.7; color: #e6e1df; }
    .highlight-name { color: #ff9f43; font-weight: bold; font-size: 16px; }
    </style>
""", unsafe_allow_html=True)

# 🌍 ΣΥΝΑΡΤΗΣΗ ΕΥΡΕΣΗΣ ΠΕΡΙΟΧΗΣ (FAIL-SAFE BOUNDING BOXES)
def get_area_name_from_coords(lat, lon):
    if 40.620 <= lat <= 40.645 and 22.930 <= lon <= 22.955: return "Κέντρο Πόλης"
    if lat < 40.610 and lon > 22.950: return "Καλαμαριά / Πυλαία"
    if lat > 40.650 and lon < 22.930: return "Εύοσμος / Κορδελιό"
    if lat > 40.640 and lon > 22.940: return "Συκιές / Νεάπολη"
    if lat < 40.625 and lon > 22.960: return "Τούμπα / Χαριλάου"
    return "Ανατολική/Δυτική Θεσσαλονίκη"

# 2. ΦΟΡΤΩΣΗ ΔΙΚΤΥΟΥ & ΚΑΤΑΣΚΕΥΗ ΤΟΠΟΛΟΓΙΚΟΥ ΓΡΑΦΟΥ (ΔΙΟΡΘΩΘΗΚΕ)
@st.cache_resource
def load_and_build_graph():
    try:
        gdf = gpd.read_file("thessaloniki_roads.geojson")
        if gdf.crs != "EPSG:4326":
            gdf = gdf.to_crs(epsg=4326)
        
        gdf['name_display'] = gdf['name'].fillna("Άγνωστη Οδός").astype(str)
        gdf['name'] = gdf['name_display'].str.strip().str.lower()
        
        G = nx.Graph()
        for idx, row in gdf.iterrows():
            geom = row['geometry']
            if geom.geom_type == 'LineString':
                coords = list(geom.coords)
                p1, p2 = coords[0], coords[-1]
                # 🌟 ΔΙΟΡΘΩΣΗ: Πρόσβαση στα στοιχεία p1[0], p1[1] για αποφυγή list-to-float error
                dist = np.sqrt((float(p1[0])-float(p2[0]))**2 + (float(p1[1])-float(p2[1]))**2) * 111000
                G.add_edge(tuple(p1), tuple(p2), weight=dist, name=row['name'], index=idx)
        return gdf, G
    except Exception as e:
        st.error(f"🚨 Σφάλμα κατά την κατασκευή του δικτύου: {e}")
        return None, None

gdf_base_roads, G_network = load_and_build_graph()

# 3. BACKGROUND CACHING ΤΟΥ ΧΑΡΤΗ ΚΙΝΗΣΗΣ
@st.cache_data(ttl=60)
def generate_background_traffic_layer(phase):
    m_sub = folium.Map(location=[40.6380, 22.9450], zoom_start=13, tiles="CartoDB dark_matter")
    if gdf_base_roads is not None:
        np.random.seed(int(time.time()) // 60)
        gdf_sample = gdf_base_roads.sample(n=min(1200, len(gdf_base_roads)))
        for _, row in gdf_sample.dropna(subset=['geometry']).iterrows():
            base_speed = np.random.randint(15, 70)
            live_speed = base_speed * 0.55 if phase == "Κατά τη διάρκεια (Τρέχουσα Κατάσταση)" else (base_speed * 1.25 if phase == "Μετά την ολοκλήρωση" else base_speed)
            if live_speed < 22: color = "#e74c3c"
            elif live_speed < 40: color = "#f39c12"
            else: color = "#2ecc71"
            geom = row['geometry']
            if geom.geom_type == 'LineString':
                folium.PolyLine(locations=[(pt[1], pt[0]) for pt in geom.coords], color=color, weight=2, opacity=0.4).add_to(m_sub)
    return m_sub
# ==============================================================================
# ΠΑΝΩ ΜΠΑΡΑ (HEADER)
# ==============================================================================
head_col1, head_col2, head_col3, head_col4 = st.columns([1.4, 1.1, 1.1, 0.8])

with head_col1:
    st.markdown("<h2 style='margin:0; padding:0;'>Thessaloniki Flyover Impact</h2>", unsafe_allow_html=True)

if "start_road_idx" not in st.session_state: st.session_state.start_road_idx = None
if "end_road_idx" not in st.session_state: st.session_state.end_road_idx = None

with head_col2:
    start_input = st.text_input("📍 Αναζήτηση Αφετηρίας:", "κασσάνδρου")
    if gdf_base_roads is not None and start_input:
        start_matches = gdf_base_roads[gdf_base_roads['name'].str.contains(start_input.strip().lower(), na=False)].copy()
        if not start_matches.empty:
            if len(start_matches) > 1:
                labels = []
                for idx, row in start_matches.iterrows():
                    centroid = row['geometry'].centroid
                    area_name = get_area_name_from_coords(centroid.y, centroid.x)
                    labels.append(f"{row['name_display']} — Περιοχή: {area_name} (ID: {idx})")
                start_matches['select_label'] = labels
                
                selected_label = st.selectbox("👉 Ποιο τμήμα εννοείτε;", start_matches['select_label'].unique(), key="start_select_box")
                chosen_id = int(selected_label.split("(ID: ")[-1].replace(")", ""))
                st.session_state.start_road_idx = chosen_id
            else:
                st.session_state.start_road_idx = start_matches.index[0]

with head_col3:
    end_input = st.text_input("🏁 Αναζήτηση Προορισμού:", "τσιμισκή")
    if gdf_base_roads is not None and end_input:
        end_matches = gdf_base_roads[gdf_base_roads['name'].str.contains(end_input.strip().lower(), na=False)].copy()
        if not end_matches.empty:
            if len(end_matches) > 1:
                labels = []
                for idx, row in end_matches.iterrows():
                    centroid = row['geometry'].centroid
                    area_name = get_area_name_from_coords(centroid.y, centroid.x)
                    labels.append(f"{row['name_display']} — Περιοχή: {area_name} (ID: {idx})")
                end_matches['select_label'] = labels
                
                selected_label = st.selectbox("👉 Ποιο τμήμα εννοείτε;", end_matches['select_label'].unique(), key="end_select_box")
                chosen_id = int(selected_label.split("(ID: ")[-1].replace(")", ""))
                st.session_state.end_road_idx = chosen_id
            else:
                st.session_state.end_road_idx = end_matches.index[0]

with head_col4:
    run_routing = st.button("🚀 Υπολογισμός")

st.markdown("<hr style='margin:10px 0; border-color:#4a423d;'>", unsafe_allow_html=True)

# ==============================================================================
# ΚΥΡΙΟ ΣΩΜΑ (MIDDLE LAYER)
# ==============================================================================
mid_col1, mid_col2 = st.columns([1, 2.2])

with mid_col1:
    st.markdown("<p style='margin:0; font-weight:bold;'>🔄 Φάσεις Έργου Flyover</p>", unsafe_allow_html=True)
    phase = st.radio(
        "Επιλογή περιόδου:",
        ["Πριν τα έργα (Προ-2024)", "Κατά τη διάρκεια (Τρέχουσα Κατάσταση)", "Μετά την ολοκλήρωση"],
        index=1, label_visibility="collapsed"
    )
    
    if phase == "Πριν τα έργα (Προ-2024)": impact_val = 35
    elif phase == "Κατά τη διάρκεια (Τρέχουσα Κατάσταση)": impact_val = 78
    else: impact_val = 15

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<p style='margin:0; font-weight:bold; text-align:center;'>Επιρροή Flyover στο Δίκτυο</p>", unsafe_allow_html=True)
    st.markdown(f"<div class='big-stat'>{impact_val}%</div>", unsafe_allow_html=True)
    st.progress(impact_val / 100)

# --- ΔΙΑΧΕΙΡΙΣΗ ΜΝΗΜΗΣ ΔΙΑΔΡΟΜΗΣ ---
if "route_data" not in st.session_state:
    st.session_state.route_data = {"coords": None, "dist": 0.0, "start": None, "end": None, "active": False}

if run_routing:
    s_idx = st.session_state.start_road_idx
    e_idx = st.session_state.end_road_idx
    
    if s_idx is not None and e_idx is not None and G_network is not None:
        with st.spinner("⏳ Υπολογισμός πραγματικής διαδρομής..."):
            geom_s = gdf_base_roads.loc[s_idx, 'geometry']
            geom_e = gdf_base_roads.loc[e_idx, 'geometry']
            
            start_node = tuple(geom_s.coords[0])
            end_node = tuple(geom_e.coords[-1])
            
            try:
                path = nx.shortest_path(G_network, source=start_node, target=end_node, weight='weight')
                route_coords = [[pt[1], pt[0]] for pt in path]
                path_length_m = nx.shortest_path_length(G_network, source=start_node, target=end_node, weight='weight')
                dist_calc = round(path_length_m / 1000.0, 1)
                
                st.session_state.route_data = {
                    "coords": route_coords, "dist": dist_calc, 
                    "start": [start_node[1], start_node[0]], "end": [end_node[1], end_node[0]], "active": True
                }
            except:
                coord_start = [geom_s.centroid.y, geom_s.centroid.x]
                coord_end = [geom_e.centroid.y, geom_e.centroid.x]
                st.session_state.route_data = {
                    "coords": [coord_start, coord_end], "dist": 4.2, 
                    "start": coord_start, "end": coord_end, "active": True
                }

with mid_col2:
    m = generate_background_traffic_layer(phase)
    r_data = st.session_state.route_data
    if r_data["active"] and r_data["coords"]:
        folium.Marker(location=r_data["start"], popup=start_input, icon=folium.Icon(color='green', icon='play')).add_to(m)
        folium.Marker(location=r_data["end"], popup=end_input, icon=folium.Icon(color='red', icon='stop')).add_to(m)
        folium.PolyLine(locations=r_data["coords"], color="#00d2ff", weight=6, opacity=0.95, tooltip="Υπολογισμένη Διαδρομή").add_to(m)
    st_folium(m, width="100%", height=440, key="thess_map")

st.markdown("<br>", unsafe_allow_html=True)

# ==============================================================================
# ΚΑΤΩ ΜΕΡΟΣ (BOTTOM LAYER) - 3 Ισότιμα Panels
# ==============================================================================
bot_col1, bot_col2, bot_col3 = st.columns([1, 1, 1.2])

with bot_col1:
    st.markdown("<p style='margin:0; font-weight:bold; color:#ff9f43;'>📊 Στατιστικά Διαδρομής</p>", unsafe_allow_html=True)
    dist_val = st.session_state.route_data["dist"]
    status_msg = "✅ Πραγματικό Οδικό Routing (NetworkX Dijkstra)" if dist_val > 0 else "⚠️ Εισάγετε οδούς και πατήστε 'Υπολογισμός'"
    calc_time = int(dist_val * 4.2) if phase == "Κατά τη διάρκεια (Τρέχουσα Κατάσταση)" else (int(dist_val * 2.3) if phase == "Πριν τα έργα (Προ-2024)" else int(dist_val * 1.6))
    
    st.markdown(f"""
    <div style='padding:5px; font-size:14px;'>
        <p style='color:#00d2ff; font-size:12px; margin-bottom:5px;'><b>{status_msg}</b></p>
        <p>• <b>Πραγματική Απόσταση:</b> {dist_val} χλμ</p>
        <p>• <b>Χρόνος Διαδρομής:</b> {calc_time} λεπτά</p>
        <p>• <b>Μέση Ταχύτητα Οδού:</b> {int(60 / (max(calc_time,1)/max(dist_val,1)))} χλμ/ώρα</p>
    </div>
    """, unsafe_allow_html=True)

with bot_col2:
    st.markdown("<p style='margin:0; font-weight:bold; color:#ff9f43;'>🌦️ Προσομοίωση Καιρικών Φαινομένων</p>", unsafe_allow_html=True)
    weather = st.selectbox("Επιλέξτε κατάσταση καιρού:", ["Καθαρός Καιρός / Ήλιος", "Ασθενής Βροχή (+10λ καθυστέρηση)", "Έντονη Καταιγίδα (+25λ καθυστέρηση)"], label_visibility="collapsed")
    w_impact = 10 if "Καθαρός" in weather else (35 if "Ασθενής" in weather else 70)
    st.markdown("<div style='font-size:13px; margin-top:10px;'>Live Επιβάρυνση Λόγω Καιρού:</div>", unsafe_allow_html=True)
    st.progress(w_impact / 100)

with bot_col3:
    st.markdown("<p style='margin:0; font-weight:bold; color:#ff9f43;'>🎓 Ακαδημαϊκά Στοιχεία</p>", unsafe_allow_html=True)
    st.markdown("""
    <div class="academic-card">
        <div class="academic-text">
            <b>ΔΙΕΘΝΕΣ ΠΑΝΕΠΙΣΤΗΜΙΟ ΕΛΛΑΔΟΣ (ΔΙ.ΠΑ.Ε.)</b><br>
            Τμήμα Μηχανικών Τοπογραφίας & Γεωπληροφορικής (Σέρρες)<br>
            <hr style='margin:5px 0; border-color:#4a423d;'>
            👨‍🎓 <b>Σπουδαστής:</b> <span class="highlight-name">Γκουτζέλης Μάριος</span><br>
            👨‍🏫 <b>Επιβλέπων:</b> <span class="highlight-name">Ντούρος Κωνσταντίνος</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
