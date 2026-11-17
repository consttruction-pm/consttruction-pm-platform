"""PostgreSQL acceptance for V26 Global and Project profile defaults."""

import os
import uuid
from datetime import datetime, timezone

import pytest

from construction_pm.identity_session import PostgresIdentityStore
from construction_pm.security_profiles import (
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
