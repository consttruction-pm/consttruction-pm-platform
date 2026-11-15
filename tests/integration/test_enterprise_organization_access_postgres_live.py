from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest

from construction_pm.enterprise_organization_access import (
    EnterpriseTeam,
    EnterpriseTeamMembership,
    OrganizationAccessError,
)
from construction_pm.enterprise_organization_access_repository import (
    PostgresEnterpriseOrganizationAccessRepository,
)
from construction_pm.identity_session import (
    IdentityUser, PostgresIdentityStore, StoredSession, token_hash,
)

DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="CONSTRUCTION_PM_POSTGRES_DSN is required")
NOW = datetime(2026, 11, 15, 17, 0, tzinfo=timezone.utc)


def _user(connection, tenant_id: str, suffix: str) -> str:
    user_id = f"org-access-{suffix}-{uuid.uuid4().hex}"
    PostgresIdentityStore(connection).upsert_user(
        IdentityUser(
            user_id=user_id,
            tenant_id=tenant_id,
            email=f"{user_id}@example.invalid",
            display_name=suffix,
            roles=frozenset(),
            password_hash="unused-integration-hash",
            active=True,
        )
    )
    return user_id


def test_postgres_team_membership_persists_and_revocation_is_immediate():
    psycopg = pytest.importorskip("psycopg")
    tenant = f"org-access-{uuid.uuid4().hex}"
    with psycopg.connect(DSN) as connection:
        identity = PostgresIdentityStore(connection)
        identity.initialize()
        owner_id = _user(connection, tenant, "owner")
        member_id = _user(connection, tenant, "member")
        other_tenant_user = _user(connection, tenant + "-other", "outsider")
        repository = PostgresEnterpriseOrganizationAccessRepository(connection)
        repository.initialize()
        team = EnterpriseTeam(
            tenant_id=tenant, team_id=f"team-{uuid.uuid4().hex}",
            name="Field delivery", owner_user_id=owner_id, status="active",
            revision=1, created_at=NOW,
        )
        repository.create_team(team, actor_id=owner_id)
        membership = EnterpriseTeamMembership(
            tenant_id=tenant, team_id=team.team_id, user_id=member_id,
            role="field_worker", status="active", scope_project_ids=("project-a",),
            revision=1, created_at=NOW,
        )
        repository.add_member(membership, actor_id=owner_id)
        with pytest.raises(OrganizationAccessError, match="TEAM_MEMBER_ACCOUNT_NOT_FOUND"):
            repository.add_member(
                EnterpriseTeamMembership(
                    tenant_id=tenant, team_id=team.team_id, user_id=other_tenant_user,
                    role="member", status="active", scope_project_ids=(), revision=1,
                    created_at=NOW,
                ),
                actor_id=owner_id,
            )
        connection.commit()

    with psycopg.connect(DSN) as connection:
        repository = PostgresEnterpriseOrganizationAccessRepository(connection)
        persisted = repository.get_membership(tenant, team.team_id, member_id)
        assert persisted is not None
        assert persisted.status == "active"
        assert persisted.scope_project_ids == ("project-a",)
        assert [item.team_id for item in repository.list_teams_for_user(tenant, member_id)] == [team.team_id]
        listed_members = repository.list_memberships(tenant, team.team_id)
        assert {item.user_id for item in listed_members} == {owner_id, member_id}
        active_users = repository.list_active_users(tenant)
        assert {item["user_id"] for item in active_users} == {owner_id, member_id}
        with pytest.raises(OrganizationAccessError, match="TEAM_LAST_OWNER_CANNOT_BE_REMOVED"):
            repository.remove_member(
                tenant, team.team_id, owner_id, actor_id=owner_id,
                expected_revision=1, occurred_at=NOW,
            )
        removed = repository.remove_member(
            tenant, team.team_id, member_id, actor_id=owner_id,
            expected_revision=1, occurred_at=NOW,
        )
        assert removed.status == "removed"
        assert removed.revision == 2
        connection.commit()

    with psycopg.connect(DSN) as connection:
        repository = PostgresEnterpriseOrganizationAccessRepository(connection)
        assert repository.get_membership(tenant, team.team_id, member_id).status == "removed"
        assert repository.list_teams_for_user(tenant, member_id) == ()
        count = connection.execute(
            "SELECT count(*) FROM enterprise_access_audit WHERE tenant_id=%s AND team_id=%s",
            (tenant, team.team_id),
        ).fetchone()[0]
        assert count == 3
        with pytest.raises(psycopg.Error, match="ENTERPRISE_ACCESS_AUDIT_APPEND_ONLY"):
            connection.execute(
                "UPDATE enterprise_access_audit SET action='member_added' "
                "WHERE tenant_id=%s AND team_id=%s",
                (tenant, team.team_id),
            )
        connection.rollback()


