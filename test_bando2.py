import folium
import pandas as pd
from shapely import wkt
import math

def calculate_bearing(lat1, lon1, lat2, lon2):
    """Tính toán góc phương vị (bearing) giữa 2 điểm tọa độ"""
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    d_lon = lon2 - lon1
    y = math.sin(d_lon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(d_lon)
    bearing = math.atan2(y, x)
    
    # Chuyển đổi sang độ và chuẩn hóa về [0, 360)
    return (math.degrees(bearing) + 360) % 360

# ==========================================
# THAY BẰNG DANH SÁCH NODE PATH TỪ THUẬT TOÁN CỦA BẠN
# (Copy kết quả in ra từ dòng cuối của file tìm đường)
# ==========================================
node_path =  [411919545, 411919580, 6111679647, 2034589236, 6534620912, 3335337343, 6534620921, 6534620932, 10560232674, 10560232676, 10560232672, 10560232675, 10264812158, 9765777687, 9708695734, 9765777688, 7498869413, 411919360, 9824009360, 9722186805, 411926001, 411926537, 5763135348, 411926412, 5763135357, 411918830, 11845234638, 11845234636, 11845234637, 11845234639, 11845234652, 11845290166, 11845290237, 11845290082, 11845290083, 11871514859, 11870810042, 11870810040, 11870810039, 11870810368, 11871287740, 11870810420, 11870810205, 11870810328, 11871287738, 11870774528, 12157150905, 11870774526, 411925453, 411925919, 411925335, 5778360115, 411926667, 411925869, 5778300414, 5778300421, 5778300416, 411926607, 411926628, 2230864394, 411926208, 411926216, 411918820, 411918821, 11900708633, 5772143093, 5352258753, 11548439909, 11361224534, 11361224527, 5352258748, 5352258747, 411926233, 11361224537, 411921356, 6666386719, 411919061, 411920252, 10290606292, 11361224541, 11187287641, 11361224543, 411920249]

print("Đang khởi tạo bản đồ và đọc dữ liệu...")

# Load dữ liệu
nodes_df = pd.read_csv('data/nodes.csv').set_index('osmid')
edges_df = pd.read_csv('data/edges.csv')

# THAY ĐỔI QUAN TRỌNG: Tạo MultiIndex (u, v) để tra cứu chính xác hướng từ u sang v
edges_df.set_index(['u', 'v'], inplace=True)

# Lấy tọa độ điểm bắt đầu làm trung tâm bản đồ
if node_path and node_path[0] in nodes_df.index:
    center_lat = nodes_df.loc[node_path[0], 'y']
    center_lon = nodes_df.loc[node_path[0], 'x']
else:
    center_lat = nodes_df['y'].mean()
    center_lon = nodes_df['x'].mean()

m = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=15,
    tiles='CartoDB dark_matter'
)

path_group = folium.FeatureGroup(name="Shortest Path")

print("Đang vẽ đường đi theo đúng thứ tự Node...")

# Duyệt qua từng cặp đỉnh (u, v) liên tiếp trong mảng node_path
for i in range(len(node_path) - 1):
    u = node_path[i]
    v = node_path[i+1]
    
    print(f"Đang vẽ cạnh: {u} -> {v}")

    try:
        # Lấy dữ liệu của cạnh CHỈ THEO CHIỀU u -> v
        if (u, v) in edges_df.index:
            edge_data = edges_df.loc[(u, v)]
            
            # Nếu có nhiều đường nối giữa u và v (Multigraph), lấy đường đầu tiên
            if isinstance(edge_data, pd.DataFrame):
                edge_data = edge_data.iloc[0]

            # Xử lý tọa độ (Ưu tiên dùng geometry nếu có đường cong, không thì nối thẳng)
            if 'geometry' in edge_data and pd.notna(edge_data['geometry']):
                geom = wkt.loads(edge_data['geometry'])
                coords = [(lat, lon) for lon, lat in geom.coords]
            else:
                coords = [
                    (nodes_df.loc[u, 'y'], nodes_df.loc[u, 'x']),
                    (nodes_df.loc[v, 'y'], nodes_df.loc[v, 'x'])
                ]

            if not coords or len(coords) < 2:
                continue

            # Vẽ đoạn thẳng đỏ
            folium.PolyLine(
                locations=coords,
                color='red',
                weight=5,
                opacity=1.0
            ).add_to(path_group)

            # Vẽ 1 mũi tên duy nhất cho cạnh này
            mid_idx = len(coords) // 2
            lat_mid, lon_mid = coords[mid_idx]
            
            idx_prev = max(0, mid_idx - 1)
            lat_prev, lon_prev = coords[idx_prev]
            
            bearing = calculate_bearing(lat_prev, lon_prev, lat_mid, lon_mid)

            # Vẽ mũi tên bằng folium.RegularPolygonMarker
            folium.RegularPolygonMarker(
                location=(lat_mid, lon_mid),
                fill_color='white',
                fill_opacity=1.0,
                color='white',
                number_of_sides=3,
                radius=6,
                rotation=bearing - 90
            ).add_to(path_group)
        else:
            print(f"CẢNH BÁO: Không tìm thấy cạnh {u} -> {v} trong file edges.csv")

    except Exception as e:
        print(f"Lỗi khi xử lý đoạn {u} -> {v}: {e}")
        continue

# Thêm group vào bản đồ
path_group.add_to(m)

file_name = "map_edges_nodes.html"
m.save(file_name)

print("Đã lưu bản đồ:", file_name)