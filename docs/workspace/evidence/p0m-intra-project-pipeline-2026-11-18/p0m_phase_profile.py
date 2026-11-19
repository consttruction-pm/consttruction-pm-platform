"""P0-M phase profiler: exact phase wall/CPU and cProfile self-time attribution.

Runs the sequential engine once per size (the Oracle path), with:
  * wall/CPU timers around fixture construction, forward pass, backward pass,
    float calculation, assembly and canonical hashing;
  * a separate ``heap_topological_order`` timing on the same graph;
  * ``cProfile`` on the whole sequential schedule, with self time grouped by
    category (calendar arithmetic, relationship evaluation, topological
    ordering, float calculation, engine glue) and call counts for the hot
    engine functions;
  * graph level statistics (depth/width) that bound wavefront parallelism.
"""
from __future__ import annotations

import cProfile
import importlib
import json
import pstats
import resource
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path("/data/work/repo")
sys.path.insert(0, str(ROOT / "src"))

bf = importlib.import_module("construction_pm.scheduling.benchmark_fixtures")
ts = importlib.import_module("construction_pm.scheduling.time_schedule")
TOPO = importlib.import_module("construction_pm.scheduling.topological_order")

CATEGORIES = {
    "topological_ordering": {"heap_topological_order"},
    "relationship_evaluation": {
        "_latest_predecessor_start",
        "_add_signed_lag",
        "_ss_successor_start",
        "_inverse_lag",
        "_add_signed_lag_for_float",
    },
}
OWNER_CATEGORY = {
    "time_calendar": "calendar_arithmetic",
    "calendar_context": "calendar_arithmetic",
}


def _category(filename: str, func: str) -> str:
    for category, names in CATEGORIES.items():
        if func in names:
            return category
    for module, category in OWNER_CATEGORY.items():
        if module in filename:
            return category
    if "__float" in func or "float" in func.lower():
        return "float_calculation"
    if "time_forward_pass" in filename:
        return "forward_pass_glue"
    if "time_schedule" in filename:
        return "backward_glue"
    return "other"


def level_stats(activities, relationships) -> dict:
    ids = [a.id for a in activities]
    preds = {i: 0 for i in ids}
    succ = {i: [] for i in ids}
    for rel in relationships:
        preds[rel.successor_id] += 1
        succ[rel.predecessor_id].append(rel.successor_id)
    depth = {i: 0 for i in ids}
    ready = [i for i in ids if preds[i] == 0]
    order = []
    while ready:
        current = ready.pop()
        order.append(current)
        for successor in succ[current]:
            depth[successor] = max(depth[successor], depth[current] + 1)
            preds[successor] -= 1
            if preds[successor] == 0:
                ready.append(successor)
    sizes = Counter(depth.values())
    ordered = [sizes[key] for key in sorted(sizes)]
    return {
        "depth": len(ordered),
        "width_max": max(ordered),
        "width_mean": round(sum(ordered) / len(ordered), 2),
        "levels_with_width_ge_2": sum(1 for value in ordered if value >= 2),
        "levels_with_width_ge_4": sum(1 for value in ordered if value >= 4),
        "largest_level_share": round(max(ordered) / len(ids), 6),
        "level_size_head": ordered[:32],
    }


def profile_sequential(fixture) -> dict:
    profiler = cProfile.Profile()
    profiler.enable()
    ts.time_schedule(
        fixture.activities,
        fixture.relationships,
        fixture.project_start,
        fixture.project_finish,
        fixture.registry,
        float_workers=1,
    )
    profiler.disable()
    stats = pstats.Stats(profiler)
    self_by_category: dict[str, float] = {}
    calls: dict[str, dict] = {}
    for (filename, line, function), entry in stats.stats.items():
        cc, nc, tt, ct, _ = entry
        category = _category(filename, function)
        self_by_category[category] = self_by_category.get(category, 0.0) + tt
        if function in {
            "heap_topological_order",
            "_latest_predecessor_start",
            "_add_signed_lag",
            "_ss_successor_start",
            "_inverse_lag",
            "_time_float_for_activity",
            "_float_limit_interval_bound",
            "_free_float_limit",
            "_verified_float_limit",
            "_parallel_time_floats",
            "_time_float_context",
            "add_duration",
            "subtract_duration",
            "add_lag",
            "subtract_lag",
            "calculate_duration",
            "normalize_start",
            "normalize_finish",
            "intervals_for",
            "resolve_calendar_aware",
            "resolve_relationship_lag",
            "time_forward_pass",
            "time_backward_pass",
            "calculate_time_floats",
            "time_schedule",
            "time_schedule_payload",
            "canonical_hash",
        }:
            key = f"{function}@{Path(filename).name}:{line}"
            calls[key] = {
                "calls": nc,
                "self_ms": round(tt * 1000, 2),
                "cumulative_ms": round(ct * 1000, 2),
            }
    return {
        "self_by_category_ms": {
            key: round(value * 1000, 2) for key, value in self_by_category.items()
        },
        "calls": calls,
        "total_profiled_ms": round(stats.total_tt * 1000, 2),
    }


