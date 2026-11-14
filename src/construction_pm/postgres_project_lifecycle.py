from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Protocol

from .application.project_lifecycle import (
    AuthenticatedSession,
    PROJECT_STATUSES,
    ProjectRepository,
    ProjectStatusEvent,
    ProjectSummary,
    SessionRepository,
)


class ProjectLifecyclePostgresConnection(Protocol):
    def execute(self, sql: str, params: tuple[Any, ...] = ()): ...


PROJECT_LIFECYCLE_SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS project_lifecycle_projects (
        tenant_id TEXT NOT NULL,
        project_id TEXT NOT NULL,
        name TEXT NOT NULL,
        revision BIGINT NOT NULL DEFAULT 0,
        description TEXT NOT NULL DEFAULT '',
        start_date TEXT,
        date_system TEXT NOT NULL DEFAULT 'gregorian',
        primary_calendar_id TEXT,
        settings_revision BIGINT NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'active',
        business_domain TEXT NOT NULL DEFAULT '',
        obs_responsible_manager TEXT NOT NULL DEFAULT '',
        website_url TEXT NOT NULL DEFAULT '',
        default_activity_type TEXT NOT NULL DEFAULT 'Task Dependent',
        default_percent_complete_type TEXT NOT NULL DEFAULT 'DURATION',
        activity_id_prefix TEXT NOT NULL DEFAULT '',
        activity_id_suffix TEXT NOT NULL DEFAULT '',
        activity_id_increment INTEGER NOT NULL DEFAULT 10,
        increment_activity_id BOOLEAN NOT NULL DEFAULT FALSE,
        checkout_state TEXT NOT NULL DEFAULT 'checked_in',
        checked_out_by TEXT NOT NULL DEFAULT '',
        checked_out_at TIMESTAMPTZ,
        PRIMARY KEY (tenant_id, project_id)
    )
    """,
    """
    ALTER TABLE project_lifecycle_projects
        ADD COLUMN IF NOT EXISTS obs_responsible_manager TEXT NOT NULL DEFAULT ''
    """,
    """
    ALTER TABLE project_lifecycle_projects
        ADD COLUMN IF NOT EXISTS website_url TEXT NOT NULL DEFAULT ''
    """,
    """
    ALTER TABLE project_lifecycle_projects
        ADD COLUMN IF NOT EXISTS default_activity_type TEXT NOT NULL DEFAULT 'Task Dependent'
    """,
    """
    ALTER TABLE project_lifecycle_projects
        ADD COLUMN IF NOT EXISTS default_percent_complete_type TEXT NOT NULL DEFAULT 'DURATION'
    """,
    """
    ALTER TABLE project_lifecycle_projects
        ADD COLUMN IF NOT EXISTS activity_id_prefix TEXT NOT NULL DEFAULT ''
    """,
    """
    ALTER TABLE project_lifecycle_projects
        ADD COLUMN IF NOT EXISTS activity_id_suffix TEXT NOT NULL DEFAULT ''
    """,
    """
    ALTER TABLE project_lifecycle_projects
        ADD COLUMN IF NOT EXISTS activity_id_increment INTEGER NOT NULL DEFAULT 10
    """,
    """
    ALTER TABLE project_lifecycle_projects
        ADD COLUMN IF NOT EXISTS increment_activity_id BOOLEAN NOT NULL DEFAULT FALSE
    """,
    """
    ALTER TABLE project_lifecycle_projects
        ADD COLUMN IF NOT EXISTS checkout_state TEXT NOT NULL DEFAULT 'checked_in'
    """,
    """
    ALTER TABLE project_lifecycle_projects
        ADD COLUMN IF NOT EXISTS checked_out_by TEXT NOT NULL DEFAULT ''
    """,
    """
    ALTER TABLE project_lifecycle_projects
        ADD COLUMN IF NOT EXISTS checked_out_at TIMESTAMPTZ
    """,
    """
    CREATE TABLE IF NOT EXISTS project_lifecycle_memberships (
        tenant_id TEXT NOT NULL,
        project_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        PRIMARY KEY (tenant_id, project_id, user_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS project_lifecycle_status_event (
        tenant_id TEXT NOT NULL,
        project_id TEXT NOT NULL,
        event_id TEXT NOT NULL,
        from_status TEXT NOT NULL,
        to_status TEXT NOT NULL,
        actor_user_id TEXT NOT NULL,
        recorded_at TIMESTAMPTZ NOT NULL,
        settings_revision BIGINT NOT NULL,
        PRIMARY KEY (tenant_id, project_id, event_id)
    )
    """,
)


def initialize_project_lifecycle_schema(
    connection: ProjectLifecyclePostgresConnection,
) -> None:
    """Create the lifecycle tables when absent. Never drops or rewrites a row."""
    for statement in PROJECT_LIFECYCLE_SCHEMA_STATEMENTS:
        connection.execute(statement)


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
        "p.start_date, p.date_system, p.primary_calendar_id, p.settings_revision, "
        "p.status, p.business_domain, p.obs_responsible_manager, p.website_url, "
        "p.default_activity_type, p.default_percent_complete_type, "
        "p.activity_id_prefix, p.activity_id_suffix, p.activity_id_increment, "
        "p.increment_activity_id, p.checkout_state, p.checked_out_by, p.checked_out_at "
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
        business_domain: str = "",
        obs_responsible_manager: str = "",
        website_url: str = "",
        default_activity_type: str = "Task Dependent",
        default_percent_complete_type: str = "DURATION",
        activity_id_prefix: str = "",
        activity_id_suffix: str = "",
        activity_id_increment: int = 10,
        increment_activity_id: bool = False,
    ) -> ProjectSummary:
        self._connection.execute(
            "INSERT INTO project_lifecycle_projects "
            "(tenant_id, project_id, name, revision, description, start_date, date_system, "
            "primary_calendar_id, settings_revision, business_domain, "
            "obs_responsible_manager, website_url, default_activity_type, "
            "default_percent_complete_type, activity_id_prefix, activity_id_suffix, "
            "activity_id_increment, increment_activity_id) "
            "VALUES (%s,%s,%s,0,%s,%s,%s,%s,0,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                tenant_id,
                project_id,
                name,
                description,
                start_date,
                date_system,
                primary_calendar_id,
                business_domain,
                obs_responsible_manager,
                website_url,
                default_activity_type,
                default_percent_complete_type,
                activity_id_prefix,
                activity_id_suffix,
                activity_id_increment,
                increment_activity_id,
            ),
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
            business_domain=business_domain,
            obs_responsible_manager=obs_responsible_manager,
            website_url=website_url,
            default_activity_type=default_activity_type,
            default_percent_complete_type=default_percent_complete_type,
            activity_id_prefix=activity_id_prefix,
            activity_id_suffix=activity_id_suffix,
            activity_id_increment=activity_id_increment,
            increment_activity_id=increment_activity_id,
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
        business_domain: str | None = None,
        obs_responsible_manager: str | None = None,
        website_url: str | None = None,
        default_activity_type: str | None = None,
        default_percent_complete_type: str | None = None,
        activity_id_prefix: str | None = None,
        activity_id_suffix: str | None = None,
        activity_id_increment: int | None = None,
        increment_activity_id: bool | None = None,
    ) -> ProjectSummary | None:
        row = self._connection.execute(
            "UPDATE project_lifecycle_projects SET name=%s, description=%s, "
            "start_date=%s, date_system=%s, primary_calendar_id=%s, "
            "business_domain=COALESCE(%s, business_domain), "
            "obs_responsible_manager=COALESCE(%s, obs_responsible_manager), "
            "website_url=COALESCE(%s, website_url), "
            "default_activity_type=COALESCE(%s, default_activity_type), "
            "default_percent_complete_type=COALESCE(%s, default_percent_complete_type), "
            "activity_id_prefix=COALESCE(%s, activity_id_prefix), "
            "activity_id_suffix=COALESCE(%s, activity_id_suffix), "
            "activity_id_increment=COALESCE(%s, activity_id_increment), "
            "increment_activity_id=COALESCE(%s, increment_activity_id), "
            "settings_revision=settings_revision+1 "
            "WHERE tenant_id=%s AND project_id=%s AND settings_revision=%s AND EXISTS ("
            "SELECT 1 FROM project_lifecycle_memberships m "
            "WHERE m.tenant_id=project_lifecycle_projects.tenant_id "
            "AND m.project_id=project_lifecycle_projects.project_id AND m.user_id=%s) "
            "RETURNING project_id, tenant_id, name, revision, description, "
            "start_date, date_system, primary_calendar_id, settings_revision, status, "
            "business_domain, obs_responsible_manager, website_url, "
            "default_activity_type, default_percent_complete_type, activity_id_prefix, "
            "activity_id_suffix, activity_id_increment, increment_activity_id, "
            "checkout_state, checked_out_by, checked_out_at",
            (
                name,
                description,
                start_date,
                date_system,
                primary_calendar_id,
                business_domain,
                obs_responsible_manager,
                website_url,
                default_activity_type,
                default_percent_complete_type,
                activity_id_prefix,
                activity_id_suffix,
                activity_id_increment,
                increment_activity_id,
                tenant_id,
                project_id,
                expected_revision,
                user_id,
            ),
        ).fetchone()
        return None if row is None else _summary(row)

    def set_status_for_user(
        self,
        tenant_id: str,
        user_id: str,
        project_id: str,
        *,
        status: str,
        expected_revision: int,
        actor_user_id: str,
        recorded_at: datetime,
    ) -> ProjectSummary | None:
        """Change status and append its event; the caller owns the transaction."""
        if status not in PROJECT_STATUSES:
            raise ValueError("PROJECT_STATUS_INVALID")
        current = self._connection.execute(
            "SELECT p.status, p.settings_revision FROM project_lifecycle_projects p "
            "WHERE p.tenant_id=%s AND p.project_id=%s AND EXISTS ("
            "SELECT 1 FROM project_lifecycle_memberships m "
            "WHERE m.tenant_id=p.tenant_id AND m.project_id=p.project_id "
            "AND m.user_id=%s)",
            (tenant_id, project_id, user_id),
        ).fetchone()
        if current is None:
            return None
        from_status = str(current[0] or "active")
        current_revision = int(current[1])
        if from_status == status:
            return self.get_for_user(tenant_id, project_id, user_id)
        if current_revision != expected_revision:
            return None
        row = self._connection.execute(
            "UPDATE project_lifecycle_projects SET status=%s, "
            "settings_revision=settings_revision+1 "
            "WHERE tenant_id=%s AND project_id=%s AND settings_revision=%s AND EXISTS ("
            "SELECT 1 FROM project_lifecycle_memberships m "
            "WHERE m.tenant_id=project_lifecycle_projects.tenant_id "
            "AND m.project_id=project_lifecycle_projects.project_id AND m.user_id=%s) "
            "RETURNING project_id, tenant_id, name, revision, description, "
            "start_date, date_system, primary_calendar_id, settings_revision, status, "
            "business_domain, obs_responsible_manager, website_url, checkout_state, "
            "checked_out_by, checked_out_at",
            (status, tenant_id, project_id, expected_revision, user_id),
        ).fetchone()
        if row is None:
            return None
        new_revision = expected_revision + 1
        event_id = f"{project_id}@{new_revision}"
        self._connection.execute(
            "INSERT INTO project_lifecycle_status_event "
            "(tenant_id, project_id, event_id, from_status, to_status, "
            "actor_user_id, recorded_at, settings_revision) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            (
                tenant_id,
                project_id,
                event_id,
                from_status,
                status,
                actor_user_id,
                recorded_at,
                new_revision,
            ),
        )
        stored = self._connection.execute(
            "SELECT from_status, to_status FROM project_lifecycle_status_event "
            "WHERE tenant_id=%s AND project_id=%s AND event_id=%s",
            (tenant_id, project_id, event_id),
        ).fetchone()
        if stored is None or str(stored[0]) != from_status or str(stored[1]) != status:
            raise ValueError("PROJECT_STATUS_READBACK_MISMATCH")
        return _summary(row)

    def set_checkout_for_user(
        self,
        tenant_id: str,
        user_id: str,
        project_id: str,
        *,
        checked_out: bool,
        expected_revision: int,
        actor_user_id: str,
        changed_at: datetime,
    ) -> ProjectSummary | None:
        """Atomically acquire or release the exclusive checkout lease."""
        if checked_out:
            next_state, next_owner, next_at = "checked_out", actor_user_id, changed_at
            lease_condition = "checkout_state='checked_in'"
            lease_values: tuple[object, ...] = ()
        else:
            next_state, next_owner, next_at = "checked_in", "", None
            lease_condition = "checkout_state='checked_out' AND checked_out_by=%s"
            lease_values = (actor_user_id,)
        row = self._connection.execute(
            "UPDATE project_lifecycle_projects SET checkout_state=%s, "
            "checked_out_by=%s, checked_out_at=%s, "
            "settings_revision=settings_revision+1 "
            "WHERE tenant_id=%s AND project_id=%s AND settings_revision=%s "
            "AND " + lease_condition + " AND EXISTS ("
            "SELECT 1 FROM project_lifecycle_memberships m "
            "WHERE m.tenant_id=project_lifecycle_projects.tenant_id "
            "AND m.project_id=project_lifecycle_projects.project_id AND m.user_id=%s) "
            "RETURNING project_id, tenant_id, name, revision, description, "
            "start_date, date_system, primary_calendar_id, settings_revision, status, "
            "business_domain, obs_responsible_manager, website_url, checkout_state, "
            "checked_out_by, checked_out_at",
            (
                next_state,
                next_owner,
                next_at,
                tenant_id,
                project_id,
                expected_revision,
                *lease_values,
                user_id,
            ),
        ).fetchone()
        return None if row is None else _summary(row)

    def status_history_for_user(
        self, tenant_id: str, project_id: str, user_id: str
    ) -> tuple[ProjectStatusEvent, ...]:
        rows = self._connection.execute(
            "SELECT e.event_id, e.from_status, e.to_status, e.actor_user_id, "
            "e.recorded_at, e.settings_revision "
            "FROM project_lifecycle_status_event e "
            "JOIN project_lifecycle_memberships m "
            "ON m.tenant_id=e.tenant_id AND m.project_id=e.project_id "
            "WHERE e.tenant_id=%s AND e.project_id=%s AND m.user_id=%s "
            "ORDER BY e.settings_revision ASC, e.recorded_at ASC, e.event_id ASC",
            (tenant_id, project_id, user_id),
        ).fetchall()
        return tuple(
            ProjectStatusEvent(
                tenant_id=tenant_id,
                project_id=project_id,
                event_id=str(row[0]),
                from_status=str(row[1]),
                to_status=str(row[2]),
                actor_user_id=str(row[3]),
                recorded_at=_as_datetime(row[4]),
                settings_revision=int(row[5]),
            )
            for row in rows
        )


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
        status=str(row[9]) if len(row) > 9 and row[9] else "active",
        business_domain=str(row[10]) if len(row) > 10 and row[10] else "",
        obs_responsible_manager=str(row[11]) if len(row) > 11 and row[11] else "",
        website_url=str(row[12]) if len(row) > 12 and row[12] else "",
        default_activity_type=(
            str(row[13]) if len(row) > 13 and row[13] else "Task Dependent"
        ),
        default_percent_complete_type=(
            str(row[14]) if len(row) > 14 and row[14] else "DURATION"
        ),
        activity_id_prefix=str(row[15]) if len(row) > 15 and row[15] else "",
        activity_id_suffix=str(row[16]) if len(row) > 16 and row[16] else "",
        activity_id_increment=(
            int(row[17]) if len(row) > 17 and row[17] is not None else 10
        ),
        increment_activity_id=bool(row[18]) if len(row) > 18 else False,
        checkout_state=(
            str(row[19]) if len(row) > 19 and row[19] else "checked_in"
        ),
        checked_out_by=str(row[20]) if len(row) > 20 and row[20] else "",
        checked_out_at=(
            None
            if len(row) <= 21 or row[21] is None
            else _as_datetime(row[21]).isoformat()
        ),
    )


def _as_datetime(value: Any) -> datetime:
    if not isinstance(value, datetime):
        raise ValueError("INVALID_SESSION_EXPIRY")
    return value
