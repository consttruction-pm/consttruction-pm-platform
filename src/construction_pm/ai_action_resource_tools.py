"""Approval-gated project resource/equipment assignment tool.

The tool writes only through CUBI's authenticated resource application API. It does
not invent resource-master records, production rates, actual usage, or capacity results.
"""
from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal, InvalidOperation
from typing import Mapping

from .ai_action_activity_tools import AIActionExecutionIdempotencyStore
from .ai_action_boundary import AIActionProposal
from .ai_action_runtime import (
    AIActionRuntimeContext,
    AIActionRuntimeError,
    AIActionToolDefinition,
)
from .application.authorization import AuthorizationContext
from .backend_p0.models import BackendScope
from .p6_activity_master_api import P6ActivityMasterAPI
from .p6_resource_assignment_repository import P6ResourceAssignment
from .p6_resource_read_api import P6ResourceReadAPI
from .p6_resource_write_api import P6ResourceWriteAPI


_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_CURRENCY = re.compile(r"^[A-Z]{3}$")


class AIResourceAssignmentToolError(ValueError):
    """Stable validation, scope or persistence error for assistant resource actions."""


def _text(value: object, *, field: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise AIResourceAssignmentToolError(f"AI_RESOURCE_ASSIGNMENT_{field.upper()}_INVALID")
    value = value.strip()
    if not 1 <= len(value) <= maximum:
        raise AIResourceAssignmentToolError(f"AI_RESOURCE_ASSIGNMENT_{field.upper()}_INVALID")
    return value


def _decimal(value: object, *, field: str, positive: bool = False) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise AIResourceAssignmentToolError(f"AI_RESOURCE_ASSIGNMENT_{field.upper()}_INVALID")
    try:
        parsed = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise AIResourceAssignmentToolError(
            f"AI_RESOURCE_ASSIGNMENT_{field.upper()}_INVALID"
        ) from exc
    if not parsed.is_finite() or parsed < 0 or (positive and parsed == 0):
        raise AIResourceAssignmentToolError(f"AI_RESOURCE_ASSIGNMENT_{field.upper()}_INVALID")
    return parsed


def _safe_json(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _safe_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe_json(item) for item in value]
    return value


def _assignment_values(item: P6ResourceAssignment) -> dict[str, object]:
    return {
        "assignment_id": item.assignment_id,
        "activity_id": item.activity_id,
        "resource_id": item.resource_id,
        "role_id": item.role_id,
        "units": None if item.units is None else str(item.units),
        "actual_units": None if item.actual_units is None else str(item.actual_units),
        "remaining_units": None if item.remaining_units is None else str(item.remaining_units),
        "planned_cost": None if item.planned_cost is None else str(item.planned_cost),
        "actual_cost": None if item.actual_cost is None else str(item.actual_cost),
        "remaining_cost": None if item.remaining_cost is None else str(item.remaining_cost),
        "unit": item.unit,
        "currency": item.currency,
        "calendar_id": item.calendar_id,
        "note": item.note,
        "calendar_version": item.calendar_version,
        "is_driving": item.is_driving,
        "units_per_time": None if item.units_per_time is None else str(item.units_per_time),
        "units_per_time_period": item.units_per_time_period,
        "hours_per_units_time_period": (
            None if item.hours_per_units_time_period is None
            else str(item.hours_per_units_time_period)
        ),
    }


def _validate_payload(payload: Mapping[str, object]) -> Mapping[str, object]:
    required = {"assignment_id", "activity_id", "resource_id", "units", "unit"}
    allowed = required | {
        "role_id", "planned_cost", "currency", "calendar_id", "calendar_version",
        "note", "is_driving",
    }
    if not isinstance(payload, Mapping) or not required.issubset(payload) or not set(payload).issubset(allowed):
        raise AIResourceAssignmentToolError("AI_RESOURCE_ASSIGNMENT_PAYLOAD_INVALID")

    values = {
        name: _text(payload[name], field=name, maximum=128 if name.endswith("_id") else 64)
        for name in ("assignment_id", "activity_id", "resource_id", "unit")
    }
    for name in ("assignment_id", "activity_id", "resource_id"):
        if not _ID.fullmatch(values[name]):
            raise AIResourceAssignmentToolError(f"AI_RESOURCE_ASSIGNMENT_{name.upper()}_INVALID")

    units = _decimal(payload["units"], field="units", positive=True)
    role_id = None if payload.get("role_id") is None else _text(
        payload["role_id"], field="role_id", maximum=128
    )
    note = None if payload.get("note") is None else _text(
        payload["note"], field="note", maximum=1000
    )
    is_driving = payload.get("is_driving")
    if is_driving is not None and not isinstance(is_driving, bool):
        raise AIResourceAssignmentToolError("AI_RESOURCE_ASSIGNMENT_IS_DRIVING_INVALID")

    planned_cost = None if payload.get("planned_cost") is None else _decimal(
        payload["planned_cost"], field="planned_cost"
    )
    currency_raw = payload.get("currency")
    if planned_cost is None:
        if currency_raw is not None:
            raise AIResourceAssignmentToolError("AI_RESOURCE_ASSIGNMENT_CURRENCY_WITHOUT_COST")
        currency = None
    else:
        if not isinstance(currency_raw, str):
            raise AIResourceAssignmentToolError("AI_RESOURCE_ASSIGNMENT_CURRENCY_REQUIRED")
        currency = currency_raw.strip().upper()
        if not _CURRENCY.fullmatch(currency):
            raise AIResourceAssignmentToolError("AI_RESOURCE_ASSIGNMENT_CURRENCY_INVALID")

    calendar_id = None if payload.get("calendar_id") is None else _text(
        payload["calendar_id"], field="calendar_id", maximum=128
    )
    calendar_version = None if payload.get("calendar_version") is None else _text(
        payload["calendar_version"], field="calendar_version", maximum=128
    )
    if (calendar_id is None) != (calendar_version is None):
        raise AIResourceAssignmentToolError("AI_RESOURCE_ASSIGNMENT_CALENDAR_VERSION_PAIR_REQUIRED")

    normalized: dict[str, object] = {
        **values,
        "units": str(units),
        "role_id": role_id,
        "planned_cost": None if planned_cost is None else str(planned_cost),
        "currency": currency,
        "calendar_id": calendar_id,
        "calendar_version": calendar_version,
        "note": note,
        "is_driving": is_driving,
    }
    # Actuals and remaining values are never supplied by the model in this tool.
    return normalized


def build_resource_assignment_create_tool(
    *,
    activity_api: P6ActivityMasterAPI,
    resource_write_api: P6ResourceWriteAPI,
    resource_read_api: P6ResourceReadAPI,
    idempotency_store: AIActionExecutionIdempotencyStore,
    transaction_manager: object,
) -> AIActionToolDefinition:
    """Build a typed resource-assignment tool with approval, audit and fresh read-back.

    The resource master/capacity catalog is not yet a complete cross-domain validation
    dependency in every deployment. Therefore the result explicitly labels resource
    reference verification and capacity review as not performed; neither is guessed.
    """
    connection = getattr(transaction_manager, "connection", None)
    assignment_service = resource_write_api.assignment_service
    read_service = resource_read_api.assignment_service
    if assignment_service is None or connection is None:
        raise AIActionRuntimeError("AI_RESOURCE_ASSIGNMENT_WRITE_SERVICE_REQUIRED")
    for repository in (
        activity_api.repository,
        assignment_service.repository,
        read_service.repository,
        idempotency_store,
    ):
        repository_connection = getattr(repository, "connection", None)
        if repository_connection is not connection:
            raise AIActionRuntimeError("AI_RESOURCE_ASSIGNMENT_TRANSACTION_CONNECTION_MISMATCH")

    def execute(
        payload: Mapping[str, object],
        proposal: AIActionProposal,
        idempotency_key: str,
        context: AIActionRuntimeContext,
    ) -> Mapping[str, object]:
        context.validate()
        if (
            proposal.tenant_id != context.tenant_id
            or proposal.project_id != context.project_id
            or proposal.project_revision_id != context.project_revision_id
            or proposal.requested_by != context.subject_id
        ):
            raise AIActionRuntimeError("AI_RESOURCE_ASSIGNMENT_TOOL_SCOPE_MISMATCH")
        try:
            revision = int(context.project_revision_id, 10)
        except (TypeError, ValueError) as exc:
            raise AIActionRuntimeError("AI_RESOURCE_ASSIGNMENT_PROJECT_REVISION_INVALID") from exc
        if revision < 0 or str(revision) != context.project_revision_id:
            raise AIActionRuntimeError("AI_RESOURCE_ASSIGNMENT_PROJECT_REVISION_INVALID")

        normalized = _validate_payload(payload)
        scope = BackendScope(context.tenant_id, context.project_id, revision)
        auth = AuthorizationContext(
            tenant_id=context.tenant_id,
            project_id=context.project_id,
            user_id=context.subject_id,
            roles=context.roles,
        )
        # An assignment cannot target a missing activity or a scope that the actor cannot read.
        if activity_api.get(scope, str(normalized["activity_id"]), auth_context=auth) is None:
            raise AIResourceAssignmentToolError("AI_RESOURCE_ASSIGNMENT_ACTIVITY_NOT_FOUND")

        assignment = P6ResourceAssignment(
            scope=scope,
            assignment_id=str(normalized["assignment_id"]),
            activity_id=str(normalized["activity_id"]),
            resource_id=str(normalized["resource_id"]),
            role_id=None if normalized["role_id"] is None else str(normalized["role_id"]),
            units=Decimal(str(normalized["units"])),
            planned_cost=None if normalized["planned_cost"] is None else Decimal(str(normalized["planned_cost"])),
            unit=str(normalized["unit"]),
            currency=None if normalized["currency"] is None else str(normalized["currency"]),
            calendar_id=None if normalized["calendar_id"] is None else str(normalized["calendar_id"]),
            calendar_version=None if normalized["calendar_version"] is None else str(normalized["calendar_version"]),
            note=None if normalized["note"] is None else str(normalized["note"]),
            is_driving=normalized["is_driving"],  # type: ignore[arg-type]
        )
        assignment.validate()
        fingerprint_payload = json.dumps(
            {
                "operation": "resource.assignment.create",
                "tenant_id": context.tenant_id,
                "project_id": context.project_id,
                "project_revision_id": context.project_revision_id,
                "payload": dict(normalized),
            },
            ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        )
        request_fingerprint = hashlib.sha256(fingerprint_payload.encode("utf-8")).hexdigest()

        def persist() -> Mapping[str, object]:
            created = resource_write_api.save_assignment(assignment, auth_context=auth)
            fresh = resource_read_api.get_assignment(
                scope, assignment.assignment_id, auth_context=auth
            )
            if fresh is None:
                raise AIResourceAssignmentToolError("AI_RESOURCE_ASSIGNMENT_READBACK_FAILED")
            fresh_assignment = read_service.read(scope, assignment.assignment_id)
            if fresh_assignment is None or _assignment_values(fresh_assignment) != created["assignment"]:
                # P6 Read/Write DTOs have different version envelopes but the assignment
                # payload itself must be byte-for-byte equivalent after Decimal encoding.
                created_values = _safe_json(created["assignment"])
                if fresh_assignment is None or _assignment_values(fresh_assignment) != created_values:
                    raise AIResourceAssignmentToolError("AI_RESOURCE_ASSIGNMENT_READBACK_MISMATCH")
            return {
                "contract_version": "ai-resource-assignment-result.v1",
                "assignment": _assignment_values(fresh_assignment),
                "scope": {
                    "tenant_id": scope.tenant_id,
                    "project_id": scope.project_id,
                    "project_revision": scope.project_revision,
                },
                "persisted_readback_verified": True,
                "resource_reference_status": "unverified_reference",
                "capacity_check_status": "not_performed",
                "note": (
                    "Resource master identity and time-phased capacity were not verified by this action. "
                    "Review these before relying on the assignment for leveling."
                ),
            }

        return idempotency_store.execute(
            tenant_id=context.tenant_id,
            project_id=context.project_id,
            tool_name=proposal.tool_name,
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint,
            mutation=persist,
        )

    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["assignment_id", "activity_id", "resource_id", "units", "unit"],
        "properties": {
            "assignment_id": {"type": "string", "minLength": 1, "maxLength": 64},
            "activity_id": {
                "type": "string", "minLength": 1, "maxLength": 64,
                "description": "Existing activity ID from the current project; do not invent it.",
            },
            "resource_id": {
                "type": "string", "minLength": 1, "maxLength": 64,
                "description": "Existing resource ID explicitly selected or confirmed by the user. Never invent resource IDs.",
            },
            "units": {"type": "number", "exclusiveMinimum": 0},
            "unit": {"type": "string", "minLength": 1, "maxLength": 64},
            "role_id": {"type": ["string", "null"], "maxLength": 128},
            "planned_cost": {"type": ["number", "null"], "minimum": 0},
            "currency": {"type": ["string", "null"], "pattern": "^[A-Z]{3}$"},
            "calendar_id": {"type": ["string", "null"], "maxLength": 128},
            "calendar_version": {"type": ["string", "null"], "maxLength": 128},
            "note": {"type": ["string", "null"], "maxLength": 1000},
            "is_driving": {"type": ["boolean", "null"]},
        },
    }
    return AIActionToolDefinition(
        tool_name="resource.assignment.create",
        action="create",
        resource_domain="resources",
        requires_human_approval=True,
        validate_payload=_validate_payload,
        execute=execute,
        description=(
            "Propose an assignment of an explicitly user-confirmed existing labor or equipment resource "
            "to an existing activity. Do not invent resource IDs, prices, actuals or capacity. "
            "All assignments require user approval. The current slice does not verify the resource master "
            "or time-phased capacity; disclose that before the user relies on the plan."
        ),
        input_schema=schema,
    )


__all__ = ["AIResourceAssignmentToolError", "build_resource_assignment_create_tool"]
