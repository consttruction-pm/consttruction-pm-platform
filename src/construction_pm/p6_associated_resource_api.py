"""V26 Users-page Associated Resource API."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .application.authorization import AuthorizationContext, AuthorizationError
from .p6_associated_resource_repository import (
    P6AssociatedResource,
    P6AssociatedResourceRepository,
)

P6_ASSOCIATED_RESOURCE_API_VERSION = "p6-associated-resource-api.v1"
_ASSOCIATED_RESOURCE_ADMIN_PRIVILEGE = "add_edit_delete_users"


def _require_admin(policy: Any, context: AuthorizationContext) -> None:
    checker = getattr(policy, "allows_global_privilege", None)
    if not callable(checker) or not checker(context, _ASSOCIATED_RESOURCE_ADMIN_PRIVILEGE):
        raise AuthorizationError("ASSOCIATED_RESOURCE_ADMIN_NOT_AUTHORIZED")


def _dto(item: P6AssociatedResource) -> dict[str, Any]:
    return {
        "contract_version": P6_ASSOCIATED_RESOURCE_API_VERSION,
        "kind": "p6_associated_resource",
        "association": {
            "tenant_id": item.tenant_id,
            "user_id": item.user_id,
            "resource_id": item.resource_id,
            "revision": item.revision,
            "updated_by": item.updated_by,
            "updated_at": item.updated_at.isoformat(),
        },
    }


@dataclass(frozen=True)
class P6AssociatedResourceAPI:
    repository: P6AssociatedResourceRepository
    authorization_policy: Any
    clock: Any = lambda: datetime.now(timezone.utc)

    def list_resources(self, *, auth_context: AuthorizationContext) -> dict[str, Any]:
        auth_context.validate()
        _require_admin(self.authorization_policy, auth_context)
        return {
            "contract_version": P6_ASSOCIATED_RESOURCE_API_VERSION,
            "resources": list(self.repository.list_resources(auth_context.tenant_id)),
        }

    def get(self, user_id: str, *, auth_context: AuthorizationContext) -> dict[str, Any] | None:
        auth_context.validate()
        _require_admin(self.authorization_policy, auth_context)
        item = self.repository.get_for_user(auth_context.tenant_id, user_id)
        return None if item is None else _dto(item)

    def assign(
        self, user_id: str, resource_id: str, *, expected_revision: int | None = None,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        auth_context.validate()
        _require_admin(self.authorization_policy, auth_context)
        current = self.repository.get_for_user(auth_context.tenant_id, user_id)
        if current is None:
            revision = 1
            expected = expected_revision
        else:
            if expected_revision is None or expected_revision != current.revision:
                raise ValueError("ASSOCIATED_RESOURCE_REVISION_CONFLICT")
            if current.resource_id == resource_id:
                return _dto(current)
            revision = current.revision + 1
            expected = expected_revision
        item = P6AssociatedResource(
            auth_context.tenant_id, user_id, resource_id, revision,
            auth_context.user_id, self.clock(),
        )
        return _dto(self.repository.assign(item, expected_revision=expected))

    def unassign(
        self, user_id: str, *, expected_revision: int,
        auth_context: AuthorizationContext,
    ) -> None:
        auth_context.validate()
        _require_admin(self.authorization_policy, auth_context)
        self.repository.unassign(
            auth_context.tenant_id, user_id, actor_id=auth_context.user_id,
            expected_revision=expected_revision, occurred_at=self.clock(),
        )


__all__ = ["P6_ASSOCIATED_RESOURCE_API_VERSION", "P6AssociatedResourceAPI"]
