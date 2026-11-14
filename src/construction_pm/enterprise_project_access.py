from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import uuid4

from .application.authorization import AuthorizationContext, Permission, RoleBasedAuthorizationPolicy
from .application.project_lifecycle import ProjectLifecycleError, SessionError

PROJECT_PERMISSION_CODES = frozenset(item.value for item in Permission)
PROFILE_ID_MAX = 120


class ProjectAccessError(ValueError):
    pass


class ProjectAccessDenied(PermissionError):
    pass


@dataclass(frozen=True)
class ProjectSecurityProfile:
    tenant_id: str
    profile_id: str
    name: str
    permissions: tuple[str, ...]
    active: bool
    revision: int
    created_at: datetime

    def validate(self) -> None:
        if not self.tenant_id.strip() or not self.profile_id.strip() or not self.name.strip():
            raise ProjectAccessError("PROJECT_SECURITY_PROFILE_REQUIRED")
        if len(self.profile_id) > PROFILE_ID_MAX or len(self.name) > 160:
            raise ProjectAccessError("PROJECT_SECURITY_PROFILE_INVALID")
        if len(set(self.permissions)) != len(self.permissions):
            raise ProjectAccessError("PROJECT_SECURITY_PROFILE_DUPLICATE_PERMISSION")
        if any(value not in PROJECT_PERMISSION_CODES for value in self.permissions):
            raise ProjectAccessError("PROJECT_SECURITY_PROFILE_PERMISSION_INVALID")
        if self.revision < 1 or self.created_at.tzinfo is None:
            raise ProjectAccessError("PROJECT_SECURITY_PROFILE_REVISION_INVALID")


@dataclass(frozen=True)
class UserOBSAssignment:
    tenant_id: str
    user_id: str
    obs_id: str
    profile_id: str
    active: bool
    revision: int
    assigned_by: str
    assigned_at: datetime

    def validate(self) -> None:
        for value in (self.tenant_id, self.user_id, self.obs_id, self.profile_id, self.assigned_by):
            if not isinstance(value, str) or not value.strip():
                raise ProjectAccessError("USER_OBS_ASSIGNMENT_REQUIRED")
        if self.revision < 1 or self.assigned_at.tzinfo is None:
            raise ProjectAccessError("USER_OBS_ASSIGNMENT_REVISION_INVALID")


class ProjectAccessRepository(Protocol):
    def create_profile(self, profile: ProjectSecurityProfile, actor_id: str) -> ProjectSecurityProfile: ...
    def get_profile(self, tenant_id: str, profile_id: str) -> ProjectSecurityProfile | None: ...
    def assign_user_obs(self, assignment: UserOBSAssignment) -> UserOBSAssignment: ...
    def revoke_user_obs(self, tenant_id: str, user_id: str, obs_id: str, profile_id: str, actor_id: str, expected_revision: int, at: datetime) -> UserOBSAssignment: ...
    def list_user_obs(self, tenant_id: str, user_id: str) -> tuple[UserOBSAssignment, ...]: ...
    def project_permission(self, tenant_id: str, user_id: str, project_id: str, permission: str) -> bool: ...


