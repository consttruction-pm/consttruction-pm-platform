from __future__ import annotations

"""Versioned API boundary for cross-project baseline conversion (BAS-001)."""

from dataclasses import dataclass
from typing import Any

from .application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)
from .backend_p0.models import BackendScope
from .p6_baseline_conversion import P6BaselineConversionService
from .p6_baseline_repository import P6Baseline

P6_BASELINE_CONVERSION_API_VERSION = "p6-baseline-conversion-api.v1"


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
    if contract_version != P6_BASELINE_CONVERSION_API_VERSION:
        raise ValueError("BASELINE_CONVERSION_CONTRACT_VERSION_UNSUPPORTED")


def _require_revision(scope: BackendScope, expected_revision: int) -> None:
    if (
        isinstance(expected_revision, bool)
        or not isinstance(expected_revision, int)
        or expected_revision < 0
    ):
        raise ValueError("BASELINE_CONVERSION_REVISION_INVALID")
    if expected_revision != scope.project_revision:
        raise ValueError("BASELINE_CONVERSION_STALE_REVISION")


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


@dataclass(frozen=True)
class P6BaselineConversionAPI:
    """Transport boundary over the authoritative conversion service."""

    service: P6BaselineConversionService
    authorization_policy: AuthorizationPolicy

    def convert(
        self,
        source_scope: BackendScope,
        target_scope: BackendScope,
        *,
        source_baseline_id: str | None,
        target_baseline_id: str,
        target_name: str,
        expected_revision: int,
        auth_context: AuthorizationContext,
        source_auth_context: AuthorizationContext,
        baseline_type: str = "USER_SELECTED",
        notes: str | None = None,
        contract_version: str = P6_BASELINE_CONVERSION_API_VERSION,
    ) -> dict[str, Any]:
        _require_contract(contract_version)
        _require_scope(target_scope, auth_context)
        _require_scope(source_scope, source_auth_context)
        if source_scope.tenant_id != target_scope.tenant_id:
            raise AuthorizationError("CROSS_TENANT_ACCESS")
        _require_permission(
            self.authorization_policy,
            source_auth_context,
            Permission.PROJECT_READ,
        )
        _require_permission(
            self.authorization_policy,
            auth_context,
            Permission.PROJECT_WRITE,
        )
        _require_revision(target_scope, expected_revision)
        if source_baseline_id is not None and (
            not isinstance(source_baseline_id, str)
            or not source_baseline_id.strip()
        ):
            raise ValueError("BASELINE_CONVERSION_SOURCE_INVALID")
        if not isinstance(target_baseline_id, str) or not target_baseline_id.strip():
            raise ValueError("BASELINE_CONVERSION_TARGET_INVALID")
        if not isinstance(target_name, str) or not target_name.strip():
            raise ValueError("BASELINE_CONVERSION_TARGET_NAME_INVALID")
        result = self.service.convert(
            source_scope,
            target_scope,
            target_baseline_id=target_baseline_id,
            target_name=target_name,
            source_baseline_id=source_baseline_id,
            baseline_type=baseline_type,
            notes=notes,
        )
        return {
            "contract_version": P6_BASELINE_CONVERSION_API_VERSION,
            "kind": "p6_baseline_conversion",
            "source_scope": _scope_payload(source_scope),
            "target_scope": _scope_payload(target_scope),
            "source": {
                "kind": result.source_kind,
                "baseline_id": result.source_baseline_id,
                "project_revision": source_scope.project_revision,
            },
            "baseline": _baseline_payload(result.baseline),
            "activity_count": len(result.rows),
            "currencies": list(result.currency_totals()),
            "replayed": result.replayed,
        }


__all__ = [
    "P6_BASELINE_CONVERSION_API_VERSION",
    "P6BaselineConversionAPI",
]
