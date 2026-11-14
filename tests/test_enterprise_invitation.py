from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from construction_pm.enterprise_invitation import (
    EnterpriseInvitationService, InvitationDenied, PublicCubiIdentity, TeamInvitation,
)

NOW = datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc)


class Lifecycle:
    def get_session(self, session_id, *, now):
        sessions = {
            "owner": SimpleNamespace(user_id="owner", tenant_id="tenant-a"),
            "member": SimpleNamespace(user_id="member", tenant_id="tenant-a"),
            "other": SimpleNamespace(user_id="other", tenant_id="tenant-a"),
        }
        return sessions.get(session_id)


class Access:
    def __init__(self):
        self.team = SimpleNamespace(tenant_id="tenant-a", team_id="team-a", status="active")
        self.members = {
            ("tenant-a", "team-a", "owner"): SimpleNamespace(status="active", role="owner"),
            ("tenant-a", "team-a", "other"): SimpleNamespace(status="active", role="viewer"),
        }

    def get_team(self, tenant_id, team_id):
        return self.team if (tenant_id, team_id) == ("tenant-a", "team-a") else None

    def get_membership(self, tenant_id, team_id, user_id):
        return self.members.get((tenant_id, team_id, user_id))


class Repository:
    def __init__(self):
        self.ids = {"CUBI-2345-6789-ABCD": ("member", "Member")}
        self.invites = {}

    def find_public_identity(self, tenant_id, cubi_id):
        value = self.ids.get(cubi_id)
        return PublicCubiIdentity(cubi_id, value[1]) if value else None

    def public_id_for_user(self, tenant_id, user_id):
        return "CUBI-2345-6789-ABCD" if user_id == "member" else "CUBI-3456-789A-BCDE"

    def user_id_for_cubi_id(self, tenant_id, cubi_id):
        return self.ids[cubi_id][0]

    def create_invitation(self, item, token_hash):
        self.invites[item.invitation_id] = (item, token_hash)
        return item

    def get_invitation(self, tenant_id, invitation_id):
        pair = self.invites.get(invitation_id)
        return pair[0] if pair else None

    def accept_invitation(self, tenant_id, invitation_id, token_hash, user_id, *, now):
        item, expected = self.invites[invitation_id]
        if token_hash != expected:
            raise InvitationDenied("INVITATION_TOKEN_INVALID")
        if item.target_user_id != user_id:
            raise InvitationDenied("INVITATION_ACCOUNT_MISMATCH")
        accepted = TeamInvitation(**{**item.__dict__, "status": "accepted", "responded_at": now, "token": None})
        self.invites[invitation_id] = (accepted, expected)
        return accepted, SimpleNamespace(user_id=user_id, role=item.role, status="active")

    def decline_invitation(self, tenant_id, invitation_id, token_hash, user_id, *, now):
        item, expected = self.invites[invitation_id]
        if token_hash != expected or item.target_user_id != user_id:
            raise InvitationDenied("INVITATION_ACCOUNT_MISMATCH")
        declined = TeamInvitation(**{**item.__dict__, "status": "declined", "responded_at": now, "token": None})
        self.invites[invitation_id] = (declined, expected)
        return declined

    def revoke_invitation(self, tenant_id, invitation_id, actor_id, *, now):
        item, token_hash = self.invites[invitation_id]
        revoked = TeamInvitation(**{**item.__dict__, "status": "revoked", "responded_at": now, "token": None})
        self.invites[invitation_id] = (revoked, token_hash)
        return revoked

    def list_invitations(self, tenant_id, team_id):
        return tuple(pair[0] for pair in self.invites.values() if pair[0].team_id == team_id)

    def list_received_invitations(self, tenant_id, target_user_id):
        return tuple(pair[0] for pair in self.invites.values()
                     if pair[0].tenant_id == tenant_id
                     and pair[0].target_user_id == target_user_id
                     and pair[0].status == "pending")


def build():
    repository = Repository()
    service = EnterpriseInvitationService(
        repository, Access(), Lifecycle(), clock=lambda: NOW
    )
    return service, repository


def test_cubi_id_lookup_normalizes_format_and_returns_only_public_context():
    service, _ = build()
    result = service.lookup("owner", " cubi 2345-6789-abcd ")
    assert result == PublicCubiIdentity("CUBI-2345-6789-ABCD", "Member")


def test_invitation_is_bound_to_target_and_token_is_not_persisted_as_plaintext():
    service, repository = build()
    item = service.invite("owner", "team-a", "CUBI-2345-6789-ABCD", "field_worker")
    stored, digest = repository.invites[item.invitation_id]
    assert item.status == "pending"
    assert item.token and digest == hashlib.sha256(item.token.encode()).hexdigest()
    assert stored.token == item.token
    with pytest.raises(InvitationDenied, match="INVITATION_ACCOUNT_MISMATCH"):
        service.accept("other", item.invitation_id, item.token)
    accepted, membership = service.accept("member", item.invitation_id, item.token)
    assert accepted.status == "accepted"
    assert membership.user_id == "member"


def test_non_manager_cannot_invite_and_unknown_cubi_id_is_not_resolved():
    service, _ = build()
    with pytest.raises(InvitationDenied, match="TEAM_ADMIN_PERMISSION_REQUIRED"):
        service.invite("other", "team-a", "CUBI-2345-6789-ABCD", "member")
    with pytest.raises(InvitationDenied, match="CUBI_ID_NOT_FOUND"):
        service.lookup("owner", "CUBI-9999-9999-9999")


def test_invalid_public_id_and_token_fail_closed():
    service, _ = build()
    with pytest.raises(ValueError, match="CUBI_ID_INVALID"):
        service.lookup("owner", "CUBI-123")
    with pytest.raises(InvitationDenied, match="INVITATION_TOKEN_INVALID"):
        service.accept("member", "invite-x", "short")

def test_invitation_rejects_user_who_is_already_an_active_team_member():
    service, _ = build()
    service._access.members[("tenant-a", "team-a", "member")] = SimpleNamespace(
        status="active", role="member"
    )
    with pytest.raises(ValueError, match="USER_ALREADY_TEAM_MEMBER"):
        service.invite("owner", "team-a", "CUBI-2345-6789-ABCD", "field_worker")


def test_recipient_can_list_only_their_own_pending_invitations():
    service, _ = build()
    created = service.invite("owner", "team-a", "CUBI-2345-6789-ABCD", "field_worker")
    inbox = service.list_received("member")
    assert [item.invitation_id for item in inbox] == [created.invitation_id]
    assert inbox[0].token is None