class PostgresProjectAccessRepository:
    """P6-style user↔OBS↔project-profile access with append-only audit."""

    def __init__(self, connection: Any) -> None:
        self.connection = connection

    def initialize(self) -> None:
        statements = (
            """CREATE TABLE IF NOT EXISTS enterprise_project_security_profiles (
                tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL,
                name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 160),
                permissions JSONB NOT NULL CHECK(jsonb_typeof(permissions)='array'),
                active BOOLEAN NOT NULL DEFAULT TRUE, revision BIGINT NOT NULL CHECK(revision >= 1),
                created_by TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL,
                PRIMARY KEY(tenant_id,profile_id))""",
            """CREATE TABLE IF NOT EXISTS enterprise_user_obs_assignments (
                tenant_id TEXT NOT NULL, user_id TEXT NOT NULL, obs_id TEXT NOT NULL,
                profile_id TEXT NOT NULL, active BOOLEAN NOT NULL DEFAULT TRUE,
                revision BIGINT NOT NULL CHECK(revision >= 1), assigned_by TEXT NOT NULL,
                assigned_at TIMESTAMPTZ NOT NULL,
                PRIMARY KEY(tenant_id,user_id,obs_id,profile_id),
                FOREIGN KEY(tenant_id,profile_id) REFERENCES enterprise_project_security_profiles(tenant_id,profile_id),
                FOREIGN KEY(tenant_id,obs_id) REFERENCES p6_obs_node(tenant_id,obs_id))""",
            """CREATE INDEX IF NOT EXISTS enterprise_user_obs_active_idx
                ON enterprise_user_obs_assignments(tenant_id,user_id,active,obs_id)""",
            """CREATE TABLE IF NOT EXISTS enterprise_project_access_audit (
                audit_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, actor_id TEXT NOT NULL,
                target_user_id TEXT NOT NULL, obs_id TEXT NOT NULL, profile_id TEXT NOT NULL,
                action TEXT NOT NULL CHECK(action IN ('profile_created','obs_assigned','obs_revoked')),
                before_state JSONB, after_state JSONB NOT NULL, occurred_at TIMESTAMPTZ NOT NULL)""",
            """CREATE OR REPLACE FUNCTION cubi_project_access_audit_immutable()
                RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN RAISE EXCEPTION 'PROJECT_ACCESS_AUDIT_APPEND_ONLY'; END; $$""",
            """DROP TRIGGER IF EXISTS enterprise_project_access_audit_immutable
                ON enterprise_project_access_audit""",
            """CREATE TRIGGER enterprise_project_access_audit_immutable
                BEFORE UPDATE OR DELETE ON enterprise_project_access_audit
                FOR EACH ROW EXECUTE FUNCTION cubi_project_access_audit_immutable()""",
        )
        for statement in statements:
            self.connection.execute(statement)

    def create_profile(self, profile: ProjectSecurityProfile, actor_id: str) -> ProjectSecurityProfile:
        profile.validate()
        self.connection.execute(
            """INSERT INTO enterprise_project_security_profiles
               (tenant_id,profile_id,name,permissions,active,revision,created_by,created_at)
               VALUES(%s,%s,%s,%s::jsonb,%s,%s,%s,%s)""",
            (profile.tenant_id, profile.profile_id, profile.name,
             json.dumps(list(profile.permissions)), profile.active, profile.revision,
             actor_id, profile.created_at),
        )
        self._audit(profile.tenant_id, actor_id, actor_id, "", profile.profile_id,
                    "profile_created", None, {"name": profile.name,
                    "permissions": list(profile.permissions), "revision": profile.revision},
                    profile.created_at)
        return profile

    def get_profile(self, tenant_id: str, profile_id: str) -> ProjectSecurityProfile | None:
        row = self.connection.execute(
            """SELECT tenant_id,profile_id,name,permissions,active,revision,created_at
               FROM enterprise_project_security_profiles WHERE tenant_id=%s AND profile_id=%s""",
            (tenant_id, profile_id),
        ).fetchone()
        if row is None:
            return None
        permissions = row[3] if not isinstance(row[3], str) else json.loads(row[3])
        result = ProjectSecurityProfile(str(row[0]), str(row[1]), str(row[2]),
            tuple(permissions or ()), bool(row[4]), int(row[5]), row[6])
        result.validate()
        return result

    def assign_user_obs(self, assignment: UserOBSAssignment) -> UserOBSAssignment:
        assignment.validate()
        user = self.connection.execute(
            "SELECT tenant_id,active FROM identity_users WHERE user_id=%s",
            (assignment.user_id,),
        ).fetchone()
        if user is None or str(user[0]) != assignment.tenant_id or not bool(user[1]):
            raise ProjectAccessError("PROJECT_ACCESS_USER_NOT_FOUND")
        profile = self.get_profile(assignment.tenant_id, assignment.profile_id)
        if profile is None or not profile.active:
            raise ProjectAccessError("PROJECT_SECURITY_PROFILE_NOT_FOUND")
        obs = self.connection.execute(
            "SELECT 1 FROM p6_obs_node WHERE tenant_id=%s AND obs_id=%s",
            (assignment.tenant_id, assignment.obs_id),
        ).fetchone()
        if obs is None:
            raise ProjectAccessError("PROJECT_ACCESS_OBS_NOT_FOUND")
        self.connection.execute(
            """INSERT INTO enterprise_user_obs_assignments
               (tenant_id,user_id,obs_id,profile_id,active,revision,assigned_by,assigned_at)
               VALUES(%s,%s,%s,%s,TRUE,%s,%s,%s)
               ON CONFLICT(tenant_id,user_id,obs_id,profile_id) DO UPDATE SET
               active=TRUE,revision=enterprise_user_obs_assignments.revision+1,
               assigned_by=EXCLUDED.assigned_by,assigned_at=EXCLUDED.assigned_at""",
            (assignment.tenant_id, assignment.user_id, assignment.obs_id,
             assignment.profile_id, assignment.revision, assignment.assigned_by,
             assignment.assigned_at),
        )
        row = self.connection.execute(
            """SELECT tenant_id,user_id,obs_id,profile_id,active,revision,assigned_by,assigned_at
               FROM enterprise_user_obs_assignments
               WHERE tenant_id=%s AND user_id=%s AND obs_id=%s AND profile_id=%s""",
            (assignment.tenant_id, assignment.user_id, assignment.obs_id, assignment.profile_id),
        ).fetchone()
        saved = self._assignment(row)
        self._audit(saved.tenant_id, saved.assigned_by, saved.user_id, saved.obs_id,
                    saved.profile_id, "obs_assigned", None, self._assignment_json(saved),
                    saved.assigned_at)
        return saved

    def revoke_user_obs(self, tenant_id: str, user_id: str, obs_id: str, profile_id: str,
                        actor_id: str, expected_revision: int, at: datetime) -> UserOBSAssignment:
        row = self.connection.execute(
            """UPDATE enterprise_user_obs_assignments SET active=FALSE,revision=revision+1
               WHERE tenant_id=%s AND user_id=%s AND obs_id=%s AND profile_id=%s
                 AND active=TRUE AND revision=%s
               RETURNING tenant_id,user_id,obs_id,profile_id,active,revision,assigned_by,assigned_at""",
            (tenant_id, user_id, obs_id, profile_id, expected_revision),
        ).fetchone()
        if row is None:
            raise ProjectAccessError("PROJECT_ACCESS_REVISION_CONFLICT_OR_NOT_FOUND")
        saved = self._assignment(row)
        self._audit(tenant_id, actor_id, user_id, obs_id, profile_id, "obs_revoked",
                    {"active": True, "revision": expected_revision},
                    self._assignment_json(saved), at)
        return saved

    def list_user_obs(self, tenant_id: str, user_id: str) -> tuple[UserOBSAssignment, ...]:
        rows = self.connection.execute(
            """SELECT tenant_id,user_id,obs_id,profile_id,active,revision,assigned_by,assigned_at
               FROM enterprise_user_obs_assignments WHERE tenant_id=%s AND user_id=%s
               ORDER BY obs_id,profile_id""", (tenant_id, user_id)
        ).fetchall()
        return tuple(self._assignment(row) for row in rows)

    def project_permission(self, tenant_id: str, user_id: str, project_id: str, permission: str) -> bool:
        row = self.connection.execute(
            """WITH RECURSIVE project_obs(obs_id,parent_obs_id) AS (
                   SELECT o.obs_id,o.parent_obs_id FROM project_lifecycle_projects p
                   JOIN p6_obs_node o ON o.tenant_id=p.tenant_id AND o.obs_id=p.obs_id
                   WHERE p.tenant_id=%s AND p.project_id=%s
                   UNION ALL
                   SELECT parent.obs_id,parent.parent_obs_id FROM p6_obs_node parent
                   JOIN project_obs child ON child.parent_obs_id=parent.obs_id
                   WHERE parent.tenant_id=%s
               )
               SELECT 1 FROM project_obs po
               JOIN enterprise_user_obs_assignments a ON a.tenant_id=%s
                    AND a.user_id=%s AND a.obs_id=po.obs_id AND a.active=TRUE
               JOIN enterprise_project_security_profiles sp ON sp.tenant_id=a.tenant_id
                    AND sp.profile_id=a.profile_id AND sp.active=TRUE
               WHERE sp.permissions ? %s LIMIT 1""",
            (tenant_id, project_id, tenant_id, tenant_id, user_id, permission),
        ).fetchone()
        return row is not None

    def _audit(self, tenant_id: str, actor_id: str, target_id: str, obs_id: str,
               profile_id: str, action: str, before: dict | None, after: dict,
               occurred_at: datetime) -> None:
        self.connection.execute(
            """INSERT INTO enterprise_project_access_audit
               (audit_id,tenant_id,actor_id,target_user_id,obs_id,profile_id,action,
                before_state,after_state,occurred_at)
               VALUES(%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s)""",
            (f"project-access-{uuid4().hex}", tenant_id, actor_id, target_id, obs_id,
             profile_id, action, json.dumps(before) if before is not None else None,
             json.dumps(after), occurred_at),
        )

    @staticmethod
    def _assignment(row: Any) -> UserOBSAssignment:
        return UserOBSAssignment(str(row[0]),str(row[1]),str(row[2]),str(row[3]),
            bool(row[4]),int(row[5]),str(row[6]),row[7])

    @staticmethod
    def _assignment_json(item: UserOBSAssignment) -> dict[str, Any]:
        return {"user_id":item.user_id,"obs_id":item.obs_id,"profile_id":item.profile_id,
                "active":item.active,"revision":item.revision}


