#!/usr/bin/env python3
"""P0-J phase 3: safe parallel float execution in a real worker thread.

The Scheduling Job executor runs ``calculate`` on a worker thread while holding
one permit of the process-wide budget. This harness reproduces exactly that
condition and compares the per-activity float pass for 1..N slots:

* every run happens inside a thread that holds one budget permit;
* the policy reserves its extra slots from the same budget (``admit_extra``);
* a threaded process must use ``spawn``, never ``fork``;
* the canonical payload hash must be byte-identical for every worker count.

    python3 scripts/p0j_float_parallel.py --context main \
        --sizes 500,2000,5000,25000 --workers 1,2,4 --repeats 7 --out <dir>
    python3 scripts/p0j_float_parallel.py --context thread \
        --label float-parallel-threaded --sizes 5000,25000 ... --allow-spawn

No value is estimated: each configuration is measured, medians/p95 need at
least two warm-ups plus repeated samples, and a hash mismatch fails the run.
"""
from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import resource
import statistics
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from construction_pm.scheduling.benchmark_fixtures import (  # noqa: E402
    canonical_hash,
    environment_fingerprint,
    time_network,
    time_schedule_payload,
)
from construction_pm.scheduling.time_schedule import (  # noqa: E402
    FloatExecutionPolicy,
    time_schedule,
)
from construction_pm.scheduling_execution_budget import (  # noqa: E402
    GlobalExecutionBudget,
    detect_effective_capacity,
)

CALCULATION = "p0j-float-parallel"


class _RecordingContext:
    """Proxy that records which start method created a pool."""

    def __init__(self, context, method, log: list[str]) -> None:
        self._context = context
        self._method = method
        self._log = log

    def Pool(self, *args, **kwargs):
        self._log.append(self._method)
        return self._context.Pool(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._context, name)


class _PoolRecorder:
    """Record pool creation without changing the pool that is created."""

    def __init__(self) -> None:
        self.methods: list[str] = []

    def __enter__(self):
        self._original = multiprocessing.get_context

        def recording(method=None):
            context = self._original(method)
            return _RecordingContext(context, method, self.methods)

        multiprocessing.get_context = recording
        return self

    def __exit__(self, *exc) -> None:
        multiprocessing.get_context = self._original


def _percentile(samples: list[float], fraction: float) -> float:
    ordered = sorted(samples)
    index = min(len(ordered) - 1, max(0, int(round(fraction * (len(ordered) - 1)))))
    return ordered[index]


def _run_once(
    network,
    policy: FloatExecutionPolicy | None,
    budget: GlobalExecutionBudget,
    context: str,
) -> dict:
    outcome: dict[str, object] = {}
    errors: list[BaseException] = []

    def calculate() -> None:
        try:
            with budget.permit():
                result = time_schedule(
                    network.activities,
                    network.relationships,
                    network.project_start,
                    network.project_finish,
                    network.registry,
                    float_policy=policy,
                )
            outcome["hash"] = canonical_hash(time_schedule_payload(result))
        except BaseException as error:  # noqa: BLE001 - surface in the caller
            errors.append(error)

    if context == "thread":
        worker = threading.Thread(target=calculate)
        worker.start()
        worker.join()
    else:
        calculate()
    if errors:
        raise errors[0]
    return outcome


