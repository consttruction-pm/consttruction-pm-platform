from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest

psycopg = pytest.importorskip("psycopg")

from construction_pm.threshold_persistence import (  # noqa: E402
    PostgresThresholdStore,
    Threshold,
    ThresholdIdempotencyReuse,
    ThresholdRevisionConflict,
)

NOW = datetime(2026, 11, 24, 9, 30, tzinfo=timezone.utc)


@pytest.fixture()
def dsn() -> str:
    value = os.getenv("P6_TEST_POSTGRES_DSN") or os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
    if not value:
        pytest.skip("P6_TEST_POSTGRES_DSN is not configured")
    return value


@pytest.fixture()
def schema(dsn: str):
    name = "threshold_" + uuid.uuid4().hex[:12]
    with psycopg.connect(dsn) as admin:
        admin.execute(f"CREATE SCHEMA {name}")
        admin.execute(f"SET search_path TO {name}")
        PostgresThresholdStore(admin).initialize()
        admin.commit()
    try:
        yield name
    finally:
        with psycopg.connect(dsn) as admin:
            admin.execute(f"DROP SCHEMA {name} CASCADE")
            admin.commit()


def connection(dsn: str, schema: str):
    conn = psycopg.connect(dsn)
    conn.execute(f"SET search_path TO {schema}")
    return conn


def threshold(tenant: str = "tenant-a", project: str = "project-1", **overrides) -> Threshold:
    payload = dict(
        tenant_id=tenant,
        project_id=project,
        threshold_id="TH-1",
        name="Expense ceiling",
        monitoring_subject="cost",
        parameter="expense_actual_total",
        currency="USD",
        lower_threshold=None,
        upper_threshold=Decimal("100"),
        warning_level=Decimal("10"),
        issue_level=Decimal("50"),
        responsible_manager="manager-1",
        status="active",
    )
    payload.update(overrides)
    return Threshold(**payload)


def test_postgres_threshold_full_lifecycle_persists_across_connections(dsn, schema) -> None:
    writer = connection(dsn, schema)
    store = PostgresThresholdStore(writer)
    try:
        created = store.create_threshold(
            threshold(), idempotency_key="idem-1", actor_id="planner-1", occurred_at=NOW
        )
        assert created.revision == 1
        writer.commit()
    finally:
        writer.close()

    # Reload through a brand-new connection: the definition, its revision and
    # its audit row are real persisted rows, not connection state.
    reader = connection(dsn, schema)
    store = PostgresThresholdStore(reader)
    try:
        loaded = store.get_threshold("tenant-a", "project-1", "TH-1")
        assert loaded.revision == 1
        assert loaded.threshold.upper_threshold == Decimal("100")
        assert loaded.threshold.currency == "USD"
        audit = reader.execute(
            "SELECT event_type, actor_id FROM project_threshold_audit "
            "WHERE tenant_id='tenant-a' AND project_id='project-1'"
        ).fetchall()
        assert audit == [("created", "planner-1")]

        listed = store.list_thresholds(
            "tenant-a", "project-1", monitoring_subject="cost", status="active", search="ceiling"
        )
        assert [item.threshold.threshold_id for item in listed] == ["TH-1"]

        updated = store.update_threshold(
            threshold(upper_threshold=Decimal("2000")),
            expected_revision=1,
            actor_id="planner-2",
            occurred_at=NOW,
        )
        assert updated.revision == 2
        reader.commit()
        assert store.get_threshold("tenant-a", "project-1", "TH-1").threshold.upper_threshold == Decimal("2000")

        # A stale expected_revision must be rejected without changing the row.
        with pytest.raises(ThresholdRevisionConflict, match="THRESHOLD_REVISION_CONFLICT"):
            store.update_threshold(
                threshold(upper_threshold=Decimal("5")),
                expected_revision=1,
                actor_id="planner-3",
                occurred_at=NOW,
            )
        reader.rollback()
        assert store.get_threshold("tenant-a", "project-1", "TH-1").threshold.upper_threshold == Decimal("2000")

        # A reused idempotency key with a different payload is rejected.
        with pytest.raises(ThresholdIdempotencyReuse, match="THRESHOLD_IDEMPOTENCY_KEY_REUSE"):
            store.create_threshold(
                threshold(upper_threshold=Decimal("999")),
                idempotency_key="idem-1",
                actor_id="planner-1",
                occurred_at=NOW,
            )
        reader.rollback()

        # Replaying the same payload under the same key is idempotent.
        replay = store.create_threshold(
            threshold(), idempotency_key="idem-1", actor_id="planner-1", occurred_at=NOW
        )
        assert replay.revision == 2

        history = store.threshold_history("tenant-a", "project-1", "TH-1")
        assert [(event.event_type, event.revision) for event in history] == [
            ("created", 1),
            ("updated", 2),
        ]

        # Another tenant never sees the row.
        assert store.list_thresholds("tenant-b", "project-1") == ()
        with pytest.raises(KeyError, match="THRESHOLD_NOT_FOUND"):
            store.get_threshold("tenant-b", "project-1", "TH-1")

        store.delete_threshold(
            tenant_id="tenant-a",
            project_id="project-1",
            threshold_id="TH-1",
            expected_revision=2,
            actor_id="planner-2",
            occurred_at=NOW,
            reason="superseded",
        )
        reader.commit()
        with pytest.raises(KeyError, match="THRESHOLD_NOT_FOUND"):
            store.get_threshold("tenant-a", "project-1", "TH-1")
        # The definition is gone, but the audit trail proves the full cycle.
        events = reader.execute(
            "SELECT event_type, revision, reason FROM project_threshold_audit "
            "WHERE tenant_id='tenant-a' AND project_id='project-1' ORDER BY revision"
        ).fetchall()
        assert events == [
            ("created", 1, ""),
            ("updated", 2, ""),
            ("deleted", 3, "superseded"),
        ]
        count = reader.execute(
            "SELECT COUNT(*) FROM project_threshold WHERE tenant_id='tenant-a'"
        ).fetchone()[0]
        assert count == 0
    finally:
        reader.close()


