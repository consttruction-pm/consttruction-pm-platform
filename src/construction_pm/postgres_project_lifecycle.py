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

    def __init__(self, connection: ProjectLifecyclePostgresConnection) -> None:
        self._connection = connection

    def list_for_user(self, tenant_id: str, user_id: str) -> tuple[ProjectSummary, ...]:
        rows = self._connection.execute(
            "SELECT p.project_id, p.tenant_id, p.name, p.revision "
            "FROM project_lifecycle_projects p "
            "JOIN project_lifecycle_memberships m ON m.tenant_id=p.tenant_id AND m.project_id=p.project_id "
            "WHERE p.tenant_id=%s AND m.user_id=%s ORDER BY p.project_id",
            (tenant_id, user_id),
        ).fetchall()
        return tuple(ProjectSummary(r[0], r[1], r[2], r[3]) for r in rows)

    def get_for_user(self, tenant_id: str, project_id: str, user_id: str) -> ProjectSummary | None:
        row = self._connection.execute(
            "SELECT p.project_id, p.tenant_id, p.name, p.revision "
            "FROM project_lifecycle_projects p "
            "JOIN project_lifecycle_memberships m ON m.tenant_id=p.tenant_id AND m.project_id=p.project_id "
            "WHERE p.tenant_id=%s AND p.project_id=%s AND m.user_id=%s",
            (tenant_id, project_id, user_id),
        ).fetchone()
        return None if row is None else ProjectSummary(row[0], row[1], row[2], row[3])

    def create_for_user(self, tenant_id: str, user_id: str, project_id: str, name: str) -> ProjectSummary:
        self._connection.execute(
            "INSERT INTO project_lifecycle_projects (tenant_id, project_id, name, revision) "
            "VALUES (%s,%s,%s,0)",
            (tenant_id, project_id, name),
        )
        self._connection.execute(
            "INSERT INTO project_lifecycle_memberships (tenant_id, project_id, user_id) "
            "VALUES (%s,%s,%s)",
            (tenant_id, project_id, user_id),
        )
        return ProjectSummary(project_id, tenant_id, name, 0)


def _as_datetime(value: Any) -> datetime:
    if not isinstance(value, datetime):
        raise ValueError("INVALID_SESSION_EXPIRY")
    return value
