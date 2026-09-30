from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .project_lifecycle import ProjectContext, ProjectLifecycleService, ProjectSummary


@dataclass(frozen=True)
class SessionResponse:
    session_id: str
    user_id: str
    tenant_id: str
    roles: frozenset[str]
    expires_at: datetime


@dataclass(frozen=True)
class ProjectListResponse:
    projects: tuple[ProjectSummary, ...]


@dataclass(frozen=True)
class ProjectContextResponse:
    context: ProjectContext


class ProjectLifecycleAPI:
    """Transport-neutral API adapter for authenticated Web lifecycle calls."""

    def __init__(self, service: ProjectLifecycleService) -> None:
        self._service = service

    def get_session(self, session_id: str, *, now: datetime) -> SessionResponse:
        session = self._service.session(session_id, now=now)
        return SessionResponse(
            session_id=session.session_id,
            user_id=session.user_id,
            tenant_id=session.tenant_id,
            roles=session.roles,
            expires_at=session.expires_at,
        )

    def list_projects(self, session_id: str, *, now: datetime) -> ProjectListResponse:
        return ProjectListResponse(self._service.list_projects(session_id, now=now))

    def open_project(
        self, session_id: str, project_id: str, *, now: datetime
    ) -> ProjectContextResponse:
        return ProjectContextResponse(
            self._service.open_project(session_id, project_id, now=now)
        )

    def create_project(
        self, session_id: str, project_id: str, name: str, *, now: datetime
    ) -> ProjectContextResponse:
        return ProjectContextResponse(
            self._service.create_project(session_id, project_id, name, now=now)
        )
