import os
import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from scipy.spatial import KDTree
from functools import lru_cache
from src.algorithms.Dijkstra import dijkstra_search
from src.algorithms.AStarOrigin import a_star_search
from src.algorithms.DWAStar import dwa_star_search
from src.load_graph import load_graph
import ast
from shapely import wkt
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- KHỞI TẠO ĐƯỜNG DẪN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
nodes_path = os.path.join(BASE_DIR, "data", "processed", "nodes.csv")
edges_path = os.path.join(BASE_DIR, "data", "processed", "edges.csv")

# Load nodes_df chỉ để dùng cho KDTree (Snap-node)
nodes_df = pd.read_csv(nodes_path)
df_edges = pd.read_csv(edges_path)
spatial_index = KDTree(nodes_df[['y', 'x']].values)

class RouteRequest(BaseModel):
    start_id: int
    end_id: int
    slot: int

# --- CACHE GRAPH ---

@app.get("/api/traffic-geojson")
async def get_traffic_geojson(slot: int):
    get_cached_data(slot)
    
    coords, adj, edge_lookup = get_cached_data(slot)
    idx = slot - 1
    features = []
    important_highways = ['motorway', 'trunk', 'primary', 'secondary', 'tertiary']
    
    # Lọc dữ liệu như logic cũ của bạn
    df_filtered = df_edges[(df_edges['length'] >= 10) & (df_edges['highway'].isin(important_highways))]
    
    width_map = {'motorway': 6, 'trunk': 5, 'primary': 4, 'secondary': 2.5, 'tertiary': 1.2}
    # Logic màu sắc: LOS < 1.1: Xanh, < 1.3: Vàng, < 1.5: Cam, Còn lại: Đỏ
    color_map = [(1.1, "#2ecc71"), (1.3, "#f1c40f"), (1.5, "#e67e22")]

    for _, row in df_filtered.iterrows():
        try:
            # Parse list LOS từ string (cột los trong file của bạn là string dạng list)
            los_list = ast.literal_eval(row['los'])
            los_value = float(los_list[idx])
            
            # Xác định màu
            color = "#e74c3c" # Mặc định là đỏ
            for threshold, c in color_map:
                if los_value < threshold:
                    color = c
                    break
            
            # Chuyển WKT sang GeoJSON geometry
            geom = wkt.loads(row['geometry']).__geo_interface__
            
            features.append({
                "type": "Feature",
                "geometry": geom,
                "properties": {
                    "color": color,
                    "weight": width_map.get(row['highway'], 2),
                    "opacity": 0.6
                }
            })
        except:
            continue
            
    return {"type": "FeatureCollection", "features": features}

@lru_cache(maxsize=10)
def get_cached_data(slot):
    print(f" Đang tải dữ liệu đồ thị cho slot: {slot}")
    # Truyền đuờng dẫn file vào hàm của bạn
    return load_graph(nodes_path, edges_path, slot)

def to_plain(obj):
    if isinstance(obj, (np.int64, np.int32)): return int(obj)
    if isinstance(obj, (np.float64, np.float32)): return float(obj)
    if isinstance(obj, float) and (obj == float('inf') or obj == float('-inf')):
        return None
    return obj

# --- API ---

@app.get("/api/snap-node")
async def snap_node(lat: float, lng: float):
    dist, idx = spatial_index.query([lat, lng])
    row = nodes_df.iloc[idx]
    return {"id": int(row['osmid']), "lat": float(row['y']), "lng": float(row['x'])}

@app.post("/api/route")
async def get_route(req: RouteRequest):
    try:
        # Hứng 3 giá trị trả về từ hàm load_graph của bạn
        coords, adj, edge_lookup = get_cached_data(req.slot)
        
        # Gọi thuật toán DWA* với đúng các tham số (coords, adj)
        path, cost, visited = dwa_star_search(coords, adj, req.start_id, req.end_id)
        
        if not path:
            return {"status": "error", "message": "Không tìm thấy đường đi"}

        # Tạo tọa độ cho Front-end
        path_coords = [[coords[nid][0], coords[nid][1]] for nid in path if nid in coords]
            
        return {
            "path_coords": path_coords,
            "stats": {
                "distance_m": to_plain(cost),
                "visited_nodes": to_plain(visited)
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc() # In lỗi chi tiết ra Terminal
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/compare")
async def compare_algorithms(req: RouteRequest):
    try:
        coords, adj, _ = get_cached_data(req.slot)
        
        results = []
        
        # Danh sách cấu hình thuật toán để chạy vòng lặp cho gọn
        algos = [
            ("DWA*", dwa_star_search),
            ("Dijkstra", dijkstra_search),
            ("A*", a_star_search)
        ]

        # Warm-up để giảm ảnh hưởng của lần chạy đầu và bộ nhớ đệm Python
        for _, func in algos:
            func(coords, adj, req.start_id, req.end_id)
        
        num_trials = 3
        for name, func in algos:
            total_ms = 0.0
            last_cost = None
            last_visited = None
            for _ in range(num_trials):
                start_t = time.perf_counter()
                _, cost, vis = func(coords, adj, req.start_id, req.end_id)
                end_t = time.perf_counter()
                total_ms += (end_t - start_t) * 1000
                last_cost = cost
                last_visited = vis
            avg_ms = round(total_ms / num_trials, 2)
            results.append({
                "algo": name,
                "dist": to_plain(last_cost),
                "visited": to_plain(last_visited),
                "time_ms": avg_ms
            })
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)