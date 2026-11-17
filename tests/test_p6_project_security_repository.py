import sqlite3
from dataclasses import replace

import pytest

from construction_pm.application.authorization import AuthorizationContext, AuthorizationError
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
        return self.allowed and code == "add_edit_delete_security_profiles"


def setup_repository():
    connection = sqlite3.connect(":memory:")
    obs = SQLiteP6OBSRepository(connection)
    obs_service = P6OBSApplicationService(obs)
    obs_service.save(P6OBSNode("tenant-a", "OBS-ROOT", name="Root"))
    obs_service.save(P6OBSNode("tenant-a", "OBS-CIVIL", parent_obs_id="OBS-ROOT", name="Civil"))
    project_obs = {"project-civil": "OBS-CIVIL", "project-other": "OBS-OTHER"}
    repository = SQLiteP6ProjectSecurityRepository(
        connection, project_obs_lookup=lambda tenant, project: project_obs.get(project),
        obs_repository=obs,
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
    with pytest.raises(ValueError, match="PROJECT_SECURITY_PRIVILEGE_DEPENDENCY_MISSING"):
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
