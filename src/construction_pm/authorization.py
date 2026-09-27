from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Protocol


class AuthorizationError(ValueError):
    """Raised when an application/API actor is not permitted to perform an action."""


@dataclass(frozen=True)
class AuthorizationContext:
    """Provider-neutral authorization input owned by the Application/API boundary."""

    tenant_id: str
    actor_id: str
    roles: FrozenSet[str] = frozenset()

    def validate(self) -> None:
        for name, value in (("tenant_id", self.tenant_id), ("actor_id", self.actor_id)):
            if not isinstance(value, str) or not value.strip():
                raise AuthorizationError(f"INVALID_AUTHORIZATION_{name.upper()}")
        if not isinstance(self.roles, frozenset) or any(
            not isinstance(role, str) or not role.strip() for role in self.roles
        ):
            raise AuthorizationError("INVALID_AUTHORIZATION_ROLES")


class AuthorizationPolicy(Protocol):
    def authorize(
        self,
        *,
        context: AuthorizationContext,
        project_id: str,
        action: str,
    ) -> None: ...


class RoleAuthorizationPolicy:
    """Deterministic application-boundary policy; no authentication provider dependency."""

    def __init__(self, permissions: dict[str, set[str]]) -> None:
        self._permissions = {role: frozenset(actions) for role, actions in permissions.items()}

    def authorize(self, *, context: AuthorizationContext, project_id: str, action: str) -> None:
        context.validate()
        if not isinstance(project_id, str) or not project_id.strip():
            raise AuthorizationError("INVALID_AUTHORIZATION_PROJECT_ID")
        if not isinstance(action, str) or not action.strip():
            raise AuthorizationError("INVALID_AUTHORIZATION_ACTION")
        if not any(action in self._permissions.get(role, frozenset()) for role in context.roles):
            raise AuthorizationError("AUTHORIZATION_FORBIDDEN")


def require_authorization(
    policy: AuthorizationPolicy,
    *,
    context: AuthorizationContext,
    project_id: str,
    action: str,
) -> None:
    """Application/use-case helper; domain calculations remain unaware of authorization."""
    policy.authorize(context=context, project_id=project_id, action=action)
