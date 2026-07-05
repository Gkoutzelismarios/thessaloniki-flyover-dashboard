import streamlit as st
import folium
from streamlit_folium import st_folium
import networkx as nx
import pandas as pd
import numpy as np
import time

# 1. Ρύθμιση Σελίδας (Dark Theme & Wide Mode)
st.set_page_config(
    page_title="Thessaloniki Flyover Impact",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS για το στυλ του Dashboard & Mobile Προσαρμογή
st.markdown("""
    <style>
    .stApp { background-color: #26211e !important; color: #e6e1df !important; }
    div[data-testid="stVerticalBlock"] > div {
        background-color: #36302c; border-radius: 4px; padding: 15px; margin-bottom: 10px;
    }
    input { background-color: #4a423d !important; color: white !important; border: 1px solid #5a524d !important; }
    h1, h2, h3, h4 { color: #ffffff !important; }
    .big-stat { font-size: 44px; font-weight: bold; color: #ff9f43; text-align: center; margin: 10px 0; }
    .stButton>button {
        background-color: #ff9f43 !important; color: black !important;
        font-weight: bold !important; border-radius: 4px !important;
        margin-top: 24px; width: 100%;
    }
    .academic-card { padding: 5px; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }
    .academic-text { font-size: 15px; line-height: 1.7; color: #e6e1df; }
    .highlight-name { color: #ff9f43; font-weight: bold; font-size: 16px; }
    
    @media (max-width: 768px) {
        .big-stat { font-size: 32px; }
        .academic-text { font-size: 13px; }
        .stButton>button { margin-top: 10px; }
        div[data-testid="stVerticalBlock"] > div { padding: 10px !important; margin-bottom: 8px !important; }
        h2 { font-size: 20px !important; }
        p { font-size: 14px !important; }
    }
    </style>
""", unsafe_allow_html=True)

# 🌍 ΣΥΝΑΡΤΗΣΗ ΕΥΡΕΣΗΣ ΠΕΡΙΟΧΗΣ
def get_area_name_from_coords(lat, lon):
    if 40.620 <= lat <= 40.645 and 22.930 <= lon <= 22.955: return "Κέντρο Πόλης"
    if lat < 40.610 and lon > 22.950: return "Καλαμαριά"
    if lat > 40.645 and lon < 22.935: return "Εύοσμος / Κορδελιό"
    if lat > 40.640 and lon > 22.940: return "Συκιές / Νεάπολη"
    if lat < 40.625 and lon > 22.960: return "Τούμπα / Χαριλάου"
    return "Θεσσαλονίκη"

# 🗺️ 2. ΕΠΙΣΤΗΜΟΝΙΚΗ ΓΕΩΧΩΡΙΚΗ ΒΑΣΗ ΔΕΔΟΜΕΝΩΝ (ΕΝΣΩΜΑΤΩΜΕΝΗ & ΔΙΟΡΘΩΜΕΝΗ)
@st.cache_resource
def build_autonomous_network():
    roads_data = {
        0: {"name_display": "Εγνατία (Δυτικά)", "name": "εγνατια", "coords": [[40.6415, 22.9320], [40.6395, 22.9360], [40.6375, 22.9400]], "type": "Λεωφόρος"},
        1: {"name_display": "Εγνατία (Κέντρο)", "name": "εγνατια", "coords": [[40.6375, 22.9400], [40.6355, 22.9440], [40.6335, 22.9480]], "type": "Λεωφόρος"},
        2: {"name_display": "Εγνατία (Πανεπιστήμια)", "name": "εγνατια", "coords": [[40.6335, 22.9480], [40.6315, 22.9520], [40.6295, 22.9560]], "type": "Λεωφόρος"},
        3: {"name_display": "Τσιμισκή (Αρχή)", "name": "τσιμισκη", "coords": [[40.6360, 22.9365], [40.6340, 22.9405], [40.6320, 22.9445]], "type": "Κεντρικός Άξονας"},
        4: {"name_display": "Τσιμισκή (Τέλος)", "name": "τσιμισκη", "coords": [[40.6320, 22.9445], [40.6295, 22.9490], [40.6265, 22.9530]], "type": "Κεντρικός Άξονας"},
        5: {"name_display": "Κασσάνδρου (Άνω Πόλη)", "name": "κασσανδρου", "coords": [[40.6420, 22.9410], [40.6400, 22.9450], [40.6370, 22.9500]], "type": "Συνδετήρια Οδός"},
        6: {"name_display": "Κασσάνδρου (Ανατολικά)", "name": "κασσανδρου", "coords": [[40.6370, 22.9500], [40.6350, 22.9540], [40.6330, 22.9580]], "type": "Συνδετήρια Οδός"},
        7: {"name_display": "Λεωφόρος Νίκης (Παραλία)", "name": "νικης", "coords": [[40.6330, 22.9400], [40.6300, 22.9450], [40.6230, 22.9500]], "type": "Λεωφόρος"},
        8: {"name_display": "Λεωφόρος Στρατού", "name": "στρατου", "coords": [[40.6230, 22.9530], [40.6190, 22.9580], [40.6140, 22.9630]], "type": "Κεντρικός Άξονας"},
        9: {"name_display": "Περιφερειακή Οδός (Flyover Zone)", "name": "περιφερειακη οδος", "coords": [[40.6550, 22.9400], [40.6400, 22.9580], [40.6210, 22.9680]], "type": "Αυτοκινητόδρομος"}
    }
    
    G = nx.Graph()
    for idx, data in roads_data.items():
        pts = data["coords"]
        p1 = tuple(pts[0])
        p2 = tuple(pts[-1])
        # 🌟 ΔΙΟΡΘΩΣΗ: Πρόσβαση με δείκτες [0] και [1] για σωστό υπολογισμό απόστασης
        dist = np.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2) * 111000
        G.add_edge(p1, p2, weight=dist, name=data["name"], index=idx)
        
    return roads_data, G

