"""Durable project closeout and reopening over stored facts.

A project is closed once, by an administrator, only when its stored issue
register has no open or in-progress items. Closing and reopening are audited
lifecycle operations with their own optimistic revision: the closeout record is
never rewritten in place without a revision guard, and its event table is
append-only. The closeout state is deliberately separate from the V26 General
tab status field, so a status edit cannot silently reopen a finished project and
a closeout does not fabricate a status value.

No scheduling, cost or issue fact is recalculated here. The only derived value
is the count of open issues, read from the same ``p6_issue`` rows the issue API
writes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .api_errors import (
    APIError,
    authorization_error,
    conflict_error,
    validation_error,
)
from .application.authorization import (
    AuthorizationContext,
    AuthorizationPolicy,
    Permission,
)
from .backend_p0.models import BackendScope
from .p6_issue_repository import ISSUE_OPEN_STATUSES

CLOSEOUT_CONTRACT_VERSION = "project-closeout.v1"
CLOSEOUT_STATES = frozenset({"open", "closed"})
CLOSEOUT_ACTIONS = frozenset({"closed", "reopened"})


class ProjectCloseoutError(ValueError):
    """A closeout request violates the stored contract."""


class ProjectCloseoutRevisionConflict(ProjectCloseoutError):
    pass


class ProjectCloseoutBlocked(ProjectCloseoutError):
    pass


class ProjectCloseoutAuthorizationError(ProjectCloseoutError):
    pass


@dataclass(frozen=True)
class CloseoutEvent:
    """Append-only record of one close or reopen action."""

    tenant_id: str
    project_id: str
    event_id: str
    record_revision: int
    action: str
    actor_id: str
    occurred_at: datetime
    note: str = ""
    open_issue_count: int = 0

    def as_dict(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "record_revision": self.record_revision,
            "action": self.action,
            "actor_id": self.actor_id,
            "occurred_at": self.occurred_at.isoformat(),
            "note": self.note,
            "open_issue_count": self.open_issue_count,
        }


@dataclass(frozen=True)
class ProjectCloseout:
    """The current closeout state of one project."""

    tenant_id: str
    project_id: str
    state: str = "open"
    record_revision: int = 0
    closed_at: datetime | None = None
    closed_by: str = ""
    note: str = ""
    open_issue_count: int = 0
    updated_at: datetime | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "project_id": self.project_id,
            "state": self.state,
            "record_revision": self.record_revision,
            "closed_at": None if self.closed_at is None else self.closed_at.isoformat(),
            "closed_by": self.closed_by,
            "note": self.note,
            "open_issue_count": self.open_issue_count,
            "updated_at": (
                None if self.updated_at is None else self.updated_at.isoformat()
            ),
        }


class PostgresProjectCloseoutStore:
    """PostgreSQL closeout record and append-only event log.

    The store owns no transaction. The service opens one, so a state change and
    its event become visible together or not at all.
    """

    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS project_closeout (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                state TEXT NOT NULL,
                record_revision INTEGER NOT NULL,
                closed_at TEXT,
                closed_by TEXT NOT NULL DEFAULT '',
                note TEXT NOT NULL DEFAULT '',
                open_issue_count INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id)
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS project_closeout_event (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                event_id TEXT NOT NULL,
                record_revision INTEGER NOT NULL,
                action TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                open_issue_count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (tenant_id, project_id, event_id)
            )"""
        )
        self.connection.execute(
            """CREATE INDEX IF NOT EXISTS project_closeout_event_scope
               ON project_closeout_event
                  (tenant_id, project_id, record_revision)"""
        )

    def get(self, tenant_id: str, project_id: str) -> ProjectCloseout | None:
        row = self.connection.execute(
            """SELECT state, record_revision, closed_at, closed_by, note,
                      open_issue_count, updated_at
               FROM project_closeout
               WHERE tenant_id = %s AND project_id = %s""",
            (tenant_id, project_id),
        ).fetchone()
        if row is None:
            return None
        return ProjectCloseout(
            tenant_id=tenant_id,
            project_id=project_id,
            state=str(row[0]),
            record_revision=int(row[1]),
            closed_at=None if row[2] is None else datetime.fromisoformat(str(row[2])),
            closed_by=str(row[3]),
            note=str(row[4]),
            open_issue_count=int(row[5]),
            updated_at=None if row[6] is None else datetime.fromisoformat(str(row[6])),
        )

    def history(
        self, tenant_id: str, project_id: str
    ) -> tuple[CloseoutEvent, ...]:
        rows = self.connection.execute(
            """SELECT event_id, record_revision, action, actor_id, occurred_at,
                      note, open_issue_count
               FROM project_closeout_event
               WHERE tenant_id = %s AND project_id = %s
               ORDER BY record_revision""",
            (tenant_id, project_id),
        ).fetchall()
        return tuple(
            CloseoutEvent(
                tenant_id=tenant_id,
                project_id=project_id,
                event_id=str(row[0]),
                record_revision=int(row[1]),
                action=str(row[2]),
                actor_id=str(row[3]),
                occurred_at=datetime.fromisoformat(str(row[4])),
                note=str(row[5]),
                open_issue_count=int(row[6]),
            )
            for row in rows
        )

    def transition(
        self,
        *,
        expected_revision: int,
        state: ProjectCloseout,
        event: CloseoutEvent,
    ) -> ProjectCloseout:
        """Write one guarded state change and its event.

        Revision 0 means "no row exists yet"; the insert is the compare-and-set.
        Every later change is a conditional update on ``record_revision``, so a
        competing closer cannot overwrite the accepted decision.
        """

        if expected_revision == 0:
            try:
                cursor = self.connection.execute(
                    """INSERT INTO project_closeout
                       (tenant_id, project_id, state, record_revision, closed_at,
                        closed_by, note, open_issue_count, updated_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (tenant_id, project_id) DO NOTHING""",
                    (
                        state.tenant_id,
                        state.project_id,
                        state.state,
                        state.record_revision,
                        None if state.closed_at is None else state.closed_at.isoformat(),
                        state.closed_by,
                        state.note,
                        state.open_issue_count,
                        state.updated_at.isoformat() if state.updated_at else "",
                    ),
                )
            except Exception as exc:  # noqa: BLE001 - unique race is a conflict
                raise ProjectCloseoutRevisionConflict(
                    "CLOSEOUT_REVISION_CONFLICT"
                ) from exc
            if getattr(cursor, "rowcount", 0) != 1:
                raise ProjectCloseoutRevisionConflict("CLOSEOUT_REVISION_CONFLICT")
        else:
            cursor = self.connection.execute(
                """UPDATE project_closeout
                   SET state = %s, record_revision = %s, closed_at = %s,
                       closed_by = %s, note = %s, open_issue_count = %s,
                       updated_at = %s
                   WHERE tenant_id = %s AND project_id = %s
                     AND record_revision = %s""",
                (
                    state.state,
                    state.record_revision,
                    None if state.closed_at is None else state.closed_at.isoformat(),
                    state.closed_by,
                    state.note,
                    state.open_issue_count,
                    state.updated_at.isoformat() if state.updated_at else "",
                    state.tenant_id,
                    state.project_id,
                    expected_revision,
                ),
            )
            if getattr(cursor, "rowcount", 0) != 1:
                raise ProjectCloseoutRevisionConflict("CLOSEOUT_REVISION_CONFLICT")
        self.connection.execute(
            """INSERT INTO project_closeout_event
               (tenant_id, project_id, event_id, record_revision, action,
                actor_id, occurred_at, note, open_issue_count)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                event.tenant_id,
                event.project_id,
                event.event_id,
                event.record_revision,
                event.action,
                event.actor_id,
                event.occurred_at.isoformat(),
                event.note,
                event.open_issue_count,
            ),
        )
        stored = self.get(state.tenant_id, state.project_id)
        if stored is None:
            raise ProjectCloseoutError("CLOSEOUT_WRITE_LOST")
        return stored


@dataclass(frozen=True)
class ProjectCloseoutService:
    store: Any
    issue_repository: Any
    authorization_policy: AuthorizationPolicy
    transaction_manager: object

    # -- reads ------------------------------------------------------------
    def read(
        self,
        *,
        tenant_id: str,
        project_id: str,
        context: AuthorizationContext,
    ) -> ProjectCloseout:
        self._check(context, tenant_id, project_id, Permission.PROJECT_READ)
        return self._current(tenant_id, project_id)

    def history(
        self,
        *,
        tenant_id: str,
        project_id: str,
        context: AuthorizationContext,
    ) -> tuple[CloseoutEvent, ...]:
        self._check(context, tenant_id, project_id, Permission.PROJECT_READ)
        return self.store.history(tenant_id, project_id)

    # -- writes -----------------------------------------------------------
    def close(
        self,
        *,
        tenant_id: str,
        project_id: str,
        project_revision: int,
        expected_revision: int,
        note: str,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> ProjectCloseout:
        self._authorize_write(context, tenant_id, project_id, actor_id)
        occurred_at = _aware(occurred_at)
        with self._transaction():
            current = self._current(tenant_id, project_id)
            if current.state == "closed":
                return current
            if current.record_revision != expected_revision:
                raise ProjectCloseoutRevisionConflict("CLOSEOUT_REVISION_CONFLICT")
            open_issues = self._open_issue_count(
                tenant_id, project_id, project_revision
            )
            if open_issues:
                raise ProjectCloseoutBlocked(
                    f"CLOSEOUT_OPEN_ISSUES:{open_issues}"
                )
            revision = current.record_revision + 1
            return self.store.transition(
                expected_revision=current.record_revision,
                state=ProjectCloseout(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    state="closed",
                    record_revision=revision,
                    closed_at=occurred_at,
                    closed_by=actor_id,
                    note=_note(note),
                    open_issue_count=0,
                    updated_at=occurred_at,
                ),
                event=CloseoutEvent(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    event_id=f"closed-{revision}",
                    record_revision=revision,
                    action="closed",
                    actor_id=actor_id,
                    occurred_at=occurred_at,
                    note=_note(note),
                    open_issue_count=0,
                ),
            )

    def reopen(
        self,
        *,
        tenant_id: str,
        project_id: str,
        project_revision: int,
        expected_revision: int,
        note: str,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> ProjectCloseout:
        self._authorize_write(context, tenant_id, project_id, actor_id)
        occurred_at = _aware(occurred_at)
        with self._transaction():
            current = self._current(tenant_id, project_id)
            if current.state == "open":
                return current
            if current.record_revision != expected_revision:
                raise ProjectCloseoutRevisionConflict("CLOSEOUT_REVISION_CONFLICT")
            open_issues = self._open_issue_count(
                tenant_id, project_id, project_revision
            )
            revision = current.record_revision + 1
            return self.store.transition(
                expected_revision=current.record_revision,
                state=ProjectCloseout(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    state="open",
                    record_revision=revision,
                    closed_at=None,
                    closed_by="",
                    note=_note(note),
                    open_issue_count=open_issues,
                    updated_at=occurred_at,
                ),
                event=CloseoutEvent(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    event_id=f"reopened-{revision}",
                    record_revision=revision,
                    action="reopened",
                    actor_id=actor_id,
                    occurred_at=occurred_at,
                    note=_note(note),
                    open_issue_count=open_issues,
                ),
            )

    # -- helpers ----------------------------------------------------------
    def _current(self, tenant_id: str, project_id: str) -> ProjectCloseout:
        stored = self.store.get(tenant_id, project_id)
        if stored is not None:
            return stored
        return ProjectCloseout(tenant_id=tenant_id, project_id=project_id)

    def _open_issue_count(
        self, tenant_id: str, project_id: str, project_revision: int
    ) -> int:
        scope = BackendScope(tenant_id, project_id, project_revision)
        issues = self.issue_repository.list(scope)
        return sum(1 for item in issues if item.status in ISSUE_OPEN_STATUSES)

    def _transaction(self):
        return self.transaction_manager.transaction()

    def _check(
        self,
        context: AuthorizationContext,
        tenant_id: str,
        project_id: str,
        permission: Permission,
    ) -> None:
        if tenant_id != context.tenant_id or project_id != context.project_id:
            raise ProjectCloseoutAuthorizationError("CLOSEOUT_CROSS_SCOPE_ACCESS")
        if not self.authorization_policy.is_allowed(context, permission):
            raise ProjectCloseoutAuthorizationError("CLOSEOUT_PERMISSION_DENIED")

    def _authorize_write(
        self,
        context: AuthorizationContext,
        tenant_id: str,
        project_id: str,
        actor_id: str,
    ) -> None:
        if actor_id != context.user_id:
            raise ProjectCloseoutAuthorizationError("CLOSEOUT_ACTOR_MISMATCH")
        self._check(context, tenant_id, project_id, Permission.PROJECT_ADMIN)

    @staticmethod
    def error_dto(exc: Exception) -> APIError:
        message = str(exc) or "CLOSEOUT_REQUEST_INVALID"
        if isinstance(exc, ProjectCloseoutRevisionConflict):
            return conflict_error("CLOSEOUT_REVISION_CONFLICT", message)
        if isinstance(exc, ProjectCloseoutBlocked):
            return conflict_error(message, message)
        if isinstance(exc, ProjectCloseoutAuthorizationError):
            return authorization_error(message, message)
        if isinstance(exc, ProjectCloseoutError):
            return validation_error(message, message)
        if isinstance(exc, ValueError):
            return validation_error(message, message)
        return validation_error(
            "CLOSEOUT_INTERNAL_ERROR", "Closeout request could not be processed"
        )


@dataclass(frozen=True)
class ProjectCloseoutAPI:
    """Thin transport boundary over the closeout service."""

    service: ProjectCloseoutService

    def read(
        self,
        *,
        tenant_id: str,
        project_id: str,
        context: AuthorizationContext,
    ) -> dict[str, Any]:
        try:
            return _state(
                self.service.read(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    context=context,
                )
            )
        except Exception as exc:  # noqa: BLE001 - bounded API boundary
            return _error(self.service.error_dto(exc))

    def history(
        self,
        *,
        tenant_id: str,
        project_id: str,
        context: AuthorizationContext,
    ) -> dict[str, Any]:
        try:
            return {
                "contract_version": CLOSEOUT_CONTRACT_VERSION,
                "project_id": project_id,
                "events": [
                    _event(item)
                    for item in self.service.history(
                        tenant_id=tenant_id,
                        project_id=project_id,
                        context=context,
                    )
                ],
            }
        except Exception as exc:  # noqa: BLE001 - bounded API boundary
            return _error(self.service.error_dto(exc))

    def close(
        self,
        *,
        tenant_id: str,
        project_id: str,
        project_revision: int,
        expected_revision: int,
        note: str,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> dict[str, Any]:
        try:
            return _state(
                self.service.close(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    project_revision=project_revision,
                    expected_revision=expected_revision,
                    note=note,
                    context=context,
                    actor_id=actor_id,
                    occurred_at=occurred_at,
                )
            )
        except Exception as exc:  # noqa: BLE001 - bounded API boundary
            return _error(self.service.error_dto(exc))

    def reopen(
        self,
        *,
        tenant_id: str,
        project_id: str,
        project_revision: int,
        expected_revision: int,
        note: str,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> dict[str, Any]:
        try:
            return _state(
                self.service.reopen(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    project_revision=project_revision,
                    expected_revision=expected_revision,
                    note=note,
                    context=context,
                    actor_id=actor_id,
                    occurred_at=occurred_at,
                )
            )
        except Exception as exc:  # noqa: BLE001 - bounded API boundary
            return _error(self.service.error_dto(exc))


def _state(closeout: ProjectCloseout) -> dict[str, Any]:
    return {
        "contract_version": CLOSEOUT_CONTRACT_VERSION,
        "closeout": closeout.as_dict(),
    }


def _event(event: CloseoutEvent) -> dict[str, Any]:
    return {"contract_version": CLOSEOUT_CONTRACT_VERSION, **event.as_dict()}


def _error(error: APIError) -> dict[str, Any]:
    error.validate()
    return {
        "contract_version": CLOSEOUT_CONTRACT_VERSION,
        "category": error.category.value,
        "code": error.code,
        "message": error.message,
        "retryable": error.retryable,
    }


def _note(value: object) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ProjectCloseoutError("CLOSEOUT_NOTE_INVALID")
    return value.strip()[:2000]


def _aware(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ProjectCloseoutError("CLOSEOUT_OCCURRED_AT_INVALID")
    return value


__all__ = [
    "CLOSEOUT_ACTIONS",
    "CLOSEOUT_CONTRACT_VERSION",
    "CLOSEOUT_STATES",
    "CloseoutEvent",
    "PostgresProjectCloseoutStore",
    "ProjectCloseout",
    "ProjectCloseoutAPI",
    "ProjectCloseoutAuthorizationError",
    "ProjectCloseoutBlocked",
    "ProjectCloseoutError",
    "ProjectCloseoutRevisionConflict",
    "ProjectCloseoutService",
]
