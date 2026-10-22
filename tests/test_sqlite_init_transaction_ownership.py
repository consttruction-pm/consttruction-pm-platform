from __future__ import annotations

import sqlite3

from construction_pm.project_schedule_settings_repository import (
    SQLiteProjectScheduleSettingsRepository,
)
from tests.test_project_schedule_settings_repository import date_settings, scope


def test_sqlite_repository_init_does_not_commit_caller_transaction(tmp_path):
    database = str(tmp_path / "repo-init-transaction.sqlite")
    writer = sqlite3.connect(database)

    try:
        writer.execute(
            "CREATE TABLE sentinel_tx (id INTEGER PRIMARY KEY, marker TEXT NOT NULL)"
        )
        writer.execute("BEGIN")
        writer.execute("INSERT INTO sentinel_tx (marker) VALUES (?)", ("pending",))
        assert writer.in_transaction is True

        repo = SQLiteProjectScheduleSettingsRepository(writer)
        assert writer.in_transaction is True
        assert repo.get(scope()) is None

        repo.save(date_settings(), expected_revision=0)

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
