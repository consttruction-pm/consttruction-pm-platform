from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest

from construction_pm.change_claims import (
    ChangeClaim, ChangeClaimStatus, ChangeClaimType, PostgresChangeClaimStore,
)
from construction_pm.claim_party_membership import ClaimPartyMembership, ClaimPartyMembershipError
from construction_pm.claim_party_membership_repository import PostgresClaimPartyMembershipRepository
from construction_pm.identity_session import IdentityUser, PostgresIdentityStore

DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN") or os.getenv("P6_TEST_POSTGRES_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="CONSTRUCTION_PM_POSTGRES_DSN or P6_TEST_POSTGRES_DSN is required")
NOW = datetime(2026, 11, 16, 13, 0, tzinfo=timezone.utc)


def test_postgres_claim_party_membership_is_tenant_claim_scoped_and_revocable():
    psycopg = pytest.importorskip("psycopg")
    suffix = uuid.uuid4().hex
    tenant, project = f"claim-party-{suffix}", f"project-{suffix}"
    contract, claim_id = f"contract-{suffix}", f"claim-{suffix}"
    user_id = f"user-{suffix}"
    with psycopg.connect(DSN) as connection:
        identity = PostgresIdentityStore(connection)
        identity.initialize()
        identity.upsert_user(IdentityUser(
            user_id=user_id, tenant_id=tenant, email=f"{user_id}@example.invalid",
            display_name="Claim party member", roles=frozenset(),
            password_hash="unused-integration-hash", active=True,
        ))
        claims = PostgresChangeClaimStore(connection)
        claims.initialize()
        claims.ensure_project(tenant, project)
        claims.persist(
            ChangeClaim(
                tenant_id=tenant, project_id=project, resource_id=claim_id, revision=0,
                resource_type=ChangeClaimType.CLAIM, status=ChangeClaimStatus.DRAFT,
                actor_id=user_id, occurred_at=NOW.isoformat(),
                payload={"contract_id": contract, "summary": "test claim"},
            ),
            expected_project_revision=0, idempotency_key=f"create-{suffix}",
        )
        repository = PostgresClaimPartyMembershipRepository(connection)
        repository.initialize()
        item = ClaimPartyMembership(
            tenant_id=tenant, project_id=project, contract_id=contract, claim_id=claim_id,
            party_id=f"party-{suffix}", user_id=user_id, party_role="contractor",
            status="active", revision=1, effective_from=NOW, created_at=NOW, created_by=user_id,
        )
        repository.grant(item)
        connection.commit()

    with psycopg.connect(DSN) as connection:
        repository = PostgresClaimPartyMembershipRepository(connection)
        assert repository.resolve_active_parties(
            tenant_id=tenant, project_id=project, contract_id=contract,
            claim_id=claim_id, user_id=user_id, at=NOW,
        ) == (item.party_id,)
        with pytest.raises(ClaimPartyMembershipError, match="CLAIM_CONTRACT_SCOPE_MISMATCH"):
            repository.resolve_active_parties(
                tenant_id=tenant, project_id=project, contract_id="wrong-contract",
                claim_id=claim_id, user_id=user_id, at=NOW,
            )
        revoked = repository.revoke(
            tenant_id=tenant, project_id=project, contract_id=contract, claim_id=claim_id,
            party_id=item.party_id, user_id=user_id, expected_revision=1,
            actor_id=user_id, occurred_at=NOW,
        )
        assert revoked.status == "revoked"
        assert repository.resolve_active_parties(
            tenant_id=tenant, project_id=project, contract_id=contract,
            claim_id=claim_id, user_id=user_id, at=NOW,
        ) == ()
        connection.commit()

    with psycopg.connect(DSN) as connection:
        count = connection.execute(
            "SELECT count(*) FROM claim_party_membership_audit WHERE tenant_id=%s AND claim_id=%s",
            (tenant, claim_id),
        ).fetchone()[0]
        assert count == 2
        with pytest.raises(psycopg.Error, match="CLAIM_PARTY_MEMBERSHIP_AUDIT_APPEND_ONLY"):
            connection.execute(
                "UPDATE claim_party_membership_audit SET action='granted' WHERE tenant_id=%s AND claim_id=%s",
                (tenant, claim_id),
            )
        connection.rollback()
