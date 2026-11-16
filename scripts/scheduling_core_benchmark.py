#!/usr/bin/env python3
"""Run the P0 scheduling-core baseline benchmark on real fixtures.

This is the measurement harness required by the P0-A phase.  It never
estimates: every number in the emitted JSON comes from a real call to the
authoritative engine on this machine, and a size that cannot complete is
recorded as an error instead of being extrapolated.

One measurement per process is recommended so ``peak_rss_kb`` is attributable
to a single shape.  Example:

    python3 scripts/scheduling_core_benchmark.py \
        --mode date --sizes 1000,5000,25000 --shape dag --repeat 3 \
        --out /tmp/p0-date-1k-25k.json

The CLI is intentionally thin: fixture construction, canonical hashing and
timing live in ``construction_pm.scheduling.benchmark_fixtures`` so tests can
reuse exactly the same definitions.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from construction_pm.scheduling.benchmark_fixtures import (  # noqa: E402
    SHAPES,
    canonical_hash,
    date_network,
    date_schedule_payload,
    environment_fingerprint,
    leveling_case,
    leveling_orchestration_case,
    leveling_orchestration_payload,
    leveling_payload,
    measure,
    run_date_schedule,
    run_leveling,
    run_leveling_orchestration,
    run_time_schedule,
    time_network,
    time_schedule_payload,
)

MODES = ("date", "time", "leveling", "leveling-orchestration")


def _parse_sizes(value: str) -> list[int]:
    sizes = [int(part) for part in value.replace(" ", "").split(",") if part]
    if not sizes or any(size <= 0 for size in sizes):
        raise argparse.ArgumentTypeError("sizes must be a comma list of positive integers")
    return sizes


def _count_cpm_passes(fixture) -> int:
    """Count the CPM passes one orchestration performs, without timing them."""
    import importlib

    module = importlib.import_module("construction_pm.scheduling.schedule")
    calls: list[int] = []
    real_schedule = module.schedule

    def counting(*args, **kwargs):
        calls.append(1)
        return real_schedule(*args, **kwargs)

    module.schedule = counting
    try:
        run_leveling_orchestration(fixture)
    finally:
        module.schedule = real_schedule
    return len(calls)


def _single_cpm_ms(fixture) -> dict[str, object]:
    """Time one authoritative CPM pass on the same fixture.

    This makes the size of the eliminated pass measurable relative to the whole
    orchestration instead of guessing its share.
    """
    from construction_pm.scheduling.schedule import schedule

    def one_pass():
        return schedule(
            fixture.activities,
            fixture.relationships,
            fixture.project_start,
            fixture.resolver,
            project_finish=fixture.project_finish,
        )

    timing = measure(one_pass, repeat=3, warmup=1)
    timing.pop("result")
    timing.pop("peak_rss_kb")
    return {"wall": timing["wall"], "cpu": timing["cpu"]}


def _measure_one(args, size: int) -> dict[str, object]:
    record: dict[str, object] = {"mode": args.mode, "size": size, "shape": args.shape, "seed": args.seed}
    build_start = time.perf_counter()
    payload_builder = None
    if args.mode == "date":
        fixture = date_network(size, args.shape, args.seed)
        operation = lambda: run_date_schedule(fixture)  # noqa: E731
        payload_builder = date_schedule_payload
    elif args.mode == "time":
        fixture = time_network(size, args.shape, args.seed, float_days=args.float_days)
        operation = lambda: run_time_schedule(fixture)  # noqa: E731
        payload_builder = time_schedule_payload
    elif args.mode == "leveling":
        fixture = leveling_case(size, args.seed)
        operation = lambda: run_leveling(fixture)  # noqa: E731
        payload_builder = leveling_payload
    else:
        fixture = leveling_orchestration_case(size, args.seed)
        operation = lambda: run_leveling_orchestration(fixture)  # noqa: E731
        payload_builder = None
    record["fixture_build_ms"] = round((time.perf_counter() - build_start) * 1000.0, 3)
    record["counts"] = fixture.counts
    if args.mode == "time":
        record["project_finish"] = fixture.project_finish.isoformat() if fixture.project_finish else None
        record["float_days"] = args.float_days

    timing = measure(operation, repeat=args.repeat, warmup=args.warmup)
    result = timing.pop("result")
    record.update(timing)
    if args.mode == "leveling-orchestration":
        schedule_result, forward, backward = result
        record["output_sha256"] = canonical_hash(
            leveling_orchestration_payload(schedule_result, forward, backward)
        )
        record["forward_shifts"] = len(forward)
        record["backward_shifts"] = len(backward)
        record["cpm_passes"] = _count_cpm_passes(fixture)
        record["single_cpm_ms"] = _single_cpm_ms(fixture)
    else:
        record["output_sha256"] = canonical_hash(payload_builder(result))
    record["status"] = "ok"
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--sizes", type=_parse_sizes, default=[1000])
    parser.add_argument("--shape", choices=SHAPES, default="dag")
    parser.add_argument("--seed", type=int, default=20261116)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--warmup", type=int, default=0)
    parser.add_argument("--float-days", type=int, default=0, help="time mode: project-finish float offset in working days")
    parser.add_argument("--git-sha", default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    if args.repeat < 1:
        parser.error("--repeat must be at least 1")

    records: list[dict[str, object]] = []
    for size in args.sizes:
        try:
            record = _measure_one(args, size)
        except Exception as error:  # noqa: BLE001 - evidence must record the real failure
            record = {
                "mode": args.mode,
                "size": size,
                "shape": args.shape,
                "seed": args.seed,
                "status": "error",
                "error_type": type(error).__name__,
                "error": str(error),
            }
        records.append(record)
        print(json.dumps(record, sort_keys=True), flush=True)

    document = {
        "environment": environment_fingerprint(args.git_sha),
        "mode": args.mode,
        "shape": args.shape,
        "seed": args.seed,
        "repeat": args.repeat,
        "warmup": args.warmup,
        "records": records,
    }
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {args.out}", file=sys.stderr)
    return 0 if all(record.get("status") == "ok" for record in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
