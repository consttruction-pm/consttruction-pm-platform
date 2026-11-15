from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import uuid4

from .application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    Permission,
    RoleBasedAuthorizationPolicy,
)
from .application.project_lifecycle import ProjectLifecycleError, SessionError
from .p6_project_privileges import PROJECT_PRIVILEGES, normalize_project_privileges

PROJECT_PERMISSION_CODES = frozenset({
    Permission.PROJECT_READ.value,
    Permission.PROJECT_WRITE.value,
    Permission.PROJECT_SCHEDULE.value,
    Permission.PROJECT_ADMIN.value,
})
PROFILE_ID_MAX = 120

# CUBI operation keys are deliberately mapped to the corresponding Oracle V26
# checkbox keys. This is an explicit adapter, not a wildcard or role bypass.
PROJECT_PROFILE_ROUTE_ALIASES: dict[str, frozenset[str]] = {
    "project.read": frozenset({"project.view"}),
    "project.write": frozenset({"project.edit_details_except_costs_financials"}),
    "project.schedule": frozenset({"schedule.run"}),
    "activity.add_edit": frozenset({"activity.add_edit_except_relationships"}),
    "expense.add_edit": frozenset({"expense.add_edit_delete"}),
    "issue.add_edit": frozenset({"issue_threshold.add_edit_delete"}),
    "issue.edit": frozenset({"issue_threshold.add_edit_delete"}),
    "issue.delete": frozenset({"issue_threshold.add_edit_delete"}),
    "risk.add_edit": frozenset({"risk.add_edit_delete"}),
    "risk.edit": frozenset({"risk.add_edit_delete"}),
    "risk.delete": frozenset({"risk.add_edit_delete"}),
    "threshold.add_edit": frozenset({"issue_threshold.add_edit_delete"}),
    "threshold.edit": frozenset({"issue_threshold.add_edit_delete"}),
    "threshold.delete": frozenset({"issue_threshold.add_edit_delete"}),
    "baseline.create_update": frozenset({"project_baseline.add_edit_delete"}),
    "baseline.update": frozenset({"baseline.update"}),
    "wbs.add_edit": frozenset({"wbs.add_edit_delete_except_costs_financials"}),
    "wbs.edit": frozenset({"wbs.add_edit_delete_except_costs_financials"}),
    "wbs.delete": frozenset({"wbs.add_edit_delete_except_costs_financials"}),
}

PROJECT_PROFILE_ROUTE_REQUIRED_ALL: dict[str, frozenset[str]] = {
    # V26 explicitly requires both Assign Project Baselines and
    # Edit Project Details Except Costs/Financials.
    "baseline.assign": frozenset({
        "project_baseline.assign",
        "project.edit_details_except_costs_financials",
    }),
}


def project_profile_has_permission(
    permissions: tuple[str, ...] | list[str] | set[str] | frozenset[str],
    permission: str,
) -> bool:
    """Resolve one CUBI route grant against explicit Oracle V26 profile options."""
    grants = frozenset(permissions)
    required_all = PROJECT_PROFILE_ROUTE_REQUIRED_ALL.get(permission)
    if required_all is not None:
        return required_all <= grants
    return permission in grants or bool(
        PROJECT_PROFILE_ROUTE_ALIASES.get(permission, frozenset()) & grants
    )



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
        if not all(isinstance(value, str) and value.strip()
                   for value in (self.tenant_id, self.profile_id, self.name)):
            raise ProjectAccessError("PROJECT_SECURITY_PROFILE_REQUIRED")
        if len(self.profile_id) > PROFILE_ID_MAX or len(self.name) > 160:
            raise ProjectAccessError("PROJECT_SECURITY_PROFILE_INVALID")
        try:
            normalized = normalize_project_privileges(self.permissions)
        except ValueError as exc:
            raise ProjectAccessError("PROJECT_SECURITY_PROFILE_PERMISSION_INVALID") from exc
        if normalized != tuple(sorted(self.permissions)):
            raise ProjectAccessError("PROJECT_SECURITY_PROFILE_PERMISSION_NOT_NORMALIZED")
        if self.revision < 1 or self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
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
        if self.revision < 1 or self.assigned_at.tzinfo is None or self.assigned_at.utcoffset() is None:
            raise ProjectAccessError("USER_OBS_ASSIGNMENT_REVISION_INVALID")


