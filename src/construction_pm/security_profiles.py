"""Persisted P6-style global/project security profiles and authorization evaluator.

The evaluator is intentionally restrictive: legacy role grants remain a ceiling;
an assigned global profile and/or project profile can only narrow those grants.
No profile assignment means the legacy policy remains in force during migration.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Iterable

from .application.authorization import (
    AuthorizationContext,
    Permission,
    RoleBasedAuthorizationPolicy,
)

_PROFILE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,99}$")
_PROFILE_SCOPES = frozenset({"global", "project"})


class SecurityProfileError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class SecurityProfile:
    tenant_id: str
    profile_id: str
    name: str
    scope: str
    active: bool
    revision: int
    privileges: frozenset[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "profile_id": self.profile_id,
            "name": self.name,
            "scope": self.scope,
            "active": self.active,
            "revision": self.revision,
            "privileges": sorted(self.privileges),
        }


SECURITY_PROFILE_SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS p6_security_profiles (
        tenant_id TEXT NOT NULL,
        profile_id TEXT NOT NULL,
        name TEXT NOT NULL CHECK (length(trim(name)) BETWEEN 1 AND 120),
        scope TEXT NOT NULL CHECK (scope IN ('global','project')),
        active BOOLEAN NOT NULL DEFAULT TRUE,
        revision BIGINT NOT NULL CHECK (revision >= 1),
        created_by TEXT NOT NULL,
        updated_by TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL,
        PRIMARY KEY (tenant_id, profile_id),
        UNIQUE (tenant_id, scope, name)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS p6_security_profile_privileges (
        tenant_id TEXT NOT NULL,
        profile_id TEXT NOT NULL,
        permission TEXT NOT NULL,
        PRIMARY KEY (tenant_id, profile_id, permission),
        FOREIGN KEY (tenant_id, profile_id)
            REFERENCES p6_security_profiles(tenant_id, profile_id) ON DELETE RESTRICT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS p6_security_profile_assignments (
        tenant_id TEXT NOT NULL,
        profile_id TEXT NOT NULL,
        user_id TEXT NOT NULL REFERENCES identity_users(user_id) ON DELETE RESTRICT,
        project_id TEXT NOT NULL DEFAULT '',
        revision BIGINT NOT NULL CHECK (revision >= 1),
        assigned_by TEXT NOT NULL,
        assigned_at TIMESTAMPTZ NOT NULL,
        PRIMARY KEY (tenant_id, profile_id, user_id, project_id),
        FOREIGN KEY (tenant_id, profile_id)
            REFERENCES p6_security_profiles(tenant_id, profile_id) ON DELETE RESTRICT,
        CHECK (project_id <> '')
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS p6_security_profile_assignments_user
    ON p6_security_profile_assignments (tenant_id, user_id, project_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS p6_security_profile_audit (
        audit_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        actor_user_id TEXT NOT NULL,
        profile_id TEXT NOT NULL,
        action TEXT NOT NULL CHECK (action IN
            ('profile_created','privileges_changed','profile_status_changed',
             'profile_assigned','profile_unassigned')),
        before_state JSONB,
        after_state JSONB NOT NULL,
        occurred_at TIMESTAMPTZ NOT NULL
    )
    """,
    """
    CREATE OR REPLACE FUNCTION cubi_p6_security_profile_audit_immutable()
    RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        RAISE EXCEPTION 'P6_SECURITY_PROFILE_AUDIT_APPEND_ONLY';
    END;
    $$
    """,
    """
    DROP TRIGGER IF EXISTS p6_security_profile_audit_immutable
    ON p6_security_profile_audit
    """,
    """
    CREATE TRIGGER p6_security_profile_audit_immutable
    BEFORE UPDATE OR DELETE ON p6_security_profile_audit
    FOR EACH ROW EXECUTE FUNCTION cubi_p6_security_profile_audit_immutable()
    """,
)


def initialize_security_profile_schema(connection: Any) -> None:
    for statement in SECURITY_PROFILE_SCHEMA:
        connection.execute(statement)


