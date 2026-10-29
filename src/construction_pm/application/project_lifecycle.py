from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

from .authorization import AuthorizationContext, AuthorizationError, Permission, RoleBasedAuthorizationPolicy


class SessionError(ValueError):
    """Raised when a session is invalid or expired."""


class ProjectLifecycleError(ValueError):
    """Raised when a project lifecycle operation cannot be completed."""


@dataclass(frozen=True)
class AuthenticatedSession:
    session_id: str
    user_id: str
    tenant_id: str
    roles: frozenset[str]
    expires_at: datetime

    def validate(self, *, now: datetime) -> None:
        for name, value in (
            ("session_id", self.session_id),
            ("user_id", self.user_id),
            ("tenant_id", self.tenant_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise SessionError(f"INVALID_SESSION_{name.upper()}")
        if not isinstance(self.roles, frozenset) or any(
            not isinstance(role, str) or not role.strip() for role in self.roles
        ):
            raise SessionError("INVALID_SESSION_ROLES")
        if self.expires_at.tzinfo is None or self.expires_at.utcoffset() is None:
            raise SessionError("SESSION_EXPIRY_MUST_BE_TIMEZONE_AWARE")
        if now.tzinfo is None or now.utcoffset() is None:
            raise SessionError("NOW_MUST_BE_TIMEZONE_AWARE")
        if now >= self.expires_at:
            raise SessionError("SESSION_EXPIRED")


@dataclass(frozen=True)
class ProjectSummary:
    project_id: str
    tenant_id: str
    name: str
    revision: int
    description: str = ""
    start_date: str | None = None
    date_system: str = "gregorian"
    primary_calendar_id: str | None = None
    # Configuration edits are guarded by their own optimistic token. The
    # ``revision`` column identifies the workspace data version every
    # activity/WBS/relationship row is stamped with; reusing it for metadata
    # edits would make existing workspace data unreadable after a rename.
    settings_revision: int = 0


DATE_SYSTEMS = frozenset({"gregorian", "jalali"})
MAX_PROJECT_DESCRIPTION = 2000
MAX_PROJECT_CALENDAR_ID = 200


def normalize_project_description(value: object) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ProjectLifecycleError("PROJECT_DESCRIPTION_INVALID")
    description = value.strip()
    if len(description) > MAX_PROJECT_DESCRIPTION:
        raise ProjectLifecycleError("PROJECT_DESCRIPTION_TOO_LONG")
    return description


def normalize_project_start_date(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ProjectLifecycleError("PROJECT_START_DATE_INVALID")
    start_date = value.strip()
    try:
        parsed = date.fromisoformat(start_date)
    except ValueError as exc:
        raise ProjectLifecycleError("PROJECT_START_DATE_INVALID") from exc
    if parsed.isoformat() != start_date:
        raise ProjectLifecycleError("PROJECT_START_DATE_INVALID")
    return start_date


def normalize_project_date_system(value: object) -> str:
    if value is None or value == "":
        return "gregorian"
    if not isinstance(value, str) or value not in DATE_SYSTEMS:
        raise ProjectLifecycleError("PROJECT_DATE_SYSTEM_INVALID")
    return value


def normalize_project_calendar_id(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ProjectLifecycleError("PROJECT_PRIMARY_CALENDAR_ID_INVALID")
    calendar_id = value.strip()
    if len(calendar_id) > MAX_PROJECT_CALENDAR_ID:
        raise ProjectLifecycleError("PROJECT_PRIMARY_CALENDAR_ID_INVALID")
    return calendar_id


def normalize_expected_revision(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ProjectLifecycleError("PROJECT_REVISION_INVALID")
    return value


@dataclass(frozen=True)
class ProjectContext:
    tenant_id: str
    project_id: str
    revision: int
    user_id: str

    def authorization_context(self, roles: frozenset[str]) -> AuthorizationContext:
        return AuthorizationContext(
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            user_id=self.user_id,
            roles=roles,
        )


class ProjectRepository(Protocol):
    def list_for_user(self, tenant_id: str, user_id: str) -> tuple[ProjectSummary, ...]: ...
    def get_for_user(self, tenant_id: str, project_id: str, user_id: str) -> ProjectSummary | None: ...
    def create_for_user(
        self,
        tenant_id: str,
        user_id: str,
        project_id: str,
        name: str,
        *,
        description: str = "",
        start_date: str | None = None,
        date_system: str = "gregorian",
        primary_calendar_id: str | None = None,
    ) -> ProjectSummary: ...
    def update_for_user(
        self,
        tenant_id: str,
        user_id: str,
        project_id: str,
        *,
        expected_revision: int,
        name: str,
        description: str = "",
        start_date: str | None = None,
        date_system: str = "gregorian",
        primary_calendar_id: str | None = None,
    ) -> ProjectSummary | None: ...


class SessionRepository(Protocol):
    def get(self, session_id: str) -> AuthenticatedSession | None: ...


class ProjectLifecycleService:
    """Authoritative session-bound project lifecycle boundary.

    The browser never supplies an authoritative tenant/user identity. A transport
    adapter resolves the opaque session first, then this service derives project
    context from that session and the authorized project repository.
    """

    def __init__(
        self,
        sessions: SessionRepository,
        projects: ProjectRepository,
        policy: RoleBasedAuthorizationPolicy,
    ) -> None:
        self._sessions = sessions
        self._projects = projects
        self._policy = policy

    def session(self, session_id: str, *, now: datetime) -> AuthenticatedSession:
        session = self._sessions.get(session_id)
        if session is None:
            raise SessionError("SESSION_NOT_FOUND")
        session.validate(now=now)
        return session

    def list_projects(
        self, session_id: str, *, now: datetime
    ) -> tuple[ProjectSummary, ...]:
        session = self.session(session_id, now=now)
        return self._projects.list_for_user(session.tenant_id, session.user_id)

    def _open_project_for_session(
        self, session: AuthenticatedSession, project_id: str
    ) -> ProjectContext:
        project = self._projects.get_for_user(
            session.tenant_id, project_id, session.user_id
        )
        if project is None:
            raise ProjectLifecycleError("PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED")
        context = ProjectContext(
            tenant_id=project.tenant_id,
            project_id=project.project_id,
            revision=project.revision,
            user_id=session.user_id,
        )
        self._policy.require(
            context.authorization_context(session.roles), Permission.PROJECT_READ
        )
        return context

    def open_project(
        self, session_id: str, project_id: str, *, now: datetime
    ) -> ProjectContext:
        session = self.session(session_id, now=now)
        return self._open_project_for_session(session, project_id)

    def authorize_project(
        self,
        session_id: str,
        project_id: str,
        permission: Permission,
        *,
        now: datetime,
    ) -> ProjectContext:
        """Resolve scope once from the authenticated session, then enforce permission."""
        session = self.session(session_id, now=now)
        context = self._open_project_for_session(session, project_id)
        self._policy.require(context.authorization_context(session.roles), permission)
        return context

    def create_project(
        self,
        session_id: str,
        project_id: str,
        name: str,
        *,
        description: str = "",
        start_date: str | None = None,
        date_system: str = "gregorian",
        primary_calendar_id: str | None = None,
        now: datetime,
    ) -> ProjectContext:
        session = self.session(session_id, now=now)
        if not self._policy.is_allowed(
            AuthorizationContext(
                tenant_id=session.tenant_id,
                project_id=project_id,
                user_id=session.user_id,
                roles=session.roles,
            ),
            Permission.PROJECT_ADMIN,
        ):
            raise AuthorizationError("authorization denied for permission=project.admin")
        if not isinstance(project_id, str) or not project_id.strip():
            raise ProjectLifecycleError("PROJECT_ID_REQUIRED")
        if not isinstance(name, str) or not name.strip():
            raise ProjectLifecycleError("PROJECT_NAME_REQUIRED")
        normalized_description = normalize_project_description(description)
        normalized_start_date = normalize_project_start_date(start_date)
        normalized_date_system = normalize_project_date_system(date_system)
        normalized_calendar_id = normalize_project_calendar_id(primary_calendar_id)
        project = self._projects.create_for_user(
            session.tenant_id,
            session.user_id,
            project_id.strip(),
            name.strip(),
            description=normalized_description,
            start_date=normalized_start_date,
            date_system=normalized_date_system,
            primary_calendar_id=normalized_calendar_id,
        )
        return ProjectContext(
            tenant_id=project.tenant_id,
            project_id=project.project_id,
            revision=project.revision,
            user_id=session.user_id,
        )

    def get_project(
        self, session_id: str, project_id: str, *, now: datetime
    ) -> ProjectSummary:
        session = self.session(session_id, now=now)
        project = self._projects.get_for_user(
            session.tenant_id, project_id, session.user_id
        )
        if project is None:
            raise ProjectLifecycleError("PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED")
        self._policy.require(
            ProjectContext(
                tenant_id=project.tenant_id,
                project_id=project.project_id,
                revision=project.revision,
                user_id=session.user_id,
            ).authorization_context(session.roles),
            Permission.PROJECT_READ,
        )
        return project

    def update_project(
        self,
        session_id: str,
        project_id: str,
        *,
        name: str,
        description: str = "",
        start_date: str | None = None,
        date_system: str = "gregorian",
        primary_calendar_id: str | None = None,
        expected_revision: int,
        now: datetime,
    ) -> ProjectSummary:
        """Replace project metadata under optimistic-concurrency control.

        ``expected_revision`` is the configuration revision the editor loaded
        (``ProjectSummary.settings_revision``), not the workspace data revision.
        A stale value never overwrites newer metadata: the repository performs a
        conditional update and the service reports a conflict for the caller to
        resolve by reloading.
        """
        session = self.session(session_id, now=now)
        existing = self._projects.get_for_user(
            session.tenant_id, project_id, session.user_id
        )
        if existing is None:
            raise ProjectLifecycleError("PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED")
        self._policy.require(
            ProjectContext(
                tenant_id=existing.tenant_id,
                project_id=existing.project_id,
                revision=existing.revision,
                user_id=session.user_id,
            ).authorization_context(session.roles),
            Permission.PROJECT_ADMIN,
        )
        if not isinstance(name, str) or not name.strip():
            raise ProjectLifecycleError("PROJECT_NAME_REQUIRED")
        revision = normalize_expected_revision(expected_revision)
        normalized_description = normalize_project_description(description)
        normalized_start_date = normalize_project_start_date(start_date)
        normalized_date_system = normalize_project_date_system(date_system)
        normalized_calendar_id = normalize_project_calendar_id(primary_calendar_id)
        updated = self._projects.update_for_user(
            session.tenant_id,
            session.user_id,
            project_id,
            expected_revision=revision,
            name=name.strip(),
            description=normalized_description,
            start_date=normalized_start_date,
            date_system=normalized_date_system,
            primary_calendar_id=normalized_calendar_id,
        )
        if updated is None:
            if self._projects.get_for_user(
                session.tenant_id, project_id, session.user_id
            ) is None:
                raise ProjectLifecycleError("PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED")
            raise ProjectLifecycleError("PROJECT_REVISION_CONFLICT")
        return updated
