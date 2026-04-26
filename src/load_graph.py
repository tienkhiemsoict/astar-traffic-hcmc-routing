import csv
import ast
from collections import defaultdict

def load_graph(nodes_path, edges_path, time_slot):
    # Giữ nguyên logic của bạn nhưng đảm bảo đầu vào là path (đường dẫn)
    coords = {}
    with open(nodes_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            coords[int(row["osmid"])] = (float(row["y"]), float(row["x"]))

    idx = time_slot - 1
    adj_map = defaultdict(dict)
    edge_lookup = {}

    with open(edges_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            u, v = int(row["u"]), int(row["v"])
            # Tránh lỗi nếu cột weight không phải dạng list
            try:
                weights = ast.literal_eval(row["weight"])
                weight = float(weights[idx])
            except:
                weight = float(row.get("length", 1)) # Fallback nếu lỗi

            if v not in adj_map[u] or weight < adj_map[u][v]:
                adj_map[u][v] = weight
                edge_lookup[(u, v)] = {
                    "osmid": row["osmid"],
                    "weight": weight,
                    "length": float(row["length"])
                }

    adj = {u: list(v_map.items()) for u, v_map in adj_map.items()}
    return coords, adj, edge_lookup