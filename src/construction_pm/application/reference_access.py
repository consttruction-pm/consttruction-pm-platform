"""Access rules for the shared Reference Testing Workspace.

The reference dataset is one shared copy that every authenticated user may read.
It is never copied into a user account, and no project role may mutate the
source rows: reviews read, calculate and propose scenarios instead. Those rules
are enforced here, in front of the ordinary role policy, so a UI that shows an
edit control cannot change the source project.

Nothing in this module grants access by itself. It narrows the decisions of the
injected policy for the reference project ids only, which keeps the
authorization surface a single place to review.
"""

from __future__ import annotations

from typing import Iterable

from .authorization import (
    AuthorizationContext,
    AuthorizationError,
    RoleBasedAuthorizationPolicy,
)

# Roles of the Reference Testing Workspace. They are read-derived by design:
# none of them can edit source data or administer the project.
REFERENCE_WORKSPACE_ROLES: frozenset[str] = frozenset(
    {"viewer", "reviewer", "test_operator"}
)

# Permissions that change the source project. A scenario is a separate,
# revision-bound artifact and must not be implemented as an edit of these rows.
_SOURCE_MUTATION_PERMISSIONS = frozenset(
    {
        "project.write",
        "project.admin",
        "project.schedule",
    }
)


class ReferenceReadOnlyPolicy:
    """Delegate every decision, but never allow mutation of reference data."""

    def __init__(
        self,
        delegate: RoleBasedAuthorizationPolicy,
        reference_project_ids: Iterable[str],
    ) -> None:
        self._delegate = delegate
        self._reference_ids = frozenset(reference_project_ids)

    @property
    def reference_project_ids(self) -> frozenset[str]:
        return self._reference_ids

    def is_allowed(
        self, context: AuthorizationContext, permission: object
    ) -> bool:
        if (
            context.project_id in self._reference_ids
            and str(getattr(permission, "value", permission))
            in _SOURCE_MUTATION_PERMISSIONS
        ):
            return False
        return self._delegate.is_allowed(context, permission)

    def require(self, context: AuthorizationContext, permission: object) -> None:
        if not self.is_allowed(context, permission):
            value = getattr(permission, "value", permission)
            raise AuthorizationError(
                f"authorization denied for permission={value}"
            )


def reference_workspace_policy(
    delegate: RoleBasedAuthorizationPolicy,
    reference_project_ids: Iterable[str],
) -> ReferenceReadOnlyPolicy:
    return ReferenceReadOnlyPolicy(delegate, reference_project_ids)
