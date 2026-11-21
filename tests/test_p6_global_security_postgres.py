"""Live PostgreSQL coverage for the V26 global security profile lifecycle."""

import os
import uuid
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from construction_pm.identity_session import IdentityUser, PostgresIdentityStore, hash_password
from construction_pm.p6_global_security import (
    ADMIN_SUPERUSER,
    GlobalSecurityError,
    GlobalSecurityProfile,
    UserGlobalSecurity,
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

            admin_copy = repo.duplicate_profile(
                tenant, "p6-admin-superuser", new_profile_id="admin-copy",
                new_name="Admin Copy", actor_id="bootstrap", created_at=now,
            )
            # Built-in Admin Superuser semantics are implicit and are not
            # copied into a custom profile's explicit privilege grants.
            assert not admin_copy.built_in
            assert admin_copy.privileges == ()
        finally:
            connection.rollback()

def test_last_admin_assignment_can_be_reassigned_only_while_another_admin_remains():
    tenant = f"tenant-admin-guard-{uuid.uuid4()}"
    now = datetime.now(timezone.utc)
    first_admin = f"admin-one-{uuid.uuid4().hex}"
    second_admin = f"admin-two-{uuid.uuid4().hex}"

    with _connection() as connection:
        identity = PostgresIdentityStore(connection)
        identity.initialize()
        for user_id, email in (
            (first_admin, f"{first_admin}@example.test"),
            (second_admin, f"{second_admin}@example.test"),
        ):
            identity.upsert_user(
                IdentityUser(
                    user_id=user_id,
                    tenant_id=tenant,
                    email=email,
                    display_name=user_id,
                    roles=frozenset({"enterprise_admin"}),
                    password_hash=hash_password("integration-password"),
                )
            )

        repo = PostgresP6GlobalSecurityRepository(connection)
        repo.initialize()
        try:
            repo.ensure_builtin_profiles(
                tenant, provisioned_by="integration-bootstrap", created_at=now
            )
            target = GlobalSecurityProfile(
                tenant_id=tenant,
                profile_id="guard-target",
                name="Guard Target",
                privileges=(),
            )
            repo.create_profile(
                target, actor_id="integration-bootstrap", created_at=now
            )

            # The first administrator is established only by the controlled
            # database/bootstrap path; the public assignment API cannot mint
            # the initial recovery principal.
            for user_id in (first_admin, second_admin):
                connection.execute(
                    "INSERT INTO p6_user_global_security "
                    "(tenant_id,user_id,profile_id,module_access,resource_access_mode,"
                    "resource_root_ids,revision,updated_by,updated_at) "
                    "VALUES (%s,%s,'p6-admin-superuser','[]'::jsonb,'all','[]'::jsonb,"
                    "1,'integration-bootstrap',%s)",
                    (tenant, user_id, now),
                )

            reassigned = UserGlobalSecurity(
                tenant_id=tenant,
                user_id=first_admin,
                profile_id=target.profile_id,
                module_access=("projects",),
                resource_access_mode="none",
                resource_root_ids=(),
                revision=2,
                updated_by=second_admin,
                updated_at=now,
            )
            repo.assign_user_security(reassigned, expected_revision=1)
            assert repo.get_user_security(tenant, first_admin).profile_id == target.profile_id

            last_admin_reassignment = UserGlobalSecurity(
                tenant_id=tenant,
                user_id=second_admin,
                profile_id=target.profile_id,
                module_access=("projects",),
                resource_access_mode="none",
                resource_root_ids=(),
                revision=2,
                updated_by=first_admin,
                updated_at=now,
            )
            with pytest.raises(GlobalSecurityError, match="LAST_ADMIN_SUPERUSER_REQUIRED"):
                repo.assign_user_security(last_admin_reassignment, expected_revision=1)
            assert repo.get_user_security(tenant, second_admin).profile_id == "p6-admin-superuser"
        finally:
            connection.rollback()

