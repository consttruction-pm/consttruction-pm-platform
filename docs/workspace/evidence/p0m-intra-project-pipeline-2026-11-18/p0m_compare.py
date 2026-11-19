"""Build the P0-M comparison table from the raw matrix JSON."""
from __future__ import annotations

import json
import sys

rows = json.load(open(sys.argv[1]))
out_path = sys.argv[2]
sizes = sorted({row["size"] for row in rows})
modes = ["pipeline", "posthoc"]
comparison = []
for size in sizes:
    entry = {"size": size, "modes": {}}
    hashes = {row["sha256"] for row in rows if row["size"] == size}
    entry["canonical_hash"] = sorted(hashes)[0]
    entry["all_hashes_identical"] = len(hashes) == 1
    for mode in modes:
        subset = {
            row["workers"]: row
            for row in rows
            if row["size"] == size and row["mode"] == mode
        }
        baseline = subset[1]
        speeds = {}
        for workers, row in sorted(subset.items()):
            speeds[workers] = {
                "wall_median_ms": row["wall_median_ms"],
                "wall_p95_ms": row["wall_p95_ms"],
                "speedup": round(baseline["wall_median_ms"] / row["wall_median_ms"], 3),
                "efficiency": round(
                    (baseline["wall_median_ms"] / row["wall_median_ms"]) / workers, 3
                ),
                "total_cpu_median_ms": row["total_cpu_median_ms"],
                "utilization": row["utilization"],
                "child_worker_utilization": row["child_worker_utilization"],
                "parent_cpu_median_ms": row["parent_cpu_median_ms"],
                "children_cpu_median_ms": row["children_cpu_median_ms"],
                "parent_peak_rss_kb": row["parent_peak_rss_kb"],
                "children_max_rss_kb": row["children_max_rss_kb"],
                "external_peak_children_rss_kb": row[
                    "external_peak_children_rss_kb"
                ],
                "external_peak_tree_rss_kb": row["external_peak_tree_rss_kb"],
                "ipc_submit_median_ms": row["ipc_submit_median_ms"],
                "drain_wait_median_ms": row["drain_wait_median_ms"],
                "pipeline_batches": row["pipeline_batches"],
                "batch_payload_bytes_total": row["batch_payload_bytes_total"],
                "batch_payload_bytes_mean": row["batch_payload_bytes_mean"],
                "batch_payload_activities_mean": row["batch_payload_activities_mean"],
                "sha256": row["sha256"],
            }
        entry["modes"][mode] = speeds
    comparison.append(entry)

json.dump(comparison, open(out_path, "w"), indent=1)

print("| size | mode | workers | median ms | p95 ms | speedup | efficiency | "
      "total CPU ms | util | child-worker util | parent RSS MB | child RSS MB (max) | "
      "IPC submit ms | drain ms |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for entry in comparison:
    for mode in modes:
        for workers, row in sorted(entry["modes"][mode].items()):
            print(
                f"| {entry['size']} | {mode} | {workers} | {row['wall_median_ms']} | "
                f"{row['wall_p95_ms']} | {row['speedup']} | {row['efficiency']} | "
                f"{row['total_cpu_median_ms']} | {row['utilization']} | "
                f"{row['child_worker_utilization']} | "
                f"{round(row['parent_peak_rss_kb'] / 1024, 1)} | "
                f"{round(max(row['children_max_rss_kb'], row['external_peak_children_rss_kb']) / 1024, 1)} | "
                f"{row['ipc_submit_median_ms']} | {row['drain_wait_median_ms']} |"
            )
print()
for entry in comparison:
    print(
        entry["size"],
        "hashes identical:",
        entry["all_hashes_identical"],
        entry["canonical_hash"][:16],
    )
