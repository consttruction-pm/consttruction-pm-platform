from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol, Sequence
from uuid import uuid4

from .application.project_lifecycle import ProjectLifecycleError, SessionError

TEAM_ROLES = frozenset({"owner", "admin", "project_manager", "approver", "field_worker", "member", "viewer"})
TEAM_STATUSES = frozenset({"active", "suspended", "archived"})
MEMBERSHIP_STATUSES = frozenset({"active", "suspended", "removed"})


class OrganizationAccessError(ValueError):
    pass


class OrganizationAccessDenied(PermissionError):
    pass


@dataclass(frozen=True)
class EnterpriseTeam:
    tenant_id: str
    team_id: str
    name: str
    owner_user_id: str
    status: str
    revision: int
    created_at: datetime
    updated_at: datetime | None = None

    def validate(self) -> None:
        for key, value in (("tenant_id", self.tenant_id), ("team_id", self.team_id),
                           ("name", self.name), ("owner_user_id", self.owner_user_id)):
            if not isinstance(value, str) or not value.strip():
                raise OrganizationAccessError(f"TEAM_{key.upper()}_INVALID")
        if len(self.name.strip()) > 200:
            raise OrganizationAccessError("TEAM_NAME_TOO_LONG")
        if self.status not in TEAM_STATUSES or self.revision < 0:
            raise OrganizationAccessError("TEAM_STATE_INVALID")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise OrganizationAccessError("TEAM_TIMESTAMP_INVALID")


@dataclass(frozen=True)
class EnterpriseTeamMembership:
    tenant_id: str
    team_id: str
    user_id: str
    role: str
    status: str
    scope_project_ids: tuple[str, ...]
    revision: int
    created_at: datetime
    revoked_at: datetime | None = None

    def validate(self) -> None:
        for key, value in (("tenant_id", self.tenant_id), ("team_id", self.team_id), ("user_id", self.user_id)):
            if not isinstance(value, str) or not value.strip():
                raise OrganizationAccessError(f"MEMBERSHIP_{key.upper()}_INVALID")
        if self.role not in TEAM_ROLES or self.status not in MEMBERSHIP_STATUSES:
            raise OrganizationAccessError("MEMBERSHIP_STATE_INVALID")
        if len(set(self.scope_project_ids)) != len(self.scope_project_ids) or any(
            not isinstance(item, str) or not item.strip() for item in self.scope_project_ids
        ):
            raise OrganizationAccessError("MEMBERSHIP_PROJECT_SCOPE_INVALID")
        if self.revision < 0 or self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise OrganizationAccessError("MEMBERSHIP_REVISION_OR_TIMESTAMP_INVALID")


class EnterpriseOrganizationAccessRepository(Protocol):
    def create_team(self, team: EnterpriseTeam, *, actor_id: str) -> EnterpriseTeam: ...
    def get_team(self, tenant_id: str, team_id: str) -> EnterpriseTeam | None: ...
    def get_membership(self, tenant_id: str, team_id: str, user_id: str) -> EnterpriseTeamMembership | None: ...
    def add_member(self, membership: EnterpriseTeamMembership, *, actor_id: str) -> EnterpriseTeamMembership: ...
    def remove_member(self, tenant_id: str, team_id: str, user_id: str, *, actor_id: str, expected_revision: int, occurred_at: datetime) -> EnterpriseTeamMembership: ...
    def list_teams_for_user(self, tenant_id: str, user_id: str) -> tuple[EnterpriseTeam, ...]: ...


