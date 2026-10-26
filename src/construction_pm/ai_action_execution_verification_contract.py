from __future__ import annotations

"""Strict durable contract for AI action execution verification.

This module has no dependency on the action runtime so both the verifier and
the durable store can validate exactly the same shape. Storing a loosely typed
mapping would let a malformed or cross-action record reach the Web client and
would break its all-or-nothing response parsing.
"""

import math
import re
from typing import Mapping


AI_ACTION_EXECUTION_VERIFICATION_VERSION = "ai-action-execution-verification.v1"

STATUS_COMPUTED = "COMPUTED"
STATUS_UNAVAILABLE = "UNAVAILABLE"
STATUS_FAILED = "FAILED"

_STATUSES = frozenset({STATUS_COMPUTED, STATUS_UNAVAILABLE, STATUS_FAILED})
_FIELDS = frozenset({
    "contract_version",
    "status",
    "reason_code",
    "activity",
    "project_finish",
    "calculation_run_identity",
    "snapshot",
    "query_id",
})
_ACTIVITY_FIELDS = frozenset({
    "activity_id",
    "start",
    "finish",
    "duration",
    "duration_unit",
    "critical",
})
_SNAPSHOT_FIELDS = frozenset({
    "snapshot_id",
    "snapshot_hash",
    "calculation_identity",
})
_REASON_CODE = re.compile(r"^[A-Z][A-Z0-9_]{0,119}$")


class ExecutionVerificationPayloadError(ValueError):
    """Raised when a verification payload does not satisfy the stored contract."""


def _non_empty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _reason_code(value: object) -> str:
    if not isinstance(value, str) or _REASON_CODE.fullmatch(value) is None:
        raise ExecutionVerificationPayloadError("AI_ACTION_VERIFICATION_REASON_CODE_INVALID")
    return value


def validate_execution_verification(
    value: object,
    *,
    error_code: str = "AI_ACTION_VERIFICATION_INVALID",
) -> dict[str, object]:
    """Return a normalized copy or raise a stable validation error.

    Unknown fields are rejected so a stored record cannot smuggle unrelated
    project data to a client. ``COMPUTED`` requires every calculated field;
    ``UNAVAILABLE``/``FAILED`` require a reason and forbid calculated fields.
    """
    if not isinstance(value, Mapping) or set(value) != _FIELDS:
        raise ExecutionVerificationPayloadError(error_code)
    if value.get("contract_version") != AI_ACTION_EXECUTION_VERIFICATION_VERSION:
        raise ExecutionVerificationPayloadError(error_code)
    status = value.get("status")
    if status not in _STATUSES:
        raise ExecutionVerificationPayloadError(error_code)
    reason_code = value.get("reason_code")
    activity = value.get("activity")
    snapshot = value.get("snapshot")
    project_finish = value.get("project_finish")
    calculation_run_identity = value.get("calculation_run_identity")
    query_id = value.get("query_id")

    if status == STATUS_COMPUTED:
        if reason_code is not None or not isinstance(activity, Mapping) or not isinstance(snapshot, Mapping):
            raise ExecutionVerificationPayloadError(error_code)
        if set(activity) != _ACTIVITY_FIELDS or set(snapshot) != _SNAPSHOT_FIELDS:
            raise ExecutionVerificationPayloadError(error_code)
        if (
            not _non_empty_text(activity.get("activity_id"))
            or not _non_empty_text(activity.get("start"))
            or not _non_empty_text(activity.get("finish"))
            or not _non_empty_text(activity.get("duration_unit"))
        ):
            raise ExecutionVerificationPayloadError(error_code)
        duration = activity.get("duration")
        if duration is not None and (
            isinstance(duration, bool)
            or not isinstance(duration, (int, float))
            or not math.isfinite(float(duration))
            or duration < 0
        ):
            raise ExecutionVerificationPayloadError(error_code)
        critical = activity.get("critical")
        if critical is not None and not isinstance(critical, bool):
            raise ExecutionVerificationPayloadError(error_code)
        if (
            not _non_empty_text(snapshot.get("snapshot_id"))
            or not _non_empty_text(snapshot.get("snapshot_hash"))
            or not _non_empty_text(snapshot.get("calculation_identity"))
            or not _non_empty_text(project_finish)
            or not _non_empty_text(calculation_run_identity)
            or not _non_empty_text(query_id)
        ):
            raise ExecutionVerificationPayloadError(error_code)
        return {
            "contract_version": AI_ACTION_EXECUTION_VERIFICATION_VERSION,
            "status": STATUS_COMPUTED,
            "reason_code": None,
            "activity": {
                "activity_id": str(activity["activity_id"]),
                "start": str(activity["start"]),
                "finish": str(activity["finish"]),
                "duration": None if duration is None else float(duration),
                "duration_unit": str(activity["duration_unit"]),
                "critical": critical,
            },
            "project_finish": str(project_finish),
            "calculation_run_identity": str(calculation_run_identity),
            "snapshot": {
                "snapshot_id": str(snapshot["snapshot_id"]),
                "snapshot_hash": str(snapshot["snapshot_hash"]),
                "calculation_identity": str(snapshot["calculation_identity"]),
            },
            "query_id": str(query_id),
        }

    if (
        not _non_empty_text(reason_code)
        or activity is not None
        or snapshot is not None
        or project_finish is not None
        or calculation_run_identity is not None
        or query_id is not None
    ):
        raise ExecutionVerificationPayloadError(error_code)
    return {
        "contract_version": AI_ACTION_EXECUTION_VERIFICATION_VERSION,
        "status": str(status),
        "reason_code": _reason_code(reason_code),
        "activity": None,
        "project_finish": None,
        "calculation_run_identity": None,
        "snapshot": None,
        "query_id": None,
    }


__all__ = [
    "AI_ACTION_EXECUTION_VERIFICATION_VERSION",
    "ExecutionVerificationPayloadError",
    "STATUS_COMPUTED",
    "STATUS_FAILED",
    "STATUS_UNAVAILABLE",
    "validate_execution_verification",
]
