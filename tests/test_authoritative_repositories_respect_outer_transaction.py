from datetime import date, datetime, timezone
from decimal import Decimal
import sqlite3

import pytest

from construction_pm.activity_master_repository import ActivityMaster, ActivityPersistenceError, SQLiteActivityMasterRepository
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.constraint_master_repository import ConstraintMaster, SQLiteConstraintMasterRepository
from construction_pm.relationship_master_repository import RelationshipMaster, SQLiteRelationshipMasterRepository
from construction_pm.schedule_calculation_context_repository import (
    SQLiteCalculationContextRepository,
    build_persisted_context,
)
from construction_pm.schedule_input_snapshot_repository import (
    SQLiteScheduleInputSnapshotRepository,
    build_snapshot,
)
from construction_pm.scheduling.activity import Activity, PercentCompleteType
from construction_pm.scheduling.authoritative_schedule import (
    ActivityCalendarAssignment,
    AuthoritativeScheduleInput,
    AuthoritativeScheduleMode,
)
from construction_pm.scheduling.calculation_context import CalculationContext
from construction_pm.scheduling.calendar_context import CalendarReference
from construction_pm.scheduling.constraints import ConstraintType
from construction_pm.scheduling.time_duration import DurationUnit


def _scope() -> BackendScope:
    return BackendScope("T-1", "P-1", 7)


def _snapshot():
    calendar = CalendarReference("CAL-1", "1")
    schedule_input = AuthoritativeScheduleInput(
        snapshot_id="S-1",
        tenant_id="T-1",
        project_id="P-1",
        project_revision=7,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=calendar,
        activities=(Activity("A-1", 2),),
        relationships=(),
        activity_calendar_assignments=(ActivityCalendarAssignment("A-1", calendar),),
        project_start=date(2026, 9, 21),
    )
    context = CalculationContext(
        project_id="P-1",
        project_version=7,
        calendar_id="CAL-1",
        calendar_version="1",
        rules_version="rules-1",
        engine_version="engine-1",
        timezone="UTC",
        calculation_timestamp="2026-09-21T08:00:00+00:00",
        input_snapshot_id="S-1",
        tenant_id="T-1",
    )
    return build_snapshot(schedule_input, context, datetime(2026, 9, 21, 8, tzinfo=timezone.utc))


def test_activity_constraint_and_snapshot_writes_rollback_with_outer_transaction():
    connection = sqlite3.connect(":memory:")
    activities = SQLiteActivityMasterRepository(connection)
    constraints = SQLiteConstraintMasterRepository(connection)
    snapshots = SQLiteScheduleInputSnapshotRepository(connection)
    scope = _scope()

    with pytest.raises(RuntimeError, match="injected failure"):
        with SQLiteTransactionManager(connection).transaction():
            activities.save(
                ActivityMaster(scope, "A-1", Decimal("2"), DurationUnit.WORKING_DAY)
            )
            constraints.save(
                ConstraintMaster(
                    scope,
                    "C-1",
                    "A-1",
                    ConstraintType.START_NO_EARLIER_THAN,
                    date(2026, 9, 21),
                )
            )
            snapshots.save(_snapshot())
            raise RuntimeError("injected failure")

    assert activities.get(scope, "A-1") is None
    assert constraints.get(scope, "C-1") is None
    assert snapshots.get(scope, "S-1") is None


def test_activity_constraint_and_snapshot_writes_commit_with_outer_transaction():
    connection = sqlite3.connect(":memory:")
    activities = SQLiteActivityMasterRepository(connection)
    constraints = SQLiteConstraintMasterRepository(connection)
    snapshots = SQLiteScheduleInputSnapshotRepository(connection)
    scope = _scope()

    with SQLiteTransactionManager(connection).transaction():
        activities.save(
            ActivityMaster(scope, "A-1", Decimal("2"), DurationUnit.WORKING_DAY)
        )
        constraints.save(
            ConstraintMaster(
                scope,
                "C-1",
                "A-1",
                ConstraintType.START_NO_EARLIER_THAN,
                date(2026, 9, 21),
            )
        )
        snapshots.save(_snapshot())

    assert activities.get(scope, "A-1") is not None
    assert constraints.get(scope, "C-1") is not None
    assert snapshots.get(scope, "S-1") is not None

def test_repository_initialization_preserves_caller_owned_transaction():
    connection = sqlite3.connect(":memory:")
    connection.execute("BEGIN IMMEDIATE")

    SQLiteActivityMasterRepository(connection)
    SQLiteConstraintMasterRepository(connection)
    SQLiteScheduleInputSnapshotRepository(connection)

    assert connection.in_transaction
    connection.rollback()
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert not {
        "activity_master",
        "constraint_master",
        "schedule_input_snapshot",
    } & tables


