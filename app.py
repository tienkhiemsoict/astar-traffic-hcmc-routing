import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
from shapely import wkt
import os
import time
from sma_algorithm import sma_star_shortest_path, a_star_search, dijkstra_search

st.set_page_config(layout="wide", page_title="HCMC Routing Comparison")

@st.cache_data
def load_data():
    nodes_df = pd.read_csv(r"D:\LapTrinh\astar-traffic-hcmc-routing\data\nodes.csv").set_index('osmid')
    edges_df = pd.read_csv(r"D:\LapTrinh\astar-traffic-hcmc-routing\data\edges.csv")
    coords = {idx: (row['y'], row['x']) for idx, row in nodes_df.iterrows()}
    adj = {}
    for _, row in edges_df.iterrows():
        u, v, w = row['u'], row['v'], row.get('length', 1.0)
        if u not in adj: adj[u] = []
        adj[u].append((v, w))
    edges_lookup = edges_df.set_index(['u', 'v'])
    min_lat, max_lat = nodes_df['y'].min(), nodes_df['y'].max()
    min_lon, max_lon = nodes_df['x'].min(), nodes_df['x'].max()
    padding = 0.001
    map_bounds = [[min_lat - padding, min_lon - padding], 
                  [max_lat + padding, max_lon + padding]]
    
    return coords, adj, edges_lookup, nodes_df, map_bounds

coords, adj, edges_lookup, nodes_df , map_bounds = load_data()

# Session State
for key in ['start_coord', 'end_coord', 'path_coords', 'comparison_df', 'selecting']:
    if key not in st.session_state: st.session_state[key] = None

# Sidebar
st.sidebar.title("🧭 Điều hướng & So sánh")
c1, c2 = st.sidebar.columns(2)
with c1: 
    if st.button("📍 Điểm đầu"): st.session_state.selecting = 'start'
with c2: 
    if st.button("🚩 Điểm cuối"): st.session_state.selecting = 'end'

if st.sidebar.button("🚀 Chạy tất cả thuật toán", type="primary"):
    if st.session_state.start_coord and st.session_state.end_coord:
        u_s = ((nodes_df['y']-st.session_state.start_coord[0])**2+(nodes_df['x']-st.session_state.start_coord[1])**2).idxmin()
        v_e = ((nodes_df['y']-st.session_state.end_coord[0])**2+(nodes_df['x']-st.session_state.end_coord[1])**2).idxmin()
        
        data = []
        # Chạy Dijkstra
        t = time.perf_counter()
        p_d, c_d, v_d = dijkstra_search(coords, adj, u_s, v_e)
        data.append(["Dijkstra", round(c_d,1), v_d, round(time.perf_counter()-t, 4)])
        
        # Chạy A*
        t = time.perf_counter()
        p_a, c_a, v_a = a_star_search(coords, adj, u_s, v_e)
        data.append(["A* (Original)", round(c_a,1), v_a, round(time.perf_counter()-t, 4)])
        
        # Chạy SMA*
        t = time.perf_counter()
        p_s, c_s, v_s = sma_star_shortest_path(coords, adj, u_s, v_e, 10000)
        data.append(["SMA* (10k)", round(c_s,1), v_s, round(time.perf_counter()-t, 4)])
        
        st.session_state.comparison_df = pd.DataFrame(data, columns=["Thuật toán", "Quãng đường (m)", "Nodes duyệt", "Thời gian (s)"])
        
        # Lấy geometry cho SMA*
        if p_s:
            path_geo = []
            for i in range(len(p_s)-1):
                u, v = p_s[i], p_s[i+1]
                if (u,v) in edges_lookup.index:
                    e = edges_lookup.loc[(u,v)]
                    if isinstance(e, pd.DataFrame): e = e.iloc[0]
                    if 'geometry' in e and pd.notna(e['geometry']):
                        path_geo.extend([(lat, lon) for lon, lat in wkt.loads(e['geometry']).coords])
                    else:
                        path_geo.extend([(nodes_df.loc[u,'y'], nodes_df.loc[u,'x']), (nodes_df.loc[v,'y'], nodes_df.loc[v,'x'])])
            st.session_state.path_coords = path_geo
        st.rerun()

if st.session_state.comparison_df is not None:
    st.sidebar.write("### 📊 Kết quả")
    st.sidebar.dataframe(st.session_state.comparison_df, hide_index=True)

if st.sidebar.button("♻️ Reset"):
    for k in ['start_coord','end_coord','path_coords','comparison_df']: st.session_state[k] = None
    st.rerun()

# Map Fragment
@st.fragment
def map_ui():
    m = folium.Map(
        location=[nodes_df['y'].mean(), nodes_df['x'].mean()], 
        zoom_start=15,
        min_zoom= 15,
        max_zoom= 18,
        max_bounds=True,
        min_lat=map_bounds[0][0], max_lat=map_bounds[1][0],
        min_lon=map_bounds[0][1], max_lon=map_bounds[1][1]
    )
    folium.Rectangle(
        bounds=map_bounds, 
        color="red", 
        weight=2, 
        fill=False, 
        interactive=False
    ).add_to(m)
    if st.session_state.start_coord: folium.Marker(st.session_state.start_coord, icon=folium.Icon(color='green')).add_to(m)
    if st.session_state.end_coord: folium.Marker(st.session_state.end_coord, icon=folium.Icon(color='red')).add_to(m)
    if st.session_state.path_coords:
        folium.PolyLine(st.session_state.path_coords, color='blue', weight=5).add_to(m)
        m.fit_bounds(st.session_state.path_coords)
    
    out = st_folium(m, width="100%", height=600, key="map", returned_objects=["last_clicked"])
    if out and out.get('last_clicked') and st.session_state.selecting:
        lat, lng = out['last_clicked']['lat'], out['last_clicked']['lng']
        if st.session_state.selecting == 'start': st.session_state.start_coord = (lat, lng)
        else: st.session_state.end_coord = (lat, lng)
        st.session_state.selecting = None
        st.rerun()

map_ui()