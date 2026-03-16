import csv
import ast
import math
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

def load_graph(nodes_path: str, edges_path: str, time_slot: int):
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

