from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from construction_pm.application.authorization import AuthorizationContext, Permission, RoleBasedAuthorizationPolicy, default_role_permissions
from construction_pm.enterprise_project_access import (
    EnterpriseProjectAccessService,
    EnterpriseProjectAuthorizationPolicy,
    ProjectAccessDenied,
    ProjectAccessError,
    ProjectSecurityProfile,
    UserOBSAssignment,
)

NOW = datetime(2026, 11, 15, 18, 0, tzinfo=timezone.utc)


@dataclass(frozen=True)
class Session:
    tenant_id: str
    user_id: str
    roles: frozenset[str]


class FakeLifecycle:
    def __init__(self, roles=frozenset({"enterprise_admin"})):
        self.session = Session("tenant-a", "admin-1", roles)

    def get_session(self, session_id, *, now):
        if session_id != "valid-session":
            raise ValueError("SESSION_NOT_FOUND")
        return self.session


class FakeOBS:
    def obs_node_exists(self, tenant_id, obs_id):
        return tenant_id == "tenant-a" and obs_id in {"root", "child"}


class FakeRepository:
    def __init__(self):
        self.profiles = {}
        self.assignments = {}

    def create_profile(self, profile, actor_id):
        self.profiles[(profile.tenant_id, profile.profile_id)] = profile
        return profile

    def get_profile(self, tenant_id, profile_id):
        return self.profiles.get((tenant_id, profile_id))

    def assign_user_obs(self, assignment):
        if assignment.user_id != "member-1":
            raise ProjectAccessError("PROJECT_ACCESS_USER_NOT_FOUND")
        profile = self.get_profile(assignment.tenant_id, assignment.profile_id)
        if profile is None or not profile.active:
            raise ProjectAccessError("PROJECT_SECURITY_PROFILE_NOT_FOUND")
        self.assignments[(assignment.tenant_id, assignment.user_id, assignment.obs_id, assignment.profile_id)] = assignment
        return assignment

    def revoke_user_obs(self, tenant_id, user_id, obs_id, profile_id, actor_id, expected_revision, at):
        key = (tenant_id, user_id, obs_id, profile_id)
        current = self.assignments.get(key)
        if current is None or current.revision != expected_revision:
            raise ProjectAccessError("PROJECT_ACCESS_REVISION_CONFLICT_OR_NOT_FOUND")
        revoked = UserOBSAssignment(tenant_id,user_id,obs_id,profile_id,False,
            current.revision+1,actor_id,at)
        self.assignments[key] = revoked
        return revoked

    def list_user_obs(self, tenant_id, user_id):
        return tuple(x for x in self.assignments.values()
                     if x.tenant_id == tenant_id and x.user_id == user_id)

    def project_permission(self, tenant_id, user_id, project_id, permission):
        return permission == "project.read" and (tenant_id,user_id,"root","read_only") in self.assignments


def test_project_security_profile_accepts_only_project_permissions():
    profile = ProjectSecurityProfile("tenant-a","read_only","Read only",
        ("project.read",),True,1,NOW)
    profile.validate()
    invalid = ProjectSecurityProfile("tenant-a","wide","Invalid",
        ("project.read","identity.admin"),True,1,NOW)
    with pytest.raises(ProjectAccessError, match="PROJECT_SECURITY_PROFILE_PERMISSION_INVALID"):
        invalid.validate()


def test_enterprise_admin_can_create_profile_assign_and_revoke_obs():
    repository = FakeRepository()
    service = EnterpriseProjectAccessService(repository, FakeLifecycle(), FakeOBS(), clock=lambda: NOW)
    profile = service.create_profile("valid-session","read_only","Read only",("project.read",))
    assert profile.permissions == ("project.read",)
    assignment = service.assign_user_obs("valid-session","member-1","root","read_only")
    assert assignment.active is True
    assert service.list_user_obs("valid-session","member-1") == (assignment,)
    revoked = service.revoke_user_obs("valid-session","member-1","root","read_only",1)
    assert revoked.active is False
    assert revoked.revision == 2


def test_non_admin_cannot_manage_project_access():
    service = EnterpriseProjectAccessService(
        FakeRepository(), FakeLifecycle(frozenset({"viewer"})), FakeOBS(), clock=lambda: NOW
    )
    with pytest.raises(ProjectAccessDenied, match="ENTERPRISE_ADMIN_REQUIRED"):
        service.create_profile("valid-session","read_only","Read only",("project.read",))


def test_obs_project_authorization_requires_both_global_module_and_project_profile():
    repository = FakeRepository()
    role_policy = RoleBasedAuthorizationPolicy(default_role_permissions())
    class Connection:
        def execute(self, sql, params):
            class Result:
                def fetchone(self):
                    return None
            return Result()
    policy = EnterpriseProjectAuthorizationPolicy(role_policy, repository, Connection())
    viewer = AuthorizationContext("tenant-a","project-1","member-1",frozenset({"viewer"}))
    assert policy.is_allowed(viewer, Permission.PROJECT_READ)
    assert not policy.is_allowed(viewer, Permission.PROJECT_WRITE)
    planner = AuthorizationContext("tenant-a","project-1","member-1",frozenset({"planner"}))
    assert not policy.is_allowed(planner, Permission.PROJECT_WRITE)
