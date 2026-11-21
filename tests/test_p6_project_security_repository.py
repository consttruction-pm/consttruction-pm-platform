import sqlite3
from dataclasses import replace

import pytest

from construction_pm.application.authorization import AuthorizationContext, AuthorizationError, Permission
from construction_pm.p6_obs_repository import P6OBSNode, P6OBSApplicationService, SQLiteP6OBSRepository
from construction_pm.p6_project_security import P6ProjectSecurityProfile, normalize_project_privileges
from construction_pm.p6_project_security_api import P6ProjectSecurityAPI
from construction_pm.p6_project_security_repository import (
    P6OBSProjectGrant,
    P6ProjectSecurityPersistenceError,
    SQLiteP6ProjectSecurityRepository,
)


class GlobalAdminPolicy:
    def __init__(self, allowed=True):
        self.allowed = allowed

    def allows_global_privilege(self, context, code):
        return self.allowed and code in {"add_edit_delete_security_profiles", "add_edit_delete_users"}


def setup_repository():
    connection = sqlite3.connect(":memory:")
    obs = SQLiteP6OBSRepository(connection)
    obs_service = P6OBSApplicationService(obs)
    obs_service.save(P6OBSNode("tenant-a", "OBS-ROOT", name="Root"))
    obs_service.save(P6OBSNode("tenant-a", "OBS-CIVIL", parent_obs_id="OBS-ROOT", name="Civil"))
    project_obs = {"project-civil": "OBS-CIVIL", "project-other": "OBS-OTHER"}
    repository = SQLiteP6ProjectSecurityRepository(
        connection, project_obs_lookup=lambda tenant, project: project_obs.get(project),
        obs_repository=obs, user_exists=lambda tenant, user: tenant == "tenant-a",
    )
    return connection, repository


def profile(profile_id="profile-pm", *, revision=1, default=False):
    return P6ProjectSecurityProfile(
        "tenant-a", profile_id, "Project Manager",
        normalize_project_privileges((
            "add_edit_activities_except_relationships",
            "add_edit_delete_wbs_except_costs_financials",
            "view_project_costs_financials",
        )),
        revision=revision, is_default=default,
    )


def context():
    return AuthorizationContext("tenant-a", "project-civil", "admin-user", frozenset())


def test_project_profile_lifecycle_default_revision_and_assignment_guard():
    connection, repo = setup_repository()
    repo.save_profile(profile(), actor_id="admin-user")
    default = repo.set_default_profile(
        "tenant-a", "profile-pm", actor_id="admin-user", expected_revision=1
    )
    assert default.is_default and default.revision == 2
    with pytest.raises(P6ProjectSecurityPersistenceError, match="DEFAULT_PROJECT_PROFILE_CANNOT_BE_DELETED"):
        repo.delete_profile("tenant-a", "profile-pm", actor_id="admin-user", expected_revision=2)

    repo.save_profile(
        P6ProjectSecurityProfile(
            "tenant-a", "profile-reader", "Reader", (), revision=1
        ),
        actor_id="admin-user",
    )
    repo.assign_obs(
        P6OBSProjectGrant("tenant-a", "user-1", "OBS-CIVIL", "profile-pm"),
        actor_id="admin-user",
    )
    with pytest.raises(P6ProjectSecurityPersistenceError, match="PROJECT_SECURITY_PROFILE_HAS_ASSIGNMENTS"):
        repo.delete_profile("tenant-a", "profile-pm", actor_id="admin-user", expected_revision=2)
    assert repo.has_project_access("tenant-a", "user-1", "project-civil")
    assert not repo.has_project_access("tenant-a", "user-1", "project-other")
    # A user assigned to an ancestor OBS also has access to descendant projects.
    repo.assign_obs(
        P6OBSProjectGrant("tenant-a", "user-root", "OBS-ROOT", "profile-pm"),
        actor_id="admin-user",
    )
    assert repo.has_project_access("tenant-a", "user-root", "project-civil")
    assert repo.has_project_privilege(
        "tenant-a", "user-root", "project-civil", "add_edit_activities_except_relationships"
    )
    assert repo.has_project_privilege(
        "tenant-a", "user-1", "project-civil", "add_edit_activities_except_relationships"
    )
    assert not repo.has_project_privilege(
        "tenant-a", "user-1", "project-civil", "delete_projects"
    )


