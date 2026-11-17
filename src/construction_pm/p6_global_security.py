"""P6 EPPM V26 global security profile primitives.

This module models the global layer separately from CUBI organization roles and
project/OBS grants. Project authorization must still combine this result with
project security profile and OBS responsibility checks.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any, Protocol
from uuid import uuid4


ADMIN_SUPERUSER = "Admin Superuser"
NO_GLOBAL_PRIVILEGES = "No Global Privileges"
BUILTIN_GLOBAL_PROFILES = frozenset({ADMIN_SUPERUSER, NO_GLOBAL_PRIVILEGES})

P6_MODULE_ACCESS_OPTIONS = frozenset({
    "projects", "portfolios", "resources", "contributor",
    "enterprise_reports", "integration_api", "p6_analytics",
    "p6_professional", "team_member", "timesheet", "visualizer",
    "web_services",
})
P6_MAX_SELECTED_RESOURCE_ROOTS = 5
P6_GLOBAL_SECURITY_HELP_URL = "https://docs.oracle.com/cd/G48897_01/p6help/en/102785.htm"
P6_GLOBAL_PRIVILEGE_DEFINITIONS = (
    ("add_edit_delete_obs", "Add/Edit/Delete OBS", "Administration"),
    ("add_edit_delete_security_profiles", "Add/Edit/Delete Security Profiles", "Administration"),
    ("add_edit_delete_users", "Add/Edit/Delete Users", "Administration"),
    ("add_edit_delete_user_interface_views", "Add/Edit/Delete User Interface Views", "Administration"),
    ("edit_application_settings", "Edit Application Settings", "Administration"),
    ("provision_users_from_ldap", "Provision Users from LDAP", "Administration"),
    ("view_published_audit_data", "View Published Audit Data", "Administration"),
    ("global_activity_codes_add", "Add Global Activity Codes", "Codes"),
    ("global_activity_codes_edit", "Edit Global Activity Codes", "Codes"),
    ("global_activity_codes_delete", "Delete Global Activity Codes", "Codes"),
    ("global_issue_codes_add", "Add Global Issue Codes", "Codes"),
    ("global_issue_codes_edit", "Edit Global Issue Codes", "Codes"),
    ("global_issue_codes_delete", "Delete Global Issue Codes", "Codes"),
    ("project_codes_add", "Add Project Codes", "Codes"),
    ("project_codes_edit", "Edit Project Codes", "Codes"),
    ("project_codes_delete", "Delete Project Codes", "Codes"),
    ("resource_codes_add", "Add Resource Codes", "Codes"),
    ("resource_codes_edit", "Edit Resource Codes", "Codes"),
    ("resource_codes_delete", "Delete Resource Codes", "Codes"),
    ("role_codes_add", "Add Role Codes", "Codes"),
    ("role_codes_edit", "Edit Role Codes", "Codes"),
    ("role_codes_delete", "Delete Role Codes", "Codes"),
    ("assignment_codes_add", "Add Assignment Codes", "Codes"),
    ("assignment_codes_edit", "Edit Assignment Codes", "Codes"),
    ("assignment_codes_delete", "Delete Assignment Codes", "Codes"),
    ("secure_codes_add_delete", "Add/Delete Secure Codes", "Codes"),
    ("secure_codes_edit", "Edit Secure Codes", "Codes"),
    ("secure_codes_assign", "Assign Secure Codes", "Codes"),
    ("secure_codes_view", "View Secure Codes", "Codes"),
    ("add_edit_delete_categories_overhead_codes", "Add/Edit/Delete Categories and Overhead Codes", "Global Data"),
    ("add_edit_delete_cost_accounts", "Add/Edit/Delete Cost Accounts", "Global Data"),
    ("add_edit_delete_currencies", "Add/Edit/Delete Currencies", "Global Data"),
    ("add_edit_delete_locations", "Add/Edit/Delete Locations", "Global Data"),
    ("add_edit_delete_financial_period_calendars", "Add/Edit/Delete Financial Period Calendars", "Global Data"),
    ("add_edit_delete_funding_sources", "Add/Edit/Delete Funding Sources", "Global Data"),
    ("add_edit_delete_global_calendars", "Add/Edit/Delete Global Calendars", "Global Data"),
    ("add_edit_delete_global_portfolios", "Add/Edit/Delete Global Portfolios", "Global Data"),
    ("add_edit_delete_risk_categories_matrices_thresholds", "Add/Edit/Delete Risk Categories, Matrices, and Thresholds", "Global Data"),
    ("add_edit_delete_timesheet_period_dates", "Add/Edit/Delete Timesheet Period Dates", "Global Data"),
    ("add_edit_delete_user_defined_fields", "Add/Edit/Delete User Defined fields", "Global Data"),
    ("add_edit_delete_stored_images", "Add/Edit/Delete Stored Images", "Global Data"),
    ("resources_add", "Add Resources", "Resources"),
    ("resources_edit", "Edit Resources", "Resources"),
    ("resources_delete", "Delete Resources", "Resources"),
    ("add_edit_delete_resource_calendars", "Add/Edit/Delete Resource Calendars", "Resources"),
    ("add_edit_delete_resource_curves", "Add/Edit/Delete Resource Curves", "Resources"),
    ("add_edit_delete_roles", "Add/Edit/Delete Roles", "Resources"),
    ("add_edit_delete_global_resource_role_teams", "Add/Edit/Delete Global Resource and Role Teams", "Resources"),
    ("add_edit_delete_rate_types_units_measure", "Add/Edit/Delete Rate Types and Units of Measure", "Resources"),
    ("view_resource_role_costs_financials", "View Resource and Role Costs/Financials", "Resources"),
    ("view_resource_role_proficiency", "View Resource Role Proficiency", "Resources"),
    ("approve_resource_timesheets", "Approve Resource Timesheets", "Resources"),
    ("add_edit_delete_activity_step_templates", "Add/Edit/Delete Activity Step Templates", "Templates"),
    ("add_edit_delete_issue_forms", "Add/Edit/Delete Issue Forms", "Templates"),
    ("add_edit_delete_microsoft_primavera_templates", "Add/Edit/Delete Microsoft and Primavera Templates", "Templates"),
    ("add_edit_delete_project_templates", "Add/Edit/Delete Project Templates", "Templates"),
    ("administer_global_external_applications", "Administer Global External Applications", "Tools"),
    ("administer_global_scheduled_services", "Administer Global Scheduled Services", "Tools"),
    ("administer_project_scheduled_services", "Administer Project Scheduled Services", "Tools"),
    ("edit_global_change_definitions", "Edit Global Change Definitions", "Tools"),
    ("import_p6_professional_xer_mpx", "Import P6 Professional XER and MPX", "Tools"),
    ("import_xlsx", "Import XLSX", "Tools"),
    ("import_xml", "Import XML", "Tools"),
    ("enable_work_offline", "Enable Work Offline", "Tools"),
    ("add_edit_delete_global_activity_assignment_layouts_views_filters", "Add/Edit/Delete Global Activity and Assignment Layouts, Views and Filters", "Views and Reports"),
    ("add_edit_delete_global_dashboards", "Add/Edit/Delete Global Dashboards", "Views and Reports"),
    ("add_edit_delete_global_project_wbs_portfolio_layouts_views_filters", "Add/Edit/Delete Global Project, WBS and Portfolio Layouts, Views and Filters", "Views and Reports"),
    ("add_edit_delete_global_reports", "Add/Edit/Delete Global Reports", "Views and Reports"),
    ("edit_global_tracking_layouts", "Edit Global Tracking Layouts", "Views and Reports"),
    ("edit_projects_from_scorecards", "Edit Projects from Scorecards", "Views and Reports"),
    ("add_edit_delete_global_visualizer_layouts", "Add/Edit/Delete Global Visualizer Layouts", "Views and Reports"),
    ("add_edit_delete_global_visualizer_filters", "Add/Edit/Delete Global Visualizer Filters", "Views and Reports"),
)
P6_GLOBAL_PRIVILEGE_IDS = frozenset(item[0] for item in P6_GLOBAL_PRIVILEGE_DEFINITIONS)
P6_GLOBAL_PRIVILEGE_DEPENDENCIES = {
    "global_activity_codes_add": frozenset({"global_activity_codes_edit"}),
    "global_activity_codes_delete": frozenset({"global_activity_codes_add", "global_activity_codes_edit"}),
    "global_issue_codes_add": frozenset({"global_issue_codes_edit"}),
    "global_issue_codes_delete": frozenset({"global_issue_codes_add", "global_issue_codes_edit"}),
    "project_codes_add": frozenset({"project_codes_edit"}),
    "project_codes_delete": frozenset({"project_codes_add", "project_codes_edit"}),
    "resource_codes_add": frozenset({"resource_codes_edit"}),
    "resource_codes_delete": frozenset({"resource_codes_add", "resource_codes_edit"}),
    "role_codes_add": frozenset({"role_codes_edit"}),
    "role_codes_delete": frozenset({"role_codes_add", "role_codes_edit"}),
    "assignment_codes_add": frozenset({"assignment_codes_edit"}),
    "assignment_codes_delete": frozenset({"assignment_codes_add", "assignment_codes_edit"}),
    "secure_codes_add_delete": frozenset({"secure_codes_edit", "secure_codes_assign", "secure_codes_view"}),
    "secure_codes_edit": frozenset({"secure_codes_assign", "secure_codes_view"}),
    "secure_codes_assign": frozenset({"secure_codes_view"}),
    "resources_add": frozenset({"resources_edit"}),
    "resources_delete": frozenset({"resources_add", "resources_edit"}),
}


def normalize_global_privileges(privileges):
    """Apply only dependency selections explicitly described by V26 HTML Help."""
    selected = set(privileges)
    if selected - P6_GLOBAL_PRIVILEGE_IDS:
        raise GlobalSecurityError("UNKNOWN_GLOBAL_SECURITY_PRIVILEGE")
    changed = True
    while changed:
        changed = False
        for privilege in tuple(selected):
            missing = P6_GLOBAL_PRIVILEGE_DEPENDENCIES.get(privilege, frozenset()) - selected
            if missing:
                selected.update(missing)
                changed = True
    return tuple(item[0] for item in P6_GLOBAL_PRIVILEGE_DEFINITIONS if item[0] in selected)



class GlobalSecurityError(ValueError):
    """Invalid or unauthorized P6 global-security operation."""


@dataclass(frozen=True)
class GlobalSecurityProfile:
    tenant_id: str
    profile_id: str
    name: str
    privileges: tuple[str, ...]
    built_in: bool = False
    active: bool = True
    revision: int = 1
    description: str = ""
    is_default: bool = False

    def validate(self) -> None:
        if not all(isinstance(v, str) and v.strip()
                   for v in (self.tenant_id, self.profile_id, self.name)):

            raise GlobalSecurityError("GLOBAL_SECURITY_PROFILE_REQUIRED")
        if (len(self.profile_id) > 120 or len(self.name) > 160
                or not isinstance(self.description, str) or len(self.description) > 2000):
            raise GlobalSecurityError("GLOBAL_SECURITY_PROFILE_INVALID")
        if self.revision < 1:
            raise GlobalSecurityError("GLOBAL_SECURITY_PROFILE_REVISION_INVALID")
        if any(not isinstance(v, str) or not v.strip() for v in self.privileges):
            raise GlobalSecurityError("GLOBAL_SECURITY_PRIVILEGE_INVALID")
        if len(set(self.privileges)) != len(self.privileges):
            raise GlobalSecurityError("DUPLICATE_GLOBAL_SECURITY_PRIVILEGE")
        if set(self.privileges) - P6_GLOBAL_PRIVILEGE_IDS:
            raise GlobalSecurityError("UNKNOWN_GLOBAL_SECURITY_PRIVILEGE")
        if set(self.privileges) != set(normalize_global_privileges(self.privileges)):
            raise GlobalSecurityError("GLOBAL_SECURITY_PRIVILEGE_DEPENDENCY_MISSING")
        if self.built_in and self.name not in BUILTIN_GLOBAL_PROFILES:
            raise GlobalSecurityError("UNKNOWN_BUILTIN_GLOBAL_SECURITY_PROFILE")
        if self.name in BUILTIN_GLOBAL_PROFILES and not self.built_in:
            raise GlobalSecurityError("BUILTIN_PROFILE_FLAG_REQUIRED")
        if not self.built_in and self.profile_id in {
            "p6-admin-superuser", "p6-no-global-privileges"
        }:
            raise GlobalSecurityError("BUILTIN_PROFILE_ID_RESERVED")
        if self.built_in:
            expected_id = ("p6-admin-superuser" if self.name == ADMIN_SUPERUSER
                           else "p6-no-global-privileges")
            if self.profile_id != expected_id:
                raise GlobalSecurityError("BUILTIN_PROFILE_ID_INVALID")
        if self.name == ADMIN_SUPERUSER and self.privileges:
            raise GlobalSecurityError("ADMIN_SUPERUSER_PRIVILEGES_ARE_IMPLICIT")
        if self.name == NO_GLOBAL_PRIVILEGES and self.privileges:
            raise GlobalSecurityError("NO_GLOBAL_PRIVILEGES_MUST_BE_EMPTY")


@dataclass(frozen=True)
class UserGlobalSecurity:
    tenant_id: str
    user_id: str
    profile_id: str
    module_access: tuple[str, ...]
    resource_access_mode: str
    resource_root_ids: tuple[str, ...]
    revision: int
    updated_by: str
    updated_at: datetime

    def validate(self) -> None:
        if not all(isinstance(v, str) and v.strip() for v in (
            self.tenant_id, self.user_id, self.profile_id, self.updated_by
        )):
            raise GlobalSecurityError("USER_GLOBAL_SECURITY_REQUIRED")
        if self.resource_access_mode not in {"none", "all", "selected"}:
            raise GlobalSecurityError("RESOURCE_ACCESS_MODE_INVALID")
        if self.resource_access_mode == "none" and self.resource_root_ids:
            raise GlobalSecurityError("RESOURCE_ROOTS_NOT_ALLOWED")
        if self.resource_access_mode == "all" and self.resource_root_ids:
            raise GlobalSecurityError("RESOURCE_ROOTS_NOT_ALLOWED")
        if self.resource_access_mode == "selected" and not self.resource_root_ids:
            raise GlobalSecurityError("RESOURCE_ROOTS_REQUIRED")
        if any(not isinstance(v, str) or not v.strip()
               for v in (*self.module_access, *self.resource_root_ids)):
            raise GlobalSecurityError("USER_GLOBAL_SECURITY_VALUE_INVALID")
        if len(set(self.resource_root_ids)) != len(self.resource_root_ids):
            raise GlobalSecurityError("DUPLICATE_RESOURCE_ROOT")
        if len(set(self.module_access)) != len(self.module_access):
            raise GlobalSecurityError("DUPLICATE_MODULE_ACCESS")
        if any(value not in P6_MODULE_ACCESS_OPTIONS for value in self.module_access):
            raise GlobalSecurityError("MODULE_ACCESS_INVALID")
        if "contributor" in self.module_access and len(self.module_access) > 1:
            raise GlobalSecurityError("CONTRIBUTOR_MODULE_ACCESS_EXCLUSIVE")
        if len(self.resource_root_ids) > P6_MAX_SELECTED_RESOURCE_ROOTS:
            raise GlobalSecurityError("RESOURCE_ROOT_LIMIT_EXCEEDED")
        if (self.revision < 1 or self.updated_at.tzinfo is None
                or self.updated_at.utcoffset() is None):
            raise GlobalSecurityError("USER_GLOBAL_SECURITY_REVISION_INVALID")


def global_profile_is_admin_superuser(profile: GlobalSecurityProfile) -> bool:
    profile.validate()
    return (profile.active and profile.built_in and profile.name == ADMIN_SUPERUSER
            and profile.profile_id == "p6-admin-superuser")


def global_profile_has_project_access_bypass(profile: GlobalSecurityProfile) -> bool:
    """Only the application-generated Admin Superuser bypasses project grants."""
    return global_profile_is_admin_superuser(profile)


def user_has_all_resource_access(profile: GlobalSecurityProfile, assignment: UserGlobalSecurity) -> bool:
    """Admin Superuser always has all resource access; otherwise honor the user setting."""
    profile.validate()
    assignment.validate()
    return global_profile_is_admin_superuser(profile) or assignment.resource_access_mode == "all"


def global_profile_has_global_read_only(profile: GlobalSecurityProfile) -> bool:
    """No Global Privileges retains the V26 documented read-only global access."""
    profile.validate()
    return (profile.active and profile.built_in and profile.name == NO_GLOBAL_PRIVILEGES
            and profile.profile_id == "p6-no-global-privileges")


class P6GlobalSecurityRepository(Protocol):
    def initialize(self) -> None: ...
    def get_profile(self, tenant_id: str, profile_id: str) -> GlobalSecurityProfile | None: ...
    def get_user_security(self, tenant_id: str, user_id: str) -> UserGlobalSecurity | None: ...


class PostgresP6GlobalSecurityRepository:
    """Tenant-scoped global profiles and user module/resource access settings."""

    def __init__(self, connection: Any) -> None:
        self._connection = connection

    def initialize(self) -> None:
        statements = (
            """CREATE TABLE IF NOT EXISTS p6_global_security_profiles (
                tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL,
                name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 160),
                description TEXT NOT NULL DEFAULT '',
                is_default BOOLEAN NOT NULL DEFAULT FALSE,
                privileges JSONB NOT NULL CHECK(jsonb_typeof(privileges)='array'),
                built_in BOOLEAN NOT NULL DEFAULT FALSE,
                active BOOLEAN NOT NULL DEFAULT TRUE,
                revision BIGINT NOT NULL CHECK(revision >= 1),
                created_by TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL,
                PRIMARY KEY(tenant_id,profile_id),
                UNIQUE(tenant_id,name))""",
            "ALTER TABLE p6_global_security_profiles ADD COLUMN IF NOT EXISTS description TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE p6_global_security_profiles ADD COLUMN IF NOT EXISTS is_default BOOLEAN NOT NULL DEFAULT FALSE",
            "CREATE UNIQUE INDEX IF NOT EXISTS p6_global_security_one_default_per_tenant "
            "ON p6_global_security_profiles(tenant_id) WHERE is_default=TRUE",
            """CREATE TABLE IF NOT EXISTS p6_user_global_security (
                tenant_id TEXT NOT NULL, user_id TEXT NOT NULL,
                profile_id TEXT NOT NULL, module_access JSONB NOT NULL
                    CHECK(jsonb_typeof(module_access)='array'),
                resource_access_mode TEXT NOT NULL
                    CHECK(resource_access_mode IN ('none','all','selected')),
                resource_root_ids JSONB NOT NULL
                    CHECK(jsonb_typeof(resource_root_ids)='array'),
                revision BIGINT NOT NULL CHECK(revision >= 1),
                updated_by TEXT NOT NULL, updated_at TIMESTAMPTZ NOT NULL,
                PRIMARY KEY(tenant_id,user_id),
                FOREIGN KEY(user_id) REFERENCES identity_users(user_id) ON DELETE RESTRICT,
                FOREIGN KEY(tenant_id,profile_id)
                    REFERENCES p6_global_security_profiles(tenant_id,profile_id),
                CHECK((resource_access_mode='selected' AND jsonb_array_length(resource_root_ids)>0)
                   OR (resource_access_mode IN ('none','all') AND jsonb_array_length(resource_root_ids)=0)))""",
            """CREATE TABLE IF NOT EXISTS p6_global_security_audit (
                audit_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, actor_id TEXT NOT NULL,
                target_user_id TEXT, profile_id TEXT NOT NULL, action TEXT NOT NULL,
                before_state JSONB, after_state JSONB NOT NULL,
                occurred_at TIMESTAMPTZ NOT NULL)""",
            """CREATE OR REPLACE FUNCTION p6_global_security_audit_immutable()
                RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN RAISE EXCEPTION 'P6_GLOBAL_SECURITY_AUDIT_APPEND_ONLY'; END; $$""",
            """DROP TRIGGER IF EXISTS p6_global_security_audit_immutable
                ON p6_global_security_audit""",
            """CREATE TRIGGER p6_global_security_audit_immutable
                BEFORE UPDATE OR DELETE ON p6_global_security_audit
                FOR EACH ROW EXECUTE FUNCTION p6_global_security_audit_immutable()""",
        )
        for statement in statements:
            self._connection.execute(statement)

    def ensure_builtin_profiles(self, tenant_id: str, *, provisioned_by: str,
                                created_at: datetime) -> None:
        """Idempotently provision the two application-generated V26 profiles."""
        if (not tenant_id.strip() or not provisioned_by.strip()
                or created_at.tzinfo is None or created_at.utcoffset() is None):
            raise GlobalSecurityError("GLOBAL_SECURITY_PROFILE_BOOTSTRAP_INVALID")
        for profile_id, name in (
            ("p6-admin-superuser", ADMIN_SUPERUSER),
            ("p6-no-global-privileges", NO_GLOBAL_PRIVILEGES),
        ):
            inserted = self._connection.execute(
                "INSERT INTO p6_global_security_profiles "
                "(tenant_id,profile_id,name,privileges,built_in,active,revision,created_by,created_at) "
                "VALUES(%s,%s,%s,'[]'::jsonb,TRUE,TRUE,1,%s,%s) "
                "ON CONFLICT(tenant_id,profile_id) DO NOTHING RETURNING profile_id",
                (tenant_id, profile_id, name, provisioned_by, created_at),
            ).fetchone()
            if inserted is not None:
                self._connection.execute(
                    "INSERT INTO p6_global_security_audit "
                    "(audit_id,tenant_id,actor_id,target_user_id,profile_id,action,before_state,"
                    "after_state,occurred_at) VALUES(%s,%s,%s,NULL,%s,"
                    "'builtin_global_profile_provisioned',NULL,%s::jsonb,%s)",
                    (f"p6-global-{uuid4().hex}", tenant_id, provisioned_by, profile_id,
                     json.dumps({"name": name, "built_in": True, "revision": 1}), created_at),
                )

    def create_profile(self, profile: GlobalSecurityProfile, *, actor_id: str,
                       created_at: datetime) -> GlobalSecurityProfile:
        profile.validate()
        if (not actor_id.strip() or created_at.tzinfo is None
                or created_at.utcoffset() is None):
            raise GlobalSecurityError("GLOBAL_SECURITY_PROFILE_ACTOR_REQUIRED")
        if profile.built_in or profile.name in BUILTIN_GLOBAL_PROFILES:
            raise GlobalSecurityError("BUILTIN_GLOBAL_SECURITY_PROFILE_IMMUTABLE")
        if profile.is_default:
            raise GlobalSecurityError("SET_DEFAULT_PROFILE_SEPARATELY")
        self._connection.execute(
            "INSERT INTO p6_global_security_profiles "
            "(tenant_id,profile_id,name,description,is_default,privileges,built_in,active,revision,created_by,created_at) "
            "VALUES(%s,%s,%s,%s,FALSE,%s::jsonb,FALSE,%s,%s,%s,%s)",
            (profile.tenant_id, profile.profile_id, profile.name, profile.description,
             json.dumps(list(profile.privileges)), profile.active, profile.revision,
             actor_id, created_at),
        )
        self._connection.execute(
            "INSERT INTO p6_global_security_audit "
            "(audit_id,tenant_id,actor_id,target_user_id,profile_id,action,before_state,"
            "after_state,occurred_at) VALUES(%s,%s,%s,NULL,%s,'global_profile_created',"
            "NULL,%s::jsonb,%s)",
            (f"p6-global-{uuid4().hex}", profile.tenant_id, actor_id,
             profile.profile_id, json.dumps({"name": profile.name,
             "privileges": list(profile.privileges), "revision": profile.revision}),
             created_at),
        )
        return profile

    def get_profile(self, tenant_id: str, profile_id: str) -> GlobalSecurityProfile | None:
        row = self._connection.execute(
            "SELECT tenant_id,profile_id,name,privileges,built_in,active,revision,description,is_default "
            "FROM p6_global_security_profiles WHERE tenant_id=%s AND profile_id=%s",
            (tenant_id, profile_id),
        ).fetchone()
        if row is None:
            return None
        privileges = row[3]
        if isinstance(privileges, str):
            privileges = json.loads(privileges)
        result = GlobalSecurityProfile(str(row[0]), str(row[1]), str(row[2]),
            tuple(privileges or ()), bool(row[4]), bool(row[5]), int(row[6]),
            str(row[7] or ""), bool(row[8]))
        result.validate()
        return result

    def get_user_security(self, tenant_id: str, user_id: str) -> UserGlobalSecurity | None:
        row = self._connection.execute(
            "SELECT tenant_id,user_id,profile_id,module_access,resource_access_mode,"
            "resource_root_ids,revision,updated_by,updated_at "
            "FROM p6_user_global_security WHERE tenant_id=%s AND user_id=%s",
            (tenant_id, user_id),
        ).fetchone()
        if row is None:
            return None
        modules, roots = row[3], row[5]
        if isinstance(modules, str):
            modules = json.loads(modules)
        if isinstance(roots, str):
            roots = json.loads(roots)
        result = UserGlobalSecurity(str(row[0]), str(row[1]), str(row[2]),
            tuple(modules or ()), str(row[4]), tuple(roots or ()), int(row[6]),
            str(row[7]), row[8])
        result.validate()
        return result

    def assign_user_security(self, assignment: UserGlobalSecurity, *,
                             expected_revision: int | None = None) -> UserGlobalSecurity:
        assignment.validate()
        profile = self.get_profile(assignment.tenant_id, assignment.profile_id)
        if profile is None or not profile.active:
            raise GlobalSecurityError("GLOBAL_SECURITY_PROFILE_NOT_FOUND")
        if global_profile_is_admin_superuser(profile):
            actor = self._connection.execute(
                "SELECT 1 FROM p6_user_global_security u "
                "JOIN p6_global_security_profiles p ON p.tenant_id=u.tenant_id "
                "AND p.profile_id=u.profile_id WHERE u.tenant_id=%s AND u.user_id=%s "
                "AND p.profile_id='p6-admin-superuser' AND p.built_in=TRUE AND p.active=TRUE",
                (assignment.tenant_id, assignment.updated_by),
            ).fetchone()
            if actor is None:
                raise GlobalSecurityError("ADMIN_SUPERUSER_ASSIGNMENT_REQUIRES_SUPERUSER")
        current = self.get_user_security(assignment.tenant_id, assignment.user_id)
        if current is None:
            if expected_revision not in (None, 0) or assignment.revision != 1:
                raise GlobalSecurityError("USER_GLOBAL_SECURITY_REVISION_CONFLICT")
            self._connection.execute(
                "INSERT INTO p6_user_global_security "
                "(tenant_id,user_id,profile_id,module_access,resource_access_mode,"
                "resource_root_ids,revision,updated_by,updated_at) "
                "VALUES(%s,%s,%s,%s::jsonb,%s,%s::jsonb,%s,%s,%s)",
                (assignment.tenant_id, assignment.user_id, assignment.profile_id,
                 json.dumps(list(assignment.module_access)), assignment.resource_access_mode,
                 json.dumps(list(assignment.resource_root_ids)), assignment.revision,
                 assignment.updated_by, assignment.updated_at),
            )
            before = None
            action = "user_global_security_assigned"
        else:
            if expected_revision is None or current.revision != expected_revision:
                raise GlobalSecurityError("USER_GLOBAL_SECURITY_REVISION_CONFLICT")
            if assignment.revision != current.revision + 1:
                raise GlobalSecurityError("USER_GLOBAL_SECURITY_REVISION_INVALID")
            row = self._connection.execute(
                "UPDATE p6_user_global_security SET profile_id=%s,module_access=%s::jsonb,"
                "resource_access_mode=%s,resource_root_ids=%s::jsonb,revision=%s,"
                "updated_by=%s,updated_at=%s WHERE tenant_id=%s AND user_id=%s "
                "AND revision=%s RETURNING user_id",
                (assignment.profile_id, json.dumps(list(assignment.module_access)),
                 assignment.resource_access_mode, json.dumps(list(assignment.resource_root_ids)),
                 assignment.revision, assignment.updated_by, assignment.updated_at,
                 assignment.tenant_id, assignment.user_id, expected_revision),
            ).fetchone()
            if row is None:
                raise GlobalSecurityError("USER_GLOBAL_SECURITY_REVISION_CONFLICT")
            before = self._assignment_json(current)
            action = "user_global_security_updated"
        self._connection.execute(
            "INSERT INTO p6_global_security_audit "
            "(audit_id,tenant_id,actor_id,target_user_id,profile_id,action,before_state,"
            "after_state,occurred_at) VALUES(%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s)",
            (f"p6-global-{uuid4().hex}", assignment.tenant_id, assignment.updated_by,
             assignment.user_id, assignment.profile_id, action,
             json.dumps(before) if before is not None else None,
             json.dumps(self._assignment_json(assignment)), assignment.updated_at),
        )
        return assignment

    @staticmethod
    def _assignment_json(value: UserGlobalSecurity) -> dict[str, Any]:
        return {"user_id": value.user_id, "profile_id": value.profile_id,
            "module_access": list(value.module_access),
            "resource_access_mode": value.resource_access_mode,
            "resource_root_ids": list(value.resource_root_ids),
            "revision": value.revision}
