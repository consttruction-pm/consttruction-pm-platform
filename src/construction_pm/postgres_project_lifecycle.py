from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Protocol

from .application.project_lifecycle import AuthenticatedSession, ProjectRepository, ProjectSummary, SessionRepository


class ProjectLifecyclePostgresConnection(Protocol):
    def execute(self, sql: str, params: tuple[Any, ...] = ()): ...


class PostgresSessionRepository(SessionRepository):
    """PostgreSQL adapter for opaque authenticated sessions.

    Authentication/credential issuance is intentionally outside this adapter. A
    trusted authentication boundary creates the session row; this adapter only
    resolves the opaque session id used by the HTTP layer.
    """

    def __init__(self, connection: ProjectLifecyclePostgresConnection) -> None:
        self._connection = connection

    def get(self, session_id: str) -> AuthenticatedSession | None:
        row = self._connection.execute(
            "SELECT session_id, user_id, tenant_id, roles_json, expires_at "
            "FROM project_lifecycle_sessions WHERE session_id=%s",
            (session_id,),
        ).fetchone()
        if row is None:
            return None
        roles = json.loads(row[3])
        if not isinstance(roles, list):
            raise ValueError("INVALID_SESSION_ROLES_JSON")
        return AuthenticatedSession(
            session_id=row[0],
            user_id=row[1],
            tenant_id=row[2],
            roles=frozenset(roles),
            expires_at=_as_datetime(row[4]),
        )


class PostgresProjectRepository(ProjectRepository):
    """Tenant- and membership-scoped project persistence adapter."""

    _SELECT = (
        "SELECT p.project_id, p.tenant_id, p.name, p.revision, p.description, "
        "p.start_date, p.date_system, p.primary_calendar_id, p.settings_revision "
        "FROM project_lifecycle_projects p "
    )

    def __init__(self, connection: ProjectLifecyclePostgresConnection) -> None:
        self._connection = connection

    def list_for_user(self, tenant_id: str, user_id: str) -> tuple[ProjectSummary, ...]:
        rows = self._connection.execute(
            self._SELECT
            + "JOIN project_lifecycle_memberships m ON m.tenant_id=p.tenant_id AND m.project_id=p.project_id "
            "WHERE p.tenant_id=%s AND m.user_id=%s ORDER BY p.project_id",
            (tenant_id, user_id),
        ).fetchall()
        return tuple(_summary(r) for r in rows)

    def get_for_user(self, tenant_id: str, project_id: str, user_id: str) -> ProjectSummary | None:
        row = self._connection.execute(
            self._SELECT
            + "JOIN project_lifecycle_memberships m ON m.tenant_id=p.tenant_id AND m.project_id=p.project_id "
            "WHERE p.tenant_id=%s AND p.project_id=%s AND m.user_id=%s",
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
        self._connection.execute(
            "INSERT INTO project_lifecycle_projects "
            "(tenant_id, project_id, name, revision, description, start_date, date_system, "
            "primary_calendar_id, settings_revision) "
            "VALUES (%s,%s,%s,0,%s,%s,%s,%s,0)",
            (tenant_id, project_id, name, description, start_date, date_system, primary_calendar_id),
        )
        self._connection.execute(
            "INSERT INTO project_lifecycle_memberships (tenant_id, project_id, user_id) "
            "VALUES (%s,%s,%s)",
            (tenant_id, project_id, user_id),
        )
        return ProjectSummary(
            project_id,
            tenant_id,
            name,
            0,
            description=description,
            start_date=start_date,
            date_system=date_system,
            primary_calendar_id=primary_calendar_id,
        )

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
        row = self._connection.execute(
            "UPDATE project_lifecycle_projects SET name=%s, description=%s, "
            "start_date=%s, date_system=%s, primary_calendar_id=%s, "
            "settings_revision=settings_revision+1 "
            "WHERE tenant_id=%s AND project_id=%s AND settings_revision=%s AND EXISTS ("
            "SELECT 1 FROM project_lifecycle_memberships m "
            "WHERE m.tenant_id=project_lifecycle_projects.tenant_id "
            "AND m.project_id=project_lifecycle_projects.project_id AND m.user_id=%s) "
            "RETURNING project_id, tenant_id, name, revision, description, "
            "start_date, date_system, primary_calendar_id, settings_revision",
            (
                name,
                description,
                start_date,
                date_system,
                primary_calendar_id,
                tenant_id,
                project_id,
                expected_revision,
                user_id,
            ),
        ).fetchone()
        return None if row is None else _summary(row)


def _summary(row: Any) -> ProjectSummary:
    start_date = row[5]
    if start_date is not None and not isinstance(start_date, str):
        # psycopg returns ``date`` for a DATE column; the API contract is ISO.
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
        settings_revision=int(row[8]) if len(row) > 8 and row[8] is not None else 0,
    )


def _as_datetime(value: Any) -> datetime:
    if not isinstance(value, datetime):
        raise ValueError("INVALID_SESSION_EXPIRY")
    return value
