from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import uuid4

from .application.authorization import AuthorizationContext, AuthorizationError, Permission, RoleBasedAuthorizationPolicy
from .application.project_lifecycle import ProjectLifecycleError, SessionError

PROJECT_PERMISSION_CODES = frozenset({Permission.PROJECT_READ.value, Permission.PROJECT_WRITE.value, Permission.PROJECT_SCHEDULE.value, Permission.PROJECT_ADMIN.value})
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
    def project_permission(self, tenant_id: str, user_id: str, project_id: str, permission: str) -> bool:
        row = self.connection.execute(
            "SELECT cubi_user_has_project_access(%s,%s,%s,%s)",
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
