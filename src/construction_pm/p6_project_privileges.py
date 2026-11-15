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
    CODES = "codes"
    EPS_PROJECTS = "eps_projects"
    PROJECT_DATA = "project_data"
    RELATED_APPLICATIONS = "related_applications"
    TIMESHEETS = "timesheets"
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

    # Explicit inheritance targets. P6 privilege inheritance is represented as
    # separate persisted capabilities so API checks never infer broad write.
    ProjectPrivilegeDefinition("activity.edit", ProjectPrivilegeGroup.ACTIVITIES, "Edit Activities", "Edit existing activities."),
    ProjectPrivilegeDefinition("activity.assign", ProjectPrivilegeGroup.ACTIVITIES, "Assign Activities", "Assign activities."),
    ProjectPrivilegeDefinition("eps.assign", ProjectPrivilegeGroup.EPS_PROJECTS, "Assign EPS", "Assign EPS responsibility."),
    ProjectPrivilegeDefinition("project.assign", ProjectPrivilegeGroup.EPS_PROJECTS, "Assign Projects", "Assign project responsibility."),
    ProjectPrivilegeDefinition("wbs.edit", ProjectPrivilegeGroup.EPS_PROJECTS, "Edit WBS", "Edit existing WBS elements."),
    ProjectPrivilegeDefinition("wbs.assign", ProjectPrivilegeGroup.EPS_PROJECTS, "Assign WBS", "Assign WBS responsibility."),
    ProjectPrivilegeDefinition("expense.view", ProjectPrivilegeGroup.PROJECT_DATA, "View Expenses", "View project expenses."),
    ProjectPrivilegeDefinition("expense.edit", ProjectPrivilegeGroup.PROJECT_DATA, "Edit Expenses", "Edit existing expenses."),
    ProjectPrivilegeDefinition("expense.assign", ProjectPrivilegeGroup.PROJECT_DATA, "Assign Expenses", "Assign expenses."),
    ProjectPrivilegeDefinition("threshold.edit", ProjectPrivilegeGroup.PROJECT_DATA, "Edit Thresholds", "Edit existing thresholds."),
    ProjectPrivilegeDefinition("threshold.assign", ProjectPrivilegeGroup.PROJECT_DATA, "Assign Thresholds", "Assign thresholds."),
    ProjectPrivilegeDefinition("risk.edit", ProjectPrivilegeGroup.PROJECT_DATA, "Edit Risks", "Edit existing risks."),
    ProjectPrivilegeDefinition("risk.assign", ProjectPrivilegeGroup.PROJECT_DATA, "Assign Risks", "Assign risks."),
    ProjectPrivilegeDefinition("baseline.edit", ProjectPrivilegeGroup.PROJECT_DATA, "Edit Baselines", "Edit existing baselines."),
    ProjectPrivilegeDefinition("baseline.assign", ProjectPrivilegeGroup.PROJECT_DATA, "Assign Baselines", "Assign baselines."),
    ProjectPrivilegeDefinition("document.edit", ProjectPrivilegeGroup.PROJECT_DATA, "Edit Documents", "Edit project documents."),
    ProjectPrivilegeDefinition("document.assign", ProjectPrivilegeGroup.PROJECT_DATA, "Assign Documents", "Assign project documents."),
    ProjectPrivilegeDefinition("resource_assignment.edit", ProjectPrivilegeGroup.RESOURCE_ASSIGNMENTS, "Edit Resource Assignments", "Edit existing resource assignments."),
    ProjectPrivilegeDefinition("resource_assignment.assign", ProjectPrivilegeGroup.RESOURCE_ASSIGNMENTS, "Assign Resource Assignments", "Assign resources."),
    ProjectPrivilegeDefinition("code.view", ProjectPrivilegeGroup.CODES, "View Codes", "View project and activity codes."),
    ProjectPrivilegeDefinition("code.edit", ProjectPrivilegeGroup.CODES, "Edit Codes", "Edit project and activity codes."),
    ProjectPrivilegeDefinition("code.assign", ProjectPrivilegeGroup.CODES, "Assign Codes", "Assign codes."),
    ProjectPrivilegeDefinition("timesheet.view", ProjectPrivilegeGroup.TIMESHEETS, "View Timesheets", "View timesheets."),
    ProjectPrivilegeDefinition("timesheet.edit", ProjectPrivilegeGroup.TIMESHEETS, "Edit Timesheets", "Edit timesheets."),
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
    ProjectPrivilegeDefinition("issue.edit", ProjectPrivilegeGroup.PROJECT_DATA, "Edit Issues", "Edit existing project issues."),
    ProjectPrivilegeDefinition("issue.assign", ProjectPrivilegeGroup.PROJECT_DATA, "Assign Issues", "Assign project issues."),
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
    ProjectPrivilegeDefinition("timesheet.approve", ProjectPrivilegeGroup.PROJECT_DATA, "Approve Timesheets as Project Manager", "Approve or reject submitted timesheets as a project manager."),
    ProjectPrivilegeDefinition("schedule.run", ProjectPrivilegeGroup.TOOLS, "Schedule Projects", "Run project scheduling."),
    ProjectPrivilegeDefinition("resource.level", ProjectPrivilegeGroup.TOOLS, "Level Resources", "Run resource leveling."),
    ProjectPrivilegeDefinition("actuals.apply", ProjectPrivilegeGroup.TOOLS, "Apply Actuals", "Apply actuals to project data."),
    ProjectPrivilegeDefinition("global_change.execute", ProjectPrivilegeGroup.TOOLS, "Run Global Change", "Execute global change."),
    ProjectPrivilegeDefinition("project.summarize", ProjectPrivilegeGroup.TOOLS, "Summarize Projects", "Summarize project data."),
    ProjectPrivilegeDefinition("baseline.update", ProjectPrivilegeGroup.TOOLS, "Run Baseline Update", "Update baselines assigned to projects with new project information."),
    ProjectPrivilegeDefinition("threshold.monitor", ProjectPrivilegeGroup.TOOLS, "Monitor Project Thresholds", "Run the threshold monitor for projects in P6 Professional."),
    ProjectPrivilegeDefinition("layout.save", ProjectPrivilegeGroup.VIEWS_REPORTS, "Save Layouts", "Save project layouts."),
    ProjectPrivilegeDefinition("report.run", ProjectPrivilegeGroup.VIEWS_REPORTS, "Run Reports", "Run project reports."),
    ProjectPrivilegeDefinition("project.export", ProjectPrivilegeGroup.VIEWS_REPORTS, "Export Project Data", "Export project data."),

    # Oracle P6 EPPM Help V26 checkbox-level privileges. These retain the
    # actual Help concepts; the shorter keys above remain CUBI route adapters.
    ProjectPrivilegeDefinition("discussion_comment.delete", ProjectPrivilegeGroup.ACTIVITIES, "Delete Discussion Comments", "Delete discussion comments assigned to activities."),
    ProjectPrivilegeDefinition("project_activity_code.add", ProjectPrivilegeGroup.CODES, "Add Project Activity Codes", "Create project activity codes and values."),
    ProjectPrivilegeDefinition("project_activity_code.edit", ProjectPrivilegeGroup.CODES, "Edit Project Activity Codes", "Modify project activity codes and create, modify, or remove their values."),
    ProjectPrivilegeDefinition("project_activity_code.delete", ProjectPrivilegeGroup.CODES, "Delete Project Activity Codes", "Remove project activity codes and values."),
    ProjectPrivilegeDefinition("eps_activity_code.add", ProjectPrivilegeGroup.CODES, "Add EPS Activity Codes", "Create EPS-level activity codes and values."),
    ProjectPrivilegeDefinition("eps_activity_code.edit", ProjectPrivilegeGroup.CODES, "Edit EPS Activity Codes", "Modify EPS-level activity codes and their values."),
    ProjectPrivilegeDefinition("eps_activity_code.delete", ProjectPrivilegeGroup.CODES, "Delete EPS Activity Codes", "Remove EPS-level activity codes and values."),
    ProjectPrivilegeDefinition("eps.add_edit_delete_except_costs_financials", ProjectPrivilegeGroup.EPS_PROJECTS, "Add/Edit/Delete EPS Except Costs/Financials", "Manage EPS nodes and non-financial EPS data."),
    ProjectPrivilegeDefinition("eps.edit_costs_financials", ProjectPrivilegeGroup.EPS_PROJECTS, "Edit EPS Costs/Financials", "Modify EPS budget logs, funding sources, and spending plans."),
    ProjectPrivilegeDefinition("project.add", ProjectPrivilegeGroup.EPS_PROJECTS, "Add Projects", "Create, copy, and paste projects within an EPS node."),
    ProjectPrivilegeDefinition("project.edit_details_except_costs_financials", ProjectPrivilegeGroup.EPS_PROJECTS, "Edit Project Details Except Costs/Financials", "Edit project preferences and project-level data excluding financial information."),
    ProjectPrivilegeDefinition("wbs.add_edit_delete_except_costs_financials", ProjectPrivilegeGroup.EPS_PROJECTS, "Add/Edit/Delete WBS Except Costs/Financials", "Manage WBS hierarchy and non-financial WBS data, including notebooks, earned-value settings, milestones, and dates."),
    ProjectPrivilegeDefinition("wbs.edit_costs_financials", ProjectPrivilegeGroup.EPS_PROJECTS, "Edit WBS Costs/Financials", "Modify project or WBS budget logs, funding sources, spending plans, and financial data."),
    ProjectPrivilegeDefinition("project.view_costs_financials", ProjectPrivilegeGroup.EPS_PROJECTS, "View Project Costs/Financials", "Display monetary values; without this privilege monetary values are masked and cannot be edited."),
    ProjectPrivilegeDefinition("project.delete_data_with_timesheet_actuals", ProjectPrivilegeGroup.EPS_PROJECTS, "Delete Project Data with Timesheet Actuals", "Delete activities and resource assignments that have timesheet actuals, in conjunction with their normal delete privileges."),
    ProjectPrivilegeDefinition("project.delete_published_data", ProjectPrivilegeGroup.EPS_PROJECTS, "Delete Published Project Data", "Delete published project data from the EPS page."),
    ProjectPrivilegeDefinition("project.export_data", ProjectPrivilegeGroup.EPS_PROJECTS, "Export Project Data", "Export project data, download grid data, and copy project or EPS data."),
    ProjectPrivilegeDefinition("issue_threshold.add_edit_delete", ProjectPrivilegeGroup.PROJECT_DATA, "Add/Edit/Delete Issues and Issue Thresholds", "Create, modify, and remove project issues and thresholds; also assign issue codes."),
    ProjectPrivilegeDefinition("project_baseline.add_edit_delete", ProjectPrivilegeGroup.PROJECT_DATA, "Add/Edit/Delete Project Baselines", "Create, modify, and remove project baselines."),
    ProjectPrivilegeDefinition("project_calendar.add_edit_delete", ProjectPrivilegeGroup.PROJECT_DATA, "Add/Edit/Delete Project Calendars", "Create, modify, and remove project calendars."),
    ProjectPrivilegeDefinition("risk.add_edit_delete", ProjectPrivilegeGroup.PROJECT_DATA, "Add/Edit/Delete Risks", "Create, modify, and remove project risks."),
    ProjectPrivilegeDefinition("template_document.add_edit_delete", ProjectPrivilegeGroup.PROJECT_DATA, "Add/Edit/Delete Template Documents", "Manage project template documents and, when configured, check out and start document reviews."),
    ProjectPrivilegeDefinition("work_product_document.add_edit_delete", ProjectPrivilegeGroup.PROJECT_DATA, "Add/Edit/Delete Work Products and Documents", "Manage project documents without a security policy and create document folders when the content repository is configured."),
    ProjectPrivilegeDefinition("project_baseline.assign", ProjectPrivilegeGroup.PROJECT_DATA, "Assign Project Baselines", "Assign project baselines; requires Edit Project Details Except Costs/Financials."),
    ProjectPrivilegeDefinition("external_application.administer", ProjectPrivilegeGroup.RELATED_APPLICATIONS, "Administer Project External Applications", "Modify entries in the External Applications feature."),
    ProjectPrivilegeDefinition("unifier.project_data.exchange", ProjectPrivilegeGroup.RELATED_APPLICATIONS, "Exchange Project Data with Primavera Unifier", "Exchange data with linked Primavera Unifier projects."),
    ProjectPrivilegeDefinition("opc.project_data.exchange", ProjectPrivilegeGroup.RELATED_APPLICATIONS, "Exchange Project Data with Oracle Primavera Cloud", "Exchange data with linked Oracle Primavera Cloud projects."),
    ProjectPrivilegeDefinition("gateway.project_data.exchange", ProjectPrivilegeGroup.RELATED_APPLICATIONS, "Exchange Project Data with Gateway", "Exchange data with projects linked through Primavera Gateway."),
    ProjectPrivilegeDefinition("activity_resource_request.add_edit", ProjectPrivilegeGroup.RESOURCE_ASSIGNMENTS, "Add/Edit Activity Resource Requests", "Create and modify activity resource requests."),
    ProjectPrivilegeDefinition("resource_planning_assignment.add_edit_delete", ProjectPrivilegeGroup.RESOURCE_ASSIGNMENTS, "Add/Edit/Delete Resource Assignments for Resource Planning", "Manage resource assignments on the Resources Planning page."),
    ProjectPrivilegeDefinition("role_planning_assignment.add_edit_delete", ProjectPrivilegeGroup.RESOURCE_ASSIGNMENTS, "Add/Edit/Delete Role Assignments for Resource Planning", "Manage role assignments on the Resources Planning page."),
    ProjectPrivilegeDefinition("resource_planning_assignment.committed_flag.edit", ProjectPrivilegeGroup.RESOURCE_ASSIGNMENTS, "Edit Committed Flag for Resource Planning", "Edit the committed flag on the Resources Planning page."),
    ProjectPrivilegeDefinition("assignment.future_periods.edit", ProjectPrivilegeGroup.RESOURCE_ASSIGNMENTS, "Edit Future Periods", "Edit future-period assignment values in the Resource Usage Spreadsheet."),
    ProjectPrivilegeDefinition("assignment.period_performance.edit", ProjectPrivilegeGroup.RESOURCE_ASSIGNMENTS, "Edit Period Performance", "Edit period performance units and costs."),
    ProjectPrivilegeDefinition("project.checkout_exclusive", ProjectPrivilegeGroup.TOOLS, "Check In/Check Out Projects and Open Projects Exclusively", "Check projects out for remote work, check them in, or acquire an exclusive project lock."),
    ProjectPrivilegeDefinition("period_performance.store", ProjectPrivilegeGroup.TOOLS, "Store Period Performance", "Store actual-this-period units and costs."),
    ProjectPrivilegeDefinition("publication_priority.edit", ProjectPrivilegeGroup.TOOLS, "Edit Publication Priority", "Edit project publication priority."),
    ProjectPrivilegeDefinition("unifier.integration.allow", ProjectPrivilegeGroup.TOOLS, "Allow Integration with Primavera Unifier", "Link projects to Primavera Unifier projects and schedule sheets."),
    ProjectPrivilegeDefinition("global_search_replace.execute", ProjectPrivilegeGroup.TOOLS, "Perform Global Search & Replace", "Update project, WBS, and activity information using Global Search & Replace."),
    ProjectPrivilegeDefinition("project_level_layout.add_edit", ProjectPrivilegeGroup.VIEWS_REPORTS, "Add/Edit Project Level Layouts", "Create, modify, and remove project-level layouts in Activities, Assignments, and WBS."),
    ProjectPrivilegeDefinition("project_report.edit", ProjectPrivilegeGroup.VIEWS_REPORTS, "Edit Project Reports", "Modify reports and report batches and export reports."),
    ProjectPrivilegeDefinition("project_website.publish", ProjectPrivilegeGroup.VIEWS_REPORTS, "Publish Project Website", "Publish a website for a project."),
    ProjectPrivilegeDefinition("project_visualizer_layout.add_edit_delete", ProjectPrivilegeGroup.VIEWS_REPORTS, "Add/Edit/Delete Project Visualizer Layouts", "Create, modify, and remove project layouts in Visualizer."),

    ProjectPrivilegeDefinition("expense.add_edit_delete", ProjectPrivilegeGroup.ACTIVITIES, "Add/Edit/Delete Expenses", "Create, modify, and remove expenses assigned to projects."),
    ProjectPrivilegeDefinition("activity.relationship.edit", ProjectPrivilegeGroup.ACTIVITIES, "Edit Activity Relationships", "Edit existing activity relationships."),
    ProjectPrivilegeDefinition("activity.relationship.assign", ProjectPrivilegeGroup.ACTIVITIES, "Assign Activity Relationships", "Assign activity relationships."),
    ProjectPrivilegeDefinition("activity.relationship.view", ProjectPrivilegeGroup.ACTIVITIES, "View Activity Relationships", "View activity relationships."),
    ProjectPrivilegeDefinition("project_activity_code.assign", ProjectPrivilegeGroup.CODES, "Assign Project Activity Codes", "Assign project activity codes."),
    ProjectPrivilegeDefinition("project_activity_code.view", ProjectPrivilegeGroup.CODES, "View Project Activity Codes", "View project activity codes."),
    ProjectPrivilegeDefinition("eps_activity_code.assign", ProjectPrivilegeGroup.CODES, "Assign EPS Activity Codes", "Assign EPS activity codes."),
    ProjectPrivilegeDefinition("eps_activity_code.view", ProjectPrivilegeGroup.CODES, "View EPS Activity Codes", "View EPS activity codes."),
    ProjectPrivilegeDefinition("calendar.edit", ProjectPrivilegeGroup.PROJECT_DATA, "Edit Project Calendars", "Edit existing project calendars."),
    ProjectPrivilegeDefinition("calendar.view", ProjectPrivilegeGroup.PROJECT_DATA, "View Project Calendars", "View project calendars."),
    ProjectPrivilegeDefinition("activity_resource_request.edit", ProjectPrivilegeGroup.RESOURCE_ASSIGNMENTS, "Edit Activity Resource Requests", "Edit existing activity resource requests."),
    ProjectPrivilegeDefinition("activity_resource_request.assign", ProjectPrivilegeGroup.RESOURCE_ASSIGNMENTS, "Assign Activity Resource Requests", "Assign activity resource requests."),
    ProjectPrivilegeDefinition("activity_resource_request.view", ProjectPrivilegeGroup.RESOURCE_ASSIGNMENTS, "View Activity Resource Requests", "View activity resource requests."),
    ProjectPrivilegeDefinition("resource_planning_assignment.edit", ProjectPrivilegeGroup.RESOURCE_ASSIGNMENTS, "Edit Resource Planning Assignments", "Edit resource planning assignments."),
    ProjectPrivilegeDefinition("resource_planning_assignment.assign", ProjectPrivilegeGroup.RESOURCE_ASSIGNMENTS, "Assign Resource Planning Assignments", "Assign resource planning assignments."),
    ProjectPrivilegeDefinition("resource_planning_assignment.view", ProjectPrivilegeGroup.RESOURCE_ASSIGNMENTS, "View Resource Planning Assignments", "View resource planning assignments."),
    ProjectPrivilegeDefinition("role_planning_assignment.edit", ProjectPrivilegeGroup.RESOURCE_ASSIGNMENTS, "Edit Role Planning Assignments", "Edit role planning assignments."),
    ProjectPrivilegeDefinition("role_planning_assignment.assign", ProjectPrivilegeGroup.RESOURCE_ASSIGNMENTS, "Assign Role Planning Assignments", "Assign role planning assignments."),
    ProjectPrivilegeDefinition("role_planning_assignment.view", ProjectPrivilegeGroup.RESOURCE_ASSIGNMENTS, "View Role Planning Assignments", "View role planning assignments."),
)

