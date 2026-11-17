from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.activity_master_repository import (
    ActivityMaster, PostgresActivityMasterRepository, SQLiteActivityMasterRepository,
)
from construction_pm.scheduling.time_duration import DurationUnit
from construction_pm.p6_resource_assignment_repository import (
    P6ResourceAssignment, P6ResourceAssignmentApplicationService,
    P6ResourceAssignmentPeriodApplicationService, P6ResourceAssignmentPeriodValue,
    PostgresP6ResourceAssignmentRepository, PostgresP6ResourceAssignmentPeriodRepository,
)
from construction_pm.p6_resource_write_api import P6ResourceWriteAPI
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.p6_activity_master_api import P6ActivityMasterAPI
from construction_pm.p6_relationship_api import P6RelationshipAPI
from construction_pm.relationship_master_repository import RelationshipMaster, SQLiteRelationshipMasterRepository
from construction_pm.scheduling.relationships import RelationshipType
from construction_pm.p6_issue_api import P6IssueAPI
from construction_pm.p6_issue_repository import P6Issue, SQLiteP6IssueRepository
from construction_pm.risk_application import (
    RiskApplicationService,
    RiskAuthorizationError,
)
from construction_pm.risk_persistence import Risk, SQLiteRiskStore
from construction_pm.threshold_application import (
    ThresholdApplicationService,
    ThresholdAuthorizationError,
)
from construction_pm.threshold_persistence import Threshold, SQLiteThresholdStore
from construction_pm.p6_expense_api import P6ExpenseAPI
from construction_pm.p6_expense_repository import (
    P6Expense, P6ExpenseApplicationService, SQLiteP6ExpenseRepository,
)
from construction_pm.p6_wbs_master_api import P6WBSMasterAPI
from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    Permission,
    RoleBasedAuthorizationPolicy,
    default_role_permissions,
)
from construction_pm.enterprise_organization_access import EnterpriseOrganizationAccessService
from construction_pm.enterprise_organization_access_http import EnterpriseOrganizationAccessHttpMiddleware
from construction_pm.enterprise_organization_access_repository import PostgresEnterpriseOrganizationAccessRepository
from construction_pm.identity_session import (
    IdentityUser,
    PostgresIdentityStore,
    hash_password,
)
from construction_pm.p6_obs_repository import P6OBSNode, PostgresP6OBSRepository
from construction_pm.p6_eps_repository import P6EPSNode, P6EPSError, PostgresP6EPSRepository
from construction_pm.wbs_master_repository import PostgresWBSMasterRepository
from construction_pm.postgres_project_lifecycle import (
    PostgresProjectRepository,
    initialize_project_lifecycle_schema,
)
from construction_pm.security_profiles import (
    PostgresSecurityProfileAuthorizationPolicy,
    PostgresSecurityProfileRepository,
    bootstrap_first_admin_superuser,
    SecurityProfileError,
    initialize_security_profile_schema,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("CONSTRUCTION_PM_POSTGRES_DSN"),
    reason="CONSTRUCTION_PM_POSTGRES_DSN is not configured",
)


def _connect():
    import psycopg
    return psycopg.connect(os.environ["CONSTRUCTION_PM_POSTGRES_DSN"])


def _identity_user(user_id: str, tenant_id: str, role: str = "planner") -> IdentityUser:
    return IdentityUser(
        user_id=user_id,
        tenant_id=tenant_id,
        email=f"{user_id}@example.invalid",
        display_name=user_id,
        roles=frozenset({role}),
        password_hash=hash_password("correct-horse-battery-staple"),
        active=True,
    )


def test_postgres_global_and_project_profiles_narrow_real_authorization():
    suffix = uuid.uuid4().hex
    tenant = f"security-profile-{suffix}"
    user_id = f"profile-user-{suffix}"
    project_id = f"profile-project-{suffix}"
    other_tenant = f"security-profile-other-{suffix}"
    now = datetime.now(timezone.utc)

    with _connect() as connection:
        PostgresIdentityStore(connection).initialize()
        initialize_project_lifecycle_schema(connection)
        PostgresP6OBSRepository(connection).initialize()
        PostgresP6EPSRepository(connection).initialize()
        initialize_security_profile_schema(connection)
        PostgresIdentityStore(connection).upsert_user(_identity_user(user_id, tenant))
        obs_repository = PostgresP6OBSRepository(connection)
        obs_repository.upsert(P6OBSNode(tenant, f"obs-root-{suffix}", name="Profile OBS Root"))
        obs_repository.upsert(P6OBSNode(
            tenant, f"obs-{suffix}", parent_obs_id=f"obs-root-{suffix}", name="Profile OBS Child"
        ))
        PostgresProjectRepository(connection).create_for_user(
            tenant, user_id, project_id, "Profile protected project", obs_id=f"obs-{suffix}"
        )
        connection.commit()

    with _connect() as connection:
        profiles = PostgresSecurityProfileRepository(connection)
        role_policy = RoleBasedAuthorizationPolicy(default_role_permissions())
        policy = PostgresSecurityProfileAuthorizationPolicy(connection, role_policy)
        context = AuthorizationContext(tenant, project_id, user_id, frozenset({"planner"}))

        # P6 requires both a Global profile and an OBS-assigned Project profile.
        assert not policy.is_allowed(context, Permission.PROJECT_READ)
        assert not policy.is_allowed(context, Permission.PROJECT_WRITE)

        global_profile = profiles.create_profile(
            tenant_id=tenant, profile_id="global-limited", name="Global Limited",
            scope="global", actor_user_id=user_id, occurred_at=now,
        )
        global_profile = profiles.set_privileges(
            tenant_id=tenant, profile_id=global_profile.profile_id,
            privileges=set(),
            expected_revision=1, actor_user_id=user_id, occurred_at=now,
        )
        project_profile = profiles.create_profile(
            tenant_id=tenant, profile_id="project-read-only", name="Project Read Only",
            scope="project", actor_user_id=user_id, occurred_at=now,
        )
        project_profile = profiles.set_privileges(
            tenant_id=tenant, profile_id=project_profile.profile_id,
            privileges={"add_edit_activities_except_relationships", "schedule_projects", "delete_project_activity_codes"},
            expected_revision=1, actor_user_id=user_id, occurred_at=now,
        )

        profiles.assign(
            tenant_id=tenant, profile_id="global-limited", user_id=user_id,
            actor_user_id=user_id, occurred_at=now,
        )
        # Global UDF definitions are governed by the V26 Global privilege,
        # not by a generic Project Write grant or the Project Profile.
        assert not policy.is_allowed(context, Permission.P6_UDF_ADMIN)
        profiles.set_privileges(
            tenant_id=tenant, profile_id="global-limited",
            privileges={"add_edit_delete_user_defined_fields"},
            expected_revision=2, actor_user_id=user_id, occurred_at=now,
        )
        assert policy.is_allowed(context, Permission.P6_UDF_ADMIN)

        profiles.create_profile(
            tenant_id=tenant, profile_id="global-replacement", name="Global Replacement",
            scope="global", actor_user_id=user_id, occurred_at=now,
        )
        assert profiles.assign(
            tenant_id=tenant, profile_id="global-replacement", user_id=user_id,
            actor_user_id=user_id, occurred_at=now, expected_revision=1,
        ) == 2
        assert len(profiles.list_assignments(tenant, "global-replacement")) == 1
        with pytest.raises(SecurityProfileError, match="SECURITY_PROFILE_GLOBAL_ASSIGNMENT_REQUIRED"):
            profiles.unassign(
                tenant_id=tenant, profile_id="global-replacement", user_id=user_id,
                expected_revision=2, actor_user_id=user_id, occurred_at=now,
            )
        # A Global profile alone is not project access; OBS Project assignment is required.
        assert not policy.is_allowed(context, Permission.PROJECT_READ)
        with pytest.raises(SecurityProfileError, match="SECURITY_PROFILE_OBS_NOT_FOUND"):
            profiles.assign(
                tenant_id=tenant, profile_id="project-read-only", user_id=user_id,
                obs_id="missing-obs", actor_user_id=user_id, occurred_at=now,
            )
        profiles.assign(
            tenant_id=tenant, profile_id="project-read-only", user_id=user_id,
            obs_id=f"obs-root-{suffix}", actor_user_id=user_id, occurred_at=now,
        )

        # OBS user assignments are exact. EPS responsibility inherits down
        # the EPS branch; it does not imply membership in child OBS elements.
        assert not policy.is_allowed(context, Permission.PROJECT_READ)
        profiles.assign(
            tenant_id=tenant, profile_id="project-read-only", user_id=user_id,
            obs_id=f"obs-{suffix}", actor_user_id=user_id, occurred_at=now,
        )
        assert policy.is_allowed(context, Permission.PROJECT_READ)
        assert policy.is_allowed(context, Permission.PROJECT_SCHEDULE)
        assert not policy.is_allowed(context, Permission.PROJECT_WRITE)
        assert not policy.is_allowed(context, Permission.PROJECT_ADMIN)

        # A profile grant can never exceed the legacy role's ceiling.
        assert not policy.is_allowed(context, Permission.FORM_APPROVE)

        # A profile in another tenant cannot affect this user's effective access.
        foreign = AuthorizationContext(other_tenant, project_id, user_id, frozenset({"planner"}))
        assert not policy.is_allowed(foreign, Permission.PROJECT_WRITE)

        with pytest.raises(SecurityProfileError, match="SECURITY_PROFILE_REVISION_CONFLICT"):
            profiles.set_privileges(
                tenant_id=tenant, profile_id="global-limited",
                privileges={Permission.PROJECT_READ.value},
                expected_revision=1, actor_user_id=user_id, occurred_at=now,
            )

        profiles.set_active(
            tenant_id=tenant, profile_id="project-read-only", active=False,
            expected_revision=2, actor_user_id=user_id, occurred_at=now,
        )
        assert not policy.is_allowed(context, Permission.PROJECT_READ)

        event = connection.execute(
            "SELECT action,before_state,after_state FROM p6_security_profile_audit "
            "WHERE tenant_id=%s AND profile_id=%s AND action='privileges_changed'",
            (tenant, "project-read-only"),
        ).fetchone()
        assert event is not None
        assert event[1]["privileges"] == []
        assert event[2]["privileges"] == ["add_edit_activities_except_relationships", "add_project_activity_codes", "delete_project_activity_codes", "edit_project_activity_codes", "schedule_projects"]

        with pytest.raises(Exception, match="P6_SECURITY_PROFILE_AUDIT_APPEND_ONLY"):
            connection.execute(
                "UPDATE p6_security_profile_audit SET action='tampered' "
                "WHERE tenant_id=%s AND profile_id=%s",
                (tenant, "project-read-only"),
            )
        connection.rollback()


def _http_request(
    app, method: str, path: str, *, session_id: str,
    payload: dict | None = None, query_string: str = "",
):
    raw = b"" if payload is None else json.dumps(payload).encode("utf-8")
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query_string,
        "CONTENT_LENGTH": str(len(raw)),
        "wsgi.input": BytesIO(raw),
        "HTTP_COOKIE": f"cp_session={session_id}",
    }
    captured = {}
    def start_response(status, headers):
        captured["status"] = status
    body = b"".join(app(environ, start_response))
    return int(str(captured["status"]).split(" ", 1)[0]), json.loads(body)


