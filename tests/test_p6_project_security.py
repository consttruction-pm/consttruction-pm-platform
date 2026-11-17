import pytest

from construction_pm.p6_project_security import (
    P6_PROJECT_SECURITY_HELP_URL,
    P6_PROJECT_PRIVILEGE_CATEGORIES,
    P6_PROJECT_PRIVILEGE_DEFINITIONS,
    P6_PROJECT_PRIVILEGE_DEPENDENCIES,
    P6_PROJECT_PRIVILEGE_IDS,
    P6ProjectSecurityProfile,
    ProjectSecurityError,
    normalize_project_privileges,
)


def test_v26_project_privilege_catalogue_has_all_eight_help_categories():
    assert P6_PROJECT_SECURITY_HELP_URL == "https://docs.oracle.com/cd/G48897_01/p6help/en/102786.htm"
    assert tuple(dict.fromkeys(category for _, _, category in P6_PROJECT_PRIVILEGE_DEFINITIONS)) == P6_PROJECT_PRIVILEGE_CATEGORIES
    assert len(P6_PROJECT_PRIVILEGE_IDS) == len(P6_PROJECT_PRIVILEGE_DEFINITIONS)
    assert len(P6_PROJECT_PRIVILEGE_IDS) >= 50


def test_v26_project_privilege_dependencies_normalize_only_documented_prerequisites():
    assert set(normalize_project_privileges(("edit_activity_id",))) == {"edit_activity_id"}
    assert set(normalize_project_privileges(("delete_project_activity_codes",))) == {
        "delete_project_activity_codes", "add_project_activity_codes",
        "edit_project_activity_codes",
    }
    assert set(normalize_project_privileges(("edit_wbs_costs_financials",))) == {
        "edit_wbs_costs_financials", "view_project_costs_financials",
    }
    assert set(normalize_project_privileges(("level_resources",))) == {
        "level_resources", "schedule_projects"
    }


def test_project_security_profile_rejects_unknown_or_missing_prerequisite():
    with pytest.raises(ProjectSecurityError, match="UNKNOWN_PROJECT_SECURITY_PRIVILEGE"):
        normalize_project_privileges(("project.superuser",))
    with pytest.raises(ProjectSecurityError, match="PROJECT_SECURITY_PRIVILEGE_REQUIREMENT_MISSING"):
        P6ProjectSecurityProfile(
            "tenant-a", "profile-a", "Profile A", ("edit_activity_id",)
        ).validate()


def test_project_security_profile_accepts_normalized_privilege_set():
    profile = P6ProjectSecurityProfile(
        "tenant-a", "profile-a", "Profile A",
        normalize_project_privileges((
            "edit_activity_id", "add_edit_activities_except_relationships",
            "edit_wbs_costs_financials", "add_edit_delete_wbs_except_costs_financials",
        )),
    )
    profile.validate()


def test_project_superuser_name_is_reserved_for_the_builtin_profile():
    with pytest.raises(ProjectSecurityError, match="PROJECT_SUPERUSER_PROFILE_NAME_RESERVED"):
        P6ProjectSecurityProfile(
            "tenant-a", "custom-superuser", "Project Superuser", ()
        ).validate()
