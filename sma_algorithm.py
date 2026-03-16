
import csv
import ast
import math
import heapq
import itertools
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple
from collections import defaultdict


# =========================
# 1) LOAD GRAPH FROM CSV
# =========================
def load_graph(nodes_path: str, edges_path: str, time_slot: int):
    """
    time_slot: 1..48

    Return:
        coords[node_id] = (lat, lon)
        adj[u] = [(v, weight_at_time_slot), ...]
        edge_lookup[(u, v)] = {
            "osmid": edge id,
            "weight": ...,
            "length": ...
        }
    """
    if not (1 <= time_slot <= 48):
        raise ValueError("time_slot must be in [1, 48].")

    # load nodes
    coords: Dict[int, Tuple[float, float]] = {}
    with open(nodes_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            node_id = int(row["osmid"])
            lat = float(row["y"])
            lon = float(row["x"])
            coords[node_id] = (lat, lon)

    # load edges
    # nếu có nhiều edge cùng u->v thì lấy edge có weight nhỏ nhất tại time_slot đó
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
# 2) HAVERSINE HEURISTIC
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
# 3) SEARCH NODE FOR SMA*
# =========================
@dataclass
class SearchNode:
    state: int
    g: float
    h: float
    f: float
    parent: Optional["SearchNode"] = None
    children: List["SearchNode"] = field(default_factory=list)
    best_forgotten: float = math.inf
    active: bool = True
    uid: int = 0


def reconstruct_path(node: SearchNode) -> List[int]:
    path = []
    while node is not None:
        path.append(node.state)
        node = node.parent
    return path[::-1]


def is_ancestor(node: Optional[SearchNode], state: int) -> bool:
    """
    Tránh cycle trên cùng nhánh tìm kiếm
    """
    while node is not None:
        if node.state == state:
            return True
        node = node.parent
    return False


def choose_best_leaf(open_leaves: Dict[int, SearchNode]) -> SearchNode:
    """
    Chọn leaf tốt nhất:
    - f nhỏ nhất
    - h nhỏ hơn ưu tiên
    - g lớn hơn ưu tiên khi tie
    """
    return min(open_leaves.values(), key=lambda n: (n.f, n.h, -n.g, n.uid))


def choose_worst_leaf(open_leaves: Dict[int, SearchNode], root_uid: int) -> Optional[SearchNode]:
    """
    Chọn leaf tệ nhất để prune khi vượt memory.
    Không prune root nếu có thể tránh.
    """
    candidates = [n for n in open_leaves.values() if n.uid != root_uid]
    if not candidates:
        return None
    return max(candidates, key=lambda n: (n.f, -n.g, -n.uid))


def backup_from(node: Optional[SearchNode], open_leaves: Dict[int, SearchNode]) -> None:
    """
    Backup f từ con lên cha theo tinh thần SMA*
    """
    while node is not None:
        if node.children:
            best_child_f = min(child.f for child in node.children)
            node.f = max(node.g + node.h, min(best_child_f, node.best_forgotten))
            open_leaves.pop(node.uid, None)  # internal node không nằm trong open leaf
        else:
            node.f = max(node.g + node.h, node.best_forgotten)
            if node.active:
                open_leaves[node.uid] = node
        node = node.parent


def prune_worst_leaf(
    open_leaves: Dict[int, SearchNode],
    active_nodes: Dict[int, SearchNode],
    root_uid: int,
) -> bool:
    """
    Prune leaf xấu nhất khi vượt memory_limit
    """
    worst = choose_worst_leaf(open_leaves, root_uid)
    if worst is None:
        return False

    open_leaves.pop(worst.uid, None)
    active_nodes.pop(worst.uid, None)
    worst.active = False

    parent = worst.parent
    if parent is not None:
        parent.best_forgotten = min(parent.best_forgotten, worst.f)
        parent.children = [c for c in parent.children if c.uid != worst.uid]
        backup_from(parent, open_leaves)

    return True


# =========================
# 4) SMA* SEARCH
# =========================
def sma_star_shortest_path(
    coords: Dict[int, Tuple[float, float]], # Nhận từ memory
    adj: Dict[int, List[Tuple[int, float]]], # Nhận từ memory
    start: int,
    goal: int,
    memory_limit: int = 10000,
) -> Tuple[Optional[List[int]], float, int]:
    
    if start not in coords or goal not in coords:
        return None, math.inf, 0

    if start == goal:
        return [start], 0.0, 0

    goal_lat, goal_lon = coords[goal]
    def heuristic(node_id: int) -> float:
        lat, lon = coords[node_id]
        # Gọi hàm haversine_m của bạn ở đây
        return haversine_m(lat, lon, goal_lat, goal_lon)
    uid_gen = itertools.count(1)

    root = SearchNode(
        state=start,
        g=0.0,
        h=heuristic(start),
        f=heuristic(start),
        uid=next(uid_gen),
    )

    open_leaves: Dict[int, SearchNode] = {root.uid: root}
    active_nodes: Dict[int, SearchNode] = {root.uid: root}

    # Giữ tinh thần g(n) theo Dijkstra:
    # chỉ giữ đường đi tốt hơn tới cùng 1 state
    best_g_seen: Dict[int, float] = {start: 0.0}

    # số node đã duyệt / expanded
    visited_count = 0

    while open_leaves:
        best = choose_best_leaf(open_leaves)

        if math.isinf(best.f):
            return None, math.inf, visited_count

        # tính là đã duyệt khi node được lấy ra để expand/check
        visited_count += 1

        if best.state == goal:
            return reconstruct_path(best), best.g, visited_count,

        open_leaves.pop(best.uid, None)
        successors = adj.get(best.state, [])
        generated_any = False

        if not successors:
            best.f = math.inf
            backup_from(best, open_leaves)
            continue

        for succ, edge_cost in successors:
            if is_ancestor(best, succ):
                continue

            new_g = best.g + edge_cost

            # g(n) kiểu Dijkstra: bỏ qua đường đi không tốt hơn
            if new_g >= best_g_seen.get(succ, math.inf) - 1e-12:
                continue
            best_g_seen[succ] = new_g

            child_h = heuristic(succ)
            child_f = max(best.f, new_g + child_h)

            child = SearchNode(
                state=succ,
                g=new_g,
                h=child_h,
                f=child_f,
                parent=best,
                uid=next(uid_gen),
            )

            best.children.append(child)
            active_nodes[child.uid] = child
            open_leaves[child.uid] = child
            generated_any = True

            # enforce memory limit = 200
            while len(active_nodes) > memory_limit:
                if not prune_worst_leaf(open_leaves, active_nodes, root.uid):
                    break

        if not generated_any:
            best.f = math.inf

        backup_from(best, open_leaves)

    return reconstruct_path(best), best.g, visited_count

# =========================
# 5) A* origin 
# =========================

def a_star_search(coords, adj, start, goal):
    # Priority Queue: (f_score, current_node)
    open_set = []
    goal_lat, goal_lon = coords[goal]
    
    def get_h(node):
        lat, lon = coords[node]
        return haversine_m(lat, lon, goal_lat, goal_lon)

    heapq.heappush(open_set, (get_h(start), start))
    
    came_from = {}
    g_score = {node: float('inf') for node in coords}
    g_score[start] = 0
    
    visited_count = 0

    while open_set:
        current_f, current = heapq.heappop(open_set)
        visited_count += 1

        if current == goal:
            # Tái tạo đường đi
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(start)
            return path[::-1], g_score[goal], visited_count

        for neighbor, weight in adj.get(current, []):
            tentative_g = g_score[current] + weight
            
            if tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score = tentative_g + get_h(neighbor)
                heapq.heappush(open_set, (f_score, neighbor))
                
    return None, float('inf'), visited_count

# =========================
# 6) Dijkstra Search Algorithm
# =========================

def dijkstra_search(coords, adj, start, goal):
    # Priority Queue: (distance, current_node)
    open_set = [(0, start)]
    
    came_from = {}
    distances = {node: float('inf') for node in coords}
    distances[start] = 0
    
    visited_count = 0

    while open_set:
        current_dist, current = heapq.heappop(open_set)
        
        # Nếu đã tìm thấy đường ngắn hơn trước đó, bỏ qua
        if current_dist > distances[current]:
            continue
            
        visited_count += 1

        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(start)
            return path[::-1], distances[goal], visited_count

        for neighbor, weight in adj.get(current, []):
            distance = current_dist + weight
            
            if distance < distances[neighbor]:
                distances[neighbor] = distance
                came_from[neighbor] = current
                heapq.heappush(open_set, (distance, neighbor))
                
    return None, float('inf'), visited_count

# =========================
# 7) NODE PATH -> EDGE IDS
# =========================
def node_path_to_edge_ids(
    node_path: List[int],
    edge_lookup: Dict[Tuple[int, int], dict],
) -> List[str]:
    edge_id_list = []

    for a, b in zip(node_path, node_path[1:]):
        edge = edge_lookup.get((a, b))
        if edge is None:
            edge_id_list.append(None)
        else:
            edge_id_list.append(edge["osmid"])

    return edge_id_list


# =========================
# 8) MAIN - INPUT / OUTPUT
# =========================
def main():
    nodes_path = r"D:\LapTrinh\astar-traffic-hcmc-routing\data\nodes.csv"
    edges_path = r"D:\LapTrinh\astar-traffic-hcmc-routing\data\edges.csv"

    start = int(input("Nhap start node: ").strip())
    goal = int(input("Nhap goal node: ").strip())
    time_slot = int(input("Nhap khoang thoi gian (1..48): ").strip())

    path, total_cost, visited_count, edge_lookup = sma_star_shortest_path(
        nodes_path=nodes_path,
        edges_path=edges_path,
        start=start,
        goal=goal,
        time_slot=time_slot,
        memory_limit=200,
    )

    if path is None:
        print("Khong tim duoc duong di voi gioi han bo nho hien tai.")
    else:
        edge_id_list = node_path_to_edge_ids(path, edge_lookup)

        print("Tong chi phi:", total_cost)
        print("So node da duyet:", visited_count)
        print("ID cac canh:", edge_id_list)

        # nếu vẫn muốn xem node path để debug thì bỏ comment dòng dưới
        print("Node path:", path)


if __name__ == "__main__":
    main()