def test_security_profile_admin_http_api_is_tenant_and_global_privilege_guarded():
    suffix = uuid.uuid4().hex
    tenant = f"profile-http-{suffix}"
    admin_id = f"profile-admin-{suffix}"
    target_id = f"profile-target-{suffix}"
    user_admin_id = f"profile-user-admin-{suffix}"
    profile_admin_only_id = f"profile-profile-admin-only-{suffix}"
    role_only_id = f"profile-role-only-{suffix}"
    project_id = f"profile-http-project-{suffix}"
    other_tenant = f"profile-http-other-{suffix}"
    now = datetime.now(timezone.utc)

    with _connect() as connection:
        identity = PostgresIdentityStore(connection)
        identity.initialize()
        initialize_project_lifecycle_schema(connection)
        PostgresP6OBSRepository(connection).initialize()
        PostgresP6EPSRepository(connection).initialize()
        initialize_security_profile_schema(connection)
        identity.upsert_user(_identity_user(admin_id, tenant, "enterprise_admin"))
        identity.upsert_user(_identity_user(target_id, tenant, "planner"))
        identity.upsert_user(_identity_user(user_admin_id, tenant, "planner"))
        identity.upsert_user(_identity_user(profile_admin_only_id, tenant, "planner"))
        identity.upsert_user(_identity_user(role_only_id, tenant, "enterprise_admin"))
        PostgresP6OBSRepository(connection).upsert(P6OBSNode(tenant, f"obs-{suffix}", name="Profile HTTP OBS"))
        profiles = PostgresSecurityProfileRepository(connection)
        profile_admin = profiles.create_profile(
            tenant_id=tenant, profile_id="http-profile-admin", name="HTTP Profile Administrator",
            scope="global", actor_user_id=admin_id, occurred_at=now,
        )
        profiles.set_privileges(
            tenant_id=tenant, profile_id=profile_admin.profile_id,
            privileges={"add_edit_delete_security_profiles", "add_edit_delete_users"},
            expected_revision=1, actor_user_id=admin_id, occurred_at=now,
        )
        profiles.assign(
            tenant_id=tenant, profile_id=profile_admin.profile_id, user_id=admin_id,
            actor_user_id=admin_id, occurred_at=now,
        )
        user_admin_profile = profiles.create_profile(
            tenant_id=tenant, profile_id="http-user-admin", name="HTTP User Administrator",
            scope="global", actor_user_id=admin_id, occurred_at=now,
        )
        profiles.set_privileges(
            tenant_id=tenant, profile_id=user_admin_profile.profile_id,
            privileges={"add_edit_delete_users"}, expected_revision=1,
            actor_user_id=admin_id, occurred_at=now,
        )
        profiles.assign(
            tenant_id=tenant, profile_id=user_admin_profile.profile_id, user_id=user_admin_id,
            actor_user_id=admin_id, occurred_at=now,
        )
        profile_admin_only = profiles.create_profile(
            tenant_id=tenant, profile_id="http-profile-admin-only", name="HTTP Profile Administrator Only",
            scope="global", actor_user_id=admin_id, occurred_at=now,
        )
        profiles.set_privileges(
            tenant_id=tenant, profile_id=profile_admin_only.profile_id,
            privileges={"add_edit_delete_security_profiles"}, expected_revision=1,
            actor_user_id=admin_id, occurred_at=now,
        )
        profiles.assign(
            tenant_id=tenant, profile_id=profile_admin_only.profile_id, user_id=profile_admin_only_id,
            actor_user_id=admin_id, occurred_at=now,
        )
        profiles.create_profile(
            tenant_id=other_tenant, profile_id="foreign-only", name="Foreign Only",
            scope="project", actor_user_id=admin_id, occurred_at=now,
        )
        PostgresProjectRepository(connection).create_for_user(
            tenant, target_id, project_id, "Profile HTTP project", obs_id=f"obs-{suffix}"
        )
        connection.commit()

    class Sessions:
        def get_session(self, session_id, *, now=None):
            if session_id == "admin-session":
                return SimpleNamespace(user_id=admin_id, tenant_id=tenant, roles=frozenset({"enterprise_admin"}))
            if session_id == "planner-session":
                return SimpleNamespace(user_id=target_id, tenant_id=tenant, roles=frozenset({"planner"}))
            if session_id == "user-admin-session":
                return SimpleNamespace(user_id=user_admin_id, tenant_id=tenant, roles=frozenset({"planner"}))
            if session_id == "profile-admin-only-session":
                return SimpleNamespace(user_id=profile_admin_only_id, tenant_id=tenant, roles=frozenset({"planner"}))
            if session_id == "role-only-session":
                return SimpleNamespace(user_id=role_only_id, tenant_id=tenant, roles=frozenset({"enterprise_admin"}))
            return None

    with _connect() as connection:
        profiles = PostgresSecurityProfileRepository(connection)
        service = EnterpriseOrganizationAccessService(
            PostgresEnterpriseOrganizationAccessRepository(connection),
            Sessions(),
            security_profiles=profiles,
        )
        app = EnterpriseOrganizationAccessHttpMiddleware(lambda environ, start: [], service)

        # P6 Global privileges independently authorize account and profile administration.
        status, user_list = _http_request(app, "GET", "/api/enterprise/users", session_id="user-admin-session")
        assert status == 200 and user_list["users"]
        status, profile_list_denied = _http_request(
            app, "GET", "/api/enterprise/security-profiles", session_id="user-admin-session",
        )
        assert status == 403 and profile_list_denied["code"] == "P6_GLOBAL_PRIVILEGE_REQUIRED"
        status, profile_admin_only_profiles = _http_request(
            app, "GET", "/api/enterprise/security-profiles", session_id="profile-admin-only-session",
        )
        assert status == 200 and profile_admin_only_profiles["profiles"]
        status, profile_admin_only_users = _http_request(
            app, "GET", "/api/enterprise/users", session_id="profile-admin-only-session",
        )
        assert status == 403 and profile_admin_only_users["code"] == "P6_GLOBAL_PRIVILEGE_REQUIRED"
        status, role_only_users = _http_request(app, "GET", "/api/enterprise/users", session_id="role-only-session")
        assert status == 403 and role_only_users["code"] == "P6_GLOBAL_PRIVILEGE_REQUIRED"
        status, role_only_profiles = _http_request(
            app, "POST", "/api/enterprise/security-profiles", session_id="role-only-session",
            payload={
                "contract_version": "cubi-p6-security-profile.v1",
                "profile_id": "role-only-profile", "name": "Role Only", "scope": "global",
            },
        )
        assert status == 403 and role_only_profiles["code"] == "P6_GLOBAL_PRIVILEGE_REQUIRED"
        assert not profiles.has_global_privilege(other_tenant, admin_id, "add_edit_delete_users")

        status, global_created = _http_request(
            app, "POST", "/api/enterprise/security-profiles", session_id="admin-session",
            payload={
                "contract_version": "cubi-p6-security-profile.v1",
                "profile_id": "http-global", "name": "HTTP Global", "scope": "global",
            },
        )
        assert status == 201, global_created
        status, profile_admin_only_assignment = _http_request(
            app, "PUT", "/api/enterprise/security-profiles/http-global/assignments",
            session_id="profile-admin-only-session",
            payload={
                "contract_version": "cubi-p6-security-profile-assignment.v1",
                "user_id": target_id,
            },
        )
        assert status == 403 and profile_admin_only_assignment["code"] == "P6_GLOBAL_PRIVILEGE_REQUIRED"
        status, global_assigned = _http_request(
            app, "PUT", "/api/enterprise/security-profiles/http-global/assignments",
            session_id="admin-session",
            payload={
                "contract_version": "cubi-p6-security-profile-assignment.v1",
                "user_id": target_id,
            },
        )
        assert status == 200 and global_assigned["revision"] == 1

        # Add/Edit/Delete Users can assign profiles, but does not grant profile CRUD.
        status, user_admin_assignment = _http_request(
            app, "PUT", "/api/enterprise/security-profiles/http-global/assignments",
            session_id="user-admin-session",
            payload={
                "contract_version": "cubi-p6-security-profile-assignment.v1",
                "user_id": target_id, "expected_revision": 1,
            },
        )
        assert status == 200 and user_admin_assignment["revision"] == 2

        # V26 Module Access and Resource Access are user attributes attached to
        # the same canonical Global profile assignment, not a second profile store.
        status, access_before = _http_request(
            app, "GET", f"/api/enterprise/users/{target_id}/global-access",
            session_id="user-admin-session",
        )
        assert status == 200
        assert access_before["access"]["profile_id"] == "http-global"
        assert access_before["access"]["module_access"] == ["projects"]
        assert access_before["access"]["resource_access_mode"] == "none"
        status, access_saved = _http_request(
            app, "PATCH", f"/api/enterprise/users/{target_id}/global-access",
            session_id="user-admin-session",
            payload={
                "contract_version": "cubi-p6-user-global-access.v1",
                "module_access": ["resources", "projects"],
                "resource_access_mode": "all",
                "resource_root_ids": [],
                "expected_revision": 2,
            },
        )
        assert status == 200, access_saved
        assert access_saved["access"]["revision"] == 3
        assert access_saved["access"]["module_access"] == ["projects", "resources"]
        assert access_saved["access"]["resource_access_mode"] == "all"
        status, denied_global_access = _http_request(
            app, "GET", f"/api/enterprise/users/{target_id}/global-access",
            session_id="profile-admin-only-session",
        )
        assert status == 403 and denied_global_access["code"] == "P6_GLOBAL_PRIVILEGE_REQUIRED"
        status, denied_global_access = _http_request(
            app, "PATCH", f"/api/enterprise/users/{target_id}/global-access",
            session_id="role-only-session",
            payload={
                "contract_version": "cubi-p6-user-global-access.v1",
                "module_access": ["projects"],
                "resource_access_mode": "none",
                "expected_revision": 3,
            },
        )
        assert status == 403 and denied_global_access["code"] == "P6_GLOBAL_PRIVILEGE_REQUIRED"
        status, invalid_contributor = _http_request(
            app, "PATCH", f"/api/enterprise/users/{target_id}/global-access",
            session_id="user-admin-session",
            payload={
                "contract_version": "cubi-p6-user-global-access.v1",
                "module_access": ["contributor", "projects"],
                "resource_access_mode": "none",
                "expected_revision": 3,
            },
        )
        assert status == 400 and invalid_contributor["code"] == "SECURITY_PROFILE_CONTRIBUTOR_MODULE_EXCLUSIVE"

        status, created = _http_request(
            app, "POST", "/api/enterprise/security-profiles", session_id="admin-session",
            payload={
                "contract_version": "cubi-p6-security-profile.v1",
                "profile_id": "http-project-reader", "name": "HTTP Project Reader",
                "description": "A scoped project reader profile.", "scope": "project",
            },
        )
        assert status == 201, created
        assert created["profile"]["revision"] == 1
        assert created["profile"]["description"] == "A scoped project reader profile."
        assert created["profile"]["is_default"] is False

        status, details = _http_request(
            app, "PATCH", "/api/enterprise/security-profiles/http-project-reader/details",
            session_id="admin-session",
            payload={
                "contract_version": "cubi-p6-security-profile-details.v1",
                "expected_revision": 1, "name": "HTTP Project Reader Updated",
                "description": "Updated description with a revision guard.",
            },
        )
        assert status == 200, details
        assert details["profile"]["revision"] == 2
        assert details["profile"]["description"] == "Updated description with a revision guard."
        status, stale_details = _http_request(
            app, "PATCH", "/api/enterprise/security-profiles/http-project-reader/details",
            session_id="admin-session",
            payload={
                "contract_version": "cubi-p6-security-profile-details.v1",
                "expected_revision": 1, "name": "Stale Update", "description": "",
            },
        )
        assert status == 409 and stale_details["code"] == "SECURITY_PROFILE_REVISION_CONFLICT"

        status, changed = _http_request(
            app, "PATCH", "/api/enterprise/security-profiles/http-project-reader/privileges",
            session_id="admin-session",
            payload={
                "contract_version": "cubi-p6-security-profile-privileges.v1",
                "expected_revision": 2, "privileges": ["add_edit_activities_except_relationships", "delete_project_activity_codes", "schedule_projects"],
            },
        )
        assert status == 200, changed
        assert changed["profile"]["revision"] == 3

        status, defaulted = _http_request(
            app, "PATCH", "/api/enterprise/security-profiles/http-project-reader/default",
            session_id="admin-session",
            payload={
                "contract_version": "cubi-p6-security-profile-default.v1",
                "expected_revision": 3, "is_default": True,
            },
        )
        assert status == 200, defaulted
        assert defaulted["profile"]["revision"] == 4
        assert defaulted["profile"]["is_default"] is True

        status, role_only_details = _http_request(
            app, "PATCH", "/api/enterprise/security-profiles/http-project-reader/details",
            session_id="role-only-session",
            payload={
                "contract_version": "cubi-p6-security-profile-details.v1",
                "expected_revision": 4, "name": "Unauthorized", "description": "",
            },
        )
        assert status == 403 and role_only_details["code"] == "P6_GLOBAL_PRIVILEGE_REQUIRED"

        status, foreign_profile = _http_request(
            app, "GET", "/api/enterprise/security-profiles/foreign-only/assignments",
            session_id="admin-session",
        )
        assert status == 404 and foreign_profile["code"] == "SECURITY_PROFILE_NOT_FOUND"

        status, duplicated = _http_request(
            app, "POST", "/api/enterprise/security-profiles/http-project-reader/duplicate",
            session_id="admin-session",
            payload={
                "contract_version": "cubi-p6-security-profile-duplicate.v1",
                "profile_id": "http-project-reader-copy", "name": "HTTP Project Reader Copy",
            },
        )
        assert status == 201, duplicated
        assert duplicated["profile"]["revision"] == 1
        assert duplicated["profile"]["description"] == "Updated description with a revision guard."
        assert duplicated["profile"]["is_default"] is False
        assert set(duplicated["profile"]["privileges"]) == set(changed["profile"]["privileges"])

        status, assigned = _http_request(
            app, "PUT", "/api/enterprise/security-profiles/http-project-reader/assignments",
            session_id="admin-session",
            payload={
                "contract_version": "cubi-p6-security-profile-assignment.v1",
                "user_id": target_id, "obs_id": f"obs-{suffix}",
            },
        )
        assert status == 200 and assigned["revision"] == 1

        status, assigned_delete = _http_request(
            app, "DELETE", "/api/enterprise/security-profiles/http-project-reader",
            session_id="admin-session", query_string="expected_revision=4",
        )
        assert status == 409 and assigned_delete["code"] == "SECURITY_PROFILE_ASSIGNED_CANNOT_DELETE"

        status, duplicate_delete = _http_request(
            app, "DELETE", "/api/enterprise/security-profiles/http-project-reader-copy",
            session_id="admin-session", query_string="expected_revision=1",
        )
        assert status == 200 and duplicate_delete["deleted"] is True
        deleted_audit = connection.execute(
            "SELECT action FROM p6_security_profile_audit WHERE tenant_id=%s "
            "AND profile_id='http-project-reader-copy' ORDER BY occurred_at DESC LIMIT 1",
            (tenant,),
        ).fetchone()
        assert deleted_audit is not None and deleted_audit[0] == "profile_deleted"

        status, assignment_list = _http_request(
            app, "GET", "/api/enterprise/security-profiles/http-project-reader/assignments",
            session_id="admin-session",
        )
        assert status == 200
        assert assignment_list["assignments"][0]["obs_id"] == f"obs-{suffix}"

        status, self_assign = _http_request(
            app, "PUT", "/api/enterprise/security-profiles/http-global/assignments",
            session_id="admin-session",
            payload={
                "contract_version": "cubi-p6-security-profile-assignment.v1",
                "user_id": admin_id,
            },
        )
        assert status == 403
        assert self_assign["code"] == "SECURITY_PROFILE_SELF_ASSIGNMENT_NOT_ALLOWED"

        status, denied = _http_request(
            app, "POST", "/api/enterprise/security-profiles",
            session_id="planner-session",
            payload={
                "contract_version": "cubi-p6-security-profile.v1",
                "profile_id": "not-admin", "name": "Not Admin", "scope": "global",
            },
        )
        assert status == 403
        assert denied["code"] == "P6_GLOBAL_PRIVILEGE_REQUIRED"

        policy = PostgresSecurityProfileAuthorizationPolicy(
            connection, RoleBasedAuthorizationPolicy(default_role_permissions())
        )
        context = AuthorizationContext(tenant, project_id, target_id, frozenset({"planner"}))
        assert policy.is_allowed(context, Permission.PROJECT_READ)
        assert not policy.is_allowed(context, Permission.PROJECT_WRITE)
        connection.commit()

