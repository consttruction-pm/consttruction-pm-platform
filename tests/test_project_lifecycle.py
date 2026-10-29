from datetime import datetime, timedelta, timezone

import pytest

from construction_pm.application.authorization import AuthorizationError, Permission, default_project_policy
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

    def create_for_user(
        self,
        tenant_id,
        user_id,
        project_id,
        name,
        *,
        description="",
        start_date=None,
        date_system="gregorian",
        primary_calendar_id=None,
    ):
        project = ProjectSummary(
            project_id,
            tenant_id,
            name,
            0,
            description=description,
            start_date=start_date,
            date_system=date_system,
            primary_calendar_id=primary_calendar_id,
        )
        self.items[(tenant_id, user_id, project_id)] = project
        return project

    def update_for_user(
        self,
        tenant_id,
        user_id,
        project_id,
        *,
        expected_revision,
        name,
        description="",
        start_date=None,
        date_system="gregorian",
        primary_calendar_id=None,
    ):
        current = self.items.get((tenant_id, user_id, project_id))
        if current is None or current.settings_revision != expected_revision:
            return None
        updated = ProjectSummary(
            project_id,
            tenant_id,
            name,
            current.revision,
            description=description,
            start_date=start_date,
            date_system=date_system,
            primary_calendar_id=primary_calendar_id,
            settings_revision=current.settings_revision + 1,
        )
        self.items[(tenant_id, user_id, project_id)] = updated
        return updated


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


def test_cross_tenant_project_is_not_discoverable_even_with_matching_project_id():
    now, original_session = make_session()
    session = AuthenticatedSession(
        session_id=original_session.session_id,
        user_id=original_session.user_id,
        tenant_id="tenant-b",
        roles=original_session.roles,
        expires_at=original_session.expires_at,
    )
    with pytest.raises(ProjectLifecycleError, match="PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED"):
        make_service(session).open_project("session-a", "project-a", now=now)


def test_authorize_project_uses_one_validated_session_snapshot():
    class CountingSessions(Sessions):
        def __init__(self, session):
            super().__init__(session)
            self.calls = 0

        def get(self, session_id):
            self.calls += 1
            return super().get(session_id)

    now, session = make_session(roles=frozenset({"viewer"}))
    sessions = CountingSessions(session)
    service = ProjectLifecycleService(sessions, Projects(), default_project_policy())

    with pytest.raises(AuthorizationError, match="permission=project.write"):
        service.authorize_project(
            "session-a", "project-a", Permission.PROJECT_WRITE, now=now
        )

    assert sessions.calls == 1


def test_project_admin_can_create_project_with_persisted_metadata():
    now, session = make_session(roles=frozenset({"project_admin"}))
    projects = Projects()
    service = ProjectLifecycleService(
        Sessions(session), projects, default_project_policy()
    )
    context = service.create_project(
        "session-a",
        "project-new",
        "New Project",
        description="  Highway package  ",
        start_date="2026-10-05",
        date_system="jalali",
        primary_calendar_id="CAL-1",
        now=now,
    )
    assert context.revision == 0

    created = service.get_project("session-a", "project-new", now=now)
    assert created.description == "Highway package"
    assert created.start_date == "2026-10-05"
    assert created.date_system == "jalali"
    assert created.primary_calendar_id == "CAL-1"


def test_create_project_rejects_invalid_metadata():
    now, session = make_session(roles=frozenset({"project_admin"}))
    service = make_service(session)

    for kwargs, code in (
        ({"start_date": "05/10/2026"}, "PROJECT_START_DATE_INVALID"),
        ({"start_date": "2026-02-30"}, "PROJECT_START_DATE_INVALID"),
        ({"date_system": "hijri"}, "PROJECT_DATE_SYSTEM_INVALID"),
        ({"description": "x" * 2001}, "PROJECT_DESCRIPTION_TOO_LONG"),
        ({"primary_calendar_id": " "}, "PROJECT_PRIMARY_CALENDAR_ID_INVALID"),
    ):
        with pytest.raises(ProjectLifecycleError, match=code):
            service.create_project(
                "session-a", "project-new", "New Project", now=now, **kwargs
            )


def test_update_project_increments_configuration_revision_and_replaces_metadata():
    now, session = make_session(roles=frozenset({"project_admin"}))
    projects = Projects()
    service = ProjectLifecycleService(
        Sessions(session), projects, default_project_policy()
    )

    updated = service.update_project(
        "session-a",
        "project-a",
        name="Project A Renamed",
        description="Updated scope",
        start_date="2026-11-01",
        date_system="gregorian",
        primary_calendar_id="CAL-2",
        expected_revision=0,
        now=now,
    )
    assert updated.settings_revision == 1
    assert updated.revision == 7, "the workspace data revision must stay stable"
    assert updated.name == "Project A Renamed"
    assert updated.description == "Updated scope"
    assert updated.start_date == "2026-11-01"
    assert updated.primary_calendar_id == "CAL-2"


def test_update_project_rejects_stale_revision_without_overwriting():
    now, session = make_session(roles=frozenset({"project_admin"}))
    projects = Projects()
    service = ProjectLifecycleService(
        Sessions(session), projects, default_project_policy()
    )

    with pytest.raises(ProjectLifecycleError, match="PROJECT_REVISION_CONFLICT"):
        service.update_project(
            "session-a",
            "project-a",
            name="Stale Rename",
            expected_revision=1,
            now=now,
        )
    assert projects.get_for_user("tenant-a", "project-a", "user-a").name == "Project A"


def test_update_project_rejects_the_workspace_data_revision_as_a_stale_token():
    now, session = make_session(roles=frozenset({"project_admin"}))
    projects = Projects()
    service = ProjectLifecycleService(
        Sessions(session), projects, default_project_policy()
    )

    with pytest.raises(ProjectLifecycleError, match="PROJECT_REVISION_CONFLICT"):
        service.update_project(
            "session-a",
            "project-a",
            name="Data revision token",
            expected_revision=7,
            now=now,
        )
    assert projects.get_for_user("tenant-a", "project-a", "user-a").name == "Project A"


def test_viewer_cannot_update_project_metadata():
    now, session = make_session(roles=frozenset({"viewer"}))
    with pytest.raises(AuthorizationError, match="project.admin"):
        make_service(session).update_project(
            "session-a",
            "project-a",
            name="Viewer Rename",
            expected_revision=7,
            now=now,
        )