class EnterpriseProjectAccessService:
    def __init__(self, repository: ProjectAccessRepository, lifecycle: Any, obs_lookup: Any,
                 *, clock=None) -> None:
        self.repository = repository
        self.lifecycle = lifecycle
        self.obs_lookup = obs_lookup
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def create_profile(self, session_id: str, profile_id: str, name: str,
                       permissions: tuple[str, ...]) -> ProjectSecurityProfile:
        session = self._admin_session(session_id)
        profile = ProjectSecurityProfile(session.tenant_id, profile_id.strip(), name.strip(),
            tuple(dict.fromkeys(permissions)), True, 1, self._now())
        profile.validate()
        return self.repository.create_profile(profile, session.user_id)

    def assign_user_obs(self, session_id: str, user_id: str, obs_id: str,
                        profile_id: str) -> UserOBSAssignment:
        session = self._admin_session(session_id)
        if not self.obs_lookup.obs_node_exists(session.tenant_id, obs_id):
            raise ProjectAccessError("PROJECT_ACCESS_OBS_NOT_FOUND")
        assignment = UserOBSAssignment(session.tenant_id, user_id, obs_id, profile_id,
            True, 1, session.user_id, self._now())
        return self.repository.assign_user_obs(assignment)

    def revoke_user_obs(self, session_id: str, user_id: str, obs_id: str,
                        profile_id: str, expected_revision: int) -> UserOBSAssignment:
        session = self._admin_session(session_id)
        return self.repository.revoke_user_obs(session.tenant_id, user_id, obs_id,
            profile_id, session.user_id, expected_revision, self._now())

    def list_user_obs(self, session_id: str, user_id: str) -> tuple[UserOBSAssignment, ...]:
        session = self._admin_session(session_id)
        return self.repository.list_user_obs(session.tenant_id, user_id)

    def _admin_session(self, session_id: str):
        if not isinstance(session_id, str) or not session_id:
            raise ProjectAccessDenied("SESSION_REQUIRED")
        try:
            session = self.lifecycle.get_session(session_id, now=self._now())
        except (ProjectLifecycleError, SessionError) as exc:
            raise ProjectAccessDenied("SESSION_REQUIRED") from exc
        if session is None or "enterprise_admin" not in session.roles:
            raise ProjectAccessDenied("ENTERPRISE_ADMIN_REQUIRED")
        return session

    def _now(self) -> datetime:
        now = self.clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ProjectAccessError("NOW_MUST_BE_TIMEZONE_AWARE")
        return now.astimezone(timezone.utc)


