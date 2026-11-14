from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .authorization import Permission

from .project_lifecycle import (
    ProjectContext,
    ProjectLifecycleService,
    ProjectStatusEvent,
    ProjectSummary,
)


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

    def authorize_project(
        self,
        session_id: str,
        project_id: str,
        permission: Permission,
        *,
        now: datetime,
    ) -> ProjectContextResponse:
        return ProjectContextResponse(
            self._service.authorize_project(
                session_id, project_id, permission, now=now
            )
        )

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
        business_domain: str = "",
        obs_responsible_manager: str = "",
        website_url: str = "",
        default_activity_type: str = "Task Dependent",
        default_percent_complete_type: str = "DURATION",
        activity_id_prefix: str = "",
        activity_id_suffix: str = "",
        activity_id_increment: int = 10,
        increment_activity_id: bool = False,
        now: datetime,
    ) -> ProjectContextResponse:
        return ProjectContextResponse(
            self._service.create_project(
                session_id,
                project_id,
                name,
                description=description,
                start_date=start_date,
                date_system=date_system,
                primary_calendar_id=primary_calendar_id,
                business_domain=business_domain,
                obs_responsible_manager=obs_responsible_manager,
                website_url=website_url,
                default_activity_type=default_activity_type,
                default_percent_complete_type=default_percent_complete_type,
                activity_id_prefix=activity_id_prefix,
                activity_id_suffix=activity_id_suffix,
                activity_id_increment=activity_id_increment,
                increment_activity_id=increment_activity_id,
                now=now,
            )
        )

    def get_project(
        self, session_id: str, project_id: str, *, now: datetime
    ) -> ProjectSummary:
        return self._service.get_project(session_id, project_id, now=now)

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
        business_domain: str | None = None,
        obs_responsible_manager: str | None = None,
        website_url: str | None = None,
        default_activity_type: str | None = None,
        default_percent_complete_type: str | None = None,
        activity_id_prefix: str | None = None,
        activity_id_suffix: str | None = None,
        activity_id_increment: int | None = None,
        increment_activity_id: bool | None = None,
        expected_revision: int,
        now: datetime,
    ) -> ProjectSummary:
        return self._service.update_project(
            session_id,
            project_id,
            name=name,
            description=description,
            start_date=start_date,
            date_system=date_system,
            primary_calendar_id=primary_calendar_id,
            business_domain=business_domain,
            obs_responsible_manager=obs_responsible_manager,
            website_url=website_url,
            default_activity_type=default_activity_type,
            default_percent_complete_type=default_percent_complete_type,
            activity_id_prefix=activity_id_prefix,
            activity_id_suffix=activity_id_suffix,
            activity_id_increment=activity_id_increment,
            increment_activity_id=increment_activity_id,
            expected_revision=expected_revision,
            now=now,
        )

    def set_project_status(
        self,
        session_id: str,
        project_id: str,
        *,
        status: str,
        expected_revision: int,
        now: datetime,
    ) -> ProjectSummary:
        return self._service.set_project_status(
            session_id,
            project_id,
            status=status,
            expected_revision=expected_revision,
            now=now,
        )

    def set_project_checkout(
        self,
        session_id: str,
        project_id: str,
        *,
        checked_out: bool,
        expected_revision: int,
        now: datetime,
    ) -> ProjectSummary:
        return self._service.set_project_checkout(
            session_id,
            project_id,
            checked_out=checked_out,
            expected_revision=expected_revision,
            now=now,
        )

    def project_status_history(
        self, session_id: str, project_id: str, *, now: datetime
    ) -> tuple[ProjectStatusEvent, ...]:
        return self._service.project_status_history(session_id, project_id, now=now)
