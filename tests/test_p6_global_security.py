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
    ordinary = profile("Portfolio Admin", built_in=False, privileges=("portfolio.view",))
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
        "tenant-a", "admin", ADMIN_SUPERUSER, (), True, False, 1
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
        module_access=("p6-web",),
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
        module_access=("p6-web", "p6-web"),
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
        profile(ADMIN_SUPERUSER, privileges=("global.user.edit",)).validate()
    with pytest.raises(GlobalSecurityError, match="NO_GLOBAL_PRIVILEGES_MUST_BE_EMPTY"):
        profile(NO_GLOBAL_PRIVILEGES, privileges=("global.user.view",)).validate()
    with pytest.raises(GlobalSecurityError, match="UNKNOWN_BUILTIN_GLOBAL_SECURITY_PROFILE"):
        profile("Custom", privileges=()).validate()
