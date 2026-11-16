from __future__ import annotations

import pytest

from construction_pm.p6_project_privileges import (
    PRIVILEGE_BY_KEY,
    PROJECT_PRIVILEGES,
    ORACLE_V26_CHECKBOX_PRIVILEGE_KEYS,
    oracle_v26_project_privileges,
    ProjectPrivilegeGroup,
    expand_project_privileges,
    privilege_keys_for_group,
    set_privilege_group,
)


def test_v26_privilege_catalogue_has_unique_keys_and_all_expected_groups():
    keys = [item.key for item in PROJECT_PRIVILEGES]
    assert len(keys) == len(set(keys)) == len(PRIVILEGE_BY_KEY)
    assert {item.group for item in PROJECT_PRIVILEGES} == set(ProjectPrivilegeGroup)
    assert {group.value for group in ProjectPrivilegeGroup} == {
        "activities", "codes", "eps_projects", "project_data",
        "related_applications", "resource_assignments", "tools", "views_reports",
    }


def test_delete_privilege_inherits_edit_assign_and_view():
    expanded = expand_project_privileges({"issue.delete"})
    assert {"issue.delete", "issue.edit", "issue.assign", "issue.view"} <= expanded


def test_unknown_privilege_fails_closed():
    with pytest.raises(ValueError, match="UNKNOWN_PROJECT_PRIVILEGE"):
        expand_project_privileges({"project.superuser"})



def test_v26_oracle_checkbox_catalogue_covers_all_eight_detail_categories():
    labels = {item.label for item in PROJECT_PRIVILEGES}
    required = {
        "Add/Edit Activities Except Relationships",
        "Delete Activities",
        "Add/Edit/Delete Activity Relationships",
        "Add/Edit/Delete Expenses",
        "Add/Edit/Delete EPS Except Costs/Financials",
        "Edit EPS Costs/Financials",
        "Add Projects",
        "Delete Projects",
        "Edit Project Details Except Costs/Financials",
        "Add/Edit/Delete WBS Except Costs/Financials",
        "Edit WBS Costs/Financials",
        "View Project Costs/Financials",
        "Delete Project Data with Timesheet Actuals",
        "Delete Published Project Data",
        "Export Project Data",
        "Add/Edit/Delete Issues and Issue Thresholds",
        "Add/Edit/Delete Project Baselines",
        "Add/Edit/Delete Project Calendars",
        "Add/Edit/Delete Risks",
        "Add/Edit/Delete Template Documents",
        "Add/Edit/Delete Work Products and Documents",
        "Assign Project Baselines",
        "Approve Timesheets as Project Manager",
        "Administer Project External Applications",
        "Exchange Project Data with Primavera Unifier",
        "Exchange Project Data with Oracle Primavera Cloud",
        "Exchange Project Data with Gateway",
        "Add/Edit Activity Resource Requests",
        "Add/Edit/Delete Resource Assignments for Resource Planning",
        "Add/Edit/Delete Role Assignments for Resource Planning",
        "Edit Committed Flag for Resource Planning",
        "Edit Future Periods",
        "Edit Period Performance",
        "Apply Actuals",
        "Check In/Check Out Projects and Open Projects Exclusively",
        "Level Resources",
        "Schedule Projects",
        "Monitor Project Thresholds",
        "Store Period Performance",
        "Summarize Projects",
        "Edit Publication Priority",
        "Run Baseline Update",
        "Run Global Change",
        "Allow Integration with Primavera Unifier",
        "Perform Global Search & Replace",
        "Add/Edit Project Level Layouts",
        "Edit Project Reports",
        "Publish Project Website",
        "Add/Edit/Delete Project Visualizer Layouts",
    }
    assert required <= labels


def test_v26_combined_privileges_expand_only_to_documented_domain_targets():
    expanded = expand_project_privileges({
        "wbs.add_edit_delete_except_costs_financials",
        "issue_threshold.add_edit_delete",
        "project_activity_code.delete",
        "risk.add_edit_delete",
    })
    assert {
        "wbs.edit", "wbs.assign", "wbs.view",
        "issue.edit", "issue.assign", "issue.view",
        "threshold.edit", "threshold.assign", "threshold.view",
        "project_activity_code.add", "project_activity_code.edit",
        "project_activity_code.assign", "project_activity_code.view",
        "risk.edit", "risk.assign", "risk.view",
    } <= expanded
    assert "wbs.edit_costs_financials" not in expanded
    assert "project.view_costs_financials" not in expanded


def test_v26_template_document_requires_separate_work_product_document_grant():
    expanded = expand_project_privileges({"template_document.add_edit_delete"})
    assert "work_product_document.add_edit_delete" not in expanded
    assert "document.add_edit_delete" not in expanded



def test_v26_group_header_selects_and_clears_only_its_detail_window_group():
    selected = {"schedule.run", "activity.view"}
    with_activities = set_privilege_group(
        selected, ProjectPrivilegeGroup.ACTIVITIES, True
    )
    assert privilege_keys_for_group(ProjectPrivilegeGroup.ACTIVITIES) <= with_activities
    assert "schedule.run" in with_activities

    cleared = set_privilege_group(
        with_activities, ProjectPrivilegeGroup.ACTIVITIES, False
    )
    assert not (
        privilege_keys_for_group(ProjectPrivilegeGroup.ACTIVITIES) & cleared
    )
    assert "schedule.run" in cleared


def test_v26_group_header_rejects_unknown_privileges_and_group_names():
    with pytest.raises(ValueError, match="UNKNOWN_PROJECT_PRIVILEGE"):
        set_privilege_group({"made.up"}, ProjectPrivilegeGroup.ACTIVITIES, True)
    with pytest.raises(ValueError, match="UNKNOWN_PROJECT_PRIVILEGE_GROUP"):
        privilege_keys_for_group("not-a-v26-group")



def test_v26_tool_and_resource_period_dependencies_are_inherited_exactly():
    level = expand_project_privileges({"resource.level"})
    assert {"resource.level", "schedule.run"} <= level

    future_periods = expand_project_privileges({"assignment.future_periods.edit"})
    assert "activity.add_edit_except_relationships" in future_periods
    assert "project.view_costs_financials" not in future_periods

    period_performance = expand_project_privileges({"assignment.period_performance.edit"})
    assert {
        "activity.add_edit_except_relationships",
        "project.view_costs_financials",
    } <= period_performance

    stored = expand_project_privileges({"period_performance.store"})
    assert "activity.add_edit_except_relationships" in stored


def test_oracle_v26_checkbox_catalogue_is_separate_from_internal_authorization_keys():
    selectable = oracle_v26_project_privileges()
    assert tuple(item.key for item in selectable) == ORACLE_V26_CHECKBOX_PRIVILEGE_KEYS
    assert len(selectable) == len(ORACLE_V26_CHECKBOX_PRIVILEGE_KEYS)
    assert len(selectable) == 57
    assert {item.group for item in selectable} == set(ProjectPrivilegeGroup)
    assert "activity.view" not in {item.key for item in selectable}
    assert "project.create" not in {item.key for item in selectable}
    assert "activity.id.edit" in {item.key for item in selectable}
    assert "discussion_comment.delete" in {item.key for item in selectable}
    assert "eps_activity_code.delete" in {item.key for item in selectable}
