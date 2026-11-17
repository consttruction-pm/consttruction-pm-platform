from datetime import datetime, timezone
import hashlib
import sqlite3
from contextlib import nullcontext

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.delay_analysis.baseline_snapshot_binding import (
    BaselineScheduleSnapshotBindingError,
    P6BaselineScheduleSnapshotBinding,
    P6BaselineScheduleSnapshotBindingService,
    SQLiteP6BaselineScheduleSnapshotBindingRepository,
)
from construction_pm.p6_baseline_repository import (
    P6Baseline,
    SQLiteP6BaselineRepository,
)
from construction_pm.schedule_input_snapshot_repository import (
    ScheduleInputSnapshot,
    SQLiteScheduleInputSnapshotRepository,
)


class _TransactionManager:
    def transaction(self):
        return nullcontext()


def scope(revision: int = 7) -> BackendScope:
    return BackendScope("tenant-a", "project-a", revision)


def snapshot(source_revision: int = 3, snapshot_id: str = "S-BASE") -> ScheduleInputSnapshot:
    payload = "{}"
    return ScheduleInputSnapshot(
        scope=BackendScope("tenant-a", "project-a", source_revision),
        snapshot_id=snapshot_id,
        snapshot_hash=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        canonical_payload=payload,
        calculation_identity="b" * 64,
        created_at=datetime(2026, 10, 1, 8, tzinfo=timezone.utc),
    )


def seed(connection):
    baseline_repository = SQLiteP6BaselineRepository(connection)
    snapshot_repository = SQLiteScheduleInputSnapshotRepository(connection)
    binding_repository = SQLiteP6BaselineScheduleSnapshotBindingRepository(connection)
    baseline = P6Baseline(
        scope(), "B-1", "Approved Baseline", "PRIMARY", 3,
        "2026-10-01T08:00:00Z",
    )
    baseline_repository.upsert(baseline)
    stored_snapshot = snapshot()
    snapshot_repository.save(stored_snapshot)
    service = P6BaselineScheduleSnapshotBindingService(
        baseline_repository,
        snapshot_repository,
        binding_repository,
        _TransactionManager(),
    )
    return baseline, stored_snapshot, service, binding_repository


def test_baseline_binding_resolves_exact_immutable_schedule_snapshot():
    connection = sqlite3.connect(":memory:")
    baseline, stored_snapshot, service, binding_repository = seed(connection)

    binding = service.bind(scope(), baseline.baseline_id, stored_snapshot.snapshot_id)

    assert binding.baseline_id == baseline.baseline_id
    assert binding.source_revision == baseline.source_revision
    assert binding.snapshot_hash == stored_snapshot.snapshot_hash
    assert service.resolve(scope(), baseline.baseline_id) == stored_snapshot
    assert binding_repository.get(scope(), baseline.baseline_id) == binding


def test_binding_is_idempotent_but_cannot_be_repointed():
    connection = sqlite3.connect(":memory:")
    baseline, stored_snapshot, service, _ = seed(connection)

    first = service.bind(scope(), baseline.baseline_id, stored_snapshot.snapshot_id)
    assert service.bind(scope(), baseline.baseline_id, stored_snapshot.snapshot_id) == first

    second_snapshot = snapshot(snapshot_id="S-OTHER")
    service.snapshot_repository.save(second_snapshot)
    with pytest.raises(
        BaselineScheduleSnapshotBindingError,
        match="IMMUTABLE_BASELINE_SNAPSHOT_BINDING",
    ):
        service.bind(scope(), baseline.baseline_id, second_snapshot.snapshot_id)


def test_binding_requires_existing_baseline_and_exact_source_revision_snapshot():
    connection = sqlite3.connect(":memory:")
    baseline, stored_snapshot, service, _ = seed(connection)

    with pytest.raises(BaselineScheduleSnapshotBindingError, match="BASELINE_NOT_FOUND"):
        service.bind(scope(), "MISSING", stored_snapshot.snapshot_id)

    wrong_revision = snapshot(source_revision=2, snapshot_id="S-WRONG-REV")
    service.snapshot_repository.save(wrong_revision)
    with pytest.raises(
        BaselineScheduleSnapshotBindingError,
        match="BASELINE_SOURCE_SNAPSHOT_NOT_FOUND",
    ):
        service.bind(scope(), baseline.baseline_id, wrong_revision.snapshot_id)


