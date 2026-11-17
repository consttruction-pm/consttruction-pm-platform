#!/usr/bin/env python3
"""P0-J phase profiler for the authoritative scheduling engine.

This harness exists to answer one question with measurements instead of
assumptions: *where does the remaining processing time actually go?*

It measures, per engine path, the wall time of the individual phases the engine
itself calls (forward pass, backward pass, float calculation, leveling proposal,
CPM passes, final validation) by wrapping those module-level functions with a
timer and running the real engine. The wrapper only counts calls and elapsed
time; it cannot change arguments, order or results, and every row also records
the canonical output hash so a re-run can be proven identical.

A separate ``--profile-top`` option collects a cProfile sample of the same run
for function-level attribution.

Example:

    python3 scripts/p0j_profile.py --mode leveling --size 250 \
        --repeat 3 --warmup 1 --git-sha <sha> --out /tmp/p0j-leveling.json
"""

from __future__ import annotations

import argparse
import cProfile
import io
import json
import pstats
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from construction_pm.scheduling.benchmark_fixtures import (  # noqa: E402
    SHAPES,
    canonical_hash,
    date_network,
    date_schedule_payload,
    environment_fingerprint,
    backward_leveling_case,
    backward_leveling_payload,
    leveling_case,
    leveling_orchestration_case,
    leveling_orchestration_payload,
    leveling_payload,
    run_date_schedule,
    run_backward_leveling,
    run_leveling,
    run_leveling_orchestration,
    run_time_schedule,
    time_network,
    time_schedule_payload,
)

MODES = ("date", "time", "leveling", "backward-leveling", "leveling-orchestration")


# ---------------------------------------------------------------------------
# Phase instrumentation
# ---------------------------------------------------------------------------


@dataclass
class _Phase:
    calls: int = 0
    seconds: float = 0.0


@dataclass
class PhaseRecorder:
    """Time selected module-level functions without changing their behaviour."""

    _patches: list[tuple[object, str, object]] = field(default_factory=list)
    phases: dict[str, _Phase] = field(default_factory=dict)

    def watch(self, module: object, attribute: str, label: str | None = None) -> None:
        original = getattr(module, attribute)
        key = label or f"{getattr(module, '__name__', '?')}.{attribute}"
        phase = self.phases.setdefault(key, _Phase())

        def timed(*args, **kwargs):
            start = time.perf_counter()
            try:
                return original(*args, **kwargs)
            finally:
                phase.calls += 1
                phase.seconds += time.perf_counter() - start

        setattr(module, attribute, timed)
        self._patches.append((module, attribute, original))

    def restore(self) -> None:
        while self._patches:
            module, attribute, original = self._patches.pop()
            setattr(module, attribute, original)

    def snapshot(self) -> dict[str, tuple[int, float]]:
        return {name: (phase.calls, phase.seconds) for name, phase in self.phases.items()}

    def __enter__(self) -> "PhaseRecorder":
        return self

    def __exit__(self, *exc: object) -> None:
        self.restore()


def _deltas(
    before: dict[str, tuple[int, float]],
    after: dict[str, tuple[int, float]],
) -> dict[str, dict[str, float | int]]:
    result: dict[str, dict[str, float | int]] = {}
    for name, (calls, seconds) in after.items():
        old_calls, old_seconds = before.get(name, (0, 0.0))
        result[name] = {
            "calls": calls - old_calls,
            "ms": round((seconds - old_seconds) * 1000.0, 3),
        }
    return result


