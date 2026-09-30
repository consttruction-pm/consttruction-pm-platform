from datetime import datetime, timedelta, timezone

import pytest

from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import (
    AuthenticatedSession,
    ProjectLifecycleError,
    ProjectLifecycleService,
    ProjectSummary,
    SessionError,
)


class Sessions:
    def __init__(self, session):
        self.session = session

    def get(self, session_id):
        return self.session if session_id == self.session.session_id else None


class Projects:
    def __init__(self):
        self.items = {
            ("tenant-a", "user-a", "project-a"): ProjectSummary(
                "project-a", "tenant-a", "Project A", 7
            )
        }

    def list_for_user(self, tenant_id, user_id):
        return tuple(
            project
            for (tenant, user, _), project in self.items.items()
            if tenant == tenant_id and user == user_id
        )

    def get_for_user(self, tenant_id, project_id, user_id):
        return self.items.get((tenant_id, user_id, project_id))

    def create_for_user(self, tenant_id, user_id, project_id, name):
        project = ProjectSummary(project_id, tenant_id, name, 0)
        self.items[(tenant_id, user_id, project_id)] = project
        return project


def make_session(*, roles=frozenset({"planner"}), expired=False):
    now = datetime(2026, 9, 30, 7, 0, tzinfo=timezone.utc)
    return now, AuthenticatedSession(
        session_id="session-a",
        user_id="user-a",
        tenant_id="tenant-a",
        roles=roles,
        expires_at=now - timedelta(seconds=1) if expired else now + timedelta(hours=1),
    )


def make_service(session):
    return ProjectLifecycleService(
        Sessions(session),
        Projects(),
        default_project_policy(),
    )


def test_open_project_derives_context_from_session_not_browser_headers():
    now, session = make_session()
    context = make_service(session).open_project("session-a", "project-a", now=now)
    assert context.tenant_id == "tenant-a"
    assert context.project_id == "project-a"
    assert context.revision == 7
    assert context.user_id == "user-a"


def test_cross_user_project_is_not_discoverable():
    now, session = make_session()
    with pytest.raises(ProjectLifecycleError, match="PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED"):
        make_service(session).open_project("session-a", "project-other", now=now)


def test_expired_session_is_rejected_before_project_access():
    now, session = make_session(expired=True)
    with pytest.raises(SessionError, match="SESSION_EXPIRED"):
        make_service(session).list_projects("session-a", now=now)


def test_viewer_cannot_create_project():
    now, session = make_session(roles=frozenset({"viewer"}))
    with pytest.raises(Exception, match="project.admin"):
        make_service(session).create_project(
            "session-a", "project-new", "New Project", now=now
        )


def test_project_admin_can_create_project():
    now, session = make_session(roles=frozenset({"project_admin"}))
    context = make_service(session).create_project(
        "session-a", "project-new", "New Project", now=now
    )
    assert context.project_id == "project-new"
    assert context.revision == 0
