"""Persisted Oracle P6 V26 global/project security profiles and authorization evaluator.

Mapped P6 permissions are authorized by the assigned Global and Project Security
Profiles and OBS/EPS/WBS responsibility. The injected role policy handles only
non-P6 CUBI surfaces; it does not replace or veto a P6 profile grant.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Iterable

from .application.authorization import (
    AuthorizationContext,
    Permission,
    RoleBasedAuthorizationPolicy,
)

_PROFILE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,99}$")
_PROFILE_SCOPES = frozenset({"global", "project"})
# Reserved Oracle P6 V26 built-in. It is provisioned only by a controlled
# installation bootstrap; tenant administrators cannot create or edit it.
ADMIN_SUPERUSER_PROFILE_ID = "p6-admin-superuser"
NO_GLOBAL_PRIVILEGES_PROFILE_ID = "p6-no-global-privileges"
PROJECT_SUPERUSER_PROFILE_ID = "p6-project-superuser"
_RESERVED_PROFILE_IDS = frozenset({
    ADMIN_SUPERUSER_PROFILE_ID, NO_GLOBAL_PRIVILEGES_PROFILE_ID,
    PROJECT_SUPERUSER_PROFILE_ID,
})
_ADMIN_ONLY_PROFILE_IDS = frozenset({
    ADMIN_SUPERUSER_PROFILE_ID, PROJECT_SUPERUSER_PROFILE_ID,
})

# Oracle P6 EPPM Help V26, Privileges Detail Window of the Global Security Profiles Page.
GLOBAL_PRIVILEGES = frozenset({
    "add_edit_delete_obs", "add_edit_delete_security_profiles", "add_edit_delete_users",
    "add_edit_delete_user_interface_views", "edit_application_settings", "provision_users_from_ldap",
    "view_published_audit_data", "add_global_activity_codes", "edit_global_activity_codes",
    "delete_global_activity_codes", "add_global_issue_codes", "edit_global_issue_codes",
    "delete_global_issue_codes", "add_project_codes", "edit_project_codes", "delete_project_codes",
    "add_resource_codes", "edit_resource_codes", "delete_resource_codes", "add_role_codes",
    "edit_role_codes", "delete_role_codes", "add_assignment_codes", "edit_assignment_codes",
    "delete_assignment_codes", "add_delete_secure_codes", "edit_secure_codes",
    "assign_secure_codes", "view_secure_codes", "add_edit_delete_categories_overhead_codes",
    "add_edit_delete_cost_accounts", "add_edit_delete_currencies", "add_edit_delete_locations",
    "add_edit_delete_financial_period_calendars", "add_edit_delete_funding_sources",
    "add_edit_delete_global_calendars", "add_edit_delete_global_portfolios",
    "add_edit_delete_risk_categories_matrices_thresholds", "add_edit_delete_timesheet_period_dates",
    "add_edit_delete_user_defined_fields", "add_edit_delete_stored_images", "add_resources",
    "edit_resources", "delete_resources", "add_edit_delete_resource_calendars",
    "add_edit_delete_resource_curves", "add_edit_delete_roles",
    "add_edit_delete_global_resource_role_teams", "add_edit_delete_rate_types_units_of_measure",
    "view_resource_role_costs_financials", "view_resource_role_proficiency",
    "approve_resource_timesheets", "add_edit_delete_activity_step_templates",
    "add_edit_delete_issue_forms", "add_edit_delete_microsoft_primavera_templates",
    "add_edit_delete_project_templates", "administer_global_external_applications",
    "administer_global_scheduled_services", "administer_project_scheduled_services",
    "edit_global_change_definitions", "import_p6_professional_xer_mpx", "import_xlsx",
    "import_xml", "enable_work_offline", "add_edit_delete_global_activity_assignment_layouts_views_filters",
    "add_edit_delete_global_dashboards", "add_edit_delete_global_project_wbs_portfolio_layouts_views_filters",
    "add_edit_delete_global_reports", "edit_global_tracking_layouts", "edit_projects_from_scorecards",
    "add_edit_delete_global_visualizer_layouts", "add_edit_delete_global_visualizer_filters",
})

# Oracle P6 EPPM Help V26, Privileges Detail Window of the Project Security Profiles Page.
PROJECT_PRIVILEGES = frozenset({
    "add_edit_activities_except_relationships", "delete_activities",
    "add_edit_delete_activity_relationships", "edit_activity_id", "add_edit_delete_expenses",
    "delete_discussion_comments", "add_project_activity_codes", "edit_project_activity_codes",
    "delete_project_activity_codes", "add_eps_activity_codes", "edit_eps_activity_codes",
    "delete_eps_activity_codes", "add_edit_delete_eps_except_costs_financials",
    "edit_eps_costs_financials", "add_projects", "delete_projects",
    "edit_project_details_except_costs_financials", "add_edit_delete_wbs_except_costs_financials",
    "edit_wbs_costs_financials", "view_project_costs_financials",
    "delete_project_data_with_timesheet_actuals", "delete_published_project_data",
    "export_project_data", "add_edit_delete_issues_issue_thresholds",
    "add_edit_delete_project_baselines", "add_edit_delete_project_calendars",
    "add_edit_delete_risks", "add_edit_delete_template_documents",
    "add_edit_delete_work_products_documents", "assign_project_baselines",
    "approve_timesheets_as_project_manager", "administer_project_external_applications",
    "exchange_project_data_unifier", "exchange_project_data_primavera_cloud",
    "exchange_project_data_gateway", "add_edit_activity_resource_requests",
    "add_edit_delete_resource_assignments_resource_planning",
    "add_edit_delete_role_assignments_resource_planning", "edit_committed_flag_resource_planning",
    "edit_future_periods", "edit_period_performance", "apply_actuals",
    "check_in_check_out_projects_open_exclusively", "level_resources", "schedule_projects",
    "monitor_project_thresholds", "store_period_performance", "summarize_projects",
    "edit_publication_priority", "run_baseline_update", "run_global_change",
    "allow_integration_with_primavera_unifier", "perform_global_search_replace",
    "add_edit_project_level_layouts", "edit_project_reports", "publish_project_website",
    "add_edit_delete_project_visualizer_layouts",
})

PROJECT_PERMISSION_PRIVILEGE_MAP = {
    Permission.PROJECT_SCHEDULE: "schedule_projects",
    Permission.PROJECT_ADMIN: "edit_project_details_except_costs_financials",
    Permission.P6_WBS_ADMIN: "add_edit_delete_wbs_except_costs_financials",
    Permission.P6_ACTIVITY_ADMIN: "add_edit_activities_except_relationships",
    Permission.P6_ACTIVITY_RELATIONSHIP_ADMIN: "add_edit_delete_activity_relationships",
    Permission.P6_ACTIVITY_ID_ADMIN: "edit_activity_id",
    Permission.P6_EXPENSE_ADMIN: "add_edit_delete_expenses",
    Permission.P6_DISCUSSION_DELETE: "delete_discussion_comments",
    Permission.P6_ISSUE_ADMIN: "add_edit_delete_issues_issue_thresholds",
    Permission.P6_BASELINE_ADMIN: "add_edit_delete_project_baselines",
    Permission.P6_PROJECT_CALENDAR_ADMIN: "add_edit_delete_project_calendars",
    Permission.P6_RISK_ADMIN: "add_edit_delete_risks",
    Permission.P6_PROJECT_DOCUMENT_ADMIN: "add_edit_delete_work_products_documents",
    Permission.P6_ASSIGN_PROJECT_BASELINE: "assign_project_baselines",
    Permission.P6_APPLY_ACTUALS: "apply_actuals",
    Permission.P6_STORE_PERIOD_PERFORMANCE: "store_period_performance",
    Permission.P6_EDIT_PERIOD_PERFORMANCE: "edit_period_performance",
    Permission.P6_MONITOR_THRESHOLDS: "monitor_project_thresholds",
    Permission.P6_COSTS_VIEW: "view_project_costs_financials",
    Permission.P6_RESOURCE_REQUEST_ADMIN: "add_edit_activity_resource_requests",
    Permission.P6_PROJECT_CHECKOUT_ADMIN: "check_in_check_out_projects_open_exclusively",
    Permission.P6_LEVEL_RESOURCES: "level_resources",
    Permission.P6_BASELINE_UPDATE: "run_baseline_update",
    Permission.P6_GLOBAL_CHANGE: "run_global_change",
    Permission.P6_EPS_ADMIN: "add_edit_delete_eps_except_costs_financials",
    Permission.P6_PROJECT_CREATE: "add_projects",
    Permission.P6_PROJECT_DELETE: "delete_projects",
    Permission.P6_EPS_COSTS_ADMIN: "edit_eps_costs_financials",
    Permission.P6_WBS_COSTS_ADMIN: "edit_wbs_costs_financials",
    Permission.P6_EXPORT_PROJECT_DATA: "export_project_data",
    Permission.P6_PROJECT_LEVEL_LAYOUT_ADMIN: "add_edit_project_level_layouts",
    Permission.P6_REPORT_ADMIN: "edit_project_reports",
}

GLOBAL_PERMISSION_PRIVILEGE_MAP = {
    # V26 Global Security Profile privilege for creating/editing/deleting UDF definitions.
    Permission.P6_UDF_ADMIN: "add_edit_delete_user_defined_fields",
    Permission.P6_OBS_ADMIN: "add_edit_delete_obs",
    Permission.P6_COST_ACCOUNT_ADMIN: "add_edit_delete_cost_accounts",
    Permission.P6_FINANCIAL_PERIOD_ADMIN: "add_edit_delete_financial_period_calendars",
    Permission.P6_ROLE_ADMIN: "add_edit_delete_roles",
    Permission.P6_RESOURCE_ADD: "add_resources",
    Permission.P6_RESOURCE_EDIT: "edit_resources",
    Permission.P6_RESOURCE_DELETE: "delete_resources",
}

GLOBAL_PRIVILEGE_IMPLICATIONS = {
    "delete_global_activity_codes": {"add_global_activity_codes", "edit_global_activity_codes"},
    "add_global_activity_codes": {"edit_global_activity_codes"},
    "delete_global_issue_codes": {"add_global_issue_codes", "edit_global_issue_codes"},
    "add_global_issue_codes": {"edit_global_issue_codes"},
    "delete_project_codes": {"add_project_codes", "edit_project_codes"},
    "add_project_codes": {"edit_project_codes"},
    "delete_resource_codes": {"add_resource_codes", "edit_resource_codes"},
    "add_resource_codes": {"edit_resource_codes"},
    "delete_role_codes": {"add_role_codes", "edit_role_codes"},
    "add_role_codes": {"edit_role_codes"},
    "delete_assignment_codes": {"add_assignment_codes", "edit_assignment_codes"},
    "add_assignment_codes": {"edit_assignment_codes"},
    "add_delete_secure_codes": {"edit_secure_codes", "assign_secure_codes", "view_secure_codes"},
    "edit_secure_codes": {"assign_secure_codes", "view_secure_codes"},
    "assign_secure_codes": {"view_secure_codes"},
    "delete_resources": {"add_resources", "edit_resources"},
    "add_resources": {"edit_resources"},
}

PROJECT_PRIVILEGE_IMPLICATIONS = {
    "delete_activities": {"add_edit_activities_except_relationships"},
    "delete_project_activity_codes": {"add_project_activity_codes", "edit_project_activity_codes"},
    "add_project_activity_codes": {"edit_project_activity_codes"},
    "delete_eps_activity_codes": {"add_eps_activity_codes", "edit_eps_activity_codes"},
    "add_eps_activity_codes": {"edit_eps_activity_codes"},
    "level_resources": {"schedule_projects"},
    "edit_wbs_costs_financials": {"view_project_costs_financials"},
}

PROJECT_PRIVILEGE_PREREQUISITES = {
    "edit_activity_id": {"add_edit_activities_except_relationships"},
    "add_edit_delete_template_documents": {"add_edit_delete_work_products_documents"},
    "assign_project_baselines": {"edit_project_details_except_costs_financials"},
    "edit_future_periods": {"add_edit_activities_except_relationships"},
    "edit_period_performance": {"add_edit_activities_except_relationships", "view_project_costs_financials"},
    "store_period_performance": {"add_edit_activities_except_relationships"},
}


def _normalize_profile_privileges(scope: str, privileges: frozenset[str]) -> frozenset[str]:
    implications = GLOBAL_PRIVILEGE_IMPLICATIONS if scope == "global" else PROJECT_PRIVILEGE_IMPLICATIONS
    expanded = set(privileges)
    changed = True
    while changed:
        changed = False
        for privilege in tuple(expanded):
            implied = implications.get(privilege, set())
            before = len(expanded)
            expanded.update(implied)
            changed = changed or len(expanded) != before
    if scope == "project":
        for privilege, prerequisites in PROJECT_PRIVILEGE_PREREQUISITES.items():
            if privilege in expanded and not prerequisites.issubset(expanded):
                raise SecurityProfileError("SECURITY_PROFILE_PRIVILEGE_DEPENDENCY_REQUIRED")
    return frozenset(expanded)


class SecurityProfileError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class SecurityProfile:
    tenant_id: str
    profile_id: str
    name: str
    scope: str
    active: bool
    revision: int
    privileges: frozenset[str]
    description: str = ""
    is_default: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "profile_id": self.profile_id,
            "name": self.name,
            "description": self.description,
            "scope": self.scope,
            "active": self.active,
            "is_default": self.is_default,
            "revision": self.revision,
            "privileges": sorted(self.privileges),
        }


SECURITY_PROFILE_SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS p6_security_profiles (
        tenant_id TEXT NOT NULL,
        profile_id TEXT NOT NULL,
        name TEXT NOT NULL CHECK (length(trim(name)) BETWEEN 1 AND 120),
        description TEXT NOT NULL DEFAULT '',
        scope TEXT NOT NULL CHECK (scope IN ('global','project')),
        active BOOLEAN NOT NULL DEFAULT TRUE,
        is_default BOOLEAN NOT NULL DEFAULT FALSE,
        revision BIGINT NOT NULL CHECK (revision >= 1),
        created_by TEXT NOT NULL,
        updated_by TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL,
        PRIMARY KEY (tenant_id, profile_id),
        UNIQUE (tenant_id, scope, name)
    )
    """,
    """
    ALTER TABLE p6_security_profiles
    ADD COLUMN IF NOT EXISTS description TEXT NOT NULL DEFAULT ''
    """,
    """
    ALTER TABLE p6_security_profiles
    ADD COLUMN IF NOT EXISTS is_default BOOLEAN NOT NULL DEFAULT FALSE
    """,
    """
    ALTER TABLE p6_security_profiles
    DROP CONSTRAINT IF EXISTS p6_security_profiles_default_scope_check
    """,
    """
    ALTER TABLE p6_security_profiles
    ADD CONSTRAINT p6_security_profiles_default_scope_check
    CHECK (NOT is_default OR scope='project')
    """,
    """
    ALTER TABLE p6_security_profiles
    DROP CONSTRAINT IF EXISTS p6_security_profiles_description_check
    """,
    """
    ALTER TABLE p6_security_profiles
    ADD CONSTRAINT p6_security_profiles_description_check
    CHECK (length(description) <= 2000)
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS p6_security_profiles_one_default_project
    ON p6_security_profiles (tenant_id) WHERE scope='project' AND is_default=TRUE
    """,
    """
    CREATE TABLE IF NOT EXISTS p6_security_profile_privileges (
        tenant_id TEXT NOT NULL,
        profile_id TEXT NOT NULL,
        permission TEXT NOT NULL,
        PRIMARY KEY (tenant_id, profile_id, permission),
        FOREIGN KEY (tenant_id, profile_id)
            REFERENCES p6_security_profiles(tenant_id, profile_id) ON DELETE RESTRICT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS p6_security_profile_assignments (
        tenant_id TEXT NOT NULL,
        profile_id TEXT NOT NULL,
        user_id TEXT NOT NULL REFERENCES identity_users(user_id) ON DELETE RESTRICT,
        obs_id TEXT NOT NULL DEFAULT '',
        revision BIGINT NOT NULL CHECK (revision >= 1),
        assigned_by TEXT NOT NULL,
        assigned_at TIMESTAMPTZ NOT NULL,
        PRIMARY KEY (tenant_id, profile_id, user_id, obs_id),
        FOREIGN KEY (tenant_id, profile_id)
            REFERENCES p6_security_profiles(tenant_id, profile_id) ON DELETE RESTRICT,
        CHECK (obs_id IS NOT NULL)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS p6_security_profile_assignments_user
    ON p6_security_profile_assignments (tenant_id, user_id, obs_id)
    """,
    """    CREATE UNIQUE INDEX IF NOT EXISTS p6_security_profile_one_global_per_user
    ON p6_security_profile_assignments (tenant_id, user_id)
    WHERE obs_id=''
    """,
    """
    CREATE OR REPLACE FUNCTION cubi_p6_security_profile_assignment_guard()
    RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE profile_scope TEXT; profile_active BOOLEAN;
            account_tenant TEXT; account_active BOOLEAN;
    BEGIN
        SELECT scope,active INTO profile_scope,profile_active
        FROM p6_security_profiles
        WHERE tenant_id=NEW.tenant_id AND profile_id=NEW.profile_id;
        IF profile_scope IS NULL OR NOT profile_active THEN
            RAISE EXCEPTION 'P6_SECURITY_PROFILE_INACTIVE_OR_MISSING';
        END IF;
        SELECT tenant_id,active INTO account_tenant,account_active
        FROM identity_users WHERE user_id=NEW.user_id;
        IF account_tenant IS DISTINCT FROM NEW.tenant_id OR NOT COALESCE(account_active,FALSE) THEN
            RAISE EXCEPTION 'P6_SECURITY_PROFILE_USER_NOT_ELIGIBLE';
        END IF;
        IF profile_scope='global' AND NEW.obs_id<>'' THEN
            RAISE EXCEPTION 'P6_SECURITY_PROFILE_ASSIGNMENT_SCOPE_MISMATCH';
        END IF;
        IF profile_scope='project' AND NEW.obs_id='' THEN
            RAISE EXCEPTION 'P6_SECURITY_PROFILE_ASSIGNMENT_SCOPE_MISMATCH';
        END IF;
        IF NEW.obs_id<>'' AND NOT EXISTS (
            SELECT 1 FROM p6_obs_node WHERE tenant_id=NEW.tenant_id AND obs_id=NEW.obs_id
        ) THEN
            RAISE EXCEPTION 'P6_SECURITY_PROFILE_OBS_NOT_FOUND';
        END IF;
        RETURN NEW;
    END;
    $$
    """,
    """
    DROP TRIGGER IF EXISTS p6_security_profile_assignment_guard
    ON p6_security_profile_assignments
    """,
    """
    CREATE TRIGGER p6_security_profile_assignment_guard
    BEFORE INSERT OR UPDATE ON p6_security_profile_assignments
    FOR EACH ROW EXECUTE FUNCTION cubi_p6_security_profile_assignment_guard()
    """,
    """
    CREATE TABLE IF NOT EXISTS p6_security_profile_audit (
        audit_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        actor_user_id TEXT NOT NULL,
        profile_id TEXT NOT NULL,
        action TEXT NOT NULL CHECK (action IN
            ('profile_created','privileges_changed','profile_status_changed',
             'profile_assigned','profile_unassigned','profile_updated','profile_default_changed','profile_deleted')),
        before_state JSONB,
        after_state JSONB NOT NULL,
        occurred_at TIMESTAMPTZ NOT NULL
    )
    """,
    """
    ALTER TABLE p6_security_profile_audit
    DROP CONSTRAINT IF EXISTS p6_security_profile_audit_action_check
    """,
    """
    ALTER TABLE p6_security_profile_audit
    ADD CONSTRAINT p6_security_profile_audit_action_check
    CHECK (action IN ('profile_created','privileges_changed','profile_status_changed',
                      'profile_assigned','profile_unassigned','profile_updated',
                      'profile_default_changed','profile_deleted'))
    """,
    """
    CREATE OR REPLACE FUNCTION cubi_p6_security_profile_audit_immutable()
    RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        RAISE EXCEPTION 'P6_SECURITY_PROFILE_AUDIT_APPEND_ONLY';
    END;
    $$
    """,
    """
    DROP TRIGGER IF EXISTS p6_security_profile_audit_immutable
    ON p6_security_profile_audit
    """,
    """
    CREATE TRIGGER p6_security_profile_audit_immutable
    BEFORE UPDATE OR DELETE ON p6_security_profile_audit
    FOR EACH ROW EXECUTE FUNCTION cubi_p6_security_profile_audit_immutable()
    """,
)


