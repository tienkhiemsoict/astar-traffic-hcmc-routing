import csv
import ast
import math
import heapq
from typing import Dict, List, Tuple, Optional
from collections import defaultdict


# =========================
# 1) LOAD GRAPH FROM CSV
# =========================
def load_graph(nodes_path: str, edges_path: str, time_slot: int):
    """
    time_slot: 1..48

    Return:
        coords[node_id] = (lat, lon)
        adj[u] = [(v, weight_at_slot), ...]
        edge_lookup[(u, v)] = {
            "osmid": edge id,
            "weight": ...,
            "length": ...
        }

    Nếu có nhiều edge cùng u->v, giữ edge có weight nhỏ nhất ở time_slot đó.
    """
    if not (1 <= time_slot <= 48):
        raise ValueError("time_slot must be in [1, 48].")

    coords: Dict[int, Tuple[float, float]] = {}
    with open(nodes_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            node_id = int(row["osmid"])
            lat = float(row["y"])
            lon = float(row["x"])
            coords[node_id] = (lat, lon)

    idx = time_slot - 1
    adj_min: Dict[int, Dict[int, float]] = defaultdict(dict)
    edge_lookup: Dict[Tuple[int, int], dict] = {}

    with open(edges_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            u = int(row["u"])
            v = int(row["v"])
            weights = ast.literal_eval(row["weight"])
            w = float(weights[idx])

            old = adj_min[u].get(v)
            if old is None or w < old:
                adj_min[u][v] = w
                edge_lookup[(u, v)] = {
                    "osmid": row["osmid"],
                    "weight": w,
                    "length": float(row["length"]),
                }

    adj = {u: list(v_map.items()) for u, v_map in adj_min.items()}
    return coords, adj, edge_lookup


# =========================
# 2) HAVERSINE
# =========================
def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Haversine distance in meters
    """
    R = 6371000.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(a))


# =========================
# 3) RECONSTRUCT PATH
# =========================
def reconstruct_node_path(came_from: Dict[int, int], goal: int) -> List[int]:
    path = [goal]
    cur = goal
    while cur in came_from:
        cur = came_from[cur]
        path.append(cur)
    path.reverse()
    return path


def node_path_to_edge_ids(
    node_path: List[int],
    edge_lookup: Dict[Tuple[int, int], dict],
) -> List[Optional[str]]:
    edge_id_list: List[Optional[str]] = []
    for a, b in zip(node_path, node_path[1:]):
        edge = edge_lookup.get((a, b))
        edge_id_list.append(None if edge is None else edge["osmid"])
    return edge_id_list


# =========================
# 4) A* SEARCH
# =========================
def a_star_shortest_path(
    nodes_path: str,
    edges_path: str,
    start: int,
    goal: int,
    time_slot: int,
    max_expansion: int = 200000,
) -> Tuple[Optional[List[int]], float, int, Dict[Tuple[int, int], dict]]:
    coords, adj, edge_lookup = load_graph(nodes_path, edges_path, time_slot)

    if start not in coords:
        raise ValueError(f"Start node {start} does not exist in nodes.csv")
    if goal not in coords:
        raise ValueError(f"Goal node {goal} does not exist in nodes.csv")

    if start == goal:
        return [start], 0.0, 1, edge_lookup

    start_lat, start_lon = coords[start]
    goal_lat, goal_lon = coords[goal]

    start_goal_dist = haversine_m(start_lat, start_lon, goal_lat, goal_lon)

    def heuristic(node_id: int) -> float:
        cur_lat, cur_lon = coords[node_id]
        cur_goal_dist = haversine_m(cur_lat, cur_lon, goal_lat, goal_lon)

        # Theo đúng công thức user yêu cầu:
        # h(n) = (1 + cur_goal_dist / start_goal_dist) * start_goal_dist
        # xử lý an toàn nếu start_goal_dist = 0
        if start_goal_dist == 0:
            return 0.0

        return (1.0 + cur_goal_dist / start_goal_dist) * start_goal_dist

    g_score: Dict[int, float] = {start: 0.0}
    came_from: Dict[int, int] = {}

    # heap item: (f, h, node)
    open_heap: List[Tuple[float, float, int]] = []
    start_h = heuristic(start)
    heapq.heappush(open_heap, (start_h, start_h, start))

    visited_count = 0
    closed_set = set()

    while open_heap:
        current_f, current_h, current = heapq.heappop(open_heap)

        if current in closed_set:
            continue

        expected_f = g_score[current] + heuristic(current)
        if current_f > expected_f + 1e-9:
            continue

        closed_set.add(current)
        visited_count += 1

        if visited_count > max_expansion:
            print(f"Search stopped: exceeded max_expansion={max_expansion}")
            return None, math.inf, visited_count, edge_lookup

        if visited_count % 5000 == 0:
            print(
                f"expanded={visited_count}, "
                f"open_size={len(open_heap)}, "
                f"current_state={current}, "
                f"current_f={current_f:.3f}"
            )

        if current == goal:
            path = reconstruct_node_path(came_from, goal)
            return path, g_score[goal], visited_count, edge_lookup

        for neighbor, edge_cost in adj.get(current, []):
            if neighbor in closed_set:
                continue

            tentative_g = g_score[current] + edge_cost

            if tentative_g < g_score.get(neighbor, math.inf):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                h = heuristic(neighbor)
                f = tentative_g + h
                heapq.heappush(open_heap, (f, h, neighbor))

    return None, math.inf, visited_count, edge_lookup


# =========================
# 5) MAIN
# =========================
def main():
    nodes_path = "nodes.csv"
    edges_path = "edges.csv"

    start = int(input("Nhap start node: ").strip())
    goal = int(input("Nhap goal node: ").strip())
    time_slot = int(input("Nhap khoang thoi gian (1..48): ").strip())

    node_path, total_cost, visited_count, edge_lookup = a_star_shortest_path(
        nodes_path=nodes_path,
        edges_path=edges_path,
        start=start,
        goal=goal,
        time_slot=time_slot,
        max_expansion=200000,
    )

    if node_path is None:
        print("Khong tim duoc duong di.")
        print("So node da duyet:", visited_count)
        return

    

    print("Tong chi phi:", total_cost)
    print("So node da duyet:", visited_count)
    print("Node path:", node_path)
    


if __name__ == "__main__":
    main()