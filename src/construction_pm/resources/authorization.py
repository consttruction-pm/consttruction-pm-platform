from __future__ import annotations

from typing import Protocol

from .context import ProjectContext
from .errors import authorization_error


class AuthorizationPolicy(Protocol):
    """Application boundary for tenant/project mutation authorization."""

    def authorize(self, context: ProjectContext, operation: str) -> None: ...


class AllowAllAuthorizationPolicy:
    """Explicit adapter for trusted/test callers; production supplies real policy."""

    def authorize(self, context: ProjectContext, operation: str) -> None:
        context.validate()


class DenyAuthorizationPolicy:
    """Deterministic test adapter for forbidden mutations."""

    def authorize(self, context: ProjectContext, operation: str) -> None:
        raise authorization_error(
            "FORBIDDEN",
            f"Operation is not authorized: {operation}",
        )
