from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol
from uuid import uuid4

from .application.project_lifecycle import ProjectLifecycleError, SessionError
from .enterprise_organization_access import (
    EnterpriseTeamMembership, TEAM_ROLES,
)

_CUBI_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


class InvitationError(ValueError):
    pass


class InvitationDenied(PermissionError):
    pass


@dataclass(frozen=True)
class PublicCubiIdentity:
    cubi_id: str
    display_name: str


@dataclass(frozen=True)
class TeamInvitation:
    invitation_id: str
    tenant_id: str
    team_id: str
    target_user_id: str
    invited_by_user_id: str
    role: str
    status: str
    expires_at: datetime
    created_at: datetime
    responded_at: datetime | None = None
    token: str | None = None


class EnterpriseInvitationRepository(Protocol):
    def find_public_identity(self, tenant_id: str, cubi_id: str) -> PublicCubiIdentity | None: ...
    def create_invitation(self, invitation: TeamInvitation, token_hash: str) -> TeamInvitation: ...
    def accept_invitation(self, tenant_id: str, invitation_id: str, token_hash: str, user_id: str,
                          *, now: datetime) -> tuple[TeamInvitation, EnterpriseTeamMembership | None]: ...
    def accept_invitation_from_recipient(self, tenant_id: str, invitation_id: str, user_id: str,
                                         *, now: datetime) -> tuple[TeamInvitation, EnterpriseTeamMembership | None]: ...
    def decline_invitation_from_recipient(self, tenant_id: str, invitation_id: str, user_id: str,
                                          *, now: datetime) -> TeamInvitation: ...
    def decline_invitation(self, tenant_id: str, invitation_id: str, token_hash: str, user_id: str,
                           *, now: datetime) -> TeamInvitation: ...
    def revoke_invitation(self, tenant_id: str, invitation_id: str, actor_id: str,
                          *, now: datetime) -> TeamInvitation: ...
    def get_invitation(self, tenant_id: str, invitation_id: str) -> TeamInvitation | None: ...
    def public_id_for_user(self, tenant_id: str, user_id: str) -> str: ...
    def user_id_for_cubi_id(self, tenant_id: str, cubi_id: str) -> str: ...
    def list_invitations(self, tenant_id: str, team_id: str) -> tuple[TeamInvitation, ...]: ...
    def list_received_invitations(self, tenant_id: str, target_user_id: str) -> tuple[TeamInvitation, ...]: ...


