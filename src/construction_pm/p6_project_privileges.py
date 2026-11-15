"""Oracle Primavera P6 EPPM V26 project-security privilege catalogue.

Stable CUBI keys are intentionally separate from display labels and Oracle UI text.
Do not authorize an endpoint merely because a key exists here: route-level mappings
must be explicit and tested before a privilege is enabled for production profiles.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ProjectPrivilegeGroup(StrEnum):
    ACTIVITIES = "activities"
    EPS_PROJECTS = "eps_projects"
    PROJECT_DATA = "project_data"
    RELATED_APPLICATIONS = "related_applications"
    RESOURCE_ASSIGNMENTS = "resource_assignments"
    TOOLS = "tools"
    VIEWS_REPORTS = "views_reports"


@dataclass(frozen=True, slots=True)
class ProjectPrivilegeDefinition:
    key: str
    group: ProjectPrivilegeGroup
    label: str
    description: str


# Keys are stable internal identifiers. Labels/descriptions follow the V26 Help
# privilege concepts; this catalogue does not imply endpoint enforcement.
PROJECT_PRIVILEGES: tuple[ProjectPrivilegeDefinition, ...] = (
    ProjectPrivilegeDefinition("activity.view", ProjectPrivilegeGroup.ACTIVITIES, "View Activities", "View activity data."),
    ProjectPrivilegeDefinition("activity.add_edit", ProjectPrivilegeGroup.ACTIVITIES, "Add/Edit Activities", "Create and edit activities."),
    ProjectPrivilegeDefinition("activity.add_edit_except_relationships", ProjectPrivilegeGroup.ACTIVITIES, "Add/Edit Activities Except Relationships", "Edit activity fields without changing relationships."),
    ProjectPrivilegeDefinition("activity.delete", ProjectPrivilegeGroup.ACTIVITIES, "Delete Activities", "Delete activities."),
    ProjectPrivilegeDefinition("activity.id.edit", ProjectPrivilegeGroup.ACTIVITIES, "Edit Activity ID", "Change activity identifiers."),
    ProjectPrivilegeDefinition("activity.relationship.add_edit_delete", ProjectPrivilegeGroup.ACTIVITIES, "Add/Edit/Delete Activity Relationships", "Create, edit and delete activity relationships."),
    ProjectPrivilegeDefinition("activity.code.assign", ProjectPrivilegeGroup.ACTIVITIES, "Assign Activity Codes", "Assign activity codes."),
    ProjectPrivilegeDefinition("eps.view", ProjectPrivilegeGroup.EPS_PROJECTS, "View EPS", "View enterprise project structure."),
    ProjectPrivilegeDefinition("eps.edit", ProjectPrivilegeGroup.EPS_PROJECTS, "Edit EPS", "Edit EPS nodes and properties."),
    ProjectPrivilegeDefinition("project.view", ProjectPrivilegeGroup.EPS_PROJECTS, "View Projects", "View project data."),
    ProjectPrivilegeDefinition("project.create", ProjectPrivilegeGroup.EPS_PROJECTS, "Create Projects", "Create projects."),
    ProjectPrivilegeDefinition("project.delete", ProjectPrivilegeGroup.EPS_PROJECTS, "Delete Projects", "Delete projects."),
    ProjectPrivilegeDefinition("project.edit", ProjectPrivilegeGroup.EPS_PROJECTS, "Edit Project Properties", "Edit project properties."),
    ProjectPrivilegeDefinition("wbs.view", ProjectPrivilegeGroup.EPS_PROJECTS, "View WBS", "View work breakdown structure."),
    ProjectPrivilegeDefinition("wbs.add_edit", ProjectPrivilegeGroup.EPS_PROJECTS, "Add/Edit WBS", "Create and edit WBS elements."),
    ProjectPrivilegeDefinition("wbs.delete", ProjectPrivilegeGroup.EPS_PROJECTS, "Delete WBS", "Delete WBS elements."),
    ProjectPrivilegeDefinition("expense.add_edit", ProjectPrivilegeGroup.PROJECT_DATA, "Add/Edit Expenses", "Create and edit project expenses."),
    ProjectPrivilegeDefinition("expense.delete", ProjectPrivilegeGroup.PROJECT_DATA, "Delete Expenses", "Delete project expenses."),
    ProjectPrivilegeDefinition("issue.view", ProjectPrivilegeGroup.PROJECT_DATA, "View Issues", "View project issues."),
    ProjectPrivilegeDefinition("issue.add_edit", ProjectPrivilegeGroup.PROJECT_DATA, "Add/Edit Issues", "Create and edit project issues."),
    ProjectPrivilegeDefinition("issue.delete", ProjectPrivilegeGroup.PROJECT_DATA, "Delete Issues", "Delete project issues."),
    ProjectPrivilegeDefinition("threshold.view", ProjectPrivilegeGroup.PROJECT_DATA, "View Thresholds", "View project thresholds."),
    ProjectPrivilegeDefinition("threshold.add_edit", ProjectPrivilegeGroup.PROJECT_DATA, "Add/Edit Thresholds", "Create and edit thresholds."),
    ProjectPrivilegeDefinition("threshold.delete", ProjectPrivilegeGroup.PROJECT_DATA, "Delete Thresholds", "Delete thresholds."),
    ProjectPrivilegeDefinition("risk.view", ProjectPrivilegeGroup.PROJECT_DATA, "View Risks", "View project risks."),
    ProjectPrivilegeDefinition("risk.add_edit", ProjectPrivilegeGroup.PROJECT_DATA, "Add/Edit Risks", "Create and edit risks."),
    ProjectPrivilegeDefinition("risk.delete", ProjectPrivilegeGroup.PROJECT_DATA, "Delete Risks", "Delete risks."),
    ProjectPrivilegeDefinition("baseline.view", ProjectPrivilegeGroup.PROJECT_DATA, "View Baselines", "View project baselines."),
    ProjectPrivilegeDefinition("baseline.create_update", ProjectPrivilegeGroup.PROJECT_DATA, "Create/Update Baselines", "Create and update baselines."),
    ProjectPrivilegeDefinition("calendar.assign", ProjectPrivilegeGroup.PROJECT_DATA, "Assign Calendars", "Assign calendars to project data."),
    ProjectPrivilegeDefinition("document.view", ProjectPrivilegeGroup.PROJECT_DATA, "View Documents", "View project documents."),
    ProjectPrivilegeDefinition("document.add_edit_delete", ProjectPrivilegeGroup.PROJECT_DATA, "Add/Edit/Delete Documents", "Manage project documents."),
    ProjectPrivilegeDefinition("resource_assignment.view", ProjectPrivilegeGroup.RESOURCE_ASSIGNMENTS, "View Resource Assignments", "View resource assignments."),
    ProjectPrivilegeDefinition("resource_assignment.add_edit", ProjectPrivilegeGroup.RESOURCE_ASSIGNMENTS, "Add/Edit Resource Assignments", "Create and edit resource assignments."),
    ProjectPrivilegeDefinition("resource_assignment.delete", ProjectPrivilegeGroup.RESOURCE_ASSIGNMENTS, "Delete Resource Assignments", "Delete resource assignments."),
    ProjectPrivilegeDefinition("timesheet.approve", ProjectPrivilegeGroup.RELATED_APPLICATIONS, "Approve Timesheets", "Approve project-related timesheets."),
    ProjectPrivilegeDefinition("schedule.run", ProjectPrivilegeGroup.TOOLS, "Schedule Projects", "Run project scheduling."),
    ProjectPrivilegeDefinition("resource.level", ProjectPrivilegeGroup.TOOLS, "Level Resources", "Run resource leveling."),
    ProjectPrivilegeDefinition("actuals.apply", ProjectPrivilegeGroup.TOOLS, "Apply Actuals", "Apply actuals to project data."),
    ProjectPrivilegeDefinition("global_change.execute", ProjectPrivilegeGroup.TOOLS, "Run Global Change", "Execute global change."),
    ProjectPrivilegeDefinition("project.summarize", ProjectPrivilegeGroup.TOOLS, "Summarize Projects", "Summarize project data."),
    ProjectPrivilegeDefinition("baseline.update", ProjectPrivilegeGroup.TOOLS, "Update Baseline", "Update project baselines."),
    ProjectPrivilegeDefinition("layout.save", ProjectPrivilegeGroup.VIEWS_REPORTS, "Save Layouts", "Save project layouts."),
    ProjectPrivilegeDefinition("report.run", ProjectPrivilegeGroup.VIEWS_REPORTS, "Run Reports", "Run project reports."),
    ProjectPrivilegeDefinition("project.export", ProjectPrivilegeGroup.VIEWS_REPORTS, "Export Project Data", "Export project data."),
)

PRIVILEGE_BY_KEY = {item.key: item for item in PROJECT_PRIVILEGES}


def expand_project_privileges(selected: set[str] | frozenset[str]) -> frozenset[str]:
    """Apply the documented Add/Delete -> Edit/Assign/View hierarchy.

    This function only expands explicit, known privileges. It never grants
    unrelated capabilities and rejects unknown keys to fail closed.
    """
    unknown = set(selected) - PRIVILEGE_BY_KEY.keys()
    if unknown:
        raise ValueError("UNKNOWN_PROJECT_PRIVILEGE")
    result = set(selected)
    for key in tuple(result):
        if key.endswith(".delete"):
            stem = key[:-len(".delete")]
            result.update({f"{stem}.edit", f"{stem}.assign", f"{stem}.view"})
        elif key.endswith(".add_edit"):
            stem = key[:-len(".add_edit")]
            result.update({f"{stem}.assign", f"{stem}.view"})
        elif key.endswith(".edit"):
            stem = key[:-len(".edit")]
            result.update({f"{stem}.assign", f"{stem}.view"})
        elif key.endswith(".assign"):
            stem = key[:-len(".assign")]
            result.add(f"{stem}.view")
    # Only retain inherited keys represented by this versioned catalogue.
    # Some UI privileges intentionally have no generic CRUD inheritance.
    return frozenset(result & PRIVILEGE_BY_KEY.keys())
