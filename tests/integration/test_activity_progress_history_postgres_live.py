import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest

from construction_pm.activity_progress_history import (
    ActivityProgressEvent,
    PostgresActivityProgressHistoryRepository,
    ProgressFieldChange,
    ProgressOutOfSequenceFinding,
)
from construction_pm.backend_p0.models import BackendScope

pytestmark = pytest.mark.skipif(
    not os.getenv("CONSTRUCTION_PM_POSTGRES_DSN"),
    reason="CONSTRUCTION_PM_POSTGRES_DSN is not configured",
)


def connect():
    import psycopg

    return psycopg.connect(os.environ["CONSTRUCTION_PM_POSTGRES_DSN"])


def _event(scope, event_id, from_revision, to_revision, *, percent="20.0"):
    return ActivityProgressEvent(
        scope=scope,
        event_id=event_id,
        activity_id="A140",
        recorded_at=datetime(2026, 11, 12, 9, 30, tzinfo=timezone.utc),
        actor_user_id="planner-live",
        from_record_revision=from_revision,
        to_record_revision=to_revision,
        changes=(ProgressFieldChange("percent_complete", None, percent),),
        findings=(
            ProgressOutOfSequenceFinding(
                "FS_PREDECESSOR_NOT_FINISHED", "REL-RPS-130", "A130", "FS"
            ),
        ),
    )


def test_postgres_append_list_isolation_and_latest():
    with connect() as c:
        repo = PostgresActivityProgressHistoryRepository(c)
        repo.initialize()
        c.commit()
        scope = BackendScope("tenant-progress", "project-progress", 3)
        first = repo.append(_event(scope, "A140@2", 1, 2))
        second = repo.append(_event(scope, "A140@3", 2, 3, percent="55.0"))
        c.commit()

        assert first == _event(scope, "A140@2", 1, 2)
        assert repo.list(scope, "A140") == (first, second)
        assert repo.latest(scope, "A140") == second
        assert repo.list(BackendScope("tenant-other", "project-progress", 3), "A140") == ()
        assert repo.latest(scope, "A999") is None


def test_postgres_identical_append_replays_without_duplication():
    with connect() as c:
        repo = PostgresActivityProgressHistoryRepository(c)
        repo.initialize()
        c.commit()
        scope = BackendScope("tenant-progress-replay", "project-progress", 3)
        event = _event(scope, "A140@2", 1, 2)
        repo.append(event)
        repo.append(event)
        c.commit()
        assert repo.list(scope, "A140") == (event,)


def test_postgres_concurrent_identical_append_is_idempotent():
    scope = BackendScope("tenant-progress-concurrent", "project-progress", 3)
    event = _event(scope, "A140@2", 1, 2)
    barrier = threading.Barrier(2)

    def save():
        with connect() as c:
            repo = PostgresActivityProgressHistoryRepository(c)
            repo.initialize()
            c.commit()
            barrier.wait(timeout=5)
            result = repo.append(event)
            c.commit()
            return result

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [future.result(timeout=10) for future in [pool.submit(save) for _ in range(2)]]

    assert results == [event, event]
    with connect() as c:
        repo = PostgresActivityProgressHistoryRepository(c)
        assert repo.list(scope, "A140") == (event,)
