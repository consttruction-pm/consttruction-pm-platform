from datetime import date, datetime, timezone
import sqlite3

import pytest

from construction_pm.backend_p0.models import BackendScope

from construction_pm.schedule_input_snapshot_repository import (
    PostgresScheduleInputSnapshotRepository,
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


def test_snapshot_rejects_mismatched_calculation_context_tenant():
    with pytest.raises(ScheduleSnapshotPersistenceError, match="SNAPSHOT_CONTEXT_TENANT_MISMATCH"):
        build_snapshot(
            make_input(),
            CalculationContext(
                project_id="P-1",
                project_version=7,
                calendar_id="CAL-1",
                calendar_version="1",
                rules_version="rules-1",
                engine_version="engine-1",
                timezone="UTC",
                calculation_timestamp="2026-09-21T08:00:00+00:00",
                input_snapshot_id="S-1",
                tenant_id="T-OTHER",
            ),
            datetime(2026, 9, 21, 8, tzinfo=timezone.utc),
        )


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

    with pytest.raises(ScheduleSnapshotPersistenceError, match="INVALID_SNAPSHOT_TIMESTAMP"):
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


def test_snapshot_validate_rejects_non_string_snapshot_fields():
    snapshot = build_snapshot(
        make_input(), make_context(), datetime(2026, 9, 21, 8, tzinfo=timezone.utc)
    )
    for field_name, value, error_code in (
        ("snapshot_id", 123, "INVALID_SNAPSHOT_ID"),
        ("snapshot_hash", 123, "INVALID_SNAPSHOT_HASH"),
        ("calculation_identity", 123, "INVALID_CALCULATION_IDENTITY"),
    ):
        candidate = snapshot.__class__(
            **{**snapshot.__dict__, field_name: value}
        )
        with pytest.raises(ScheduleSnapshotPersistenceError, match=error_code):
            candidate.validate()


def test_snapshot_save_rejects_corrupt_existing_idempotent_row():
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

    with pytest.raises(ScheduleSnapshotPersistenceError, match="INVALID_SNAPSHOT_TIMESTAMP"):
        repo.save(snapshot)


def test_snapshot_rejects_invalid_canonical_payload_json():
    snapshot = build_snapshot(
        make_input(), make_context(), datetime(2026, 9, 21, 8, tzinfo=timezone.utc)
    )
    candidate = snapshot.__class__(
        **{**snapshot.__dict__, "canonical_payload": "{not-json"}
    )
    with pytest.raises(ScheduleSnapshotPersistenceError, match="INVALID_SNAPSHOT_PAYLOAD"):
        candidate.validate()


def test_snapshot_rejects_non_object_canonical_payload_json():
    snapshot = build_snapshot(
        make_input(), make_context(), datetime(2026, 9, 21, 8, tzinfo=timezone.utc)
    )
    candidate = snapshot.__class__(
        **{**snapshot.__dict__, "canonical_payload": "[]"}
    )
    with pytest.raises(ScheduleSnapshotPersistenceError, match="INVALID_SNAPSHOT_PAYLOAD"):
        candidate.validate()


def test_snapshot_rejects_non_hex_calculation_identity():
    snapshot = build_snapshot(
        make_input(), make_context(), datetime(2026, 9, 21, 8, tzinfo=timezone.utc)
    )
    candidate = snapshot.__class__(
        **{**snapshot.__dict__, "calculation_identity": "g" * 64}
    )
    with pytest.raises(ScheduleSnapshotPersistenceError, match="INVALID_CALCULATION_IDENTITY"):
        candidate.validate()


@pytest.fixture(scope="module")
def postgres_dsn():
    import os
    dsn = os.getenv("P6_TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("P6_TEST_POSTGRES_DSN is not configured")
    return dsn


@pytest.fixture()
def postgres_connection(postgres_dsn):
    psycopg = pytest.importorskip("psycopg")
    connection = psycopg.connect(postgres_dsn)
    try:
        repo = PostgresScheduleInputSnapshotRepository(connection)
        repo.initialize()
        connection.commit()
        connection.execute("TRUNCATE TABLE schedule_input_snapshot")
        connection.commit()
        yield connection
    finally:
        connection.rollback()
        connection.execute("TRUNCATE TABLE schedule_input_snapshot")
        connection.commit()
        connection.close()


def test_postgres_snapshot_save_get_list_and_idempotency(postgres_connection):
    repo = PostgresScheduleInputSnapshotRepository(postgres_connection)
    repo.initialize()
    postgres_connection.commit()
    snapshot = build_snapshot(
        make_input(), make_context(), datetime(2026, 9, 21, 8, tzinfo=timezone.utc)
    )

    with postgres_connection.transaction():
        assert repo.save(snapshot) == snapshot
        assert repo.save(snapshot) == snapshot

    scope = BackendScope("T-1", "P-1", 7)
    assert repo.get(scope, "S-1") == snapshot
    assert repo.list(scope) == (snapshot,)


def test_postgres_snapshot_rejects_same_id_with_different_payload(postgres_connection):
    repo = PostgresScheduleInputSnapshotRepository(postgres_connection)
    repo.initialize()
    postgres_connection.commit()
    snapshot = build_snapshot(
        make_input(), make_context(), datetime(2026, 9, 21, 8, tzinfo=timezone.utc)
    )
    with postgres_connection.transaction():
        repo.save(snapshot)

    changed_input = AuthoritativeScheduleInput(
        **{**make_input().__dict__, "project_finish": date(2026, 10, 1)}
    )
    changed = build_snapshot(
        changed_input, make_context(), datetime(2026, 9, 21, 8, tzinfo=timezone.utc)
    )
    with pytest.raises(
        ScheduleSnapshotPersistenceError, match="SNAPSHOT_IMMUTABLE_CONFLICT"
    ):
        with postgres_connection.transaction():
            repo.save(changed)


def test_postgres_snapshot_rejects_revision_conflict(postgres_connection):
    repo = PostgresScheduleInputSnapshotRepository(postgres_connection)
    repo.initialize()
    postgres_connection.commit()
    snapshot = build_snapshot(
        make_input(), make_context(), datetime(2026, 9, 21, 8, tzinfo=timezone.utc)
    )
    with postgres_connection.transaction():
        repo.save(snapshot)

    with pytest.raises(ScheduleSnapshotPersistenceError, match="REVISION_CONFLICT"):
        repo.get(BackendScope("T-1", "P-1", 8), "S-1")


def test_postgres_snapshot_rolls_back_uncommitted_save(postgres_connection):
    repo = PostgresScheduleInputSnapshotRepository(postgres_connection)
    repo.initialize()
    postgres_connection.commit()
    snapshot = build_snapshot(
        make_input("rollback"), make_context("rollback"),
        datetime(2026, 9, 21, 8, tzinfo=timezone.utc)
    )
    with pytest.raises(RuntimeError, match="force rollback"):
        with postgres_connection.transaction():
            repo.save(snapshot)
            raise RuntimeError("force rollback")

    assert repo.get(snapshot.scope, snapshot.snapshot_id) is None


def test_postgres_snapshot_list_rejects_corrupt_timestamp():
    snapshot = build_snapshot(
        make_input(), make_context(), datetime(2026, 9, 21, 8, tzinfo=timezone.utc)
    )

    class FakeResult:
        def fetchall(self):
            return [(
                snapshot.snapshot_id,
                snapshot.snapshot_hash,
                snapshot.canonical_payload,
                snapshot.calculation_identity,
                "not-a-timestamp",
                snapshot.record_revision,
            )]

    class FakeConnection:
        def execute(self, *_args):
            return FakeResult()

    from construction_pm.schedule_input_snapshot_repository import PostgresScheduleInputSnapshotRepository

    repo = PostgresScheduleInputSnapshotRepository(FakeConnection())
    with pytest.raises(ScheduleSnapshotPersistenceError, match="INVALID_SNAPSHOT_TIMESTAMP"):
        repo.list(BackendScope("T-1", "P-1", 7))


@pytest.mark.parametrize(
    ("column", "value", "error_code", "method"),
    [
        ("project_revision", "not-an-int", "INVALID_PROJECT_REVISION", "get"),
        ("record_revision", "not-an-int", "INVALID_RECORD_REVISION", "list"),
    ],
)
def test_sqlite_rejects_corrupt_persisted_integer_fields(column, value, error_code, method):
    snapshot = build_snapshot(
        make_input(), make_context(), datetime(2026, 9, 21, 8, tzinfo=timezone.utc)
    )
    connection = sqlite3.connect(":memory:")
    repo = SQLiteScheduleInputSnapshotRepository(connection)
    repo.save(snapshot)
    connection.execute(
        f"UPDATE schedule_input_snapshot SET {column}=? WHERE snapshot_id=?",
        (value, snapshot.snapshot_id),
    )
    connection.commit()

    with pytest.raises(ScheduleSnapshotPersistenceError, match=error_code):
        if method == "get":
            repo.get(BackendScope("T-1", "P-1", 7), "S-1")
        else:
            repo.list(BackendScope("T-1", "P-1", 7))


def test_postgres_list_rejects_corrupt_record_revision():
    snapshot = build_snapshot(
        make_input(), make_context(), datetime(2026, 9, 21, 8, tzinfo=timezone.utc)
    )

    class FakeResult:
        def fetchall(self):
            return [(
                snapshot.snapshot_id,
                snapshot.snapshot_hash,
                snapshot.canonical_payload,
                snapshot.calculation_identity,
                snapshot.created_at.isoformat(),
                "not-an-int",
            )]

    class FakeConnection:
        def execute(self, *_args):
            return FakeResult()

    repo = PostgresScheduleInputSnapshotRepository(FakeConnection())
    with pytest.raises(ScheduleSnapshotPersistenceError, match="INVALID_RECORD_REVISION"):
        repo.list(BackendScope("T-1", "P-1", 7))