PRIVILEGE_BY_KEY = {item.key: item for item in PROJECT_PRIVILEGES}


# Explicit inheritance from the V26 Help hierarchy. Compound Oracle options
# are expanded deliberately; suffix-based guessing is unsafe for names such as
# add_edit_except_relationships and add_edit_delete.
PROJECT_PRIVILEGE_INHERITANCE: dict[str, frozenset[str]] = {
    "activity.add_edit": frozenset({"activity.edit", "activity.assign", "activity.view"}),
    "activity.add_edit_except_relationships": frozenset({"activity.edit", "activity.assign", "activity.view"}),
    "activity.delete": frozenset({"activity.edit", "activity.assign", "activity.view"}),
    "activity.relationship.add_edit_delete": frozenset({"activity.relationship.edit", "activity.relationship.assign", "activity.relationship.view"}),
    "expense.add_edit": frozenset({"expense.edit", "expense.assign", "expense.view"}),
    "expense.add_edit_delete": frozenset({"expense.edit", "expense.assign", "expense.view"}),
    "expense.delete": frozenset({"expense.edit", "expense.assign", "expense.view"}),
    "eps.add_edit_delete_except_costs_financials": frozenset({"eps.edit", "eps.assign", "eps.view"}),
    "eps.edit": frozenset({"eps.assign", "eps.view"}),
    "project.add": frozenset({"project.edit", "project.assign", "project.view"}),
    "project.create": frozenset({"project.edit", "project.assign", "project.view"}),
    "project.delete": frozenset({"project.edit", "project.assign", "project.view"}),
    "project.edit": frozenset({"project.assign", "project.view"}),
    "project_activity_code.add": frozenset({"project_activity_code.edit", "project_activity_code.assign", "project_activity_code.view"}),
    "project_activity_code.delete": frozenset({"project_activity_code.add", "project_activity_code.edit", "project_activity_code.assign", "project_activity_code.view"}),
    "eps_activity_code.add": frozenset({"eps_activity_code.edit", "eps_activity_code.assign", "eps_activity_code.view"}),
    "eps_activity_code.delete": frozenset({"eps_activity_code.add", "eps_activity_code.edit", "eps_activity_code.assign", "eps_activity_code.view"}),
    "wbs.add_edit": frozenset({"wbs.edit", "wbs.assign", "wbs.view"}),
    "wbs.add_edit_delete_except_costs_financials": frozenset({"wbs.edit", "wbs.assign", "wbs.view"}),
    "wbs.delete": frozenset({"wbs.edit", "wbs.assign", "wbs.view"}),
    "issue.add_edit": frozenset({"issue.edit", "issue.assign", "issue.view"}),
    "issue.delete": frozenset({"issue.edit", "issue.assign", "issue.view"}),
    "issue_threshold.add_edit_delete": frozenset({"issue.edit", "issue.assign", "issue.view", "threshold.edit", "threshold.assign", "threshold.view"}),
    "threshold.add_edit": frozenset({"threshold.edit", "threshold.assign", "threshold.view"}),
    "threshold.delete": frozenset({"threshold.edit", "threshold.assign", "threshold.view"}),
    "risk.add_edit": frozenset({"risk.edit", "risk.assign", "risk.view"}),
    "risk.add_edit_delete": frozenset({"risk.edit", "risk.assign", "risk.view"}),
    "risk.delete": frozenset({"risk.edit", "risk.assign", "risk.view"}),
    "project_baseline.add_edit_delete": frozenset({"baseline.edit", "baseline.assign", "baseline.view"}),
    "project_calendar.add_edit_delete": frozenset({"calendar.edit", "calendar.assign", "calendar.view"}),
    "document.add_edit_delete": frozenset({"document.edit", "document.assign", "document.view"}),
    "work_product_document.add_edit_delete": frozenset({"document.edit", "document.assign", "document.view"}),
    "resource_assignment.add_edit": frozenset({"resource_assignment.edit", "resource_assignment.assign", "resource_assignment.view"}),
    "resource_assignment.delete": frozenset({"resource_assignment.edit", "resource_assignment.assign", "resource_assignment.view"}),
    "resource_planning_assignment.add_edit_delete": frozenset({"resource_planning_assignment.edit", "resource_planning_assignment.assign", "resource_planning_assignment.view"}),
    "role_planning_assignment.add_edit_delete": frozenset({"role_planning_assignment.edit", "role_planning_assignment.assign", "role_planning_assignment.view"}),
    "activity_resource_request.add_edit": frozenset({"activity_resource_request.edit", "activity_resource_request.assign", "activity_resource_request.view"}),
    "code.edit": frozenset({"code.assign", "code.view"}),
    "code.assign": frozenset({"code.view"}),
    "timesheet.edit": frozenset({"timesheet.view"}),
}