def test_relationship_and_calculation_context_writes_rollback_with_outer_transaction():
    connection = sqlite3.connect(":memory:")
    relationships = SQLiteRelationshipMasterRepository(connection)
    contexts = SQLiteCalculationContextRepository(connection)
    scope = _scope()
    context = CalculationContext(
        project_id="P-1",
        project_version=7,
        calendar_id="CAL-1",
        calendar_version="1",
        rules_version="rules-1",
        engine_version="engine-1",
        timezone="UTC",
        calculation_timestamp="2026-09-21T08:00:00+00:00",
        input_snapshot_id="S-2",
        tenant_id="T-1",
    )
    persisted_context = build_persisted_context(scope, context)

    with pytest.raises(RuntimeError, match="injected failure"):
        with SQLiteTransactionManager(connection).transaction():
            relationships.save(RelationshipMaster(scope, "REL-1", "A-1", "B-1"))
            contexts.save(persisted_context)
            raise RuntimeError("injected failure")

    assert relationships.get(scope, "REL-1") is None
    assert contexts.get(scope, "S-2") is None


def test_relationship_and_calculation_context_initialization_preserve_outer_transaction():
    connection = sqlite3.connect(":memory:")
    connection.execute("BEGIN IMMEDIATE")

    SQLiteRelationshipMasterRepository(connection)
    SQLiteCalculationContextRepository(connection)

    assert connection.in_transaction
    connection.rollback()
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert not {"relationship_master", "schedule_calculation_context"} & tables

def test_revision_conflict_does_not_rollback_prior_caller_owned_write():
    connection = sqlite3.connect(":memory:")
    activities = SQLiteActivityMasterRepository(connection)
    scope = _scope()
    activities.save(
        ActivityMaster(scope, "A-1", Decimal("2"), DurationUnit.WORKING_DAY)
    )
    # Force the optimistic UPDATE to affect zero rows after the repository has
    # read revision 1. This reaches the rowcount-conflict rollback path.
    connection.execute(
        """
        CREATE TRIGGER ignore_activity_master_update
        BEFORE UPDATE ON activity_master
        WHEN OLD.activity_id = 'A-1'
        BEGIN
            SELECT RAISE(IGNORE);
        END
        """
    )
    connection.commit()

    with SQLiteTransactionManager(connection).transaction():
        activities.save(
            ActivityMaster(scope, "A-2", Decimal("3"), DurationUnit.WORKING_DAY)
        )
        with pytest.raises(ActivityPersistenceError, match="REVISION_CONFLICT"):
            activities.save(
                ActivityMaster(scope, "A-1", Decimal("4"), DurationUnit.WORKING_DAY),
                expected_revision=1,
            )
        # A repository must not roll back the application-owned transaction
        # when its own optimistic update loses a race.
        assert connection.in_transaction
        assert activities.get(scope, "A-2") is not None

    assert activities.get(scope, "A-2") is not None
    assert activities.get(scope, "A-1").duration_value == Decimal("2")

def test_activity_master_schema_migration_stays_inside_caller_transaction():
    connection = sqlite3.connect(":memory:")
    connection.execute(
        """CREATE TABLE activity_master (
            tenant_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            project_revision INTEGER NOT NULL,
            activity_id TEXT NOT NULL,
            duration_value TEXT NOT NULL,
            duration_unit TEXT NOT NULL,
            actual_start TEXT,
            actual_finish TEXT,
            remaining_duration INTEGER,
            remaining_start TEXT,
            percent_complete REAL,
            percent_complete_type TEXT NOT NULL DEFAULT 'DURATION',
            record_revision INTEGER NOT NULL,
            expected_finish TEXT,
            PRIMARY KEY (tenant_id, project_id, activity_id)
        )"""
    )
    connection.commit()

    connection.execute("BEGIN")
    repo = SQLiteActivityMasterRepository(connection)
    assert connection.in_transaction
    columns_during_transaction = {
        row[1]
        for row in connection.execute("PRAGMA table_info(activity_master)").fetchall()
    }
    assert {"planned_finish", "leveling_priority", "original_duration"} <= columns_during_transaction

    connection.rollback()
    columns_after_rollback = {
        row[1]
        for row in connection.execute("PRAGMA table_info(activity_master)").fetchall()
    }
    assert not {"planned_finish", "leveling_priority", "original_duration"} & columns_after_rollback

