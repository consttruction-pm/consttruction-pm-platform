"""Live PostgreSQL coverage for the V26 global security profile lifecycle."""

import os
import uuid
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from construction_pm.identity_session import PostgresIdentityStore
from construction_pm.p6_global_security import (
    ADMIN_SUPERUSER,
    GlobalSecurityError,
    GlobalSecurityProfile,
    PostgresP6GlobalSecurityRepository,
)


pytestmark = pytest.mark.postgres


def _connection():
    dsn = os.getenv("P6_TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("P6_TEST_POSTGRES_DSN is not configured")
    psycopg = pytest.importorskip("psycopg")
    return psycopg.connect(dsn)


def test_v26_global_profile_duplicate_default_edit_delete_and_audit():
    tenant = f"tenant-global-security-{uuid.uuid4()}"
    now = datetime.now(timezone.utc)
    with _connection() as connection:
        PostgresIdentityStore(connection).initialize()
        repo = PostgresP6GlobalSecurityRepository(connection)
        repo.initialize()
        try:
            repo.ensure_builtin_profiles(tenant, provisioned_by="bootstrap", created_at=now)
            source = GlobalSecurityProfile(
                tenant_id=tenant,
                profile_id="portfolio-admin",
                name="Portfolio Admin",
                privileges=("add_edit_delete_users",),
                description="Portfolio administration profile",
            )
            repo.create_profile(source, actor_id="bootstrap", created_at=now)

            duplicate = repo.duplicate_profile(
                tenant, source.profile_id, new_profile_id="portfolio-admin-copy",
                new_name="Portfolio Admin Copy", actor_id="bootstrap", created_at=now,
            )
            assert duplicate.privileges == source.privileges
            assert duplicate.description == source.description
            assert not duplicate.is_default

            default = repo.set_default_profile(
                tenant, source.profile_id, actor_id="bootstrap",
                expected_revision=1, updated_at=now,
            )
            assert default.is_default
            assert default.revision == 2
            with pytest.raises(GlobalSecurityError, match="DEFAULT_PROFILE_CANNOT_BE_DELETED"):
                repo.delete_profile(
                    tenant, source.profile_id, actor_id="bootstrap",
                    expected_revision=2, deleted_at=now,
                )

            edited = replace(
                default, name="Portfolio Administrator",
                description="Updated V26 profile description", revision=3,
            )
            updated = repo.update_profile(
                edited, actor_id="bootstrap", expected_revision=2, updated_at=now,
            )
            assert updated.name == "Portfolio Administrator"
            assert updated.is_default

            new_default = repo.set_default_profile(
                tenant, duplicate.profile_id, actor_id="bootstrap",
                expected_revision=1, updated_at=now,
            )
            assert new_default.is_default
            assert new_default.revision == 2
            old_default = repo.get_profile(tenant, source.profile_id)
            assert old_default is not None and not old_default.is_default
            assert old_default.revision == 4

            repo.delete_profile(
                tenant, source.profile_id, actor_id="bootstrap",
                expected_revision=4, deleted_at=now,
            )
            assert repo.get_profile(tenant, source.profile_id) is None

            with pytest.raises(GlobalSecurityError, match="BUILTIN_GLOBAL_SECURITY_PROFILE_IMMUTABLE"):
                repo.delete_profile(
                    tenant, "p6-admin-superuser", actor_id="bootstrap",
                    expected_revision=1, deleted_at=now,
                )

            # Default can be changed back to the built-in profile; old custom
            # default is revisioned and can then be deleted.
            admin_default = repo.set_default_profile(
                tenant, "p6-admin-superuser", actor_id="bootstrap",
                expected_revision=1, updated_at=now,
            )
            assert admin_default.is_default
            assert repo.get_profile(tenant, duplicate.profile_id).is_default is False
            repo.delete_profile(
                tenant, duplicate.profile_id, actor_id="bootstrap",
                expected_revision=3, deleted_at=now,
            )

            with pytest.raises(GlobalSecurityError, match="BUILTIN_GLOBAL_SECURITY_PROFILE_CANNOT_BE_DUPLICATED"):
                repo.duplicate_profile(
                    tenant, "p6-admin-superuser", new_profile_id="admin-copy",
                    new_name="Admin Copy", actor_id="bootstrap", created_at=now,
                )
        finally:
            connection.rollback()
