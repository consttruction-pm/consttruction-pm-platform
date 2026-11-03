from __future__ import annotations

"""Versioned API boundary for selective baseline update and comparison."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Iterable

from .application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)
from .backend_p0.models import BackendScope
from .p6_baseline_repository import P6Baseline
from .p6_baseline_update import (
    BASELINE_COMPARISON_STATUS_ADDED,
    BASELINE_COMPARISON_STATUS_CHANGED,
    BASELINE_COMPARISON_STATUS_DELETED,
    BASELINE_COMPARISON_STATUS_UNCHANGED,
    P6BaselineActivityComparison,
    P6BaselineUpdateError,
    P6BaselineUpdatePlan,
    P6BaselineUpdateSelection,
    P6BaselineUpdateService,
)

P6_BASELINE_UPDATE_API_VERSION = "p6-baseline-update-api.v1"
BASELINE_VARIANCE_CONVENTION = "CURRENT_MINUS_BASELINE"


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
    if contract_version != P6_BASELINE_UPDATE_API_VERSION:
        raise P6BaselineUpdateError(
            "BASELINE_UPDATE_CONTRACT_VERSION_UNSUPPORTED"
        )


def _require_revision(scope: BackendScope, expected_revision: int) -> None:
    if (
        isinstance(expected_revision, bool)
        or not isinstance(expected_revision, int)
        or expected_revision < 0
    ):
        raise P6BaselineUpdateError("BASELINE_UPDATE_REVISION_INVALID")
    if expected_revision != scope.project_revision:
        raise P6BaselineUpdateError("BASELINE_UPDATE_STALE_REVISION")


def _require_identifier(value: object, code: str) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or value != value.strip()
    ):
        raise P6BaselineUpdateError(code)
    return value


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


def _selection_payload(selection: P6BaselineUpdateSelection) -> dict[str, Any]:
    return {
        "activity_ids": (
            None
            if selection.activity_ids is None
            else sorted(selection.activity_ids)
        ),
        "fields": sorted(selection.fields),
        "add_new_activities": selection.add_new_activities,
        "remove_missing_activities": selection.remove_missing_activities,
    }


def _value(value: object) -> object:
    if isinstance(value, (date, Decimal)):
        return str(value)
    return value


def _row_field(row: object, field: str) -> object:
    if row is None:
        return None
    return _value(getattr(row, field, None))


def _change_type(plan: P6BaselineUpdatePlan, activity_id: str) -> str:
    if activity_id in plan.added_activity_ids:
        return BASELINE_COMPARISON_STATUS_ADDED
    if activity_id in plan.removed_activity_ids:
        return BASELINE_COMPARISON_STATUS_DELETED
    if activity_id in plan.updated_activity_ids:
        return BASELINE_COMPARISON_STATUS_CHANGED
    return BASELINE_COMPARISON_STATUS_UNCHANGED


def _preview_changes(plan: P6BaselineUpdatePlan) -> list[dict[str, Any]]:
    baseline = {row.activity_id: row for row in plan.baseline_rows}
    current = {row.activity_id: row for row in plan.current_rows}
    proposed = {row.activity_id: row for row in plan.rows}
    result: list[dict[str, Any]] = []
    for activity_id in sorted(set(baseline) | set(current) | set(proposed)):
        fields = {
            field: {
                "baseline": _row_field(baseline.get(activity_id), field),
                "current": _row_field(current.get(activity_id), field),
                "proposed": _row_field(proposed.get(activity_id), field),
            }
            for field in sorted(plan.selection.fields)
        }
        result.append(
            {
                "activity_id": activity_id,
                "change_type": _change_type(plan, activity_id),
                "fields": fields,
            }
        )
    return result


def _counts(plan: P6BaselineUpdatePlan) -> dict[str, int]:
    return {
        "added": len(plan.added_activity_ids),
        "updated": len(plan.updated_activity_ids),
        "removed": len(plan.removed_activity_ids),
        "unchanged": len(plan.unchanged_activity_ids),
        "total": len(plan.rows),
    }


def _compare_counts(
    rows: Iterable[P6BaselineActivityComparison],
) -> dict[str, int]:
    values = tuple(rows)
    return {
        "added": sum(
            1 for row in values if row.status == BASELINE_COMPARISON_STATUS_ADDED
        ),
        "changed": sum(
            1 for row in values if row.status == BASELINE_COMPARISON_STATUS_CHANGED
        ),
        "deleted": sum(
            1 for row in values if row.status == BASELINE_COMPARISON_STATUS_DELETED
        ),
        "unchanged": sum(
            1 for row in values if row.status == BASELINE_COMPARISON_STATUS_UNCHANGED
        ),
        "total": len(values),
    }


@dataclass(frozen=True)
class P6BaselineUpdateAPI:
    """Transport boundary over the authoritative selective-update service."""

    service: P6BaselineUpdateService
    authorization_policy: AuthorizationPolicy

    def preview(
        self,
        scope: BackendScope,
        source_baseline_id: str,
        target_baseline_id: str,
        selection: P6BaselineUpdateSelection,
        *,
        expected_revision: int,
        auth_context: AuthorizationContext,
        contract_version: str = P6_BASELINE_UPDATE_API_VERSION,
    ) -> dict[str, Any]:
        _require_contract(contract_version)
        _require_scope(scope, auth_context)
        _require_permission(
            self.authorization_policy, auth_context, Permission.PROJECT_READ
        )
        _require_revision(scope, expected_revision)
        source = _require_identifier(
            source_baseline_id, "BASELINE_UPDATE_SOURCE_INVALID"
        )
        target = _require_identifier(
            target_baseline_id, "BASELINE_UPDATE_TARGET_INVALID"
        )
        if source == target:
            raise P6BaselineUpdateError("BASELINE_UPDATE_TARGET_MUST_DIFFER")
        plan = self.service.preview_from_source(scope, source, target, selection)
        return {
            "contract_version": P6_BASELINE_UPDATE_API_VERSION,
            "kind": "p6_baseline_update_preview",
            "scope": _scope_payload(scope),
            "source_baseline_id": source,
            "target_baseline_id": target,
            "selection": _selection_payload(selection),
            "counts": _counts(plan),
            "added_activity_ids": list(plan.added_activity_ids),
            "updated_activity_ids": list(plan.updated_activity_ids),
            "removed_activity_ids": list(plan.removed_activity_ids),
            "unchanged_activity_ids": list(plan.unchanged_activity_ids),
            "changes": _preview_changes(plan),
        }

    def apply(
        self,
        scope: BackendScope,
        source_baseline_id: str,
        target_baseline_id: str,
        selection: P6BaselineUpdateSelection,
        *,
        target_name: str,
        expected_revision: int,
        auth_context: AuthorizationContext,
        baseline_type: str = "USER_SELECTED",
        contract_version: str = P6_BASELINE_UPDATE_API_VERSION,
    ) -> dict[str, Any]:
        _require_contract(contract_version)
        _require_scope(scope, auth_context)
        _require_permission(
            self.authorization_policy, auth_context, Permission.PROJECT_WRITE
        )
        _require_revision(scope, expected_revision)
        source = _require_identifier(
            source_baseline_id, "BASELINE_UPDATE_SOURCE_INVALID"
        )
        target = _require_identifier(
            target_baseline_id, "BASELINE_UPDATE_TARGET_INVALID"
        )
        if source == target:
            raise P6BaselineUpdateError("BASELINE_UPDATE_TARGET_MUST_DIFFER")
        if not isinstance(target_name, str) or not target_name.strip():
            raise P6BaselineUpdateError("BASELINE_UPDATE_TARGET_NAME_INVALID")
        result = self.service.apply_from_source(
            scope,
            source,
            target,
            selection,
            target_name=target_name,
            baseline_type=baseline_type,
            expected_revision=expected_revision,
        )
        return {
            "contract_version": P6_BASELINE_UPDATE_API_VERSION,
            "kind": "p6_baseline_update_apply",
            "scope": _scope_payload(scope),
            "source_baseline_id": source,
            "baseline": _baseline_payload(result.baseline),
            "selection": _selection_payload(selection),
            "counts": _counts(result.plan),
            "added_activity_ids": list(result.plan.added_activity_ids),
            "updated_activity_ids": list(result.plan.updated_activity_ids),
            "removed_activity_ids": list(result.plan.removed_activity_ids),
            "unchanged_activity_ids": list(result.plan.unchanged_activity_ids),
        }

    def compare(
        self,
        scope: BackendScope,
        baseline_id: str,
        *,
        expected_revision: int,
        auth_context: AuthorizationContext,
        activity_ids: Iterable[str] | None = None,
        contract_version: str = P6_BASELINE_UPDATE_API_VERSION,
    ) -> dict[str, Any]:
        _require_contract(contract_version)
        _require_scope(scope, auth_context)
        _require_permission(
            self.authorization_policy, auth_context, Permission.PROJECT_READ
        )
        _require_revision(scope, expected_revision)
        identifier = _require_identifier(
            baseline_id, "BASELINE_UPDATE_SOURCE_INVALID"
        )
        rows = self.service.compare_from_source(scope, identifier)
        if activity_ids is not None:
            selected = frozenset(activity_ids)
            if not selected or any(
                not isinstance(value, str) or not value.strip()
                for value in selected
            ):
                raise P6BaselineUpdateError(
                    "BASELINE_UPDATE_ACTIVITY_IDS_INVALID"
                )
            rows = tuple(row for row in rows if row.activity_id in selected)
        return {
            "contract_version": P6_BASELINE_UPDATE_API_VERSION,
            "kind": "p6_baseline_compare",
            "scope": _scope_payload(scope),
            "baseline_id": identifier,
            "variance_convention": BASELINE_VARIANCE_CONVENTION,
            "counts": _compare_counts(rows),
            "rows": [row.to_payload() for row in rows],
        }


__all__ = [
    "BASELINE_VARIANCE_CONVENTION",
    "P6_BASELINE_UPDATE_API_VERSION",
    "P6BaselineUpdateAPI",
]
