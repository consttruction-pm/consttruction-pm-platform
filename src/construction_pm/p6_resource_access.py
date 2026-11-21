"""Shared enforcement of V26 global Resource Access on resource-bearing APIs."""
from __future__ import annotations

from typing import Any

from .application.authorization import AuthorizationContext, AuthorizationError
from .backend_p0.models import BackendScope


def resource_is_accessible(
    policy: Any,
    repository: Any | None,
    scope: BackendScope,
    resource_id: str,
    auth_context: AuthorizationContext,
) -> bool:
    """Resolve authoritative self-to-root ancestry and apply persisted P6 policy.

    Legacy policies without the V26 resource gate retain their established
    behavior. Once the persisted P6 policy is installed, a missing resource
    repository is a configuration error and fails closed.
    """
    checker = getattr(policy, "can_access_resource", None)
    if not callable(checker):
        return True
    if repository is None:
        return False
    items = repository.list(scope.tenant_id, scope.project_id, scope.project_revision)
    by_id = {item.resource_id: item for item in items}
    resource = by_id.get(resource_id)
    if resource is None:
        return False
    ancestry = [resource_id]
    seen = {resource_id}
    cursor = resource.parent_resource_id
    while cursor is not None:
        if cursor in seen or cursor not in by_id:
            return False
        seen.add(cursor)
        ancestry.append(cursor)
        cursor = by_id[cursor].parent_resource_id
    try:
        return bool(checker(auth_context, resource_id, tuple(ancestry)))
    except (TypeError, ValueError, AttributeError):
        return False


def require_resource_access(
    policy: Any,
    repository: Any | None,
    scope: BackendScope,
    resource_id: str,
    auth_context: AuthorizationContext,
) -> None:
    if not resource_is_accessible(policy, repository, scope, resource_id, auth_context):
        raise AuthorizationError("RESOURCE_ACCESS_DENIED")
