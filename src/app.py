import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
from shapely import wkt
import time
import ast
from scipy.spatial import KDTree
from src.algorithms.Dijkstra import dijkstra_search
from src.algorithms.DWAStar import dwa_star_search
from src.algorithms.AStarOrigin import a_star_search
from src.load_graph import load_graph

st.set_page_config(layout="wide", page_title="HCMC Routing Comparison")

# Cache CSS
@st.cache_resource
def load_css():
    with open("static/style.css", encoding="utf-8") as f:
        return f.read()

st.markdown(f"<style>{load_css()}</style>", unsafe_allow_html=True)

# ────────────────────── CACHE FUNCTIONS ──────────────────────

@st.cache_resource 
def build_spatial_index(nodes_df):
    return KDTree(nodes_df[['y', 'x']].values)

@st.cache_data
def get_traffic_geojson(edges_df, time_slot):
    idx = time_slot - 1
    features = []
    important_highways = ['motorway', 'trunk', 'primary', 'secondary', 'tertiary']
    df_filtered = edges_df[(edges_df['length'] >= 10) & (edges_df['highway'].isin(important_highways))]
    
    width_map = {'motorway': 6, 'trunk': 5, 'primary': 4, 'secondary': 2.5, 'tertiary': 1.2}
    color_map = [(1.1, "#2ecc71"), (1.3, "#f1c40f"), (1.5, "#e67e22"), (float('inf'), "#e74c3c")]

    for _, row in df_filtered.iterrows():
        if pd.isna(row['geometry']): 
            continue
        
        los = float(ast.literal_eval(row['los'])[idx])
        color = next((c for t, c in color_map if los < t), "#e74c3c")
        
        feature = {
            "type": "Feature",
            "geometry": wkt.loads(row['geometry']).__geo_interface__,
            "properties": {"style": {"color": color, "weight": width_map.get(row['highway'], 2), "opacity": 0.5}}
        }
        features.append(feature)
    
    return {"type": "FeatureCollection", "features": features}

@st.cache_data
def load_data(time_slot):
    coords, adj, edges_lookup = load_graph('./data/processed/nodes.csv', './data/processed/edges.csv', time_slot)
    nodes_df = pd.read_csv('./data/processed/nodes.csv').set_index('osmid')
    edges_df = pd.read_csv('./data/processed/edges.csv')
    
    traffic_geojson = get_traffic_geojson(edges_df, time_slot)
    bounds = [[nodes_df['y'].min() - 0.001, nodes_df['x'].min() - 0.001], 
              [nodes_df['y'].max() + 0.001, nodes_df['x'].max() + 0.001]]
    spatial_index = build_spatial_index(nodes_df)
    
    return coords, adj, nodes_df, edges_df.set_index(['u', 'v']), traffic_geojson, bounds, spatial_index

# ────────────────────── TIME OPTIONS CACHE ──────────────────────

@st.cache_resource
def get_time_options():
    return [f"{i*30//60:02d}:{i*30%60:02d}" for i in range(48)]

# ────────────────────── SETUP ──────────────────────

st.sidebar.image("static/assets/Logo_Đại_học_Bách_Khoa_Hà_Nội.svg.png", width=200)

time_options = get_time_options()
st.sidebar.title("Chọn khung giờ")
selected_time = st.sidebar.select_slider("Kéo để chọn thời gian:", options=time_options, value=time_options[st.session_state.get('old_slot', 17) - 1])
slot = time_options.index(selected_time) + 1

if 'old_slot' not in st.session_state:
    st.session_state.old_slot = slot
if slot != st.session_state.old_slot:
    st.session_state.old_slot = slot
    st.session_state.path_coords = None
    st.session_state.comparison_df = None
    st.toast(f"🔄 Đang cập nhật dữ liệu lúc {selected_time}...", icon="⏳")
    st.rerun()

coords, adj, nodes_df, edges_lookup, traffic_data, map_bounds, spatial_index = load_data(slot)

# Init session state
for key, default in [('start_coord', None), ('end_coord', None), ('path_coords', None), 
                      ('comparison_df', None), ('selecting', None), ('last_click_id', None),
                      ('map_center', [nodes_df['y'].mean(), nodes_df['x'].mean()]), ('map_zoom', 15)]:
    if key not in st.session_state:
        st.session_state[key] = default