def test_p6_admin_superuser_builtin_is_protected_and_bypasses_profile_scope():
    suffix = uuid.uuid4().hex
    tenant = f"admin-superuser-{suffix}"
    admin_id = f"p6-admin-{suffix}"
    target_id = f"p6-target-{suffix}"
    project_id = f"p6-project-{suffix}"
    obs_id = f"p6-obs-{suffix}"
    now = datetime.now(timezone.utc)

    with _connect() as connection:
        identity = PostgresIdentityStore(connection)
        identity.initialize()
        initialize_project_lifecycle_schema(connection)
        PostgresP6OBSRepository(connection).initialize()
        PostgresP6EPSRepository(connection).initialize()
        initialize_security_profile_schema(connection)
        identity.upsert_user(_identity_user(admin_id, tenant, "enterprise_admin"))
        identity.upsert_user(_identity_user(target_id, tenant, "planner"))
        PostgresP6OBSRepository(connection).upsert(P6OBSNode(tenant, obs_id, name="Admin Scope"))
        PostgresProjectRepository(connection).create_for_user(
            tenant, target_id, project_id, "Admin Superuser project", obs_id=obs_id
        )
        # Controlled installation bootstrap: this reserved built-in is inserted
        # only by the trusted installation operator, never through the tenant API.
        connection.execute(
            "INSERT INTO p6_security_profiles "
            "(tenant_id,profile_id,name,scope,active,revision,created_by,updated_by,created_at,updated_at) "
            "VALUES (%s,'p6-admin-superuser','Admin Superuser','global',TRUE,1,%s,%s,%s,%s)",
            (tenant, admin_id, admin_id, now, now),
        )
        connection.execute(
            "INSERT INTO p6_security_profile_assignments "
            "(tenant_id,profile_id,user_id,obs_id,revision,assigned_by,assigned_at) "
            "VALUES (%s,'p6-admin-superuser',%s,'',1,%s,%s)",
            (tenant, admin_id, admin_id, now),
        )
        connection.commit()

    with _connect() as connection:
        profiles = PostgresSecurityProfileRepository(connection)
        assert profiles.has_global_privilege(tenant, admin_id, "add_edit_delete_users")
        assert profiles.has_global_privilege(tenant, admin_id, "add_edit_delete_security_profiles")
        assert not profiles.has_global_privilege(tenant, target_id, "add_edit_delete_users")
        policy = PostgresSecurityProfileAuthorizationPolicy(
            connection, RoleBasedAuthorizationPolicy(default_role_permissions())
        )
        admin_context = AuthorizationContext(tenant, project_id, admin_id, frozenset({"viewer"}))
        assert policy.is_allowed(admin_context, Permission.PROJECT_READ)
        assert policy.is_allowed(admin_context, Permission.PROJECT_WRITE)

        with pytest.raises(SecurityProfileError, match="SECURITY_PROFILE_BUILTIN_PROTECTED"):
            profiles.create_profile(
                tenant_id=tenant, profile_id="p6-admin-superuser",
                name="Forged Admin", scope="global", actor_user_id=admin_id, occurred_at=now,
            )
        with pytest.raises(SecurityProfileError, match="SECURITY_PROFILE_BUILTIN_PROTECTED"):
            profiles.set_active(
                tenant_id=tenant, profile_id="p6-admin-superuser", active=False,
                expected_revision=1, actor_user_id=admin_id, occurred_at=now,
            )
        with pytest.raises(SecurityProfileError, match="SECURITY_PROFILE_BUILTIN_PROTECTED"):
            profiles.set_privileges(
                tenant_id=tenant, profile_id="p6-admin-superuser", privileges=set(),
                expected_revision=1, actor_user_id=admin_id, occurred_at=now,
            )

        with pytest.raises(SecurityProfileError, match="SECURITY_PROFILE_BUILTIN_PROTECTED"):
            profiles.update_details(
                tenant_id=tenant, profile_id="p6-admin-superuser",
                name="Forged Admin", description="not editable", expected_revision=1,
                actor_user_id=admin_id, occurred_at=now,
            )
        with pytest.raises(SecurityProfileError, match="SECURITY_PROFILE_BUILTIN_PROTECTED"):
            profiles.set_default(
                tenant_id=tenant, profile_id="p6-admin-superuser", is_default=True,
                expected_revision=1, actor_user_id=admin_id, occurred_at=now,
            )
        with pytest.raises(SecurityProfileError, match="SECURITY_PROFILE_BUILTIN_PROTECTED"):
            profiles.duplicate_profile(
                tenant_id=tenant, source_profile_id="p6-admin-superuser",
                profile_id="admin-superuser-copy", name="Forged Admin Copy",
                actor_user_id=admin_id, occurred_at=now,
            )
        with pytest.raises(SecurityProfileError, match="SECURITY_PROFILE_BUILTIN_PROTECTED"):
            profiles.delete_profile(
                tenant_id=tenant, profile_id="p6-admin-superuser", expected_revision=1,
                actor_user_id=admin_id, occurred_at=now,
            )

        with pytest.raises(SecurityProfileError, match="SECURITY_PROFILE_ADMIN_SUPERUSER_ASSIGNER_REQUIRED"):
            profiles.assign(
                tenant_id=tenant, profile_id="p6-admin-superuser", user_id=target_id,
                actor_user_id=target_id, occurred_at=now,
            )
        assert profiles.assign(
            tenant_id=tenant, profile_id="p6-admin-superuser", user_id=target_id,
            actor_user_id=admin_id, occurred_at=now,
        ) == 1

        profiles.create_profile(
            tenant_id=tenant, profile_id="ordinary-global", name="Ordinary Global",
            scope="global", actor_user_id=admin_id, occurred_at=now,
        )
        # No Global Privileges still permits OBS-scoped Project Superuser access.
        connection.execute(
            "INSERT INTO p6_security_profiles "
            "(tenant_id,profile_id,name,scope,active,revision,created_by,updated_by,created_at,updated_at) "
            "VALUES (%s,'p6-no-global-privileges','No Global Privileges','global',TRUE,1,%s,%s,%s,%s)",
            (tenant, admin_id, admin_id, now, now),
        )
        profiles.assign(
            tenant_id=tenant, profile_id="p6-no-global-privileges", user_id=target_id,
            actor_user_id=admin_id, occurred_at=now, expected_revision=1,
        )
        # The second Admin Superuser has now been replaced; the remaining
        # administrator cannot remove their own final Admin Superuser grant.
        with pytest.raises(SecurityProfileError, match="SECURITY_PROFILE_LAST_ADMIN_SUPERUSER_REQUIRED"):
            profiles.assign(
                tenant_id=tenant, profile_id="ordinary-global", user_id=admin_id,
                actor_user_id=admin_id, occurred_at=now, expected_revision=1,
            )
        connection.execute(
            "INSERT INTO p6_security_profiles "
            "(tenant_id,profile_id,name,scope,active,revision,created_by,updated_by,created_at,updated_at) "
            "VALUES (%s,'p6-project-superuser','Project Superuser','project',TRUE,1,%s,%s,%s,%s)",
            (tenant, admin_id, admin_id, now, now),
        )
        with pytest.raises(SecurityProfileError, match="SECURITY_PROFILE_ADMIN_SUPERUSER_ASSIGNER_REQUIRED"):
            profiles.assign(
                tenant_id=tenant, profile_id="p6-project-superuser", user_id=target_id,
                obs_id=obs_id, actor_user_id=target_id, occurred_at=now,
            )
        profiles.assign(
            tenant_id=tenant, profile_id="p6-project-superuser", user_id=target_id,
            obs_id=obs_id, actor_user_id=admin_id, occurred_at=now,
        )
        with pytest.raises(SecurityProfileError, match="SECURITY_PROFILE_ADMIN_SUPERUSER_ASSIGNER_REQUIRED"):
            profiles.unassign(
                tenant_id=tenant, profile_id="p6-project-superuser", user_id=target_id,
                obs_id=obs_id, expected_revision=1, actor_user_id=target_id, occurred_at=now,
            )
        target_context = AuthorizationContext(tenant, project_id, target_id, frozenset({"viewer"}))
        assert policy.is_allowed(target_context, Permission.PROJECT_SCHEDULE)
        assert policy.is_allowed(target_context, Permission.PROJECT_WRITE)
        connection.rollback()

