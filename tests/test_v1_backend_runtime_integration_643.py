from dataclasses import replace
from datetime import date, datetime, timezone

from construction_pm.application.authorization import (
    AuthorizationContext,
    default_project_policy,
)
from construction_pm.backend_p0.api import BackendP0API
from construction_pm.backend_p0.application import BackendP0ApplicationService
from construction_pm.backend_p0.models import (
    AuditMetadata,
    BackendScope,
    FieldDailyLog,
)
from construction_pm.backend_p0.repository import InMemoryBackendP0Repository
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
import sqlite3


def _api() -> BackendP0API:
    connection = sqlite3.connect(":memory:")
    service = BackendP0ApplicationService(
        repository=InMemoryBackendP0Repository(),
        transaction_manager=SQLiteTransactionManager(connection),
        authorization_policy=default_project_policy(),
    )
    return BackendP0API(service)


def _record() -> FieldDailyLog:
    now = datetime(2026, 10, 1, 8, 30, tzinfo=timezone.utc)
    return FieldDailyLog(
        log_id="log-643",
        scope=BackendScope("tenant-a", "project-a", 7),
        log_date=date(2026, 10, 1),
        location_key="site-a",
        status="draft",
        entries=(),
        audit=AuditMetadata(
            created_by="user-a",
            created_at=now,
            updated_at=now,
            correlation_id="corr-643",
            source="integration-test",
        ),
    )


def _planner() -> AuthorizationContext:
    return AuthorizationContext(
        "tenant-a", "project-a", "user-a", frozenset({"planner"})
    )


def test_runtime_api_round_trip_preserves_project_scope_revision_and_decimal_boundary():
    api = _api()
    record = _record()

    saved = api.save_resource(record, auth_context=_planner())

    assert saved["record"]["log_id"] == "log-643"
    assert saved["record"]["scope"] == {
        "tenant_id": "tenant-a",
        "project_id": "project-a",
        "project_revision": 7,
    }
    assert saved["record_revision"] == 1

    read = api.read_resource(record, auth_context=_planner())

    assert read == saved


def test_runtime_api_rejects_stale_revision_and_cross_scope_access():
    api = _api()
    record = _record()
    api.save(record, auth_context=_planner())

    stale = api.save(
        replace(record, location_key="site-b"),
        auth_context=_planner(),
        expected_revision=0,
    )
    assert stale["category"] == "conflict"
    assert stale["code"] == "STALE_REVISION"

    cross_scope = api.read(
        record,
        auth_context=AuthorizationContext(
            "tenant-b", "project-a", "user-b", frozenset({"viewer"})
        ),
    )
    assert cross_scope["category"] == "authorization"
    assert cross_scope["code"] == "CROSS_SCOPE_ACCESS"


def test_runtime_api_enforces_permission_at_application_boundary():
    api = _api()
    record = _record()

    denied = api.save_resource(
        record,
        auth_context=AuthorizationContext(
            "tenant-a", "project-a", "user-a", frozenset({"viewer"})
        ),
    )

    assert denied["category"] == "authorization"
    assert denied["code"] == "FORBIDDEN"
