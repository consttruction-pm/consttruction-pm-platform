from __future__ import annotations

"""Baseline roles assigned to the live project summary fields (BAS-001).

A baseline snapshot identity is immutable and lives in ``p6_baseline``. The
role that the project summary uses for comparison is a *separate* assignment:
the same baseline can be created once and later promoted to the primary or
secondary comparison role without rewriting its snapshot. This module owns
that separation, its revision guard, and an append-only audit history.

Roles are the P6 summary slots: ``PROJECT`` (the project summary baseline)
plus ``PRIMARY``, ``SECONDARY`` and ``TERTIARY`` comparison roles. A role slot
holds at most one baseline. Replacing a slot requires the caller to opt in
explicitly so an accidental overwrite fails closed.
"""

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Iterable, Protocol

from .backend_p0.models import BackendScope, MAX_SAFE_REVISION
from .p6_baseline_activity_repository import P6BaselineActivityRepository
from .p6_baseline_repository import (
    P6Baseline,
    P6BaselinePersistenceError,
    P6BaselineRepository,
)

BASELINE_ROLE_PROJECT = "PROJECT"
BASELINE_ROLE_PRIMARY = "PRIMARY"
BASELINE_ROLE_SECONDARY = "SECONDARY"
BASELINE_ROLE_TERTIARY = "TERTIARY"
BASELINE_ROLES = (
    BASELINE_ROLE_PROJECT,
    BASELINE_ROLE_PRIMARY,
    BASELINE_ROLE_SECONDARY,
    BASELINE_ROLE_TERTIARY,
)

BASELINE_ASSIGNMENT_ACTION_ASSIGN = "ASSIGN"
BASELINE_ASSIGNMENT_ACTION_REASSIGN = "REASSIGN"


class P6BaselineAssignmentError(ValueError):
    """Raised when a baseline summary-role assignment is invalid or conflicts."""


def require_baseline_role(role: object) -> str:
    if not isinstance(role, str) or role not in BASELINE_ROLES:
        raise P6BaselineAssignmentError("INVALID_BASELINE_ROLE")
    return role


