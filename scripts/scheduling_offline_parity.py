#!/usr/bin/env python3
"""Prove the offline scheduling runtime boundary on real fixtures.

For each requested size this script:

1. builds an immutable authoritative snapshot and its exact calendar registry;
2. evaluates it online through ``evaluate_schedule_snapshot``;
3. binds the snapshot, calendars and calculation context into a self-contained
   offline bundle and serializes it to JSON;
4. executes that bundle in a *fresh subprocess whose socket layer is disabled
   before any ``construction_pm`` import*, so the whole import + calculation
   path is proven network-free;
5. compares the canonical ``calculation_run_identity`` of both paths.

No number is estimated: every timing comes from a real run, and a subprocess
failure is recorded as an error rather than extrapolated.

    python3 scripts/scheduling_offline_parity.py --sizes 500,2000 --runs 3 \
        --output docs/workspace/evidence/p0i-offline-runtime-2026-11-16/offline-parity.json
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from construction_pm.offline_schedule_runtime import build_offline_bundle  # noqa: E402
from construction_pm.schedule_evaluator import evaluate_schedule_snapshot  # noqa: E402
from construction_pm.schedule_input_snapshot_repository import build_snapshot  # noqa: E402
from construction_pm.scheduling.authoritative_schedule import (  # noqa: E402
    ActivityCalendarAssignment,
    AuthoritativeScheduleInput,
    AuthoritativeScheduleMode,
)
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver  # noqa: E402
from construction_pm.scheduling.calendar_context import (  # noqa: E402
    CalendarReference,
    CalendarResolverRegistry,
)
from construction_pm.scheduling.calculation_context import CalculationContext  # noqa: E402
from construction_pm.scheduling.benchmark_fixtures import (  # noqa: E402
    date_network,
    environment_fingerprint,
)

PROJECT_CALENDAR = CalendarReference("CAL-P", "1")
ACTIVITY_CALENDAR = CalendarReference("CAL-A", "1")
BASE_CALENDAR = CalendarReference("CAL-BASE", "1")


NETWORK_DENIAL = r"""
import socket

def _denied(operation):
    def _raise(*args, **kwargs):
        raise RuntimeError("OFFLINE_NETWORK_ACCESS_DENIED:" + operation)
    return _raise

# Disable the network before importing any construction_pm module so the whole
# import and calculation path is covered by the guard.
socket.socket.connect = _denied("connect")
socket.socket.connect_ex = _denied("connect_ex")
socket.create_connection = _denied("create_connection")
socket.getaddrinfo = _denied("getaddrinfo")
"""

SUBPROCESS_CODE = (
    NETWORK_DENIAL
    + r"""
import json
import sys
import time

started = time.perf_counter()
from construction_pm.offline_schedule_runtime import OfflineSchedulingRuntime

with open(sys.argv[1], "r", encoding="utf-8") as handle:
    text = handle.read()
parsed = time.perf_counter()
runtime = OfflineSchedulingRuntime.from_json(text)
execution = runtime.execute()
finished = time.perf_counter()

print(json.dumps({
    "ok": True,
    "bundle_hash": execution.bundle_hash,
    "snapshot_hash": execution.snapshot_hash,
    "calculation_run_identity": execution.calculation_run_identity,
    "load_ms": round((parsed - started) * 1000, 3),
    "execute_ms": round((finished - parsed) * 1000, 3),
    "total_ms": round((finished - started) * 1000, 3),
}))
"""
)

PROBE_CODE = (
    NETWORK_DENIAL
    + r"""
import json
import socket

try:
    socket.create_connection(("127.0.0.1", 9), timeout=0.2)
except RuntimeError as exc:
    print(json.dumps({"denied": str(exc)}))
else:
    print(json.dumps({"denied": None}))
