from datetime import date, datetime, timezone
from decimal import Decimal

from construction_pm.backend_p0 import (
    AuditMetadata,
    BackendScope,
    EvidenceRef,
    FieldDailyLog,
    FieldDailyLogEntry,
)
from construction_pm.backend_p0.repository import StoredRecord
from construction_pm.backend_p0.resource_envelope import to_resource_envelope
from construction_pm.client_sync.application_gateway import ApplicationSyncGateway
from construction_pm.client_sync.offline_mutation import OfflineMutation
from construction_pm.client_sync.sync_outcome import SyncDisposition


def test_p0_resource_envelope_can_cross_sync_boundary_without_losing_identity() -> None:
    scope = BackendScope("tenant-1", "project-1", 12)
    audit = AuditMetadata(
        "user-1",
        datetime(2026, 9, 27, 8, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 27, 8, 0, tzinfo=timezone.utc),
    )
    evidence = EvidenceRef("doc-1", "photo", "page/1", 12)
    record = FieldDailyLog(
        "DL-1",
        scope,
        date(2026, 9, 27),
        "zone-a",
        "submitted",
        (
            FieldDailyLogEntry(
                "E-1",
                "labor",
                "crew.present",
                quantity=Decimal("12.5000"),
                unit="hour",
            ),
        ),
        audit,
        (evidence,),
    )
    envelope = to_resource_envelope(StoredRecord(record, 7))

    received: list[OfflineMutation] = []

    class Handler:
        def handle(self, mutation: OfflineMutation) -> None:
            received.append(mutation)

    mutation = OfflineMutation(
        "m1",
        "tenant-1",
        "project-1",
        7,
        "upsert_resource",
        {"resource": envelope},
        "resource-sync-1",
    )
    outcome = ApplicationSyncGateway("tenant-1", "project-1", Handler()).submit_mutation(mutation)

    assert outcome.disposition is SyncDisposition.ACKNOWLEDGED
    assert len(received) == 1

    synced = received[0].payload["resource"]
    assert synced["contract_version"] == "1.0"
    assert synced["resource_type"] == "daily_log"
    assert synced["resource_id"] == "DL-1"
    assert synced["tenant_id"] == "tenant-1"
    assert synced["project_id"] == "project-1"
    assert synced["revision"] == 7
    assert synced["payload"]["entries"][0]["quantity"] == "12.5000"


def test_p0_resource_envelope_survives_versioned_sync_endpoint_with_context_and_idempotency() -> None:
    from construction_pm.client_sync.api_endpoint import VersionedSyncEndpoint

    envelope = {
        "contract_version": "1.0", "resource_type": "daily_log", "resource_id": "DL-2",
        "tenant_id": "tenant-1", "project_id": "project-1", "revision": 9,
        "payload": {"entries": [{"quantity": "4.2500"}]},
    }
    received: list[OfflineMutation] = []

    class Handler:
        def handle(self, mutation: OfflineMutation) -> None:
            received.append(mutation)

    mutation = OfflineMutation("m2", "tenant-1", "project-1", 9, "upsert_resource", {"resource": envelope}, "resource-sync-2")
    endpoint = VersionedSyncEndpoint(ApplicationSyncGateway("tenant-1", "project-1", Handler()))
    result = endpoint.post(
        {"mutation_id": mutation.mutation_id, "tenant_id": mutation.tenant_id, "project_id": mutation.project_id,
         "expected_revision": mutation.expected_revision, "operation": mutation.operation,
         "payload": mutation.payload, "idempotency_key": mutation.idempotency_key},
        {"Idempotency-Key": mutation.idempotency_key, "X-Tenant-Id": mutation.tenant_id,
         "X-Project-Id": mutation.project_id, "X-Project-Revision": str(mutation.expected_revision)},
    )
    assert result["contract_version"] == "sync-outcome.v1"
    assert result["disposition"] == "acknowledged"
    assert received[0].payload["resource"]["contract_version"] == "1.0"
    assert received[0].payload["resource"]["resource_type"] == "daily_log"
    assert received[0].payload["resource"]["tenant_id"] == "tenant-1"
    assert received[0].payload["resource"]["project_id"] == "project-1"
    assert received[0].payload["resource"]["revision"] == 9


def test_p0_resource_sync_stale_revision_is_rejected_before_handler() -> None:
    from construction_pm.client_sync.api_endpoint import VersionedSyncEndpoint

    calls = 0
    class Handler:
        def handle(self, mutation: OfflineMutation) -> None:
            nonlocal calls
            calls += 1

    endpoint = VersionedSyncEndpoint(ApplicationSyncGateway("tenant-1", "project-1", Handler()))
    result = endpoint.post(
        {"mutation_id": "m3", "tenant_id": "tenant-1", "project_id": "project-1", "expected_revision": 7,
         "operation": "upsert_resource", "payload": {"resource": {"contract_version": "1.0", "resource_type": "daily_log"}},
         "idempotency_key": "resource-sync-3"},
        {"Idempotency-Key": "resource-sync-3", "X-Tenant-Id": "tenant-1", "X-Project-Id": "project-1", "X-Project-Revision": "8"},
    )
    assert result["disposition"] == "conflict"
    assert result["error_code"] == "STALE_REVISION"
    assert calls == 0