def test_operator_bootstrap_and_recovery_preserve_one_active_admin_superuser():
    suffix = uuid.uuid4().hex
    tenant = f"p6-bootstrap-{suffix}"
    first_id = f"p6-bootstrap-first-{suffix}"
    second_id = f"p6-bootstrap-second-{suffix}"
    now = datetime.now(timezone.utc)
    secret = "one-time-installation-bootstrap-secret-0123456789"

    with _connect() as connection:
        identity = PostgresIdentityStore(connection)
        identity.initialize()
        initialize_project_lifecycle_schema(connection)
        PostgresP6OBSRepository(connection).initialize()
        PostgresP6EPSRepository(connection).initialize()
        initialize_security_profile_schema(connection)
        identity.upsert_user(_identity_user(first_id, tenant, "project_admin"))
        identity.upsert_user(_identity_user(second_id, tenant, "project_admin"))
        connection.commit()

    with _connect() as connection:
        with pytest.raises(SecurityProfileError, match="SECURITY_PROFILE_BOOTSTRAP_TOKEN_INVALID"):
            bootstrap_first_admin_superuser(
                connection, tenant_id=tenant, user_id=first_id,
                supplied_token="wrong-token", configured_token=secret, occurred_at=now,
            )
        profile = bootstrap_first_admin_superuser(
            connection, tenant_id=tenant, user_id=first_id,
            supplied_token=secret, configured_token=secret, occurred_at=now,
        )
        assert profile.profile_id == "p6-admin-superuser"
        builtins = connection.execute(
            "SELECT profile_id,name,scope,active FROM p6_security_profiles "
            "WHERE tenant_id=%s AND profile_id IN "
            "('p6-admin-superuser','p6-no-global-privileges','p6-project-superuser')",
            (tenant,),
        ).fetchall()
        assert {(row[0],row[1],row[2],bool(row[3])) for row in builtins} == {
            ("p6-admin-superuser","Admin Superuser","global",True),
            ("p6-no-global-privileges","No Global Privileges","global",True),
            ("p6-project-superuser","Project Superuser","project",True),
        }
        connection.commit()

    with _connect() as connection:
        with pytest.raises(SecurityProfileError, match="SECURITY_PROFILE_BOOTSTRAP_ALREADY_INITIALIZED"):
            bootstrap_first_admin_superuser(
                connection, tenant_id=tenant, user_id=second_id,
                supplied_token=secret, configured_token=secret, occurred_at=now,
            )
        connection.rollback()

    with _connect() as connection:
        access_repository = PostgresEnterpriseOrganizationAccessRepository(connection)
        access_repository.initialize()
        with pytest.raises(Exception, match="LAST_P6_ADMIN_SUPERUSER_CANNOT_BE_DEACTIVATED"):
            access_repository.set_account_active(
                tenant, first_id, second_id, False, now,
            )
        connection.rollback()

    # Simulate an out-of-band account loss; the operator recovery path may
    # appoint a replacement only when no active Admin Superuser remains.
    with _connect() as connection:
        identity = PostgresIdentityStore(connection)
        identity.upsert_user(IdentityUser(
            user_id=first_id, tenant_id=tenant, email=f"{first_id}@example.invalid",
            display_name=first_id, roles=frozenset({"project_admin"}),
            password_hash=hash_password("correct-horse-battery-staple"), active=False,
        ))
        connection.commit()

    with _connect() as connection:
        profile = bootstrap_first_admin_superuser(
            connection, tenant_id=tenant, user_id=second_id,
            supplied_token=secret, configured_token=secret, occurred_at=now,
        )
        assert profile.profile_id == "p6-admin-superuser"
        builtins = connection.execute(
            "SELECT profile_id,scope FROM p6_security_profiles "
            "WHERE tenant_id=%s AND profile_id IN "
            "('p6-admin-superuser','p6-no-global-privileges','p6-project-superuser')",
            (tenant,),
        ).fetchall()
        assert {row[0] for row in builtins} == {
            "p6-admin-superuser", "p6-no-global-privileges", "p6-project-superuser"
        }
        assert {row[1] for row in builtins} == {"global", "project"}
        connection.commit()

    with _connect() as connection:
        access_repository = PostgresEnterpriseOrganizationAccessRepository(connection)
        access_repository.initialize()
        result = access_repository.set_account_active(
            tenant, first_id, second_id, False, now,
        )
        assert result["changed"] is False
        connection.rollback()

def test_eps_responsibility_inherits_project_profile_access_through_eps_ancestors():
    suffix = uuid.uuid4().hex
    tenant = f"eps-security-{suffix}"
    user_id = f"eps-user-{suffix}"
    project_id = f"eps-project-{suffix}"
    obs_id = f"eps-obs-{suffix}"
    root_id = f"eps-root-{suffix}"
    child_id = f"eps-child-{suffix}"
    now = datetime.now(timezone.utc)

    with _connect() as connection:
        identity = PostgresIdentityStore(connection)
        identity.initialize()
        initialize_project_lifecycle_schema(connection)
        PostgresP6OBSRepository(connection).initialize()
        PostgresP6EPSRepository(connection).initialize()
        initialize_security_profile_schema(connection)
        identity.upsert_user(_identity_user(user_id, tenant, "planner"))
        PostgresP6OBSRepository(connection).upsert(
            P6OBSNode(tenant, obs_id, name="EPS Responsible OBS")
        )
        other_obs_id = f"eps-other-obs-{suffix}"
        PostgresP6OBSRepository(connection).upsert(
            P6OBSNode(tenant, other_obs_id, name="WBS Override OBS")
        )
        PostgresProjectRepository(connection).create_for_user(
            tenant, user_id, project_id, "EPS inherited project"
        )
        PostgresWBSMasterRepository(connection).initialize()
        connection.execute(
            "INSERT INTO wbs_master "
            "(tenant_id,project_id,project_revision,wbs_id,parent_kind,parent_wbs_id,"
            "code,name,sequence_number,record_revision,status,percent_complete_technique) "
            "VALUES (%s,%s,0,%s,'project',NULL,'ROOT','Root WBS',0,1,'active','activities')",
            (tenant, project_id, f"eps-wbs-{suffix}"),
        )
        connection.execute(
            "INSERT INTO wbs_master "
            "(tenant_id,project_id,project_revision,wbs_id,parent_kind,parent_wbs_id,"
            "code,name,sequence_number,record_revision,status,percent_complete_technique) "
            "VALUES (%s,%s,0,%s,'wbs',%s,'OVERRIDE','WBS OBS Override',1,1,'active','activities')",
            (tenant, project_id, f"eps-wbs-override-{suffix}", f"eps-wbs-{suffix}"),
        )
        connection.execute(
            "INSERT INTO wbs_master "
            "(tenant_id,project_id,project_revision,wbs_id,parent_kind,parent_wbs_id,"
            "code,name,sequence_number,record_revision,status,percent_complete_technique) "
            "VALUES (%s,%s,0,%s,'wbs',%s,'INHERIT','WBS Inherited OBS',2,1,'active','activities')",
            (tenant, project_id, f"eps-wbs-inherit-{suffix}", f"eps-wbs-{suffix}"),
        )
        eps = PostgresP6EPSRepository(connection)
        eps.save_node(P6EPSNode(tenant, root_id, "Root EPS", responsible_obs_id=obs_id), actor_user_id=user_id, occurred_at=now)
        eps.save_node(P6EPSNode(tenant, child_id, "Child EPS", parent_eps_id=root_id), actor_user_id=user_id, occurred_at=now)
        eps.assign_project(
            tenant, project_id, child_id, actor_user_id=user_id, occurred_at=now,
        )
        assert connection.execute(
            "SELECT count(*) FROM p6_eps_audit WHERE tenant_id=%s",
            (tenant,),
        ).fetchone()[0] == 3
        assert eps.assign_wbs_responsibility(
            tenant, project_id, f"eps-wbs-{suffix}", obs_id,
            actor_user_id=user_id, occurred_at=now,
        ) == 1
        assert eps.get_wbs_responsibility(
            tenant, project_id, f"eps-wbs-{suffix}"
        ) == (obs_id, 1)
        # The immediate parent WBS has an explicit OBS assignment, so it
        # takes precedence over the inherited EPS responsibility.
        assert eps.get_effective_wbs_responsibility(
            tenant, project_id, f"eps-wbs-inherit-{suffix}"
        ) == (obs_id, 1, "wbs_parent")
        eps.assign_wbs_responsibility(
            tenant, project_id, f"eps-wbs-override-{suffix}", other_obs_id,
            actor_user_id=user_id, occurred_at=now,
        )
        with pytest.raises(P6EPSError, match="P6_WBS_RESPONSIBILITY_REVISION_CONFLICT"):
            eps.assign_wbs_responsibility(
                tenant, project_id, f"eps-wbs-{suffix}", obs_id,
                actor_user_id=user_id, occurred_at=now, expected_revision=0,
            )
        connection.commit()

    with _connect() as connection:
        eps = PostgresP6EPSRepository(connection)
        profiles = PostgresSecurityProfileRepository(connection)
        global_profile = profiles.create_profile(
            tenant_id=tenant, profile_id=f"eps-global-{suffix}", name="EPS Global",
            scope="global", actor_user_id=user_id, occurred_at=now,
        )
        project_profile = profiles.create_profile(
            tenant_id=tenant, profile_id=f"eps-project-{suffix}", name="EPS Project",
            scope="project", actor_user_id=user_id, occurred_at=now,
        )
        profiles.assign(
            tenant_id=tenant, profile_id=global_profile.profile_id, user_id=user_id,
            actor_user_id=user_id, occurred_at=now,
        )
        profiles.assign(
            tenant_id=tenant, profile_id=project_profile.profile_id, user_id=user_id,
            obs_id=obs_id, actor_user_id=user_id, occurred_at=now,
        )
        profiles.set_privileges(
            tenant_id=tenant, profile_id=project_profile.profile_id,
            privileges={"add_edit_delete_wbs_except_costs_financials"},
            expected_revision=1, actor_user_id=user_id, occurred_at=now,
        )
        policy = PostgresSecurityProfileAuthorizationPolicy(
            connection, RoleBasedAuthorizationPolicy(default_role_permissions())
        )
        context = AuthorizationContext(tenant, project_id, user_id, frozenset({"project_admin"}))
        assert policy.is_allowed(context, Permission.PROJECT_READ)
        assert policy.is_allowed_for_wbs(
            context, Permission.PROJECT_READ, f"eps-wbs-override-{suffix}"
        )
        assert not policy.is_allowed_for_wbs(
            context, Permission.PROJECT_WRITE, f"eps-wbs-override-{suffix}"
        )
        assert policy.is_allowed_for_wbs(
            context, Permission.P6_WBS_ADMIN, f"eps-wbs-{suffix}"
        )
        assert not policy.is_allowed_for_wbs(
            context, Permission.P6_ACTIVITY_ADMIN, f"eps-wbs-{suffix}"
        )
        profiles.set_privileges(
            tenant_id=tenant, profile_id=project_profile.profile_id,
            privileges={
                "add_edit_delete_wbs_except_costs_financials",
                "add_edit_activities_except_relationships",
            },
            expected_revision=2, actor_user_id=user_id, occurred_at=now,
        )
        assert policy.is_allowed_for_wbs(
            context, Permission.P6_ACTIVITY_ADMIN, f"eps-wbs-{suffix}"
        )
        assert not policy.is_allowed_for_wbs(
            context, Permission.P6_ACTIVITY_ADMIN, f"eps-wbs-override-{suffix}"
        )
        wbs_api = P6WBSMasterAPI(
            PostgresWBSMasterRepository(connection), policy,
            responsibility_repository=eps,
        )
        wbs_scope = BackendScope(tenant, project_id, 0)
        assert wbs_api.get_responsible_obs(
            wbs_scope, f"eps-wbs-{suffix}", auth_context=context
        )["responsible_obs_id"] == obs_id
        visible_wbs = wbs_api.list(wbs_scope, auth_context=context)
        assert {item["wbs"]["wbs_id"] for item in visible_wbs} == {
            f"eps-wbs-{suffix}", f"eps-wbs-inherit-{suffix}",
            f"eps-wbs-override-{suffix}",
        }
        changed = wbs_api.assign_responsible_obs(
            wbs_scope, f"eps-wbs-{suffix}", obs_id,
            expected_revision=1, occurred_at=now, auth_context=context,
        )
        assert changed["revision"] == 2
        with pytest.raises(P6EPSError, match="P6_WBS_RESPONSIBILITY_REVISION_CONFLICT"):
            wbs_api.assign_responsible_obs(
                wbs_scope, f"eps-wbs-{suffix}", obs_id,
                expected_revision=1, occurred_at=now, auth_context=context,
            )
        audit_rows = connection.execute(
            "SELECT before_state,after_state FROM p6_wbs_obs_responsibility_audit "
            "WHERE tenant_id=%s AND project_id=%s AND wbs_id=%s",
            (tenant,project_id,f"eps-wbs-{suffix}"),
        ).fetchall()
        assert len(audit_rows) == 2
        assert audit_rows[0][0] is None
        assert audit_rows[1][0]["revision"] == 1
        connection.execute("SAVEPOINT before_wbs_audit_delete")
        with pytest.raises(Exception, match="P6_WBS_OBS_AUDIT_APPEND_ONLY"):
            connection.execute(
                "DELETE FROM p6_wbs_obs_responsibility_audit "
                "WHERE tenant_id=%s AND project_id=%s AND wbs_id=%s",
                (tenant,project_id,f"eps-wbs-{suffix}"),
            )
        connection.execute("ROLLBACK TO SAVEPOINT before_wbs_audit_delete")

        # Re-parenting an EPS node below its descendant must fail atomically.
        eps = PostgresP6EPSRepository(connection)
        with pytest.raises(P6EPSError, match="P6_EPS_HIERARCHY_CYCLE"):
            eps.save_node(
                P6EPSNode(tenant, root_id, "Root EPS", parent_eps_id=child_id,
                          responsible_obs_id=obs_id),
                actor_user_id=user_id, occurred_at=now, expected_revision=1,
            )
        assert policy.is_allowed(context, Permission.PROJECT_READ)
        connection.rollback()