def test_obs_grant_requires_existing_tenant_obs_and_active_profile():
    _, repo = setup_repository()
    repo.save_profile(profile(), actor_id="admin-user")
    with pytest.raises(P6ProjectSecurityPersistenceError, match="OBS_NODE_NOT_FOUND"):
        repo.assign_obs(
            P6OBSProjectGrant("tenant-a", "user-1", "OBS-MISSING", "profile-pm"),
            actor_id="admin-user",
        )
    with pytest.raises(P6ProjectSecurityPersistenceError, match="PROJECT_SECURITY_PROFILE_NOT_FOUND"):
        repo.assign_obs(
            P6OBSProjectGrant("tenant-a", "user-1", "OBS-CIVIL", "inactive-profile"),
            actor_id="admin-user",
        )


def test_project_security_api_requires_named_global_admin_privilege_and_scopes_tenant():
    _, repo = setup_repository()
    api = P6ProjectSecurityAPI(repo, GlobalAdminPolicy())
    created = api.save_profile(profile(), auth_context=context())
    assert created["profile"]["profile_id"] == "profile-pm"
    repo.set_default_profile(
        "tenant-a", "profile-pm", actor_id="admin-user", expected_revision=1
    )
    grant = api.assign_obs("user-1", "OBS-CIVIL", auth_context=context())
    assert grant["grant"]["obs_id"] == "OBS-CIVIL"
    assert api.list_user_grants("user-1", auth_context=context())["grants"][0]["profile_id"] == "profile-pm"

    denied = P6ProjectSecurityAPI(repo, GlobalAdminPolicy(False))
    with pytest.raises(AuthorizationError, match="P6_PROJECT_SECURITY_PROFILE_ADMIN_NOT_AUTHORIZED"):
        denied.list_profiles(auth_context=context())


def test_profile_privilege_dependency_is_enforced_at_persistence_boundary():
    _, repo = setup_repository()
    invalid = P6ProjectSecurityProfile(
        "tenant-a", "invalid", "Invalid", ("edit_activity_id",)
    )
    with pytest.raises(ValueError, match="PROJECT_SECURITY_PRIVILEGE_REQUIREMENT_MISSING"):
        repo.save_profile(invalid, actor_id="admin-user")


def test_builtin_project_superuser_is_provisioned_idempotently_and_immutable():
    _, repo = setup_repository()
    first = repo.ensure_builtin_profile("tenant-a", actor_id="admin-user")
    second = repo.ensure_builtin_profile("tenant-a", actor_id="admin-user")
    assert first == second
    assert first.built_in is True
    assert set(first.privileges) == __import__(
        "construction_pm.p6_project_security", fromlist=["P6_PROJECT_PRIVILEGE_IDS"]
    ).P6_PROJECT_PRIVILEGE_IDS
    with pytest.raises(P6ProjectSecurityPersistenceError, match="BUILTIN_PROJECT_SECURITY_PROFILE_IMMUTABLE"):
        repo.delete_profile("tenant-a", first.profile_id, actor_id="admin-user", expected_revision=1)
    with pytest.raises(P6ProjectSecurityPersistenceError, match="BUILTIN_PROJECT_SECURITY_PROFILE_IMMUTABLE"):
        repo.save_profile(replace(first, revision=2), actor_id="admin-user", expected_revision=1)