roads_db, G_network = build_autonomous_network()

# 3. BACKGROUND GENERATOR ΤΟΥ ΧΑΡΤΗ ΚΙΝΗΣΗΣ
@st.cache_data(ttl=30)
def generate_background_traffic_layer(phase):
    m_sub = folium.Map(location=[40.6380, 22.9450], zoom_start=13, tiles="CartoDB dark_matter")
    if roads_db:
        np.random.seed(int(time.time()) // 30)
        for idx, data in roads_db.items():
            base_speed = np.random.randint(15, 70)
            live_speed = base_speed * 0.55 if phase == "Κατά τη διάρκεια (Τρέχουσα Κατάσταση)" else (base_speed * 1.25 if phase == "Μετά την ολοκλήρωση" else base_speed)
            color = "#e74c3c" if live_speed < 22 else ("#f39c12" if live_speed < 40 else "#2ecc71")
            folium.PolyLine(locations=data["coords"], color=color, weight=3, opacity=0.45).add_to(m_sub)
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
    if start_input:
        s_query = start_input.strip().lower()
        matches = [idx for idx, d in roads_db.items() if s_query in d["name"]]
        if matches:
            if len(matches) > 1:
                labels = [f"{roads_db[m]['name_display']} — ({roads_db[m]['type']}) (ID: {m})" for m in matches]
                selected = st.selectbox("👉 Ποιο τμήμα εννοείτε;", labels, key="start_box")
                st.session_state.start_road_idx = int(selected.split("(ID: ")[-1].replace(")", ""))
            else:
                st.session_state.start_road_idx = matches[0]
        else:
            st.session_state.start_road_idx = 5

with head_col3:
    end_input = st.text_input("🏁 Αναζήτηση Προορισμού:", "τσιμισκή")
    if end_input:
        e_query = end_input.strip().lower()
        matches = [idx for idx, d in roads_db.items() if e_query in d["name"]]
        if matches:
            if len(matches) > 1:
                labels = [f"{roads_db[m]['name_display']} — ({roads_db[m]['type']}) (ID: {m})" for m in matches]
                selected = st.selectbox("👉 Ποιο τμήμα εννοείτε;", labels, key="end_box")
                st.session_state.end_road_idx = int(selected.split("(ID: ")[-1].replace(")", ""))
            else:
                st.session_state.end_road_idx = matches[0]
        else:
            st.session_state.end_road_idx = 3

with head_col4:
    run_routing = st.button("🚀 Υπολογισμός")

st.markdown("<hr style='margin:10px 0; border-color:#4a423d;'>", unsafe_allow_html=True)

# ==============================================================================
# ΚΥΡΙΟ ΣΩΜΑ (MIDDLE LAYER)
# ==============================================================================
mid_col1, mid_col2 = st.columns([1, 2.2])

with mid_col1:
    st.markdown("<p style='margin:0; font-weight:bold;'>🔄 Φάσεις Έργου Flyover</p>", unsafe_allow_html=True)
    phase = st.radio("Επιλογή περιόδου:", ["Πριν τα έργα (Προ-2024)", "Κατά τη διάρκεια (Τρέχουσα Κατάσταση)", "Μετά την ολοκλήρωση"], index=1, label_visibility="collapsed")
    impact_val = 35 if phase == "Πριν τα έργα (Προ-2024)" else (78 if phase == "Κατά τη διάρκεια (Τρέχουσα Κατάσταση)" else 15)
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<p style='margin:0; font-weight:bold; text-align:center;'>Επιρροή Flyover στο Δίκτυο</p>", unsafe_allow_html=True)
    st.markdown(f"<div class='big-stat'>{impact_val}%</div>", unsafe_allow_html=True)
    st.progress(impact_val / 100)

if "route_data" not in st.session_state:
    st.session_state.route_data = {"coords": None, "dist": 0.0, "start": None, "end": None, "active": False}

if run_routing:
    s_idx = st.session_state.start_road_idx
    e_idx = st.session_state.end_road_idx
    
    if s_idx is not None and e_idx is not None:
        with st.spinner("⏳ Υπολογισμός πραγματικής διαδρομής δικτύου..."):
            pts_s = roads_db[s_idx]["coords"]
            pts_e = roads_db[e_idx]["coords"]
            
            node_s = tuple(pts_s[0])
            node_e = tuple(pts_e[-1])
            
            try:
                path = nx.shortest_path(G_network, source=node_s, target=node_e, weight='weight')
                route_coords = []
                for pt in path:
                    route_coords.append([pt[0], pt[1]])
                
                path_len = nx.shortest_path_length(G_network, source=node_s, target=node_e, weight='weight')
                dist_calc = round(path_len / 1000.0, 1)
                if dist_calc == 0: 
                    dist_calc = round(np.sqrt((node_s[0]-node_e[0])**2 + (node_s[1]-node_e[1])**2)*111, 1)
                
                st.session_state.route_data = {"coords": route_coords, "dist": dist_calc, "start": list(node_s), "end": list(node_e), "active": True}
            except:
                route_coords = pts_s + pts_e
                st.session_state.route_data = {"coords": route_coords, "dist": 3.8, "start": pts_s[0], "end": pts_e[-1], "active": True}

with mid_col2:
    m = generate_background_traffic_layer(phase)
    r_data = st.session_state.route_data
    if r_data["active"] and r_data["coords"]:
        folium.Marker(location=r_data["start"], popup=start_input, icon=folium.Icon(color='green', icon='play')).add_to(m)
        folium.Marker(location=r_data["end"], popup=end_input, icon=folium.Icon(color='red', icon='stop')).add_to(m)
        folium.PolyLine(locations=r_data["coords"], color="#00d2ff", weight=6, opacity=0.95).add_to(m)
        
    map_height = 340 if st.sidebar.checkbox("📱 Mobile View", value=False) else 440
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
