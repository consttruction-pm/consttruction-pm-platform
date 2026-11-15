"""Persisted P6-style global/project security profiles and authorization evaluator.

The evaluator is intentionally restrictive: legacy role grants remain a ceiling;
an assigned global profile and/or project profile can only narrow those grants.
No profile assignment means the legacy policy remains in force during migration.
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
}


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

    def as_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "profile_id": self.profile_id,
            "name": self.name,
            "scope": self.scope,
            "active": self.active,
            "revision": self.revision,
            "privileges": sorted(self.privileges),
        }


SECURITY_PROFILE_SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS p6_security_profiles (
        tenant_id TEXT NOT NULL,
        profile_id TEXT NOT NULL,
        name TEXT NOT NULL CHECK (length(trim(name)) BETWEEN 1 AND 120),
        scope TEXT NOT NULL CHECK (scope IN ('global','project')),
        active BOOLEAN NOT NULL DEFAULT TRUE,
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
    """
    CREATE UNIQUE INDEX IF NOT EXISTS p6_security_profile_one_global_per_user
    ON p6_security_profile_assignments (tenant_id, user_id)
    WHERE obs_id=''
    """,
    """
    CREATE TABLE IF NOT EXISTS p6_security_profile_audit (
        audit_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        actor_user_id TEXT NOT NULL,
        profile_id TEXT NOT NULL,
        action TEXT NOT NULL CHECK (action IN
            ('profile_created','privileges_changed','profile_status_changed',
             'profile_assigned','profile_unassigned')),
        before_state JSONB,
        after_state JSONB NOT NULL,
        occurred_at TIMESTAMPTZ NOT NULL
    )
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


class PostgresSecurityProfileRepository:
    """Tenant-isolated, revision-guarded profile persistence."""

    def __init__(self, connection: Any) -> None:
        self._connection = connection

    def create_profile(
        self, *, tenant_id: str, profile_id: str, name: str, scope: str,
        actor_user_id: str, occurred_at: Any,
    ) -> SecurityProfile:
        if not tenant_id.strip() or not _PROFILE_ID.fullmatch(profile_id):
            raise SecurityProfileError("SECURITY_PROFILE_ID_INVALID")
        if scope not in _PROFILE_SCOPES:
            raise SecurityProfileError("SECURITY_PROFILE_SCOPE_INVALID")
        normalized = name.strip() if isinstance(name, str) else ""
        if not normalized or len(normalized) > 120:
            raise SecurityProfileError("SECURITY_PROFILE_NAME_INVALID")
        self._connection.execute(
            "INSERT INTO p6_security_profiles "
            "(tenant_id,profile_id,name,scope,active,revision,created_by,updated_by,created_at,updated_at) "
            "VALUES (%s,%s,%s,%s,TRUE,1,%s,%s,%s,%s)",
            (tenant_id, profile_id, normalized, scope, actor_user_id,
             actor_user_id, occurred_at, occurred_at),
        )
        self._audit(tenant_id, actor_user_id, profile_id, "profile_created",
                    None, {"name": normalized, "scope": scope, "active": True, "revision": 1},
                    occurred_at)
        return SecurityProfile(tenant_id, profile_id, normalized, scope, True, 1, frozenset())

    def set_privileges(
        self, *, tenant_id: str, profile_id: str, privileges: Iterable[str],
        expected_revision: int, actor_user_id: str, occurred_at: Any,
    ) -> SecurityProfile:
        normalized = frozenset(privileges)
        row = self._connection.execute(
            "SELECT name,scope,active,revision FROM p6_security_profiles "
            "WHERE tenant_id=%s AND profile_id=%s FOR UPDATE",
            (tenant_id, profile_id),
        ).fetchone()
        if row is None:
            raise SecurityProfileError("SECURITY_PROFILE_NOT_FOUND")
        if int(row[3]) != expected_revision:
            raise SecurityProfileError("SECURITY_PROFILE_REVISION_CONFLICT")
        valid = GLOBAL_PRIVILEGES if str(row[1]) == "global" else PROJECT_PRIVILEGES
        if not normalized.issubset(valid):
            raise SecurityProfileError("SECURITY_PROFILE_PRIVILEGE_INVALID")
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
                 "revision": revision, "privileges": sorted(normalized)}
        self._audit(tenant_id, actor_user_id, profile_id, "privileges_changed",
                    before.as_dict(), after, occurred_at)
        return SecurityProfile(tenant_id, profile_id, row[0], row[1], bool(row[2]),
                               revision, normalized)

    def set_active(
        self, *, tenant_id: str, profile_id: str, active: bool,
        expected_revision: int, actor_user_id: str, occurred_at: Any,
    ) -> SecurityProfile:
        if not isinstance(active, bool):
            raise SecurityProfileError("SECURITY_PROFILE_STATUS_INVALID")
        row = self._connection.execute(
            "SELECT name,scope,active,revision FROM p6_security_profiles "
            "WHERE tenant_id=%s AND profile_id=%s FOR UPDATE",
            (tenant_id, profile_id),
        ).fetchone()
        if row is None:
            raise SecurityProfileError("SECURITY_PROFILE_NOT_FOUND")
        if int(row[3]) != expected_revision:
            raise SecurityProfileError("SECURITY_PROFILE_REVISION_CONFLICT")
        before = self.get_profile(tenant_id, profile_id)
        revision = expected_revision + 1
        self._connection.execute(
            "UPDATE p6_security_profiles SET active=%s,revision=%s,updated_by=%s,updated_at=%s "
            "WHERE tenant_id=%s AND profile_id=%s",
            (active, revision, actor_user_id, occurred_at, tenant_id, profile_id),
        )
        after = {**before.as_dict(), "active": active, "revision": revision}
        self._audit(tenant_id, actor_user_id, profile_id, "profile_status_changed",
                    before.as_dict(), after, occurred_at)
        return SecurityProfile(tenant_id, profile_id, row[0], row[1], active,
                               revision, before.privileges)

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
            "SELECT name,scope,active,revision FROM p6_security_profiles "
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
                               int(row[3]), frozenset(str(item[0]) for item in grants))

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
        if not self._role_policy.is_allowed(context, permission):
            return False
        rows = self._connection.execute(
            "SELECT p.scope,p.active,a.obs_id,p.profile_id FROM p6_security_profile_assignments a "
            "JOIN p6_security_profiles p ON p.tenant_id=a.tenant_id AND p.profile_id=a.profile_id "
            "LEFT JOIN project_lifecycle_projects project "
            "ON project.tenant_id=a.tenant_id AND project.project_id=%s "
            "WHERE a.tenant_id=%s AND a.user_id=%s "
            "AND ((p.scope='global' AND a.obs_id='') "
            "OR (p.scope='project' AND a.obs_id=project.obs_id AND project.obs_id<>''))",
            (context.project_id, context.tenant_id, context.user_id),
        ).fetchall()
        global_rows = [row for row in rows if str(row[0]) == "global"]
        project_rows = [row for row in rows if str(row[0]) == "project"]
        # P6 requires a Global Security Profile for every user. Project access
        # requires an active Project profile assigned to the project's responsible
        # OBS. A project profile does not create project membership.
        if not any(bool(row[1]) for row in global_rows):
            return False
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