def test_project_profile_duplicate_copies_privileges_but_not_default_or_identity():
    _, repo = setup_repository()
    source = profile()
    repo.save_profile(source, actor_id="admin-user")
    duplicate = repo.duplicate_profile(
        "tenant-a", source.profile_id, new_profile_id="profile-copy",
        new_name="Project Manager Copy", actor_id="admin-user",
    )
    assert duplicate.profile_id == "profile-copy"
    assert duplicate.name == "Project Manager Copy"
    assert duplicate.privileges == source.privileges
    assert duplicate.revision == 1
    assert duplicate.is_default is False
    assert duplicate.built_in is False


def test_global_policy_enforces_project_profile_privileges_through_obs_grant():
    from datetime import datetime, timezone
    from construction_pm.application.authorization import AuthorizationContext
    from construction_pm.p6_global_security import (
        GlobalSecurityProfile, UserGlobalSecurity, P6GlobalSecurityAuthorizationPolicy,
    )

    _, project_repo = setup_repository()
    project_repo.save_profile(profile(), actor_id="admin-user")
    project_repo.assign_obs(
        P6OBSProjectGrant("tenant-a", "user-1", "OBS-ROOT", "profile-pm"),
        actor_id="admin-user",
    )
    global_profile = GlobalSecurityProfile("tenant-a", "global-pm", "Global PM", ())
    global_assignment = UserGlobalSecurity(
        "tenant-a", "user-1", "global-pm", ("projects",), "none", (),
        1, "admin-user", datetime.now(timezone.utc),
    )
    class GlobalRepository:
        def get_user_security(self, tenant_id, user_id):
            return global_assignment if (tenant_id, user_id) == ("tenant-a", "user-1") else None
        def get_profile(self, tenant_id, profile_id):
            return global_profile if (tenant_id, profile_id) == ("tenant-a", "global-pm") else None

    policy = P6GlobalSecurityAuthorizationPolicy(
        GlobalRepository(), object(), obs_project_access=project_repo
    )
    auth = AuthorizationContext("tenant-a", "project-civil", "user-1", frozenset())
    assert policy.is_allowed(auth, Permission.PROJECT_READ)
    assert policy.has_project_privilege(auth, "add_edit_activities_except_relationships")
    policy.require_project_privilege(auth, "add_edit_activities_except_relationships")
    assert not policy.has_project_privilege(auth, "delete_projects")
    with pytest.raises(AuthorizationError, match="P6_PROJECT_PRIVILEGE_REQUIRED:delete_projects"):
        policy.require_project_privilege(auth, "delete_projects")


def test_project_superuser_profile_assignment_requires_global_admin_superuser():
    _, repo = setup_repository()
    repo.ensure_builtin_profile("tenant-a", actor_id="admin-user")
    api = P6ProjectSecurityAPI(repo, GlobalAdminPolicy())
    with pytest.raises(AuthorizationError, match="PROJECT_SUPERUSER_ASSIGNMENT_REQUIRES_ADMIN_SUPERUSER"):
        api.assign_obs(
            "user-1", "OBS-ROOT", "p6-project-superuser", auth_context=context()
        )


def test_project_superuser_cannot_be_defaulted_or_duplicated_by_profile_admin():
    _, repo = setup_repository()
    builtin = repo.ensure_builtin_profile("tenant-a", actor_id="admin-user")
    api = P6ProjectSecurityAPI(repo, GlobalAdminPolicy())
    with pytest.raises(AuthorizationError, match="PROJECT_SUPERUSER_PROFILE_DEFAULT_REQUIRES_ADMIN_SUPERUSER"):
        api.set_default(builtin.profile_id, expected_revision=1, auth_context=context())
    with pytest.raises(P6ProjectSecurityPersistenceError, match="BUILTIN_PROJECT_SECURITY_PROFILE_CANNOT_BE_DUPLICATED"):
        repo.duplicate_profile(
            "tenant-a", builtin.profile_id, new_profile_id="copy", new_name="Copy",
            actor_id="admin-user",
        )


