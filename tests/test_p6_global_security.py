from datetime import datetime, timezone

import pytest

from construction_pm.p6_global_security import (
    ADMIN_SUPERUSER,
    NO_GLOBAL_PRIVILEGES,
    GlobalSecurityError,
    GlobalSecurityProfile,
    UserGlobalSecurity,
    global_profile_has_global_read_only,
    global_profile_has_project_access_bypass,
    user_has_all_resource_access,
    P6_GLOBAL_PRIVILEGE_DEFINITIONS,
    normalize_global_privileges,
)


def profile(name, *, built_in=True, privileges=()):
    return GlobalSecurityProfile(
        tenant_id="tenant-a",
        profile_id=("p6-admin-superuser" if name == ADMIN_SUPERUSER else
                    "p6-no-global-privileges" if name == NO_GLOBAL_PRIVILEGES else
                    name.lower().replace(" ", "-")),
        name=name,
        privileges=tuple(privileges),
        built_in=built_in,
    )


def test_only_application_generated_admin_superuser_bypasses_project_profile_gate():
    admin = profile(ADMIN_SUPERUSER)
    ordinary = profile("Portfolio Admin", built_in=False, privileges=("add_edit_delete_users",))
    no_global = profile(NO_GLOBAL_PRIVILEGES)

    assert global_profile_has_project_access_bypass(admin)
    assert not global_profile_has_project_access_bypass(ordinary)
    assert not global_profile_has_project_access_bypass(no_global)


def test_no_global_privileges_is_a_distinct_read_only_global_profile():
    no_global = profile(NO_GLOBAL_PRIVILEGES)
    assert global_profile_has_global_read_only(no_global)
    assert not global_profile_has_global_read_only(profile(ADMIN_SUPERUSER))


def test_inactive_or_forged_admin_profile_cannot_bypass():
    inactive = GlobalSecurityProfile(
        "tenant-a", "p6-admin-superuser", ADMIN_SUPERUSER, (), True, False, 1
    )
    forged = GlobalSecurityProfile(
        "tenant-a", "fake-admin", ADMIN_SUPERUSER, (), True, True, 1
    )
    assert not global_profile_has_project_access_bypass(inactive)
    with pytest.raises(GlobalSecurityError, match="BUILTIN_PROFILE_ID_INVALID"):
        global_profile_has_project_access_bypass(forged)


@pytest.mark.parametrize(
    ("mode", "roots", "error"),
    [
        ("none", ("resource-1",), "RESOURCE_ROOTS_NOT_ALLOWED"),
        ("all", ("resource-1",), "RESOURCE_ROOTS_NOT_ALLOWED"),
        ("selected", (), "RESOURCE_ROOTS_REQUIRED"),
        ("selected", ("resource-1", "resource-1"), "DUPLICATE_RESOURCE_ROOT"),
    ],
)
def test_resource_access_scope_is_explicit_and_consistent(mode, roots, error):
    value = UserGlobalSecurity(
        tenant_id="tenant-a",
        user_id="user-1",
        profile_id="no-global",
        module_access=("projects",),
        resource_access_mode=mode,
        resource_root_ids=roots,
        revision=1,
        updated_by="admin",
        updated_at=datetime.now(timezone.utc),
    )
    with pytest.raises(GlobalSecurityError, match=error):
        value.validate()


def test_user_global_security_requires_explicit_module_access_and_aware_timestamp():
    value = UserGlobalSecurity(
        tenant_id="tenant-a",
        user_id="user-1",
        profile_id="no-global",
        module_access=("projects", "projects"),
        resource_access_mode="none",
        resource_root_ids=(),
        revision=1,
        updated_by="admin",
        updated_at=datetime.now(timezone.utc),
    )
    with pytest.raises(GlobalSecurityError, match="DUPLICATE_MODULE_ACCESS"):
        value.validate()


def test_builtin_profile_privileges_are_implicit_or_empty():
    with pytest.raises(GlobalSecurityError, match="ADMIN_SUPERUSER_PRIVILEGES_ARE_IMPLICIT"):
        profile(ADMIN_SUPERUSER, privileges=("add_edit_delete_users",)).validate()
    with pytest.raises(GlobalSecurityError, match="NO_GLOBAL_PRIVILEGES_MUST_BE_EMPTY"):
        profile(NO_GLOBAL_PRIVILEGES, privileges=("add_edit_delete_users",)).validate()
    with pytest.raises(GlobalSecurityError, match="UNKNOWN_BUILTIN_GLOBAL_SECURITY_PROFILE"):
        profile("Custom", privileges=()).validate()

