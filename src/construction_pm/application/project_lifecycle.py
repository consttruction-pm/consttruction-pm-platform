from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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
        self, tenant_id: str, user_id: str, project_id: str, name: str
    ) -> ProjectSummary: ...


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

    def open_project(
        self, session_id: str, project_id: str, *, now: datetime
    ) -> ProjectContext:
        session = self.session(session_id, now=now)
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
        auth = context.authorization_context(session.roles)
        self._policy.require(auth, Permission.PROJECT_READ)
        return context

    def create_project(
        self,
        session_id: str,
        project_id: str,
        name: str,
        *,
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
        project = self._projects.create_for_user(
            session.tenant_id, session.user_id, project_id.strip(), name.strip()
        )
        return ProjectContext(
            tenant_id=project.tenant_id,
            project_id=project.project_id,
            revision=project.revision,
            user_id=session.user_id,
        )
