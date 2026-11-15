from __future__ import annotations

import pytest

from construction_pm.p6_project_privileges import (
    PRIVILEGE_BY_KEY,
    PROJECT_PRIVILEGES,
    ProjectPrivilegeGroup,
    expand_project_privileges,
)


def test_v26_privilege_catalogue_has_unique_keys_and_all_expected_groups():
    keys = [item.key for item in PROJECT_PRIVILEGES]
    assert len(keys) == len(set(keys)) == len(PRIVILEGE_BY_KEY)
    assert {item.group for item in PROJECT_PRIVILEGES} == set(ProjectPrivilegeGroup)


def test_delete_privilege_inherits_edit_assign_and_view():
    expanded = expand_project_privileges({"issue.delete"})
    assert {"issue.delete", "issue.edit", "issue.assign", "issue.view"} <= expanded


def test_unknown_privilege_fails_closed():
    with pytest.raises(ValueError, match="UNKNOWN_PROJECT_PRIVILEGE"):
        expand_project_privileges({"project.superuser"})