def test_wbs_linked_issue_and_expense_apis_enforce_postgres_obs_responsibility():
    suffix = uuid.uuid4().hex
    tenant = f"wbs-linked-api-{suffix}"
    user_id = f"wbs-linked-user-{suffix}"
    project_id = f"wbs-linked-project-{suffix}"
    project_obs = f"wbs-linked-project-obs-{suffix}"
    restricted_obs = f"wbs-linked-restricted-obs-{suffix}"
    root_wbs = f"wbs-linked-root-{suffix}"
    restricted_wbs = f"wbs-linked-restricted-{suffix}"
    now = datetime.now(timezone.utc)
    occurred_at = now.isoformat()

    with _connect() as connection:
        identity = PostgresIdentityStore(connection)
        identity.initialize()
        initialize_project_lifecycle_schema(connection)
        obs_repository = PostgresP6OBSRepository(connection)
        obs_repository.initialize()
        PostgresWBSMasterRepository(connection).initialize()
        eps_repository = PostgresP6EPSRepository(connection)
        eps_repository.initialize()
        initialize_security_profile_schema(connection)
        identity.upsert_user(_identity_user(user_id, tenant, "planner"))
        obs_repository.upsert(P6OBSNode(tenant, project_obs, name="Project Responsible OBS"))
        obs_repository.upsert(P6OBSNode(tenant, restricted_obs, name="Restricted WBS OBS"))
        PostgresProjectRepository(connection).create_for_user(
            tenant, user_id, project_id, "WBS linked API project", obs_id=project_obs
        )
        connection.execute(
            "INSERT INTO wbs_master "
            "(tenant_id,project_id,project_revision,wbs_id,parent_kind,parent_wbs_id,"
            "code,name,sequence_number,record_revision,status,percent_complete_technique) "
            "VALUES (%s,%s,0,%s,'project',NULL,'ROOT','Root WBS',0,1,'active','activities')",
            (tenant, project_id, root_wbs),
        )
        connection.execute(
            "INSERT INTO wbs_master "
            "(tenant_id,project_id,project_revision,wbs_id,parent_kind,parent_wbs_id,"
            "code,name,sequence_number,record_revision,status,percent_complete_technique) "
            "VALUES (%s,%s,0,%s,'wbs',%s,'RESTRICTED','Restricted WBS',1,1,'active','activities')",
            (tenant, project_id, restricted_wbs, root_wbs),
        )
        eps_repository.assign_wbs_responsibility(
            tenant, project_id, restricted_wbs, restricted_obs,
            actor_user_id=user_id, occurred_at=now,
        )

        profiles = PostgresSecurityProfileRepository(connection)
        global_profile = profiles.create_profile(
            tenant_id=tenant, profile_id=f"global-{suffix}", name="WBS API Global",
            scope="global", actor_user_id=user_id, occurred_at=now,
        )
        project_profile = profiles.create_profile(
            tenant_id=tenant, profile_id=f"project-{suffix}", name="WBS API Project",
            scope="project", actor_user_id=user_id, occurred_at=now,
        )
        profiles.set_privileges(
            tenant_id=tenant, profile_id=project_profile.profile_id,
            privileges={
                "add_edit_delete_issues_issue_thresholds",
                "add_edit_delete_expenses",
                "add_edit_activities_except_relationships",
                "add_edit_delete_activity_relationships",
            },
            expected_revision=1, actor_user_id=user_id, occurred_at=now,
        )
        profiles.assign(
            tenant_id=tenant, profile_id=global_profile.profile_id, user_id=user_id,
            actor_user_id=user_id, occurred_at=now,
        )
        profiles.assign(
            tenant_id=tenant, profile_id=project_profile.profile_id, user_id=user_id,
            obs_id=project_obs, actor_user_id=user_id, occurred_at=now,
        )
        connection.commit()

    issue_connection = sqlite3.connect(":memory:")
    expense_connection = sqlite3.connect(":memory:")
    with _connect() as connection:
        policy = PostgresSecurityProfileAuthorizationPolicy(
            connection, RoleBasedAuthorizationPolicy(default_role_permissions())
        )
        context = AuthorizationContext(tenant, project_id, user_id, frozenset({"planner"}))
        scope = BackendScope(tenant, project_id, 0)
        issue_repository = SQLiteP6IssueRepository(issue_connection)
        issue_api = P6IssueAPI(issue_repository, policy)
        visible_issue = P6Issue(
            scope, f"visible-{suffix}", "Visible WBS issue", "", "scope", "open",
            "normal", user_id, date_identified="2026-11-15", wbs_id=root_wbs,
        )
        restricted_issue = P6Issue(
            scope, f"restricted-{suffix}", "Restricted WBS issue", "", "scope", "open",
            "normal", user_id, date_identified="2026-11-15", wbs_id=restricted_wbs,
        )
        issue_api.create(visible_issue, auth_context=context, occurred_at=occurred_at)
        issue_repository.create(restricted_issue, actor_id=user_id, occurred_at=occurred_at)

        # The project OBS assignment keeps read-only visibility on a WBS
        # overridden to another OBS, but cannot authorize issue writes there.
        assert issue_api.get(scope, restricted_issue.issue_id, auth_context=context) is not None
        assert {item["issue"]["issue_id"] for item in issue_api.list(scope, auth_context=context)} == {
            visible_issue.issue_id, restricted_issue.issue_id,
        }
        with pytest.raises(AuthorizationError, match="authorization denied"):
            issue_api.create(
                P6Issue(
                    scope, f"denied-{suffix}", "Denied WBS issue", "", "scope", "open",
                    "normal", user_id, date_identified="2026-11-15", wbs_id=restricted_wbs,
                ),
                auth_context=context, occurred_at=occurred_at,
            )
        with pytest.raises(AuthorizationError, match="authorization denied"):
            issue_api.update(
                restricted_issue, expected_revision=1, auth_context=context,
                occurred_at=occurred_at,
            )
        with pytest.raises(AuthorizationError, match="authorization denied"):
            issue_api.delete(
                scope, restricted_issue.issue_id, expected_revision=1,
                auth_context=context, occurred_at=occurred_at,
            )
        with pytest.raises(AuthorizationError, match="authorization denied"):
            issue_api.add_comment(
                scope, restricted_issue.issue_id, comment="not allowed",
                expected_revision=1, auth_context=context, occurred_at=occurred_at,
            )

        expense_repository = SQLiteP6ExpenseRepository(expense_connection)
        expense_api = P6ExpenseAPI(
            P6ExpenseApplicationService(
                expense_repository, SQLiteTransactionManager(expense_connection)
            ),
            policy,
        )
        visible_expense = P6Expense(
            scope, f"visible-expense-{suffix}", "Visible WBS expense", "SITE",
            wbs_id=root_wbs, planned_cost=Decimal("10.00"),
        )
        restricted_expense = P6Expense(
            scope, f"restricted-expense-{suffix}", "Restricted WBS expense", "SITE",
            wbs_id=restricted_wbs, planned_cost=Decimal("20.00"),
        )
        expense_api.create(visible_expense, auth_context=context)
        expense_repository.upsert(restricted_expense)
        assert expense_api.get(
            scope, restricted_expense.expense_id, auth_context=context
        ) is not None
        assert {item["expense"]["expense_id"] for item in expense_api.list(
            scope, auth_context=context
        )} == {visible_expense.expense_id, restricted_expense.expense_id}
        with pytest.raises(AuthorizationError, match="authorization denied"):
            expense_api.create(
                P6Expense(
                    scope, f"denied-expense-{suffix}", "Denied WBS expense", "SITE",
                    wbs_id=restricted_wbs, planned_cost=Decimal("30.00"),
                ),
                auth_context=context,
            )

        # Use the same PostgreSQL WBS source as the authorization policy;
        # a separate SQLite activity store cannot resolve these WBS identifiers.
        activity_repository = PostgresActivityMasterRepository(connection)
        activity_repository.initialize()
        activity_api = P6ActivityMasterAPI(activity_repository, policy)
        visible_a = ActivityMaster(
            scope, f"visible-a-{suffix}", Decimal("1"), DurationUnit.WORKING_DAY,
            name="Visible A", wbs_id=root_wbs,
        )
        visible_b = ActivityMaster(
            scope, f"visible-b-{suffix}", Decimal("1"), DurationUnit.WORKING_DAY,
            name="Visible B", wbs_id=root_wbs,
        )
        restricted_activity = ActivityMaster(
            scope, f"restricted-activity-{suffix}", Decimal("1"), DurationUnit.WORKING_DAY,
            name="Restricted Activity", wbs_id=restricted_wbs,
        )
        activity_api.create(visible_a, auth_context=context)
        activity_api.create(visible_b, auth_context=context)
        activity_repository.save(restricted_activity, expected_revision=0)
        with pytest.raises(AuthorizationError, match="p6.activity.admin"):
            activity_api.update(
                ActivityMaster(
                    scope, restricted_activity.activity_id, Decimal("1"), DurationUnit.WORKING_DAY,
                    record_revision=1, name="Unauthorized edit", wbs_id=restricted_wbs,
                ),
                expected_revision=1, auth_context=context,
            )
        with pytest.raises(AuthorizationError, match="p6.activity.admin"):
            activity_api.update(
                ActivityMaster(
                    scope, visible_a.activity_id, Decimal("1"), DurationUnit.WORKING_DAY,
                    record_revision=1, name="Move out of authorized WBS", wbs_id=restricted_wbs,
                ),
                expected_revision=1, auth_context=context,
            )
        with pytest.raises(AuthorizationError, match="p6.activity.admin"):
            activity_api.update(
                ActivityMaster(
                    scope, restricted_activity.activity_id, Decimal("1"), DurationUnit.WORKING_DAY,
                    record_revision=1, name="Move into authorized WBS", wbs_id=root_wbs,
                ),
                expected_revision=1, auth_context=context,
            )

        relationship_connection = sqlite3.connect(":memory:")
        relationship_repository = SQLiteRelationshipMasterRepository(relationship_connection)
        relationship_api = P6RelationshipAPI(
            relationship_repository, policy, activity_repository,
        )
        visible_relationship = RelationshipMaster(
            scope, f"visible-rel-{suffix}", visible_a.activity_id, visible_b.activity_id,
            RelationshipType.FS,
        )
        relationship_api.create(visible_relationship, auth_context=context)
        restricted_relationship = RelationshipMaster(
            scope, f"restricted-rel-{suffix}", visible_a.activity_id,
            restricted_activity.activity_id, RelationshipType.FS,
        )
        with pytest.raises(AuthorizationError, match="p6.activity.relationship.admin"):
            relationship_api.create(restricted_relationship, auth_context=context)
        relationship_repository.save(restricted_relationship, expected_revision=0)
        with pytest.raises(AuthorizationError, match="p6.activity.relationship.admin"):
            relationship_api.delete(
                scope, restricted_relationship.relationship_id, expected_revision=1,
                auth_context=context,
            )
        with pytest.raises(AuthorizationError, match="p6.activity.relationship.admin"):
            relationship_api.update(
                RelationshipMaster(
                    scope, visible_relationship.relationship_id, visible_a.activity_id,
                    restricted_activity.activity_id, RelationshipType.FS, record_revision=1,
                ),
                expected_revision=1, auth_context=context,
            )
        connection.rollback()
    issue_connection.close()
    expense_connection.close()
    relationship_connection.close()


