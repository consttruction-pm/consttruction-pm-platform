from __future__ import annotations

"""SQLite project-lifecycle persistence for installed, offline CUBI clients.

This adapter implements the existing ProjectRepository contract. It is not a
preview/demo store and it does not issue identities or grants.
"""

import sqlite3
from datetime import date
from typing import Any

from construction_pm.application.project_lifecycle import ProjectRepository, ProjectSummary
from construction_pm.backend_p0.transactions import SQLiteTransactionManager


_SCHEMA_VERSION = 1
_SELECT_PROJECT = (
    "SELECT p.project_id, p.tenant_id, p.name, p.revision, p.description, "
    "p.start_date, p.date_system, p.primary_calendar_id, p.settings_revision "
    "FROM project_lifecycle_projects p "
)


def _summary(row: Any) -> ProjectSummary:
    start_date = row[5]
    if start_date is not None and not isinstance(start_date, str):
        start_date = start_date.isoformat()
    return ProjectSummary(
        project_id=str(row[0]),
        tenant_id=str(row[1]),
        name=str(row[2]),
        revision=int(row[3]),
        description=str(row[4] or ""),
        start_date=start_date,
        date_system=str(row[6] or "gregorian"),
        primary_calendar_id=None if row[7] is None else str(row[7]),
        settings_revision=int(row[8]) if row[8] is not None else 0,
    )


