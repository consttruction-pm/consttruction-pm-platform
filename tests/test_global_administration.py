"""Global Administration: catalogue, gate, and live PostgreSQL behaviour.

The unit tests need no database. The live tests run only when
``CONSTRUCTION_PM_POSTGRES_DSN`` is set (CI skips them, the evidence run sets it).
"""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone

import pytest

from construction_pm.global_administration import (
    GLOBAL_ADMIN_ROLE,
    ROLE_CATALOG,
    GlobalAdministrationError,
    GlobalAdministrationService,
    PostgresGlobalAdministrationStore,
    role_catalog_payload,
    tokens_for,
)

CSRF = "cubisite-test-secret-0123456789abcdef"
LIVE = bool(os.getenv("CONSTRUCTION_PM_POSTGRES_DSN"))


def test_catalogue_has_the_eleven_required_roles() -> None:
    keys = [role.key for role in ROLE_CATALOG]
    assert len(keys) == 11
    assert len(set(keys)) == 11
    assert keys[0] == "global_admin"
    payload = role_catalog_payload()
    assert all(item["label_en"] and item["label_fa"] for item in payload)


def test_catalogue_reuses_existing_role_tokens() -> None:
    tokens = {role.token for role in ROLE_CATALOG}
    assert tokens <= {"global_admin", "project_admin", "planner", "viewer"}


def test_tokens_for_maps_labels_onto_policy_tokens() -> None:
    assert tokens_for(["enterprise_viewer"]) == frozenset({"viewer"})
    assert tokens_for(["engineering_planner"]) == frozenset({"planner"})
    assert tokens_for(["organization_admin"]) == frozenset({"project_admin"})
    assert tokens_for(["test_user"]) == frozenset({"viewer", "test_user"})
    assert tokens_for(["global_admin"]) == frozenset({"global_admin"})


def test_tokens_for_rejects_unknown_and_empty() -> None:
    with pytest.raises(GlobalAdministrationError) as exc:
        tokens_for(["owner_of_everything"])
    assert exc.value.code == "ROLE_NOT_IN_CATALOG"
    with pytest.raises(GlobalAdministrationError) as exc:
        tokens_for([])
    assert exc.value.code == "ROLES_REQUIRED"


class _NoSessionIdentity:
    def resolve(self, token: str):  # noqa: ANN001 - test double
        return None


def test_gate_requires_a_session() -> None:
    service = GlobalAdministrationService(store=None, identity=_NoSessionIdentity())  # type: ignore[arg-type]
    with pytest.raises(GlobalAdministrationError) as exc:
        service.actor("anything")
    assert exc.value.code == "SESSION_REQUIRED"


# ---------------------------------------------------------------- live tests

pytestmark_live = pytest.mark.skipif(not LIVE, reason="CONSTRUCTION_PM_POSTGRES_DSN is not configured")


def _connect():
    import psycopg

    return psycopg.connect(os.environ["CONSTRUCTION_PM_POSTGRES_DSN"], autocommit=False)


def _identity(connection):
    from construction_pm.identity_session import IdentityService, PostgresIdentityStore

    return IdentityService(PostgresIdentityStore(connection), csrf_secret=CSRF)


def _bootstrap(connection) -> None:
    from construction_pm.deployment.schema import initialize_production_schema

    initialize_production_schema(connection)
    connection.commit()


@pytestmark_live
def test_live_global_administration_flow() -> None:
    from construction_pm.identity_session import IdentityUser, hash_password

    suffix = secrets.token_hex(4)
    admin_email = f"admin-{suffix}@cubisite.test"
    admin_password = "Admin-" + secrets.token_urlsafe(12)
    admin = IdentityUser(
        user_id=f"usr-admin-{suffix}",
        tenant_id="platform-owner",
        email=admin_email,
        display_name="Product Owner",
        roles=frozenset({GLOBAL_ADMIN_ROLE}),
        password_hash=hash_password(admin_password),
    )

    with _connect() as connection:
        _bootstrap(connection)
        from construction_pm.identity_session import PostgresIdentityStore

        PostgresIdentityStore(connection).upsert_user(admin)
        connection.commit()
        identity = _identity(connection)
        issued = identity.login(admin_email, admin_password)
        connection.commit()
        service = GlobalAdministrationService(
            PostgresGlobalAdministrationStore(connection), identity
        )

        dashboard = service.dashboard(issued.token)
        assert dashboard["users_total"] >= 1
        assert dashboard["database"] == "connected"
        assert len(dashboard["role_catalog"]) == 11

        created = service.create_user(
            issued.token,
            {
                "email": f"viewer-{suffix}@cubisite.test",
                "tenant_id": f"test-{suffix}",
                "display_name": "Test Viewer",
                "roles": ["enterprise_viewer"],
                "is_test_user": True,
                "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
                "locale": "fa",
                "reason": "scenario: enterprise viewer",
            },
        )
        child = created["user"]
        assert child["is_test_user"] is True
        assert child["roles"] == ["viewer"]
        temp = created["temporary_password"]

        # The temporary password works once and the account is flagged.
        child_session = identity.login(child["email"], temp)
        connection.commit()
        assert child_session.tenant_id == f"test-{suffix}"

        # Every mutation is audited.
        actions = [entry["action"] for entry in service.audit(issued.token)["entries"]]
        assert "user.create" in actions

        # Locking blocks login even with the correct password.
        service.update_user(issued.token, child["user_id"], {"locked": True, "reason": "lock test"})
        connection.commit()
        with pytest.raises(Exception):
            identity.login(child["email"], temp)
        service.update_user(issued.token, child["user_id"], {"locked": False, "reason": "unlock test"})
        connection.commit()

        # Disabling blocks login too.
        service.update_user(issued.token, child["user_id"], {"active": False, "reason": "disable"})
        connection.commit()
        with pytest.raises(Exception):
            identity.login(child["email"], temp)
        service.update_user(issued.token, child["user_id"], {"active": True, "reason": "enable"})
        connection.commit()

        # Expiry is enforced by the identity service, not by the UI.
        service.update_user(
            issued.token,
            child["user_id"],
            {"expires_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()},
        )
        connection.commit()
        with pytest.raises(Exception):
            identity.login(child["email"], temp)
        service.update_user(issued.token, child["user_id"], {"expires_at": None, "reason": "reactivate window"})
        connection.commit()

        # Reset rotates the password, revokes sessions and forces a change.
        reset = service.reset_password(
            issued.token,
            child["user_id"],
            confirm_password=admin_password,
            reason="rotate",
        )
        connection.commit()
        assert reset["temporary_password"] != temp
        assert reset["must_change_password"] is True
        assert reset["sessions_revoked"] >= 1
        with pytest.raises(Exception):
            identity.login(child["email"], temp)
        child_session = identity.login(child["email"], reset["temporary_password"])
        connection.commit()

        # A non-administrator cannot reach the surface.
        with pytest.raises(GlobalAdministrationError) as exc:
            service.users(child_session.token)
        assert exc.value.code == "GLOBAL_ADMIN_REQUIRED"

        # Reauthentication is required for destructive operations.
        with pytest.raises(GlobalAdministrationError) as exc:
            service.revoke_sessions(issued.token, child["user_id"], confirm_password="wrong")
        assert exc.value.code == "REAUTHENTICATION_FAILED"
