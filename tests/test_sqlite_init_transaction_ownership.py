from __future__ import annotations

import sqlite3

import pytest

from construction_pm.project_schedule_settings_repository import (
    ProjectScheduleSettingsPersistenceError,
    SQLiteProjectScheduleSettingsRepository,
)
from tests.test_project_schedule_settings_repository import date_settings, scope


def test_sqlite_repository_init_does_not_commit_caller_transaction(tmp_path):
    database = str(tmp_path / "repo-init-transaction.sqlite")
    connection = sqlite3.connect(database)
    try:
        connection.execute("BEGIN")
        repo = SQLiteProjectScheduleSettingsRepository(connection)
        assert connection.in_transaction
        assert repo.get(scope()) is None
        connection.rollback()
        assert connection.in_transaction is False
    finally:
        connection.close()
