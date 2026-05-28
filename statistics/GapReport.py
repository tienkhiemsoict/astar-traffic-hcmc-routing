import argparse
import csv
from pathlib import Path

BUCKETS = ["< 5 km", "5 <= distance < 10 km", ">= 10 km"]
ROWS = [
    ("Dijkstra", "Dijkstra"),
    ("A* Origin", "A* Origin"),
    ("DWA* (c=0.5)", "DWA* base"),
    ("DWA* (c=1.0)", "DWA* c=1.0"),
    ("DWA* (c=1.5)", "DWA* c=1.5"),
    ("DWA* (c=2.0)", "DWA* c=2.0"),
]


def load_summary(path: Path):
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        required = {"bucket", "algorithm", "avg_distance_km", "avg_visited_nodes", "avg_runtime_ms"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing columns: {sorted(missing)}")
        return {
            (row["bucket"].strip(), row["algorithm"].strip()): {
                "distance": float(row["avg_distance_km"]) if row["avg_distance_km"] else None,
                "nodes": float(row["avg_visited_nodes"]) if row["avg_visited_nodes"] else None,
                "time": float(row["avg_runtime_ms"]) if row["avg_runtime_ms"] else None,
            }
            for row in reader
        }


def gap(cur, base):
    return None if cur is None or base in (None, 0) else abs((cur - base) / base)


def build_report(data, out_path: Path):
    wb = Workbook()
    comp = wb.active
    comp.title = "Comparison"
    comp.append(["bucket", "algorithm", "gap", "nodes", "time"])

    for bucket in BUCKETS:
        base = data.get((bucket, "A* Origin"), {})
        for label, key in ROWS:
            current = data.get((bucket, key), {})
            comp.append([
                bucket,
                label,
                gap(current.get("distance"), base.get("distance")),
                current.get("nodes"),
                current.get("time"),
            ])

    raw = wb.create_sheet("Input_Summary")
    raw.append(["bucket", "algorithm", "avg_distance_km", "avg_visited_nodes", "avg_runtime_ms"])
    for bucket in BUCKETS:
        for _, key in ROWS:
            row = data.get((bucket, key), {})
            raw.append([bucket, key, row.get("distance"), row.get("nodes"), row.get("time")])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)


def main():
    parser = argparse.ArgumentParser(description="Build comparison gap report.")
    parser.add_argument("--summary-csv", required=True)
    parser.add_argument("--output", default="algorithm_comparison_gap_v4.xlsx")
    args = parser.parse_args()

    build_report(load_summary(Path(args.summary_csv)), Path(args.output))
    print("Created:", args.output)


if __name__ == "__main__":
    main()
