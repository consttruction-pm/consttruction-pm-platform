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
    project_profile_has_permission,
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

    def list(self, tenant_id):
        return (type("OBSNode",(),{"obs_id":"root","parent_obs_id":None,"code":"ROOT",
            "name":"Root","manager_user_id":"admin-1","sequence_number":1})(),)


class FakeRepository:
    def __init__(self):
        self.profiles = {}
        self.assignments = {}

    def create_profile(self, profile, actor_id):
        self.profiles[(profile.tenant_id, profile.profile_id)] = profile
        return profile

    def get_profile(self, tenant_id, profile_id):
        return self.profiles.get((tenant_id, profile_id))

    def list_profiles(self, tenant_id):
        return tuple(value for (tenant, _), value in self.profiles.items() if tenant == tenant_id)

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
    repository.assignments[("tenant-a","member-1","root","read_only")] = UserOBSAssignment(
        "tenant-a","member-1","root","read_only",True,1,"admin-1",NOW
    )
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


def test_legacy_project_membership_alone_does_not_bypass_obs_profile():
    repository = FakeRepository()
    role_policy = RoleBasedAuthorizationPolicy(default_role_permissions())

    class MembershipOnlyConnection:
        def execute(self, sql, params):
            class Result:
                def fetchone(self):
                    return (1,) if "project_lifecycle_projects" in sql else None
            return Result()

    policy = EnterpriseProjectAuthorizationPolicy(
        role_policy, repository, MembershipOnlyConnection()
    )
    viewer = AuthorizationContext(
        "tenant-a", "project-1", "member-1", frozenset({"viewer"})
    )
    assert not policy.is_allowed(viewer, Permission.PROJECT_READ)


def test_enterprise_admin_can_list_profiles_and_obs_directory():
    repository=FakeRepository()
    service=EnterpriseProjectAccessService(repository,FakeLifecycle(),FakeOBS(),clock=lambda:NOW)
    service.create_profile("valid-session","read_only","Read only",("project.read",))
    profiles=service.list_profiles("valid-session")
    nodes=service.list_obs_nodes("valid-session")
    assert profiles[0].profile_id=="read_only"
    assert nodes[0].obs_id=="root"


def test_user_can_hold_multiple_obs_profile_pairs_without_collapsing_scope():
    repository = FakeRepository()
    service = EnterpriseProjectAccessService(
        repository, FakeLifecycle(), FakeOBS(), clock=lambda: NOW
    )
    service.create_profile("valid-session", "read_only", "Read only", ("project.read",))
    service.create_profile("valid-session", "schedule", "Schedule", ("project.read", "project.schedule"))
    root = service.assign_user_obs("valid-session", "member-1", "root", "read_only")
    child = service.assign_user_obs("valid-session", "member-1", "child", "schedule")
    assignments = service.list_user_obs("valid-session", "member-1")
    assert {(item.obs_id, item.profile_id) for item in assignments} == {
        ("root", "read_only"), ("child", "schedule")
    }
    assert root.active and child.active



def test_project_security_profile_accepts_and_normalizes_granular_v26_privileges():
    repository = FakeRepository()
    service = EnterpriseProjectAccessService(
        repository, FakeLifecycle(), FakeOBS(), clock=lambda: NOW
    )
    profile = service.create_profile(
        "valid-session", "issue-manager", "Issue manager", ("issue.delete",)
    )
    assert set(profile.permissions) == {
        "issue.delete", "issue.edit", "issue.assign", "issue.view"
    }


def test_project_security_profile_rejects_unknown_granular_privileges():
    repository = FakeRepository()
    service = EnterpriseProjectAccessService(
        repository, FakeLifecycle(), FakeOBS(), clock=lambda: NOW
    )
    with pytest.raises(ProjectAccessError, match="PROJECT_SECURITY_PROFILE_PERMISSION_INVALID"):
        service.create_profile(
            "valid-session", "invalid", "Invalid", ("project.superuser",)
        )