def expand_project_privileges(selected: set[str] | frozenset[str]) -> frozenset[str]:
    """Apply only explicit, Help-reviewed privilege inheritance and fail closed."""
    unknown = set(selected) - PRIVILEGE_BY_KEY.keys()
    if unknown:
        raise ValueError("UNKNOWN_PROJECT_PRIVILEGE")
    result = set(selected)
    pending = list(selected)
    while pending:
        key = pending.pop()
        for inherited in PROJECT_PRIVILEGE_INHERITANCE.get(key, frozenset()):
            if inherited not in PRIVILEGE_BY_KEY:
                raise ValueError("PROJECT_PRIVILEGE_INHERITANCE_TARGET_MISSING")
            if inherited not in result:
                result.add(inherited)
                pending.append(inherited)
    return frozenset(result)


LEGACY_PROJECT_PERMISSION_CODES = frozenset({
    "project.read", "project.write", "project.schedule", "project.admin",
})


def normalize_project_privileges(selected: tuple[str, ...] | list[str] | set[str] | frozenset[str]) -> tuple[str, ...]:
    """Validate and normalize a profile's legacy or granular P6 grants.

    Legacy permissions remain readable during migration. Granular privileges
    are expanded according to P6 inheritance and stored in deterministic order.
    """
    values = tuple(selected)
    if any(not isinstance(value, str) for value in values):
        raise ValueError("UNKNOWN_PROJECT_PRIVILEGE")
    unique = set(values)
    if len(unique) != len(values):
        raise ValueError("DUPLICATE_PROJECT_PRIVILEGE")
    legacy = unique & LEGACY_PROJECT_PERMISSION_CODES
    granular = unique - LEGACY_PROJECT_PERMISSION_CODES
    expanded = set(expand_project_privileges(granular)) if granular else set()
    if unique != legacy | granular:
        raise ValueError("UNKNOWN_PROJECT_PRIVILEGE")
    return tuple(sorted(legacy | expanded))