class EnterpriseProjectAuthorizationPolicy:
    """Combines global role grants with project-specific OBS profile grants.

    Existing direct project memberships remain valid. An OBS assignment is an
    additional route to project access, never a side effect of team membership.
    """

    def __init__(self, role_policy: RoleBasedAuthorizationPolicy,
                 project_access: ProjectAccessRepository, connection: Any) -> None:
        self.role_policy = role_policy
        self.project_access = project_access
        self.connection = connection

    def is_allowed(self, context: AuthorizationContext, permission: Permission) -> bool:
        if not self.role_policy.is_allowed(context, permission):
            return False
        direct = self.connection.execute(
            """SELECT 1 FROM project_lifecycle_memberships
               WHERE tenant_id=%s AND project_id=%s AND user_id=%s""",
            (context.tenant_id, context.project_id, context.user_id),
        ).fetchone()
        if direct is not None:
            return True
        return self.project_access.project_permission(
            context.tenant_id, context.user_id, context.project_id, permission.value
        )


__all__ = [
    "EnterpriseProjectAccessService", "EnterpriseProjectAuthorizationPolicy",
    "PostgresProjectAccessRepository", "ProjectAccessDenied", "ProjectAccessError",
    "ProjectSecurityProfile", "UserOBSAssignment",
]
