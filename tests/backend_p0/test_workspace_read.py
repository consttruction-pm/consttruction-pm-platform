from __future__ import annotations

import pytest

from construction_pm.application.authorization import AuthorizationContext, Permission, RoleBasedAuthorizationPolicy
from construction_pm.backend_p0.api import BackendP0API
from construction_pm.backend_p0.errors import ErrorCategory
from construction_pm.backend_p0.models import (
    BackendScope,
    AuditMetadata,
    ProcurementQuote,
    ProcurementQuoteItem,
    EvidenceRef,
)
from decimal import Decimal
from datetime import date, datetime, timezone
from construction_pm.backend_p0.persistence import SQLiteBackendP0Repository
from construction_pm.backend_p0.workspace_read import (
    WORKSPACE_CONTROL_ROOM_READ_PATH,
    WORKSPACE_CONTROL_ROOM_READ_VERSION,
    InMemoryWorkspaceReadProvider,
    WorkspaceControlRoomReadService,
)


def policy() -> RoleBasedAuthorizationPolicy:
    return RoleBasedAuthorizationPolicy({
        "viewer": frozenset({Permission.PROJECT_READ}),
        "planner": frozenset({Permission.PROJECT_READ, Permission.PROJECT_WRITE}),
    })


def auth(role: str = "viewer") -> AuthorizationContext:
    return AuthorizationContext("tenant-1", "project-1", "user-1", frozenset({role}))


def snapshot(revision: int = 7) -> dict[str, object]:
    return {
        "contract_version": WORKSPACE_CONTROL_ROOM_READ_VERSION,
        "context": {
            "tenant_id": "tenant-1",
            "project_id": "project-1",
            "revision": revision,
        },
        "workspace": {
            "contract_version": "workspace-control-room.v1",
            "context": {
                "tenant_id": "tenant-1",
                "project_id": "project-1",
                "revision": revision,
            },
            "columns": [],
            "activities": [],
        },
        "field_daily_logs": [],
        "field_issues": [],
        "field_timecards": [],
        "equipment_status_reports": [],
        "inspections": [],
        "quality_records": [],
        "safety_observations": [],
        "punch_items": [],
    }


def service_with(snapshot_value: dict[str, object]) -> WorkspaceControlRoomReadService:
    provider = InMemoryWorkspaceReadProvider({
        ("tenant-1", "project-1", 7): snapshot_value,
    })
    return WorkspaceControlRoomReadService(provider, policy())


def test_workspace_read_service_returns_versioned_snapshot_for_authorized_scope() -> None:
    service = service_with(snapshot())
    result = service.read(BackendScope("tenant-1", "project-1", 7), auth_context=auth())

    assert result is not None
    assert result["contract_version"] == WORKSPACE_CONTROL_ROOM_READ_VERSION
    assert result["context"]["revision"] == 7  # type: ignore[index]


def test_workspace_read_service_rejects_cross_scope_and_forbidden_reads() -> None:
    service = service_with(snapshot())

    with pytest.raises(Exception) as cross_scope:
        service.read(
            BackendScope("tenant-2", "project-1", 7),
            auth_context=auth(),
        )
    assert getattr(cross_scope.value, "category") == ErrorCategory.AUTHORIZATION
    assert getattr(cross_scope.value, "code") == "CROSS_SCOPE_ACCESS"

    with pytest.raises(Exception) as forbidden:
        service.read(
            BackendScope("tenant-1", "project-1", 7),
            auth_context=auth("unknown-role"),
        )
    assert getattr(forbidden.value, "code") == "FORBIDDEN"


def test_workspace_read_service_rejects_unsupported_version_and_stale_context() -> None:
    unsupported = snapshot()
    unsupported["contract_version"] = "workspace-control-room-read.v99"
    service = service_with(unsupported)
    with pytest.raises(Exception) as exc:
        service.read(BackendScope("tenant-1", "project-1", 7), auth_context=auth())
    assert getattr(exc.value, "code") == "UNSUPPORTED_WORKSPACE_READ_CONTRACT"

    stale = snapshot(revision=6)
    service = service_with(stale)
    with pytest.raises(Exception) as exc:
        service.read(BackendScope("tenant-1", "project-1", 7), auth_context=auth())
    assert getattr(exc.value, "code") == "STALE_WORKSPACE_READ_SCOPE"


def test_workspace_read_materializes_authoritative_procurement_records() -> None:
    import sqlite3
    connection = sqlite3.connect(":memory:")
    try:
        repository = SQLiteBackendP0Repository(connection)
        scope = BackendScope("tenant-1", "project-1", 7)
        audit = AuditMetadata("user-1", datetime(2026, 9, 27, 8, tzinfo=timezone.utc), datetime(2026, 9, 27, 8, tzinfo=timezone.utc))
        quote = ProcurementQuote(
            "Q-READ", scope, "RFQ-1", "SUP-1", "submitted", "USD", date(2026, 10, 5),
            (ProcurementQuoteItem("I-1", "concrete", Decimal("10.5000"), "m3", Decimal("125.2500"), activity_ids=("A-1",)),),
            audit, evidence_refs=(EvidenceRef("DOC-1", "document", "/doc/1", 7),),
        )
        repository.save(quote)
        service = WorkspaceControlRoomReadService(
            InMemoryWorkspaceReadProvider({("tenant-1", "project-1", 7): snapshot()}),
            policy(),
            procurement_repository=repository,
        )
        result = service.read(scope, auth_context=auth())
        assert result is not None
        assert result["procurement_quotes"][0]["quote_id"] == "Q-READ"
        assert result["procurement_quotes"][0]["contract_version"] == "procurement-quote.v1"
        assert result["procurement_quotes"][0]["items"][0]["unit_price"] == Decimal("125.2500")
    finally:
        connection.close()


