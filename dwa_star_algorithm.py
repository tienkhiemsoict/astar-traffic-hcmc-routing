import csv
import ast
import math
import heapq
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from load_graph import load_graph

# =========================
# 1) HAVERSINE
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
# 2) RECONSTRUCT PATH
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
# 3) DWA* SEARCH
# =========================
def dwa_star_search(
    coords: Dict[int, Tuple[float, float]], 
    adj: Dict[int, List[Tuple[int, float]]], 
    start: int,
    goal: int,
    max_expansion: int = 200000,
) -> Tuple[Optional[List[int]], float, int]:
    
    if start not in coords or goal not in coords:
        return None, math.inf, 0

    if start == goal:
        return [start], 0.0, 1

    start_lat, start_lon = coords[start]
    goal_lat, goal_lon = coords[goal]
    start_goal_dist = haversine_m(start_lat, start_lon, goal_lat, goal_lon)

    def heuristic(node_id: int) -> float:
        if start_goal_dist == 0:
            return 0.0
        cur_lat, cur_lon = coords[node_id]
        cur_goal_dist = haversine_m(cur_lat, cur_lon, goal_lat, goal_lon)
        # Công thức: h(n) = (1 + cur_goal_dist / start_goal_dist) * cur_goal_dist
        return (1.0 + cur_goal_dist / start_goal_dist) * cur_goal_dist


    g_score: Dict[int, float] = {start: 0.0}
    came_from: Dict[int, int] = {}
    start_h = heuristic(start)
    open_heap: List[Tuple[float, float, int]] = []
    heapq.heappush(open_heap, (start_h, start_h, start))

    visited_count = 0
    closed_set = set()

    while open_heap:
        current_f, current_h, current = heapq.heappop(open_heap)

        if current in closed_set:
            continue


        closed_set.add(current)
        visited_count += 1

        if current == goal:
            path = []
            curr = goal
            while curr in came_from:
                path.append(curr)
                curr = came_from[curr]
            path.append(start)
            return path[::-1], g_score[goal], visited_count


        if visited_count > max_expansion:
            return None, math.inf, visited_count

        for neighbor, edge_cost in adj.get(current, []):
            if neighbor in closed_set:
                continue

            tentative_g = g_score[current] + edge_cost

            if tentative_g < g_score.get(neighbor, math.inf):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                h_val = heuristic(neighbor)
                f_val = tentative_g + h_val
                heapq.heappush(open_heap, (f_val, h_val, neighbor))

    return None, math.inf, visited_count