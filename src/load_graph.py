import csv
import ast
from collections import defaultdict

def load_graph(nodes_path, edges_path, time_slot):
    # Tải nodes vào dict tọa độ
    coords = {}
    with open(nodes_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            coords[int(row["osmid"])] = (float(row["y"]), float(row["x"]))

    # Tải edges với weight theo time_slot
    idx = time_slot - 1
    adj_map = defaultdict(dict)
    edge_lookup = {}

    with open(edges_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            u, v = int(row["u"]), int(row["v"])
            weight = float(ast.literal_eval(row["weight"])[idx])

            # Lọc cạnh tối ưu (weight nhỏ nhất nếu có multi-edges)
            if v not in adj_map[u] or weight < adj_map[u][v]:
                adj_map[u][v] = weight
                edge_lookup[(u, v)] = {
                    "osmid": row["osmid"],
                    "weight": weight,
                    "length": float(row["length"])
                }

    adj = {u: list(v_map.items()) for u, v_map in adj_map.items()}
    return coords, adj, edge_lookup