def test_workspace_read_materialization_keeps_project_scope_isolated() -> None:
    import sqlite3
    connection = sqlite3.connect(":memory:")
    try:
        repository = SQLiteBackendP0Repository(connection)
        scope = BackendScope("tenant-2", "project-1", 7)
        audit = AuditMetadata("user-1", datetime(2026, 9, 27, 8, tzinfo=timezone.utc), datetime(2026, 9, 27, 8, tzinfo=timezone.utc))
        quote = ProcurementQuote(
            "Q-OTHER", scope, "RFQ-1", "SUP-1", "submitted", "USD", date(2026, 10, 5),
            (ProcurementQuoteItem("I-1", "concrete", Decimal("10"), "m3", Decimal("100"), activity_ids=("A-1",)),),
            audit, evidence_refs=(EvidenceRef("DOC-1", "document", "/doc/1", 7),),
        )
        repository.save(quote)
        service = WorkspaceControlRoomReadService(
            InMemoryWorkspaceReadProvider({("tenant-1", "project-1", 7): snapshot()}),
            policy(),
            procurement_repository=repository,
        )
        result = service.read(BackendScope("tenant-1", "project-1", 7), auth_context=auth())
        assert result is not None
        assert result["procurement_quotes"] == []
    finally:
        connection.close()


def test_backend_api_exposes_the_same_versioned_read_boundary() -> None:
    from construction_pm.backend_p0.api import BackendP0ApplicationService
    from construction_pm.backend_p0.persistence import SQLiteBackendP0Repository
    from construction_pm.backend_p0.transactions import SQLiteTransactionManager
    import sqlite3

    connection = sqlite3.connect(":memory:")
    try:
        app_service = BackendP0ApplicationService(
            SQLiteBackendP0Repository(connection),
            SQLiteTransactionManager(connection),
            policy(),
        )
        api = BackendP0API(app_service, service_with(snapshot()))
        result = api.read_workspace_control_room(
            tenant_id="tenant-1",
            project_id="project-1",
            revision=7,
            auth_context=auth(),
        )
        assert result is not None
        assert result["contract_version"] == WORKSPACE_CONTROL_ROOM_READ_VERSION
        assert WORKSPACE_CONTROL_ROOM_READ_PATH == "/api/v1/workspace/control-room/read"
    finally:
        connection.close()


@pytest.mark.parametrize(
    "key",
    [
        "change_notices",
        "change_cases",
        "claims",
        "change_claim_impacts",
        "documents",
        "procurement_rfqs",
        "procurement_quotes",
        "procurement_bid_comparisons",
        "purchase_orders",
        "procurement_commitments",
        "procurement_deliveries",
    ],
)
def test_workspace_read_service_rejects_malformed_optional_collection(key: str) -> None:
    value = snapshot()
    value[key] = {"invalid": True}
    service = service_with(value)

    with pytest.raises(Exception) as exc:
        service.read(BackendScope("tenant-1", "project-1", 7), auth_context=auth())

    assert getattr(exc.value, "code") == "INVALID_WORKSPACE_READ_COLLECTION"


@pytest.mark.parametrize(
    ("workspace_value", "expected_code"),
    [
        (None, "INVALID_WORKSPACE_READ_WORKSPACE"),
        ({"contract_version": "workspace-control-room.v99", "context": {"tenant_id": "tenant-1", "project_id": "project-1", "revision": 7}, "columns": [], "activities": []}, "UNSUPPORTED_WORKSPACE_CONTRACT"),
        ({"contract_version": "workspace-control-room.v1", "context": {"tenant_id": "tenant-1", "project_id": "project-1", "revision": 6}, "columns": [], "activities": []}, "STALE_WORKSPACE_SNAPSHOT_SCOPE"),
        ({"contract_version": "workspace-control-room.v1", "context": {"tenant_id": "tenant-1", "project_id": "project-1", "revision": 7}, "columns": {}, "activities": []}, "INVALID_WORKSPACE_READ_WORKSPACE_COLLECTION"),
        ({"contract_version": "workspace-control-room.v1", "context": {"tenant_id": "tenant-1", "project_id": "project-1", "revision": 7}, "columns": (), "activities": []}, "INVALID_WORKSPACE_READ_WORKSPACE_COLLECTION"),
        ({"contract_version": "workspace-control-room.v1", "context": {"tenant_id": "tenant-1", "project_id": "project-1", "revision": 7}, "columns": []}, "INVALID_WORKSPACE_READ_WORKSPACE_COLLECTION"),
    ],
)
def test_workspace_read_service_rejects_malformed_nested_workspace(
    workspace_value: object,
    expected_code: str,
) -> None:
    value = snapshot()
    value["workspace"] = workspace_value
    service = service_with(value)

    with pytest.raises(Exception) as exc:
        service.read(BackendScope("tenant-1", "project-1", 7), auth_context=auth())

    assert getattr(exc.value, "code") == expected_code

def test_backend_p0_api_returns_unconfigured_workspace_read_error_as_dto() -> None:
    api = BackendP0API(service=object())

    result = api.read_workspace_control_room(
        tenant_id="tenant-1",
        project_id="project-1",
        revision=7,
        auth_context=auth(),
    )

    assert result is not None
    assert result["error"]["category"] == ErrorCategory.VALIDATION.value
    assert result["error"]["code"] == "WORKSPACE_READ_NOT_CONFIGURED"