class PostgresSecurityProfileRepository:
    """Tenant-isolated, revision-guarded profile persistence."""

    def __init__(self, connection: Any) -> None:
        self._connection = connection

    def create_profile(
        self, *, tenant_id: str, profile_id: str, name: str, scope: str,
        actor_user_id: str, occurred_at: Any,
    ) -> SecurityProfile:
        if not tenant_id.strip() or not _PROFILE_ID.fullmatch(profile_id):
            raise SecurityProfileError("SECURITY_PROFILE_ID_INVALID")
        if scope not in _PROFILE_SCOPES:
            raise SecurityProfileError("SECURITY_PROFILE_SCOPE_INVALID")
        normalized = name.strip() if isinstance(name, str) else ""
        if not normalized or len(normalized) > 120:
            raise SecurityProfileError("SECURITY_PROFILE_NAME_INVALID")
        self._connection.execute(
            "INSERT INTO p6_security_profiles "
            "(tenant_id,profile_id,name,scope,active,revision,created_by,updated_by,created_at,updated_at) "
            "VALUES (%s,%s,%s,%s,TRUE,1,%s,%s,%s,%s)",
            (tenant_id, profile_id, normalized, scope, actor_user_id,
             actor_user_id, occurred_at, occurred_at),
        )
        self._audit(tenant_id, actor_user_id, profile_id, "profile_created",
                    None, {"name": normalized, "scope": scope, "active": True, "revision": 1},
                    occurred_at)
        return SecurityProfile(tenant_id, profile_id, normalized, scope, True, 1, frozenset())

    def set_privileges(
        self, *, tenant_id: str, profile_id: str, privileges: Iterable[str],
        expected_revision: int, actor_user_id: str, occurred_at: Any,
    ) -> SecurityProfile:
        normalized = frozenset(privileges)
        valid = {permission.value for permission in Permission}
        if not normalized.issubset(valid):
            raise SecurityProfileError("SECURITY_PROFILE_PRIVILEGE_INVALID")
        row = self._connection.execute(
            "SELECT name,scope,active,revision FROM p6_security_profiles "
            "WHERE tenant_id=%s AND profile_id=%s FOR UPDATE",
            (tenant_id, profile_id),
        ).fetchone()
        if row is None:
            raise SecurityProfileError("SECURITY_PROFILE_NOT_FOUND")
        if int(row[3]) != expected_revision:
            raise SecurityProfileError("SECURITY_PROFILE_REVISION_CONFLICT")
        before = self.get_profile(tenant_id, profile_id)
        self._connection.execute(
            "DELETE FROM p6_security_profile_privileges WHERE tenant_id=%s AND profile_id=%s",
            (tenant_id, profile_id),
        )
        for permission in sorted(normalized):
            self._connection.execute(
                "INSERT INTO p6_security_profile_privileges (tenant_id,profile_id,permission) "
                "VALUES (%s,%s,%s)", (tenant_id, profile_id, permission),
            )
        revision = expected_revision + 1
        self._connection.execute(
            "UPDATE p6_security_profiles SET revision=%s,updated_by=%s,updated_at=%s "
            "WHERE tenant_id=%s AND profile_id=%s",
            (revision, actor_user_id, occurred_at, tenant_id, profile_id),
        )
        after = {"name": row[0], "scope": row[1], "active": bool(row[2]),
                 "revision": revision, "privileges": sorted(normalized)}
        self._audit(tenant_id, actor_user_id, profile_id, "privileges_changed",
                    before.as_dict(), after, occurred_at)
        return SecurityProfile(tenant_id, profile_id, row[0], row[1], bool(row[2]),
                               revision, normalized)

    def set_active(
        self, *, tenant_id: str, profile_id: str, active: bool,
        expected_revision: int, actor_user_id: str, occurred_at: Any,
    ) -> SecurityProfile:
        if not isinstance(active, bool):
            raise SecurityProfileError("SECURITY_PROFILE_STATUS_INVALID")
        row = self._connection.execute(
            "SELECT name,scope,active,revision FROM p6_security_profiles "
            "WHERE tenant_id=%s AND profile_id=%s FOR UPDATE",
            (tenant_id, profile_id),
        ).fetchone()
        if row is None:
            raise SecurityProfileError("SECURITY_PROFILE_NOT_FOUND")
        if int(row[3]) != expected_revision:
            raise SecurityProfileError("SECURITY_PROFILE_REVISION_CONFLICT")
        before = self.get_profile(tenant_id, profile_id)
        revision = expected_revision + 1
        self._connection.execute(
            "UPDATE p6_security_profiles SET active=%s,revision=%s,updated_by=%s,updated_at=%s "
            "WHERE tenant_id=%s AND profile_id=%s",
            (active, revision, actor_user_id, occurred_at, tenant_id, profile_id),
        )
        after = {**before.as_dict(), "active": active, "revision": revision}
        self._audit(tenant_id, actor_user_id, profile_id, "profile_status_changed",
                    before.as_dict(), after, occurred_at)
        return SecurityProfile(tenant_id, profile_id, row[0], row[1], active,
                               revision, before.privileges)

    def assign(
        self, *, tenant_id: str, profile_id: str, user_id: str,
        actor_user_id: str, occurred_at: Any, project_id: str = "",
        expected_revision: int | None = None,
    ) -> int:
        profile = self._connection.execute(
            "SELECT scope FROM p6_security_profiles WHERE tenant_id=%s AND profile_id=%s FOR UPDATE",
            (tenant_id, profile_id),
        ).fetchone()
        if profile is None:
            raise SecurityProfileError("SECURITY_PROFILE_NOT_FOUND")
        scope = str(profile[0])
        if (scope == "global" and project_id) or (scope == "project" and not project_id):
            raise SecurityProfileError("SECURITY_PROFILE_ASSIGNMENT_SCOPE_MISMATCH")
        user = self._connection.execute(
            "SELECT tenant_id,active FROM identity_users WHERE user_id=%s",
            (user_id,),
        ).fetchone()
        if user is None or str(user[0]) != tenant_id or not bool(user[1]):
            raise SecurityProfileError("SECURITY_PROFILE_USER_NOT_ELIGIBLE")
        if project_id:
            project = self._connection.execute(
                "SELECT 1 FROM project_lifecycle_projects WHERE tenant_id=%s AND project_id=%s",
                (tenant_id, project_id),
            ).fetchone()
            if project is None:
                raise SecurityProfileError("SECURITY_PROFILE_PROJECT_NOT_FOUND")
        existing = self._connection.execute(
            "SELECT revision FROM p6_security_profile_assignments "
            "WHERE tenant_id=%s AND profile_id=%s AND user_id=%s AND project_id=%s FOR UPDATE",
            (tenant_id, profile_id, user_id, project_id),
        ).fetchone()
        if existing is not None:
            if expected_revision is None or int(existing[0]) != expected_revision:
                raise SecurityProfileError("SECURITY_PROFILE_ASSIGNMENT_REVISION_CONFLICT")
            revision = expected_revision + 1
            self._connection.execute(
                "UPDATE p6_security_profile_assignments SET revision=%s,assigned_by=%s,assigned_at=%s "
                "WHERE tenant_id=%s AND profile_id=%s AND user_id=%s AND project_id=%s",
                (revision, actor_user_id, occurred_at, tenant_id, profile_id, user_id, project_id),
            )
        else:
            if expected_revision not in (None, 0):
                raise SecurityProfileError("SECURITY_PROFILE_ASSIGNMENT_REVISION_CONFLICT")
            revision = 1
            self._connection.execute(
                "INSERT INTO p6_security_profile_assignments "
                "(tenant_id,profile_id,user_id,project_id,revision,assigned_by,assigned_at) "
                "VALUES (%s,%s,%s,%s,1,%s,%s)",
                (tenant_id, profile_id, user_id, project_id, actor_user_id, occurred_at),
            )
        self._audit(tenant_id, actor_user_id, profile_id, "profile_assigned", None,
                    {"user_id": user_id, "project_id": project_id, "revision": revision},
                    occurred_at)
        return revision

    def unassign(
        self, *, tenant_id: str, profile_id: str, user_id: str,
        project_id: str = "", expected_revision: int,
        actor_user_id: str, occurred_at: Any,
    ) -> None:
        result = self._connection.execute(
            "DELETE FROM p6_security_profile_assignments "
            "WHERE tenant_id=%s AND profile_id=%s AND user_id=%s AND project_id=%s AND revision=%s "
            "RETURNING revision",
            (tenant_id, profile_id, user_id, project_id, expected_revision),
        ).fetchone()
        if result is None:
            raise SecurityProfileError("SECURITY_PROFILE_ASSIGNMENT_REVISION_CONFLICT")
        self._audit(tenant_id, actor_user_id, profile_id, "profile_unassigned",
                    {"user_id": user_id, "project_id": project_id, "revision": expected_revision},
                    {"unassigned": True}, occurred_at)

    def get_profile(self, tenant_id: str, profile_id: str) -> SecurityProfile:
        row = self._connection.execute(
            "SELECT name,scope,active,revision FROM p6_security_profiles "
            "WHERE tenant_id=%s AND profile_id=%s",
            (tenant_id, profile_id),
        ).fetchone()
        if row is None:
            raise SecurityProfileError("SECURITY_PROFILE_NOT_FOUND")
        grants = self._connection.execute(
            "SELECT permission FROM p6_security_profile_privileges "
            "WHERE tenant_id=%s AND profile_id=%s ORDER BY permission",
            (tenant_id, profile_id),
        ).fetchall()
        return SecurityProfile(tenant_id, profile_id, row[0], row[1], bool(row[2]),
                               int(row[3]), frozenset(str(item[0]) for item in grants))

    def list_profiles(self, tenant_id: str, scope: str | None = None) -> tuple[SecurityProfile, ...]:
        if scope is not None and scope not in _PROFILE_SCOPES:
            raise SecurityProfileError("SECURITY_PROFILE_SCOPE_INVALID")
        params: tuple[Any, ...] = (tenant_id,) if scope is None else (tenant_id, scope)
        where = "tenant_id=%s" if scope is None else "tenant_id=%s AND scope=%s"
        rows = self._connection.execute(
            f"SELECT profile_id FROM p6_security_profiles WHERE {where} ORDER BY scope,name",
            params,
        ).fetchall()
        return tuple(self.get_profile(tenant_id, str(row[0])) for row in rows)

    def _audit(self, tenant_id: str, actor_id: str, profile_id: str,
               action: str, before: Any, after: Any, occurred_at: Any) -> None:
        import uuid
        self._connection.execute(
            "INSERT INTO p6_security_profile_audit "
            "(audit_id,tenant_id,actor_user_id,profile_id,action,before_state,after_state,occurred_at) "
            "VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s)",
            (str(uuid.uuid4()), tenant_id, actor_id, profile_id, action,
             None if before is None else json.dumps(before, sort_keys=True),
             json.dumps(after, sort_keys=True), occurred_at),
        )


