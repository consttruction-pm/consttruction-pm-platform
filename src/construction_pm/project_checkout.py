"""Exclusive project checkout enforcement for project-scoped write boundaries.

A project can be checked out by at most one user. While another user holds the
lease, every project write — schedule data, WBS, relationships, cost structure
and stored defaults — must be rejected before the repository is asked to
mutate anything.
"""

from __future__ import annotations

from typing import Protocol

from .application.authorization import AuthorizationContext
from .backend_p0.models import BackendScope


PROJECT_CHECKED_OUT_BY_OTHER = "PROJECT_CHECKED_OUT_BY_OTHER"


class ProjectCheckoutLease(Protocol):
    """Read the exclusive checkout holder for one project scope, if any."""

    def checked_out_by(self, scope: BackendScope) -> str | None: ...


class ProjectCheckoutConflict(ValueError):
    """A write was attempted while another user holds the project checkout."""

    code = PROJECT_CHECKED_OUT_BY_OTHER

    def __init__(self, holder: str = "") -> None:
        super().__init__(PROJECT_CHECKED_OUT_BY_OTHER)
        self.holder = holder


def require_project_write_ownership(
    lease: ProjectCheckoutLease | None,
    scope: BackendScope,
    auth_context: AuthorizationContext,
) -> None:
    """Reject a write when the project is checked out by a different user.

    Called immediately before a repository write, so a conflict never leaves a
    partial mutation behind. ``lease`` is optional to keep read-only and test
    compositions unchanged, but production and preview always supply it.
    """

    if lease is None:
        return
    holder = lease.checked_out_by(scope)
    if holder is not None and holder != auth_context.user_id:
        raise ProjectCheckoutConflict(holder)


__all__ = [
    "PROJECT_CHECKED_OUT_BY_OTHER",
    "ProjectCheckoutConflict",
    "ProjectCheckoutLease",
    "require_project_write_ownership",
]