@st.dialog(" Phân tích & So sánh Thuật toán", width="large")
def show_comparison_dialog(df):
    st.write("So sánh hiệu năng các thuật toán tìm đường trên lưới giao thông TP.HCM.")
    c1, c2, c3 = st.columns(3)
    fastest = df.loc[df['Time (ms)'].idxmin()]
    c1.metric("Nhanh nhất", fastest['Thuật toán'], f"{fastest['Time (ms)']} ms")
    c2.metric("Quãng đường", f"{df['Quãng đường (km)'].min()} km")
    c3.metric("Nodes duyệt ít nhất", int(df['Nodes'].min()))
    
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Thời gian thực thi (ms)**")
        st.bar_chart(df, x="Thuật toán", y="Time (ms)", color="#2ecc71")
    with col2:
        st.write("**Số Node đã duyệt**")
        st.bar_chart(df, x="Thuật toán", y="Nodes", color="#3498db")
    
    st.write("**Chi tiết kỹ thuật:**")
    st.dataframe(df, use_container_width=True, hide_index=True)

# ────────────────────── SIDEBAR BUTTONS ──────────────────────

@st.fragment
def render_location_buttons():
    st.title("Chọn vị trí")
    c1, c2 = st.columns(2)
    with c1: 
        if st.button("Điểm đầu", use_container_width=True): 
            st.session_state.selecting = 'start'
            st.session_state.path_coords = None
            st.session_state.comparison_df = None
            st.session_state.start_coord = None
            st.session_state.end_coord = None
    with c2: 
        if st.button("Điểm cuối", use_container_width=True): 
            st.session_state.selecting = 'end'
            st.session_state.path_coords = None
            st.session_state.comparison_df = None
            st.session_state.end_coord = None

with st.sidebar:
    render_location_buttons()

if st.sidebar.button("Chạy thuật toán", type="primary", use_container_width=True):
    if st.session_state.start_coord and st.session_state.end_coord:
        u_s = st.session_state.get('start_node_id')
        v_e = st.session_state.get('end_node_id')
        
        if u_s is None or v_e is None:
            _, idx_s = spatial_index.query(st.session_state.start_coord)
            _, idx_e = spatial_index.query(st.session_state.end_coord)
            u_s, v_e = nodes_df.index[idx_s], nodes_df.index[idx_e]
        
        stats = []
        final_path = None
        
        for name, func in [("Dijkstra", dijkstra_search), ("A* Origin", a_star_search), ("DWA*", dwa_star_search)]:
            t_start = time.perf_counter()
            p, c, v = func(coords, adj, u_s, v_e)
            duration_ms = round((time.perf_counter() - t_start) * 1000, 2)
            stats.append([name, round(c/1000, 4), v, duration_ms])
            if name == "DWA*" and p:
                final_path = p

        st.session_state.comparison_df = pd.DataFrame(stats, columns=["Thuật toán", "Quãng đường (km)", "Nodes", "Time (ms)"])
        
        if final_path:
            path_geo = []
            for i in range(len(final_path) - 1):
                u, v = final_path[i], final_path[i + 1]
                if (u, v) in edges_lookup.index:
                    row = edges_lookup.loc[(u, v)]
                    if isinstance(row, pd.DataFrame): 
                        row = row.iloc[0]
                    if 'geometry' in row and pd.notna(row['geometry']):
                        path_geo.extend([(lat, lon) for lon, lat in wkt.loads(row['geometry']).coords])
                    else:
                        path_geo.extend([(nodes_df.loc[u, 'y'], nodes_df.loc[u, 'x']), (nodes_df.loc[v, 'y'], nodes_df.loc[v, 'x'])])
            st.session_state.path_coords = path_geo
        st.rerun()

with st.sidebar: 
    if st.button("So sánh thuật toán", use_container_width=True, type="secondary"):
        if st.session_state.comparison_df is not None:
            show_comparison_dialog(st.session_state.comparison_df)
    if st.button("Reset Bản đồ", use_container_width=True):
        st.session_state.start_coord = None
        st.session_state.end_coord = None
        st.session_state.path_coords = None
        st.session_state.comparison_df = None
        st.rerun()

# ────────────────────── MAP ──────────────────────