def initialize_security_profile_schema(connection: Any) -> None:
    for statement in SECURITY_PROFILE_SCHEMA:
        connection.execute(statement)


def bootstrap_first_admin_superuser(
    connection: Any, *, tenant_id: str, user_id: str,
    supplied_token: str, configured_token: str, occurred_at: Any,
) -> SecurityProfile:
    """Provision or recover the tenant's first active P6 Admin Superuser.

    This is deliberately not an HTTP/API operation. A deployment operator must
    invoke it out-of-band with the one-time bootstrap secret. It is safe to
    retry only while the tenant has no active Admin Superuser assignment.
    """
    import hmac
    import uuid

    if (not isinstance(supplied_token, str) or not supplied_token
            or not isinstance(configured_token, str) or len(configured_token) < 32
            or not hmac.compare_digest(supplied_token, configured_token)):
        raise SecurityProfileError("SECURITY_PROFILE_BOOTSTRAP_TOKEN_INVALID")
    if not isinstance(tenant_id, str) or not tenant_id.strip() or not isinstance(user_id, str) or not user_id.strip():
        raise SecurityProfileError("SECURITY_PROFILE_BOOTSTRAP_TARGET_INVALID")

    # Serialize first-time provisioning/recovery per tenant to avoid two
    # concurrent operators creating different first administrators.
    connection.execute(
        "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (tenant_id,)
    )
    active_admin = connection.execute(
        "SELECT 1 FROM p6_security_profile_assignments a "
        "JOIN p6_security_profiles p ON p.tenant_id=a.tenant_id AND p.profile_id=a.profile_id "
        "JOIN identity_users u ON u.user_id=a.user_id "
        "WHERE a.tenant_id=%s AND a.profile_id=%s AND a.obs_id='' "
        "AND p.scope='global' AND p.active=TRUE AND u.active=TRUE LIMIT 1",
        (tenant_id, ADMIN_SUPERUSER_PROFILE_ID),
    ).fetchone()
    if active_admin is not None:
        raise SecurityProfileError("SECURITY_PROFILE_BOOTSTRAP_ALREADY_INITIALIZED")

    target = connection.execute(
        "SELECT tenant_id,active FROM identity_users WHERE user_id=%s FOR UPDATE",
        (user_id,),
    ).fetchone()
    if target is None or str(target[0]) != tenant_id or not bool(target[1]):
        raise SecurityProfileError("SECURITY_PROFILE_USER_NOT_ELIGIBLE")
    occupied = connection.execute(
        "SELECT profile_id FROM p6_security_profile_assignments "
        "WHERE tenant_id=%s AND user_id=%s AND obs_id='' FOR UPDATE",
        (tenant_id, user_id),
    ).fetchone()
    if occupied is not None:
        raise SecurityProfileError("SECURITY_PROFILE_BOOTSTRAP_USER_HAS_GLOBAL_PROFILE")

    # Provision the other two Oracle built-ins alongside the first
    # administrator so every tenant has the complete immutable catalog.
    for builtin_id, builtin_name, builtin_scope in (
        (NO_GLOBAL_PRIVILEGES_PROFILE_ID, "No Global Privileges", "global"),
        (PROJECT_SUPERUSER_PROFILE_ID, "Project Superuser", "project"),
    ):
        builtin = connection.execute(
            "SELECT name,scope,active FROM p6_security_profiles "
            "WHERE tenant_id=%s AND profile_id=%s FOR UPDATE",
            (tenant_id, builtin_id),
        ).fetchone()
        if builtin is None:
            connection.execute(
                "INSERT INTO p6_security_profiles "
                "(tenant_id,profile_id,name,scope,active,revision,created_by,updated_by,created_at,updated_at) "
                "VALUES (%s,%s,%s,%s,TRUE,1,%s,%s,%s,%s)",
                (tenant_id,builtin_id,builtin_name,builtin_scope,user_id,user_id,occurred_at,occurred_at),
            )
            connection.execute(
                "INSERT INTO p6_security_profile_audit "
                "(audit_id,tenant_id,actor_user_id,profile_id,action,before_state,after_state,occurred_at) "
                "VALUES (%s,%s,%s,%s,'profile_created',NULL,%s::jsonb,%s)",
                (str(uuid.uuid4()),tenant_id,user_id,builtin_id,
                 json.dumps({"name":builtin_name,"scope":builtin_scope,"active":True,"revision":1}),
                 occurred_at),
            )
        elif str(builtin[0]) != builtin_name or str(builtin[1]) != builtin_scope or not bool(builtin[2]):
            raise SecurityProfileError("SECURITY_PROFILE_BUILTIN_COLLISION")

    profile = connection.execute(
        "SELECT name,scope,active,revision FROM p6_security_profiles "
        "WHERE tenant_id=%s AND profile_id=%s FOR UPDATE",
        (tenant_id, ADMIN_SUPERUSER_PROFILE_ID),
    ).fetchone()
    if profile is None:
        connection.execute(
            "INSERT INTO p6_security_profiles "
            "(tenant_id,profile_id,name,scope,active,revision,created_by,updated_by,created_at,updated_at) "
            "VALUES (%s,%s,'Admin Superuser','global',TRUE,1,%s,%s,%s,%s)",
            (tenant_id, ADMIN_SUPERUSER_PROFILE_ID, user_id, user_id, occurred_at, occurred_at),
        )
        connection.execute(
            "INSERT INTO p6_security_profile_audit "
            "(audit_id,tenant_id,actor_user_id,profile_id,action,before_state,after_state,occurred_at) "
            "VALUES (%s,%s,%s,%s,'profile_created',NULL,%s::jsonb,%s)",
            (str(uuid.uuid4()), tenant_id, user_id, ADMIN_SUPERUSER_PROFILE_ID,
             json.dumps({"name": "Admin Superuser", "scope": "global", "active": True, "revision": 1}),
             occurred_at),
        )
    elif str(profile[0]) != "Admin Superuser" or str(profile[1]) != "global" or not bool(profile[2]):
        raise SecurityProfileError("SECURITY_PROFILE_BUILTIN_COLLISION")

    for builtin_id, builtin_name, builtin_scope in (
        (NO_GLOBAL_PRIVILEGES_PROFILE_ID, "No Global Privileges", "global"),
        (PROJECT_SUPERUSER_PROFILE_ID, "Project Superuser", "project"),
    ):
        existing_builtin = connection.execute(
            "SELECT name,scope,active FROM p6_security_profiles "
            "WHERE tenant_id=%s AND profile_id=%s FOR UPDATE",
            (tenant_id,builtin_id),
        ).fetchone()
        if existing_builtin is None:
            connection.execute(
                "INSERT INTO p6_security_profiles "
                "(tenant_id,profile_id,name,scope,active,revision,created_by,updated_by,created_at,updated_at) "
                "VALUES (%s,%s,%s,%s,TRUE,1,%s,%s,%s,%s)",
                (tenant_id,builtin_id,builtin_name,builtin_scope,user_id,user_id,occurred_at,occurred_at),
            )
            connection.execute(
                "INSERT INTO p6_security_profile_audit "
                "(audit_id,tenant_id,actor_user_id,profile_id,action,before_state,after_state,occurred_at) "
                "VALUES (%s,%s,%s,%s,'profile_created',NULL,%s::jsonb,%s)",
                (str(uuid.uuid4()),tenant_id,user_id,builtin_id,
                 json.dumps({"name":builtin_name,"scope":builtin_scope,"active":True,"revision":1}),
                 occurred_at),
            )
        elif (
            str(existing_builtin[0]) != builtin_name
            or str(existing_builtin[1]) != builtin_scope
            or not bool(existing_builtin[2])
        ):
            raise SecurityProfileError("SECURITY_PROFILE_BUILTIN_COLLISION")

    connection.execute(
        "INSERT INTO p6_security_profile_assignments "
        "(tenant_id,profile_id,user_id,obs_id,revision,assigned_by,assigned_at) "
        "VALUES (%s,%s,%s,'',1,%s,%s)",
        (tenant_id, ADMIN_SUPERUSER_PROFILE_ID, user_id, user_id, occurred_at),
    )
    connection.execute(
        "INSERT INTO p6_security_profile_audit "
        "(audit_id,tenant_id,actor_user_id,profile_id,action,before_state,after_state,occurred_at) "
        "VALUES (%s,%s,%s,%s,'profile_assigned',NULL,%s::jsonb,%s)",
        (str(uuid.uuid4()), tenant_id, user_id, ADMIN_SUPERUSER_PROFILE_ID,
         json.dumps({"user_id": user_id, "obs_id": "", "revision": 1}), occurred_at),
    )
    return SecurityProfile(
        tenant_id, ADMIN_SUPERUSER_PROFILE_ID, "Admin Superuser",
        "global", True, 1, frozenset(),
    )


