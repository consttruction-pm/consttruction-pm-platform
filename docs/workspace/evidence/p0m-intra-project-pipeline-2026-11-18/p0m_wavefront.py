"""P0-M wavefront cost model: measured level structure, serial pass cost and
measured per-barrier latency of a fork pool.

No scheduling is reimplemented here: the pass timings call the production
functions, and the barrier latency is a measured pool round trip (``identity``
in the child), which is the irreducible cost of one wavefront level.
"""
from __future__ import annotations

import importlib
import json
import multiprocessing
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path("/data/work/repo")
sys.path.insert(0, str(ROOT / "src"))

bf = importlib.import_module("construction_pm.scheduling.benchmark_fixtures")
ts = importlib.import_module("construction_pm.scheduling.time_schedule")


def _identity(value):
    return value


def level_stats(activities, relationships) -> dict:
    ids = [activity.id for activity in activities]
    preds = {value: 0 for value in ids}
    successors: dict[str, list[str]] = {value: [] for value in ids}
    for rel in relationships:
        preds[rel.successor_id] += 1
        successors[rel.predecessor_id].append(rel.successor_id)
    depth = {value: 0 for value in ids}
    ready = [value for value in ids if preds[value] == 0]
    while ready:
        current = ready.pop()
        for successor in successors[current]:
            depth[successor] = max(depth[successor], depth[current] + 1)
            preds[successor] -= 1
            if preds[successor] == 0:
                ready.append(successor)
    sizes = Counter(depth.values())
    ordered = [sizes[key] for key in sorted(sizes)]
    return {
        "depth": len(ordered),
        "width_max": max(ordered),
        "width_mean": round(len(ids) / len(ordered), 3),
        "level_count_with_width_1": sum(1 for value in ordered if value == 1),
    }


def barrier_latency_ms(children: int, rounds: int = 15) -> dict:
    context = multiprocessing.get_context("fork")
    pool = context.Pool(processes=children)
    try:
        pool.map(_identity, list(range(4)))  # warm-up
        samples = []
        for _ in range(rounds):
            start = time.perf_counter()
            pool.map(_identity, [0])
            samples.append((time.perf_counter() - start) * 1000)
    finally:
        pool.close()
        pool.join()
    return {
        "children": children,
        "median_ms": round(statistics.median(samples), 3),
        "min_ms": round(min(samples), 3),
    }


def main() -> None:
    size = int(sys.argv[1])
    out_path = sys.argv[2]
    rows = []
    for shape in ("dag", "chain", "fan", "wide", "mixed"):
        fixture = bf.time_network(size, shape)
        forward, backward, floats = [], [], []
        for _ in range(3):
            start = time.perf_counter()
            early = ts.time_forward_pass(
                fixture.activities,
                fixture.relationships,
                fixture.project_start,
                fixture.registry,
            )
            forward.append((time.perf_counter() - start) * 1000)
            finish = fixture.project_finish or max(i.finish for i in early.values())
            start = time.perf_counter()
            late = ts.time_backward_pass(
                fixture.activities,
                fixture.relationships,
                early,
                finish,
                fixture.registry,
            )
            backward.append((time.perf_counter() - start) * 1000)
            start = time.perf_counter()
            ts.calculate_time_floats(
                fixture.activities,
                fixture.relationships,
                early,
                late,
                fixture.registry,
            )
            floats.append((time.perf_counter() - start) * 1000)
        stats = level_stats(fixture.activities, fixture.relationships)
        activities = len(fixture.activities)
        rows.append(
            {
                "shape": shape,
                "size": activities,
                "relationships": len(fixture.relationships),
                **stats,
                "forward_median_ms": round(statistics.median(forward), 2),
                "backward_median_ms": round(statistics.median(backward), 2),
                "float_median_ms": round(statistics.median(floats), 2),
                "forward_us_per_activity": round(
                    statistics.median(forward) * 1000 / activities, 3
                ),
                "backward_us_per_activity": round(
                    statistics.median(backward) * 1000 / activities, 3
                ),
            }
        )
        print(rows[-1], flush=True)
    barriers = [barrier_latency_ms(count) for count in (1, 3)]
    payload = {"size": size, "shapes": rows, "barrier": barriers}
    json.dump(payload, open(out_path, "w"), indent=1)
    # Cost model: a level-synchronous pass needs one barrier per level; its
    # irreducible overhead is depth * barrier latency.
    for row in rows:
        barrier = barriers[-1]["median_ms"]
        row["barrier_count"] = row["depth"]
        row["barrier_overhead_ms"] = round(row["depth"] * barrier, 2)
        row["barrier_overhead_vs_forward"] = round(
            row["barrier_overhead_ms"] / row["forward_median_ms"], 3
        )
        print(
            f"{row['shape']}: depth {row['depth']} width {row['width_max']} "
            f"barrier overhead {row['barrier_overhead_ms']} ms vs forward "
            f"{row['forward_median_ms']} ms -> {row['barrier_overhead_vs_forward']}x",
            flush=True,
        )
    json.dump(payload, open(out_path, "w"), indent=1)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