def measure(
    network, workers: int, repeats: int, warmups: int, context: str, allow_spawn: bool
) -> dict:
    budget = GlobalExecutionBudget(workers)
    if workers == 1:
        policy = FloatExecutionPolicy(workers=1)
    else:
        policy = FloatExecutionPolicy(
            workers=workers, admission=budget.admit_extra, allow_spawn=allow_spawn
        )

    for _ in range(warmups):
        _run_once(network, policy, budget, context)

    samples: list[float] = []
    hashes: set[str] = set()
    extra_peak = 0
    children_rss = 0
    recorder = _PoolRecorder()
    with recorder:
        for _ in range(repeats):
            start = time.perf_counter()
            outcome = _run_once(network, policy, budget, context)
            samples.append((time.perf_counter() - start) * 1000.0)
            hashes.add(str(outcome["hash"]))
            extra_peak = max(extra_peak, budget.extra_peak)
            children_rss = max(
                children_rss,
                resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
            )

    median = statistics.median(samples)
    return {
        "workers": workers,
        "pool_start_methods": sorted(set(recorder.methods)),
        "pool_slots_used": 1 + extra_peak,
        "samples_ms": [round(value, 3) for value in samples],
        "median_ms": round(median, 3),
        "min_ms": round(min(samples), 3),
        "p95_ms": round(_percentile(samples, 0.95), 3),
        "spread_pct": round((max(samples) - min(samples)) / median * 100.0, 3),
        "hash": sorted(hashes),
        "identical_hash": len(hashes) == 1,
        "budget": budget.as_dict(),
        "children_peak_rss_kb": children_rss or None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", default="500,2000,5000")
    parser.add_argument("--workers", default="1,2,3,4")
    parser.add_argument("--shape", default="mixed")
    parser.add_argument("--context", choices=("main", "thread"), default="main")
    parser.add_argument("--allow-spawn", action="store_true")
    parser.add_argument("--label", default=None)
    parser.add_argument("--git-sha", default=None)
    parser.add_argument("--seed", type=int, default=20261117)
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument("--warmups", type=int, default=2)
    parser.add_argument("--out", default=str(ROOT / "docs/workspace/evidence/p0j-scheduling-optimization-2026-11-17"))
    args = parser.parse_args(argv)

    sizes = [int(value) for value in args.sizes.split(",") if value]
    worker_counts = [int(value) for value in args.workers.split(",") if value]
    capacity = detect_effective_capacity()
    output_dir = Path(args.out)
    output_dir.mkdir(parents=True, exist_ok=True)

    report: dict[str, object] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "calculation": CALCULATION,
        "python": sys.version,
        "start_methods": multiprocessing.get_all_start_methods(),
        "hardware": {
            "nproc": os.cpu_count(),
            "affinity": len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None,
            "effective_capacity": capacity.as_dict(),
            "note": (
                "Worker counts above the effective affinity are simulated quotas; "
                "this process can only run one OS thread per permitted CPU."
            ),
        },
        "environment": environment_fingerprint(args.git_sha),
        "repeats": args.repeats,
        "warmups": args.warmups,
        "shape": args.shape,
        "context": args.context,
        "allow_spawn": args.allow_spawn,
        "cases": [],
    }

    for size in sizes:
        network = time_network(size, args.shape, args.seed)
        case: dict[str, object] = {
            "size": size,
            "counts": network.counts,
            "runs": [],
        }
        for workers in worker_counts:
            run = measure(
                network,
                workers,
                args.repeats,
                args.warmups,
                args.context,
                args.allow_spawn,
            )
            case["runs"].append(run)
            print(
                f"size={size} workers={workers} median={run['median_ms']} ms "
                f"p95={run['p95_ms']} slots={run['pool_slots_used']} "
                f"method={run['pool_start_methods']} "
                f"hash={run['hash'][0][:12]}"
            )
        baseline = case["runs"][0]
        for run in case["runs"]:
            run["speedup_vs_1"] = round(float(baseline["median_ms"]) / float(run["median_ms"]), 3)
            run["hash_equals_sequential"] = run["hash"] == baseline["hash"]
        report["cases"].append(case)

    label = args.label or f"float-parallel-{args.context}"
    target = output_dir / f"{label}.json"
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    mismatches = [
        (case["size"], run["workers"])
        for case in report["cases"]
        for run in case["runs"]
        if not run["hash_equals_sequential"]
    ]
    print(f"wrote {target}")
    if mismatches:
        print(f"HASH MISMATCH: {mismatches}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