def test_binding_database_foreign_keys_require_parent_records():
    connection = sqlite3.connect(":memory:")
    _, _, _, repository = seed(connection)
    connection.execute("DELETE FROM p6_baseline WHERE baseline_id='B-1'")
    connection.commit()
    binding = P6BaselineScheduleSnapshotBinding(
        scope(), "B-1", 3, "S-BASE", hashlib.sha256(b"{}").hexdigest(), "b" * 64
    )
    with pytest.raises(
        BaselineScheduleSnapshotBindingError,
        match="BASELINE_OR_SCHEDULE_SNAPSHOT_REQUIRED",
    ):
        repository.save(binding)


def test_binding_read_is_scope_isolated_and_revision_pinned():
    connection = sqlite3.connect(":memory:")
    baseline, stored_snapshot, service, repository = seed(connection)
    service.bind(scope(), baseline.baseline_id, stored_snapshot.snapshot_id)

    assert repository.get(BackendScope("tenant-b", "project-a", 7), "B-1") is None
    assert repository.get(BackendScope("tenant-a", "project-b", 7), "B-1") is None
    with pytest.raises(BaselineScheduleSnapshotBindingError, match="REVISION_CONFLICT"):
        repository.get(scope(8), "B-1")


def test_binding_record_rejects_invalid_hashes_and_source_revision():
    binding = P6BaselineScheduleSnapshotBinding(
        scope(), "B-1", 3, "S-1", "not-a-hash", "b" * 64
    )
    with pytest.raises(BaselineScheduleSnapshotBindingError, match="INVALID_SNAPSHOT_HASH"):
        binding.validate()
    binding = P6BaselineScheduleSnapshotBinding(
        scope(), "B-1", -1, "S-1", "a" * 64, "b" * 64
    )
    with pytest.raises(BaselineScheduleSnapshotBindingError, match="INVALID_SOURCE_REVISION"):
        binding.validate()


@pytest.fixture(scope="module")
def postgres_dsn():
    import os
    value = os.getenv("P6_TEST_POSTGRES_DSN")
    if not value:
        pytest.skip("P6_TEST_POSTGRES_DSN is not configured")
    return value


def test_postgres_binding_round_trip(postgres_dsn):
    psycopg = pytest.importorskip("psycopg")
    connection = psycopg.connect(postgres_dsn)
    try:
        from construction_pm.p6_baseline_repository import PostgresP6BaselineRepository
        from construction_pm.schedule_input_snapshot_repository import PostgresScheduleInputSnapshotRepository
        from construction_pm.delay_analysis.baseline_snapshot_binding import PostgresP6BaselineScheduleSnapshotBindingRepository

        baseline_repository = PostgresP6BaselineRepository(connection)
        baseline_repository.initialize()
        snapshot_repository = PostgresScheduleInputSnapshotRepository(connection)
        snapshot_repository.initialize()
        binding_repository = PostgresP6BaselineScheduleSnapshotBindingRepository(connection)
        binding_repository.initialize()

        unique = str(__import__("uuid").uuid4())
        project_scope = BackendScope("tenant-" + unique, "project-" + unique, 7)
        baseline = P6Baseline(
            project_scope, "B-" + unique, "Approved", "PRIMARY", 3,
            "2026-10-01T08:00:00Z",
        )
        baseline_repository.upsert(baseline)
        stored_snapshot = ScheduleInputSnapshot(
            BackendScope(project_scope.tenant_id, project_scope.project_id, 3),
            "S-" + unique,
            hashlib.sha256(b"{}").hexdigest(),
            "{}",
            "b" * 64,
            datetime(2026, 10, 1, 8, tzinfo=timezone.utc),
        )
        snapshot_repository.save(stored_snapshot)
        binding = P6BaselineScheduleSnapshotBinding(
            project_scope, baseline.baseline_id, 3, stored_snapshot.snapshot_id,
            stored_snapshot.snapshot_hash, stored_snapshot.calculation_identity,
        )
        assert binding_repository.save(binding) == binding
        assert binding_repository.get(project_scope, baseline.baseline_id) == binding
        connection.commit()
    finally:
        connection.rollback()
        connection.close()
