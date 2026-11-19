"""P0-M benchmark: one (size, workers, mode) configuration per process.

Modes
-----
pipeline : the P0-M backward/float producer-consumer pipeline, i.e. the public
           ``time_schedule(float_workers=w)`` entry point.
posthoc  : the historical P0-H/P0-J shape -- serial backward pass, then the
           chunked parallel float pass -- invoked through the same engine
           functions, used as the comparison baseline.

The driver runs each configuration in a fresh process so that
``resource.RUSAGE_CHILDREN`` starts at zero.
"""
from __future__ import annotations

import importlib
import json
import math
import pickle
import resource
import statistics
import sys
import time

ROOT = "/data/work/repo"
sys.path.insert(0, ROOT + "/src")

bf = importlib.import_module("construction_pm.scheduling.benchmark_fixtures")
ts = importlib.import_module("construction_pm.scheduling.time_schedule")


def _children_cpu_ms() -> float:
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    return (usage.ru_utime + usage.ru_stime) * 1000.0


def _self_cpu_ms() -> float:
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return (usage.ru_utime + usage.ru_stime) * 1000.0


def _instrument_timing(records: list) -> None:
    original = ts._FloatPipeline

    class TimingPipeline(original):  # type: ignore[misc, valid-type]
        def __init__(self, pool, batch_size):
            super().__init__(pool, batch_size)
            self.submit_ms = 0.0
            self.drain_ms = 0.0
            records.append(self)

        def _dispatch(self):  # type: ignore[override]
            start = time.perf_counter()
            super()._dispatch()
            self.submit_ms += (time.perf_counter() - start) * 1000.0

        def finish(self):  # type: ignore[override]
            start = time.perf_counter()
            result = super().finish()
            self.drain_ms += (time.perf_counter() - start) * 1000.0
            return result

    ts._FloatPipeline = TimingPipeline


def _instrument_bytes(records: list) -> None:
    original = ts._FloatPipeline

    class ByteCounting(original):  # type: ignore[misc, valid-type]
        def _dispatch(self):  # type: ignore[override]
            batch = self._buffer
            records.append(
                {
                    "batch_activities": len(batch),
                    "batch_bytes": len(pickle.dumps(batch)),
                }
            )
            super()._dispatch()

    ts._FloatPipeline = ByteCounting


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * fraction
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return ordered[low]
    weight = position - low
    return ordered[low] * (1 - weight) + ordered[high] * weight


def _schedule(fixture, workers: int, mode: str):
    if mode == "pipeline":
        return ts.time_schedule(
            fixture.activities,
            fixture.relationships,
            fixture.project_start,
            fixture.project_finish,
            fixture.registry,
            float_workers=workers,
        )
    early = ts.time_forward_pass(
        fixture.activities,
        fixture.relationships,
        fixture.project_start,
        fixture.registry,
    )
    project_finish = fixture.project_finish or max(
        item.finish for item in early.values()
    )
    context = fixture.activities[0].calendar_context
    if context is not None:
        resolver = ts.resolve_calendar_aware(fixture.registry, context.project)
        project_finish = resolver.normalize_finish(project_finish)
    late = ts.time_backward_pass(
        fixture.activities,
        fixture.relationships,
        early,
        project_finish,
        fixture.registry,
    )
    floats = ts.calculate_time_floats(
        fixture.activities,
        fixture.relationships,
        early,
        late,
        fixture.registry,
        workers=workers,
    )
    return ts.TimeScheduleResult(
        activities=early,
        early_activities=early,
        late_activities=late,
        floats=floats,
        project_finish=project_finish,
    )


