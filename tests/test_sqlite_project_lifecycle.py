from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import AuthenticatedSession, ProjectSummary
from construction_pm.sqlite_project_lifecycle import (
    SQLiteProjectRepository,
    build_sqlite_project_lifecycle_api,
)


def test_sqlite_project_repository_create_list_get_and_membership_scope():
    connection = sqlite3.connect(":memory:")
    repository = SQLiteProjectRepository(connection)

    created = repository.create_for_user(
        "tenant-a",
        "user-a",
        "project-a",
        "Local project",
        description="offline project",
        start_date="2026-11-03",
        date_system="jalali",
        primary_calendar_id="CAL-1",
    )

    assert created == ProjectSummary(
        project_id="project-a",
        tenant_id="tenant-a",
        name="Local project",
        revision=0,
        description="offline project",
        start_date="2026-11-03",
        date_system="jalali",
        primary_calendar_id="CAL-1",
        settings_revision=0,
    )
    assert repository.get_for_user("tenant-a", "project-a", "user-a") == created
    assert repository.get_for_user("tenant-a", "project-a", "other-user") is None
    assert repository.get_for_user("other-tenant", "project-a", "user-a") is None
    assert repository.list_for_user("tenant-a", "user-a") == (created,)
    assert repository.list_for_user("tenant-a", "other-user") == ()
    connection.close()


def test_sqlite_project_repository_settings_revision_is_separate_from_project_data_revision():
    connection = sqlite3.connect(":memory:")
    repository = SQLiteProjectRepository(connection)
    repository.create_for_user("t", "u", "p", "Before")

    updated = repository.update_for_user(
        "t",
        "u",
        "p",
        expected_revision=0,
        name="After",
        description="updated description",
        start_date="2026-11-03",
        date_system="gregorian",
        primary_calendar_id="CAL-2",
    )
    assert updated is not None
    assert updated.name == "After"
    assert updated.revision == 0
    assert updated.settings_revision == 1

    stale = repository.update_for_user(
        "t", "u", "p", expected_revision=0, name="Stale writer"
    )
    assert stale is None
    assert repository.get_for_user("t", "p", "u") == updated
    connection.close()


def test_sqlite_project_repository_create_respects_caller_owned_transaction():
    connection = sqlite3.connect(":memory:")
    repository = SQLiteProjectRepository(connection)
    connection.execute("BEGIN IMMEDIATE")

    repository.create_for_user("t", "u", "p", "Caller transaction")
    assert connection.in_transaction
    assert repository.get_for_user("t", "p", "u") is not None

    connection.rollback()
    assert repository.get_for_user("t", "p", "u") is None
    connection.close()


def test_sqlite_project_repository_is_durable_across_connection_restart(tmp_path):
    database = tmp_path / "offline-project.sqlite3"
    connection = sqlite3.connect(database)
    repository = SQLiteProjectRepository(connection)
    repository.create_for_user("t", "u", "p", "Durable project")
    connection.close()

    reopened = sqlite3.connect(database)
    repository_after_restart = SQLiteProjectRepository(reopened)
    persisted = repository_after_restart.get_for_user("t", "p", "u")
    assert persisted is not None
    assert persisted.name == "Durable project"
    assert persisted.revision == 0
    reopened.close()


def test_sqlite_project_repository_duplicate_create_is_rejected_atomically():
    connection = sqlite3.connect(":memory:")
    repository = SQLiteProjectRepository(connection)
    repository.create_for_user("t", "u", "p", "Original")

    with pytest.raises(ValueError, match="PROJECT_ALREADY_EXISTS_OR_MEMBERSHIP_INVALID"):
        repository.create_for_user("t", "u2", "p", "Duplicate")

    assert repository.get_for_user("t", "p", "u") is not None
    assert repository.get_for_user("t", "p", "u2") is None
    connection.close()



class LocalSessions:
    def __init__(self, session):
        self.session = session

    def get(self, session_id):
        return self.session if session_id == self.session.session_id else None


def test_sqlite_project_repository_composes_with_shared_lifecycle_api():
    now = datetime(2026, 11, 3, 10, 0, tzinfo=timezone.utc)
    session = AuthenticatedSession(
        "offline-session",
        "local-user",
        "local-tenant",
        frozenset({"project_admin"}),
        now + timedelta(days=2),
    )
    connection = sqlite3.connect(":memory:")
    api = build_sqlite_project_lifecycle_api(
        connection,
        LocalSessions(session),
        default_project_policy(),
    )

    created = api.create_project(
        "offline-session",
        "project-1",
        "Offline project",
        start_date="2026-11-03",
        date_system="jalali",
        now=now,
    )
    assert created.context.tenant_id == "local-tenant"
    assert created.context.project_id == "project-1"

    project = api.get_project("offline-session", "project-1", now=now)
    assert project.name == "Offline project"
    assert project.start_date == "2026-11-03"
    assert project.date_system == "jalali"

    updated = api.update_project(
        "offline-session",
        "project-1",
        name="Offline project revised",
        expected_revision=project.settings_revision,
        now=now,
    )
    assert updated.name == "Offline project revised"
    assert updated.revision == 0
    assert updated.settings_revision == 1
    assert api.open_project("offline-session", "project-1", now=now).context.revision == 0
    connection.close()



def test_sqlite_project_repository_uses_component_schema_version_not_database_user_version():
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA user_version = 37")
    connection.execute(
        """CREATE TABLE cubi_local_schema_versions (
            component TEXT PRIMARY KEY,
            version INTEGER NOT NULL CHECK (version >= 1)
        )"""
    )
    connection.execute(
        "INSERT INTO cubi_local_schema_versions(component, version) VALUES (?, ?)",
        ("other_component", 6),
    )
    connection.commit()

    SQLiteProjectRepository(connection)

    assert connection.execute("PRAGMA user_version").fetchone()[0] == 37
    versions = dict(connection.execute(
        "SELECT component, version FROM cubi_local_schema_versions"
    ).fetchall())
    assert versions == {"other_component": 6, "project_lifecycle": 1}
    connection.close()


def test_sqlite_project_repository_schema_initialization_respects_outer_transaction():
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE caller_state (value TEXT NOT NULL)")
    connection.execute("BEGIN IMMEDIATE")
    connection.execute("INSERT INTO caller_state(value) VALUES ('pending')")

    SQLiteProjectRepository(connection)

    assert connection.in_transaction
    assert connection.execute(
        "SELECT version FROM cubi_local_schema_versions WHERE component='project_lifecycle'"
    ).fetchone() == (1,)
    connection.rollback()
    assert connection.execute("SELECT value FROM caller_state").fetchall() == []
    assert connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='project_lifecycle_projects'"
    ).fetchone() is None
    connection.close()
