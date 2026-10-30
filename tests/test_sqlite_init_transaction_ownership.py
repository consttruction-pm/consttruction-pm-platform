from __future__ import annotations

import sqlite3

import pytest

from construction_pm.project_schedule_settings_repository import (
    SQLiteProjectScheduleSettingsRepository,
)
from tests.test_project_schedule_settings_repository import date_settings, scope


def test_sqlite_repository_init_does_not_commit_caller_transaction(tmp_path):
    database = str(tmp_path / "repo-init-transaction.sqlite")
    writer = sqlite3.connect(database)

    try:
        # Reuse the same database file so the schema is visible to a separate
        # connection before the caller begins its own transaction.
        repo = SQLiteProjectScheduleSettingsRepository(writer)
        writer.execute(
            "CREATE TABLE IF NOT EXISTS sentinel_tx (id INTEGER PRIMARY KEY, marker TEXT NOT NULL)"
        )
        writer.execute("BEGIN")
        writer.execute("INSERT INTO sentinel_tx (marker) VALUES (?)", ("pending",))

        assert writer.in_transaction is True

        # Re-initialize on the same connection while the caller's transaction is active.
        repo_again = SQLiteProjectScheduleSettingsRepository(writer)
        assert repo_again.connection is writer
        assert writer.in_transaction is True
        assert repo_again.get(scope()) is None

        # The original unconditional constructor commit would commit the caller-owned
        # transaction here, making the sentinel row visible to a second connection.
        with sqlite3.connect(database) as reader:
            assert reader.execute(
                "SELECT COUNT(*) FROM sentinel_tx WHERE marker = ?",
                ("pending",),
            ).fetchone()[0] == 0
            assert reader.execute(
                "SELECT COUNT(*) FROM project_schedule_settings"
            ).fetchone()[0] == 0

        writer.rollback()
        assert writer.in_transaction is False

        with sqlite3.connect(database) as reader:
            assert reader.execute(
                "SELECT COUNT(*) FROM sentinel_tx WHERE marker = ?",
                ("pending",),
            ).fetchone()[0] == 0
            assert reader.execute(
                "SELECT COUNT(*) FROM project_schedule_settings"
            ).fetchone()[0] == 0
    finally:
        writer.close()


def test_sqlite_repository_init_standalone_connection_creates_schema(tmp_path):
    database = str(tmp_path / "repo-init-standalone.sqlite")
    connection = sqlite3.connect(database)

    try:
        repo = SQLiteProjectScheduleSettingsRepository(connection)
        assert connection.in_transaction is False
        assert repo.get(scope()) is None
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='project_schedule_settings'"
        ).fetchone()[0] == "project_schedule_settings"
    finally:
        connection.close()


def test_failed_repository_write_preserves_caller_owned_transaction(tmp_path):
    database = str(tmp_path / "repo-failed-write-outer-transaction.sqlite")
    writer = sqlite3.connect(database)
    repo = SQLiteProjectScheduleSettingsRepository(writer)
    writer.execute(
        "CREATE TABLE sentinel_tx (id INTEGER PRIMARY KEY, marker TEXT NOT NULL)"
    )
    writer.execute(
        "CREATE TRIGGER fail_settings_insert BEFORE INSERT ON project_schedule_settings "
        "BEGIN SELECT RAISE(ABORT, 'forced insert failure'); END"
    )

    try:
        writer.execute("BEGIN")
        writer.execute("INSERT INTO sentinel_tx (marker) VALUES (?)", ("pending",))
        with pytest.raises(sqlite3.IntegrityError, match="forced insert failure"):
            repo.save(date_settings(), expected_revision=0)

        # The repository must not roll back a transaction that the caller began.
        assert writer.in_transaction is True
        with sqlite3.connect(database) as reader:
            assert reader.execute("SELECT COUNT(*) FROM sentinel_tx").fetchone()[0] == 0
            assert reader.execute("SELECT COUNT(*) FROM project_schedule_settings").fetchone()[0] == 0

        writer.rollback()
        assert writer.in_transaction is False
        with sqlite3.connect(database) as reader:
            assert reader.execute("SELECT COUNT(*) FROM sentinel_tx").fetchone()[0] == 0
            assert reader.execute("SELECT COUNT(*) FROM project_schedule_settings").fetchone()[0] == 0
    finally:
        writer.close()