def test_project_security_profile_inheritance_targets_are_present_for_all_crud_domains():
    from construction_pm.p6_project_privileges import (
        PRIVILEGE_BY_KEY, expand_project_privileges,
    )
    for key in ("activity.delete", "project.delete", "wbs.delete",
                "expense.delete", "issue.delete", "threshold.delete",
                "risk.delete",
                "resource_assignment.add_edit"):
        expanded = expand_project_privileges({key})
        assert expanded <= PRIVILEGE_BY_KEY.keys()
        assert any(item.endswith(".view") for item in expanded)



def test_granular_wbs_profile_is_checked_without_legacy_project_read_write():
    class GranularRepository(FakeRepository):
        def project_permission(self, tenant_id, user_id, project_id, permission):
            return permission == "wbs.view" and (
                tenant_id, user_id, "root", "wbs_only"
            ) in self.assignments

    repository = GranularRepository()
    repository.assignments[("tenant-a", "member-1", "root", "wbs_only")] = UserOBSAssignment(
        "tenant-a", "member-1", "root", "wbs_only", True, 1, "admin-1", NOW
    )

    class ExistingProjectConnection:
        def execute(self, sql, params):
            class Result:
                def fetchone(self):
                    return (1,)
            return Result()

    policy = EnterpriseProjectAuthorizationPolicy(
        RoleBasedAuthorizationPolicy(default_role_permissions()),
        repository,
        ExistingProjectConnection(),
    )
    planner = AuthorizationContext(
        "tenant-a", "project-1", "member-1", frozenset({"planner"})
    )
    assert policy.is_allowed(planner, Permission.WBS_VIEW)
    assert not policy.is_allowed(planner, Permission.WBS_DELETE)



@pytest.mark.parametrize(
    ("profile_grant", "route_permission"),
    [
        ("activity.add_edit_except_relationships", "activity.add_edit"),
        ("expense.add_edit_delete", "expense.add_edit"),
        ("issue_threshold.add_edit_delete", "issue.add_edit"),
        ("issue_threshold.add_edit_delete", "issue.delete"),
        ("issue_threshold.add_edit_delete", "threshold.add_edit"),
        ("risk.add_edit_delete", "risk.delete"),
        ("project_baseline.add_edit_delete", "baseline.create_update"),
        ("baseline.update", "baseline.update"),
        ("wbs.add_edit_delete_except_costs_financials", "wbs.add_edit"),
        ("wbs.add_edit_delete_except_costs_financials", "wbs.delete"),
        ("project.view", "project.read"),
        ("project.edit_details_except_costs_financials", "project.write"),
        ("schedule.run", "project.schedule"),
    ],
)
def test_oracle_v26_profile_checkbox_maps_to_its_cubi_route_grant(
    profile_grant, route_permission
):
    assert project_profile_has_permission({profile_grant}, route_permission)


def test_wbs_structural_profile_never_grants_wbs_costs_or_financials():
    structural = {"wbs.add_edit_delete_except_costs_financials"}
    assert project_profile_has_permission(structural, "wbs.edit")
    assert not project_profile_has_permission(structural, "wbs.edit_costs_financials")
    assert not project_profile_has_permission(structural, "project.view_costs_financials")


def test_unmapped_profile_privileges_do_not_grant_unrelated_routes():
    assert not project_profile_has_permission(
        {"threshold.monitor"}, "threshold.add_edit"
    )
    assert not project_profile_has_permission(
        {"activity.add_edit_except_relationships"}, "activity.relationship.add_edit_delete"
    )



def test_v26_baseline_assignment_requires_both_documented_profile_privileges():
    assert project_profile_has_permission(
        {
            "project_baseline.assign",
            "project.edit_details_except_costs_financials",
        },
        "baseline.assign",
    )
    assert not project_profile_has_permission(
        {"project_baseline.assign"}, "baseline.assign"
    )
    assert not project_profile_has_permission(
        {"project.edit_details_except_costs_financials"}, "baseline.assign"
    )



def test_project_costs_financials_visibility_is_never_inferred_from_project_view():
    assert project_profile_has_permission(
        {"project.view_costs_financials"}, "project.view_costs_financials"
    )
    assert not project_profile_has_permission(
        {"project.view"}, "project.view_costs_financials"
    )
