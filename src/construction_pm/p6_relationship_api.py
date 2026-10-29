from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .application.authorization import AuthorizationContext, AuthorizationError, AuthorizationPolicy, Permission
from .activity_master_repository import ActivityMasterRepository
from .backend_p0.models import BackendScope
from .relationship_master_repository import (
    RelationshipMaster,
    RelationshipMasterRepository,
    RelationshipPersistenceError,
)


P6_RELATIONSHIP_API_VERSION = "p6-relationship-api.v1"


def _require_scope(scope: BackendScope, auth_context: AuthorizationContext) -> None:
    scope.validate()
    auth_context.validate()
    if scope.tenant_id != auth_context.tenant_id or scope.project_id != auth_context.project_id:
        raise AuthorizationError("CROSS_SCOPE_ACCESS")


def _require_permission(policy: AuthorizationPolicy, auth_context: AuthorizationContext, permission: Permission) -> None:
    if not policy.is_allowed(auth_context, permission):
        raise AuthorizationError(f"authorization denied for permission={permission.value}")


def _scope_dto(scope: BackendScope) -> dict[str, Any]:
    return {"tenant_id": scope.tenant_id, "project_id": scope.project_id, "project_revision": scope.project_revision}


def _dto(relationship: RelationshipMaster) -> dict[str, Any]:
    return {
        "contract_version": P6_RELATIONSHIP_API_VERSION,
        "kind": "p6_relationship",
        "scope": _scope_dto(relationship.scope),
        "relationship": {
            "relationship_id": relationship.relationship_id,
            "predecessor_id": relationship.predecessor_id,
            "successor_id": relationship.successor_id,
            "relationship_type": relationship.relationship_type.value,
            "lag_value": str(relationship.lag_value),
            "lag_unit": relationship.lag_unit.value,
            "record_revision": relationship.record_revision,
        },
    }


@dataclass(frozen=True)
class P6RelationshipAPI:
    """Authenticated application boundary over authoritative relationship persistence."""

    repository: RelationshipMasterRepository
    authorization_policy: AuthorizationPolicy
    activity_repository: ActivityMasterRepository | None = None

    def create(self, relationship: RelationshipMaster, *, auth_context: AuthorizationContext, expected_revision: int | None = None) -> dict[str, Any]:
        _require_scope(relationship.scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_WRITE)
        self._validate_network(relationship, previous_id=None)
        return _dto(self.repository.save(relationship, expected_revision=expected_revision))

    def update(self, relationship: RelationshipMaster, *, expected_revision: int, auth_context: AuthorizationContext) -> dict[str, Any]:
        _require_scope(relationship.scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_WRITE)
        self._validate_network(relationship, previous_id=relationship.relationship_id)
        return _dto(self.repository.save(relationship, expected_revision=expected_revision))

    def _validate_network(
        self,
        relationship: RelationshipMaster,
        *,
        previous_id: str | None,
    ) -> None:
        """Reject invalid endpoints, duplicate logic links and cycles before save.

        The scheduling core still detects cycles defensively; this boundary
        prevents storing a network that can never be scheduled.
        """
        scope = relationship.scope
        if self.activity_repository is not None:
            for activity_id in (relationship.predecessor_id, relationship.successor_id):
                if self.activity_repository.get(scope, activity_id) is None:
                    raise RelationshipPersistenceError("ACTIVITY_NOT_FOUND_OR_SCOPE_MISMATCH")
        existing = self.repository.list(scope)
        edges: list[tuple[str, str]] = []
        for item in existing:
            if previous_id is not None and item.relationship_id == previous_id:
                continue
            if (
                item.predecessor_id == relationship.predecessor_id
                and item.successor_id == relationship.successor_id
                and item.relationship_type is relationship.relationship_type
            ):
                raise RelationshipPersistenceError("DUPLICATE_RELATIONSHIP")
            edges.append((item.predecessor_id, item.successor_id))
        edges.append((relationship.predecessor_id, relationship.successor_id))
        if _has_cycle(edges):
            raise RelationshipPersistenceError("RELATIONSHIP_CYCLE")

    def get(self, scope: BackendScope, relationship_id: str, *, auth_context: AuthorizationContext) -> dict[str, Any] | None:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        result = self.repository.get(scope, relationship_id)
        return None if result is None else _dto(result)

    def list(self, scope: BackendScope, *, auth_context: AuthorizationContext) -> tuple[dict[str, Any], ...]:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        return tuple(_dto(item) for item in self.repository.list(scope))

    def delete(self, scope: BackendScope, relationship_id: str, *, expected_revision: int, auth_context: AuthorizationContext) -> dict[str, Any]:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_WRITE)
        deleted = self.repository.delete(scope, relationship_id, expected_revision=expected_revision)
        return {
            "contract_version": P6_RELATIONSHIP_API_VERSION,
            "kind": "p6_relationship_delete",
            "scope": _scope_dto(scope),
            "relationship_id": relationship_id,
            "deleted": deleted,
        }


__all__ = ["P6_RELATIONSHIP_API_VERSION", "P6RelationshipAPI"]


def _has_cycle(edges: list[tuple[str, str]]) -> bool:
    """Depth-first cycle detection over the directed predecessor→successor graph."""
    adjacency: dict[str, list[str]] = {}
    for predecessor, successor in edges:
        adjacency.setdefault(predecessor, []).append(successor)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for neighbour in adjacency.get(node, ()):
            if visit(neighbour):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in list(adjacency))