@st.fragment
def show_map():
    # 1. Xử lý sự kiện click từ session_state trước khi khởi tạo map
    if "main_map" in st.session_state and st.session_state.main_map.get("last_clicked"):
        click_data = st.session_state.main_map["last_clicked"]
        current_click_id = f"{click_data['lat']}_{click_data['lng']}"

        if st.session_state.selecting is not None and current_click_id != st.session_state.last_click_id:
            dist, idx = spatial_index.query([click_data['lat'], click_data['lng']])
            nearest_node_id = nodes_df.index[idx]
            nearest_coords = (nodes_df.iloc[idx]['y'], nodes_df.iloc[idx]['x'])
            
            if st.session_state.selecting == 'start':
                st.session_state.start_coord = nearest_coords
                st.session_state.start_node_id = nearest_node_id
            elif st.session_state.selecting == 'end':
                st.session_state.end_coord = nearest_coords
                st.session_state.end_node_id = nearest_node_id
            
            st.session_state.last_click_id = current_click_id
            st.session_state.selecting = None

    # 2. Vẽ bản đồ
    min_lat, max_lat = map_bounds[0][0], map_bounds[1][0]
    min_lon, max_lon = map_bounds[0][1], map_bounds[1][1]
    
    try:    
        overlay_color = "#ffffff" if st.get_option("theme.base") == "light" else "#0e1117"
    except:
        overlay_color = "#0e1117"
    
    m = folium.Map(location=st.session_state.map_center, zoom_start=14, min_zoom=13, max_zoom=18, 
                   max_bounds=True, min_lat=min_lat, max_lat=max_lat, min_lon=min_lon, max_lon=max_lon)
    m.get_root().html.add_child(folium.Element("<style>.leaflet-control-attribution { display: none !important; }</style>"))
    
    folium.GeoJson(traffic_data, style_function=lambda x: x['properties']['style']).add_to(m)
    
    # Border
    OUTER = 10
    for panel in [
        [[max_lat, min_lon - OUTER], [max_lat + OUTER, max_lon + OUTER]],
        [[min_lat - OUTER, min_lon - OUTER], [min_lat, max_lon + OUTER]],
        [[min_lat, min_lon - OUTER], [max_lat, min_lon]],
        [[min_lat, max_lon], [max_lat, max_lon + OUTER]],
    ]:
        folium.Rectangle(bounds=panel, color=overlay_color, weight=0, fill=True, 
                         fill_color=overlay_color, fill_opacity=0.82, interactive=False).add_to(m)
    
    r = 0.0008
    svg_path = f"M {min_lon+r},{min_lat} L {max_lon-r},{min_lat} Q {max_lon},{min_lat} {max_lon},{min_lat+r} L {max_lon},{max_lat-r} Q {max_lon},{max_lat} {max_lon-r},{max_lat} L {min_lon+r},{max_lat} Q {min_lon},{max_lat} {min_lon},{max_lat-r} L {min_lon},{min_lat+r} Q {min_lon},{min_lat} {min_lon+r},{min_lat} Z"
    svg_str = f'<svg xmlns="http://www.w3.org/2000/svg"><path d="{svg_path}" fill="none" stroke="#e74c3c" stroke-width="3" vector-effect="non-scaling-stroke"/></svg>'
    svg_encoded = svg_str.replace(" ", "%20").replace('"', "%22").replace("#", "%23").replace("<", "%3C").replace(">", "%3E")
    folium.raster_layers.ImageOverlay(f"data:image/svg+xml;charset=utf-8,{svg_encoded}", 
                                      bounds=[[min_lat, min_lon], [max_lat, max_lon]], opacity=1, interactive=False, zindex=500).add_to(m)
    
    if st.session_state.start_coord:
        folium.Marker(st.session_state.start_coord, icon=folium.Icon(color='green')).add_to(m)
    if st.session_state.end_coord:
        folium.Marker(st.session_state.end_coord, icon=folium.Icon(color='red')).add_to(m)
    if st.session_state.path_coords:
        folium.PolyLine(st.session_state.path_coords, color='blue', weight=10, opacity=1).add_to(m)
        m.fit_bounds(st.session_state.path_coords)

    st_folium(m, width="100%", height=600, key="main_map", returned_objects=["last_clicked"])

show_map()