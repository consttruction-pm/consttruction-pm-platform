from __future__ import annotations

"""Post-execution verification for committed AI actions.

Verification is deliberately a read-after-write check over the existing
authoritative components. It never calculates a schedule itself and never
mutates the committed action result. A successful action whose schedule
cannot be recalculated is reported as UNAVAILABLE/FAILED instead of being
shown as a fully calculated success.
"""

import re
from typing import Mapping

from .ai_action_execution_verification_contract import (
    AI_ACTION_EXECUTION_VERIFICATION_VERSION,
    STATUS_COMPUTED,
    STATUS_FAILED,
    STATUS_UNAVAILABLE,
    validate_execution_verification,
)
from .ai_action_runtime import AIActionStoredProposal
from .application.authorization import AuthorizationContext, AuthorizationError
from .backend_p0.models import BackendScope
from .backend_p0.schedule_query import SCHEDULE_QUERY_RESULT_VERSION, ScheduleQueryAPI
from .control_intelligence.contracts import ControlScope
from .control_intelligence.query import ScheduleQueryKind, ScheduleQueryRequest
from .p6_activity_master_api import P6ActivityMasterAPI
from .p6_schedule_snapshot_publication_api import P6ScheduleSnapshotPublicationAPI
from .schedule_snapshot_publisher import ScheduleSnapshotPublicationError


_SAFE_REASON_CODE = re.compile(r"^[A-Z][A-Z0-9_]{0,119}$")


def _payload(
    status: str,
    *,
    reason_code: str | None = None,
) -> dict[str, object]:
    return {
        "contract_version": AI_ACTION_EXECUTION_VERIFICATION_VERSION,
        "status": status,
        "reason_code": reason_code,
        "activity": None,
        "project_finish": None,
        "calculation_run_identity": None,
        "snapshot": None,
        "query_id": None,
    }


def _stable_code(exc: BaseException, fallback: str) -> str:
    # Never surface an arbitrary exception message to clients. Only a compact
    # upper-case diagnostic token is accepted; everything else becomes a stable
    # sanitized fallback.
    code = str(exc).split(":", 1)[0].strip().replace(" ", "_")
    return code if _SAFE_REASON_CODE.fullmatch(code) else fallback