class PostgresSecurityProfileRepository:
    """Tenant-isolated, revision-guarded profile persistence."""

    def __init__(self, connection: Any) -> None:
        self._connection = connection

    def has_global_privilege(self, tenant_id: str, user_id: str, privilege: str) -> bool:
        """Evaluate one assigned Global Security Profile privilege for a live tenant user.

        Admin Superuser is the V26 built-in and implicitly carries every Global
        privilege. Other profiles grant only the exact stored Global privilege;
        Project profiles and OBS assignments are never consulted here.
        """
        if not isinstance(privilege, str) or privilege not in GLOBAL_PRIVILEGES:
            return False
        return self._connection.execute(
            "SELECT 1 FROM p6_security_profile_assignments a "
            "JOIN p6_security_profiles p ON p.tenant_id=a.tenant_id AND p.profile_id=a.profile_id "
            "JOIN identity_users u ON u.tenant_id=a.tenant_id AND u.user_id=a.user_id "
            "LEFT JOIN p6_security_profile_privileges grant_row "
            "ON grant_row.tenant_id=p.tenant_id AND grant_row.profile_id=p.profile_id "
            "AND grant_row.permission=%s "
            "WHERE a.tenant_id=%s AND a.user_id=%s AND a.obs_id='' "
            "AND p.scope='global' AND p.active=TRUE AND u.active=TRUE "
            "AND (p.profile_id=%s OR grant_row.permission IS NOT NULL) LIMIT 1",
            (privilege, tenant_id, user_id, ADMIN_SUPERUSER_PROFILE_ID),
        ).fetchone() is not None

    def create_profile(
        self, *, tenant_id: str, profile_id: str, name: str, scope: str,
        actor_user_id: str, occurred_at: Any, description: str = "",
    ) -> SecurityProfile:
        if not tenant_id.strip() or not _PROFILE_ID.fullmatch(profile_id):
            raise SecurityProfileError("SECURITY_PROFILE_ID_INVALID")
        if profile_id in _RESERVED_PROFILE_IDS:
            raise SecurityProfileError("SECURITY_PROFILE_BUILTIN_PROTECTED")
        if scope not in _PROFILE_SCOPES:
            raise SecurityProfileError("SECURITY_PROFILE_SCOPE_INVALID")
        normalized = name.strip() if isinstance(name, str) else ""
        if not normalized or len(normalized) > 120:
            raise SecurityProfileError("SECURITY_PROFILE_NAME_INVALID")
        normalized_description = self._description(description)
        existing_id = self._connection.execute(
            "SELECT 1 FROM p6_security_profiles WHERE tenant_id=%s AND profile_id=%s LIMIT 1",
            (tenant_id, profile_id),
        ).fetchone()
        if existing_id is not None:
            raise SecurityProfileError("SECURITY_PROFILE_ID_ALREADY_EXISTS")
        duplicate = self._connection.execute(
            "SELECT 1 FROM p6_security_profiles WHERE tenant_id=%s AND scope=%s AND name=%s LIMIT 1",
            (tenant_id, scope, normalized),
        ).fetchone()
        if duplicate is not None:
            raise SecurityProfileError("SECURITY_PROFILE_NAME_ALREADY_EXISTS")
        self._connection.execute(
            "INSERT INTO p6_security_profiles "
            "(tenant_id,profile_id,name,description,scope,active,is_default,revision,created_by,updated_by,created_at,updated_at) "
            "VALUES (%s,%s,%s,%s,%s,TRUE,FALSE,1,%s,%s,%s,%s)",
            (tenant_id, profile_id, normalized, normalized_description, scope, actor_user_id,
             actor_user_id, occurred_at, occurred_at),
        )
        self._audit(tenant_id, actor_user_id, profile_id, "profile_created",
                    None, {"name": normalized, "description": normalized_description,
                           "scope": scope, "active": True, "is_default": False, "revision": 1},
                    occurred_at)
        return SecurityProfile(tenant_id, profile_id, normalized, scope, True, 1,
                               frozenset(), normalized_description, False)

    def update_details(
        self, *, tenant_id: str, profile_id: str, name: str, description: str,
        expected_revision: int, actor_user_id: str, occurred_at: Any,
    ) -> SecurityProfile:
        if profile_id in _RESERVED_PROFILE_IDS:
            raise SecurityProfileError("SECURITY_PROFILE_BUILTIN_PROTECTED")
        normalized_name = name.strip() if isinstance(name, str) else ""
        if not normalized_name or len(normalized_name) > 120:
            raise SecurityProfileError("SECURITY_PROFILE_NAME_INVALID")
        normalized_description = self._description(description)
        row = self._connection.execute(
            "SELECT name,scope,active,revision,description,is_default FROM p6_security_profiles "
            "WHERE tenant_id=%s AND profile_id=%s FOR UPDATE",
            (tenant_id, profile_id),
        ).fetchone()
        if row is None:
            raise SecurityProfileError("SECURITY_PROFILE_NOT_FOUND")
        if int(row[3]) != expected_revision:
            raise SecurityProfileError("SECURITY_PROFILE_REVISION_CONFLICT")
        duplicate = self._connection.execute(
            "SELECT 1 FROM p6_security_profiles WHERE tenant_id=%s AND scope=%s "
            "AND name=%s AND profile_id<>%s LIMIT 1",
            (tenant_id, str(row[1]), normalized_name, profile_id),
        ).fetchone()
        if duplicate is not None:
            raise SecurityProfileError("SECURITY_PROFILE_NAME_ALREADY_EXISTS")
        before = self.get_profile(tenant_id, profile_id)
        revision = expected_revision + 1
        self._connection.execute(
            "UPDATE p6_security_profiles SET name=%s,description=%s,revision=%s,"
            "updated_by=%s,updated_at=%s WHERE tenant_id=%s AND profile_id=%s",
            (normalized_name, normalized_description, revision, actor_user_id,
             occurred_at, tenant_id, profile_id),
        )
        after = {**before.as_dict(), "name": normalized_name,
                 "description": normalized_description, "revision": revision}
        self._audit(tenant_id, actor_user_id, profile_id, "profile_updated",
                    before.as_dict(), after, occurred_at)
        return SecurityProfile(
            tenant_id, profile_id, normalized_name, str(row[1]), bool(row[2]),
            revision, before.privileges, normalized_description, bool(row[5]),
        )

    def set_default(
        self, *, tenant_id: str, profile_id: str, is_default: bool,
        expected_revision: int, actor_user_id: str, occurred_at: Any,
    ) -> SecurityProfile:
        if not isinstance(is_default, bool):
            raise SecurityProfileError("SECURITY_PROFILE_DEFAULT_FLAG_INVALID")
        self._connection.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
            (f"p6-project-profile-default:{tenant_id}",),
        )
        row = self._connection.execute(
            "SELECT name,scope,active,revision,description,is_default FROM p6_security_profiles "
            "WHERE tenant_id=%s AND profile_id=%s FOR UPDATE",
            (tenant_id, profile_id),
        ).fetchone()
        if row is None:
            raise SecurityProfileError("SECURITY_PROFILE_NOT_FOUND")
        if profile_id in _RESERVED_PROFILE_IDS:
            raise SecurityProfileError("SECURITY_PROFILE_BUILTIN_PROTECTED")
        if str(row[1]) != "project":
            raise SecurityProfileError("SECURITY_PROFILE_DEFAULT_PROJECT_ONLY")
        if not bool(row[2]) and is_default:
            raise SecurityProfileError("SECURITY_PROFILE_INACTIVE")
        if int(row[3]) != expected_revision:
            raise SecurityProfileError("SECURITY_PROFILE_REVISION_CONFLICT")
        before = self.get_profile(tenant_id, profile_id)
        if bool(row[5]) == is_default:
            return before
        if is_default:
            previous_rows = self._connection.execute(
                "SELECT profile_id,revision FROM p6_security_profiles "
                "WHERE tenant_id=%s AND scope='project' AND is_default=TRUE "
                "AND profile_id<>%s FOR UPDATE",
                (tenant_id, profile_id),
            ).fetchall()
            for previous in previous_rows:
                previous_id, previous_revision = str(previous[0]), int(previous[1])
                previous_before = self.get_profile(tenant_id, previous_id)
                next_revision = previous_revision + 1
                self._connection.execute(
                    "UPDATE p6_security_profiles SET is_default=FALSE,revision=%s,"
                    "updated_by=%s,updated_at=%s WHERE tenant_id=%s AND profile_id=%s",
                    (next_revision, actor_user_id, occurred_at, tenant_id, previous_id),
                )
                previous_after = {**previous_before.as_dict(),
                                  "is_default": False, "revision": next_revision}
                self._audit(
                    tenant_id, actor_user_id, previous_id, "profile_default_changed",
                    previous_before.as_dict(), previous_after, occurred_at,
                )
        revision = expected_revision + 1
        self._connection.execute(
            "UPDATE p6_security_profiles SET is_default=%s,revision=%s,"
            "updated_by=%s,updated_at=%s WHERE tenant_id=%s AND profile_id=%s",
            (is_default, revision, actor_user_id, occurred_at, tenant_id, profile_id),
        )
        after = {**before.as_dict(), "is_default": is_default, "revision": revision}
        self._audit(tenant_id, actor_user_id, profile_id, "profile_default_changed",
                    before.as_dict(), after, occurred_at)
        return SecurityProfile(
            tenant_id, profile_id, row[0], row[1], bool(row[2]), revision,
            before.privileges, str(row[4]), is_default,
        )

    def duplicate_profile(
        self, *, tenant_id: str, source_profile_id: str, profile_id: str,
        actor_user_id: str, occurred_at: Any, name: str | None = None,
        description: str | None = None,
    ) -> SecurityProfile:
        if not tenant_id.strip() or not _PROFILE_ID.fullmatch(profile_id):
            raise SecurityProfileError("SECURITY_PROFILE_ID_INVALID")
        if profile_id in _RESERVED_PROFILE_IDS:
            raise SecurityProfileError("SECURITY_PROFILE_BUILTIN_PROTECTED")
        if profile_id == source_profile_id:
            raise SecurityProfileError("SECURITY_PROFILE_ID_INVALID")
        target_exists = self._connection.execute(
            "SELECT 1 FROM p6_security_profiles WHERE tenant_id=%s AND profile_id=%s LIMIT 1",
            (tenant_id, profile_id),
        ).fetchone()
        if target_exists is not None:
            raise SecurityProfileError("SECURITY_PROFILE_ID_ALREADY_EXISTS")
        source = self._connection.execute(
            "SELECT name,scope,description FROM p6_security_profiles "
            "WHERE tenant_id=%s AND profile_id=%s FOR SHARE",
            (tenant_id, source_profile_id),
        ).fetchone()
        if source is None:
            raise SecurityProfileError("SECURITY_PROFILE_NOT_FOUND")
        if source_profile_id in _RESERVED_PROFILE_IDS:
            raise SecurityProfileError("SECURITY_PROFILE_BUILTIN_PROTECTED")
        normalized_name = name.strip() if isinstance(name, str) else ""
        if not normalized_name:
            base = str(source[0])
            for suffix in range(1, 1000):
                candidate = f"{base}-{suffix}"
                exists = self._connection.execute(
                    "SELECT 1 FROM p6_security_profiles WHERE tenant_id=%s AND scope=%s AND name=%s LIMIT 1",
                    (tenant_id, str(source[1]), candidate),
                ).fetchone()
                if exists is None:
                    normalized_name = candidate
                    break
        if not normalized_name or len(normalized_name) > 120:
            raise SecurityProfileError("SECURITY_PROFILE_NAME_INVALID")
        normalized_description = self._description(
            str(source[2]) if description is None else description
        )
        exists = self._connection.execute(
            "SELECT 1 FROM p6_security_profiles WHERE tenant_id=%s AND scope=%s AND name=%s LIMIT 1",
            (tenant_id, str(source[1]), normalized_name),
        ).fetchone()
        if exists is not None:
            raise SecurityProfileError("SECURITY_PROFILE_NAME_ALREADY_EXISTS")
        privileges = self._connection.execute(
            "SELECT permission FROM p6_security_profile_privileges "
            "WHERE tenant_id=%s AND profile_id=%s ORDER BY permission",
            (tenant_id, source_profile_id),
        ).fetchall()
        copied = tuple(str(item[0]) for item in privileges)
        self._connection.execute(
            "INSERT INTO p6_security_profiles "
            "(tenant_id,profile_id,name,description,scope,active,is_default,revision,"
            "created_by,updated_by,created_at,updated_at) "
            "VALUES (%s,%s,%s,%s,%s,TRUE,FALSE,1,%s,%s,%s,%s)",
            (tenant_id, profile_id, normalized_name, normalized_description,
             str(source[1]), actor_user_id, actor_user_id, occurred_at, occurred_at),
        )
        for permission in copied:
            self._connection.execute(
                "INSERT INTO p6_security_profile_privileges (tenant_id,profile_id,permission) "
                "VALUES (%s,%s,%s)", (tenant_id, profile_id, permission),
            )
        after = {
            "name": normalized_name, "description": normalized_description,
            "scope": str(source[1]), "active": True, "is_default": False,
            "revision": 1, "privileges": list(copied),
            "duplicated_from": source_profile_id,
        }
        self._audit(tenant_id, actor_user_id, profile_id, "profile_created",
                    None, after, occurred_at)
        return self.get_profile(tenant_id, profile_id)

    def delete_profile(
        self, *, tenant_id: str, profile_id: str, expected_revision: int,
        actor_user_id: str, occurred_at: Any,
    ) -> None:
        if profile_id in _RESERVED_PROFILE_IDS:
            raise SecurityProfileError("SECURITY_PROFILE_BUILTIN_PROTECTED")
        row = self._connection.execute(
            "SELECT revision FROM p6_security_profiles "
            "WHERE tenant_id=%s AND profile_id=%s FOR UPDATE",
            (tenant_id, profile_id),
        ).fetchone()
        if row is None:
            raise SecurityProfileError("SECURITY_PROFILE_NOT_FOUND")
        if int(row[0]) != expected_revision:
            raise SecurityProfileError("SECURITY_PROFILE_REVISION_CONFLICT")
        assigned = self._connection.execute(
            "SELECT 1 FROM p6_security_profile_assignments "
            "WHERE tenant_id=%s AND profile_id=%s LIMIT 1",
            (tenant_id, profile_id),
        ).fetchone()
        if assigned is not None:
            raise SecurityProfileError("SECURITY_PROFILE_ASSIGNED_CANNOT_DELETE")
        before = self.get_profile(tenant_id, profile_id)
        self._connection.execute(
            "DELETE FROM p6_security_profile_privileges WHERE tenant_id=%s AND profile_id=%s",
            (tenant_id, profile_id),
        )
        deleted = self._connection.execute(
            "DELETE FROM p6_security_profiles WHERE tenant_id=%s AND profile_id=%s "
            "AND revision=%s RETURNING profile_id",
            (tenant_id, profile_id, expected_revision),
        ).fetchone()
        if deleted is None:
            raise SecurityProfileError("SECURITY_PROFILE_REVISION_CONFLICT")
        self._audit(
            tenant_id, actor_user_id, profile_id, "profile_deleted",
            before.as_dict(), {"profile_id": profile_id, "deleted": True,
                               "revision": expected_revision}, occurred_at,
        )

    def get_default_project_profile(self, tenant_id: str) -> SecurityProfile | None:
        row = self._connection.execute(
            "SELECT profile_id FROM p6_security_profiles "
            "WHERE tenant_id=%s AND scope='project' AND active=TRUE AND is_default=TRUE",
            (tenant_id,),
        ).fetchone()
        return None if row is None else self.get_profile(tenant_id, str(row[0]))

    def set_privileges(
        self, *, tenant_id: str, profile_id: str, privileges: Iterable[str],
        expected_revision: int, actor_user_id: str, occurred_at: Any,
    ) -> SecurityProfile:
        requested = frozenset(privileges)
        row = self._connection.execute(
            "SELECT name,scope,active,revision,description,is_default FROM p6_security_profiles "
            "WHERE tenant_id=%s AND profile_id=%s FOR UPDATE",
            (tenant_id, profile_id),
        ).fetchone()
        if row is None:
            raise SecurityProfileError("SECURITY_PROFILE_NOT_FOUND")
        if profile_id in _RESERVED_PROFILE_IDS:
            raise SecurityProfileError("SECURITY_PROFILE_BUILTIN_PROTECTED")
        if int(row[3]) != expected_revision:
            raise SecurityProfileError("SECURITY_PROFILE_REVISION_CONFLICT")
        valid = GLOBAL_PRIVILEGES if str(row[1]) == "global" else PROJECT_PRIVILEGES
        if not requested.issubset(valid):
            raise SecurityProfileError("SECURITY_PROFILE_PRIVILEGE_INVALID")
        normalized = _normalize_profile_privileges(str(row[1]), requested)
        before = self.get_profile(tenant_id, profile_id)
        self._connection.execute(
            "DELETE FROM p6_security_profile_privileges WHERE tenant_id=%s AND profile_id=%s",
            (tenant_id, profile_id),
        )
        for permission in sorted(normalized):
            self._connection.execute(
                "INSERT INTO p6_security_profile_privileges (tenant_id,profile_id,permission) "
                "VALUES (%s,%s,%s)", (tenant_id, profile_id, permission),
            )
        revision = expected_revision + 1
        self._connection.execute(
            "UPDATE p6_security_profiles SET revision=%s,updated_by=%s,updated_at=%s "
            "WHERE tenant_id=%s AND profile_id=%s",
            (revision, actor_user_id, occurred_at, tenant_id, profile_id),
        )
        after = {"name": row[0], "scope": row[1], "active": bool(row[2]),
                 "description": str(row[4]), "is_default": bool(row[5]),
                 "revision": revision, "privileges": sorted(normalized)}
        self._audit(tenant_id, actor_user_id, profile_id, "privileges_changed",
                    before.as_dict(), after, occurred_at)
        return SecurityProfile(tenant_id, profile_id, row[0], row[1], bool(row[2]),
                               revision, normalized, str(row[4]), bool(row[5]))

    def set_active(
        self, *, tenant_id: str, profile_id: str, active: bool,
        expected_revision: int, actor_user_id: str, occurred_at: Any,
    ) -> SecurityProfile:
        if not isinstance(active, bool):
            raise SecurityProfileError("SECURITY_PROFILE_STATUS_INVALID")
        row = self._connection.execute(
            "SELECT name,scope,active,revision,description,is_default FROM p6_security_profiles "
            "WHERE tenant_id=%s AND profile_id=%s FOR UPDATE",
            (tenant_id, profile_id),
        ).fetchone()
        if row is None:
            raise SecurityProfileError("SECURITY_PROFILE_NOT_FOUND")
        if profile_id in _RESERVED_PROFILE_IDS:
            raise SecurityProfileError("SECURITY_PROFILE_BUILTIN_PROTECTED")
        if int(row[3]) != expected_revision:
            raise SecurityProfileError("SECURITY_PROFILE_REVISION_CONFLICT")
        before = self.get_profile(tenant_id, profile_id)
        revision = expected_revision + 1
        is_default = bool(row[5]) and active
        self._connection.execute(
            "UPDATE p6_security_profiles SET active=%s,is_default=%s,revision=%s,updated_by=%s,updated_at=%s "
            "WHERE tenant_id=%s AND profile_id=%s",
            (active, is_default, revision, actor_user_id, occurred_at, tenant_id, profile_id),
        )
        after = {**before.as_dict(), "active": active, "is_default": is_default, "revision": revision}
        self._audit(tenant_id, actor_user_id, profile_id, "profile_status_changed",
                    before.as_dict(), after, occurred_at)
        return SecurityProfile(tenant_id, profile_id, row[0], row[1], active,
                               revision, before.privileges, str(row[4]), is_default)

    def assign(
        self, *, tenant_id: str, profile_id: str, user_id: str,
        actor_user_id: str, occurred_at: Any, obs_id: str = "",
        expected_revision: int | None = None,
    ) -> int:
        profile = self._connection.execute(
            "SELECT scope,active FROM p6_security_profiles WHERE tenant_id=%s AND profile_id=%s FOR UPDATE",
            (tenant_id, profile_id),
        ).fetchone()
        if profile is None:
            raise SecurityProfileError("SECURITY_PROFILE_NOT_FOUND")
        scope, active = str(profile[0]), bool(profile[1])
        if profile_id in _ADMIN_ONLY_PROFILE_IDS:
            actor_is_admin_superuser = self._connection.execute(
                "SELECT 1 FROM p6_security_profile_assignments a "
                "JOIN p6_security_profiles p ON p.tenant_id=a.tenant_id AND p.profile_id=a.profile_id "
                "WHERE a.tenant_id=%s AND a.user_id=%s AND a.profile_id=%s "
                "AND a.obs_id='' AND p.scope='global' AND p.active=TRUE",
                (tenant_id, actor_user_id, ADMIN_SUPERUSER_PROFILE_ID),
            ).fetchone()
            if actor_is_admin_superuser is None:
                raise SecurityProfileError("SECURITY_PROFILE_ADMIN_SUPERUSER_ASSIGNER_REQUIRED")
        if not active:
            raise SecurityProfileError("SECURITY_PROFILE_INACTIVE")
        if (scope == "global" and obs_id) or (scope == "project" and not obs_id):
            raise SecurityProfileError("SECURITY_PROFILE_ASSIGNMENT_SCOPE_MISMATCH")
        user = self._connection.execute(
            "SELECT tenant_id,active FROM identity_users WHERE user_id=%s",
            (user_id,),
        ).fetchone()
        if user is None or str(user[0]) != tenant_id or not bool(user[1]):
            raise SecurityProfileError("SECURITY_PROFILE_USER_NOT_ELIGIBLE")
        if obs_id:
            node = self._connection.execute(
                "SELECT 1 FROM p6_obs_node WHERE tenant_id=%s AND obs_id=%s",
                (tenant_id, obs_id),
            ).fetchone()
            if node is None:
                raise SecurityProfileError("SECURITY_PROFILE_OBS_NOT_FOUND")
        existing = self._connection.execute(
            "SELECT revision FROM p6_security_profile_assignments "
            "WHERE tenant_id=%s AND profile_id=%s AND user_id=%s AND obs_id=%s FOR UPDATE",
            (tenant_id, profile_id, user_id, obs_id),
        ).fetchone()
        if existing is not None:
            if expected_revision is None or int(existing[0]) != expected_revision:
                raise SecurityProfileError("SECURITY_PROFILE_ASSIGNMENT_REVISION_CONFLICT")
            revision = expected_revision + 1
            self._connection.execute(
                "UPDATE p6_security_profile_assignments SET revision=%s,assigned_by=%s,assigned_at=%s "
                "WHERE tenant_id=%s AND profile_id=%s AND user_id=%s AND obs_id=%s",
                (revision, actor_user_id, occurred_at, tenant_id, profile_id, user_id, obs_id),
            )
        else:
            if expected_revision not in (None, 0):
                raise SecurityProfileError("SECURITY_PROFILE_ASSIGNMENT_REVISION_CONFLICT")
            if scope == "global":
                occupied = self._connection.execute(
                    "SELECT profile_id,revision FROM p6_security_profile_assignments "
                    "WHERE tenant_id=%s AND user_id=%s AND obs_id='' FOR UPDATE",
                    (tenant_id, user_id),
                ).fetchone()
                if occupied is not None:
                    if expected_revision is None or int(occupied[1]) != expected_revision:
                        raise SecurityProfileError("SECURITY_PROFILE_ASSIGNMENT_REVISION_CONFLICT")
                    if str(occupied[0]) == ADMIN_SUPERUSER_PROFILE_ID and profile_id != ADMIN_SUPERUSER_PROFILE_ID:
                        remaining = self._connection.execute(
                            "SELECT count(*) FROM p6_security_profile_assignments a "
                            "JOIN identity_users u ON u.user_id=a.user_id "
                            "WHERE a.tenant_id=%s AND a.profile_id=%s AND a.obs_id='' "
                            "AND u.active=TRUE",
                            (tenant_id, ADMIN_SUPERUSER_PROFILE_ID),
                        ).fetchone()
                        if remaining is not None and int(remaining[0]) <= 1:
                            raise SecurityProfileError("SECURITY_PROFILE_LAST_ADMIN_SUPERUSER_REQUIRED")
                    revision = expected_revision + 1
                    self._connection.execute(
                        "UPDATE p6_security_profile_assignments "
                        "SET profile_id=%s,revision=%s,assigned_by=%s,assigned_at=%s "
                        "WHERE tenant_id=%s AND profile_id=%s AND user_id=%s AND obs_id=''",
                        (profile_id, revision, actor_user_id, occurred_at,
                         tenant_id, str(occupied[0]), user_id),
                    )
                    self._audit(
                        tenant_id, actor_user_id, profile_id, "profile_assigned",
                        {"profile_id": str(occupied[0]), "user_id": user_id,
                         "obs_id": "", "revision": int(occupied[1])},
                        {"profile_id": profile_id, "user_id": user_id,
                         "obs_id": "", "revision": revision},
                        occurred_at,
                    )
                    return revision
            revision = 1
            self._connection.execute(
                "INSERT INTO p6_security_profile_assignments "
                "(tenant_id,profile_id,user_id,obs_id,revision,assigned_by,assigned_at) "
                "VALUES (%s,%s,%s,%s,1,%s,%s)",
                (tenant_id, profile_id, user_id, obs_id, actor_user_id, occurred_at),
            )
        self._audit(tenant_id, actor_user_id, profile_id, "profile_assigned", None,
                    {"user_id": user_id, "obs_id": obs_id, "revision": revision},
                    occurred_at)
        return revision

    def unassign(
        self, *, tenant_id: str, profile_id: str, user_id: str,
        obs_id: str = "", expected_revision: int,
        actor_user_id: str, occurred_at: Any,
    ) -> None:
        profile = self._connection.execute(
            "SELECT scope FROM p6_security_profiles WHERE tenant_id=%s AND profile_id=%s",
            (tenant_id, profile_id),
        ).fetchone()
        if profile is None:
            raise SecurityProfileError("SECURITY_PROFILE_NOT_FOUND")
        if str(profile[0]) == "global":
            raise SecurityProfileError("SECURITY_PROFILE_GLOBAL_ASSIGNMENT_REQUIRED")
        if profile_id in _ADMIN_ONLY_PROFILE_IDS:
            actor_is_admin_superuser = self._connection.execute(
                "SELECT 1 FROM p6_security_profile_assignments a "
                "JOIN p6_security_profiles p ON p.tenant_id=a.tenant_id AND p.profile_id=a.profile_id "
                "WHERE a.tenant_id=%s AND a.user_id=%s AND a.profile_id=%s "
                "AND a.obs_id='' AND p.scope='global' AND p.active=TRUE",
                (tenant_id, actor_user_id, ADMIN_SUPERUSER_PROFILE_ID),
            ).fetchone()
            if actor_is_admin_superuser is None:
                raise SecurityProfileError("SECURITY_PROFILE_ADMIN_SUPERUSER_ASSIGNER_REQUIRED")
        result = self._connection.execute(
            "DELETE FROM p6_security_profile_assignments "
            "WHERE tenant_id=%s AND profile_id=%s AND user_id=%s AND obs_id=%s AND revision=%s "
            "RETURNING revision",
            (tenant_id, profile_id, user_id, obs_id, expected_revision),
        ).fetchone()
        if result is None:
            raise SecurityProfileError("SECURITY_PROFILE_ASSIGNMENT_REVISION_CONFLICT")
        self._audit(tenant_id, actor_user_id, profile_id, "profile_unassigned",
                    {"user_id": user_id, "obs_id": obs_id, "revision": expected_revision},
                    {"unassigned": True}, occurred_at)

    def get_profile(self, tenant_id: str, profile_id: str) -> SecurityProfile:
        row = self._connection.execute(
            "SELECT name,scope,active,revision,description,is_default FROM p6_security_profiles "
            "WHERE tenant_id=%s AND profile_id=%s",
            (tenant_id, profile_id),
        ).fetchone()
        if row is None:
            raise SecurityProfileError("SECURITY_PROFILE_NOT_FOUND")
        grants = self._connection.execute(
            "SELECT permission FROM p6_security_profile_privileges "
            "WHERE tenant_id=%s AND profile_id=%s ORDER BY permission",
            (tenant_id, profile_id),
        ).fetchall()
        return SecurityProfile(tenant_id, profile_id, row[0], row[1], bool(row[2]),
                               int(row[3]), frozenset(str(item[0]) for item in grants),
                               str(row[4]), bool(row[5]))

    def list_profiles(self, tenant_id: str, scope: str | None = None) -> tuple[SecurityProfile, ...]:
        if scope is not None and scope not in _PROFILE_SCOPES:
            raise SecurityProfileError("SECURITY_PROFILE_SCOPE_INVALID")
        params: tuple[Any, ...] = (tenant_id,) if scope is None else (tenant_id, scope)
        where = "tenant_id=%s" if scope is None else "tenant_id=%s AND scope=%s"
        rows = self._connection.execute(
            f"SELECT profile_id FROM p6_security_profiles WHERE {where} ORDER BY scope,name",
            params,
        ).fetchall()
        return tuple(self.get_profile(tenant_id, str(row[0])) for row in rows)

    def list_assignments(self, tenant_id: str, profile_id: str) -> tuple[dict[str, Any], ...]:
        exists = self._connection.execute(
            "SELECT 1 FROM p6_security_profiles WHERE tenant_id=%s AND profile_id=%s",
            (tenant_id, profile_id),
        ).fetchone()
        if exists is None:
            raise SecurityProfileError("SECURITY_PROFILE_NOT_FOUND")
        rows = self._connection.execute(
            "SELECT a.user_id,u.email,u.display_name,a.obs_id,a.revision,a.assigned_by,a.assigned_at "
            "FROM p6_security_profile_assignments a "
            "JOIN identity_users u ON u.user_id=a.user_id "
            "WHERE a.tenant_id=%s AND a.profile_id=%s ORDER BY u.email,a.obs_id",
            (tenant_id, profile_id),
        ).fetchall()
        return tuple({
            "user_id": str(row[0]), "email": str(row[1]),
            "display_name": str(row[2]), "obs_id": str(row[3]),
            "revision": int(row[4]), "assigned_by": str(row[5]),
            "assigned_at": row[6].isoformat(),
        } for row in rows)

    def _description(self, value: Any) -> str:
        if not isinstance(value, str):
            raise SecurityProfileError("SECURITY_PROFILE_DESCRIPTION_INVALID")
        normalized = value.strip()
        if len(normalized) > 2000:
            raise SecurityProfileError("SECURITY_PROFILE_DESCRIPTION_INVALID")
        return normalized

    def _audit(self, tenant_id: str, actor_id: str, profile_id: str,
               action: str, before: Any, after: Any, occurred_at: Any) -> None:
        import uuid
        self._connection.execute(
            "INSERT INTO p6_security_profile_audit "
            "(audit_id,tenant_id,actor_user_id,profile_id,action,before_state,after_state,occurred_at) "
            "VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s)",
            (str(uuid.uuid4()), tenant_id, actor_id, profile_id, action,
             None if before is None else json.dumps(before, sort_keys=True),
             json.dumps(after, sort_keys=True), occurred_at),
        )


