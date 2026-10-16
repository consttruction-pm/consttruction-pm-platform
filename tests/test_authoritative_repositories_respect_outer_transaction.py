from datetime import date, datetime, timezone
from decimal import Decimal
import sqlite3

import pytest

from construction_pm.activity_master_repository import ActivityMaster, SQLiteActivityMasterRepository
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.constraint_master_repository import ConstraintMaster, SQLiteConstraintMasterRepository
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
