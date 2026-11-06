from __future__ import annotations

from datetime import datetime, timezone
import sqlite3

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.control_intelligence.quality_audit_history import (
    ScheduleQualityAuditHistoryError,
    SQLiteScheduleQualityAuditHistoryRepository,
)


NOW = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)
HASH = "a" * 64


def report(*, project_id: str = "project-1", revision: int = 7) -> dict[str, object]:
    return {
        "engine": "ENG-06",
        "status": "partial",
        "snapshot": {
            "snapshot_id": "snapshot-1",
            "snapshot_hash": HASH,
            "project_id": project_id,
            "project_revision": revision,
            "mode": "DATE_BASED",
        },
        "summary": {"finding_count": 1, "critical_count": 0, "warning_count": 1, "info_count": 0},
        "findings": [{"rule_id": "OPEN_SUCCESSOR", "severity": "warning"}],
    }


def test_sqlite_history_is_immutable_idempotent_and_project_scoped() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        repository = SQLiteScheduleQualityAuditHistoryRepository(connection)
        scope = BackendScope("tenant-1", "project-1", 7)

        first = repository.record(scope, "query-1", report(), created_at=NOW)
        replay = repository.record(scope, "query-1", report(), created_at=NOW)

        assert replay.audit_id == first.audit_id
        assert replay.created_at == NOW
        assert replay.report == report()
        assert repository.get("tenant-1", "project-1", first.audit_id) == first
        assert repository.get("tenant-2", "project-1", first.audit_id) is None
        assert repository.get("tenant-1", "project-2", first.audit_id) is None
        assert repository.list_for_project("tenant-1", "project-1") == (first,)
        assert repository.list_for_project("tenant-2", "project-1") == ()

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE schedule_quality_audit_history SET report_json='{}' WHERE audit_id=?",
                (first.audit_id,),
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "DELETE FROM schedule_quality_audit_history WHERE audit_id=?",
                (first.audit_id,),
            )
    finally:
        connection.close()


def test_history_query_id_cannot_be_reused_for_a_different_report() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        repository = SQLiteScheduleQualityAuditHistoryRepository(connection)
        scope = BackendScope("tenant-1", "project-1", 7)
        repository.record(scope, "query-1", report(), created_at=NOW)

        changed = report()
        changed["summary"] = {"finding_count": 99}
        with pytest.raises(ScheduleQualityAuditHistoryError, match="QUERY_ID_REUSED"):
            repository.record(scope, "query-1", changed, created_at=NOW)
    finally:
        connection.close()


def test_history_rejects_snapshot_scope_mismatch_and_invalid_limits() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        repository = SQLiteScheduleQualityAuditHistoryRepository(connection)
        with pytest.raises(ScheduleQualityAuditHistoryError, match="SCOPE_MISMATCH"):
            repository.record(
                BackendScope("tenant-1", "other-project", 7),
                "query-1",
                report(),
                created_at=NOW,
            )
        with pytest.raises(ScheduleQualityAuditHistoryError, match="LIMIT_INVALID"):
            repository.list_for_project("tenant-1", "project-1", limit=0)
    finally:
        connection.close()


def test_history_keeps_distinct_project_revisions_in_one_ordered_project_ledger() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        repository = SQLiteScheduleQualityAuditHistoryRepository(connection)
        old = repository.record(
            BackendScope("tenant-1", "project-1", 6),
            "query-old",
            report(revision=6),
            created_at=NOW,
        )
        current = repository.record(
            BackendScope("tenant-1", "project-1", 7),
            "query-current",
            report(revision=7),
            created_at=datetime(2026, 11, 4, 13, 0, tzinfo=timezone.utc),
        )

        rows = repository.list_for_project("tenant-1", "project-1")
        assert tuple(item.audit_id for item in rows) == (current.audit_id, old.audit_id)
        assert {item.scope.project_revision for item in rows} == {6, 7}
    finally:
        connection.close()
