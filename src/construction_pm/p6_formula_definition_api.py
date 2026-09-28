from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .application.authorization import AuthorizationContext, AuthorizationError, AuthorizationPolicy, Permission
from .backend_p0.models import BackendScope
from .p6_formula_audit import P6FormulaAuditEvent, new_create_event
from .p6_formula_definition_repository import (
    FormulaDefinitionCreateRequest,
    P6FormulaDefinitionApplicationService,
    PersistedP6FormulaDefinition,
)


P6_FORMULA_DEFINITION_API_VERSION = "p6-formula-definition-api.v1"


def _require_scope(scope: BackendScope, auth_context: AuthorizationContext) -> None:
    scope.validate()
    auth_context.validate()
    if scope.tenant_id != auth_context.tenant_id or scope.project_id != auth_context.project_id:
        raise AuthorizationError("CROSS_SCOPE_ACCESS")


def _require_permission(
    policy: AuthorizationPolicy,
    auth_context: AuthorizationContext,
    permission: Permission,
) -> None:
    if not policy.is_allowed(auth_context, permission):
        raise AuthorizationError(f"authorization denied for permission={permission.value}")


@dataclass(frozen=True)
class P6FormulaDefinitionAPI:
    service: P6FormulaDefinitionApplicationService
    authorization_policy: AuthorizationPolicy

    def create(
        self,
        request: FormulaDefinitionCreateRequest,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(request.scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_WRITE)
        audit_event = new_create_event(
            scope=request.scope,
            formula_id=request.formula_id,
            formula_version=request.version,
            actor_id=auth_context.user_id,
            occurred_at=datetime.now(timezone.utc),
            semantic_version=request.semantic_version,
            expression=request.expression,
        )
        return _dto(self.service.create(request, audit_event=audit_event))

    def get(
        self,
        scope: BackendScope,
        formula_id: str,
        version: str,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any] | None:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        result = self.service.read(scope, formula_id, version)
        return None if result is None else _dto(result.formula)

    def list_audit(
        self,
        scope: BackendScope,
        formula_id: str,
        *,
        auth_context: AuthorizationContext,
    ) -> tuple[dict[str, Any], ...]:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        return tuple(_audit_dto(item) for item in self.service.list_audit(scope, formula_id))

    def list_versions(
        self,
        scope: BackendScope,
        formula_id: str,
        *,
        auth_context: AuthorizationContext,
    ) -> tuple[dict[str, Any], ...]:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        result = self.service.list(scope, formula_id)
        return tuple(_dto(item) for item in result.formulas)


def _dto(record: PersistedP6FormulaDefinition) -> dict[str, Any]:
    return {
        "contract_version": P6_FORMULA_DEFINITION_API_VERSION,
        "kind": "formula_definition",
        "scope": {
            "tenant_id": record.scope.tenant_id,
            "project_id": record.scope.project_id,
            "project_revision": record.scope.project_revision,
        },
        "semantic_version": record.semantic_version,
        "semantic_reference": record.semantic_reference,
        "formula": {
            "formula_id": record.formula_id,
            "version": record.version,
            "expression": record.definition.expression,
            "result_type": record.definition.result_type.value,
            "result_unit": record.result_unit,
            "dependencies": list(record.dependencies),
            "metadata": dict(record.metadata),
        },
    }


__all__ = ["P6_FORMULA_DEFINITION_API_VERSION", "P6FormulaDefinitionAPI"]


def _audit_dto(event: P6FormulaAuditEvent) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "scope": {
            "tenant_id": event.scope.tenant_id,
            "project_id": event.scope.project_id,
            "project_revision": event.scope.project_revision,
        },
        "formula_id": event.formula_id,
        "formula_version": event.formula_version,
        "action": event.action,
        "actor_id": event.actor_id,
        "occurred_at": event.occurred_at.isoformat(),
        "semantic_version": event.semantic_version,
        "expression_sha256": event.expression_sha256,
    }


def _audit_dto(event: P6FormulaAuditEvent) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "scope": {
            "tenant_id": event.scope.tenant_id,
            "project_id": event.scope.project_id,
            "project_revision": event.scope.project_revision,
        },
        "formula_id": event.formula_id,
        "formula_version": event.formula_version,
        "action": event.action,
        "actor_id": event.actor_id,
        "occurred_at": event.occurred_at.isoformat(),
        "semantic_version": event.semantic_version,
        "expression_sha256": event.expression_sha256,
    }