def measure(size: int, repeats: int, profile: bool) -> dict:
    prep0 = time.perf_counter()
    fixture = bf.time_network(size)
    prep_ms = (time.perf_counter() - prep0) * 1000

    # Warm-up: the same sequential engine path is measured below.
    ts.time_schedule(
        fixture.activities,
        fixture.relationships,
        fixture.project_start,
        fixture.project_finish,
        fixture.registry,
        float_workers=1,
    )

    runs = []
    result = None
    for _ in range(repeats):
        wall0 = time.perf_counter()
        cpu0 = time.process_time()
        early = ts.time_forward_pass(
            fixture.activities,
            fixture.relationships,
            fixture.project_start,
            fixture.registry,
            (),
            None,
            None,
            None,
        )
        wall1 = time.perf_counter()
        cpu1 = time.process_time()
        late = ts.time_backward_pass(
            fixture.activities,
            fixture.relationships,
            early,
            fixture.project_finish,
            fixture.registry,
        )
        wall2 = time.perf_counter()
        cpu2 = time.process_time()
        floats = ts.calculate_time_floats(
            fixture.activities,
            fixture.relationships,
            early,
            late,
            fixture.registry,
        )
        wall3 = time.perf_counter()
        cpu3 = time.process_time()
        result = ts.TimeScheduleResult(
            activities=early,
            early_activities=early,
            late_activities=late,
            floats=floats,
            project_finish=fixture.project_finish,
        )
        payload = bf.time_schedule_payload(result)
        wall4 = time.perf_counter()
        cpu4 = time.process_time()
        digest = bf.canonical_hash(payload)
        wall5 = time.perf_counter()
        cpu5 = time.process_time()
        runs.append(
            {
                "forward_ms": round((wall1 - wall0) * 1000, 2),
                "backward_ms": round((wall2 - wall1) * 1000, 2),
                "float_ms": round((wall3 - wall2) * 1000, 2),
                "assemble_ms": round((wall4 - wall3) * 1000, 2),
                "hash_ms": round((wall5 - wall4) * 1000, 2),
                "total_ms": round((wall5 - wall0) * 1000, 2),
                "forward_cpu_ms": round((cpu1 - cpu0) * 1000, 2),
                "backward_cpu_ms": round((cpu2 - cpu1) * 1000, 2),
                "float_cpu_ms": round((cpu3 - cpu2) * 1000, 2),
                "assemble_cpu_ms": round((cpu4 - cpu3) * 1000, 2),
                "hash_cpu_ms": round((cpu5 - cpu4) * 1000, 2),
                "sha256": digest,
            }
        )

    topo_runs = []
    for _ in range(max(1, min(repeats, 3))):
        topo0 = time.perf_counter()
        TOPO.heap_topological_order(
            [activity.id for activity in fixture.activities],
            (
                (rel.predecessor_id, rel.successor_id)
                for rel in fixture.relationships
            ),
        )
        topo_runs.append((time.perf_counter() - topo0) * 1000)

    median = lambda key: round(
        statistics.median(run[key] for run in runs), 2
    )
    summary = {
        "size": len(fixture.activities),
        "relationships": len(fixture.relationships),
        "prep_ms": round(prep_ms, 2),
        "topo_ms": round(statistics.median(topo_runs), 2),
        "forward_ms": median("forward_ms"),
        "backward_ms": median("backward_ms"),
        "float_ms": median("float_ms"),
        "assemble_ms": median("assemble_ms"),
        "hash_ms": median("hash_ms"),
        "total_ms": median("total_ms"),
        "forward_cpu_ms": median("forward_cpu_ms"),
        "backward_cpu_ms": median("backward_cpu_ms"),
        "float_cpu_ms": median("float_cpu_ms"),
        "assemble_cpu_ms": median("assemble_cpu_ms"),
        "hash_cpu_ms": median("hash_cpu_ms"),
        "utilization": round(
            statistics.median(
                run["forward_cpu_ms"]
                + run["backward_cpu_ms"]
                + run["float_cpu_ms"]
                + run["assemble_cpu_ms"]
                + run["hash_cpu_ms"]
                for run in runs
            )
            / median("total_ms"),
            3,
        ),
        "peak_rss_kb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "level_stats": level_stats(fixture.activities, fixture.relationships),
        "runs": runs,
    }
    float_share = summary["float_ms"] / summary["total_ms"]
    summary["float_share"] = round(float_share, 4)
    summary["serial_vs_parallelizable_ratio"] = round(
        (summary["total_ms"] - summary["float_ms"]) / summary["float_ms"], 3
    )
    if profile:
        profiled = profile_sequential(fixture)
        summary["profile_self_by_category_ms"] = profiled["self_by_category_ms"]
        summary["profile_calls"] = profiled["calls"]
        summary["profile_total_ms"] = profiled["total_profiled_ms"]
    return summary


if __name__ == "__main__":
    sizes = [int(value) for value in sys.argv[1].split(",")]
    repeats = int(sys.argv[2])
    out_path = sys.argv[3]
    rows = []
    for size in sizes:
        row = measure(size, repeats, profile=True)
        rows.append(row)
        print(
            f"{size}: total {row['total_ms']} ms | fwd {row['forward_ms']} "
            f"bwd {row['backward_ms']} float {row['float_ms']} "
            f"asm {row['assemble_ms']} hash {row['hash_ms']} | topo {row['topo_ms']} "
            f"prep {row['prep_ms']} | float share {row['float_share']} | "
            f"depth {row['level_stats']['depth']} width_max "
            f"{row['level_stats']['width_max']} | rss {row['peak_rss_kb']} kB",
            flush=True,
        )
        json.dump(rows, open(out_path, "w"), indent=1)
    print("DONE", flush=True)