def test_v26_module_access_catalogue_and_contributor_exclusivity():
    def assignment(modules):
        return UserGlobalSecurity(
            tenant_id="tenant-a", user_id="user-1", profile_id="custom",
            module_access=modules, resource_access_mode="none",
            resource_root_ids=(), revision=1, updated_by="admin",
            updated_at=datetime.now(timezone.utc),
        )

    with pytest.raises(GlobalSecurityError, match="MODULE_ACCESS_INVALID"):
        assignment(("p6-web",)).validate()
    with pytest.raises(GlobalSecurityError, match="CONTRIBUTOR_MODULE_ACCESS_EXCLUSIVE"):
        assignment(("contributor", "projects")).validate()
    assignment(("projects", "resources", "enterprise_reports")).validate()


def test_selected_resource_access_is_limited_to_five_roots():
    value = UserGlobalSecurity(
        tenant_id="tenant-a", user_id="user-1", profile_id="custom",
        module_access=("projects",), resource_access_mode="selected",
        resource_root_ids=tuple(f"resource-{i}" for i in range(6)),
        revision=1, updated_by="admin", updated_at=datetime.now(timezone.utc),
    )
    with pytest.raises(GlobalSecurityError, match="RESOURCE_ROOT_LIMIT_EXCEEDED"):
        value.validate()


def test_admin_superuser_always_has_all_resource_access():
    from construction_pm.p6_global_security import UserGlobalSecurity

    assignment = UserGlobalSecurity(
        tenant_id="tenant-a",
        user_id="user-1",
        profile_id="p6-admin-superuser",
        module_access=("projects",),
        resource_access_mode="none",
        resource_root_ids=(),
        revision=1,
        updated_by="admin",
        updated_at=datetime.now(timezone.utc),
    )
    assert user_has_all_resource_access(profile(ADMIN_SUPERUSER), assignment)
    assert not user_has_all_resource_access(profile(NO_GLOBAL_PRIVILEGES), assignment)


def test_v26_global_privilege_catalogue_matches_help_categories_and_source():
    assert len(P6_GLOBAL_PRIVILEGE_DEFINITIONS) == 72
    assert {row[2] for row in P6_GLOBAL_PRIVILEGE_DEFINITIONS} == {
        "Administration", "Codes", "Global Data", "Resources",
        "Templates", "Tools", "Views and Reports",
    }

@pytest.mark.parametrize(
    ("selected", "expected"),
    [
        (("global_activity_codes_add",), {"global_activity_codes_add", "global_activity_codes_edit"}),
        (("global_activity_codes_delete",), {"global_activity_codes_delete", "global_activity_codes_add", "global_activity_codes_edit"}),
        (("secure_codes_add_delete",), {"secure_codes_add_delete", "secure_codes_edit", "secure_codes_assign", "secure_codes_view"}),
        (("resources_delete",), {"resources_delete", "resources_add", "resources_edit"}),
    ],
)
def test_v26_global_privilege_dependencies_are_auto_selected(selected, expected):
    assert set(normalize_global_privileges(selected)) == expected

def test_custom_profile_rejects_unknown_global_privilege_and_missing_dependencies():
    with pytest.raises(GlobalSecurityError, match="UNKNOWN_GLOBAL_SECURITY_PRIVILEGE"):
        profile("Custom", built_in=False, privileges=("made_up_privilege",)).validate()
    with pytest.raises(GlobalSecurityError, match="GLOBAL_SECURITY_PRIVILEGE_DEPENDENCY_MISSING"):
        profile("Custom", built_in=False, privileges=("global_activity_codes_add",)).validate()
    normalized = normalize_global_privileges(("global_activity_codes_add",))
    profile("Custom", built_in=False, privileges=normalized).validate()


