import hashlib
import os
import uuid
from datetime import datetime, timezone

import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
if not DSN:
    pytest.skip("CONSTRUCTION_PM_POSTGRES_DSN is not configured", allow_module_level=True)

from construction_pm.backend_p0.models import BackendScope
from construction_pm.schedule_input_snapshot_repository import (
    PostgresScheduleInputSnapshotRepository,
    ScheduleInputSnapshot,
    ScheduleSnapshotPersistenceError,
)


def make_snapshot(suffix: str, *, tenant_id: str = "live-tenant") -> ScheduleInputSnapshot:
    scope = BackendScope(tenant_id, f"snapshot-project-{suffix}", 7)
    payload = '{"project_id":"' + scope.project_id + '","snapshot_id":"snap-' + suffix + '"}'
    return ScheduleInputSnapshot(
        scope=scope,
        snapshot_id=f"snap-{suffix}",
        snapshot_hash=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        canonical_payload=payload,
        calculation_identity="a" * 64,
        created_at=datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc),
    )


def test_schedule_snapshot_live_round_trip_replay_conflict_and_isolation() -> None:
    suffix = uuid.uuid4().hex
    snapshot = make_snapshot(suffix)

    with psycopg.connect(DSN) as connection:
        repository = PostgresScheduleInputSnapshotRepository(connection)
        repository.initialize()
        connection.commit()

        created = repository.save(snapshot)
        assert created == snapshot
        assert repository.get(snapshot.scope, snapshot.snapshot_id) == snapshot
        assert repository.list(snapshot.scope) == (snapshot,)

        assert repository.save(snapshot) == snapshot

        conflicting = ScheduleInputSnapshot(
            scope=snapshot.scope,
            snapshot_id=snapshot.snapshot_id,
            snapshot_hash=hashlib.sha256('{"different":true}'.encode("utf-8")).hexdigest(),
            canonical_payload='{"different":true}',
            calculation_identity="c" * 64,
            created_at=snapshot.created_at,
        )
        with pytest.raises(ScheduleSnapshotPersistenceError, match="SNAPSHOT_IMMUTABLE_CONFLICT"):
            repository.save(conflicting)

        isolated = make_snapshot(suffix, tenant_id=f"isolated-{suffix}")
        assert repository.get(isolated.scope, isolated.snapshot_id) is None
        repository.save(isolated)
        assert repository.list(snapshot.scope) == (snapshot,)
        assert repository.list(isolated.scope) == (isolated,)