class EnterpriseOrganizationAccessService:
    """Tenant-bound team membership service; it never grants project access implicitly."""

    def __init__(self, repository: EnterpriseOrganizationAccessRepository, lifecycle_api: object, *, clock=None) -> None:
        self._repository = repository
        self._lifecycle = lifecycle_api
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def create_team(self, session_id: str, name: str) -> EnterpriseTeam:
        session = self._session(session_id)
        roles = frozenset(getattr(session, "roles", ()))
        # Team is a Pro entitlement, not a standalone subscription. Until billing
        # provisions this server-side claim, creation fails closed.
        if "pro_monthly_active" not in roles:
            raise OrganizationAccessDenied("ACTIVE_PRO_ENTITLEMENT_REQUIRED")
        if "enterprise_admin" not in roles:
            raise OrganizationAccessDenied("ENTERPRISE_ADMIN_REQUIRED")
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 200:
            raise OrganizationAccessError("TEAM_NAME_INVALID")
        now = self._now()
        team = EnterpriseTeam(
            tenant_id=session.tenant_id,
            team_id=f"team-{uuid4().hex}",
            name=name.strip(),
            owner_user_id=session.user_id,
            status="active",
            revision=1,
            created_at=now,
        )
        team.validate()
        self._repository.create_team(team, actor_id=session.user_id)
        return team

    def add_member(
        self, session_id: str, team_id: str, user_id: str, role: str,
        *, scope_project_ids: Sequence[str] = (),
    ) -> EnterpriseTeamMembership:
        session = self._session(session_id)
        team = self._team(team_id, session.tenant_id)
        self._require_manager(session, team)
        if role not in TEAM_ROLES - {"owner"}:
            raise OrganizationAccessError("TEAM_ROLE_INVALID")
        if not isinstance(user_id, str) or not user_id.strip() or user_id == session.user_id:
            raise OrganizationAccessError("TEAM_MEMBER_TARGET_INVALID")
        scopes = tuple(dict.fromkeys(scope_project_ids))
        now = self._now()
        membership = EnterpriseTeamMembership(
            tenant_id=session.tenant_id,
            team_id=team_id,
            user_id=user_id,
            role=role,
            status="active",
            scope_project_ids=scopes,
            revision=1,
            created_at=now,
        )
        membership.validate()
        self._repository.add_member(membership, actor_id=session.user_id)
        return membership

    def remove_member(
        self, session_id: str, team_id: str, user_id: str, *, expected_revision: int,
    ) -> EnterpriseTeamMembership:
        session = self._session(session_id)
        team = self._team(team_id, session.tenant_id)
        self._require_manager(session, team)
        if user_id == team.owner_user_id:
            raise OrganizationAccessDenied("TEAM_OWNER_TRANSFER_REQUIRED")
        return self._repository.remove_member(
            session.tenant_id, team_id, user_id, actor_id=session.user_id,
            expected_revision=expected_revision, occurred_at=self._now(),
        )

    def list_my_teams(self, session_id: str) -> tuple[EnterpriseTeam, ...]:
        session = self._session(session_id)
        return self._repository.list_teams_for_user(session.tenant_id, session.user_id)

    def require_active_membership(self, tenant_id: str, team_id: str, user_id: str) -> EnterpriseTeamMembership:
        membership = self._repository.get_membership(tenant_id, team_id, user_id)
        if membership is None or membership.status != "active":
            raise OrganizationAccessDenied("ACTIVE_TEAM_MEMBERSHIP_REQUIRED")
        return membership

    def _team(self, team_id: str, tenant_id: str) -> EnterpriseTeam:
        team = self._repository.get_team(tenant_id, team_id)
        if team is None or team.status != "active":
            raise OrganizationAccessDenied("TEAM_NOT_FOUND_OR_INACTIVE")
        return team

    def _require_manager(self, session: object, team: EnterpriseTeam) -> EnterpriseTeamMembership:
        membership = self._repository.get_membership(team.tenant_id, team.team_id, session.user_id)
        if membership is None or membership.status != "active" or membership.role not in {"owner", "admin"}:
            raise OrganizationAccessDenied("TEAM_ADMIN_PERMISSION_REQUIRED")
        return membership

    def _session(self, session_id: str):
        if not isinstance(session_id, str) or not session_id:
            raise OrganizationAccessDenied("SESSION_REQUIRED")
        try:
            session = self._lifecycle.get_session(session_id, now=self._now())
        except (ProjectLifecycleError, SessionError) as exc:
            raise OrganizationAccessDenied("SESSION_REQUIRED") from exc
        if session is None or not getattr(session, "tenant_id", None) or not getattr(session, "user_id", None):
            raise OrganizationAccessDenied("SESSION_REQUIRED")
        return session

    def _now(self) -> datetime:
        now = self._clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise OrganizationAccessError("NOW_MUST_BE_TIMEZONE_AWARE")
        return now.astimezone(timezone.utc)