@pytest.mark.parametrize("admin_count", [0])
def test_last_admin_superuser_guard_rejects_removal_when_none_would_remain(admin_count):
    from construction_pm.p6_global_security import PostgresP6GlobalSecurityRepository

    with pytest.raises(GlobalSecurityError, match="LAST_ADMIN_SUPERUSER_REQUIRED"):
        PostgresP6GlobalSecurityRepository._require_remaining_admin_superuser(admin_count)


@pytest.mark.parametrize("remaining_admins", [1, 2])
def test_last_admin_superuser_guard_allows_removal_when_another_admin_remains(remaining_admins):
    from construction_pm.p6_global_security import PostgresP6GlobalSecurityRepository

    PostgresP6GlobalSecurityRepository._require_remaining_admin_superuser(remaining_admins)


def test_custom_profile_cannot_preempt_reserved_builtin_profile_ids():
    forged = GlobalSecurityProfile(
        "tenant-a", "p6-admin-superuser", "Portfolio Admin",
        ("add_edit_delete_users",), False, True, 1,
    )
    with pytest.raises(GlobalSecurityError, match="BUILTIN_PROFILE_ID_RESERVED"):
        forged.validate()



class _FakeGlobalSecurityRepository:
    def __init__(self, assignment, profile_value):
        self.assignment = assignment
        self.profile_value = profile_value

    def get_user_security(self, tenant_id, user_id):
        if self.assignment is None or (tenant_id, user_id) != (self.assignment.tenant_id, self.assignment.user_id):
            return None
        return self.assignment

    def get_profile(self, tenant_id, profile_id):
        if self.profile_value is None or (tenant_id, profile_id) != (self.profile_value.tenant_id, self.profile_value.profile_id):
            return None
        return self.profile_value


class _FakeProjectPolicy:
    def __init__(self, allowed):
        self.allowed = allowed
        self.calls = 0

    def is_allowed(self, context, permission):
        self.calls += 1
        return self.allowed


def _authorization_context():
    from construction_pm.application.authorization import AuthorizationContext
    return AuthorizationContext(
        tenant_id="tenant-a", project_id="project-1", user_id="user-1",
        roles=frozenset({"viewer"}),
    )


def _user_assignment(profile_id, modules=("projects",)):
    return UserGlobalSecurity(
        tenant_id="tenant-a", user_id="user-1", profile_id=profile_id,
        module_access=tuple(modules), resource_access_mode="none",
        resource_root_ids=(), revision=1, updated_by="admin",
        updated_at=datetime.now(timezone.utc),
    )


def test_production_authorization_fails_closed_without_global_assignment():
    from construction_pm.p6_global_security import P6GlobalSecurityAuthorizationPolicy
    from construction_pm.application.authorization import Permission
    role_policy = _FakeProjectPolicy(True)
    policy = P6GlobalSecurityAuthorizationPolicy(_FakeGlobalSecurityRepository(None, None), role_policy)
    assert not policy.is_allowed(_authorization_context(), Permission.PROJECT_READ)
    assert role_policy.calls == 0


def test_production_authorization_allows_only_real_builtin_admin_global_bypass():
    from construction_pm.p6_global_security import P6GlobalSecurityAuthorizationPolicy
    from construction_pm.application.authorization import Permission
    admin = profile(ADMIN_SUPERUSER)
    role_policy = _FakeProjectPolicy(False)
    policy = P6GlobalSecurityAuthorizationPolicy(
        _FakeGlobalSecurityRepository(_user_assignment("p6-admin-superuser", modules=()), admin),
        role_policy,
    )
    assert policy.is_allowed(_authorization_context(), Permission.PROJECT_ADMIN)
    assert role_policy.calls == 0


def test_production_authorization_does_not_treat_no_global_privileges_as_obs_grant():
    from construction_pm.p6_global_security import P6GlobalSecurityAuthorizationPolicy
    from construction_pm.application.authorization import Permission
    no_global = profile(NO_GLOBAL_PRIVILEGES)
    role_policy = _FakeProjectPolicy(True)
    policy = P6GlobalSecurityAuthorizationPolicy(
        _FakeGlobalSecurityRepository(_user_assignment("p6-no-global-privileges"), no_global),
        role_policy,
    )
    assert not policy.is_allowed(_authorization_context(), Permission.PROJECT_READ)
    assert role_policy.calls == 0


