import argparse
import csv
import importlib.util
import inspect
import random
import time
from pathlib import Path

ALGO_SPECS = {
    "dijkstra": {"display": "Dijkstra", "function": "dijkstra_search", "files": ["Dijkstra.py"]},
    "astar": {"display": "A* Origin", "function": "a_star_search", "files": ["AStarOrigin.py"]},
    "dwa": {"display": "DWA* base", "function": "dwa_star_search", "files": ["DWAStar.py"]},
}

BUCKET_FILES = {
    "distance_lt_5km.csv": lambda d: d < 5,
    "distance_5_to_10km.csv": lambda d: 5 <= d < 10,
    "distance_gt_10km.csv": lambda d: d >= 10,
}


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise ImportError(f"Cannot load {path}")
    spec.loader.exec_module(module)
    return module


def locate_algorithm(key: str, project_dir: Path):
    spec = ALGO_SPECS[key]
    for path in project_dir.rglob("*.py"):
        if path.name in spec["files"]:
            module = load_module(path)
            func = getattr(module, spec["function"], None)
            if func:
                return {"key": key, "display": spec["display"], "func": func}
    raise FileNotFoundError(f"Algorithm {key} not found")


def locate_load_graph(project_dir: Path):
    for name in ("load_graph.py", "app.py"):
        path = project_dir / name
        if path.exists():
            module = load_module(path)
            func = getattr(module, "load_graph", None)
            if func:
                return func
    raise FileNotFoundError("Cannot find load_graph()")


def call_load_graph(func, nodes, edges, slot, undirected):
    sig = inspect.signature(func)
    return func(nodes, edges, slot, directed=not undirected) if "directed" in sig.parameters else func(nodes, edges, slot)


def run_algorithm(func, coords, adj, start, goal):
    t0 = time.perf_counter()
    path, distance_m, visited = func(coords, adj, start, goal)
    return {
        "path": path,
        "distance_km": float(distance_m) / 1000.0 if distance_m is not None else None,
        "visited": int(visited) if visited is not None else None,
        "runtime_ms": round((time.perf_counter() - t0) * 1000.0, 6),
    }


def append_row(path: Path, row: dict, headers: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not path.exists()
    with path.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        if new_file:
            writer.writeheader()
        writer.writerow(row)


def sample_pair(coords, adj, algos, seen, directed):
    node_ids = list(coords.keys())
    for _ in range(5000):
        start, goal = random.sample(node_ids, 2)
        key = (start, goal) if directed else tuple(sorted((start, goal)))
        if key in seen:
            continue
        result = {}
        for algo in algos:
            stats = run_algorithm(algo["func"], coords, adj, start, goal)
            if stats["path"] is None:
                break
            result[algo["key"]] = stats
        else:
            seen.add(key)
            return start, goal, result
    raise RuntimeError("Cannot find a successful pair")


def classify_bucket(distance_km):
    for name, fn in BUCKET_FILES.items():
        if fn(distance_km):
            return name
    return "distance_gt_10km.csv"


def parse_args():
    p = argparse.ArgumentParser(description="Run route benchmarks and append results to bucket CSV files.")
    p.add_argument("--nodes", default="data/nodes.csv")
    p.add_argument("--edges", default="data/edges.csv")
    p.add_argument("--time-slot", type=int, required=True)
    p.add_argument("--trials", type=int, default=1)
    p.add_argument("--algorithms", nargs="+", default=["dijkstra", "astar", "dwa"])
    p.add_argument("--output-dir", default="distance_bucket_results")
    return p.parse_args()


def main():
    args = parse_args()
    project_dir = Path.cwd()
    algos = [locate_algorithm(k, project_dir) for k in args.algorithms]
    load_graph = locate_load_graph(project_dir)
    coords, adj = call_load_graph(load_graph, args.nodes, args.edges, args.time_slot, undirected=False)[:2]
    seen = set()
    headers = [
        "timestamp", "time_slot", "start_node", "goal_node", "bucket", "reference_distance_km"
    ]
    for idx, algo in enumerate(algos, 1):
        headers += [
            f"algo{idx}_key",
            f"algo{idx}_name",
            f"algo{idx}_distance_km",
            f"algo{idx}_visited",
            f"algo{idx}_runtime_ms",
        ]

    for i in range(1, args.trials + 1):
        start, goal, results = sample_pair(coords, adj, algos, seen, directed=False)
        ref_key = "dijkstra" if "dijkstra" in results else next(iter(results))
        bucket = classify_bucket(results[ref_key]["distance_km"])
        row = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "time_slot": args.time_slot,
            "start_node": start,
            "goal_node": goal,
            "bucket": bucket,
            "reference_distance_km": results[ref_key]["distance_km"],
        }
        for idx, algo in enumerate(algos, 1):
            stats = results[algo["key"]]
            row.update({
                f"algo{idx}_key": algo["key"],
                f"algo{idx}_name": algo["display"],
                f"algo{idx}_distance_km": stats["distance_km"],
                f"algo{idx}_visited": stats["visited"],
                f"algo{idx}_runtime_ms": stats["runtime_ms"],
            })
        append_row(Path(args.output_dir) / bucket, row, headers)
        print(f"[{i}/{args.trials}] {start}->{goal} bucket={bucket}")


if __name__ == "__main__":
    main()