"""
)


def _build_case(size: int):
    fixture = date_network(size, "dag", 20261116)
    registry = CalendarResolverRegistry(
        day_resolvers={
            "CAL-P@1": WorkingTimeResolver(
                WorkingCalendar(holidays=frozenset({date(2026, 1, 6), date(2026, 2, 17)}))
            ),
            "CAL-A@1": WorkingTimeResolver(
                WorkingCalendar(
                    holidays=frozenset({date(2026, 3, 20), date(2026, 4, 3)})
                )
            ),
            "CAL-BASE@1": WorkingTimeResolver(
                WorkingCalendar(holidays=frozenset({date(2026, 12, 25)}))
            ),
        },
        base_calendar_references={"CAL-A@1": BASE_CALENDAR},
    )
    snapshot_id = f"S-OFFLINE-{size}"
    source = AuthoritativeScheduleInput(
        snapshot_id=snapshot_id,
        tenant_id="T-OFFLINE",
        project_id="P-OFFLINE",
        project_revision=size,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=PROJECT_CALENDAR,
        activities=tuple(fixture.activities),
        relationships=tuple(fixture.relationships),
        activity_calendar_assignments=tuple(
            ActivityCalendarAssignment(activity.id, ACTIVITY_CALENDAR)
            for activity in fixture.activities
        ),
        project_start=fixture.project_start,
    )
    context = CalculationContext(
        project_id="P-OFFLINE",
        project_version=size,
        calendar_id="CAL-P",
        calendar_version="1",
        rules_version="rules-v26",
        engine_version="shared-scheduling-core",
        timezone="UTC",
        calculation_timestamp="2026-11-16T00:00:00+00:00",
        input_snapshot_id=snapshot_id,
        tenant_id="T-OFFLINE",
    )
    snapshot = build_snapshot(
        source, context, datetime(2026, 11, 16, tzinfo=timezone.utc)
    )
    return fixture, snapshot, context, registry


def _time_online(snapshot, context, registry) -> tuple[str, float]:
    started = time.perf_counter()
    result = evaluate_schedule_snapshot(snapshot, context, registry)
    return result.calculation_run_identity, (time.perf_counter() - started) * 1000


def _run_offline_subprocess(bundle_text: str) -> dict:
    with tempfile.NamedTemporaryFile(
        "w", suffix=".offline-schedule.json", delete=True, encoding="utf-8"
    ) as handle:
        handle.write(bundle_text)
        handle.flush()
        completed = subprocess.run(
            [sys.executable, "-c", SUBPROCESS_CODE, handle.name],
            capture_output=True,
            text=True,
            timeout=900,
            env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        )
    if completed.returncode != 0:
        return {
            "ok": False,
            "returncode": completed.returncode,
            "stderr": completed.stderr.strip()[-4000:],
        }
    try:
        return json.loads(completed.stdout.strip().splitlines()[-1])
    except (IndexError, ValueError):
        return {
            "ok": False,
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip()[-2000:],
        }


def _median(values):
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def _probe_network_guard() -> dict:
    completed = subprocess.run(
        [sys.executable, "-c", PROBE_CODE],
        capture_output=True,
        text=True,
        timeout=60,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
    )
    if completed.returncode != 0:
        return {"ok": False, "stderr": completed.stderr.strip()[-2000:]}
    try:
        payload = json.loads(completed.stdout.strip().splitlines()[-1])
    except (IndexError, ValueError):
        return {"ok": False, "stdout": completed.stdout.strip()[-1000:]}
    return {
        "ok": payload.get("denied")
        == "OFFLINE_NETWORK_ACCESS_DENIED:create_connection",
        "denied": payload.get("denied"),
    }


def run_size(size: int, runs: int) -> dict:
    fixture, snapshot, context, registry = _build_case(size)
    online_samples = []
    run_identity = None
    for _ in range(runs):
        run_identity, elapsed_ms = _time_online(snapshot, context, registry)
        online_samples.append(elapsed_ms)

    started = time.perf_counter()
    bundle = build_offline_bundle(snapshot, context, registry)
    bundle_text = bundle.to_json()
    bundle_build_ms = (time.perf_counter() - started) * 1000

    offline_samples = []
    offline_identity = None
    failures = []
    for _ in range(runs):
        result = _run_offline_subprocess(bundle_text)
        if not result.get("ok"):
            failures.append(result)
            continue
        offline_samples.append(result["execute_ms"])
        offline_identity = result["calculation_run_identity"]

    record = {
        "size": size,
        "counts": fixture.counts,
        "snapshot_id": snapshot.snapshot_id,
        "snapshot_hash": snapshot.snapshot_hash,
        "calculation_identity": context.calculation_identity,
        "bundle_hash": bundle.bundle_hash,
        "bundle_bytes": len(bundle_text.encode("utf-8")),
        "calendars": sorted(
            f"{item.reference.calendar_id}@{item.reference.calendar_version}"
            for item in bundle.calendars
        ),
        "online_run_identity": run_identity,
        "online_median_ms": round(_median(online_samples), 3),
        "bundle_build_ms": round(bundle_build_ms, 3),
        "offline_runs": len(offline_samples),
        "offline_median_execute_ms": (
            round(_median(offline_samples), 3) if offline_samples else None
        ),
        "offline_run_identity": offline_identity,
        "identity_equal": run_identity == offline_identity,
        "failures": failures,
    }
    record["ok"] = bool(offline_samples) and record["identity_equal"] and not failures
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", default="500,2000", help="comma-separated activity counts")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--git-sha", default=None)
    args = parser.parse_args()

    sizes = [int(part) for part in args.sizes.replace(" ", "").split(",") if part]
    if not sizes or any(size <= 0 for size in sizes):
        parser.error("sizes must be positive integers")
    if args.runs < 1:
        parser.error("runs must be at least 1")

    results = [run_size(size, args.runs) for size in sizes]
    guard_probe = _probe_network_guard()
    payload = {
        "phase": "P0-I",
        "boundary": "offline-schedule-bundle/v1",
        "engine": "shared-scheduling-core",
        "runs_per_size": args.runs,
        "environment": environment_fingerprint(args.git_sha),
        "network_guard_probe": guard_probe,
        "results": results,
        "ok": guard_probe["ok"] and all(item["ok"] for item in results),
    }
    encoded = json.dumps(payload, indent=2, sort_keys=True)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
