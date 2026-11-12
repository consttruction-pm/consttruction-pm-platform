"""Versioned application boundary for the project issue register."""

from __future__ import annotations

from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass
from typing import Any

from .application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)
from .backend_p0.models import BackendScope
from .p6_issue_repository import (
    P6Issue,
    P6IssueEvent,
    P6IssueRepository,
    P6IssuePersistenceError,
)

P6_ISSUE_API_VERSION = "p6-issue-api.v1"


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


def _scope_dto(scope: BackendScope) -> dict[str, Any]:
    return {
        "tenant_id": scope.tenant_id,
        "project_id": scope.project_id,
        "project_revision": scope.project_revision,
    }


def _dto(issue: P6Issue) -> dict[str, Any]:
    return {
        "contract_version": P6_ISSUE_API_VERSION,
        "kind": "p6_issue",
        "scope": _scope_dto(issue.scope),
        "issue": {
            "issue_id": issue.issue_id,
            "title": issue.title,
            "description": issue.description,
            "issue_type": issue.issue_type,
            "status": issue.status,
            "priority": issue.priority,
            "owner": issue.owner,
            "responsible_manager": issue.responsible_manager,
            "date_identified": issue.date_identified,
            "due_date": issue.due_date,
            "wbs_id": issue.wbs_id,
            "activity_id": issue.activity_id,
            "document_refs": list(issue.document_refs),
            "resolution_note": issue.resolution_note,
            "record_revision": issue.record_revision,
            "created_at": issue.created_at,
            "updated_at": issue.updated_at,
        },
    }


def _event_dto(event: P6IssueEvent) -> dict[str, Any]:
    return {
        "contract_version": P6_ISSUE_API_VERSION,
        "kind": "p6_issue_event",
        "issue_id": event.issue_id,
        "event": event.as_dict(),
    }


@dataclass(frozen=True)
class P6IssueAPI:
    """Authoritative issue operations with permission and scope enforcement."""

    repository: P6IssueRepository
    authorization_policy: AuthorizationPolicy
    transaction_manager: object | None = None

    def _transaction(self) -> AbstractContextManager[None]:
        if self.transaction_manager is None:
            return nullcontext()
        return self.transaction_manager.transaction()  # type: ignore[attr-defined,no-any-return]

    def create(
        self, issue: P6Issue, *, auth_context: AuthorizationContext, occurred_at: str
    ) -> dict[str, Any]:
        _require_scope(issue.scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_WRITE)
        with self._transaction():
            stored = self.repository.create(
                issue, actor_id=auth_context.user_id, occurred_at=occurred_at
            )
        return _dto(_subject(stored, issue))

    def get(
        self, scope: BackendScope, issue_id: str, *, auth_context: AuthorizationContext
    ) -> dict[str, Any] | None:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        stored = self.repository.get(scope, issue_id)
        return None if stored is None else _dto(stored)

    def list(
        self,
        scope: BackendScope,
        *,
        status: str | None = None,
        priority: str | None = None,
        owner: str | None = None,
        issue_type: str | None = None,
        wbs_id: str | None = None,
        activity_id: str | None = None,
        search: str | None = None,
        auth_context: AuthorizationContext,
    ) -> tuple[dict[str, Any], ...]:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        return tuple(
            _dto(item)
            for item in self.repository.list(
                scope,
                status=status,
                priority=priority,
                owner=owner,
                issue_type=issue_type,
                wbs_id=wbs_id,
                activity_id=activity_id,
                search=search,
            )
        )

    def update(
        self,
        issue: P6Issue,
        *,
        expected_revision: int,
        auth_context: AuthorizationContext,
        occurred_at: str,
    ) -> dict[str, Any]:
        _require_scope(issue.scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_WRITE)
        with self._transaction():
            stored = self.repository.update(
                issue,
                expected_revision=expected_revision,
                actor_id=auth_context.user_id,
                occurred_at=occurred_at,
            )
        return _dto(_subject(stored, issue))

    def delete(
        self,
        scope: BackendScope,
        issue_id: str,
        *,
        expected_revision: int,
        auth_context: AuthorizationContext,
        occurred_at: str,
    ) -> dict[str, Any]:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_WRITE)
        with self._transaction():
            deleted = self.repository.delete(
                scope,
                issue_id,
                expected_revision=expected_revision,
                actor_id=auth_context.user_id,
                occurred_at=occurred_at,
            )
        if not deleted:
            raise P6IssuePersistenceError("ISSUE_NOT_FOUND")
        return {
            "contract_version": P6_ISSUE_API_VERSION,
            "kind": "p6_issue_delete",
            "issue_id": issue_id,
            "deleted": True,
        }

    def add_comment(
        self,
        scope: BackendScope,
        issue_id: str,
        *,
        comment: str,
        expected_revision: int,
        auth_context: AuthorizationContext,
        occurred_at: str,
    ) -> dict[str, Any]:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_WRITE)
        with self._transaction():
            stored = self.repository.add_comment(
                scope,
                issue_id,
                comment=comment,
                expected_revision=expected_revision,
                actor_id=auth_context.user_id,
                occurred_at=occurred_at,
            )
        return _dto(stored)

    def history(
        self, scope: BackendScope, issue_id: str, *, auth_context: AuthorizationContext
    ) -> tuple[dict[str, Any], ...]:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        if self.repository.get(scope, issue_id) is None:
            raise P6IssuePersistenceError("ISSUE_NOT_FOUND")
        return tuple(_event_dto(event) for event in self.repository.history(scope, issue_id))


def _subject(stored: P6Issue, requested: P6Issue) -> P6Issue:
    """A write must never change the identity or tenant scope of the record."""

    if (
        stored.scope.tenant_id != requested.scope.tenant_id
        or stored.scope.project_id != requested.scope.project_id
        or stored.issue_id != requested.issue_id
    ):
        raise P6IssuePersistenceError("ISSUE_IDENTITY_CHANGED")
    return stored


__all__ = ["P6_ISSUE_API_VERSION", "P6IssueAPI"]