def _is_non_empty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _verify_ai_action_execution(
    record: AIActionStoredProposal,
    *,
    activity_api: P6ActivityMasterAPI | None,
    snapshot_api: P6ScheduleSnapshotPublicationAPI | None,
    schedule_query_api: ScheduleQueryAPI | None,
    auth_context: AuthorizationContext,
    timezone_name: str | None,
    request_id: str | None = None,
) -> dict[str, object]:
    """Recalculate one committed ``activity.create`` through the Shared Core.

    The caller must invoke this only after the action runtime has durably
    committed the mutation. Every failure is contained in the returned payload;
    the committed action is never rolled back or reported as uncommitted.
    """
    if record.status != "executed":
        return _payload(STATUS_UNAVAILABLE, reason_code="AI_ACTION_NOT_EXECUTED")
    if record.proposal.tool_name not in {"activity.create", "activity.update"}:
        return _payload(STATUS_UNAVAILABLE, reason_code="AI_ACTION_VERIFICATION_NOT_SUPPORTED")
    if activity_api is None or snapshot_api is None or schedule_query_api is None:
        return _payload(STATUS_UNAVAILABLE, reason_code="SCHEDULE_VERIFICATION_NOT_COMPOSED")
    if not _is_non_empty_text(timezone_name):
        return _payload(STATUS_UNAVAILABLE, reason_code="CALCULATION_TIMEZONE_REQUIRED")
    assert timezone_name is not None
    if len(timezone_name) > 100:
        return _payload(STATUS_UNAVAILABLE, reason_code="CALCULATION_TIMEZONE_INVALID")

    auth_context.validate()
    try:
        revision = int(str(record.proposal.project_revision_id), 10)
    except (TypeError, ValueError):
        return _payload(STATUS_FAILED, reason_code="AI_ACTION_VERIFICATION_REVISION_INVALID")
    if revision < 0 or str(revision) != str(record.proposal.project_revision_id):
        return _payload(STATUS_FAILED, reason_code="AI_ACTION_VERIFICATION_REVISION_INVALID")

    result = record.result
    if not isinstance(result, Mapping):
        return _payload(STATUS_FAILED, reason_code="AI_ACTION_VERIFICATION_RESULT_MISSING")
    result_scope = result.get("scope")
    result_activity = result.get("activity")
    if not isinstance(result_scope, Mapping) or not isinstance(result_activity, Mapping):
        return _payload(STATUS_FAILED, reason_code="AI_ACTION_VERIFICATION_RESULT_INVALID")
    if (
        result_scope.get("tenant_id") != auth_context.tenant_id
        or result_scope.get("project_id") != auth_context.project_id
        or result_scope.get("project_revision") != revision
    ):
        return _payload(STATUS_FAILED, reason_code="AI_ACTION_VERIFICATION_SCOPE_MISMATCH")
    activity_id = result_activity.get("activity_id")
    if not _is_non_empty_text(activity_id):
        return _payload(STATUS_FAILED, reason_code="AI_ACTION_VERIFICATION_RESULT_INVALID")
    assert isinstance(activity_id, str)

    scope = BackendScope(auth_context.tenant_id, auth_context.project_id, revision)
    try:
        persisted = activity_api.get(scope, activity_id, auth_context=auth_context)
    except AuthorizationError:
        return _payload(STATUS_UNAVAILABLE, reason_code="PROJECT_READ_PERMISSION_REQUIRED")
    except Exception as exc:
        return _payload(
            STATUS_FAILED,
            reason_code=_stable_code(exc, "ACTIVITY_FRESH_READ_FAILED"),
        )
    if persisted is None:
        return _payload(STATUS_FAILED, reason_code="ACTIVITY_NOT_READABLE_AFTER_EXECUTION")
    persisted_activity = persisted.get("activity") if isinstance(persisted, Mapping) else None
    persisted_duration_unit = (
        persisted_activity.get("duration_unit")
        if isinstance(persisted_activity, Mapping)
        else None
    )
    if not _is_non_empty_text(persisted_duration_unit):
        return _payload(STATUS_FAILED, reason_code="ACTIVITY_FRESH_READ_INVALID")
    assert isinstance(persisted_duration_unit, str)

    try:
        published = snapshot_api.publish(
            scope,
            timezone_name=timezone_name,
            auth_context=auth_context,
            request_id=request_id,
            idempotency_key=f"ai-action-execution:{record.proposal.proposal_id}",
        )
    except AuthorizationError:
        return _payload(STATUS_UNAVAILABLE, reason_code="PROJECT_SCHEDULE_PERMISSION_REQUIRED")
    except (ScheduleSnapshotPublicationError, ValueError, TypeError, ArithmeticError, KeyError) as exc:
        return _payload(STATUS_FAILED, reason_code=_stable_code(exc, "SCHEDULE_VERIFICATION_FAILED"))
    except Exception:
        return _payload(STATUS_FAILED, reason_code="SCHEDULE_VERIFICATION_FAILED")

    published_scope = published.get("scope")
    snapshot_id = published.get("snapshot_id")
    snapshot_hash = published.get("snapshot_hash")
    calculation_identity = published.get("calculation_identity")
    if (
        not isinstance(published_scope, Mapping)
        or published_scope.get("tenant_id") != auth_context.tenant_id
        or published_scope.get("project_id") != auth_context.project_id
        or published_scope.get("project_revision") != revision
        or not _is_non_empty_text(snapshot_id)
        or not _is_non_empty_text(snapshot_hash)
        or not _is_non_empty_text(calculation_identity)
    ):
        return _payload(STATUS_FAILED, reason_code="SCHEDULE_SNAPSHOT_RESPONSE_INVALID")
    assert isinstance(snapshot_id, str)
    assert isinstance(snapshot_hash, str)
    assert isinstance(calculation_identity, str)

    query_id = f"ai-action-execution:{record.proposal.proposal_id}"
    request = ScheduleQueryRequest(
        query_id=query_id,
        scope=ControlScope(auth_context.tenant_id, auth_context.project_id, revision),
        requested_by=auth_context.user_id,
        query_text="Verify the committed activity against the authoritative schedule.",
        kind=ScheduleQueryKind.FACT,
        language="en",
        constraints={"snapshot_id": snapshot_id, "activity_ids": [activity_id]},
    )
    try:
        query_result = schedule_query_api.execute(request, auth_context=auth_context)
    except Exception as exc:
        return _payload(
            STATUS_FAILED,
            reason_code=_stable_code(exc, "SCHEDULE_QUERY_FAILED"),
        )
    if not isinstance(query_result, dict):
        return _payload(STATUS_FAILED, reason_code="SCHEDULE_QUERY_RESPONSE_INVALID")
    query_error = query_result.get("error")
    if isinstance(query_error, Mapping):
        code = query_error.get("code")
        return _payload(
            STATUS_FAILED,
            reason_code=code if _is_non_empty_text(code) else "SCHEDULE_QUERY_FAILED",
        )
    if query_result.get("contract_version") != SCHEDULE_QUERY_RESULT_VERSION:
        return _payload(STATUS_FAILED, reason_code="SCHEDULE_QUERY_RESPONSE_INVALID")

    data = query_result.get("data")
    if not isinstance(data, Mapping):
        return _payload(STATUS_FAILED, reason_code="SCHEDULE_QUERY_RESPONSE_INVALID")
    activities = data.get("activities")
    calculated = activities.get(activity_id) if isinstance(activities, Mapping) else None
    if not isinstance(calculated, Mapping):
        return _payload(STATUS_FAILED, reason_code="ACTIVITY_NOT_PRESENT_IN_CALCULATED_SCHEDULE")
    start = calculated.get("start")
    finish = calculated.get("finish")
    duration = calculated.get("duration")
    critical = calculated.get("critical")
    if not _is_non_empty_text(start) or not _is_non_empty_text(finish):
        return _payload(STATUS_FAILED, reason_code="ACTIVITY_CALCULATION_FIELDS_INVALID")
    if duration is not None and (
        isinstance(duration, bool)
        or not isinstance(duration, (int, float))
        or duration < 0
    ):
        return _payload(STATUS_FAILED, reason_code="ACTIVITY_CALCULATION_FIELDS_INVALID")
    if critical is not None and not isinstance(critical, bool):
        return _payload(STATUS_FAILED, reason_code="ACTIVITY_CALCULATION_FIELDS_INVALID")
    project_finish = data.get("project_finish")
    calculation_run_identity = data.get("calculation_run_identity")
    if not _is_non_empty_text(project_finish) or not _is_non_empty_text(calculation_run_identity):
        return _payload(STATUS_FAILED, reason_code="SCHEDULE_QUERY_RESPONSE_INVALID")

    payload = _payload(STATUS_COMPUTED)
    payload["activity"] = {
        "activity_id": activity_id,
        "start": start,
        "finish": finish,
        "duration": duration,
        "duration_unit": persisted_duration_unit,
        "critical": critical,
    }
    payload["project_finish"] = project_finish
    payload["calculation_run_identity"] = calculation_run_identity
    resolved_query_id = query_result.get("query_id")
    payload["snapshot"] = {
        "snapshot_id": snapshot_id,
        "snapshot_hash": snapshot_hash,
        "calculation_identity": calculation_identity,
    }
    payload["query_id"] = resolved_query_id if _is_non_empty_text(resolved_query_id) else query_id
    return validate_execution_verification(payload)


def verify_ai_action_execution(
    record: AIActionStoredProposal,
    *,
    activity_api: P6ActivityMasterAPI | None,
    snapshot_api: P6ScheduleSnapshotPublicationAPI | None,
    schedule_query_api: ScheduleQueryAPI | None,
    auth_context: AuthorizationContext,
    timezone_name: str | None,
    request_id: str | None = None,
) -> dict[str, object]:
    """Contain all verification failures so a committed mutation is never masked."""
    try:
        return _verify_ai_action_execution(
            record,
            activity_api=activity_api,
            snapshot_api=snapshot_api,
            schedule_query_api=schedule_query_api,
            auth_context=auth_context,
            timezone_name=timezone_name,
            request_id=request_id,
        )
    except Exception:
        return _payload(STATUS_FAILED, reason_code="SCHEDULE_VERIFICATION_FAILED")


__all__ = [
    "AI_ACTION_EXECUTION_VERIFICATION_VERSION",
    "STATUS_COMPUTED",
    "STATUS_FAILED",
    "STATUS_UNAVAILABLE",
    "verify_ai_action_execution",
]