def test_project_creation_privilege_resolves_from_target_obs_before_project_exists():
    from datetime import datetime, timezone
    from construction_pm.application.authorization import AuthorizationContext
    from construction_pm.p6_global_security import (
        GlobalSecurityProfile, UserGlobalSecurity, P6GlobalSecurityAuthorizationPolicy,
    )

    _, project_repo = setup_repository()
    create_profile = P6ProjectSecurityProfile(
        "tenant-a", "profile-create", "Project Creator", ("add_projects",)
    )
    project_repo.save_profile(create_profile, actor_id="admin-user")
    project_repo.assign_obs(
        P6OBSProjectGrant("tenant-a", "creator", "OBS-ROOT", "profile-create"),
        actor_id="admin-user",
    )
    global_profile = GlobalSecurityProfile("tenant-a", "global-projects", "Projects", ())
    global_assignment = UserGlobalSecurity(
        "tenant-a", "creator", "global-projects", ("projects",), "none", (),
        1, "admin-user", datetime.now(timezone.utc),
    )
    class GlobalRepository:
        def get_user_security(self, tenant_id, user_id):
            return global_assignment if (tenant_id, user_id) == ("tenant-a", "creator") else None
        def get_profile(self, tenant_id, profile_id):
            return global_profile if (tenant_id, profile_id) == ("tenant-a", "global-projects") else None

    policy = P6GlobalSecurityAuthorizationPolicy(
        GlobalRepository(), object(), obs_project_access=project_repo
    )
    auth = AuthorizationContext("tenant-a", "new-project-not-created-yet", "creator", frozenset())
    policy.require_project_privilege_for_obs(auth, "OBS-CIVIL", "add_projects")
    assert not policy.has_project_privilege_for_obs(auth, "OBS-CIVIL", "delete_projects")


def test_assigned_profile_cannot_be_deactivated_and_api_preserves_default_flag():
    _, repo = setup_repository()
    saved = repo.save_profile(profile(), actor_id="admin-user")
    repo.assign_obs(
        P6OBSProjectGrant("tenant-a", "user-1", "OBS-CIVIL", saved.profile_id),
        actor_id="admin-user",
    )
    with pytest.raises(P6ProjectSecurityPersistenceError, match="PROJECT_SECURITY_PROFILE_HAS_ASSIGNMENTS"):
        repo.save_profile(replace(saved, active=False, revision=2), actor_id="admin-user", expected_revision=1)

    repo.set_default_profile(
        "tenant-a", saved.profile_id, actor_id="admin-user", expected_revision=1
    )
    api = P6ProjectSecurityAPI(repo, GlobalAdminPolicy())
    updated = api.save_profile(
        replace(saved, name="Project Manager Revised", revision=3),
        expected_revision=2, auth_context=context(),
    )
    assert updated["profile"]["is_default"] is True


def test_user_admin_can_list_profiles_for_assignment_but_cannot_edit_catalog():
    _, repo = setup_repository()
    repo.save_profile(profile(), actor_id="admin-user")
    class UserAdminOnly:
        def allows_global_privilege(self, context, code):
            return code == "add_edit_delete_users"
    api = P6ProjectSecurityAPI(repo, UserAdminOnly())
    assert len(api.list_profiles(auth_context=context())["profiles"]) == 1
    with pytest.raises(AuthorizationError, match="P6_PROJECT_SECURITY_PROFILE_ADMIN_NOT_AUTHORIZED"):
        api.save_profile(profile(), expected_revision=None, auth_context=context())


def test_project_profile_api_applies_v26_auto_selected_privileges():
    _, repo = setup_repository()
    api = P6ProjectSecurityAPI(repo, GlobalAdminPolicy())
    result = api.save_profile(
        P6ProjectSecurityProfile(
            "tenant-a", "profile-codes", "Code Manager", ("delete_project_activity_codes",)
        ), auth_context=context(),
    )
    selected = {item["code"] for item in result["profile"]["privileges"]}
    assert selected == {
        "delete_project_activity_codes", "add_project_activity_codes",
        "edit_project_activity_codes",
    }
