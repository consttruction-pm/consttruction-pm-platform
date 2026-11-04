from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")

from construction_pm.backend_p0.models import BackendScope
from construction_pm.control_intelligence.quality_audit_history import (
    PostgresScheduleQualityAuditHistoryRepository,
    ScheduleQualityAuditHistoryError,
)


@pytest.fixture()
def postgres_connection():
    dsn = os.getenv("P6_TEST_POSTGRES_DSN") or os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
    if not dsn:
        pytest.skip("P6_TEST_POSTGRES_DSN is not configured")
    connection = psycopg.connect(dsn)
    try:
        yield connection
    finally:
        connection.rollback()
        connection.close()


def test_postgres_schedule_quality_audit_history_is_scoped_and_idempotent(postgres_connection):
    suffix = uuid4().hex
    tenant_id = f"tenant-{suffix}"
    project_id = f"project-{suffix}"
    scope = BackendScope(tenant_id, project_id, 12)
    report = {
        "engine": "ENG-06",
        "status": "partial",
        "snapshot": {
            "snapshot_id": f"snapshot-{suffix}",
            "snapshot_hash": "c" * 64,
            "project_id": project_id,
            "project_revision": 12,
            "mode": "DATE_BASED",
        },
        "summary": {"finding_count": 1, "critical_count": 0, "warning_count": 1, "info_count": 0},
        "findings": [{"rule_id": "OPEN_SUCCESSOR", "severity": "warning"}],
    }
    now = datetime(2026, 11, 4, 14, 0, tzinfo=timezone.utc)

    with postgres_connection.transaction():
        repository = PostgresScheduleQualityAuditHistoryRepository(postgres_connection)
        first = repository.record(scope, f"query-{suffix}", report, created_at=now)
        replay = repository.record(scope, f"query-{suffix}", report, created_at=now)

        assert replay.audit_id == first.audit_id
        assert repository.get(tenant_id, project_id, first.audit_id) == first
        assert repository.get(f"other-{tenant_id}", project_id, first.audit_id) is None
        rows = repository.list_for_project(tenant_id, project_id)
        assert len(rows) == 1
        assert rows[0].scope.project_revision == 12
        assert rows[0].report == report

        changed = dict(report)
        changed["summary"] = {"finding_count": 88}
        with pytest.raises(ScheduleQualityAuditHistoryError, match="QUERY_ID_REUSED"):
            repository.record(scope, f"query-{suffix}", changed, created_at=now)