def test_postgres_account_deactivation_is_tenant_scoped_audited_and_revokes_sessions():
    psycopg = pytest.importorskip("psycopg")
    tenant = f"org-account-{uuid.uuid4().hex}"
    with psycopg.connect(DSN) as connection:
        identity = PostgresIdentityStore(connection)
        identity.initialize()
        admin_id = f"account-admin-{uuid.uuid4().hex}"
        target_id = f"account-target-{uuid.uuid4().hex}"
        identity.upsert_user(IdentityUser(
            user_id=admin_id, tenant_id=tenant, email=f"{admin_id}@example.invalid",
            display_name="Admin", roles=frozenset({"enterprise_admin"}),
            password_hash="unused-integration-hash", active=True,
        ))
        identity.upsert_user(IdentityUser(
            user_id=target_id, tenant_id=tenant, email=f"{target_id}@example.invalid",
            display_name="Target", roles=frozenset(), password_hash="unused-integration-hash",
            active=True,
        ))
        repository = PostgresEnterpriseOrganizationAccessRepository(connection)
        repository.initialize()
        issued_token = "session-token-for-account-deactivation-test"
        identity.save_session(StoredSession(
            token_hash=token_hash(issued_token), user_id=target_id, tenant_id=tenant,
            roles=frozenset(), created_at=NOW, last_seen_at=NOW,
            expires_at=NOW.replace(year=NOW.year + 1),
        ))
        assert repository.has_active_role(tenant, admin_id, "enterprise_admin")
        accounts = repository.list_tenant_users(tenant)
        assert {item["user_id"] for item in accounts} == {admin_id, target_id}

        changed = repository.set_account_active(
            tenant, target_id, admin_id, False, NOW,
        )
        assert changed == {"user_id": target_id, "active": False, "changed": True}
        assert not identity.is_user_active(target_id, tenant)
        revoked = connection.execute(
            "SELECT revoked_at FROM identity_sessions WHERE token_hash=%s",
            (token_hash(issued_token),),
        ).fetchone()
        assert revoked is not None and revoked[0] is not None

        with pytest.raises(OrganizationAccessError, match="LAST_ENTERPRISE_ADMIN_CANNOT_BE_DEACTIVATED"):
            repository.set_account_active(tenant, admin_id, admin_id, False, NOW)

        audit_count = connection.execute(
            "SELECT count(*) FROM enterprise_user_access_audit WHERE tenant_id=%s",
            (tenant,),
        ).fetchone()[0]
        assert audit_count == 1
        with pytest.raises(psycopg.Error, match="ENTERPRISE_ACCESS_AUDIT_APPEND_ONLY"):
            connection.execute(
                "UPDATE enterprise_user_access_audit SET action='account_activated' WHERE tenant_id=%s",
                (tenant,),
            )
        connection.rollback()



def test_postgres_team_ownership_transfer_is_atomic_revision_guarded_and_audited():
    psycopg = pytest.importorskip("psycopg")
    tenant = f"org-owner-transfer-{uuid.uuid4().hex}"
    with psycopg.connect(DSN) as connection:
        identity = PostgresIdentityStore(connection)
        identity.initialize()
        old_owner_id = _user(connection, tenant, "old-owner")
        new_owner_id = _user(connection, tenant, "new-owner")
        repository = PostgresEnterpriseOrganizationAccessRepository(connection)
        repository.initialize()
        team = EnterpriseTeam(
            tenant_id=tenant, team_id=f"team-{uuid.uuid4().hex}",
            name="Ownership transfer", owner_user_id=old_owner_id, status="active",
            revision=1, created_at=NOW,
        )
        repository.create_team(team, actor_id=old_owner_id)
        target_membership = EnterpriseTeamMembership(
            tenant_id=tenant, team_id=team.team_id, user_id=new_owner_id,
            role="admin", status="active", scope_project_ids=("project-9",),
            revision=1, created_at=NOW,
        )
        repository.add_member(target_membership, actor_id=old_owner_id)
        connection.commit()

    with psycopg.connect(DSN) as connection:
        repository = PostgresEnterpriseOrganizationAccessRepository(connection)
        with pytest.raises(OrganizationAccessError, match="TEAM_REVISION_CONFLICT"):
            repository.transfer_team_ownership(
                tenant, team.team_id, new_owner_id, actor_id=old_owner_id,
                expected_team_revision=2, expected_membership_revision=1,
                occurred_at=NOW,
            )
        updated = repository.transfer_team_ownership(
            tenant, team.team_id, new_owner_id, actor_id=old_owner_id,
            expected_team_revision=1, expected_membership_revision=1,
            occurred_at=NOW,
        )
        assert updated.owner_user_id == new_owner_id
        assert updated.revision == 2
        old_membership = repository.get_membership(tenant, team.team_id, old_owner_id)
        new_membership = repository.get_membership(tenant, team.team_id, new_owner_id)
        assert old_membership is not None and old_membership.role == "admin"
        assert old_membership.revision == 2
        assert new_membership is not None and new_membership.role == "owner"
        assert new_membership.revision == 2
        assert new_membership.scope_project_ids == ("project-9",)
        audit = connection.execute(
            "SELECT action,before_state,after_state FROM enterprise_access_audit "
            "WHERE tenant_id=%s AND team_id=%s ORDER BY occurred_at,audit_id",
            (tenant, team.team_id),
        ).fetchall()
        assert [row[0] for row in audit][-1] == "team_owner_transferred"
        assert audit[-1][1]["team"]["owner_user_id"] == old_owner_id
        assert audit[-1][2]["team"]["owner_user_id"] == new_owner_id
        connection.commit()
