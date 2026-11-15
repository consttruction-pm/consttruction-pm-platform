from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    Permission,
    RoleBasedAuthorizationPolicy,
    default_role_permissions,
)
from construction_pm.identity_session import (
    IdentityUser,
    PostgresIdentityStore,
    hash_password,
)
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
        initialize_security_profile_schema(connection)
        PostgresIdentityStore(connection).upsert_user(_identity_user(user_id, tenant))
        PostgresProjectRepository(connection).create_for_user(
            tenant, user_id, project_id, "Profile protected project"
        )
        connection.commit()

    with _connect() as connection:
        profiles = PostgresSecurityProfileRepository(connection)
        role_policy = RoleBasedAuthorizationPolicy(default_role_permissions())
        policy = PostgresSecurityProfileAuthorizationPolicy(connection, role_policy)
        context = AuthorizationContext(tenant, project_id, user_id, frozenset({"planner"}))

        # Compatibility window: no assigned profiles preserves existing role behavior.
        assert policy.is_allowed(context, Permission.PROJECT_WRITE)

        global_profile = profiles.create_profile(
            tenant_id=tenant, profile_id="global-limited", name="Global Limited",
            scope="global", actor_user_id=user_id, occurred_at=now,
        )
        global_profile = profiles.set_privileges(
            tenant_id=tenant, profile_id=global_profile.profile_id,
            privileges={Permission.PROJECT_READ.value, Permission.PROJECT_WRITE.value},
            expected_revision=1, actor_user_id=user_id, occurred_at=now,
        )
        project_profile = profiles.create_profile(
            tenant_id=tenant, profile_id="project-read-only", name="Project Read Only",
            scope="project", actor_user_id=user_id, occurred_at=now,
        )
        project_profile = profiles.set_privileges(
            tenant_id=tenant, profile_id=project_profile.profile_id,
            privileges={Permission.PROJECT_READ.value},
            expected_revision=1, actor_user_id=user_id, occurred_at=now,
        )

        profiles.assign(
            tenant_id=tenant, profile_id="global-limited", user_id=user_id,
            actor_user_id=user_id, occurred_at=now,
        )
        profiles.assign(
            tenant_id=tenant, profile_id="project-read-only", user_id=user_id,
            project_id=project_id, actor_user_id=user_id, occurred_at=now,
        )

        assert policy.is_allowed(context, Permission.PROJECT_READ)
        assert not policy.is_allowed(context, Permission.PROJECT_WRITE)
        assert not policy.is_allowed(context, Permission.PROJECT_ADMIN)

        # A profile grant can never exceed the legacy role's ceiling.
        assert not policy.is_allowed(context, Permission.FORM_APPROVE)

        # A profile in another tenant cannot affect this user's effective access.
        foreign = AuthorizationContext(other_tenant, project_id, user_id, frozenset({"planner"}))
        assert policy.is_allowed(foreign, Permission.PROJECT_WRITE)

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
        assert event[2]["privileges"] == [Permission.PROJECT_READ.value]

        with pytest.raises(Exception, match="P6_SECURITY_PROFILE_AUDIT_APPEND_ONLY"):
            connection.execute(
                "UPDATE p6_security_profile_audit SET action='tampered' "
                "WHERE tenant_id=%s AND profile_id=%s",
                (tenant, "project-read-only"),
            )
        connection.rollback()