def _summarize(samples: Iterable[float]) -> dict[str, float]:
    ordered = sorted(samples)
    if not ordered:
        raise ValueError("at least one sample is required")
    p95_index = min(len(ordered) - 1, max(0, int(round(0.95 * (len(ordered) - 1)))))
    return {
        "count": len(ordered),
        "median_ms": round(ordered[len(ordered) // 2] if len(ordered) % 2 else (
            ordered[len(ordered) // 2 - 1] + ordered[len(ordered) // 2]
        ) / 2.0, 3),
        "p95_ms": round(ordered[p95_index], 3),
        "min_ms": round(ordered[0], 3),
        "max_ms": round(ordered[-1], 3),
    }


def _install_watches(mode: str) -> PhaseRecorder:
    import importlib

    leveling_scheduler = importlib.import_module("construction_pm.scheduling.leveling_scheduler")
    resource_leveling = importlib.import_module("construction_pm.scheduling.resource_leveling")
    schedule_module = importlib.import_module("construction_pm.scheduling.schedule")
    time_module = importlib.import_module("construction_pm.scheduling.time_schedule")

    recorder = PhaseRecorder()
    if mode == "date":
        recorder.watch(schedule_module, "forward_pass", "date.forward_pass")
        recorder.watch(schedule_module, "backward_pass", "date.backward_pass")
        recorder.watch(schedule_module, "calculate_floats", "date.calculate_floats")
        recorder.watch(schedule_module, "_multiple_float_paths", "date.float_paths")
    elif mode == "time":
        recorder.watch(time_module, "time_forward_pass", "time.forward_pass")
        recorder.watch(time_module, "time_backward_pass", "time.backward_pass")
        recorder.watch(time_module, "calculate_time_floats", "time.calculate_floats")
    elif mode in ("leveling", "backward-leveling", "leveling-orchestration"):
        recorder.watch(
            resource_leveling,
            "propose_forward_leveling_within_float",
            "leveling.propose_forward",
        )
        recorder.watch(
            resource_leveling, "propose_backward_leveling", "leveling.propose_backward"
        )
        recorder.watch(resource_leveling, "_shift_demands", "leveling.shift_demands")
        recorder.watch(
            resource_leveling, "_shift_demands_backward", "leveling.shift_demands_backward"
        )
        recorder.watch(
            resource_leveling, "_shift_date_forward", "leveling.shift_date_forward"
        )
        recorder.watch(
            resource_leveling, "_shift_date_backward", "leveling.shift_date_backward"
        )
        recorder.watch(
            resource_leveling, "_working_days_between", "leveling.working_days_between"
        )
        # leveling_scheduler imports ``schedule`` inside the orchestration
        # function, so the patchable binding is the schedule module itself.
        recorder.watch(schedule_module, "schedule", "leveling.cpm_pass")
        recorder.watch(
            leveling_scheduler,
            "_validate_final_resource_load",
            "leveling.final_validation",
        )
        recorder.watch(
            leveling_scheduler,
            "_forward_activities_with_authoritative_floats",
            "leveling.rebase_floats",
        )
    return recorder


def _build(args):
    if args.mode == "date":
        return date_network(args.size, args.shape, args.seed), run_date_schedule, date_schedule_payload
    if args.mode == "time":
        return (
            time_network(args.size, args.shape, args.seed, float_days=args.float_days),
            lambda fixture: run_time_schedule(fixture, float_workers=args.time_float_workers),
            time_schedule_payload,
        )
    if args.mode == "leveling":
        return leveling_case(args.size, args.seed), run_leveling, leveling_payload
    if args.mode == "backward-leveling":
        return (
            backward_leveling_case(args.size, args.seed),
            run_backward_leveling,
            backward_leveling_payload,
        )
    return (
        leveling_orchestration_case(args.size, args.seed),
        run_leveling_orchestration,
        leveling_orchestration_payload,
    )


def _output_hash(mode: str, result: object) -> str:
    if mode == "leveling":
        return canonical_hash(leveling_payload(result))
    if mode == "backward-leveling":
        return canonical_hash(backward_leveling_payload(result))
    if mode == "leveling-orchestration":
        schedule_result, forward, backward = result
        return canonical_hash(leveling_orchestration_payload(schedule_result, forward, backward))
    if mode == "date":
        return canonical_hash(date_schedule_payload(result))
    return canonical_hash(time_schedule_payload(result))


def _measure(args) -> dict[str, object]:
    fixture, runner, _ = _build(args)
    record: dict[str, object] = {
        "mode": args.mode,
        "size": args.size,
        "shape": args.shape if args.mode in ("date", "time") else None,
        "seed": args.seed,
        "counts": fixture.counts,
        "repeat": args.repeat,
        "warmup": args.warmup,
    }
    if args.mode == "time":
        record["float_days"] = args.float_days
        record["time_float_workers"] = args.time_float_workers
    recorder = _install_watches(args.mode)
    wall_samples: list[float] = []
    phase_samples: dict[str, list[dict[str, float | int]]] = {}
    result = None
    try:
        for index in range(args.warmup + args.repeat):
            before = recorder.snapshot()
            start = time.perf_counter()
            result = runner(fixture)
            elapsed = (time.perf_counter() - start) * 1000.0
            after = recorder.snapshot()
            if index >= args.warmup:
                wall_samples.append(elapsed)
                for name, values in _deltas(before, after).items():
                    phase_samples.setdefault(name, []).append(values)
    finally:
        recorder.restore()

    record["wall"] = _summarize(wall_samples)
    phases: dict[str, object] = {}
    for name, samples in phase_samples.items():
        phases[name] = {
            "calls_median": sorted(s["calls"] for s in samples)[len(samples) // 2],
            "median_ms": _summarize([s["ms"] for s in samples])["median_ms"],
            "p95_ms": _summarize([s["ms"] for s in samples])["p95_ms"],
            "share_of_wall": round(
                (_summarize([s["ms"] for s in samples])["median_ms"] / record["wall"]["median_ms"])
                if record["wall"]["median_ms"]
                else 0.0,
                4,
            ),
        }
    record["phases"] = phases
    record["output_sha256"] = _output_hash(args.mode, result)
    record["output_counts"] = _output_counts(args.mode, result)
    record["peak_rss_kb"] = _peak_rss_kb()
    record["status"] = "ok"
    return record


def _output_counts(mode: str, result: object) -> dict[str, int]:
    if mode == "leveling":
        return {"shifts": len(result)}
    if mode == "backward-leveling":
        return {"shifts": len(result)}
    if mode == "leveling-orchestration":
        schedule_result, forward, backward = result
        return {
            "activities": len(schedule_result.activities),
            "forward_shifts": len(forward),
            "backward_shifts": len(backward),
        }
    if mode == "date":
        return {"activities": len(result.activities), "float_paths": len(result.float_paths)}
    return {"activities": len(result.activities)}


def _peak_rss_kb() -> int:
    import resource

    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def _profile(args) -> list[dict[str, object]]:
    fixture, runner, _ = _build(args)
    runner(fixture)  # warm-up outside the profile
    profiler = cProfile.Profile()
    profiler.enable()
    runner(fixture)
    profiler.disable()
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream).sort_stats("cumulative")
    stats.print_stats(args.profile_top)
    rows: list[dict[str, object]] = []
    for (filename, line, function), values in stats.stats.items():
        calls, _, total, cumulative = values[:4]
        rows.append(
            {
                "function": function,
                "file": Path(filename).name,
                "line": line,
                "calls": calls,
                "self_ms": round(total * 1000.0, 3),
                "cumulative_ms": round(cumulative * 1000.0, 3),
            }
        )
    rows.sort(key=lambda row: row["cumulative_ms"], reverse=True)
    return rows[: args.profile_top]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--size", type=int, default=1000)
    parser.add_argument("--shape", choices=SHAPES, default="dag")
    parser.add_argument("--seed", type=int, default=20261116)
    parser.add_argument("--float-days", type=int, default=0)
    parser.add_argument("--time-float-workers", type=int, default=1)
    parser.add_argument("--repeat", type=int, default=7)
    parser.add_argument("--warmup", type=int, default=2)
    parser.add_argument("--profile-top", type=int, default=0)
    parser.add_argument("--git-sha")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    if args.repeat < 1:
        parser.error("--repeat must be at least 1")
    if args.warmup < 0:
        parser.error("--warmup must be non-negative")
    start = time.time()
    try:
        record = _measure(args)
        record["status"] = "ok"
    except Exception as exc:  # noqa: BLE001 - a failed size must be recorded, not invented
        record = {
            "mode": args.mode,
            "size": args.size,
            "shape": args.shape,
            "seed": args.seed,
            "status": "error",
            "error": f"{type(exc).__name__}: {exc}",
            "elapsed_s": round(time.time() - start, 3),
        }
    record["environment"] = environment_fingerprint(args.git_sha)
    if args.profile_top:
        record["profile_top"] = _profile(args)
    Path(args.out).write_text(
        json.dumps(record, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({k: record.get(k) for k in ("mode", "size", "status", "wall")}, sort_keys=True))
    return 0 if record.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
