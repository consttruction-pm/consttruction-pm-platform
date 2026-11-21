from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from construction_pm.claim_party_membership import (
    ClaimPartyMembership,
    ClaimPartyMembershipDenied,
    ClaimPartyMembershipError,
    ClaimPartyMembershipService,
)

NOW = datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)


class Sessions:
    def __init__(self, roles=("enterprise_admin",)):
        self.roles = frozenset(roles)

    def get_session(self, session_id, *, now):
        if session_id != "valid":
            return None
        return SimpleNamespace(user_id="admin-user", tenant_id="tenant-1", roles=self.roles)


class Repository:
    def __init__(self):
        self.rows = {}

    def grant(self, item):
        key = (item.tenant_id, item.project_id, item.contract_id, item.claim_id, item.party_id, item.user_id)
        if key in self.rows:
            raise ClaimPartyMembershipError("CLAIM_PARTY_MEMBERSHIP_ALREADY_EXISTS")
        self.rows[key] = item
        return item

    def revoke(self, **kwargs):
        key = (kwargs["tenant_id"], kwargs["project_id"], kwargs["contract_id"], kwargs["claim_id"], kwargs["party_id"], kwargs["user_id"])
        item = self.rows[key]
        if item.revision != kwargs["expected_revision"]:
            raise ClaimPartyMembershipError("CLAIM_PARTY_MEMBERSHIP_REVISION_CONFLICT")
        revoked = ClaimPartyMembership(
            **{**item.__dict__, "status": "revoked", "revision": item.revision + 1,
               "revoked_at": kwargs["occurred_at"], "revoked_by": kwargs["actor_id"]}
        )
        self.rows[key] = revoked
        return revoked

    def resolve_active_parties(self, **kwargs):
        return tuple(sorted(
            item.party_id for item in self.rows.values()
            if item.tenant_id == kwargs["tenant_id"] and item.project_id == kwargs["project_id"]
            and item.contract_id == kwargs["contract_id"] and item.claim_id == kwargs["claim_id"]
            and item.user_id == kwargs["user_id"] and item.active_at(kwargs["at"])
        ))


def make_service(roles=("enterprise_admin",)):
    repo = Repository()
    service = ClaimPartyMembershipService(repo, Sessions(roles), clock=lambda: NOW)
    return service, repo


def test_grant_is_bound_to_authenticated_tenant_and_server_actor():
    service, repo = make_service()
    item = service.grant(
        "valid", project_id="project-1", contract_id="contract-1", claim_id="claim-1",
        party_id="party-employer", user_id="user-1", party_role="employer",
    )
    assert item.tenant_id == "tenant-1"
    assert item.created_by == "admin-user"
    assert repo.resolve_active_parties(
        tenant_id="tenant-1", project_id="project-1", contract_id="contract-1",
        claim_id="claim-1", user_id="user-1", at=NOW,
    ) == ("party-employer",)


def test_party_grant_requires_contract_admin_and_valid_session():
    service, _ = make_service(("project_viewer",))
    with pytest.raises(ClaimPartyMembershipDenied, match="CONTRACT_PARTY_ADMIN_REQUIRED"):
        service.grant(
            "valid", project_id="project-1", contract_id="contract-1", claim_id="claim-1",
            party_id="party-1", user_id="user-1", party_role="contractor",
        )
    with pytest.raises(ClaimPartyMembershipDenied, match="AUTHENTICATED_SESSION_REQUIRED"):
        service.grant(
            "invalid", project_id="project-1", contract_id="contract-1", claim_id="claim-1",
            party_id="party-1", user_id="user-1", party_role="contractor",
        )


def test_revocation_is_immediate_and_revision_guarded():
    service, repo = make_service()
    item = service.grant(
        "valid", project_id="project-1", contract_id="contract-1", claim_id="claim-1",
        party_id="party-contractor", user_id="user-2", party_role="contractor",
    )
    revoked = service.revoke(
        "valid", project_id="project-1", contract_id="contract-1", claim_id="claim-1",
        party_id=item.party_id, user_id=item.user_id, expected_revision=item.revision,
    )
    assert revoked.status == "revoked"
    assert repo.resolve_active_parties(
        tenant_id="tenant-1", project_id="project-1", contract_id="contract-1",
        claim_id="claim-1", user_id="user-2", at=NOW,
    ) == ()
    with pytest.raises(ClaimPartyMembershipError, match="REVOCATION_METADATA_REQUIRED"):
        ClaimPartyMembership(
            tenant_id="tenant-1", project_id="p", contract_id="c", claim_id="cl",
            party_id="party", user_id="u", party_role="other", status="revoked",
            revision=1, effective_from=NOW, created_at=NOW, created_by="a",
        ).validate()


def test_effective_period_and_tenant_scoping():
    service, repo = make_service()
    starts = NOW + timedelta(hours=1)
    service.grant(
        "valid", project_id="project-1", contract_id="contract-1", claim_id="claim-1",
        party_id="party-1", user_id="user-1", party_role="other", effective_from=starts,
    )
    assert repo.resolve_active_parties(
        tenant_id="tenant-1", project_id="project-1", contract_id="contract-1",
        claim_id="claim-1", user_id="user-1", at=NOW,
    ) == ()
    assert repo.resolve_active_parties(
        tenant_id="tenant-2", project_id="project-1", contract_id="contract-1",
        claim_id="claim-1", user_id="user-1", at=starts,
    ) == ()
