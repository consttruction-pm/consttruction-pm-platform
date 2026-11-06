from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from .application.authorization import AuthorizationContext, AuthorizationError, AuthorizationPolicy, Permission
from .backend_p0.models import BackendScope
from .p6_activity_filter_repository import (
    P6ActivityFilterDefinition,
    P6ActivityFilterRepository,
    P6ActivityFilterPersistenceError,
)


P6_ACTIVITY_FILTER_API_VERSION = "p6-activity-filter-api.v1"


def _require_scope(scope: BackendScope, auth: AuthorizationContext) -> None:
    scope.validate()
    auth.validate()
    if scope.tenant_id != auth.tenant_id or scope.project_id != auth.project_id:
        raise AuthorizationError("CROSS_SCOPE_ACCESS")


def _dto(record: P6ActivityFilterDefinition) -> dict[str, Any]:
    return {
        "contract_version": P6_ACTIVITY_FILTER_API_VERSION,
        "kind": "activity_filter",
        "scope": {
            "tenant_id": record.scope.tenant_id,
            "project_id": record.scope.project_id,
            "project_revision": record.scope.project_revision,
        },
        "filter": {
            "filter_id": record.filter_id,
            "name": record.name,
            "category": record.category,
            "owner_id": record.owner_id,
            "revision": record.revision,
            "criteria": [dict(item) for item in record.criteria],
            "match_mode": record.match_mode,
        },
    }


@dataclass(frozen=True)
class P6ActivityFilterAPI:
    repository: P6ActivityFilterRepository
    authorization_policy: AuthorizationPolicy
    transaction_manager: object | None = None

    def _transaction(self):
        manager = self.transaction_manager
        return manager.transaction() if manager is not None else _NullTransaction()

    def list(self, scope: BackendScope, *, auth_context: AuthorizationContext) -> dict[str, Any]:
        _require_scope(scope, auth_context)
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_READ):
            raise AuthorizationError("authorization denied")
        with self._transaction():
            filters = self.repository.list(scope)
        return {
            "contract_version": P6_ACTIVITY_FILTER_API_VERSION,
            "kind": "activity_filter_register",
            "scope": {
                "tenant_id": scope.tenant_id,
                "project_id": scope.project_id,
                "project_revision": scope.project_revision,
            },
            "filters": [_dto(item)["filter"] for item in filters],
        }

    def save(
        self,
        scope: BackendScope,
        *,
        filter_id: str,
        name: str,
        category: str,
        criteria: tuple[Mapping[str, Any], ...],
        match_mode: str,
        expected_revision: int,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(scope, auth_context)
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_WRITE):
            raise AuthorizationError("authorization denied")
        with self._transaction():
            current = self.repository.get(scope, filter_id)
            if current is not None:
                if current.owner_id != auth_context.user_id and not ({"project_admin", "admin"} & set(auth_context.roles)):
                    raise AuthorizationError("ACTIVITY_FILTER_OWNER_REQUIRED")
                owner_id = current.owner_id
                revision = current.revision + 1
            else:
                if expected_revision != 0:
                    raise P6ActivityFilterPersistenceError("REVISION_CONFLICT")
                owner_id = auth_context.user_id
                revision = 1
            record = P6ActivityFilterDefinition(
                scope=scope,
                filter_id=filter_id,
                name=name,
                category=category,
                owner_id=owner_id,
                revision=revision,
                criteria=tuple(dict(item) for item in criteria),
                match_mode=match_mode,
            )
            saved = self.repository.save(record, expected_revision=expected_revision)
        return _dto(saved)

    def delete(
        self,
        scope: BackendScope,
        filter_id: str,
        *,
        expected_revision: int,
        auth_context: AuthorizationContext,
    ) -> None:
        _require_scope(scope, auth_context)
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_WRITE):
            raise AuthorizationError("authorization denied")
        with self._transaction():
            current = self.repository.get(scope, filter_id)
            if current is None:
                raise P6ActivityFilterPersistenceError("ACTIVITY_FILTER_NOT_FOUND")
            if current.owner_id != auth_context.user_id and not ({"project_admin", "admin"} & set(auth_context.roles)):
                raise AuthorizationError("ACTIVITY_FILTER_OWNER_REQUIRED")
            self.repository.delete(scope, filter_id, expected_revision=expected_revision)


class _NullTransaction:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


__all__ = ["P6_ACTIVITY_FILTER_API_VERSION", "P6ActivityFilterAPI"]