def _identifier(value: object, code: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise P6BaselineAssignmentError(code)
    return value


@dataclass(frozen=True)
class P6BaselineRoleAssignment:
    """One live summary slot pointing at one immutable baseline identity."""

    scope: BackendScope
    role: str
    baseline_id: str
    assigned_at: str
    assigned_by: str
    previous_baseline_id: str | None = None

    def validate(self) -> None:
        self.scope.validate()
        if not 0 <= self.scope.project_revision <= MAX_SAFE_REVISION:
            raise P6BaselineAssignmentError("INVALID_PROJECT_REVISION")
        require_baseline_role(self.role)
        _identifier(self.baseline_id, "INVALID_BASELINE_ID")
        _identifier(self.assigned_at, "INVALID_ASSIGNED_AT")
        _identifier(self.assigned_by, "INVALID_ASSIGNED_BY")
        if self.previous_baseline_id is not None:
            _identifier(self.previous_baseline_id, "INVALID_PREVIOUS_BASELINE_ID")

    def to_payload(self) -> dict[str, object]:
        return {
            "role": self.role,
            "baseline_id": self.baseline_id,
            "assigned_at": self.assigned_at,
            "assigned_by": self.assigned_by,
            "previous_baseline_id": self.previous_baseline_id,
        }


class P6BaselineRoleAssignmentRepository(Protocol):
    def assign(
        self,
        assignment: P6BaselineRoleAssignment,
        *,
        replace: bool,
    ) -> tuple[P6BaselineRoleAssignment, bool]: ...

    def get(
        self, scope: BackendScope, role: str
    ) -> P6BaselineRoleAssignment | None: ...

    def list(
        self, scope: BackendScope
    ) -> tuple[P6BaselineRoleAssignment, ...]: ...

    def history(
        self, scope: BackendScope, role: str
    ) -> tuple[P6BaselineRoleAssignment, ...]: ...


def _from_row(
    scope: BackendScope,
    row: tuple[object, ...],
    *,
    revision_column: int,
) -> P6BaselineRoleAssignment:
    try:
        if int(row[revision_column]) != scope.project_revision:
            raise P6BaselineAssignmentError("REVISION_CONFLICT")
        result = P6BaselineRoleAssignment(
            scope=scope,
            role=str(row[0]),
            baseline_id=str(row[1]),
            assigned_at=str(row[2]),
            assigned_by=str(row[3]),
            previous_baseline_id=None if row[4] is None else str(row[4]),
        )
        result.validate()
        return result
    except (ArithmeticError, TypeError, ValueError) as exc:
        if isinstance(exc, P6BaselineAssignmentError):
            raise
        raise P6BaselineAssignmentError("INVALID_STORED_BASELINE_ASSIGNMENT") from exc


def _ordered(rows: Iterable[P6BaselineRoleAssignment]) -> tuple[P6BaselineRoleAssignment, ...]:
    positions = {role: index for index, role in enumerate(BASELINE_ROLES)}
    return tuple(sorted(rows, key=lambda item: positions[item.role]))


class SQLiteP6BaselineRoleAssignmentRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS p6_baseline_role_assignment (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                project_revision INTEGER NOT NULL,
                role TEXT NOT NULL,
                baseline_id TEXT NOT NULL,
                assigned_at TEXT NOT NULL,
                assigned_by TEXT NOT NULL,
                previous_baseline_id TEXT,
                PRIMARY KEY (tenant_id, project_id, role),
                FOREIGN KEY (tenant_id, project_id, baseline_id)
                    REFERENCES p6_baseline (tenant_id, project_id, baseline_id)
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS p6_baseline_role_assignment_history (
                history_sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                project_revision INTEGER NOT NULL,
                role TEXT NOT NULL,
                baseline_id TEXT NOT NULL,
                previous_baseline_id TEXT,
                assigned_at TEXT NOT NULL,
                assigned_by TEXT NOT NULL,
                action TEXT NOT NULL
            )
            """
        )
        self.connection.commit()

    def _history_append(
        self,
        assignment: P6BaselineRoleAssignment,
        *,
        action: str,
    ) -> None:
        self.connection.execute(
            "INSERT INTO p6_baseline_role_assignment_history "
            "(tenant_id,project_id,project_revision,role,baseline_id,"
            "previous_baseline_id,assigned_at,assigned_by,action) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (
                assignment.scope.tenant_id,
                assignment.scope.project_id,
                assignment.scope.project_revision,
                assignment.role,
                assignment.baseline_id,
                assignment.previous_baseline_id,
                assignment.assigned_at,
                assignment.assigned_by,
                action,
            ),
        )

    def assign(
        self,
        assignment: P6BaselineRoleAssignment,
        *,
        replace: bool,
    ) -> tuple[P6BaselineRoleAssignment, bool]:
        assignment.validate()
        if not isinstance(replace, bool):
            raise P6BaselineAssignmentError("INVALID_REPLACE_FLAG")
        scope = assignment.scope
        was_in_transaction = self.connection.in_transaction
        try:
            existing = self.get(scope, assignment.role)
            if existing is not None and existing.baseline_id == assignment.baseline_id:
                return existing, False
            if existing is not None and not replace:
                raise P6BaselineAssignmentError(
                    f"BASELINE_ROLE_ALREADY_ASSIGNED:{assignment.role}"
                )
            if existing is None:
                self.connection.execute(
                    "INSERT INTO p6_baseline_role_assignment "
                    "(tenant_id,project_id,project_revision,role,baseline_id,"
                    "assigned_at,assigned_by,previous_baseline_id) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (
                        scope.tenant_id,
                        scope.project_id,
                        scope.project_revision,
                        assignment.role,
                        assignment.baseline_id,
                        assignment.assigned_at,
                        assignment.assigned_by,
                        assignment.previous_baseline_id,
                    ),
                )
                action = BASELINE_ASSIGNMENT_ACTION_ASSIGN
                stored = assignment
            else:
                self.connection.execute(
                    "UPDATE p6_baseline_role_assignment SET "
                    "project_revision=?, baseline_id=?, assigned_at=?, "
                    "assigned_by=?, previous_baseline_id=? "
                    "WHERE tenant_id=? AND project_id=? AND role=?",
                    (
                        scope.project_revision,
                        assignment.baseline_id,
                        assignment.assigned_at,
                        assignment.assigned_by,
                        existing.baseline_id,
                        scope.tenant_id,
                        scope.project_id,
                        assignment.role,
                    ),
                )
                action = BASELINE_ASSIGNMENT_ACTION_REASSIGN
                stored = P6BaselineRoleAssignment(
                    scope=scope,
                    role=assignment.role,
                    baseline_id=assignment.baseline_id,
                    assigned_at=assignment.assigned_at,
                    assigned_by=assignment.assigned_by,
                    previous_baseline_id=existing.baseline_id,
                )
            self._history_append(stored, action=action)
        except sqlite3.IntegrityError as exc:
            if not was_in_transaction:
                self.connection.rollback()
            raise P6BaselineAssignmentError(
                "BASELINE_ROLE_BASELINE_REQUIRED"
            ) from exc
        if not was_in_transaction:
            self.connection.commit()
        return stored, existing is not None

    def get(
        self, scope: BackendScope, role: str
    ) -> P6BaselineRoleAssignment | None:
        scope.validate()
        role = require_baseline_role(role)
        row = self.connection.execute(
            "SELECT role,baseline_id,assigned_at,assigned_by,"
            "previous_baseline_id,project_revision "
            "FROM p6_baseline_role_assignment "
            "WHERE tenant_id=? AND project_id=? AND role=?",
            (scope.tenant_id, scope.project_id, role),
        ).fetchone()
        if row is None:
            return None
        return _from_row(scope, row, revision_column=5)

    def list(
        self, scope: BackendScope
    ) -> tuple[P6BaselineRoleAssignment, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT role,baseline_id,assigned_at,assigned_by,"
            "previous_baseline_id,project_revision "
            "FROM p6_baseline_role_assignment "
            "WHERE tenant_id=? AND project_id=?",
            (scope.tenant_id, scope.project_id),
        ).fetchall()
        return _ordered(
            _from_row(scope, row, revision_column=5) for row in rows
        )

    def history(
        self, scope: BackendScope, role: str
    ) -> tuple[P6BaselineRoleAssignment, ...]:
        scope.validate()
        role = require_baseline_role(role)
        rows = self.connection.execute(
            "SELECT role,baseline_id,assigned_at,assigned_by,"
            "previous_baseline_id,project_revision "
            "FROM p6_baseline_role_assignment_history "
            "WHERE tenant_id=? AND project_id=? AND role=? "
            "ORDER BY history_sequence",
            (scope.tenant_id, scope.project_id, role),
        ).fetchall()
        return tuple(
            _from_row(scope, row, revision_column=5) for row in rows
        )


class PostgresP6BaselineRoleAssignmentRepository:
    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS p6_baseline_role_assignment ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, "
            "project_revision BIGINT NOT NULL, role TEXT NOT NULL, "
            "baseline_id TEXT NOT NULL, assigned_at TEXT NOT NULL, "
            "assigned_by TEXT NOT NULL, previous_baseline_id TEXT, "
            "PRIMARY KEY (tenant_id, project_id, role), "
            "FOREIGN KEY (tenant_id, project_id, baseline_id) "
            "REFERENCES p6_baseline (tenant_id, project_id, baseline_id))"
        )
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS p6_baseline_role_assignment_history ("
            "history_sequence BIGSERIAL PRIMARY KEY, tenant_id TEXT NOT NULL, "
            "project_id TEXT NOT NULL, project_revision BIGINT NOT NULL, "
            "role TEXT NOT NULL, baseline_id TEXT NOT NULL, "
            "previous_baseline_id TEXT, assigned_at TEXT NOT NULL, "
            "assigned_by TEXT NOT NULL, action TEXT NOT NULL)"
        )

    def assign(
        self,
        assignment: P6BaselineRoleAssignment,
        *,
        replace: bool,
    ) -> tuple[P6BaselineRoleAssignment, bool]:
        assignment.validate()
        if not isinstance(replace, bool):
            raise P6BaselineAssignmentError("INVALID_REPLACE_FLAG")
        scope = assignment.scope
        existing = self.get(scope, assignment.role)
        if existing is not None and existing.baseline_id == assignment.baseline_id:
            return existing, False
        if existing is not None and not replace:
            raise P6BaselineAssignmentError(
                f"BASELINE_ROLE_ALREADY_ASSIGNED:{assignment.role}"
            )
        try:
            if existing is None:
                self.connection.execute(
                    "INSERT INTO p6_baseline_role_assignment "
                    "(tenant_id,project_id,project_revision,role,baseline_id,"
                    "assigned_at,assigned_by,previous_baseline_id) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                    (
                        scope.tenant_id,
                        scope.project_id,
                        scope.project_revision,
                        assignment.role,
                        assignment.baseline_id,
                        assignment.assigned_at,
                        assignment.assigned_by,
                        assignment.previous_baseline_id,
                    ),
                )
                action = BASELINE_ASSIGNMENT_ACTION_ASSIGN
                stored = assignment
            else:
                self.connection.execute(
                    "UPDATE p6_baseline_role_assignment SET "
                    "project_revision=%s, baseline_id=%s, assigned_at=%s, "
                    "assigned_by=%s, previous_baseline_id=%s "
                    "WHERE tenant_id=%s AND project_id=%s AND role=%s",
                    (
                        scope.project_revision,
                        assignment.baseline_id,
                        assignment.assigned_at,
                        assignment.assigned_by,
                        existing.baseline_id,
                        scope.tenant_id,
                        scope.project_id,
                        assignment.role,
                    ),
                )
                action = BASELINE_ASSIGNMENT_ACTION_REASSIGN
                stored = P6BaselineRoleAssignment(
                    scope=scope,
                    role=assignment.role,
                    baseline_id=assignment.baseline_id,
                    assigned_at=assignment.assigned_at,
                    assigned_by=assignment.assigned_by,
                    previous_baseline_id=existing.baseline_id,
                )
            self.connection.execute(
                "INSERT INTO p6_baseline_role_assignment_history "
                "(tenant_id,project_id,project_revision,role,baseline_id,"
                "previous_baseline_id,assigned_at,assigned_by,action) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    scope.tenant_id,
                    scope.project_id,
                    scope.project_revision,
                    stored.role,
                    stored.baseline_id,
                    stored.previous_baseline_id,
                    stored.assigned_at,
                    stored.assigned_by,
                    action,
                ),
            )
        except Exception as exc:
            if getattr(exc, "sqlstate", None) == "23503":
                raise P6BaselineAssignmentError(
                    "BASELINE_ROLE_BASELINE_REQUIRED"
                ) from exc
            raise
        return stored, existing is not None

    def get(
        self, scope: BackendScope, role: str
    ) -> P6BaselineRoleAssignment | None:
        scope.validate()
        role = require_baseline_role(role)
        row = self.connection.execute(
            "SELECT role,baseline_id,assigned_at,assigned_by,"
            "previous_baseline_id,project_revision "
            "FROM p6_baseline_role_assignment "
            "WHERE tenant_id=%s AND project_id=%s AND role=%s",
            (scope.tenant_id, scope.project_id, role),
        ).fetchone()
        if row is None:
            return None
        return _from_row(scope, row, revision_column=5)

    def list(
        self, scope: BackendScope
    ) -> tuple[P6BaselineRoleAssignment, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT role,baseline_id,assigned_at,assigned_by,"
            "previous_baseline_id,project_revision "
            "FROM p6_baseline_role_assignment "
            "WHERE tenant_id=%s AND project_id=%s",
            (scope.tenant_id, scope.project_id),
        ).fetchall()
        return _ordered(
            _from_row(scope, row, revision_column=5) for row in rows
        )

    def history(
        self, scope: BackendScope, role: str
    ) -> tuple[P6BaselineRoleAssignment, ...]:
        scope.validate()
        role = require_baseline_role(role)
        rows = self.connection.execute(
            "SELECT role,baseline_id,assigned_at,assigned_by,"
            "previous_baseline_id,project_revision "
            "FROM p6_baseline_role_assignment_history "
            "WHERE tenant_id=%s AND project_id=%s AND role=%s "
            "ORDER BY history_sequence",
            (scope.tenant_id, scope.project_id, role),
        ).fetchall()
        return tuple(
            _from_row(scope, row, revision_column=5) for row in rows
        )


@dataclass(frozen=True)
class P6BaselineRoleSummaryEntry:
    role: str
    assignment: P6BaselineRoleAssignment
    baseline: P6Baseline
    activity_count: int

    def to_payload(self) -> dict[str, object]:
        return {
            "role": self.role,
            "baseline_id": self.baseline.baseline_id,
            "name": self.baseline.name,
            "baseline_type": self.baseline.baseline_type,
            "source_revision": self.baseline.source_revision,
            "created_at": self.baseline.created_at,
            "activity_count": self.activity_count,
            "assigned_at": self.assignment.assigned_at,
            "assigned_by": self.assignment.assigned_by,
        }


@dataclass(frozen=True)
class P6BaselineRoleSummary:
    """The live project-summary baseline fields resolved from assignments."""

    scope: BackendScope
    entries: tuple[P6BaselineRoleSummaryEntry, ...]

    def by_role(self) -> dict[str, P6BaselineRoleSummaryEntry]:
        return {entry.role: entry for entry in self.entries}

    def to_payload(self) -> dict[str, object]:
        by_role = self.by_role()
        return {
            "scope": {
                "tenant_id": self.scope.tenant_id,
                "project_id": self.scope.project_id,
                "project_revision": self.scope.project_revision,
            },
            "roles": {
                role: (
                    None
                    if role not in by_role
                    else by_role[role].to_payload()
                )
                for role in BASELINE_ROLES
            },
            "assigned_roles": [
                role for role in BASELINE_ROLES if role in by_role
            ],
            "unassigned_roles": [
                role for role in BASELINE_ROLES if role not in by_role
            ],
        }


@dataclass(frozen=True)
class P6BaselineAssignmentService:
    """Assign immutable baseline identities to live summary roles."""

    repository: P6BaselineRoleAssignmentRepository
    baseline_repository: P6BaselineRepository
    baseline_activity_repository: P6BaselineActivityRepository
    transaction_manager: object
    clock: Callable[[], str] | None = None

    def _now(self) -> str:
        if self.clock is not None:
            return self.clock()
        return datetime.now().astimezone().isoformat()

    def assign(
        self,
        scope: BackendScope,
        role: str,
        baseline_id: str,
        *,
        assigned_by: str,
        replace: bool = False,
    ) -> tuple[P6BaselineRoleAssignment, bool]:
        scope.validate()
        role = require_baseline_role(role)
        _identifier(baseline_id, "INVALID_BASELINE_ID")
        _identifier(assigned_by, "INVALID_ASSIGNED_BY")
        with self.transaction_manager.transaction():
            try:
                baseline = self.baseline_repository.get(scope, baseline_id)
            except P6BaselinePersistenceError as exc:
                if str(exc) == "REVISION_CONFLICT":
                    raise P6BaselineAssignmentError("REVISION_CONFLICT") from exc
                raise
            if baseline is None:
                raise P6BaselineAssignmentError("BASELINE_NOT_FOUND")
            assignment = P6BaselineRoleAssignment(
                scope=scope,
                role=role,
                baseline_id=baseline_id,
                assigned_at=self._now(),
                assigned_by=assigned_by,
            )
            return self.repository.assign(assignment, replace=replace)

    def read(
        self, scope: BackendScope, role: str
    ) -> P6BaselineRoleAssignment | None:
        scope.validate()
        role = require_baseline_role(role)
        with self.transaction_manager.transaction():
            return self.repository.get(scope, role)

    def history(
        self, scope: BackendScope, role: str
    ) -> tuple[P6BaselineRoleAssignment, ...]:
        scope.validate()
        role = require_baseline_role(role)
        with self.transaction_manager.transaction():
            return self.repository.history(scope, role)

    def summary(self, scope: BackendScope) -> P6BaselineRoleSummary:
        scope.validate()
        with self.transaction_manager.transaction():
            entries: list[P6BaselineRoleSummaryEntry] = []
            for assignment in self.repository.list(scope):
                baseline = self.baseline_repository.get(
                    scope, assignment.baseline_id
                )
                if baseline is None:
                    raise P6BaselineAssignmentError(
                        "BASELINE_SUMMARY_BASELINE_MISSING:"
                        + assignment.role
                    )
                activities = self.baseline_activity_repository.list(
                    scope, assignment.baseline_id
                )
                entries.append(
                    P6BaselineRoleSummaryEntry(
                        role=assignment.role,
                        assignment=assignment,
                        baseline=baseline,
                        activity_count=len(activities),
                    )
                )
            return P6BaselineRoleSummary(scope=scope, entries=tuple(entries))


__all__ = [
    "BASELINE_ASSIGNMENT_ACTION_ASSIGN",
    "BASELINE_ASSIGNMENT_ACTION_REASSIGN",
    "BASELINE_ROLES",
    "BASELINE_ROLE_PRIMARY",
    "BASELINE_ROLE_PROJECT",
    "BASELINE_ROLE_SECONDARY",
    "BASELINE_ROLE_TERTIARY",
    "P6BaselineAssignmentError",
    "P6BaselineAssignmentService",
    "P6BaselineRoleAssignment",
    "P6BaselineRoleAssignmentRepository",
    "P6BaselineRoleSummary",
    "P6BaselineRoleSummaryEntry",
    "PostgresP6BaselineRoleAssignmentRepository",
    "SQLiteP6BaselineRoleAssignmentRepository",
    "require_baseline_role",
]