def test_postgres_project_profile_default_switch_deactivation_and_tenant_isolation():
    suffix = uuid.uuid4().hex
    tenant = f"profile-default-{suffix}"
    user_id = f"profile-default-user-{suffix}"
    obs_id = f"profile-default-obs-{suffix}"
    now = datetime.now(timezone.utc)

    with _connect() as connection:
        identity = PostgresIdentityStore(connection)
        identity.initialize()
        initialize_project_lifecycle_schema(connection)
        PostgresP6OBSRepository(connection).initialize()
        initialize_security_profile_schema(connection)
        identity.upsert_user(_identity_user(user_id, tenant))
        PostgresP6OBSRepository(connection).upsert(
            P6OBSNode(tenant, obs_id, name="Default Profile OBS")
        )
        profiles = PostgresSecurityProfileRepository(connection)

        global_profile = profiles.create_profile(
            tenant_id=tenant, profile_id=f"default-global-{suffix}", name="Default Global",
            scope="global", actor_user_id=user_id, occurred_at=now,
        )
        first = profiles.create_profile(
            tenant_id=tenant, profile_id=f"default-project-a-{suffix}", name="Default Project A",
            scope="project", description="First project profile",
            actor_user_id=user_id, occurred_at=now,
        )
        second = profiles.create_profile(
            tenant_id=tenant, profile_id=f"default-project-b-{suffix}", name="Default Project B",
            scope="project", description="Second project profile",
            actor_user_id=user_id, occurred_at=now,
        )

        first = profiles.set_default(
            tenant_id=tenant, profile_id=first.profile_id, is_default=True,
            expected_revision=1, actor_user_id=user_id, occurred_at=now,
        )
        assert first.is_default and first.revision == 2
        second = profiles.set_default(
            tenant_id=tenant, profile_id=second.profile_id, is_default=True,
            expected_revision=1, actor_user_id=user_id, occurred_at=now,
        )
        assert second.is_default and second.revision == 2
        first_after = profiles.get_profile(tenant, first.profile_id)
        assert not first_after.is_default and first_after.revision == 3
        assert profiles.get_default_project_profile(tenant).profile_id == second.profile_id

        profiles.assign(
            tenant_id=tenant, profile_id=global_profile.profile_id, user_id=user_id,
            actor_user_id=user_id, occurred_at=now,
        )
        profiles.assign(
            tenant_id=tenant, profile_id=second.profile_id, user_id=user_id,
            obs_id=obs_id, actor_user_id=user_id, occurred_at=now,
        )
        with pytest.raises(SecurityProfileError, match="SECURITY_PROFILE_ASSIGNED_CANNOT_DELETE"):
            profiles.delete_profile(
                tenant_id=tenant, profile_id=second.profile_id, expected_revision=2,
                actor_user_id=user_id, occurred_at=now,
            )

        second = profiles.set_active(
            tenant_id=tenant, profile_id=second.profile_id, active=False,
            expected_revision=2, actor_user_id=user_id, occurred_at=now,
        )
        assert not second.active and not second.is_default
        assert profiles.get_default_project_profile(tenant) is None
        global_profile = profiles.set_default(
            tenant_id=tenant, profile_id=global_profile.profile_id, is_default=True,
            expected_revision=1, actor_user_id=user_id, occurred_at=now,
        )
        assert global_profile.is_default
        assert profiles.get_default_global_profile(tenant).profile_id == global_profile.profile_id
        with pytest.raises(SecurityProfileError, match="SECURITY_PROFILE_NOT_FOUND"):
            profiles.get_profile(f"{tenant}-other", first.profile_id)

        audit = connection.execute(
            "SELECT action FROM p6_security_profile_audit "
            "WHERE tenant_id=%s AND profile_id=%s ORDER BY occurred_at,audit_id",
            (tenant, second.profile_id),
        ).fetchall()
        assert "profile_default_changed" in {str(row[0]) for row in audit}
        assert "profile_status_changed" in {str(row[0]) for row in audit}
        connection.rollback()


class _PostgresTransactionManager:
    def __init__(self, connection):
        self.connection = connection

    @contextmanager
    def transaction(self):
        with self.connection.transaction():
            yield


def test_postgres_project_profiles_enforce_activity_assignment_wbs_and_period_privileges():
    suffix = uuid.uuid4().hex
    tenant = f"resource-profile-{suffix}"
    user_id = f"resource-profile-user-{suffix}"
    unassigned_user_id = f"resource-profile-unassigned-{suffix}"
    restricted_user_id = f"resource-profile-restricted-{suffix}"
    project_id = f"resource-profile-project-{suffix}"
    project_obs = f"resource-profile-project-obs-{suffix}"
    restricted_obs = f"resource-profile-restricted-obs-{suffix}"
    root_wbs = f"resource-profile-root-{suffix}"
    restricted_wbs = f"resource-profile-wbs-{suffix}"
    root_activity = f"resource-profile-act-root-{suffix}"
    restricted_activity = f"resource-profile-act-restricted-{suffix}"
    now = datetime.now(timezone.utc)

    with _connect() as connection:
        identity = PostgresIdentityStore(connection)
        identity.initialize()
        initialize_project_lifecycle_schema(connection)
        obs = PostgresP6OBSRepository(connection)
        obs.initialize()
        eps = PostgresP6EPSRepository(connection)
        eps.initialize()
        wbs = PostgresWBSMasterRepository(connection)
        wbs.initialize()
        # Activity initialization performs idempotent WBS schema migrations;
        # run it before this test creates rows that fire deferred WBS triggers.
        activities = PostgresActivityMasterRepository(connection)
        activities.initialize()
        initialize_security_profile_schema(connection)

        identity.upsert_user(_identity_user(user_id, tenant, "planner"))
        identity.upsert_user(_identity_user(unassigned_user_id, tenant, "planner"))
        identity.upsert_user(_identity_user(restricted_user_id, tenant, "planner"))
        obs.upsert(P6OBSNode(tenant, project_obs, name="Project Responsible"))
        obs.upsert(P6OBSNode(tenant, restricted_obs, name="Restricted WBS Responsible"))
        PostgresProjectRepository(connection).create_for_user(
            tenant, user_id, project_id, "Resource Security Project", obs_id=project_obs
        )
        connection.execute(
            "INSERT INTO wbs_master "
            "(tenant_id,project_id,project_revision,wbs_id,parent_kind,parent_wbs_id,"
            "code,name,sequence_number,record_revision,status,percent_complete_technique) "
            "VALUES (%s,%s,0,%s,'project',NULL,'ROOT','Root WBS',0,1,'active','activities')",
            (tenant, project_id, root_wbs),
        )
        connection.execute(
            "INSERT INTO wbs_master "
            "(tenant_id,project_id,project_revision,wbs_id,parent_kind,parent_wbs_id,"
            "code,name,sequence_number,record_revision,status,percent_complete_technique) "
            "VALUES (%s,%s,0,%s,'wbs',%s,'RESTRICTED','Restricted WBS',1,1,'active','activities')",
            (tenant, project_id, restricted_wbs, root_wbs),
        )
        eps.assign_wbs_responsibility(
            tenant, project_id, restricted_wbs, restricted_obs,
            actor_user_id=user_id, occurred_at=now,
        )

        scope = BackendScope(tenant, project_id, 0)
        activities.save(ActivityMaster(
            scope, root_activity, Decimal("1"), DurationUnit.WORKING_DAY,
            name="Root WBS activity", wbs_id=root_wbs,
        ))
        activities.save(ActivityMaster(
            scope, restricted_activity, Decimal("1"), DurationUnit.WORKING_DAY,
            name="Restricted WBS activity", wbs_id=restricted_wbs,
        ))

        profiles = PostgresSecurityProfileRepository(connection)
        global_profile = profiles.create_profile(
            tenant_id=tenant, profile_id=f"resource-global-{suffix}",
            name="Resource Global", scope="global",
            actor_user_id=user_id, occurred_at=now,
        )
        project_profile = profiles.create_profile(
            tenant_id=tenant, profile_id=f"resource-project-{suffix}",
            name="Resource Activity Editor", scope="project",
            actor_user_id=user_id, occurred_at=now,
        )
        profiles.set_privileges(
            tenant_id=tenant, profile_id=project_profile.profile_id,
            privileges={"add_edit_activities_except_relationships"},
            expected_revision=1, actor_user_id=user_id, occurred_at=now,
        )
        for target_user in (user_id, unassigned_user_id, restricted_user_id):
            profiles.assign(
                tenant_id=tenant, profile_id=global_profile.profile_id,
                user_id=target_user, actor_user_id=user_id, occurred_at=now,
            )
        profiles.assign(
            tenant_id=tenant, profile_id=project_profile.profile_id,
            user_id=user_id, obs_id=project_obs,
            actor_user_id=user_id, occurred_at=now,
        )
        profiles.assign(
            tenant_id=tenant, profile_id=project_profile.profile_id,
            user_id=restricted_user_id, obs_id=restricted_obs,
            actor_user_id=user_id, occurred_at=now,
        )
        connection.commit()

        policy = PostgresSecurityProfileAuthorizationPolicy(
            connection, RoleBasedAuthorizationPolicy(default_role_permissions())
        )
        assignment_repository = PostgresP6ResourceAssignmentRepository(connection)
        assignment_repository.initialize()
        period_repository = PostgresP6ResourceAssignmentPeriodRepository(connection)
        period_repository.initialize()
        transactions = _PostgresTransactionManager(connection)
        write_api = P6ResourceWriteAPI(
            P6ResourceAssignmentPeriodApplicationService(period_repository, transactions),
            policy,
            assignment_service=P6ResourceAssignmentApplicationService(
                assignment_repository, transactions
            ),
            activity_repository=activities,
        )
        context = AuthorizationContext(
            tenant, project_id, user_id, frozenset({"planner"})
        )
        unassigned_context = AuthorizationContext(
            tenant, project_id, unassigned_user_id, frozenset({"planner"})
        )
        restricted_context = AuthorizationContext(
            tenant, project_id, restricted_user_id, frozenset({"planner"})
        )

        assert policy.is_allowed(context, Permission.P6_ACTIVITY_ADMIN)
        assert not policy.is_allowed(context, Permission.P6_EDIT_PERIOD_PERFORMANCE)
        assert not policy.is_allowed(
            unassigned_context, Permission.P6_ACTIVITY_ADMIN
        ), "a planner/team role without an OBS-assigned Project Profile must not grant project writes"

        root_assignment = P6ResourceAssignment(
            scope, f"resource-assignment-root-{suffix}", root_activity, "resource-1"
        )
        restricted_assignment = P6ResourceAssignment(
            scope, f"resource-assignment-restricted-{suffix}",
            restricted_activity, "resource-1",
        )
        write_api.save_assignment(root_assignment, auth_context=context)
        with pytest.raises(AuthorizationError, match="RESOURCE_WRITE_NOT_AUTHORIZED"):
            write_api.save_assignment(restricted_assignment, auth_context=context)

        root_period = P6ResourceAssignmentPeriodValue(
            scope, root_assignment.assignment_id, root_activity, "resource-1",
            "2026-11-15", Decimal("4"), Decimal("40"),
        )
        with pytest.raises(AuthorizationError, match="RESOURCE_WRITE_NOT_AUTHORIZED"):
            write_api.save_assignment_period(root_period, auth_context=context)

        profiles.set_privileges(
            tenant_id=tenant, profile_id=project_profile.profile_id,
            privileges={
                "add_edit_activities_except_relationships",
                "edit_period_performance",
                "view_project_costs_financials",
            },
            expected_revision=2, actor_user_id=user_id, occurred_at=now,
        )
        assert policy.is_allowed(context, Permission.P6_EDIT_PERIOD_PERFORMANCE)
        assert policy.is_allowed_for_wbs(
            context, Permission.P6_EDIT_PERIOD_PERFORMANCE, root_wbs
        )
        assert not policy.is_allowed_for_wbs(
            context, Permission.P6_EDIT_PERIOD_PERFORMANCE, restricted_wbs
        )
        write_api.save_assignment_period(root_period, auth_context=context)
        restricted_period = P6ResourceAssignmentPeriodValue(
            scope, restricted_assignment.assignment_id, restricted_activity,
            "resource-1", "2026-11-15", Decimal("2"), Decimal("20"),
        )
        with pytest.raises(AuthorizationError, match="RESOURCE_WRITE_NOT_AUTHORIZED"):
            write_api.save_assignment_period(
                restricted_period, auth_context=context
            )
        write_api.save_assignment_period(
            restricted_period, auth_context=restricted_context
        )

        # A user assigned to the restricted OBS can write that WBS only, not
        # the project OBS WBS; this is not inferred from team membership.
        write_api.save_assignment(restricted_assignment, auth_context=restricted_context)
        assert policy.is_allowed_for_wbs(
            restricted_context, Permission.P6_ACTIVITY_ADMIN, restricted_wbs
        )
        assert not policy.is_allowed_for_wbs(
            restricted_context, Permission.P6_ACTIVITY_ADMIN, root_wbs
        )
        with pytest.raises(AuthorizationError, match="RESOURCE_WRITE_NOT_AUTHORIZED"):
            write_api.save_assignment(root_assignment, auth_context=restricted_context)

        foreign_context = AuthorizationContext(
            f"{tenant}-foreign", project_id, user_id, frozenset({"planner"})
        )
        assert not policy.is_allowed(foreign_context, Permission.P6_ACTIVITY_ADMIN)
        connection.rollback()