def test_production_authorization_requires_projects_module_before_role_grant():
    from construction_pm.p6_global_security import P6GlobalSecurityAuthorizationPolicy
    from construction_pm.application.authorization import Permission
    custom = profile("Planner", built_in=False)
    role_policy = _FakeProjectPolicy(True)
    policy = P6GlobalSecurityAuthorizationPolicy(
        _FakeGlobalSecurityRepository(_user_assignment("planner", modules=("resources",)), custom),
        role_policy,
    )
    assert not policy.is_allowed(_authorization_context(), Permission.PROJECT_READ)
    assert role_policy.calls == 0


def test_production_authorization_composes_project_module_and_role_policy():
    from construction_pm.p6_global_security import P6GlobalSecurityAuthorizationPolicy
    from construction_pm.application.authorization import Permission
    custom = profile("Planner", built_in=False)
    role_policy = _FakeProjectPolicy(True)
    policy = P6GlobalSecurityAuthorizationPolicy(
        _FakeGlobalSecurityRepository(_user_assignment("planner", modules=("projects",)), custom),
        role_policy,
    )
    assert policy.is_allowed(_authorization_context(), Permission.PROJECT_READ)
    assert role_policy.calls == 1

def test_production_policy_preserves_require_contract_for_lifecycle_callers():
    from construction_pm.application.authorization import AuthorizationError, Permission
    from construction_pm.p6_global_security import P6GlobalSecurityAuthorizationPolicy

    allowed = P6GlobalSecurityAuthorizationPolicy(
        _FakeGlobalSecurityRepository(_user_assignment("project-access"), profile("Project Access", built_in=False)),
        _FakeProjectPolicy(True),
    )
    allowed.require(_authorization_context(), Permission.PROJECT_READ)

    denied = P6GlobalSecurityAuthorizationPolicy(
        _FakeGlobalSecurityRepository(None, None),
        _FakeProjectPolicy(True),
    )
    with pytest.raises(AuthorizationError, match="authorization denied"):
        denied.require(_authorization_context(), Permission.PROJECT_READ)

class _FakeOBSProjectAccess:
    def __init__(self, allowed):
        self.allowed = allowed
        self.calls = []

    def project_permission(self, tenant_id, user_id, project_id, permission):
        self.calls.append((tenant_id, user_id, project_id, permission))
        return self.allowed


def test_no_global_privileges_uses_authoritative_obs_project_profile_resolver():
    from construction_pm.application.authorization import Permission
    from construction_pm.p6_global_security import P6GlobalSecurityAuthorizationPolicy

    no_global = profile(NO_GLOBAL_PRIVILEGES)
    resolver = _FakeOBSProjectAccess(True)
    policy = P6GlobalSecurityAuthorizationPolicy(
        _FakeGlobalSecurityRepository(
            _user_assignment("p6-no-global-privileges", modules=("projects",)),
            no_global,
        ),
        _FakeProjectPolicy(False),
        obs_project_access=resolver,
    )

    assert policy.is_allowed(_authorization_context(), Permission.PROJECT_READ)
    assert resolver.calls == [("tenant-a", "user-1", "project-1", "project.read")]


def test_no_global_privileges_fails_closed_without_obs_assignment_or_projects_module():
    from construction_pm.application.authorization import Permission
    from construction_pm.p6_global_security import P6GlobalSecurityAuthorizationPolicy

    no_global = profile(NO_GLOBAL_PRIVILEGES)
    resolver = _FakeOBSProjectAccess(True)
    no_module = P6GlobalSecurityAuthorizationPolicy(
        _FakeGlobalSecurityRepository(
            _user_assignment("p6-no-global-privileges", modules=("resources",)),
            no_global,
        ),
        _FakeProjectPolicy(True),
        obs_project_access=resolver,
    )
    no_resolver = P6GlobalSecurityAuthorizationPolicy(
        _FakeGlobalSecurityRepository(
            _user_assignment("p6-no-global-privileges", modules=("projects",)),
            no_global,
        ),
        _FakeProjectPolicy(True),
    )

    assert not no_module.is_allowed(_authorization_context(), Permission.PROJECT_READ)
    assert resolver.calls == []
    assert not no_resolver.is_allowed(_authorization_context(), Permission.PROJECT_READ)

