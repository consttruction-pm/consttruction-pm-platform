from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from construction_pm.enterprise_invitation import TeamInvitation
from construction_pm.enterprise_invitation_repository import PostgresEnterpriseInvitationRepository
from construction_pm.enterprise_organization_access import EnterpriseTeam
from construction_pm.enterprise_organization_access_repository import PostgresEnterpriseOrganizationAccessRepository
from construction_pm.identity_session import IdentityUser, PostgresIdentityStore

DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="CONSTRUCTION_PM_POSTGRES_DSN is required")
NOW = datetime(2026, 11, 15, 18, 0, tzinfo=timezone.utc)


def _user(connection, tenant_id: str, label: str) -> str:
    user_id = f"invite-{label}-{uuid.uuid4().hex}"
    PostgresIdentityStore(connection).upsert_user(IdentityUser(
        user_id=user_id, tenant_id=tenant_id, email=f"{user_id}@example.invalid",
        display_name=label, roles=frozenset(), password_hash="unused-integration-hash", active=True,
    ))
    return user_id


def test_postgres_cubi_id_invitation_is_tenant_bound_one_time_and_audited():
    psycopg = pytest.importorskip("psycopg")
    tenant = f"invite-tenant-{uuid.uuid4().hex}"
    with psycopg.connect(DSN) as connection:
        identity = PostgresIdentityStore(connection)
        identity.initialize()
        owner_id = _user(connection, tenant, "owner")
        member_id = _user(connection, tenant, "member")
        access = PostgresEnterpriseOrganizationAccessRepository(connection)
        access.initialize()
        invitations = PostgresEnterpriseInvitationRepository(connection)
        invitations.initialize()
        team = EnterpriseTeam(
            tenant_id=tenant, team_id=f"team-{uuid.uuid4().hex}", name="Invitation test",
            owner_user_id=owner_id, status="active", revision=1, created_at=NOW,
        )
        access.create_team(team, actor_id=owner_id)
        public_id = invitations.public_id_for_user(tenant, member_id)
        assert public_id.startswith("CUBI-") and len(public_id) == 19
        assert invitations.find_public_identity(tenant, public_id).display_name == "member"
        assert invitations.find_public_identity(tenant + "-other", public_id) is None

        token = "opaque-invitation-token-" + uuid.uuid4().hex
        item = TeamInvitation(
            invitation_id=f"invite-{uuid.uuid4().hex}", tenant_id=tenant, team_id=team.team_id,
            target_user_id=member_id, invited_by_user_id=owner_id, role="field_worker",
            status="pending", expires_at=NOW + timedelta(days=7), created_at=NOW, token=token,
        )
        invitations.create_invitation(item, hashlib.sha256(token.encode()).hexdigest())
        inbox = invitations.list_received_invitations(tenant, member_id)
        assert [entry.invitation_id for entry in inbox] == [item.invitation_id]
        assert inbox[0].token is None
        assert invitations.list_received_invitations(tenant, owner_id) == ()
        connection.commit()

    with psycopg.connect(DSN) as connection:
        invitations = PostgresEnterpriseInvitationRepository(connection)
        with pytest.raises(Exception, match="INVITATION_ACCOUNT_MISMATCH"):
            invitations.accept_invitation(
                tenant, item.invitation_id, hashlib.sha256(token.encode()).hexdigest(),
                owner_id, now=NOW,
            )
        connection.rollback()
        accepted, membership = invitations.accept_invitation(
            tenant, item.invitation_id, hashlib.sha256(token.encode()).hexdigest(),
            member_id, now=NOW,
        )
        assert accepted.status == "accepted"
        assert membership.user_id == member_id
        assert membership.role == "field_worker"
        connection.commit()

    with psycopg.connect(DSN) as connection:
        invitations = PostgresEnterpriseInvitationRepository(connection)
        access = PostgresEnterpriseOrganizationAccessRepository(connection)
        assert invitations.get_invitation(tenant, item.invitation_id).status == "accepted"
        assert invitations.list_received_invitations(tenant, member_id) == ()
        assert access.get_membership(tenant, team.team_id, member_id).status == "active"
        with pytest.raises(Exception, match="INVITATION_NOT_PENDING"):
            invitations.accept_invitation(
                tenant, item.invitation_id, hashlib.sha256(token.encode()).hexdigest(),
                member_id, now=NOW,
            )
        audit_count = connection.execute(
            "SELECT count(*) FROM enterprise_invitation_audit WHERE tenant_id=%s AND invitation_id=%s",
            (tenant, item.invitation_id),
        ).fetchone()[0]
        assert audit_count == 2
        connection.rollback()