class EnterpriseInvitationService:
    """CUBI-ID invitations; authenticated identity and current team membership remain authoritative."""

    def __init__(self, repository: EnterpriseInvitationRepository, access_repository: object,
                 lifecycle: object, *, clock=None, ttl: timedelta = timedelta(days=7)) -> None:
        if ttl <= timedelta(0) or ttl > timedelta(days=30):
            raise InvitationError("INVITATION_TTL_INVALID")
        self._repository = repository
        self._access = access_repository
        self._lifecycle = lifecycle
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._ttl = ttl

    def my_public_id(self, session_id: str) -> str:
        session = self._session(session_id)
        return self._repository.public_id_for_user(session.tenant_id, session.user_id)

    def lookup(self, session_id: str, cubi_id: str) -> PublicCubiIdentity:
        session = self._session(session_id)
        normalized = self._normalize_cubi_id(cubi_id)
        result = self._repository.find_public_identity(session.tenant_id, normalized)
        if result is None:
            raise InvitationDenied("CUBI_ID_NOT_FOUND")
        return result

    def invite(self, session_id: str, team_id: str, cubi_id: str, role: str) -> TeamInvitation:
        session = self._session(session_id)
        team = self._access.get_team(session.tenant_id, team_id)
        if team is None or team.status != "active":
            raise InvitationDenied("TEAM_NOT_FOUND_OR_INACTIVE")
        manager = self._access.get_membership(session.tenant_id, team_id, session.user_id)
        if manager is None or manager.status != "active" or manager.role not in {"owner", "admin"}:
            raise InvitationDenied("TEAM_ADMIN_PERMISSION_REQUIRED")
        if role not in TEAM_ROLES - {"owner"}:
            raise InvitationError("TEAM_ROLE_INVALID")
        if role == "admin" and manager.role != "owner":
            raise InvitationDenied("ONLY_OWNER_CAN_GRANT_TEAM_ADMIN")
        target = self._repository.find_public_identity(
            session.tenant_id, self._normalize_cubi_id(cubi_id)
        )
        if target is None:
            raise InvitationDenied("CUBI_ID_NOT_FOUND")
        # Avoid self-invites and duplicate active memberships/invitations in the repository.
        if target.cubi_id == self._repository.public_id_for_user(session.tenant_id, session.user_id):
            raise InvitationError("SELF_INVITATION_NOT_ALLOWED")
        now = self._now()
        raw_token = secrets.token_urlsafe(32)
        target_user_id = self._repository.user_id_for_cubi_id(session.tenant_id, target.cubi_id)
        existing = self._access.get_membership(session.tenant_id, team_id, target_user_id)
        if existing is not None and existing.status == "active":
            raise InvitationError("USER_ALREADY_TEAM_MEMBER")
        invitation = TeamInvitation(
            invitation_id=f"invite-{uuid4().hex}", tenant_id=session.tenant_id,
            team_id=team_id, target_user_id=target_user_id,
            invited_by_user_id=session.user_id, role=role, status="pending",
            expires_at=now + self._ttl, created_at=now, token=raw_token,
        )
        return self._repository.create_invitation(
            invitation, hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        )

    def accept(self, session_id: str, invitation_id: str, token: str) -> tuple[TeamInvitation, EnterpriseTeamMembership | None]:
        session = self._session(session_id)
        return self._repository.accept_invitation(
            session.tenant_id, invitation_id, self._token_hash(token), session.user_id, now=self._now()
        )

    def decline(self, session_id: str, invitation_id: str, token: str) -> TeamInvitation:
        session = self._session(session_id)
        return self._repository.decline_invitation(
            session.tenant_id, invitation_id, self._token_hash(token), session.user_id, now=self._now()
        )

    def accept_from_inbox(self, session_id: str, invitation_id: str) -> tuple[TeamInvitation, EnterpriseTeamMembership | None]:
        session = self._session(session_id)
        return self._repository.accept_invitation_from_recipient(
            session.tenant_id, invitation_id, session.user_id, now=self._now()
        )

    def decline_from_inbox(self, session_id: str, invitation_id: str) -> TeamInvitation:
        session = self._session(session_id)
        return self._repository.decline_invitation_from_recipient(
            session.tenant_id, invitation_id, session.user_id, now=self._now()
        )

    def revoke(self, session_id: str, invitation_id: str) -> TeamInvitation:
        session = self._session(session_id)
        invitation = self._repository.get_invitation(session.tenant_id, invitation_id)
        if invitation is None:
            raise InvitationDenied("INVITATION_NOT_FOUND")
        team = self._access.get_team(session.tenant_id, invitation.team_id)
        membership = self._access.get_membership(session.tenant_id, invitation.team_id, session.user_id)
        if team is None or membership is None or membership.status != "active" or membership.role not in {"owner", "admin"}:
            raise InvitationDenied("TEAM_ADMIN_PERMISSION_REQUIRED")
        return self._repository.revoke_invitation(
            session.tenant_id, invitation_id, session.user_id, now=self._now()
        )

    def list_for_team(self, session_id: str, team_id: str) -> tuple[TeamInvitation, ...]:
        session = self._session(session_id)
        team = self._access.get_team(session.tenant_id, team_id)
        membership = self._access.get_membership(session.tenant_id, team_id, session.user_id)
        if team is None or membership is None or membership.status != "active" or membership.role not in {"owner", "admin"}:
            raise InvitationDenied("TEAM_ADMIN_PERMISSION_REQUIRED")
        return self._repository.list_invitations(session.tenant_id, team_id)

    def list_received(self, session_id: str) -> tuple[TeamInvitation, ...]:
        """Return only the authenticated user's incoming invitations."""
        session = self._session(session_id)
        return self._repository.list_received_invitations(
            session.tenant_id, session.user_id
        )

    def _session(self, session_id: str):
        if not isinstance(session_id, str) or not session_id:
            raise InvitationDenied("SESSION_REQUIRED")
        try:
            session = self._lifecycle.get_session(session_id, now=self._now())
        except (ProjectLifecycleError, SessionError) as exc:
            raise InvitationDenied("SESSION_REQUIRED") from exc
        if session is None or not getattr(session, "tenant_id", None) or not getattr(session, "user_id", None):
            raise InvitationDenied("SESSION_REQUIRED")
        return session

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise InvitationError("NOW_MUST_BE_TIMEZONE_AWARE")
        return value.astimezone(timezone.utc)

    @staticmethod
    def _normalize_cubi_id(value: str) -> str:
        if not isinstance(value, str):
            raise InvitationError("CUBI_ID_INVALID")
        normalized = value.strip().upper().replace("-", "").replace(" ", "")
        if len(normalized) != 16 or not normalized.startswith("CUBI") or any(
            char not in _CUBI_ALPHABET for char in normalized[4:]
        ):
            raise InvitationError("CUBI_ID_INVALID")
        return f"CUBI-{normalized[4:8]}-{normalized[8:12]}-{normalized[12:16]}"

    @staticmethod
    def _token_hash(token: str) -> str:
        if not isinstance(token, str) or len(token) < 32 or len(token) > 256:
            raise InvitationDenied("INVITATION_TOKEN_INVALID")
        return hashlib.sha256(token.encode("utf-8")).hexdigest()
