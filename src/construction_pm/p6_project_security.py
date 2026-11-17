"""Primavera P6 EPPM V26 Project Security Profile privilege catalogue.

The catalogue and prerequisite graph are transcribed from the official V26
HTML Help Privileges Detail Window. This module is deliberately independent
from CUBI organization roles and global security profiles.
"""
from __future__ import annotations

from dataclasses import dataclass

P6_PROJECT_SECURITY_HELP_URL = "https://docs.oracle.com/cd/G48897_01/p6help/en/102786.htm"
P6_PROJECT_SUPERUSER_PROFILE_ID = "p6-project-superuser"
P6_PROJECT_SUPERUSER_PROFILE_NAME = "Project Superuser"

# (stable privilege code, exact V26 label, exact Help category)
P6_PROJECT_PRIVILEGE_DEFINITIONS = (
    ("add_edit_activities_except_relationships", "Add/Edit Activities Except Relationships", "Activities"),
    ("delete_activities", "Delete Activities", "Activities"),
    ("add_edit_delete_activity_relationships", "Add/Edit/Delete Activity Relationships", "Activities"),
    ("edit_activity_id", "Edit Activity ID", "Activities"),
    ("add_edit_delete_expenses", "Add/Edit/Delete Expenses", "Activities"),
    ("delete_discussion_comments", "Delete Discussion Comments", "Activities"),
    ("add_project_activity_codes", "Add Project Activity Codes", "Codes"),
    ("edit_project_activity_codes", "Edit Project Activity Codes", "Codes"),
    ("delete_project_activity_codes", "Delete Project Activity Codes", "Codes"),
    ("add_eps_activity_codes", "Add EPS Activity Codes", "Codes"),
    ("edit_eps_activity_codes", "Edit EPS Activity Codes", "Codes"),
    ("delete_eps_activity_codes", "Delete EPS Activity Codes", "Codes"),
    ("add_edit_delete_eps_except_costs_financials", "Add/Edit/Delete EPS Except Costs/Financials", "EPS and Projects"),
    ("edit_eps_costs_financials", "Edit EPS Costs/Financials", "EPS and Projects"),
    ("add_projects", "Add Projects", "EPS and Projects"),
    ("delete_projects", "Delete Projects", "EPS and Projects"),
    ("edit_project_details_except_costs_financials", "Edit Project Details Except Costs/Financials", "EPS and Projects"),
    ("add_edit_delete_wbs_except_costs_financials", "Add/Edit/Delete WBS Except Costs/Financials", "EPS and Projects"),
    ("edit_wbs_costs_financials", "Edit WBS Costs/Financials", "EPS and Projects"),
    ("view_project_costs_financials", "View Project Costs/Financials", "EPS and Projects"),
    ("delete_project_data_with_timesheet_actuals", "Delete Project Data with Timesheet Actuals", "EPS and Projects"),
    ("delete_published_project_data", "Delete Published Project Data", "EPS and Projects"),
    ("export_project_data", "Export Project Data", "EPS and Projects"),
    ("add_edit_delete_issues_issue_thresholds", "Add/Edit/Delete Issues and Issue Thresholds", "Project Data"),
    ("add_edit_delete_project_baselines", "Add/Edit/Delete Project Baselines", "Project Data"),
    ("add_edit_delete_project_calendars", "Add/Edit/Delete Project Calendars", "Project Data"),
    ("add_edit_delete_risks", "Add/Edit/Delete Risks", "Project Data"),
    ("add_edit_delete_template_documents", "Add/Edit/Delete Template Documents", "Project Data"),
    ("add_edit_delete_work_products_documents", "Add/Edit/Delete Work Products and Documents", "Project Data"),
    ("assign_project_baselines", "Assign Project Baselines", "Project Data"),
    ("approve_timesheets_as_project_manager", "Approve Timesheets as Project Manager", "Project Data"),
    ("administer_project_external_applications", "Administer Project External Applications", "Related Applications"),
    ("exchange_project_data_with_unifier", "Exchange Project Data with Primavera Unifier", "Related Applications"),
    ("exchange_project_data_with_primavera_cloud", "Exchange Project Data with Oracle Primavera Cloud", "Related Applications"),
    ("exchange_project_data_with_gateway", "Exchange Project Data with Gateway", "Related Applications"),
    ("add_edit_activity_resource_requests", "Add/Edit Activity Resource Requests", "Resource Assignments"),
    ("add_edit_delete_resource_assignments_resource_planning", "Add/Edit/Delete Resource Assignments for Resource Planning", "Resource Assignments"),
    ("add_edit_delete_role_assignments_resource_planning", "Add/Edit/Delete Role Assignments for Resource Planning", "Resource Assignments"),
    ("edit_committed_flag_resource_planning", "Edit Committed Flag for Resource Planning", "Resource Assignments"),
    ("edit_future_periods", "Edit Future Periods", "Resource Assignments"),
    ("edit_period_performance", "Edit Period Performance", "Resource Assignments"),
    ("apply_actuals", "Apply Actuals", "Tools"),
    ("check_in_out_projects_open_exclusively", "Check In/Check Out Projects and Open Projects Exclusively", "Tools"),
    ("level_resources", "Level Resources", "Tools"),
    ("schedule_projects", "Schedule Projects", "Tools"),
    ("monitor_project_thresholds", "Monitor Project Thresholds", "Tools"),
    ("store_period_performance", "Store Period Performance", "Tools"),
    ("summarize_projects", "Summarize Projects", "Tools"),
    ("edit_publication_priority", "Edit Publication Priority", "Tools"),
    ("run_baseline_update", "Run Baseline Update", "Tools"),
    ("run_global_change", "Run Global Change", "Tools"),
    ("allow_integration_with_unifier", "Allow Integration with Primavera Unifier", "Tools"),
    ("perform_global_search_replace", "Perform Global Search & Replace", "Tools"),
    ("add_edit_project_level_layouts", "Add/Edit Project Level Layouts", "Views and Reports"),
    ("edit_project_reports", "Edit Project Reports", "Views and Reports"),
    ("publish_project_website", "Publish Project Website", "Views and Reports"),
    ("add_edit_delete_project_visualizer_layouts", "Add/Edit/Delete Project Visualizer Layouts", "Views and Reports"),
)
P6_PROJECT_PRIVILEGE_IDS = frozenset(item[0] for item in P6_PROJECT_PRIVILEGE_DEFINITIONS)
P6_PROJECT_PRIVILEGE_CATEGORIES = (
    "Activities", "Codes", "EPS and Projects", "Project Data",
    "Related Applications", "Resource Assignments", "Tools", "Views and Reports",
)

