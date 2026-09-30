from datetime import datetime, timezone

from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import (
    AuthenticatedSession, ProjectLifecycleService, ProjectSummary
)
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI


class Sessions:
    def __init__(self, session): self.session = session
    def get(self, session_id): return self.session if session_id == self.session.session_id else None


class Projects:
    def list_for_user(self, tenant_id, user_id):
        return (ProjectSummary("p1", tenant_id, "Project 1", 3),)
    def get_for_user(self, tenant_id, project_id, user_id):
        return ProjectSummary(project_id, tenant_id, "Project 1", 3) if project_id == "p1" else None
    def create_for_user(self, tenant_id, user_id, project_id, name):
        return ProjectSummary(project_id, tenant_id, name, 0)


def make_api():
    now = datetime(2026, 9, 30, 8, 0, tzinfo=timezone.utc)
    session = AuthenticatedSession("s1", "u1", "t1", frozenset({"project_admin"}), now.replace(hour=9))
    service = ProjectLifecycleService(Sessions(session), Projects(), default_project_policy())
    return ProjectLifecycleAPI(service), now


def test_api_exposes_session_and_authorized_project_context():
    api, now = make_api()
    session = api.get_session("s1", now=now)
    assert session.user_id == "u1"
    projects = api.list_projects("s1", now=now)
    assert projects.projects[0].project_id == "p1"
    opened = api.open_project("s1", "p1", now=now)
    assert opened.context.tenant_id == "t1"


def test_api_create_project_returns_authoritative_context():
    api, now = make_api()
    created = api.create_project("s1", "p2", "Project 2", now=now)
    assert created.context.project_id == "p2"
    assert created.context.user_id == "u1"
