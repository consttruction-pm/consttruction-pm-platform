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
from construction_pm.identity_session import IdentityUser, PostgresIdentityStore

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
        assert {item.user_id for item in repository.list_members(tenant, team.team_id)} == {owner_id, member_id}
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


def test_postgres_ownership_transfer_is_atomic_audited_and_preserves_single_owner():
    psycopg = pytest.importorskip("psycopg")
    tenant = f"org-transfer-{uuid.uuid4().hex}"
    with psycopg.connect(DSN) as connection:
        identity = PostgresIdentityStore(connection)
        identity.initialize()
        owner_id = _user(connection, tenant, "owner")
        next_owner_id = _user(connection, tenant, "next-owner")
        repository = PostgresEnterpriseOrganizationAccessRepository(connection)
        repository.initialize()
        team = EnterpriseTeam(
            tenant_id=tenant, team_id=f"team-{uuid.uuid4().hex}",
            name="Ownership transfer", owner_user_id=owner_id, status="active",
            revision=1, created_at=NOW,
        )
        repository.create_team(team, actor_id=owner_id)
        repository.add_member(EnterpriseTeamMembership(
            tenant_id=tenant, team_id=team.team_id, user_id=next_owner_id,
            role="admin", status="active", scope_project_ids=(), revision=1,
            created_at=NOW,
        ), actor_id=owner_id)
        transferred = repository.transfer_ownership(
            tenant, team.team_id, owner_id, next_owner_id,
            expected_team_revision=1, occurred_at=NOW,
        )
        assert transferred.owner_user_id == next_owner_id
        assert transferred.revision == 2
        assert repository.get_membership(tenant, team.team_id, owner_id).role == "admin"
        assert repository.get_membership(tenant, team.team_id, next_owner_id).role == "owner"
        with pytest.raises(OrganizationAccessError, match="TEAM_OWNER_CHANGED"):
            repository.transfer_ownership(
                tenant, team.team_id, owner_id, next_owner_id,
                expected_team_revision=2, occurred_at=NOW,
            )
        with pytest.raises(OrganizationAccessError, match="TEAM_LAST_OWNER_CANNOT_BE_REMOVED"):
            repository.remove_member(
                tenant, team.team_id, next_owner_id, actor_id=next_owner_id,
                expected_revision=2, occurred_at=NOW,
            )
        audit_count = connection.execute(
            "SELECT count(*) FROM enterprise_access_audit WHERE tenant_id=%s AND team_id=%s",
            (tenant, team.team_id),
        ).fetchone()[0]
        assert audit_count == 3
        transfer_event = connection.execute(
            "SELECT action FROM enterprise_access_audit WHERE tenant_id=%s AND team_id=%s "
            "ORDER BY occurred_at DESC,audit_id DESC LIMIT 1",
            (tenant, team.team_id),
        ).fetchone()
        assert transfer_event[0] == "team_owner_transferred"
        connection.commit()
