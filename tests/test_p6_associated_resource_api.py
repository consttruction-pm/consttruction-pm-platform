import sqlite3
from datetime import datetime, timezone

import pytest

from construction_pm.application.authorization import AuthorizationContext, AuthorizationError
from construction_pm.p6_associated_resource_api import P6AssociatedResourceAPI
from construction_pm.p6_associated_resource_repository import (
    P6AssociatedResource,
    P6AssociatedResourceError,
    SQLiteP6AssociatedResourceRepository,
)
from construction_pm.p6_global_security import P6GlobalSecurityAuthorizationPolicy
from construction_pm.p6_resource_master_repository import P6Resource, SQLiteP6ResourceRepository
from construction_pm.p6_resource_assignment_repository import (
    P6ResourceAssignment, SQLiteP6ResourceAssignmentRepository,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.application.authorization import Permission


class UserRepository:
    def __init__(self, users):
        self.users = set(users)

    def exists(self, tenant_id, user_id):
        return (tenant_id, user_id) in self.users


class AdminPolicy:
    def __init__(self, allowed=True):
        self.allowed = allowed

    def allows_global_privilege(self, context, code):
        return self.allowed and code == "add_edit_delete_users"


def setup():
    connection = sqlite3.connect(":memory:")
    resources = SQLiteP6ResourceRepository(connection)
    SQLiteP6ResourceAssignmentRepository(connection)
    resources.save(P6Resource("tenant-a", "project-a", 1, "R-100", "Civil Crew"))
    resources.save(P6Resource("tenant-a", "project-b", 1, "R-200", "Plant Team"))
    users = UserRepository({("tenant-a", "user-1"), ("tenant-a", "user-2")})
    repository = SQLiteP6AssociatedResourceRepository(connection, user_exists=users.exists)
    return connection, resources, repository


def context(user_id="admin"):
    return AuthorizationContext("tenant-a", "project-a", user_id, frozenset())


def test_associated_resource_enforces_one_to_one_and_tenant_scoping():
    connection, _, repo = setup()
    now = datetime.now(timezone.utc)
    first = P6AssociatedResource("tenant-a", "user-1", "R-100", 1, "admin", now)
    assert repo.assign(first) == first
    assert repo.get_for_user("tenant-a", "user-1") == first
    assert repo.get_for_resource("tenant-a", "R-100") == first

    second = P6AssociatedResource("tenant-a", "user-2", "R-100", 1, "admin", now)
    with pytest.raises(P6AssociatedResourceError, match="RESOURCE_ALREADY_ASSOCIATED"):
        repo.assign(second)
    assert repo.get_for_user("tenant-a", "user-2") is None
    assert repo.get_for_user("other-tenant", "user-1") is None


def test_associated_resource_reassignment_requires_revision_and_unassign_keeps_resource():
    _, resources, repo = setup()
    now = datetime.now(timezone.utc)
    first = P6AssociatedResource("tenant-a", "user-1", "R-100", 1, "admin", now)
    repo.assign(first)
    with pytest.raises(P6AssociatedResourceError, match="ASSOCIATED_RESOURCE_REVISION_CONFLICT"):
        repo.assign(P6AssociatedResource("tenant-a", "user-1", "R-200", 2, "admin", now))
    updated = P6AssociatedResource("tenant-a", "user-1", "R-200", 2, "admin", now)
    assert repo.assign(updated, expected_revision=1) == updated
    repo.unassign("tenant-a", "user-1", actor_id="admin", expected_revision=2, occurred_at=now)
    assert repo.get_for_user("tenant-a", "user-1") is None
    assert resources.get("tenant-a", "project-a", 1, "R-100") is not None


def test_associated_resource_requires_existing_user_and_enterprise_resource():
    _, _, repo = setup()
    now = datetime.now(timezone.utc)
    with pytest.raises(P6AssociatedResourceError, match="ASSOCIATED_RESOURCE_USER_NOT_FOUND"):
        repo.assign(P6AssociatedResource("tenant-a", "missing", "R-100", 1, "admin", now))
    with pytest.raises(P6AssociatedResourceError, match="ASSOCIATED_RESOURCE_NOT_FOUND"):
        repo.assign(P6AssociatedResource("tenant-a", "user-1", "R-MISSING", 1, "admin", now))


def test_associated_resource_api_requires_add_edit_delete_users_global_privilege():
    _, _, repo = setup()
    api = P6AssociatedResourceAPI(repo, AdminPolicy())
    created = api.assign("user-1", "R-100", auth_context=context())
    assert created["association"]["resource_id"] == "R-100"
    assert api.get("user-1", auth_context=context())["association"]["resource_id"] == "R-100"
    api.unassign("user-1", expected_revision=1, auth_context=context())
    assert api.get("user-1", auth_context=context()) is None

    denied = P6AssociatedResourceAPI(repo, AdminPolicy(False))
    with pytest.raises(AuthorizationError, match="ASSOCIATED_RESOURCE_ADMIN_NOT_AUTHORIZED"):
        denied.assign("user-1", "R-100", auth_context=context())


def test_resource_identity_is_registered_tenant_wide_and_not_deleted_with_association():
    connection, _, _ = setup()
    row = connection.execute(
        "SELECT tenant_id,resource_id,name FROM p6_enterprise_resource_identity "
        "WHERE tenant_id='tenant-a' AND resource_id='R-100'"
    ).fetchone()
    assert row == ("tenant-a", "R-100", "Civil Crew")


def test_global_policy_requires_associated_resource_for_team_member_and_personal_calendar():
    from datetime import datetime, timezone
    from construction_pm.p6_global_security import (
        GlobalSecurityProfile, UserGlobalSecurity, P6GlobalSecurityAuthorizationPolicy,
    )

    connection, _, associations = setup()
    now = datetime.now(timezone.utc)
    associations.assign(P6AssociatedResource("tenant-a", "user-1", "R-100", 1, "admin", now))
    profile = GlobalSecurityProfile(
        "tenant-a", "profile-1", "Team Member + Calendar",
        ("add_edit_delete_resource_calendars",),
    )
    assignment = UserGlobalSecurity(
        "tenant-a", "user-1", "profile-1", ("team_member", "resources"),
        "none", (), 1, "admin", now,
    )
    class SecurityRepository:
        def get_user_security(self, tenant_id, user_id):
            return assignment if (tenant_id, user_id) == ("tenant-a", "user-1") else None
        def get_profile(self, tenant_id, profile_id):
            return profile if (tenant_id, profile_id) == ("tenant-a", "profile-1") else None

    policy = P6GlobalSecurityAuthorizationPolicy(
        SecurityRepository(), object(), associated_resource_access=associations
    )
    user_context = AuthorizationContext("tenant-a", "project-a", "user-1", frozenset())
    assert policy.associated_resource_id(user_context) == "R-100"
    assert policy.can_use_team_member(user_context)
    assert policy.can_edit_personal_resource_calendar(user_context)

    without_link = P6GlobalSecurityAuthorizationPolicy(
        SecurityRepository(), object(), associated_resource_access=None
    )
    assert not without_link.can_use_team_member(user_context)
    assert not without_link.can_edit_personal_resource_calendar(user_context)


def test_contributor_module_sees_projects_where_associated_resource_is_assigned():
    connection, _, associations = setup()
    now = datetime.now(timezone.utc)
    associations.assign(P6AssociatedResource("tenant-a", "user-1", "R-100", 1, "admin", now))
    assignment_repo = SQLiteP6ResourceAssignmentRepository(connection)
    assignment_repo.upsert(P6ResourceAssignment(
        BackendScope("tenant-a", "project-a", 1), "A-1", "ACT-1", "R-100"
    ))
    profile = __import__("construction_pm.p6_global_security", fromlist=["GlobalSecurityProfile"]).GlobalSecurityProfile(
        "tenant-a", "contributor-profile", "Contributor", ()
    )
    assignment = __import__("construction_pm.p6_global_security", fromlist=["UserGlobalSecurity"]).UserGlobalSecurity(
        "tenant-a", "user-1", "contributor-profile", ("contributor",),
        "none", (), 1, "admin", now,
    )
    class SecurityRepository:
        def get_user_security(self, tenant_id, user_id):
            return assignment if (tenant_id, user_id) == ("tenant-a", "user-1") else None
        def get_profile(self, tenant_id, profile_id):
            return profile if (tenant_id, profile_id) == ("tenant-a", "contributor-profile") else None

    policy = P6GlobalSecurityAuthorizationPolicy(
        SecurityRepository(), object(), associated_resource_access=associations
    )
    user_context = AuthorizationContext("tenant-a", "project-a", "user-1", frozenset())
    assert policy.is_allowed(user_context, Permission.PROJECT_READ)
    other_project = AuthorizationContext("tenant-a", "project-b", "user-1", frozenset())
    assert not policy.is_allowed(other_project, Permission.PROJECT_READ)
    assert not policy.is_allowed(user_context, Permission.PROJECT_WRITE)


def test_native_associated_resource_assignment_syncs_user_personal_name():
    connection, _, _ = setup()
    users = UserRepository({("tenant-a", "user-1")})
    synced = []
    repo = SQLiteP6AssociatedResourceRepository(
        connection, user_exists=users.exists,
        native_auth_name_sync=lambda tenant, user, name: synced.append((tenant, user, name)),
    )
    repo.assign(P6AssociatedResource(
        "tenant-a", "user-1", "R-100", 1, "admin", datetime.now(timezone.utc)
    ))
    assert synced == [("tenant-a", "user-1", "Civil Crew")]