class PostgresSecurityProfileAuthorizationPolicy:
    """Role ceiling plus assigned global/project profile intersections."""

    def __init__(self, connection: Any, role_policy: RoleBasedAuthorizationPolicy) -> None:
        self._connection = connection
        self._role_policy = role_policy

    def is_allowed(self, context: AuthorizationContext, permission: Permission) -> bool:
        context.validate()
        if not self._role_policy.is_allowed(context, permission):
            return False
        rows = self._connection.execute(
            "SELECT p.scope,p.active,g.permission FROM p6_security_profile_assignments a "
            "JOIN p6_security_profiles p ON p.tenant_id=a.tenant_id AND p.profile_id=a.profile_id "
            "LEFT JOIN p6_security_profile_privileges g "
            "ON g.tenant_id=p.tenant_id AND g.profile_id=p.profile_id "
            "AND g.permission=%s "
            "WHERE a.tenant_id=%s AND a.user_id=%s "
            "AND ((p.scope='global' AND a.project_id='') "
            "OR (p.scope='project' AND a.project_id=%s))",
            (permission.value, context.tenant_id, context.user_id, context.project_id),
        ).fetchall()
        global_rows = [row for row in rows if str(row[0]) == "global"]
        project_rows = [row for row in rows if str(row[0]) == "project"]
        if global_rows and not any(bool(row[1]) and row[2] == permission.value for row in global_rows):
            return False
        if project_rows and not any(bool(row[1]) and row[2] == permission.value for row in project_rows):
            return False
        return True

    def require(self, context: AuthorizationContext, permission: Permission) -> None:
        from .application.authorization import AuthorizationError
        if not self.is_allowed(context, permission):
            raise AuthorizationError(f"authorization denied for permission={permission.value}")
