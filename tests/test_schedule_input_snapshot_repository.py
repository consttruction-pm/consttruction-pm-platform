from datetime import date, datetime, timezone
import sqlite3

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.schedule_input_snapshot_repository import (
    ScheduleSnapshotPersistenceError,
    SQLiteScheduleInputSnapshotRepository,
    build_snapshot,
)
from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.authoritative_schedule import (
    ActivityCalendarAssignment,
    AuthoritativeScheduleInput,
    AuthoritativeScheduleMode,
)
from construction_pm.scheduling.calculation_context import CalculationContext
from construction_pm.scheduling.calendar_context import CalendarReference
from construction_pm.scheduling.relationships import Relationship


def make_input(snapshot_id: str = "S-1"):
    cal = CalendarReference("CAL-1", "1")
    return AuthoritativeScheduleInput(
        snapshot_id=snapshot_id,
        tenant_id="T-1",
        project_id="P-1",
        project_revision=7,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=cal,
        activities=(Activity("A", 2), Activity("B", 1)),
        relationships=(Relationship("A", "B"),),
        activity_calendar_assignments=(
            ActivityCalendarAssignment("A", cal),
            ActivityCalendarAssignment("B", cal),
        ),
        project_start=date(2026, 9, 21),
    )


def make_context(snapshot_id: str = "S-1"):
    return CalculationContext(
        project_id="P-1",
        project_version=7,
        calendar_id="CAL-1",
        calendar_version="1",
        rules_version="rules-1",
        engine_version="engine-1",
        timezone="UTC",
        calculation_timestamp="2026-09-21T08:00:00+00:00",
        input_snapshot_id=snapshot_id,
        tenant_id="T-1",
    )


def test_build_and_round_trip_snapshot():
    snapshot = build_snapshot(make_input(), make_context(), datetime(2026, 9, 21, 8, tzinfo=timezone.utc))
    repo = SQLiteScheduleInputSnapshotRepository(sqlite3.connect(":memory:"))
    assert repo.save(snapshot) == snapshot
    assert repo.get(BackendScope("T-1", "P-1", 7), "S-1") == snapshot


def test_snapshot_is_immutable_and_idempotent_for_same_content():
    snapshot = build_snapshot(make_input(), make_context(), datetime(2026, 9, 21, 8, tzinfo=timezone.utc))
    repo = SQLiteScheduleInputSnapshotRepository(sqlite3.connect(":memory:"))
    assert repo.save(snapshot) == snapshot
    assert repo.save(snapshot) == snapshot
    changed = build_snapshot(make_input("S-1"), make_context("S-1"), datetime(2026, 9, 21, 9, tzinfo=timezone.utc))
    # timestamp is outside canonical schedule payload, so the snapshot identity remains the same.
    assert repo.save(changed) == snapshot


def test_snapshot_rejects_same_id_with_different_payload():
    snapshot = build_snapshot(make_input(), make_context(), datetime(2026, 9, 21, 8, tzinfo=timezone.utc))
    repo = SQLiteScheduleInputSnapshotRepository(sqlite3.connect(":memory:"))
    repo.save(snapshot)
    changed_input = make_input()
    changed_input = AuthoritativeScheduleInput(
        **{**changed_input.__dict__, "project_finish": date(2026, 10, 1)}
    )
    changed = build_snapshot(changed_input, make_context(), datetime(2026, 9, 21, 8, tzinfo=timezone.utc))
    with pytest.raises(ScheduleSnapshotPersistenceError, match="SNAPSHOT_IMMUTABLE_CONFLICT"):
        repo.save(changed)


def test_snapshot_requires_matching_calculation_context():
    with pytest.raises(ScheduleSnapshotPersistenceError, match="SNAPSHOT_CONTEXT_ID_MISMATCH"):
        build_snapshot(make_input("S-1"), make_context("S-2"), datetime(2026, 9, 21, 8, tzinfo=timezone.utc))


def test_snapshot_list_validates_persisted_rows():
    snapshot = build_snapshot(
        make_input(), make_context(), datetime(2026, 9, 21, 8, tzinfo=timezone.utc)
    )
    connection = sqlite3.connect(":memory:")
    repo = SQLiteScheduleInputSnapshotRepository(connection)
    repo.save(snapshot)

    connection.execute(
        "UPDATE schedule_input_snapshot SET created_at=? WHERE snapshot_id=?",
        ("not-a-timestamp", snapshot.snapshot_id),
    )
    connection.commit()

    with pytest.raises(ValueError):
        repo.list(BackendScope("T-1", "P-1", 7))


def test_snapshot_rejects_payload_hash_mismatch():
    snapshot = build_snapshot(
        make_input(), make_context(), datetime(2026, 9, 21, 8, tzinfo=timezone.utc)
    )
    connection = sqlite3.connect(":memory:")
    repo = SQLiteScheduleInputSnapshotRepository(connection)
    repo.save(snapshot)

    connection.execute(
        "UPDATE schedule_input_snapshot SET canonical_payload=? WHERE snapshot_id=?",
        (snapshot.canonical_payload + " ", snapshot.snapshot_id),
    )
    connection.commit()

    with pytest.raises(ScheduleSnapshotPersistenceError, match="SNAPSHOT_HASH_MISMATCH"):
        repo.get(BackendScope("T-1", "P-1", 7), "S-1")


@pytest.mark.parametrize("snapshot_id", [None, "", "   ", 123])
def test_snapshot_get_rejects_invalid_snapshot_id(snapshot_id):
    repo = SQLiteScheduleInputSnapshotRepository(sqlite3.connect(":memory:"))
    with pytest.raises(ScheduleSnapshotPersistenceError, match="INVALID_SNAPSHOT_ID"):
        repo.get(BackendScope("T-1", "P-1", 7), snapshot_id)
