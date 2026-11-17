#!/usr/bin/env python3
"""Compare the P0-J leveling implementation against the pre-P0-J reference.

The P0-J leveling work replaced a rebuild-per-shift algorithm with an
incremental ledger.  Proving "same decisions, less work" needs a same-condition
comparison against the real previous implementation, not a report of previous
numbers.  This script loads ``resource_leveling.py`` from a fixed git revision
(default: the parent of the P0-J change), builds the same deterministic
fixtures in this process, and reports real timings plus the canonical output
hash for both implementations.

Only ``from .calendar import`` is rewritten in the reference copy so it can be
imported outside its original package; nothing else in that file is touched.

Example:

    python3 scripts/p0j_leveling_reference.py --mode forward --sizes 100,250 \
        --reference-rev ee9753e6 --repeat 1 --git-sha <sha> --out /tmp/ref.json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from construction_pm.scheduling.benchmark_fixtures import (  # noqa: E402
    backward_leveling_case,
    backward_leveling_payload,
    canonical_hash,
    environment_fingerprint,
    leveling_case,
    leveling_payload,
    measure,
    run_backward_leveling,
    run_leveling,
)

MODES = ("forward", "backward")


def _load_reference(revision: str):
    source = subprocess.run(
        ["git", "show", f"{revision}:src/construction_pm/scheduling/resource_leveling.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    patched = source.replace(
        "from .calendar import WorkingTimeResolver",
        "from construction_pm.scheduling.calendar import WorkingTimeResolver",
    )
    path = Path("/tmp/p0j_reference_resource_leveling.py")
    path.write_text(patched, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("p0j_reference_resource_leveling", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _measure(args, revision):
    reference = _load_reference(revision)
    if args.mode == "forward":
        fixture = leveling_case(args.size, args.seed)
        reference_operation = lambda: reference.propose_forward_leveling_within_float(  # noqa: E731
            fixture.activities, fixture.capacities, resolver=fixture.resolver
        )
        current_operation = lambda: run_leveling(fixture)  # noqa: E731
        payload = leveling_payload
    else:
        fixture = backward_leveling_case(args.size, args.seed)
        reference_operation = lambda: reference.propose_backward_leveling(  # noqa: E731
            fixture.activities, fixture.capacities, resolver=fixture.resolver, priorities=()
        )
        current_operation = lambda: run_backward_leveling(fixture)  # noqa: E731
        payload = backward_leveling_payload

    record: dict[str, object] = {
        "mode": args.mode,
        "size": args.size,
        "seed": args.seed,
        "counts": fixture.counts,
        "repeat": args.repeat,
        "warmup": args.warmup,
    }
    reference_timing = measure(reference_operation, repeat=args.repeat, warmup=args.warmup)
    current_timing = measure(current_operation, repeat=args.repeat, warmup=args.warmup)
    reference_result = reference_timing.pop("result")
    current_result = current_timing.pop("result")
    record["reference"] = {
        key: value for key, value in reference_timing.items() if key in ("wall", "cpu")
    }
    record["current"] = {
        key: value for key, value in current_timing.items() if key in ("wall", "cpu", "peak_rss_kb")
    }
    record["reference_hash"] = canonical_hash(payload(reference_result))
    record["current_hash"] = canonical_hash(payload(current_result))
    record["identical"] = record["reference_hash"] == record["current_hash"]
    record["output_counts"] = {"reference": len(reference_result), "current": len(current_result)}
    speedup = record["reference"]["wall"]["median_ms"] / record["current"]["wall"]["median_ms"]
    record["speedup_median"] = round(speedup, 2)
    record["status"] = "ok" if record["identical"] else "mismatch"
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--sizes", required=True, help="comma separated activity counts")
    parser.add_argument("--seed", type=int, default=20261116)
    parser.add_argument("--reference-rev", default="ee9753e6")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--warmup", type=int, default=0)
    parser.add_argument("--git-sha", default=None)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    records = []
    for size in (int(part) for part in args.sizes.replace(" ", "").split(",") if part):
        args.size = size
        started = time.time()
        record = _measure(args, args.reference_rev)
        record["elapsed_s"] = round(time.time() - started, 3)
        records.append(record)
        print(json.dumps(record, sort_keys=True), flush=True)
    document = {
        "mode": args.mode,
        "reference_rev": args.reference_rev,
        "repeat": args.repeat,
        "warmup": args.warmup,
        "seed": args.seed,
        "records": records,
        "environment": environment_fingerprint(args.git_sha),
    }
    Path(args.out).write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if all(record["identical"] for record in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
