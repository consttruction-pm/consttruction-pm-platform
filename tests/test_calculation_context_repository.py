from datetime import date, datetime, timezone
import sqlite3

import pytest

from construction_pm.calculation_context_repository import (
    CalculationContextPersistenceError,
    SQLiteCalculationContextRepository,
    resolve_authoritative_context,
    resolve_context_for_replay,
)
from construction_pm.schedule_input_snapshot_repository import (
    SQLiteScheduleInputSnapshotRepository,
    build_snapshot,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.authoritative_schedule import (
    AuthoritativeScheduleInput,
    AuthoritativeScheduleMode,
)
from construction_pm.scheduling.calendar_context import CalendarReference
from construction_pm.scheduling.calculation_context import CalculationContext
from construction_pm.scheduling.relationships import Relationship


def make_context(**changes):
    values = dict(
        project_id="P-1",
        project_version=7,
        calendar_id="CAL-1",
        calendar_version="1",
        rules_version="rules-1",
        engine_version="engine-1",
        timezone="UTC",
        calculation_timestamp="2026-10-08T00:00:00+00:00",
        input_snapshot_id="SNAP-1",
        tenant_id="T-1",
        actor_id="actor-1",
        request_id="req-1",
        idempotency_key="idem-1",
    )
    values.update(changes)
    return CalculationContext(**values)


def make_snapshot(context):
    source = AuthoritativeScheduleInput(
        snapshot_id=context.input_snapshot_id,
        tenant_id=context.tenant_id,
        project_id=context.project_id,
        project_revision=context.project_version,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=CalendarReference(context.calendar_id, context.calendar_version),
        activities=(Activity("A", 1),),
        relationships=(),
        activity_calendar_assignments=(),
        project_start=date(2026, 10, 8),
    )
    return build_snapshot(
        source,
        context,
        datetime(2026, 10, 8, tzinfo=timezone.utc),
    )


def test_sqlite_context_round_trip_preserves_all_authoritative_fields():
    repo = SQLiteCalculationContextRepository(sqlite3.connect(":memory:"))
    context = make_context()
    repo.save(context)

    restored = repo.get(
        BackendScope("T-1", "P-1", 7),
        "SNAP-1",
    )

    assert restored is not None
    assert restored.to_dict() == context.to_dict()
    assert restored.calculation_identity == context.calculation_identity


def test_sqlite_context_is_immutable():
    repo = SQLiteCalculationContextRepository(sqlite3.connect(":memory:"))
    repo.save(make_context())

    with pytest.raises(
        CalculationContextPersistenceError,
        match="IMMUTABLE_CONFLICT",
    ):
        repo.save(make_context(calendar_version="2"))


def test_scope_mismatch_is_rejected():
    repo = SQLiteCalculationContextRepository(sqlite3.connect(":memory:"))

    with pytest.raises(CalculationContextPersistenceError, match="CONTEXT_SCOPE_MISMATCH"):
        repo.save(make_context(project_version=8))


def test_replay_requires_identity_match():
    context = make_context()
    snapshot = make_snapshot(context)
    changed = make_context(calendar_version="2")

    with pytest.raises(CalculationContextPersistenceError, match="CALCULATION_IDENTITY_MISMATCH"):
        resolve_authoritative_context(snapshot, changed)


def test_replay_resolves_persisted_context_without_client_metadata():
    connection = sqlite3.connect(":memory:")
    context_repo = SQLiteCalculationContextRepository(connection)
    snapshot_repo = SQLiteScheduleInputSnapshotRepository(connection)
    context = make_context()
    snapshot = make_snapshot(context)
    snapshot_repo.save(snapshot)
    context_repo.save(context)

    restored_snapshot, restored_context = resolve_context_for_replay(
        snapshot_repo,
        context_repo,
        BackendScope("T-1", "P-1", 7),
        "SNAP-1",
    )

    assert restored_snapshot.snapshot_id == "SNAP-1"
    assert restored_context.calculation_identity == snapshot.calculation_identity
    assert restored_context.calendar_id == "CAL-1"
    assert restored_context.rules_version == "rules-1"
    assert restored_context.engine_version == "engine-1"


def test_replay_fails_when_persisted_context_is_missing():
    connection = sqlite3.connect(":memory:")
    snapshot_repo = SQLiteScheduleInputSnapshotRepository(connection)
    context = make_context()
    snapshot_repo.save(make_snapshot(context))

    with pytest.raises(CalculationContextPersistenceError, match="CONTEXT_NOT_FOUND"):
        resolve_context_for_replay(
            snapshot_repo,
            SQLiteCalculationContextRepository(connection),
            BackendScope("T-1", "P-1", 7),
            "SNAP-1",
        )
