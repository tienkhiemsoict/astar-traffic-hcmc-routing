import ast
import math
import heapq
from typing import Dict, List, Tuple, Optional
# =========================
# 1) HAVERSINE
# =========================
def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:

    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dlam = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = (math.sin(dphi / 2) ** 2 + 
         math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))

# =========================
# 2) A* origin 
# =========================
def a_star_search(
    coords: Dict[int, Tuple[float, float]], 
    adj: Dict[int, List[Tuple[int, float]]], # Giữ nguyên kiểu List[Tuple] như file cũ
    start: int,
    goal: int,
    max_expansion: int = 200000,
) -> Tuple[Optional[List[int]], float, int]:
    
    if start not in coords or goal not in coords:
        return None, math.inf, 0
    if start == goal:
        return [start], 0.0, 1

    # Pre-fetch tọa độ mục tiêu để tăng tốc truy cập
    goal_lat, goal_lon = coords[goal]
    start_lat, start_lon = coords[start]
    
    # Tính khoảng cách tổng để làm tham số cho DWA* (Dùng Haversine 1 lần duy nhất)
    start_goal_dist = haversine_m(start_lat, start_lon, goal_lat, goal_lon)
    if start_goal_dist == 0: start_goal_dist = 0.0001 # Tránh chia cho 0

    # TỐI ƯU: Hệ số chuyển đổi độ sang mét xấp xỉ cho TP.HCM
    # Giúp thay thế hàm Haversine nặng nề bằng công thức Pytago siêu nhanh
    deg_to_m = 111319.0
    lon_factor = math.cos(math.radians(goal_lat))

    # Hàm heuristic nội bộ đã tối ưu hóa phép tính
    def fast_heuristic(node_id: int) -> float:
        n_lat, n_lon = coords[node_id]
        # Pytago xấp xỉ trên mặt phẳng (sai số cực thấp ở quy mô thành phố)
        dy = (n_lat - goal_lat) * deg_to_m
        dx = (n_lon - goal_lon) * deg_to_m * lon_factor
        cur_goal_dist = math.sqrt(dx*dx + dy*dy)
        
        # Công thức Dynamic Weight: h(n) = (1 + 0.5 * d_cur/d_total) * d_cur
        return cur_goal_dist + start_goal_dist

    # Khởi tạo các cấu trúc dữ liệu
    g_score: Dict[int, float] = {start: 0.0}
    came_from: Dict[int, int] = {}
    
    # Priority Queue: (f_score, current_node)
    start_h = fast_heuristic(start)
    open_heap: List[Tuple[float, int]] = [(start_h, start)]
    
    closed_set = set()
    visited_count = 0
    
    # Cache các hàm build-in của Python để chạy nhanh hơn trong vòng lặp
    push = heapq.heappush
    pop = heapq.heappop

    while open_heap:
        current_f, current = pop(open_heap)

        if current in closed_set:
            continue
        
        if current == goal:
            # Truy hồi đường đi (Reconstruct Path)
            path = []
            curr = goal
            while curr in came_from:
                path.append(curr)
                curr = came_from[curr]
            path.append(start)
            return path[::-1], g_score[goal], visited_count

        closed_set.add(current)
        visited_count += 1

        if visited_count > max_expansion:
            return None, math.inf, visited_count

        # Duyệt láng giềng theo cấu trúc cũ: List[Tuple[neighbor, cost]]
        for neighbor, edge_cost in adj.get(current, []):
            if neighbor in closed_set:
                continue

            tentative_g = g_score[current] + edge_cost

            # Kiểm tra g_score nhanh hơn bằng cách dùng .get()
            if tentative_g < g_score.get(neighbor, math.inf):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                
                # f(n) = g(n) + h(n)
                f_val = tentative_g + fast_heuristic(neighbor)
                push(open_heap, (f_val, neighbor))

    return None, math.inf, visited_count