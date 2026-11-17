from datetime import datetime, timezone
from types import SimpleNamespace
import hashlib
import json
import sqlite3

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.delay_analysis.schedule_run_capture import (
    ScheduleRunCaptureError,
    SQLiteScheduleRunCaptureRepository,
    build_schedule_run_capture,
)
from construction_pm.schedule_input_snapshot_repository import ScheduleInputSnapshot
from construction_pm.scheduling.calculation_context import CalculationContext


def make_inputs():
    scope = BackendScope("tenant-a", "project-a", 7)
    context = CalculationContext(
        project_id="project-a",
        project_version=7,
        calendar_id="calendar-a",
        calendar_version="v3",
        rules_version="p6-v26",
        engine_version="shared-core-1.4",
        timezone="UTC",
        calculation_timestamp="2026-11-18T00:00:00+00:00",
        input_snapshot_id="snapshot-a",
        tenant_id="tenant-a",
    )
    payload = json.dumps(
        {
            "schedule_options": {"mode": "EARLIEST", "data_date": "2026-11-01"},
            "project_calendar": {"calendar_id": "project-calendar", "version": "3"},
            "activity_calendar_assignments": [],
            "relationship_lag_calendar_assignments": [],
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    snapshot = ScheduleInputSnapshot(
        scope=scope,
        snapshot_id="snapshot-a",
        snapshot_hash=hashlib.sha256(payload.encode()).hexdigest(),
        canonical_payload=payload,
        calculation_identity=context.calculation_identity,
        created_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
    )
    evaluation = SimpleNamespace(
        snapshot_id=snapshot.snapshot_id,
        snapshot_hash=snapshot.snapshot_hash,
        calculation_identity=snapshot.calculation_identity,
        calculation_run_identity="c" * 64,
        project_id="project-a",
        project_revision=7,
        mode="DATE_BASED",
        date_result=None,
        time_result=None,
        time_activities={"A-1": {"start": "2026-11-01", "finish": "2026-12-01"}},
        resource_dependent_placement=None,
        diagnostics=(),
        schedule_check_findings=(),
        project_finish=datetime(2026, 12, 1, tzinfo=timezone.utc),
    )
    return snapshot, context, evaluation


def test_capture_binds_exact_snapshot_context_and_authoritative_evaluation():
    snapshot, context, evaluation = make_inputs()
    capture = build_schedule_run_capture(
        snapshot, context, evaluation,
        captured_at=datetime(2026, 11, 18, tzinfo=timezone.utc),
    )

    assert capture.snapshot_hash == snapshot.snapshot_hash
    assert capture.calculation_identity == context.calculation_identity
    assert capture.engine_version == context.engine_version
    assert capture.project_finish.startswith("2026-12-01")
    assert capture.validate() is None
    log = json.loads(capture.log_envelope_json)
    assert log["native_p6_log_parity"] == "PARTIAL"
    assert "native_scheduler_errors" in log["unavailable_native_sections"]


def test_capture_fails_closed_on_snapshot_or_context_mismatch():
    snapshot, context, evaluation = make_inputs()
    bad_evaluation = SimpleNamespace(**{
        **evaluation.__dict__,
        "snapshot_hash": "d" * 64,
    })
    with pytest.raises(ScheduleRunCaptureError, match="EVALUATION_SNAPSHOT_MISMATCH"):
        build_schedule_run_capture(
            snapshot, context, bad_evaluation,
            captured_at=datetime(2026, 11, 18, tzinfo=timezone.utc),
        )


def test_capture_requires_timezone_aware_capture_timestamp():
    snapshot, context, evaluation = make_inputs()
    with pytest.raises(ScheduleRunCaptureError, match="INVALID_CAPTURE_TIMESTAMP"):
        build_schedule_run_capture(
            snapshot, context, evaluation,
            captured_at=datetime(2026, 11, 18),
        )


def test_capture_requires_help_relevant_settings_and_calendar_provenance():
    snapshot, context, evaluation = make_inputs()
    broken_payload = "{}"
    broken_snapshot = ScheduleInputSnapshot(
        scope=snapshot.scope,
        snapshot_id=snapshot.snapshot_id,
        snapshot_hash=hashlib.sha256(broken_payload.encode()).hexdigest(),
        canonical_payload=broken_payload,
        calculation_identity=snapshot.calculation_identity,
        created_at=snapshot.created_at,
    )
    with pytest.raises(ScheduleRunCaptureError, match="SCHEDULE_SNAPSHOT_MISSING_SCHEDULE_OPTIONS"):
        build_schedule_run_capture(
            broken_snapshot, context, evaluation,
            captured_at=datetime(2026, 11, 18, tzinfo=timezone.utc),
        )


def test_sqlite_capture_repository_is_immutable_and_scope_isolated():
    snapshot, context, evaluation = make_inputs()
    capture = build_schedule_run_capture(
        snapshot, context, evaluation,
        captured_at=datetime(2026, 11, 18, tzinfo=timezone.utc),
    )
    connection = sqlite3.connect(":memory:")
    repository = SQLiteScheduleRunCaptureRepository(connection)

    assert repository.save(capture) == capture
    assert repository.save(capture) == capture
    assert repository.get(snapshot.scope, capture.run_id) == capture
    assert repository.get(BackendScope("tenant-b", "project-a", 7), capture.run_id) is None
    with pytest.raises(ScheduleRunCaptureError, match="REVISION_CONFLICT"):
        repository.get(BackendScope("tenant-a", "project-a", 8), capture.run_id)


def test_sqlite_capture_rejects_same_run_identity_with_different_payload():
    snapshot, context, evaluation = make_inputs()
    captured_at = datetime(2026, 11, 18, tzinfo=timezone.utc)
    capture = build_schedule_run_capture(
        snapshot, context, evaluation, captured_at=captured_at,
    )
    changed = build_schedule_run_capture(
        snapshot, context, evaluation,
        captured_at=datetime(2026, 11, 18, 1, tzinfo=timezone.utc),
    )
    repository = SQLiteScheduleRunCaptureRepository(sqlite3.connect(":memory:"))
    repository.save(capture)

    with pytest.raises(ScheduleRunCaptureError, match="IMMUTABLE_SCHEDULE_RUN_CAPTURE_CONFLICT"):
        repository.save(changed)



@pytest.fixture(scope="module")
def postgres_dsn():
    import os
    value = os.getenv("P6_TEST_POSTGRES_DSN")
    if not value:
        pytest.skip("P6_TEST_POSTGRES_DSN is not configured")
    return value


def test_postgres_capture_repository_round_trip(postgres_dsn):
    psycopg = pytest.importorskip("psycopg")
    from construction_pm.delay_analysis.schedule_run_capture import (
        PostgresScheduleRunCaptureRepository,
    )

    snapshot, context, evaluation = make_inputs()
    capture = build_schedule_run_capture(
        snapshot, context, evaluation,
        captured_at=datetime(2026, 11, 18, tzinfo=timezone.utc),
    )
    connection = psycopg.connect(postgres_dsn)
    try:
        repository = PostgresScheduleRunCaptureRepository(connection)
        repository.initialize()
        assert repository.save(capture) == capture
        assert repository.get(snapshot.scope, capture.run_id) == capture
    finally:
        connection.rollback()
        connection.close()