def test_postgres_project_profiles_gate_risk_and_threshold_services_by_v26_privileges():
    """Exercise real project API services against persisted PostgreSQL profile grants."""
    suffix = uuid.uuid4().hex
    tenant = f"risk-threshold-{suffix}"
    other_tenant = f"risk-threshold-other-{suffix}"
    user_id = f"risk-threshold-user-{suffix}"
    project_id = f"risk-threshold-project-{suffix}"
    obs_id = f"risk-threshold-obs-{suffix}"
    now = datetime.now(timezone.utc)

    with _connect() as connection:
        identity = PostgresIdentityStore(connection)
        identity.initialize()
        initialize_project_lifecycle_schema(connection)
        PostgresP6OBSRepository(connection).initialize()
        initialize_security_profile_schema(connection)
        identity.upsert_user(_identity_user(user_id, tenant))
        PostgresP6OBSRepository(connection).upsert(
            P6OBSNode(tenant, obs_id, name="Risk and threshold OBS")
        )
        PostgresProjectRepository(connection).create_for_user(
            tenant, user_id, project_id, "Risk and threshold project", obs_id=obs_id
        )

    with _connect() as connection:
        profiles = PostgresSecurityProfileRepository(connection)
        policy = PostgresSecurityProfileAuthorizationPolicy(
            connection, RoleBasedAuthorizationPolicy(default_role_permissions())
        )
        context = AuthorizationContext(tenant, project_id, user_id, frozenset({"planner"}))

        global_profile = profiles.create_profile(
            tenant_id=tenant, profile_id="risk-threshold-global", name="Risk Threshold Global",
            scope="global", actor_user_id=user_id, occurred_at=now,
        )
        profiles.assign(
            tenant_id=tenant, profile_id=global_profile.profile_id, user_id=user_id,
            actor_user_id=user_id, occurred_at=now,
        )
        project_profile = profiles.create_profile(
            tenant_id=tenant, profile_id="risk-threshold-project", name="Risk Threshold Project",
            scope="project", actor_user_id=user_id, occurred_at=now,
        )
        profiles.assign(
            tenant_id=tenant, profile_id=project_profile.profile_id, user_id=user_id,
            obs_id=obs_id, actor_user_id=user_id, occurred_at=now,
        )

        risk_connection = sqlite3.connect(":memory:")
        risk_store = SQLiteRiskStore(risk_connection)
        risk_store.initialize()
        risk_service = RiskApplicationService(
            risk_store, policy, SQLiteTransactionManager(risk_connection)
        )
        risk = Risk(
            tenant_id=tenant, project_id=project_id, risk_id="RK-1",
            title="Supplier lead-time exposure", description="",
            category="technical", status="open", probability=2, impact=3,
            response_strategy="mitigate", owner=user_id, date_identified=now.date().isoformat(),
        )
        with pytest.raises(RiskAuthorizationError, match="RISK_PERMISSION_DENIED"):
            risk_service.create_risk(
                risk, idempotency_key="risk-key", context=context,
                actor_id=user_id, occurred_at=now,
            )

        threshold_connection = sqlite3.connect(":memory:")
        threshold_store = SQLiteThresholdStore(threshold_connection)
        threshold_store.initialize()

        class ZeroMetric:
            def observe(self, **kwargs):
                return Decimal("0")

        threshold_service = ThresholdApplicationService(
            threshold_store, policy, SQLiteTransactionManager(threshold_connection),
            ZeroMetric(), lambda issue, *, context, occurred_at: issue.issue_id,
        )
        threshold = Threshold(
            tenant_id=tenant, project_id=project_id, threshold_id="TH-1",
            name="Open issue watch", monitoring_subject="quality",
            parameter="open_issue_count", upper_threshold=Decimal("5"),
            warning_level=Decimal("1"), issue_level=Decimal("3"),
            responsible_manager=user_id,
        )
        with pytest.raises(ThresholdAuthorizationError, match="THRESHOLD_PERMISSION_DENIED"):
            threshold_service.create_threshold(
                threshold, idempotency_key="threshold-key", context=context,
                actor_id=user_id, occurred_at=now,
            )

        project_privileges = {
            "add_edit_delete_risks",
            "add_edit_delete_issues_issue_thresholds",
        }
        profiles.set_privileges(
            tenant_id=tenant, profile_id=project_profile.profile_id,
            privileges=project_privileges, expected_revision=1,
            actor_user_id=user_id, occurred_at=now,
        )
        assert risk_service.create_risk(
            risk, idempotency_key="risk-key", context=context,
            actor_id=user_id, occurred_at=now,
        ).revision == 1
        assert threshold_service.create_threshold(
            threshold, idempotency_key="threshold-key", context=context,
            actor_id=user_id, occurred_at=now,
        ).revision == 1

        with pytest.raises(ThresholdAuthorizationError, match="THRESHOLD_PERMISSION_DENIED"):
            threshold_service.monitor(
                tenant_id=tenant, project_id=project_id, project_revision=1,
                threshold_id="TH-1", context=context, actor_id=user_id, occurred_at=now,
            )

        project_privileges.add("monitor_project_thresholds")
        profiles.set_privileges(
            tenant_id=tenant, profile_id=project_profile.profile_id,
            privileges=project_privileges, expected_revision=2,
            actor_user_id=user_id, occurred_at=now,
        )
        monitored = threshold_service.monitor(
            tenant_id=tenant, project_id=project_id, project_revision=1,
            threshold_id="TH-1", context=context, actor_id=user_id, occurred_at=now,
        )
        assert monitored.run.level == "normal"

        # Monitoring remains separate from threshold CRUD.
        profiles.set_privileges(
            tenant_id=tenant, profile_id=project_profile.profile_id,
            privileges={"add_edit_delete_risks", "monitor_project_thresholds"},
            expected_revision=3, actor_user_id=user_id, occurred_at=now,
        )
        monitored_again = threshold_service.monitor(
            tenant_id=tenant, project_id=project_id, project_revision=1,
            threshold_id="TH-1", context=context, actor_id=user_id, occurred_at=now,
        )
        assert monitored_again.run.level == "normal"
        with pytest.raises(ThresholdAuthorizationError, match="THRESHOLD_PERMISSION_DENIED"):
            threshold_service.update_threshold(
                Threshold(
                    tenant_id=tenant, project_id=project_id, threshold_id="TH-1",
                    name="Changed without issue/threshold grant", monitoring_subject="quality",
                    parameter="open_issue_count", upper_threshold=Decimal("6"),
                    warning_level=Decimal("1"), issue_level=Decimal("3"),
                    responsible_manager=user_id,
                ),
                expected_revision=1, context=context, actor_id=user_id, occurred_at=now,
            )
        risk_updated = risk_service.update_risk(
            Risk(
                tenant_id=tenant, project_id=project_id, risk_id="RK-1",
                title="Supplier lead-time exposure", description="",
                category="technical", status="mitigating", probability=2, impact=3,
                response_strategy="mitigate", owner=user_id, date_identified=now.date().isoformat(),
            ),
            expected_revision=1, context=context, actor_id=user_id, occurred_at=now,
        )
        assert risk_updated.revision == 2

        foreign_context = AuthorizationContext(
            other_tenant, project_id, user_id, frozenset({"planner"})
        )
        assert not policy.is_allowed(foreign_context, Permission.P6_RISK_ADMIN)
        assert not policy.is_allowed(foreign_context, Permission.P6_ISSUE_ADMIN)