def run(size: int, workers: int, repeats: int, mode: str, want_bytes: bool) -> dict:
    fixture = bf.time_network(size)
    result = None
    original_pipeline = ts._FloatPipeline

    _schedule(fixture, workers, mode)  # warm-up, untimed

    samples = []
    submit_samples = []
    drain_samples = []
    batches = 0
    activities = 0
    for _ in range(repeats):
        records: list = []
        instrumented = mode == "pipeline" and workers > 1
        if instrumented:
            _instrument_timing(records)
        try:
            children_cpu0 = _children_cpu_ms()
            parent_cpu0 = _self_cpu_ms()
            wall0 = time.perf_counter()
            result = _schedule(fixture, workers, mode)
            wall1 = time.perf_counter()
            wall_ms = (wall1 - wall0) * 1000.0
            parent_cpu = _self_cpu_ms() - parent_cpu0
            children_cpu = _children_cpu_ms() - children_cpu0
        finally:
            ts._FloatPipeline = original_pipeline
        digest = bf.canonical_hash(bf.time_schedule_payload(result))
        if records:
            record = records[-1]
            batches += record.dispatched_batches
            activities += record.dispatched_activities
            submit_samples.append(record.submit_ms)
            drain_samples.append(record.drain_ms)
        samples.append(
            {
                "wall_ms": wall_ms,
                "parent_cpu_ms": parent_cpu,
                "children_cpu_ms": children_cpu,
                "sha256": digest,
            }
        )

    batch_records: list = []
    if want_bytes and mode == "pipeline" and workers > 1:
        _instrument_bytes(batch_records)
        try:
            _schedule(fixture, workers, mode)
        finally:
            ts._FloatPipeline = original_pipeline

    walls = [s["wall_ms"] for s in samples]
    parent_cpus = [s["parent_cpu_ms"] for s in samples]
    children_cpus = [s["children_cpu_ms"] for s in samples]
    child_count = max(workers - 1, 0)
    wall_median = statistics.median(walls)
    total_cpu_median = statistics.median(
        [p + c for p, c in zip(parent_cpus, children_cpus)]
    )
    return {
        "size": len(fixture.activities),
        "relationships": len(fixture.relationships),
        "workers": workers,
        "mode": mode,
        "repeats": repeats,
        "wall_ms": [round(v, 1) for v in walls],
        "wall_median_ms": round(wall_median, 1),
        "wall_p95_ms": round(percentile(walls, 0.95), 1),
        "wall_min_ms": round(min(walls), 1),
        "wall_max_ms": round(max(walls), 1),
        "parent_cpu_median_ms": round(statistics.median(parent_cpus), 1),
        "children_cpu_median_ms": round(statistics.median(children_cpus), 1),
        "total_cpu_median_ms": round(total_cpu_median, 1),
        "utilization": round(total_cpu_median / wall_median, 3),
        "child_worker_utilization": (
            round(statistics.median(children_cpus) / (wall_median * child_count), 3)
            if child_count
            else 0.0
        ),
        "parent_peak_rss_kb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "children_max_rss_kb": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        "pipeline_batches": batches // repeats,
        "pipeline_activities": activities // repeats,
        "ipc_submit_ms": [round(v, 2) for v in submit_samples],
        "ipc_submit_median_ms": (
            round(statistics.median(submit_samples), 2) if submit_samples else 0.0
        ),
        "drain_wait_ms": [round(v, 2) for v in drain_samples],
        "drain_wait_median_ms": (
            round(statistics.median(drain_samples), 2) if drain_samples else 0.0
        ),
        "batch_payload_bytes_mean": (
            round(sum(r["batch_bytes"] for r in batch_records) / len(batch_records), 1)
            if batch_records
            else 0
        ),
        "batch_payload_bytes_total": sum(r["batch_bytes"] for r in batch_records),
        "batch_payload_activities_mean": (
            round(
                sum(r["batch_activities"] for r in batch_records) / len(batch_records), 2
            )
            if batch_records
            else 0
        ),
        "sha256": samples[-1]["sha256"],
    }


if __name__ == "__main__":
    if len(sys.argv) < 6 or sys.argv[1] != "--run":
        raise SystemExit(
            "usage: --run <size> <workers> <repeats> <pipeline|posthoc> [--bytes]"
        )
    print(
        json.dumps(
            run(
                int(sys.argv[2]),
                int(sys.argv[3]),
                int(sys.argv[4]),
                sys.argv[5],
                "--bytes" in sys.argv,
            )
        ),
        flush=True,
    )