class SQLiteProjectRepository(ProjectRepository):
    """Tenant- and membership-scoped local ProjectRepository.

    The same SQLite connection should be shared with the other local domain
    repositories and the durable outbox so a host-owned transaction can commit
    the local domain write and its mutation event atomically.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._transactions = SQLiteTransactionManager(connection)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        if not self._connection.in_transaction:
            self._connection.execute("PRAGMA foreign_keys = ON")
        version = int(self._connection.execute("PRAGMA user_version").fetchone()[0])
        if version not in (0, _SCHEMA_VERSION):
            raise ValueError("UNSUPPORTED_LOCAL_PROJECT_SCHEMA_VERSION")

        self._connection.execute(
            """CREATE TABLE IF NOT EXISTS project_lifecycle_projects (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                name TEXT NOT NULL,
                revision INTEGER NOT NULL DEFAULT 0 CHECK (revision >= 0),
                description TEXT NOT NULL DEFAULT '',
                start_date TEXT,
                date_system TEXT NOT NULL DEFAULT 'gregorian'
                    CHECK (date_system IN ('gregorian', 'jalali')),
                primary_calendar_id TEXT,
                settings_revision INTEGER NOT NULL DEFAULT 0
                    CHECK (settings_revision >= 0),
                PRIMARY KEY (tenant_id, project_id)
            )"""
        )
        self._connection.execute(
            """CREATE TABLE IF NOT EXISTS project_lifecycle_memberships (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, user_id),
                FOREIGN KEY (tenant_id, project_id)
                    REFERENCES project_lifecycle_projects(tenant_id, project_id)
                    ON DELETE CASCADE
            )"""
        )
        self._connection.execute(
            """CREATE INDEX IF NOT EXISTS idx_project_lifecycle_memberships_user
                ON project_lifecycle_memberships (tenant_id, user_id)"""
        )
        if version == 0:
            self._connection.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")

    def list_for_user(self, tenant_id: str, user_id: str) -> tuple[ProjectSummary, ...]:
        rows = self._connection.execute(
            _SELECT_PROJECT
            + "JOIN project_lifecycle_memberships m "
            "ON m.tenant_id=p.tenant_id AND m.project_id=p.project_id "
            "WHERE p.tenant_id=? AND m.user_id=? ORDER BY p.project_id",
            (tenant_id, user_id),
        ).fetchall()
        return tuple(_summary(row) for row in rows)

    def get_for_user(
        self, tenant_id: str, project_id: str, user_id: str
    ) -> ProjectSummary | None:
        row = self._connection.execute(
            _SELECT_PROJECT
            + "JOIN project_lifecycle_memberships m "
            "ON m.tenant_id=p.tenant_id AND m.project_id=p.project_id "
            "WHERE p.tenant_id=? AND p.project_id=? AND m.user_id=?",
            (tenant_id, project_id, user_id),
        ).fetchone()
        return None if row is None else _summary(row)

    def create_for_user(
        self,
        tenant_id: str,
        user_id: str,
        project_id: str,
        name: str,
        *,
        description: str = "",
        start_date: str | None = None,
        date_system: str = "gregorian",
        primary_calendar_id: str | None = None,
    ) -> ProjectSummary:
        for value in (tenant_id, user_id, project_id, name):
            if not isinstance(value, str) or not value.strip():
                raise ValueError("PROJECT_IDENTITY_REQUIRED")
        if date_system not in {"gregorian", "jalali"}:
            raise ValueError("PROJECT_DATE_SYSTEM_INVALID")
        if start_date is not None:
            if not isinstance(start_date, str) or date.fromisoformat(start_date).isoformat() != start_date:
                raise ValueError("PROJECT_START_DATE_INVALID")

        try:
            with self._transactions.transaction():
                self._connection.execute(
                    """INSERT INTO project_lifecycle_projects
                    (tenant_id, project_id, name, revision, description, start_date,
                     date_system, primary_calendar_id, settings_revision)
                    VALUES (?, ?, ?, 0, ?, ?, ?, ?, 0)""",
                    (
                        tenant_id, project_id, name, description, start_date,
                        date_system, primary_calendar_id,
                    ),
                )
                self._connection.execute(
                    """INSERT INTO project_lifecycle_memberships
                    (tenant_id, project_id, user_id) VALUES (?, ?, ?)""",
                    (tenant_id, project_id, user_id),
                )
                created = self.get_for_user(tenant_id, project_id, user_id)
                if created is None:
                    raise RuntimeError("LOCAL_PROJECT_CREATE_READBACK_FAILED")
                return created
        except sqlite3.IntegrityError as exc:
            raise ValueError("PROJECT_ALREADY_EXISTS_OR_MEMBERSHIP_INVALID") from exc

    def update_for_user(
        self,
        tenant_id: str,
        user_id: str,
        project_id: str,
        *,
        expected_revision: int,
        name: str,
        description: str = "",
        start_date: str | None = None,
        date_system: str = "gregorian",
        primary_calendar_id: str | None = None,
    ) -> ProjectSummary | None:
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 0:
            raise ValueError("PROJECT_SETTINGS_REVISION_INVALID")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("PROJECT_NAME_REQUIRED")
        if date_system not in {"gregorian", "jalali"}:
            raise ValueError("PROJECT_DATE_SYSTEM_INVALID")
        if start_date is not None:
            if not isinstance(start_date, str) or date.fromisoformat(start_date).isoformat() != start_date:
                raise ValueError("PROJECT_START_DATE_INVALID")

        with self._transactions.transaction():
            cursor = self._connection.execute(
                """UPDATE project_lifecycle_projects
                SET name=?, description=?, start_date=?, date_system=?,
                    primary_calendar_id=?, settings_revision=settings_revision+1
                WHERE tenant_id=? AND project_id=? AND settings_revision=?
                  AND EXISTS (
                    SELECT 1 FROM project_lifecycle_memberships m
                    WHERE m.tenant_id=project_lifecycle_projects.tenant_id
                      AND m.project_id=project_lifecycle_projects.project_id
                      AND m.user_id=?
                  )""",
                (
                    name.strip(), description, start_date, date_system,
                    primary_calendar_id, tenant_id, project_id, expected_revision, user_id,
                ),
            )
            if cursor.rowcount != 1:
                return None
            return self.get_for_user(tenant_id, project_id, user_id)


__all__ = ["SQLiteProjectRepository"]