def test_global_and_project_defaults_are_independent_and_protected_from_delete():
    tenant = f"security-defaults-{uuid.uuid4().hex}"
    actor = "security-defaults-test-admin"
    now = datetime.now(timezone.utc)

    with _connect() as connection:
        PostgresIdentityStore(connection).initialize()
        initialize_security_profile_schema(connection)
        profiles = PostgresSecurityProfileRepository(connection)

        global_a = profiles.create_profile(
            tenant_id=tenant, profile_id="global-a", name="Global A", scope="global",
            actor_user_id=actor, occurred_at=now,
        )
        global_b = profiles.create_profile(
            tenant_id=tenant, profile_id="global-b", name="Global B", scope="global",
            actor_user_id=actor, occurred_at=now,
        )
        project_a = profiles.create_profile(
            tenant_id=tenant, profile_id="project-a", name="Project A", scope="project",
            actor_user_id=actor, occurred_at=now,
        )
        project_b = profiles.create_profile(
            tenant_id=tenant, profile_id="project-b", name="Project B", scope="project",
            actor_user_id=actor, occurred_at=now,
        )

        global_a = profiles.set_default(
            tenant_id=tenant, profile_id=global_a.profile_id, is_default=True,
            expected_revision=global_a.revision, actor_user_id=actor, occurred_at=now,
        )
        project_a = profiles.set_default(
            tenant_id=tenant, profile_id=project_a.profile_id, is_default=True,
            expected_revision=project_a.revision, actor_user_id=actor, occurred_at=now,
        )
        assert profiles.get_default_global_profile(tenant).profile_id == "global-a"
        assert profiles.get_default_project_profile(tenant).profile_id == "project-a"

        global_b = profiles.set_default(
            tenant_id=tenant, profile_id=global_b.profile_id, is_default=True,
            expected_revision=global_b.revision, actor_user_id=actor, occurred_at=now,
        )
        project_b = profiles.set_default(
            tenant_id=tenant, profile_id=project_b.profile_id, is_default=True,
            expected_revision=project_b.revision, actor_user_id=actor, occurred_at=now,
        )

        assert profiles.get_default_global_profile(tenant).profile_id == "global-b"
        assert profiles.get_default_project_profile(tenant).profile_id == "project-b"
        assert profiles.get_profile(tenant, "global-a").revision == global_a.revision + 1
        assert profiles.get_profile(tenant, "project-a").revision == project_a.revision + 1
        assert profiles.get_profile(tenant, "global-a").is_default is False
        assert profiles.get_profile(tenant, "project-a").is_default is False
        assert global_b.is_default is True
        assert project_b.is_default is True

        default_events = connection.execute(
            "SELECT profile_id FROM p6_security_profile_audit "
            "WHERE tenant_id=%s AND action='profile_default_changed'",
            (tenant,),
        ).fetchall()
        assert sorted(str(row[0]) for row in default_events) == [
            "global-a", "global-a", "global-b",
            "project-a", "project-a", "project-b",
        ]

        with pytest.raises(SecurityProfileError, match="SECURITY_PROFILE_DEFAULT_CANNOT_DELETE"):
            profiles.delete_profile(
                tenant_id=tenant, profile_id="global-b", expected_revision=global_b.revision,
                actor_user_id=actor, occurred_at=now,
            )
        with pytest.raises(SecurityProfileError, match="SECURITY_PROFILE_DEFAULT_CANNOT_DELETE"):
            profiles.delete_profile(
                tenant_id=tenant, profile_id="project-b", expected_revision=project_b.revision,
                actor_user_id=actor, occurred_at=now,
            )

        connection.rollback()


def test_global_user_module_access_is_revisioned_and_shares_canonical_assignment():
    suffix = uuid.uuid4().hex
    tenant = f"global-user-access-{suffix}"
    user_id = f"global-user-access-user-{suffix}"
    now = datetime.now(timezone.utc)
    with _connect() as connection:
        identity = PostgresIdentityStore(connection)
        identity.initialize()
        initialize_security_profile_schema(connection)
        identity.upsert_user(_identity_user(user_id, tenant, "planner"))
        profiles = PostgresSecurityProfileRepository(connection)
        profile = profiles.create_profile(
            tenant_id=tenant, profile_id=f"global-access-profile-{suffix}",
            name="Global Access", scope="global",
            actor_user_id=user_id, occurred_at=now,
        )
        profiles.assign(
            tenant_id=tenant, profile_id=profile.profile_id, user_id=user_id,
            actor_user_id=user_id, occurred_at=now,
        )
        saved = profiles.set_global_user_access(
            tenant_id=tenant, user_id=user_id,
            module_access=("resources", "projects"),
            resource_access_mode="all", expected_revision=1,
            actor_user_id=user_id, occurred_at=now,
        )
        assert saved["revision"] == 2
        assert saved["module_access"] == ["projects", "resources"]
        assert saved["resource_access_mode"] == "all"
        loaded = profiles.get_global_user_access(tenant, user_id)
        assert loaded == saved
        assignment = profiles.list_assignments(tenant, profile.profile_id)[0]
        assert assignment["module_access"] == ["projects", "resources"]
        assert assignment["resource_access_mode"] == "all"
        with pytest.raises(SecurityProfileError, match="SECURITY_PROFILE_ASSIGNMENT_REVISION_CONFLICT"):
            profiles.set_global_user_access(
                tenant_id=tenant, user_id=user_id, module_access=("projects",),
                resource_access_mode="none", expected_revision=1,
                actor_user_id=user_id, occurred_at=now,
            )
        with pytest.raises(SecurityProfileError, match="SECURITY_PROFILE_CONTRIBUTOR_MODULE_EXCLUSIVE"):
            profiles.set_global_user_access(
                tenant_id=tenant, user_id=user_id,
                module_access=("contributor", "projects"),
                resource_access_mode="none", expected_revision=2,
                actor_user_id=user_id, occurred_at=now,
            )
        with pytest.raises(SecurityProfileError, match="SECURITY_PROFILE_GLOBAL_RESOURCE_HIERARCHY_REQUIRED"):
            profiles.set_global_user_access(
                tenant_id=tenant, user_id=user_id, module_access=("projects",),
                resource_access_mode="selected", resource_root_ids=("root-a",),
                expected_revision=2, actor_user_id=user_id, occurred_at=now,
            )
        audit = connection.execute(
            "SELECT action,before_state,after_state FROM p6_security_profile_audit "
            "WHERE tenant_id=%s AND profile_id=%s AND action='user_global_access_updated'",
            (tenant, profile.profile_id),
        ).fetchall()
        assert len(audit) == 1
        assert audit[0][2]["module_access"] == ["projects", "resources"]
        connection.rollback()


def test_global_default_profile_is_assigned_to_existing_and_new_users():
    suffix = uuid.uuid4().hex
    tenant = f"global-default-bootstrap-{suffix}"
    admin_id = f"global-default-admin-{suffix}"
    existing_id = f"global-default-existing-{suffix}"
    new_id = f"global-default-new-{suffix}"
    later_id = f"global-default-later-{suffix}"
    now = datetime.now(timezone.utc)
    with _connect() as connection:
        identity = PostgresIdentityStore(connection)
        identity.initialize()
        initialize_project_lifecycle_schema(connection)
        PostgresP6OBSRepository(connection).initialize()
        initialize_security_profile_schema(connection)
        identity.upsert_user(_identity_user(admin_id, tenant, "enterprise_admin"))
        identity.upsert_user(_identity_user(existing_id, tenant, "planner"))

        bootstrap_first_admin_superuser(
            connection, tenant_id=tenant, user_id=admin_id,
            supplied_token="bootstrap-secret-" + "x" * 40,
            configured_token="bootstrap-secret-" + "x" * 40,
            occurred_at=now,
        )
        profiles = PostgresSecurityProfileRepository(connection)
        default_profile = profiles.get_default_global_profile(tenant)
        assert default_profile.profile_id == "p6-no-global-privileges"
        assert default_profile.is_default is True
        existing_access = profiles.get_global_user_access(tenant, existing_id)
        assert existing_access["profile_id"] == "p6-no-global-privileges"
        assert existing_access["module_access"] == ["projects"]
        assert existing_access["resource_access_mode"] == "none"

        obs_id = f"global-default-obs-{suffix}"
        project_id = f"global-default-project-{suffix}"
        PostgresP6OBSRepository(connection).upsert(
            P6OBSNode(tenant, obs_id, name="Global Default OBS")
        )
        PostgresProjectRepository(connection).create_for_user(
            tenant, existing_id, project_id, "Global Default Project", obs_id=obs_id
        )
        assert profiles.get_default_project_profile(tenant).profile_id == "p6-default-project-readonly"
        project_profile = profiles.create_profile(
            tenant_id=tenant, profile_id=f"global-default-project-profile-{suffix}",
            name="Global Default Project Read", scope="project",
            actor_user_id=admin_id, occurred_at=now,
        )
        profiles.assign(
            tenant_id=tenant, profile_id=project_profile.profile_id, user_id=existing_id,
            obs_id=obs_id, actor_user_id=admin_id, occurred_at=now,
        )
        default_project_assignment = profiles.assign_default_project_profile(
            tenant_id=tenant, user_id=existing_id, obs_id=obs_id,
            expected_revision=1, actor_user_id=admin_id, occurred_at=now,
        )
        assert default_project_assignment == {
            "profile_id": "p6-default-project-readonly", "obs_id": obs_id, "revision": 2,
        }
        with pytest.raises(SecurityProfileError, match="SECURITY_PROFILE_ASSIGNMENT_REVISION_CONFLICT"):
            profiles.assign_default_project_profile(
                tenant_id=tenant, user_id=existing_id, obs_id=obs_id,
                expected_revision=1, actor_user_id=admin_id, occurred_at=now,
            )

        admin_access = profiles.get_global_user_access(tenant, admin_id)
        assert admin_access["profile_id"] == "p6-admin-superuser"
        assert set(admin_access["module_access"]) == {
            "projects", "portfolios", "resources", "enterprise_reports",
            "integration_api", "p6_analytics", "p6_professional",
            "team_member", "timesheet", "visualizer", "web_services",
        }
        assert admin_access["resource_access_mode"] == "all"

        # Module access is an additional gate, not a substitute for OBS/project
        # privileges. Removing Projects immediately denies project reads.
        context = AuthorizationContext(
            tenant_id=tenant, user_id=existing_id, project_id=project_id,
            roles=frozenset({"planner"}),
        )
        policy = PostgresSecurityProfileAuthorizationPolicy(
            connection, RoleBasedAuthorizationPolicy(default_role_permissions())
        )
        assert policy.is_allowed(context, Permission.PROJECT_READ)
        existing_access = profiles.set_global_user_access(
            tenant_id=tenant, user_id=existing_id, module_access=(),
            resource_access_mode="none", expected_revision=existing_access["revision"],
            actor_user_id=admin_id, occurred_at=now,
        )
        assert not policy.is_allowed(context, Permission.PROJECT_READ)
        existing_access = profiles.set_global_user_access(
            tenant_id=tenant, user_id=existing_id, module_access=("projects",),
            resource_access_mode="none", expected_revision=existing_access["revision"],
            actor_user_id=admin_id, occurred_at=now,
        )
        assert profiles.get_global_user_access(tenant, existing_id)["module_access"] == ["projects"]

        identity.upsert_user(_identity_user(new_id, tenant, "planner"))
        new_access = profiles.get_global_user_access(tenant, new_id)
        assert new_access["profile_id"] == "p6-no-global-privileges"
        assert new_access["revision"] == 1

        custom = profiles.create_profile(
            tenant_id=tenant, profile_id=f"later-default-{suffix}",
            name="Later Default", scope="global",
            actor_user_id=admin_id, occurred_at=now,
        )
        custom = profiles.set_default(
            tenant_id=tenant, profile_id=custom.profile_id, is_default=True,
            expected_revision=custom.revision, actor_user_id=admin_id, occurred_at=now,
        )
        assert custom.is_default is True
        identity.upsert_user(_identity_user(later_id, tenant, "planner"))
        later_access = profiles.get_global_user_access(tenant, later_id)
        assert later_access["profile_id"] == custom.profile_id
        assert profiles.get_global_user_access(tenant, existing_id)["profile_id"] == "p6-no-global-privileges"
        connection.rollback()