def test_postgres_threshold_runs_are_unique_and_ordered(dsn, schema) -> None:
    from construction_pm.threshold_persistence import ThresholdRun

    conn = connection(dsn, schema)
    store = PostgresThresholdStore(conn)
    try:
        store.create_threshold(
            threshold(parameter="open_issue_count", currency=None, upper_threshold=Decimal("4")),
            idempotency_key="idem-run",
            actor_id="planner-1",
            occurred_at=NOW,
        )
        conn.commit()
        assert store.next_run_sequence("tenant-a", "project-1", "TH-1") == 1
        store.record_run(
            ThresholdRun(
                tenant_id="tenant-a",
                project_id="project-1",
                threshold_id="TH-1",
                run_sequence=1,
                observed_value=Decimal("0"),
                level="normal",
                currency=None,
                actor_id="planner-1",
                occurred_at=NOW,
            )
        )
        conn.commit()
        assert store.next_run_sequence("tenant-a", "project-1", "TH-1") == 2
        store.record_run(
            ThresholdRun(
                tenant_id="tenant-a",
                project_id="project-1",
                threshold_id="TH-1",
                run_sequence=2,
                observed_value=Decimal("9"),
                level="issue",
                currency=None,
                actor_id="planner-1",
                occurred_at=NOW,
            )
        )
        conn.commit()
        runs = store.runs("tenant-a", "project-1", "TH-1")
        assert [(run.run_sequence, run.level) for run in runs] == [(1, "normal"), (2, "issue")]
        with pytest.raises(ValueError, match="THRESHOLD_RUN_ALREADY_RECORDED"):
            store.record_run(
                ThresholdRun(
                    tenant_id="tenant-a",
                    project_id="project-1",
                    threshold_id="TH-1",
                    run_sequence=2,
                    observed_value=Decimal("9"),
                    level="issue",
                    currency=None,
                    actor_id="planner-1",
                    occurred_at=NOW,
                )
            )
        conn.rollback()
    finally:
        conn.close()
