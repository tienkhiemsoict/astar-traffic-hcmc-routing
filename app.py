import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
from shapely import wkt
import os
import time
import ast
import json
from scipy.spatial import KDTree
from dijkstra_algorithm import dijkstra_search
from dwa_star_algorithm import dwa_star_search
from A_star_algorithm import a_star_search
from load_graph import load_graph

st.set_page_config(layout="wide", page_title="HCMC Routing Comparison")

# Style - CSS
with open("static/style.css", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
# ──────────────────────────────────────────────────────────────────────────────


# Header
st.title("Ho Chi Minh Routing Comparison")
# ________________________________________________________________________________


@st.cache_resource 
def build_spatial_index(nodes_df):
    # Lấy mảng tọa độ [[lat1, lon1], [lat2, lon2], ...]
    points = nodes_df[['y', 'x']].values
    return KDTree(points)

#preload 
@st.cache_data
def get_traffic_geojson(edges_df, time_slot):
    idx = time_slot - 1
    features = []
    important_highways = ['motorway', 'trunk', 'primary', 'secondary', 'tertiary']
    # Lọc đường để bản đồ mượt hơn
    df_filtered = edges_df[
        (edges_df['length'] >= 10) & 
        (edges_df['highway'].isin(important_highways))
    ].copy()
    #độ dày đường
    width_map = {'motorway': 6, 'trunk': 5, 'primary': 4, 'secondary': 2.5, 'tertiary': 1.2}

    for _, row in df_filtered.iterrows():
        if pd.isna(row['geometry']): continue
        
        # Lấy weight
        los_list = ast.literal_eval(row['los'])
        w = float(los_list[idx])
        
        # color
        if w < 1.1:
            color = "#2ecc71" 
        elif w < 1.3:
            color = "#f1c40f"
        elif w < 1.5:
            color = "#e67e22"
        else:
            color = "#e74c3c" 

        line_weight = width_map.get(row['highway'], 2)

        # Chuyển Geometry sang dạng dict cho GeoJSON
        geo_dict = wkt.loads(row['geometry']).__geo_interface__
        
        feature = {
            "type": "Feature",
            "geometry": geo_dict,
            "properties": {
                "style": {"color": color, "weight": line_weight, "opacity": 0.5},
            }
        }
        features.append(feature)
        
    return {"type": "FeatureCollection", "features": features}

@st.cache_data
def load_data(time_slot):
    n_path = 'data/nodes.csv'
    e_path = 'data/edges.csv'
    
    coords, adj ,edges_lookup = load_graph(n_path, e_path, time_slot)

    nodes_df = pd.read_csv(n_path).set_index('osmid')
    edges_df = pd.read_csv(e_path)

    edges_lookup = edges_df.set_index(['u', 'v'])
    
    traffic_geojson = get_traffic_geojson(edges_df, time_slot)

    min_lat, max_lat = nodes_df['y'].min(), nodes_df['y'].max()
    min_lon, max_lon = nodes_df['x'].min(), nodes_df['x'].max()
    bounds = [[min_lat - 0.001, min_lon - 0.001], [max_lat + 0.001, max_lon + 0.001]]
    spatial_index = build_spatial_index(nodes_df)

    return coords, adj, nodes_df, edges_lookup,traffic_geojson, bounds , spatial_index

# Logo siu cấp AI
st.sidebar.image(r"static\assets\Logo_Đại_học_Bách_Khoa_Hà_Nội.svg.png", width = 200)

# Chọn khung thời gian
time_options = []
for i in range(48):
    total_minutes = i * 30
    hours = total_minutes // 60
    minutes = total_minutes % 60
    time_options.append(f"{hours:02d}:{minutes:02d}")

st.sidebar.title("Chọn khung giờ")

selected_time = st.sidebar.select_slider(
    "Kéo để chọn thời gian:",
    options=time_options,
    value=time_options[st.session_state.get('old_slot', 17) - 1],
    # help="Dữ liệu giao thông cập nhật mỗi 30 phút"
)
# chuyển ngược từ hh:mm -> 0-47 để chạy thuật toán
slot = time_options.index(selected_time) + 1

#Logic reset đổi giờ
if 'old_slot' not in st.session_state:
    st.session_state.old_slot = slot
if slot != st.session_state.old_slot:
    st.session_state.old_slot = slot
    st.session_state.path_coords = None
    st.session_state.comparison_df = None
    st.toast(f"🔄 Đang cập nhật dữ liệu lúc {selected_time}...", icon="⏳")
    st.rerun()

# lấy dữ liệu
coords, adj, nodes_df, edges_lookup, traffic_data,map_bounds,spatial_index = load_data(slot)

if 'start_coord' not in st.session_state: st.session_state.start_coord = None
if 'end_coord' not in st.session_state: st.session_state.end_coord = None
if 'path_coords' not in st.session_state: st.session_state.path_coords = None
if 'comparison_df' not in st.session_state: st.session_state.comparison_df = None
if 'selecting' not in st.session_state: st.session_state.selecting = None

if 'last_click_id' not in st.session_state: st.session_state.last_click_id = None

st.sidebar.title("Chọn vị trí")

c1, c2 = st.sidebar.columns(2)
with c1: 
    if st.button(" Điểm đầu",use_container_width= True): 
        st.session_state.selecting = 'start'
        st.session_state.path_coords = None
        st.session_state.comparison_df = None
        st.session_state.start_coord = None
        st.session_state.end_coord = None
        if 'main_map' in st.session_state and 'last_clicked' in st.session_state['main_map']:
             click_old = st.session_state['main_map']['last_clicked']
             if click_old:
                st.session_state.last_click_id = f"{click_old['lat']}_{click_old['lng']}"
with c2: 
    if st.button(" Điểm cuối",use_container_width= True): 
        st.session_state.selecting = 'end'
        st.session_state.path_coords = None
        st.session_state.comparison_df = None
        st.session_state.end_coord = None
        if 'main_map' in st.session_state and 'last_clicked' in st.session_state['main_map']:
             click_old = st.session_state['main_map']['last_clicked']
             if click_old:
                st.session_state.last_click_id = f"{click_old['lat']}_{click_old['lng']}"

if st.sidebar.button("Chạy thuật toán", type="primary", use_container_width=True):
    if st.session_state.start_coord and st.session_state.end_coord:
        if st.session_state.start_coord and st.session_state.end_coord:
            u_s = st.session_state.get('start_node_id')
            v_e = st.session_state.get('end_node_id')
        if u_s is None or v_e is None:
            # Dùng spatial_index (KD-Tree) để tìm lại nhanh
            _, idx_s = spatial_index.query(st.session_state.start_coord)
            _, idx_e = spatial_index.query(st.session_state.end_coord)
            u_s = nodes_df.index[idx_s]
            v_e = nodes_df.index[idx_e]
            
        stats = []
        final_path = None
        
        algorithms = [
            ("Dijkstra", dijkstra_search),
            ("A* Origin", a_star_search),
            ("DWA*", dwa_star_search)
        ]

        for name, func in algorithms:
            t_start = time.perf_counter()
            p, c, v = func(coords, adj, u_s, v_e)
            
            duration_ms = round((time.perf_counter() - t_start) * 1000, 2)
            stats.append([name, round(c/1000, 4), v, duration_ms])
            
            if name == "DWA*" and p:
                final_path = p

        st.session_state.comparison_df = pd.DataFrame(stats, columns=["Thuật toán", "Quãng đường (km)", "Nodes", "Time (ms)"])
        
        if final_path:
            path_geo = []
            for i in range(len(final_path)-1):
                u, v = final_path[i], final_path[i+1]
                if (u,v) in edges_lookup.index:
                    row = edges_lookup.loc[(u,v)]
                    if isinstance(row, pd.DataFrame): row = row.iloc[0]
                    if 'geometry' in row and pd.notna(row['geometry']):
                        path_geo.extend([(lat, lon) for lon, lat in wkt.loads(row['geometry']).coords])
                    else:
                        path_geo.extend([(nodes_df.loc[u,'y'], nodes_df.loc[u,'x']), (nodes_df.loc[v,'y'], nodes_df.loc[v,'x'])])
            st.session_state.path_coords = path_geo
        st.rerun()


@st.fragment
def show_map():
    m = folium.Map(location=[nodes_df['y'].mean(), nodes_df['x'].mean()], zoom_start=15,min_zoom=10,max_zoom=18, max_bounds=True)
    
    folium.GeoJson(
        traffic_data,
        style_function=lambda x: x['properties']['style'],
    ).add_to(m)
    folium.Rectangle(bounds=map_bounds, color="red", weight=2, fill=False).add_to(m)


    if st.session_state.start_coord:
        folium.Marker(st.session_state.start_coord, icon=folium.Icon(color='green')).add_to(m)
    if st.session_state.end_coord:
        folium.Marker(st.session_state.end_coord, icon=folium.Icon(color='red')).add_to(m)

    if st.session_state.path_coords:
        folium.PolyLine(st.session_state.path_coords, color='blue', weight=10, opacity=1).add_to(m)
        m.fit_bounds(st.session_state.path_coords)

    out = st_folium(m, width="100%", height=800, key="main_map", returned_objects=["last_clicked"])


    if out and out.get('last_clicked'):
        click_data = out['last_clicked']
        current_click_id = f"{click_data['lat']}_{click_data['lng']}"

        if st.session_state.selecting is not None and current_click_id != st.session_state.last_click_id:
            
           
            dist, idx = spatial_index.query([click_data['lat'], click_data['lng']])
            
            # Lấy osmid và tọa độ thực của Node đó
            nearest_node_id = nodes_df.index[idx]
            nearest_coords = (nodes_df.iloc[idx]['y'], nodes_df.iloc[idx]['x'])
            
            if st.session_state.selecting == 'start':
                st.session_state.start_coord = nearest_coords
                st.session_state.start_node_id = nearest_node_id # Lưu ID để chạy thuật toán
            elif st.session_state.selecting == 'end':
                st.session_state.end_coord = nearest_coords
                st.session_state.end_node_id = nearest_node_id
            
            st.session_state.last_click_id = current_click_id
            st.session_state.selecting = None
            st.rerun()
    
show_map()

if st.session_state.comparison_df is not None: 
    st.write("### Kết quả")
    st.table(st.session_state.comparison_df)
    if st.button("Reset", use_container_width=True):
    
        st.session_state.start_coord = None
        st.session_state.end_coord = None
        st.session_state.path_coords = None
        st.session_state.comparison_df = None
        st.session_state.selecting = None
        st.rerun()