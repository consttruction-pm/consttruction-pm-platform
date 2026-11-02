from __future__ import annotations

import sqlite3

import pytest

from construction_pm.application.project_lifecycle import ProjectSummary
from construction_pm.sqlite_project_lifecycle import SQLiteProjectRepository


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