# Only prerequisites explicitly stated by V26 Help are included here.
P6_PROJECT_PRIVILEGE_DEPENDENCIES = {
    "edit_activity_id": frozenset({"add_edit_activities_except_relationships"}),
    "delete_project_activity_codes": frozenset({"add_project_activity_codes", "edit_project_activity_codes"}),
    "add_project_activity_codes": frozenset({"edit_project_activity_codes"}),
    "delete_eps_activity_codes": frozenset({"add_eps_activity_codes", "edit_eps_activity_codes"}),
    "add_eps_activity_codes": frozenset({"edit_eps_activity_codes"}),
    "edit_wbs_costs_financials": frozenset({"add_edit_delete_wbs_except_costs_financials", "view_project_costs_financials"}),
    "assign_project_baselines": frozenset({"edit_project_details_except_costs_financials"}),
    "add_edit_delete_template_documents": frozenset({"add_edit_delete_work_products_documents"}),
    "edit_period_performance": frozenset({"add_edit_activities_except_relationships", "view_project_costs_financials"}),
    "store_period_performance": frozenset({"add_edit_activities_except_relationships"}),
    "level_resources": frozenset({"schedule_projects"}),
}


class ProjectSecurityError(ValueError):
    """Invalid V26 Project Security Profile or privilege operation."""


def normalize_project_privileges(privileges: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    selected = set(privileges)
    if selected - P6_PROJECT_PRIVILEGE_IDS:
        raise ProjectSecurityError("UNKNOWN_PROJECT_SECURITY_PRIVILEGE")
    changed = True
    while changed:
        changed = False
        for privilege in tuple(selected):
            missing = P6_PROJECT_PRIVILEGE_DEPENDENCIES.get(privilege, frozenset()) - selected
            if missing:
                selected.update(missing)
                changed = True
    return tuple(code for code, _, _ in P6_PROJECT_PRIVILEGE_DEFINITIONS if code in selected)


@dataclass(frozen=True)
class P6ProjectSecurityProfile:
    tenant_id: str
    profile_id: str
    name: str
    privileges: tuple[str, ...] = ()
    active: bool = True
    revision: int = 1
    is_default: bool = False
    built_in: bool = False
    description: str = ""

    def validate(self) -> None:
        if not all(isinstance(value, str) and value.strip() for value in (
            self.tenant_id, self.profile_id, self.name
        )):
            raise ProjectSecurityError("PROJECT_SECURITY_PROFILE_REQUIRED")
        if (len(self.profile_id) > 120 or len(self.name) > 160
                or isinstance(self.revision, bool) or not isinstance(self.revision, int)
                or self.revision < 1 or not isinstance(self.active, bool)
                or not isinstance(self.is_default, bool) or not isinstance(self.built_in, bool)
                or not isinstance(self.description, str) or len(self.description) > 2000):
            raise ProjectSecurityError("PROJECT_SECURITY_PROFILE_INVALID")
        if not isinstance(self.privileges, tuple) or any(
            not isinstance(code, str) or not code.strip() for code in self.privileges
        ):
            raise ProjectSecurityError("PROJECT_SECURITY_PRIVILEGE_INVALID")
        if len(set(self.privileges)) != len(self.privileges):
            raise ProjectSecurityError("DUPLICATE_PROJECT_SECURITY_PRIVILEGE")
        if set(self.privileges) != set(normalize_project_privileges(self.privileges)):
            raise ProjectSecurityError("PROJECT_SECURITY_PRIVILEGE_DEPENDENCY_MISSING")
        if self.built_in and (self.profile_id != P6_PROJECT_SUPERUSER_PROFILE_ID
                              or self.name != P6_PROJECT_SUPERUSER_PROFILE_NAME
                              or set(self.privileges) != set(P6_PROJECT_PRIVILEGE_IDS)):
            raise ProjectSecurityError("PROJECT_SUPERUSER_PROFILE_INVALID")
        if not self.built_in and self.profile_id == P6_PROJECT_SUPERUSER_PROFILE_ID:
            raise ProjectSecurityError("PROJECT_SUPERUSER_PROFILE_ID_RESERVED")


def require_project_privilege(policy, auth_context, privilege_code: str) -> None:
    """Apply a named V26 project privilege when the composed policy supports it.

    Legacy standalone policies remain compatible; the production P6 global
    security policy exposes this method and fails closed without an OBS grant.
    """
    checker = getattr(policy, "require_project_privilege", None)
    if callable(checker):
        checker(auth_context, privilege_code)