class PostgresSecurityProfileAuthorizationPolicy:
    """Role ceiling plus required Global and OBS-assigned Project profiles."""

    def __init__(self, connection: Any, role_policy: RoleBasedAuthorizationPolicy) -> None:
        self._connection = connection
        self._role_policy = role_policy

    def is_allowed(self, context: AuthorizationContext, permission: Permission) -> bool:
        context.validate()
        p6_project_permissions = {
            Permission.PROJECT_READ, Permission.PROJECT_WRITE,
            Permission.PROJECT_SCHEDULE, Permission.PROJECT_ADMIN,
            Permission.P6_WBS_ADMIN, Permission.P6_ACTIVITY_ADMIN,
            Permission.P6_ACTIVITY_RELATIONSHIP_ADMIN, Permission.P6_ACTIVITY_ID_ADMIN,
            Permission.P6_EXPENSE_ADMIN, Permission.P6_DISCUSSION_DELETE,
            Permission.P6_ISSUE_ADMIN, Permission.P6_BASELINE_ADMIN,
            Permission.P6_PROJECT_CALENDAR_ADMIN, Permission.P6_RISK_ADMIN,
            Permission.P6_PROJECT_DOCUMENT_ADMIN, Permission.P6_ASSIGN_PROJECT_BASELINE,
            Permission.P6_APPLY_ACTUALS, Permission.P6_STORE_PERIOD_PERFORMANCE,
            Permission.P6_MONITOR_THRESHOLDS, Permission.P6_COSTS_VIEW,
            Permission.P6_RESOURCE_REQUEST_ADMIN, Permission.P6_EDIT_PERIOD_PERFORMANCE,
            Permission.P6_PROJECT_CHECKOUT_ADMIN,
            Permission.P6_LEVEL_RESOURCES, Permission.P6_BASELINE_UPDATE,
            Permission.P6_GLOBAL_CHANGE, Permission.P6_EPS_ADMIN,
            Permission.P6_PROJECT_CREATE, Permission.P6_PROJECT_DELETE,
            Permission.P6_EPS_COSTS_ADMIN, Permission.P6_WBS_COSTS_ADMIN,
            Permission.P6_EXPORT_PROJECT_DATA, Permission.P6_PROJECT_LEVEL_LAYOUT_ADMIN,
            Permission.P6_REPORT_ADMIN,
        }
        p6_permissions = p6_project_permissions | {
            Permission.P6_UDF_ADMIN, Permission.P6_OBS_ADMIN,
            Permission.P6_COST_ACCOUNT_ADMIN, Permission.P6_FINANCIAL_PERIOD_ADMIN,
            Permission.P6_ROLE_ADMIN, Permission.P6_RESOURCE_ADD,
            Permission.P6_RESOURCE_EDIT, Permission.P6_RESOURCE_DELETE,
        }
        admin_superuser = self._connection.execute(
            "SELECT 1 FROM p6_security_profile_assignments a "
            "JOIN p6_security_profiles p ON p.tenant_id=a.tenant_id AND p.profile_id=a.profile_id "
            "WHERE a.tenant_id=%s AND a.user_id=%s AND a.profile_id=%s "
            "AND a.obs_id='' AND p.scope='global' AND p.active=TRUE",
            (context.tenant_id, context.user_id, ADMIN_SUPERUSER_PROFILE_ID),
        ).fetchone()
        # Oracle V26 Admin Superuser has complete P6 global and project access.
        # Non-P6 CUBI surfaces continue through the injected role policy.
        if admin_superuser is not None and permission in p6_permissions:
            return True
        if permission not in p6_permissions:
            return self._role_policy.is_allowed(context, permission)
        rows = self._connection.execute(
            "WITH RECURSIVE project_eps(eps_id,parent_eps_id,responsible_obs_id) AS ("
            "SELECT eps.eps_id,eps.parent_eps_id,eps.responsible_obs_id "
            "FROM p6_project_eps_assignment assignment "
            "JOIN p6_eps_node eps ON eps.tenant_id=assignment.tenant_id "
            "AND eps.eps_id=assignment.eps_id "
            "WHERE assignment.tenant_id=%s AND assignment.project_id=%s "
            "UNION "
            "SELECT parent.eps_id,parent.parent_eps_id,parent.responsible_obs_id "
            "FROM p6_eps_node parent JOIN project_eps child "
            "ON child.parent_eps_id=parent.eps_id WHERE parent.tenant_id=%s), "
            "responsible_obs(obs_id) AS ("
            "SELECT NULLIF(project.obs_id,'') FROM project_lifecycle_projects project "
            "WHERE project.tenant_id=%s AND project.project_id=%s "
            "UNION SELECT NULLIF(responsible_obs_id,'') FROM project_eps) "
            "SELECT p.scope,p.active,a.obs_id,p.profile_id "
            "FROM p6_security_profile_assignments a "
            "JOIN p6_security_profiles p ON p.tenant_id=a.tenant_id "
            "AND p.profile_id=a.profile_id "
            "WHERE a.tenant_id=%s AND a.user_id=%s "
            "AND ( (p.scope='global' AND a.obs_id='') "
            "OR (p.scope='project' AND a.obs_id IN "
            "(SELECT obs_id FROM responsible_obs)))",
            (context.tenant_id, context.project_id, context.tenant_id,
             context.tenant_id, context.project_id, context.tenant_id,
             context.user_id),
        ).fetchall()
        global_rows = [row for row in rows if str(row[0]) == "global"]
        project_rows = [row for row in rows if str(row[0]) == "project"]
        # P6 requires a Global Security Profile for every user. Project access
        # requires an active Project profile assigned to the project's responsible
        # OBS. A project profile does not create project membership.
        if not any(bool(row[1]) for row in global_rows):
            return False
        if (permission in p6_project_permissions and any(
            bool(row[1]) and str(row[3]) == PROJECT_SUPERUSER_PROFILE_ID
            for row in project_rows
        )):
            # Project Superuser grants complete P6 project access, but only
            # within the OBS responsibility assigned to this project.
            return True
        global_required = GLOBAL_PERMISSION_PRIVILEGE_MAP.get(permission)
        if global_required is not None:
            return any(bool(row[1]) and global_required in self._profile_privileges(
                context.tenant_id, str(row[3])
            ) for row in global_rows)
        # Read access follows the assigned OBS/project profile. Only the
        # operations with a verified V26 privilege mapping are enabled here;
        # generic write and CUBI-only permissions fail closed until each API
        # endpoint is mapped to its precise P6 privilege.
        if permission == Permission.PROJECT_READ:
            return any(bool(row[1]) for row in project_rows)
        required = PROJECT_PERMISSION_PRIVILEGE_MAP.get(permission)
        if required is None:
            return False
        return any(bool(row[1]) and required in self._profile_privileges(
            context.tenant_id, str(row[3])
        ) for row in project_rows)

    def is_admin_superuser(self, context: AuthorizationContext) -> bool:
        context.validate()
        return self._connection.execute(
            "SELECT 1 FROM p6_security_profile_assignments a "
            "JOIN p6_security_profiles p ON p.tenant_id=a.tenant_id AND p.profile_id=a.profile_id "
            "WHERE a.tenant_id=%s AND a.user_id=%s AND a.profile_id=%s "
            "AND a.obs_id='' AND p.scope='global' AND p.active=TRUE LIMIT 1",
            (context.tenant_id,context.user_id,ADMIN_SUPERUSER_PROFILE_ID),
        ).fetchone() is not None

    def is_allowed_for_eps(
        self, context: AuthorizationContext, permission: Permission, eps_id: str,
    ) -> bool:
        """Authorize project creation against the responsible OBS of an EPS branch."""
        context.validate()
        if permission not in {Permission.P6_PROJECT_CREATE, Permission.P6_EPS_ADMIN} or not isinstance(eps_id,str) or not eps_id.strip():
            return False
        admin = self._connection.execute(
            "SELECT 1 FROM p6_security_profile_assignments a "
            "JOIN p6_security_profiles p ON p.tenant_id=a.tenant_id AND p.profile_id=a.profile_id "
            "WHERE a.tenant_id=%s AND a.user_id=%s AND a.profile_id=%s "
            "AND a.obs_id='' AND p.scope='global' AND p.active=TRUE",
            (context.tenant_id,context.user_id,ADMIN_SUPERUSER_PROFILE_ID),
        ).fetchone()
        if admin is not None:
            return True
        global_profile = self._connection.execute(
            "SELECT 1 FROM p6_security_profile_assignments a "
            "JOIN p6_security_profiles p ON p.tenant_id=a.tenant_id AND p.profile_id=a.profile_id "
            "WHERE a.tenant_id=%s AND a.user_id=%s AND p.scope='global' "
            "AND a.obs_id='' AND p.active=TRUE LIMIT 1",
            (context.tenant_id,context.user_id),
        ).fetchone()
        if global_profile is None:
            return False
        obs_rows = self._connection.execute(
            "WITH RECURSIVE eps_path(eps_id,parent_eps_id,responsible_obs_id,path) AS ("
            "SELECT eps_id,parent_eps_id,responsible_obs_id,ARRAY[eps_id]::text[] "
            "FROM p6_eps_node WHERE tenant_id=%s AND eps_id=%s "
            "UNION ALL "
            "SELECT parent.eps_id,parent.parent_eps_id,parent.responsible_obs_id,path.path || parent.eps_id "
            "FROM p6_eps_node parent JOIN eps_path path ON path.parent_eps_id=parent.eps_id "
            "WHERE parent.tenant_id=%s AND NOT parent.eps_id=ANY(path.path)) "
            "SELECT DISTINCT NULLIF(responsible_obs_id,'') FROM eps_path "
            "WHERE responsible_obs_id<>''",
            (context.tenant_id,eps_id,context.tenant_id),
        ).fetchall()
        obs_ids = sorted({str(row[0]) for row in obs_rows if row[0]})
        if not obs_ids:
            return False
        profiles = self._connection.execute(
            "SELECT p.profile_id FROM p6_security_profile_assignments a "
            "JOIN p6_security_profiles p ON p.tenant_id=a.tenant_id AND p.profile_id=a.profile_id "
            "WHERE a.tenant_id=%s AND a.user_id=%s AND p.scope='project' "
            "AND p.active=TRUE AND a.obs_id=ANY(%s)",
            (context.tenant_id,context.user_id,obs_ids),
        ).fetchall()
        profile_ids = [str(row[0]) for row in profiles]
        if not profile_ids:
            return False
        if PROJECT_SUPERUSER_PROFILE_ID in profile_ids:
            return True
        required = (
            "add_projects" if permission == Permission.P6_PROJECT_CREATE
            else "add_edit_delete_eps_except_costs_financials"
        )
        return any(
            required in self._profile_privileges(context.tenant_id, profile_id)
            for profile_id in profile_ids
        )

    def is_allowed_for_wbs(
        self, context: AuthorizationContext, permission: Permission, wbs_id: str,
    ) -> bool:
        """Evaluate project privileges against the responsible OBS of one WBS.

        A WBS-level OBS override is the write boundary. A user assigned only
        to the project/EPS responsible OBS retains read-only visibility of a
        WBS whose responsible OBS differs, matching the V26 security model.
        """
        context.validate()
        if not isinstance(wbs_id, str) or not wbs_id.strip():
            return False
        if self._connection.execute(
            "SELECT 1 FROM wbs_master WHERE tenant_id=%s AND project_id=%s AND wbs_id=%s",
            (context.tenant_id,context.project_id,wbs_id),
        ).fetchone() is None:
            return False
        p6_project_permissions = {
            Permission.PROJECT_READ, Permission.PROJECT_WRITE,
            Permission.PROJECT_SCHEDULE, Permission.PROJECT_ADMIN,
            Permission.P6_WBS_ADMIN, Permission.P6_ACTIVITY_ADMIN,
            Permission.P6_ACTIVITY_RELATIONSHIP_ADMIN, Permission.P6_ACTIVITY_ID_ADMIN,
            Permission.P6_EXPENSE_ADMIN, Permission.P6_DISCUSSION_DELETE,
            Permission.P6_ISSUE_ADMIN, Permission.P6_BASELINE_ADMIN,
            Permission.P6_PROJECT_CALENDAR_ADMIN, Permission.P6_RISK_ADMIN,
            Permission.P6_PROJECT_DOCUMENT_ADMIN, Permission.P6_ASSIGN_PROJECT_BASELINE,
            Permission.P6_APPLY_ACTUALS, Permission.P6_STORE_PERIOD_PERFORMANCE,
            Permission.P6_MONITOR_THRESHOLDS, Permission.P6_COSTS_VIEW,
            Permission.P6_RESOURCE_REQUEST_ADMIN, Permission.P6_EDIT_PERIOD_PERFORMANCE,
            Permission.P6_PROJECT_CHECKOUT_ADMIN,
            Permission.P6_LEVEL_RESOURCES, Permission.P6_BASELINE_UPDATE,
            Permission.P6_GLOBAL_CHANGE, Permission.P6_EPS_ADMIN,
            Permission.P6_PROJECT_CREATE, Permission.P6_PROJECT_DELETE,
            Permission.P6_EPS_COSTS_ADMIN, Permission.P6_WBS_COSTS_ADMIN,
            Permission.P6_EXPORT_PROJECT_DATA, Permission.P6_PROJECT_LEVEL_LAYOUT_ADMIN,
            Permission.P6_REPORT_ADMIN,
        }
        if permission not in p6_project_permissions:
            return self.is_allowed(context, permission)

        admin = self._connection.execute(
            "SELECT 1 FROM p6_security_profile_assignments a "
            "JOIN p6_security_profiles p ON p.tenant_id=a.tenant_id AND p.profile_id=a.profile_id "
            "WHERE a.tenant_id=%s AND a.user_id=%s AND a.profile_id=%s "
            "AND a.obs_id='' AND p.scope='global' AND p.active=TRUE",
            (context.tenant_id,context.user_id,ADMIN_SUPERUSER_PROFILE_ID),
        ).fetchone()
        if admin is not None:
            return True

        global_profile = self._connection.execute(
            "SELECT 1 FROM p6_security_profile_assignments a "
            "JOIN p6_security_profiles p ON p.tenant_id=a.tenant_id AND p.profile_id=a.profile_id "
            "WHERE a.tenant_id=%s AND a.user_id=%s AND p.scope='global' "
            "AND a.obs_id='' AND p.active=TRUE LIMIT 1",
            (context.tenant_id,context.user_id),
        ).fetchone()
        if global_profile is None:
            return False

        project_obs_rows = self._connection.execute(
            "WITH RECURSIVE project_eps(eps_id,parent_eps_id,responsible_obs_id,depth,path) AS ("
            "SELECT eps.eps_id,eps.parent_eps_id,eps.responsible_obs_id,0,ARRAY[eps.eps_id]::text[] "
            "FROM p6_project_eps_assignment assignment "
            "JOIN p6_eps_node eps ON eps.tenant_id=assignment.tenant_id "
            "AND eps.eps_id=assignment.eps_id "
            "WHERE assignment.tenant_id=%s AND assignment.project_id=%s "
            "UNION ALL "
            "SELECT parent.eps_id,parent.parent_eps_id,parent.responsible_obs_id,child.depth+1,child.path || parent.eps_id "
            "FROM p6_eps_node parent JOIN project_eps child "
            "ON child.parent_eps_id=parent.eps_id WHERE parent.tenant_id=%s "
            "AND NOT parent.eps_id=ANY(child.path)), "
            "responsible_obs(obs_id) AS ("
            "SELECT NULLIF(project.obs_id,'') FROM project_lifecycle_projects project "
            "WHERE project.tenant_id=%s AND project.project_id=%s "
            "UNION SELECT NULLIF(responsible_obs_id,'') FROM project_eps) "
            "SELECT DISTINCT obs_id FROM responsible_obs WHERE obs_id IS NOT NULL",
            (context.tenant_id,context.project_id,context.tenant_id,
             context.tenant_id,context.project_id),
        ).fetchall()
        project_obs_ids = {str(row[0]) for row in project_obs_rows}

        wbs_obs_row = self._connection.execute(
            "WITH RECURSIVE wbs_path(wbs_id,parent_kind,parent_wbs_id,depth,path) AS ("
            "SELECT wbs_id,parent_kind,parent_wbs_id,0,ARRAY[wbs_id]::text[] FROM wbs_master "
            "WHERE tenant_id=%s AND project_id=%s AND wbs_id=%s "
            "UNION ALL "
            "SELECT parent.wbs_id,parent.parent_kind,parent.parent_wbs_id,child.depth+1,child.path || parent.wbs_id "
            "FROM wbs_master parent JOIN wbs_path child "
            "ON child.parent_kind='wbs' AND child.parent_wbs_id=parent.wbs_id "
            "WHERE parent.tenant_id=%s AND parent.project_id=%s "
            "AND NOT parent.wbs_id=ANY(child.path)) "
            "SELECT responsibility.responsible_obs_id FROM p6_wbs_obs_responsibility responsibility "
            "JOIN wbs_path path ON path.wbs_id=responsibility.wbs_id "
            "WHERE responsibility.tenant_id=%s AND responsibility.project_id=%s "
            "ORDER BY path.depth LIMIT 1",
            (context.tenant_id,context.project_id,wbs_id,
             context.tenant_id,context.project_id,context.tenant_id,context.project_id),
        ).fetchone()
        if wbs_obs_row is not None:
            effective_obs_id = str(wbs_obs_row[0])
        else:
            # No WBS override: the project OBS takes precedence; otherwise
            # inherit the nearest responsible OBS on the project's EPS branch.
            project_obs = self._connection.execute(
                "SELECT NULLIF(obs_id,'') FROM project_lifecycle_projects "
                "WHERE tenant_id=%s AND project_id=%s",
                (context.tenant_id,context.project_id),
            ).fetchone()
            if project_obs is not None and project_obs[0]:
                effective_obs_id = str(project_obs[0])
            else:
                eps_obs = self._connection.execute(
                    "WITH RECURSIVE project_eps(eps_id,parent_eps_id,responsible_obs_id,depth,path) AS ("
                    "SELECT eps.eps_id,eps.parent_eps_id,eps.responsible_obs_id,0,ARRAY[eps.eps_id]::text[] "
                    "FROM p6_project_eps_assignment assignment "
                    "JOIN p6_eps_node eps ON eps.tenant_id=assignment.tenant_id "
                    "AND eps.eps_id=assignment.eps_id "
                    "WHERE assignment.tenant_id=%s AND assignment.project_id=%s "
                    "UNION ALL "
                    "SELECT parent.eps_id,parent.parent_eps_id,parent.responsible_obs_id,child.depth+1,child.path || parent.eps_id "
                    "FROM p6_eps_node parent JOIN project_eps child "
                    "ON child.parent_eps_id=parent.eps_id WHERE parent.tenant_id=%s "
                    "AND NOT parent.eps_id=ANY(child.path)) "
                    "SELECT NULLIF(responsible_obs_id,'') FROM project_eps "
                    "WHERE responsible_obs_id<>'' ORDER BY depth LIMIT 1",
                    (context.tenant_id,context.project_id,context.tenant_id),
                ).fetchone()
                effective_obs_id = "" if eps_obs is None or eps_obs[0] is None else str(eps_obs[0])
        if not effective_obs_id:
            return False

        profile_rows = self._connection.execute(
            "SELECT p.profile_id,p.active FROM p6_security_profile_assignments a "
            "JOIN p6_security_profiles p ON p.tenant_id=a.tenant_id AND p.profile_id=a.profile_id "
            "WHERE a.tenant_id=%s AND a.user_id=%s AND p.scope='project' "
            "AND a.obs_id=%s",
            (context.tenant_id,context.user_id,effective_obs_id),
        ).fetchall()
        active_profiles = [str(row[0]) for row in profile_rows if bool(row[1])]
        if not active_profiles:
            # Project/EPS responsible OBS grants read-only access to a WBS
            # overridden by another OBS, but never write access.
            if permission != Permission.PROJECT_READ or effective_obs_id in project_obs_ids:
                return False
            if not project_obs_ids:
                return False
            readonly = self._connection.execute(
                "SELECT 1 FROM p6_security_profile_assignments a "
                "JOIN p6_security_profiles p ON p.tenant_id=a.tenant_id AND p.profile_id=a.profile_id "
                "WHERE a.tenant_id=%s AND a.user_id=%s AND p.scope='project' "
                "AND p.active=TRUE AND a.obs_id = ANY(%s) LIMIT 1",
                (context.tenant_id,context.user_id,sorted(project_obs_ids)),
            ).fetchone()
            return readonly is not None

        if permission in p6_project_permissions and any(
            profile_id == PROJECT_SUPERUSER_PROFILE_ID for profile_id in active_profiles
        ):
            return True
        if permission == Permission.PROJECT_READ:
            return True
        required = PROJECT_PERMISSION_PRIVILEGE_MAP.get(permission)
        if required is None:
            return False
        return any(
            required in self._profile_privileges(context.tenant_id, profile_id)
            for profile_id in active_profiles
        )

    def _profile_privileges(self, tenant_id: str, profile_id: str) -> frozenset[str]:
        rows = self._connection.execute(
            "SELECT permission FROM p6_security_profile_privileges "
            "WHERE tenant_id=%s AND profile_id=%s",
            (tenant_id, profile_id),
        ).fetchall()
        return frozenset(str(row[0]) for row in rows)

    def require(self, context: AuthorizationContext, permission: Permission) -> None:
        from .application.authorization import AuthorizationError
        if not self.is_allowed(context, permission):
            raise AuthorizationError(f"authorization denied for permission={permission.value}")