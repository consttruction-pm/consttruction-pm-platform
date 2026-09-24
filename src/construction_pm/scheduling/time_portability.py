from __future__ import annotations

import json
from hashlib import sha256
from typing import Any


def canonicalize_time_scheduling_payload(payload: dict[str, Any]) -> str:
    """Return a deterministic JSON representation for cross-client parity checks."""
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def time_scheduling_fingerprint(payload: dict[str, Any]) -> str:
    canonical = canonicalize_time_scheduling_payload(payload)
    return sha256(canonical.encode("utf-8")).hexdigest()


def round_trip_time_scheduling_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Simulate portable JSON round-trip without changing wire semantics."""
    return json.loads(canonicalize_time_scheduling_payload(payload))
