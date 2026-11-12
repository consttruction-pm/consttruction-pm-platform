from __future__ import annotations

"""Versioned API boundary for capturing the current schedule as a baseline."""

from dataclasses import dataclass
from typing import Any

from .application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)
from .backend_p0.models import BackendScope
from .p6_baseline_capture import (
    BASELINE_CAPTURE_BASELINE_TYPES,
    P6BaselineCaptureError,
    P6BaselineCaptureRequest,
    P6BaselineCaptureService,
    P6BaselineScheduleSnapshot,
)
from .p6_baseline_repository import P6Baseline
from .scheduling.evm_source import (
    EVM_TECHNIQUES,
    EVM_TECHNIQUE_ACTIVITY_PERCENT_COMPLETE,
)

P6_BASELINE_CAPTURE_API_VERSION = "p6-baseline-capture-api.v1"


def _require_scope(scope: BackendScope, auth_context: AuthorizationContext) -> None:
    scope.validate()
    auth_context.validate()
    if (
        scope.tenant_id != auth_context.tenant_id
        or scope.project_id != auth_context.project_id
    ):
        raise AuthorizationError("CROSS_SCOPE_ACCESS")


def _require_permission(
    policy: AuthorizationPolicy,
    auth_context: AuthorizationContext,
    permission: Permission,
) -> None:
    if not policy.is_allowed(auth_context, permission):
        raise AuthorizationError(
            f"authorization denied for permission={permission.value}"
        )


def _require_contract(contract_version: str) -> None:
    if contract_version != P6_BASELINE_CAPTURE_API_VERSION:
        raise P6BaselineCaptureError(
            "BASELINE_CAPTURE_CONTRACT_VERSION_UNSUPPORTED"
        )


def _require_revision(scope: BackendScope, expected_revision: int) -> None:
    if (
        isinstance(expected_revision, bool)
        or not isinstance(expected_revision, int)
        or expected_revision < 0
    ):
        raise P6BaselineCaptureError("BASELINE_CAPTURE_REVISION_INVALID")
    if expected_revision != scope.project_revision:
        raise P6BaselineCaptureError("BASELINE_CAPTURE_STALE_REVISION")


def _scope_payload(scope: BackendScope) -> dict[str, Any]:
    return {
        "tenant_id": scope.tenant_id,
        "project_id": scope.project_id,
        "project_revision": scope.project_revision,
    }


def _baseline_payload(baseline: P6Baseline) -> dict[str, Any]:
    return {
        "baseline_id": baseline.baseline_id,
        "name": baseline.name,
        "baseline_type": baseline.baseline_type,
        "source_revision": baseline.source_revision,
        "created_at": baseline.created_at,
        "notes": baseline.notes,
    }


def _snapshot_payload(snapshot: P6BaselineScheduleSnapshot) -> dict[str, Any]:
    return {
        "snapshot_id": snapshot.snapshot_id,
        "calculation_run_identity": snapshot.calculation_run_identity,
        "project_finish": snapshot.project_finish.isoformat(),
        "activity_count": len(snapshot.activities),
    }


def _optional_text(value: object, code: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise P6BaselineCaptureError(code)
    return value


@dataclass(frozen=True)
class P6BaselineCaptureAPI:
    """Transport boundary over the authoritative baseline capture service."""

    service: P6BaselineCaptureService
    authorization_policy: AuthorizationPolicy

    def capture(
        self,
        scope: BackendScope,
        *,
        baseline_id: str,
        name: str,
        expected_revision: int,
        auth_context: AuthorizationContext,
        baseline_type: str = "USER_SELECTED",
        notes: str | None = None,
        currency: str | None = None,
        earned_value_technique: str = EVM_TECHNIQUE_ACTIVITY_PERCENT_COMPLETE,
        contract_version: str = P6_BASELINE_CAPTURE_API_VERSION,
    ) -> dict[str, Any]:
        _require_contract(contract_version)
        _require_scope(scope, auth_context)
        _require_permission(
            self.authorization_policy,
            auth_context,
            Permission.PROJECT_WRITE,
        )
        _require_revision(scope, expected_revision)
        if baseline_type not in BASELINE_CAPTURE_BASELINE_TYPES:
            raise P6BaselineCaptureError("BASELINE_CAPTURE_TYPE_INVALID")
        if earned_value_technique not in EVM_TECHNIQUES:
            raise P6BaselineCaptureError(
                "BASELINE_CAPTURE_EARNED_VALUE_TECHNIQUE_INVALID"
            )
        request = P6BaselineCaptureRequest(
            baseline_id=baseline_id,
            name=name,
            baseline_type=baseline_type,
            notes=_optional_text(notes, "BASELINE_CAPTURE_NOTES_INVALID"),
            currency=_optional_text(
                currency, "BASELINE_CAPTURE_CURRENCY_INVALID"
            ),
            earned_value_technique=earned_value_technique,
        )
        result = self.service.capture(
            scope, request, auth_context=auth_context
        )
        return {
            "contract_version": P6_BASELINE_CAPTURE_API_VERSION,
            "kind": "p6_baseline_capture",
            "scope": _scope_payload(scope),
            "baseline": _baseline_payload(result.baseline),
            "snapshot": _snapshot_payload(result.schedule),
            "currency": result.currency,
            "counts": {
                "activities": len(result.rows),
                "budgeted_cost": str(result.budgeted_cost_total()),
            },
            "excluded_activity_ids": list(result.excluded_activity_ids),
            "unattributed_expense_ids": list(
                result.unattributed_expense_ids
            ),
            "replayed": result.replayed,
        }


__all__ = [
    "P6_BASELINE_CAPTURE_API_VERSION",
    "P6BaselineCaptureAPI",
]
