from __future__ import annotations

from datetime import datetime, timezone
import sqlite3

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    Permission,
    RoleBasedAuthorizationPolicy,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.control_intelligence.quality_audit_history import (
    SQLiteScheduleQualityAuditHistoryRepository,
)
from construction_pm.control_intelligence.quality_audit_history_api import (
    SCHEDULE_QUALITY_AUDIT_HISTORY_VERSION,
    ScheduleQualityAuditHistoryAPI,
)


def test_history_api_lists_and_reads_immutable_reports_with_project_read_grant() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        repository = SQLiteScheduleQualityAuditHistoryRepository(connection)
        scope = BackendScope("tenant-1", "project-1", 7)
        report = {
            "engine": "ENG-06",
            "status": "partial",
            "evaluation_status": "completed",
            "snapshot": {
                "snapshot_id": "snapshot-1",
                "snapshot_hash": "b" * 64,
                "project_id": "project-1",
                "project_revision": 7,
                "mode": "DATE_BASED",
            },
            "summary": {"finding_count": 2, "critical_count": 1, "warning_count": 1, "info_count": 0},
            "quality_index": {"status": "not_calculated", "value": None},
        }
        record = repository.record(
            scope,
            "query-1",
            report,
            created_at=datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc),
        )
        api = ScheduleQualityAuditHistoryAPI(
            repository,
            RoleBasedAuthorizationPolicy(
                {"viewer": frozenset({Permission.PROJECT_READ})}
            ),
        )
        auth = AuthorizationContext(
            "tenant-1", "project-1", "user-1", frozenset({"viewer"})
        )

        listing = api.list_for_project(scope, auth_context=auth)
        assert listing["contract_version"] == SCHEDULE_QUALITY_AUDIT_HISTORY_VERSION
        assert len(listing["audits"]) == 1
        assert listing["audits"][0]["audit_id"] == record.audit_id
        assert listing["audits"][0]["summary"]["critical_count"] == 1

        detail = api.get(scope, record.audit_id, auth_context=auth)
        assert detail is not None
        assert detail["audit"]["report"] == report
        assert api.get(scope, "missing", auth_context=auth) is None
    finally:
        connection.close()


def test_history_api_rejects_cross_project_and_missing_read_permission() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        repository = SQLiteScheduleQualityAuditHistoryRepository(connection)
        api = ScheduleQualityAuditHistoryAPI(
            repository,
            RoleBasedAuthorizationPolicy(
                {"viewer": frozenset({Permission.PROJECT_READ})}
            ),
        )
        with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
            api.list_for_project(
                BackendScope("tenant-1", "project-2", 7),
                auth_context=AuthorizationContext(
                    "tenant-1", "project-1", "user-1", frozenset({"viewer"})
                ),
            )
        with pytest.raises(AuthorizationError, match="authorization denied"):
            api.list_for_project(
                BackendScope("tenant-1", "project-1", 7),
                auth_context=AuthorizationContext(
                    "tenant-1", "project-1", "user-2", frozenset({"unprivileged"})
                ),
            )
    finally:
        connection.close()
