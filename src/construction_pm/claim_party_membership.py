from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4


PARTY_ROLES = frozenset({"employer", "contractor", "subcontractor", "consultant", "other"})
MEMBERSHIP_STATES = frozenset({"active", "suspended", "revoked"})


class ClaimPartyMembershipError(ValueError):
    pass


class ClaimPartyMembershipDenied(PermissionError):
    pass


@dataclass(frozen=True)
class ClaimPartyMembership:
    tenant_id: str
    project_id: str
    contract_id: str
    claim_id: str
    party_id: str
    user_id: str
    party_role: str
    status: str
    revision: int
    effective_from: datetime
    created_at: datetime
    created_by: str
    effective_until: datetime | None = None
    revoked_at: datetime | None = None
    revoked_by: str | None = None

    def validate(self) -> None:
        for field in (
            "tenant_id", "project_id", "contract_id", "claim_id",
            "party_id", "user_id", "created_by",
        ):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip():
                raise ClaimPartyMembershipError(f"INVALID_{field.upper()}")
        if self.party_role not in PARTY_ROLES or self.status not in MEMBERSHIP_STATES:
            raise ClaimPartyMembershipError("INVALID_CLAIM_PARTY_MEMBERSHIP_STATE")
        if isinstance(self.revision, bool) or not isinstance(self.revision, int) or self.revision < 1:
            raise ClaimPartyMembershipError("INVALID_CLAIM_PARTY_MEMBERSHIP_REVISION")
        for field in ("effective_from", "created_at", "effective_until", "revoked_at"):
            value = getattr(self, field)
            if value is not None and (value.tzinfo is None or value.utcoffset() is None):
                raise ClaimPartyMembershipError(f"{field.upper()}_MUST_BE_TIMEZONE_AWARE")
        if self.effective_until is not None and self.effective_until <= self.effective_from:
            raise ClaimPartyMembershipError("INVALID_CLAIM_PARTY_MEMBERSHIP_PERIOD")
        if self.status == "revoked":
            if self.revoked_at is None or not self.revoked_by:
                raise ClaimPartyMembershipError("REVOCATION_METADATA_REQUIRED")
        elif self.revoked_at is not None or self.revoked_by is not None:
            raise ClaimPartyMembershipError("REVOCATION_METADATA_WITHOUT_REVOKED_STATE")

    def active_at(self, when: datetime) -> bool:
        self.validate()
        if when.tzinfo is None or when.utcoffset() is None:
            raise ClaimPartyMembershipError("QUERY_TIME_MUST_BE_TIMEZONE_AWARE")
        instant = when.astimezone(timezone.utc)
        return (
            self.status == "active"
            and self.effective_from.astimezone(timezone.utc) <= instant
            and (self.effective_until is None or instant < self.effective_until.astimezone(timezone.utc))
        )


class ClaimPartyMembershipRepository(Protocol):
    def grant(self, membership: ClaimPartyMembership) -> ClaimPartyMembership: ...
    def revoke(
        self, *, tenant_id: str, project_id: str, contract_id: str, claim_id: str,
        party_id: str, user_id: str, expected_revision: int, actor_id: str, occurred_at: datetime,
    ) -> ClaimPartyMembership: ...
    def resolve_active_parties(
        self, *, tenant_id: str, project_id: str, contract_id: str,
        claim_id: str, user_id: str, at: datetime,
    ) -> tuple[str, ...]: ...


class ClaimPartySessionResolver(Protocol):
    def get_session(self, session_id: str, *, now: datetime): ...


class ClaimPartyMembershipService:
    """Binds authenticated CUBI users to a claim party; never trusts request party IDs."""

    def __init__(self, repository: ClaimPartyMembershipRepository, sessions: ClaimPartySessionResolver, *, clock=None):
        self._repository = repository
        self._sessions = sessions
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def grant(
        self, session_id: str, *, project_id: str, contract_id: str, claim_id: str,
        party_id: str, user_id: str, party_role: str, effective_from: datetime | None = None,
    ) -> ClaimPartyMembership:
        session = self._session(session_id)
        self._require_contract_admin(session)
        now = self._now()
        membership = ClaimPartyMembership(
            tenant_id=session.tenant_id, project_id=project_id, contract_id=contract_id,
            claim_id=claim_id, party_id=party_id, user_id=user_id, party_role=party_role,
            status="active", revision=1, effective_from=effective_from or now,
            created_at=now, created_by=session.user_id,
        )
        membership.validate()
        return self._repository.grant(membership)

    def revoke(
        self, session_id: str, *, project_id: str, contract_id: str, claim_id: str,
        party_id: str, user_id: str, expected_revision: int,
    ) -> ClaimPartyMembership:
        session = self._session(session_id)
        self._require_contract_admin(session)
        return self._repository.revoke(
            tenant_id=session.tenant_id, project_id=project_id, contract_id=contract_id,
            claim_id=claim_id, party_id=party_id, user_id=user_id,
            expected_revision=expected_revision, actor_id=session.user_id, occurred_at=self._now(),
        )

    def resolve_active_parties(
        self, session_id: str, *, project_id: str, contract_id: str, claim_id: str,
    ) -> tuple[str, ...]:
        session = self._session(session_id)
        return self._repository.resolve_active_parties(
            tenant_id=session.tenant_id, project_id=project_id, contract_id=contract_id,
            claim_id=claim_id, user_id=session.user_id, at=self._now(),
        )

    def _session(self, session_id: str):
        if not isinstance(session_id, str) or not session_id:
            raise ClaimPartyMembershipDenied("AUTHENTICATED_SESSION_REQUIRED")
        try:
            session = self._sessions.get_session(session_id, now=self._now())
        except Exception as exc:
            raise ClaimPartyMembershipDenied("AUTHENTICATED_SESSION_REQUIRED") from exc
        if session is None or not getattr(session, "tenant_id", None) or not getattr(session, "user_id", None):
            raise ClaimPartyMembershipDenied("AUTHENTICATED_SESSION_REQUIRED")
        return session

    @staticmethod
    def _require_contract_admin(session) -> None:
        roles = frozenset(getattr(session, "roles", ()))
        if not roles.intersection({"enterprise_admin", "contract_admin"}):
            raise ClaimPartyMembershipDenied("CONTRACT_PARTY_ADMIN_REQUIRED")

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ClaimPartyMembershipError("NOW_MUST_BE_TIMEZONE_AWARE")
        return value.astimezone(timezone.utc)


def new_claim_party_membership_id() -> str:
    return f"claim-party-membership-{uuid4().hex}"
