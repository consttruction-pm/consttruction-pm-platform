from __future__ import annotations

import sqlite3

import pytest

from construction_pm.backend_p0.transactions import execute_sqlite_script
from construction_pm.calendar_exception_repository import SQLiteCalendarExceptionRepository
from construction_pm.calendar_master_repository import SQLiteCalendarMasterRepository
from construction_pm.calendar_snapshot_repository import SQLiteCalendarSnapshotRepository
from construction_pm.calendar_work_hours_repository import SQLiteCalendarWorkHourRepository
from construction_pm.p6_baseline_repository import SQLiteP6BaselineRepository
from construction_pm.p6_cost_account_repository import SQLiteP6CostAccountRepository
from construction_pm.p6_expense_repository import SQLiteP6ExpenseRepository
from construction_pm.p6_resource_assignment_repository import (
    SQLiteP6ResourceAssignmentPeriodRepository,
    SQLiteP6ResourceAssignmentRepository,
)
from construction_pm.p6_resource_capacity_repository import SQLiteP6ResourceCapacityRepository
from construction_pm.p6_resource_spread_repository import SQLiteP6ResourceSpreadRepository
from construction_pm.resources.persistence import ContextScopedSQLiteResourceRepository
from construction_pm.p6_role_repository import P6Role, SQLiteP6RoleRepository
from construction_pm.project_schedule_settings_repository import SQLiteProjectScheduleSettingsRepository
from construction_pm.schedule_calculation_context_repository import SQLiteCalculationContextRepository
from construction_pm.schedule_input_snapshot_repository import SQLiteScheduleInputSnapshotRepository


REPOSITORIES = [
    pytest.param(SQLiteCalendarMasterRepository, id="calendar-master"),
    pytest.param(SQLiteCalendarExceptionRepository, id="calendar-exception"),
    pytest.param(SQLiteCalendarSnapshotRepository, id="calendar-snapshot"),
    pytest.param(SQLiteCalendarWorkHourRepository, id="calendar-work-hours"),
    pytest.param(SQLiteP6BaselineRepository, id="baseline"),
    pytest.param(SQLiteP6CostAccountRepository, id="cost-account"),
    pytest.param(SQLiteP6ExpenseRepository, id="expense"),
    pytest.param(SQLiteP6ResourceAssignmentRepository, id="resource-assignment"),
    pytest.param(SQLiteP6ResourceAssignmentPeriodRepository, id="resource-period"),
    pytest.param(SQLiteP6ResourceCapacityRepository, id="resource-capacity"),
    pytest.param(SQLiteP6ResourceSpreadRepository, id="resource-spread"),
    pytest.param(SQLiteP6RoleRepository, id="resource-role"),
    pytest.param(SQLiteProjectScheduleSettingsRepository, id="schedule-settings"),
    pytest.param(SQLiteCalculationContextRepository, id="calculation-context"),
    pytest.param(SQLiteScheduleInputSnapshotRepository, id="schedule-snapshot"),
    pytest.param(ContextScopedSQLiteResourceRepository, id="context-scoped-resources"),
]


@pytest.mark.parametrize("repository_type", REPOSITORIES)
def test_sqlite_repository_schema_initialization_preserves_caller_transaction(repository_type):
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE caller_state (value TEXT NOT NULL)")
    connection.execute("BEGIN IMMEDIATE")
    connection.execute("INSERT INTO caller_state(value) VALUES ('uncommitted')")

    repository_type(connection)

    assert connection.in_transaction, repository_type.__name__
    connection.rollback()
    assert connection.execute("SELECT value FROM caller_state").fetchall() == []
    connection.close()


def test_execute_sqlite_script_preserves_caller_transaction():
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE caller_state (value TEXT NOT NULL)")
    connection.execute("BEGIN IMMEDIATE")
    connection.execute("INSERT INTO caller_state(value) VALUES ('uncommitted')")

    execute_sqlite_script(
        connection,
        """
        CREATE TABLE first_table (id INTEGER PRIMARY KEY);
        CREATE TABLE second_table (id INTEGER PRIMARY KEY, first_id INTEGER);
        """,
    )

    assert connection.in_transaction
    connection.rollback()
    assert connection.execute("SELECT value FROM caller_state").fetchall() == []
    assert connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('first_table','second_table')"
    ).fetchall() == []
    connection.close()


def test_role_repository_save_participates_in_caller_transaction():
    connection = sqlite3.connect(":memory:")
    repository = SQLiteP6RoleRepository(connection)
    role = P6Role(
        tenant_id="tenant-1",
        project_id="project-1",
        project_revision=3,
        role_id="ROLE-1",
        name="Planner",
    )

    connection.execute("BEGIN IMMEDIATE")
    repository.save(role)
    assert connection.in_transaction
    connection.rollback()

    assert repository.get("tenant-1", "project-1", 3, "ROLE-1") is None
    connection.close()
