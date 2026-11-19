"""Canonical time-schedule hashes for the sequential Oracle path.

Run with the target tree's ``src`` on ``sys.path``:

    cd <tree> && PYTHONPATH=src python3 /tmp/p0m_baseline_hash.py
"""
from __future__ import annotations

import importlib
import json

bf = importlib.import_module("construction_pm.scheduling.benchmark_fixtures")
ts = importlib.import_module("construction_pm.scheduling.time_schedule")

rows = []
for size, shape in ((1000, "dag"), (5000, "dag"), (25000, "dag"), (100000, "dag"), (25000, "mixed")):
    fixture = bf.time_network(size, shape)
    result = ts.time_schedule(
        fixture.activities,
        fixture.relationships,
        fixture.project_start,
        fixture.project_finish,
        fixture.registry,
        float_workers=1,
    )
    rows.append(
        {
            "size": size,
            "shape": shape,
            "activities": len(fixture.activities),
            "relationships": len(fixture.relationships),
            "sha256": bf.canonical_hash(bf.time_schedule_payload(result)),
        }
    )
    print(rows[-1], flush=True)
json.dump(rows, open("/tmp/p0m-baseline-hashes.json", "w"), indent=1)
