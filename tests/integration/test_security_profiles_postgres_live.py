from __future__ import annotations

import json
import os
import uuid
from io import BytesIO
from types import SimpleNamespace
from datetime import datetime, timezone

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
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
from construction_pm.postgres_project_lifecycle import (
    PostgresProjectRepository,
    initialize_project_lifecycle_schema,
)
from construction_pm.security_profiles import (
    PostgresSecurityProfileAuthorizationPolicy,
    PostgresSecurityProfileRepository,
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

        # OBS responsibility inherits to descendant OBS nodes and their projects.
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


def _http_request(app, method: str, path: str, *, session_id: str, payload: dict | None = None):
    raw = b"" if payload is None else json.dumps(payload).encode("utf-8")
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": "",
        "CONTENT_LENGTH": str(len(raw)),
        "wsgi.input": BytesIO(raw),
        "HTTP_COOKIE": f"cp_session={session_id}",
    }
    captured = {}
    def start_response(status, headers):
        captured["status"] = status
    body = b"".join(app(environ, start_response))
    return int(str(captured["status"]).split(" ", 1)[0]), json.loads(body)


def test_security_profile_admin_http_api_is_tenant_and_role_guarded():
    suffix = uuid.uuid4().hex
    tenant = f"profile-http-{suffix}"
    admin_id = f"profile-admin-{suffix}"
    target_id = f"profile-target-{suffix}"
    project_id = f"profile-http-project-{suffix}"
    now = datetime.now(timezone.utc)

    with _connect() as connection:
        identity = PostgresIdentityStore(connection)
        identity.initialize()
        initialize_project_lifecycle_schema(connection)
        PostgresP6OBSRepository(connection).initialize()
        initialize_security_profile_schema(connection)
        identity.upsert_user(_identity_user(admin_id, tenant, "enterprise_admin"))
        identity.upsert_user(_identity_user(target_id, tenant, "planner"))
        PostgresP6OBSRepository(connection).upsert(P6OBSNode(tenant, f"obs-{suffix}", name="Profile HTTP OBS"))
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
            return None

    with _connect() as connection:
        service = EnterpriseOrganizationAccessService(
            PostgresEnterpriseOrganizationAccessRepository(connection),
            Sessions(),
            security_profiles=PostgresSecurityProfileRepository(connection),
        )
        app = EnterpriseOrganizationAccessHttpMiddleware(lambda environ, start: [], service)

        status, global_created = _http_request(
            app, "POST", "/api/enterprise/security-profiles", session_id="admin-session",
            payload={
                "contract_version": "cubi-p6-security-profile.v1",
                "profile_id": "http-global", "name": "HTTP Global", "scope": "global",
            },
        )
        assert status == 201, global_created
        status, global_assigned = _http_request(
            app, "PUT", "/api/enterprise/security-profiles/http-global/assignments",
            session_id="admin-session",
            payload={
                "contract_version": "cubi-p6-security-profile-assignment.v1",
                "user_id": target_id,
            },
        )
        assert status == 200 and global_assigned["revision"] == 1

        status, created = _http_request(
            app, "POST", "/api/enterprise/security-profiles", session_id="admin-session",
            payload={
                "contract_version": "cubi-p6-security-profile.v1",
                "profile_id": "http-project-reader", "name": "HTTP Project Reader", "scope": "project",
            },
        )
        assert status == 201, created
        assert created["profile"]["revision"] == 1

        status, changed = _http_request(
            app, "PATCH", "/api/enterprise/security-profiles/http-project-reader/privileges",
            session_id="admin-session",
            payload={
                "contract_version": "cubi-p6-security-profile-privileges.v1",
                "expected_revision": 1, "privileges": ["add_edit_activities_except_relationships", "delete_project_activity_codes", "schedule_projects"],
            },
        )
        assert status == 200, changed
        assert changed["profile"]["revision"] == 2

        status, assigned = _http_request(
            app, "PUT", "/api/enterprise/security-profiles/http-project-reader/assignments",
            session_id="admin-session",
            payload={
                "contract_version": "cubi-p6-security-profile-assignment.v1",
                "user_id": target_id, "obs_id": f"obs-{suffix}",
            },
        )
        assert status == 200 and assigned["revision"] == 1

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
        assert denied["code"] == "ENTERPRISE_ADMIN_REQUIRED"

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
        policy = PostgresSecurityProfileAuthorizationPolicy(
            connection, RoleBasedAuthorizationPolicy(default_role_permissions())
        )
        admin_context = AuthorizationContext(tenant, project_id, admin_id, frozenset({"enterprise_admin"}))
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
        with pytest.raises(SecurityProfileError, match="SECURITY_PROFILE_LAST_ADMIN_SUPERUSER_REQUIRED"):
            profiles.assign(
                tenant_id=tenant, profile_id="ordinary-global", user_id=admin_id,
                actor_user_id=admin_id, occurred_at=now, expected_revision=1,
            )
        connection.rollback()

