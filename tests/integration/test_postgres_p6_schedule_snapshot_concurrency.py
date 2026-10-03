import hashlib
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier

import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
if not DSN:
    pytest.skip("CONSTRUCTION_PM_POSTGRES_DSN is not configured", allow_module_level=True)

from construction_pm.backend_p0.models import BackendScope
from construction_pm.schedule_input_snapshot_repository import (
    PostgresScheduleInputSnapshotRepository,
    ScheduleInputSnapshot,
)


def make_snapshot(suffix: str) -> ScheduleInputSnapshot:
    scope = BackendScope("concurrent-snapshot-tenant", f"snapshot-project-{suffix}", 7)
    payload = '{"snapshot":"concurrent"}'
    return ScheduleInputSnapshot(
        scope=scope,
        snapshot_id=f"snap-{suffix}",
        snapshot_hash=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        canonical_payload=payload,
        calculation_identity="b" * 64,
        created_at=datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc),
    )


def test_schedule_snapshot_live_concurrent_identical_upsert_is_idempotent() -> None:
    suffix = uuid.uuid4().hex
    snapshot = make_snapshot(suffix)
    barrier = Barrier(2)

    # Initialize the schema once, outside the concurrent workers. Running
    # CREATE TABLE IF NOT EXISTS concurrently can race in PostgreSQL's
    # catalog and fail before either worker reaches the synchronization point.
    with psycopg.connect(DSN) as connection:
        PostgresScheduleInputSnapshotRepository(connection).initialize()
        connection.commit()

    def worker() -> ScheduleInputSnapshot:
        with psycopg.connect(DSN) as connection:
            repository = PostgresScheduleInputSnapshotRepository(connection)
            barrier.wait()
            return repository.save(snapshot)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: worker(), range(2)))

    assert results == [snapshot, snapshot]

    with psycopg.connect(DSN) as connection:
        repository = PostgresScheduleInputSnapshotRepository(connection)
        assert repository.list(snapshot.scope) == (snapshot,)