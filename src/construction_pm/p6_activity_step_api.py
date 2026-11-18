"""Versioned read boundary for activity step child records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import uuid

from .application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)
from .backend_p0.models import BackendScope
from .p6_activity_step_repository import (
    P6ActivityStep,
    P6ActivityStepApplicationService,
    P6ActivityStepPersistenceError,
)

P6_ACTIVITY_STEP_READ_API_VERSION = "p6-activity-step-read-api.v1"


def _require_scope(scope: BackendScope, auth_context: AuthorizationContext) -> None:
    scope.validate()
    auth_context.validate()
    if scope.tenant_id != auth_context.tenant_id or scope.project_id != auth_context.project_id:
        raise AuthorizationError("CROSS_SCOPE_ACCESS")


def _scope_dto(scope: BackendScope) -> dict[str, Any]:
    return {
        "tenant_id": scope.tenant_id,
        "project_id": scope.project_id,
        "project_revision": scope.project_revision,
    }


def _step_dto(step: P6ActivityStep, percent_complete: str | None = None) -> dict[str, Any]:
    return {
        "step_id": step.step_id,
        "activity_id": step.activity_id,
        "sequence": step.sequence,
        "description": step.description,
        "weight": None if step.weight is None else str(step.weight),
        "percent_complete": percent_complete,
        "start_date": step.start_date,
        "finish_date": step.finish_date,
        "udf_values": {key: value for key, value in step.udf_values},
    }


@dataclass(frozen=True)
class P6ActivityStepReadAPI:
    """Read-only activity steps with revision and permission enforcement."""

    service: P6ActivityStepApplicationService
    authorization_policy: AuthorizationPolicy

    def list(
        self,
        scope: BackendScope,
        activity_id: str,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(scope, auth_context)
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_READ):
            raise AuthorizationError("ACTIVITY_STEP_READ_NOT_AUTHORIZED")
        if not isinstance(activity_id, str) or not activity_id.strip():
            raise P6ActivityStepPersistenceError("INVALID_ACTIVITY_ID")
        steps = self.service.list(scope, activity_id)
        percent = self.service.percent_by_activity(scope, activity_id)
        # The stored order is authoritative: sequence, then step id.
        return {
            "contract_version": P6_ACTIVITY_STEP_READ_API_VERSION,
            "kind": "p6_activity_step_list",
            "scope": _scope_dto(scope),
            "activity_id": activity_id,
            "steps": [_step_dto(step, percent.get(step.step_id)) for step in steps],
        }


@dataclass(frozen=True)
class P6ActivityStepWriteAPI:
    """Create, edit, move and delete activity steps.

    A step is a planning detail of the activity, never a scheduling input:
    moving or re-weighting steps does not touch dates, float or the critical
    path, and the activity percent complete is still read from the scheduling
    core. ``percent_complete`` here is the step's own progress value.
    """

    service: P6ActivityStepApplicationService
    authorization_policy: AuthorizationPolicy
    clock: object | None = None

    def _now(self) -> str:
        from datetime import datetime, timezone

        clock = getattr(self.clock, "now", None)
        value = clock() if callable(clock) else datetime.now(timezone.utc)
        return value.replace(microsecond=0).isoformat()

    def _check(
        self, scope: BackendScope, auth_context: AuthorizationContext, permission: Permission
    ) -> None:
        _require_scope(scope, auth_context)
        if not self.authorization_policy.is_allowed(auth_context, permission):
            raise AuthorizationError("ACTIVITY_STEP_WRITE_NOT_AUTHORIZED")

    @staticmethod
    def _parse_percent(value: object) -> str | None:
        if value is None or value == "":
            return None
        from decimal import Decimal, InvalidOperation

        try:
            parsed = Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise P6ActivityStepPersistenceError("INVALID_PERCENT_COMPLETE") from exc
        if not parsed.is_finite() or parsed < 0 or parsed > 100:
            raise P6ActivityStepPersistenceError("INVALID_PERCENT_COMPLETE")
        return str(parsed)

    def create(
        self,
        scope: BackendScope,
        activity_id: str,
        *,
        description: str,
        weight: str | None,
        percent_complete: object,
        sequence: int | None,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        self._check(scope, auth_context, Permission.PROJECT_WRITE)
        if not activity_id.strip():
            raise P6ActivityStepPersistenceError("INVALID_ACTIVITY_ID")
        existing = self.service.list(scope, activity_id)
        next_sequence = max((item.sequence for item in existing), default=0) + 1 if sequence is None else sequence
        step = P6ActivityStep(
            scope=scope,
            step_id=f"STEP-{uuid.uuid4()}",
            activity_id=activity_id,
            sequence=next_sequence,
            description=description.strip(),
            weight=None if weight is None else _decimal(weight),
        )
        stored = self.service.save(step)
        percent = self._parse_percent(percent_complete)
        if percent is not None:
            self.service.set_completion(scope, stored.step_id, percent, self._now())
        return {
            "contract_version": P6_ACTIVITY_STEP_READ_API_VERSION,
            "kind": "p6_activity_step",
            "step": _step_dto(stored, percent),
        }

    def update(
        self,
        scope: BackendScope,
        activity_id: str,
        step_id: str,
        *,
        description: str | None,
        weight: str | None,
        percent_complete: object,
        sequence: int | None,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        self._check(scope, auth_context, Permission.PROJECT_WRITE)
        existing = self.service.read(scope, step_id)
        if existing is None or existing.activity_id != activity_id:
            raise P6ActivityStepPersistenceError("ACTIVITY_STEP_NOT_FOUND")
        updated = P6ActivityStep(
            scope=scope,
            step_id=existing.step_id,
            activity_id=existing.activity_id,
            sequence=existing.sequence if sequence is None else sequence,
            description=existing.description if description is None else description.strip(),
            weight=existing.weight if weight is None else _decimal(weight),
            start_date=existing.start_date,
            finish_date=existing.finish_date,
            udf_values=existing.udf_values,
        )
        stored = self.service.replace(updated)
        percent = None if percent_complete is None else self._parse_percent(percent_complete)
        if percent is not None:
            self.service.set_completion(scope, stored.step_id, percent, self._now())
        else:
            percent = self.service.percent_by_activity(scope, activity_id).get(step_id)
        return {
            "contract_version": P6_ACTIVITY_STEP_READ_API_VERSION,
            "kind": "p6_activity_step",
            "step": _step_dto(stored, percent),
        }

    def delete(
        self, scope: BackendScope, activity_id: str, step_id: str, *, auth_context: AuthorizationContext
    ) -> dict[str, Any]:
        self._check(scope, auth_context, Permission.PROJECT_WRITE)
        existing = self.service.read(scope, step_id)
        if existing is None or existing.activity_id != activity_id:
            raise P6ActivityStepPersistenceError("ACTIVITY_STEP_NOT_FOUND")
        if not self.service.delete(scope, step_id):
            raise P6ActivityStepPersistenceError("ACTIVITY_STEP_NOT_FOUND")
        return {
            "contract_version": P6_ACTIVITY_STEP_READ_API_VERSION,
            "kind": "p6_activity_step_delete",
            "step_id": step_id,
            "deleted": True,
        }


def _decimal(value: str):
    from decimal import Decimal, InvalidOperation

    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise P6ActivityStepPersistenceError("INVALID_WEIGHT") from exc
    if not parsed.is_finite() or parsed < 0:
        raise P6ActivityStepPersistenceError("INVALID_WEIGHT")
    return parsed


__all__ = [
    "P6_ACTIVITY_STEP_READ_API_VERSION",
    "P6ActivityStepReadAPI",
    "P6ActivityStepWriteAPI",
]