class ProjectAccessRepository(Protocol):
    def create_profile(self, profile: ProjectSecurityProfile, actor_id: str) -> ProjectSecurityProfile: ...
    def get_profile(self, tenant_id: str, profile_id: str) -> ProjectSecurityProfile | None: ...
    def list_profiles(self, tenant_id: str) -> tuple[ProjectSecurityProfile, ...]: ...
    def assign_user_obs(self, assignment: UserOBSAssignment) -> UserOBSAssignment: ...
    def revoke_user_obs(self, tenant_id: str, user_id: str, obs_id: str, profile_id: str,
                        actor_id: str, expected_revision: int, at: datetime) -> UserOBSAssignment: ...
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
                FOREIGN KEY(tenant_id,profile_id)
                    REFERENCES enterprise_project_security_profiles(tenant_id,profile_id),
                FOREIGN KEY(tenant_id,obs_id)
                    REFERENCES p6_obs_node(tenant_id,obs_id))""",
            """CREATE INDEX IF NOT EXISTS enterprise_user_obs_active_idx
                ON enterprise_user_obs_assignments(tenant_id,user_id,active,obs_id)""",
            """CREATE TABLE IF NOT EXISTS enterprise_project_access_audit (
                audit_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, actor_id TEXT NOT NULL,
                target_user_id TEXT NOT NULL, obs_id TEXT NOT NULL, profile_id TEXT NOT NULL,
                action TEXT NOT NULL CHECK(action IN ('profile_created','obs_assigned','obs_revoked')),
                before_state JSONB, after_state JSONB NOT NULL, occurred_at TIMESTAMPTZ NOT NULL)""",
            """CREATE OR REPLACE FUNCTION cubi_project_profile_has_privilege(
                    p_permissions JSONB,p_permission TEXT)
                RETURNS BOOLEAN LANGUAGE SQL IMMUTABLE AS $cubi$
                SELECT CASE p_permission
                    WHEN 'project.read' THEN p_permissions ?| ARRAY['project.read','project.view']
                    WHEN 'project.write' THEN p_permissions ?| ARRAY['project.write','project.edit_details_except_costs_financials']
                    WHEN 'project.schedule' THEN p_permissions ?| ARRAY['project.schedule','schedule.run']
                    WHEN 'activity.add_edit' THEN p_permissions ?| ARRAY['activity.add_edit','activity.add_edit_except_relationships']
                    WHEN 'expense.add_edit' THEN p_permissions ?| ARRAY['expense.add_edit','expense.add_edit_delete']
                    WHEN 'issue.add_edit' THEN p_permissions ?| ARRAY['issue.add_edit','issue_threshold.add_edit_delete']
                    WHEN 'issue.edit' THEN p_permissions ?| ARRAY['issue.edit','issue_threshold.add_edit_delete']
                    WHEN 'issue.delete' THEN p_permissions ?| ARRAY['issue.delete','issue_threshold.add_edit_delete']
                    WHEN 'risk.add_edit' THEN p_permissions ?| ARRAY['risk.add_edit','risk.add_edit_delete']
                    WHEN 'risk.edit' THEN p_permissions ?| ARRAY['risk.edit','risk.add_edit_delete']
                    WHEN 'risk.delete' THEN p_permissions ?| ARRAY['risk.delete','risk.add_edit_delete']
                    WHEN 'threshold.add_edit' THEN p_permissions ?| ARRAY['threshold.add_edit','issue_threshold.add_edit_delete']
                    WHEN 'threshold.edit' THEN p_permissions ?| ARRAY['threshold.edit','issue_threshold.add_edit_delete']
                    WHEN 'threshold.delete' THEN p_permissions ?| ARRAY['threshold.delete','issue_threshold.add_edit_delete']
                    WHEN 'baseline.create_update' THEN p_permissions ?| ARRAY['baseline.create_update','project_baseline.add_edit_delete']
                    WHEN 'baseline.assign' THEN p_permissions ? 'project_baseline.assign' AND p_permissions ? 'project.edit_details_except_costs_financials'
                    WHEN 'wbs.add_edit' THEN p_permissions ?| ARRAY['wbs.add_edit','wbs.add_edit_delete_except_costs_financials']
                    WHEN 'wbs.edit' THEN p_permissions ?| ARRAY['wbs.edit','wbs.add_edit_delete_except_costs_financials']
                    WHEN 'wbs.delete' THEN p_permissions ?| ARRAY['wbs.delete','wbs.add_edit_delete_except_costs_financials']
                    ELSE p_permissions ? p_permission
                END
                $cubi$""",
            """CREATE OR REPLACE FUNCTION cubi_user_has_project_access(
                    p_tenant_id TEXT,p_user_id TEXT,p_project_id TEXT,p_permission TEXT)
                RETURNS BOOLEAN LANGUAGE SQL STABLE AS $$
                WITH RECURSIVE project_obs(obs_id,parent_obs_id,path) AS (
                    SELECT o.obs_id,o.parent_obs_id,ARRAY[o.obs_id]::text[]
                    FROM project_lifecycle_projects p
                    JOIN p6_obs_node o ON o.tenant_id=p.tenant_id AND o.obs_id=p.obs_id
                    WHERE p.tenant_id=p_tenant_id AND p.project_id=p_project_id
                    UNION ALL
                    SELECT parent.obs_id,parent.parent_obs_id,po.path || parent.obs_id
                    FROM project_obs po
                    JOIN p6_obs_node parent ON parent.obs_id=po.parent_obs_id
                    WHERE parent.tenant_id=p_tenant_id AND NOT parent.obs_id=ANY(po.path)
                )
                SELECT EXISTS(SELECT 1 FROM project_obs po
                    JOIN enterprise_user_obs_assignments a ON a.tenant_id=p_tenant_id
                        AND a.user_id=p_user_id AND a.obs_id=po.obs_id AND a.active=TRUE
                    JOIN enterprise_project_security_profiles sp ON sp.tenant_id=a.tenant_id
                        AND sp.profile_id=a.profile_id AND sp.active=TRUE
                    WHERE cubi_project_profile_has_privilege(sp.permissions,p_permission))
                $$""",
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
        profile = ProjectSecurityProfile(str(row[0]), str(row[1]), str(row[2]),
            tuple(permissions or ()), bool(row[4]), int(row[5]), row[6])
        profile.validate()
        return profile

    def list_profiles(self, tenant_id: str) -> tuple[ProjectSecurityProfile, ...]:
        rows = self.connection.execute(
            """SELECT tenant_id,profile_id,name,permissions,active,revision,created_at
               FROM enterprise_project_security_profiles WHERE tenant_id=%s
               ORDER BY name,profile_id""", (tenant_id,)
        ).fetchall()
        profiles=[]
        for row in rows:
            permissions = row[3] if not isinstance(row[3], str) else json.loads(row[3])
            profile = ProjectSecurityProfile(str(row[0]),str(row[1]),str(row[2]),
                tuple(permissions or ()),bool(row[4]),int(row[5]),row[6])
            profile.validate()
            profiles.append(profile)
        return tuple(profiles)

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
            "SELECT cubi_user_has_project_access(%s::text,%s::text,%s::text,%s::text)",
            (tenant_id, user_id, project_id, permission),
        ).fetchone()
        return bool(row and row[0])

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
        return UserOBSAssignment(str(row[0]), str(row[1]), str(row[2]), str(row[3]),
            bool(row[4]), int(row[5]), str(row[6]), row[7])

    @staticmethod
    def _assignment_json(item: UserOBSAssignment) -> dict[str, Any]:
        return {"user_id": item.user_id, "obs_id": item.obs_id,
                "profile_id": item.profile_id, "active": item.active,
                "revision": item.revision}


class EnterpriseProjectAccessService:
    def __init__(self, repository: ProjectAccessRepository, lifecycle: Any,
                 obs_lookup: Any, *, clock=None) -> None:
        self.repository = repository
        self.lifecycle = lifecycle
        self.obs_lookup = obs_lookup
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def create_profile(self, session_id: str, profile_id: str, name: str,
                       permissions: tuple[str, ...]) -> ProjectSecurityProfile:
        session = self._admin_session(session_id)
        try:
            normalized_permissions = normalize_project_privileges(permissions)
        except ValueError as exc:
            raise ProjectAccessError("PROJECT_SECURITY_PROFILE_PERMISSION_INVALID") from exc
        profile = ProjectSecurityProfile(session.tenant_id, profile_id.strip(), name.strip(),
            normalized_permissions, True, 1, self._now())
        profile.validate()
        return self.repository.create_profile(profile, session.user_id)

    def list_profiles(self, session_id: str) -> tuple[ProjectSecurityProfile, ...]:
        session = self._admin_session(session_id)
        return self.repository.list_profiles(session.tenant_id)

    def list_privilege_definitions(self, session_id: str):
        self._admin_session(session_id)
        return PROJECT_PRIVILEGES

    def list_obs_nodes(self, session_id: str):
        session = self._admin_session(session_id)
        return self.obs_lookup.list(session.tenant_id)

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
    """Global/module grants AND explicit project-level OBS profile grants."""

    def __init__(self, role_policy: RoleBasedAuthorizationPolicy,
                 project_access: ProjectAccessRepository, connection: Any) -> None:
        self.role_policy = role_policy
        self.project_access = project_access
        self.connection = connection

    def is_allowed(self, context: AuthorizationContext, permission: Permission) -> bool:
        if not self.role_policy.is_allowed(context, permission):
            return False
        exists = self.connection.execute(
            "SELECT 1 FROM project_lifecycle_projects WHERE tenant_id=%s AND project_id=%s",
            (context.tenant_id, context.project_id),
        ).fetchone()
        if exists is None and permission == Permission.PROJECT_ADMIN:
            # Project creation is authorized before the new project/member rows exist.
            return True
        if self.project_access.project_permission(
            context.tenant_id, context.user_id, context.project_id, permission.value
        ):
            return True
        # Transitional compatibility is deliberately one-way: old broad
        # project.read/write grants continue to work, while granular-only
        # profiles are evaluated against the exact operation privilege above.
        legacy = {
            Permission.ACTIVITY_VIEW: Permission.PROJECT_READ,
            Permission.ACTIVITY_ADD_EDIT: Permission.PROJECT_WRITE,
            Permission.ACTIVITY_EDIT: Permission.PROJECT_WRITE,
            Permission.ACTIVITY_DELETE: Permission.PROJECT_WRITE,
            Permission.ACTIVITY_RELATIONSHIP_MANAGE: Permission.PROJECT_WRITE,
            Permission.ISSUE_VIEW: Permission.PROJECT_READ,
            Permission.ISSUE_ADD_EDIT: Permission.PROJECT_WRITE,
            Permission.ISSUE_EDIT: Permission.PROJECT_WRITE,
            Permission.ISSUE_DELETE: Permission.PROJECT_WRITE,
            Permission.EXPENSE_VIEW: Permission.PROJECT_READ,
            Permission.EXPENSE_ADD_EDIT: Permission.PROJECT_WRITE,
            Permission.RISK_VIEW: Permission.PROJECT_READ,
            Permission.RISK_ADD_EDIT: Permission.PROJECT_WRITE,
            Permission.RISK_EDIT: Permission.PROJECT_WRITE,
            Permission.RISK_DELETE: Permission.PROJECT_WRITE,
            Permission.THRESHOLD_VIEW: Permission.PROJECT_READ,
            Permission.THRESHOLD_ADD_EDIT: Permission.PROJECT_WRITE,
            Permission.THRESHOLD_EDIT: Permission.PROJECT_WRITE,
            Permission.THRESHOLD_DELETE: Permission.PROJECT_WRITE,
            Permission.THRESHOLD_MONITOR: Permission.PROJECT_WRITE,
            Permission.BASELINE_VIEW: Permission.PROJECT_READ,
            Permission.BASELINE_CREATE_UPDATE: Permission.PROJECT_WRITE,
            Permission.WBS_VIEW: Permission.PROJECT_READ,
            Permission.WBS_EDIT: Permission.PROJECT_WRITE,
            Permission.WBS_ADD_EDIT: Permission.PROJECT_WRITE,
            Permission.WBS_DELETE: Permission.PROJECT_WRITE,
        }.get(permission)
        return False if legacy is None else self.project_access.project_permission(
            context.tenant_id, context.user_id, context.project_id, legacy.value
        )

    def require(self, context: AuthorizationContext, permission: Permission) -> None:
        if not self.is_allowed(context, permission):
            raise AuthorizationError(
                f"authorization denied for permission={permission.value}"
            )


__all__ = [
    "EnterpriseProjectAccessService", "EnterpriseProjectAuthorizationPolicy",
    "PostgresProjectAccessRepository", "ProjectAccessDenied", "ProjectAccessError",
    "ProjectSecurityProfile", "UserOBSAssignment",
]
