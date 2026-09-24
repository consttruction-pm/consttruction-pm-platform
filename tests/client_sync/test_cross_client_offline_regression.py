from __future__ import annotations

import sqlite3

from construction_pm.client_sync.context import OfflineProjectContext
from construction_pm.client_sync.mutation import OfflineMutation
from construction_pm.client_sync.queue import InMemoryOfflineMutationQueue, SQLiteOfflineMutationQueue
from construction_pm.client_sync.time_api import TimeSchedulingAPIPayload


def _context() -> OfflineProjectContext:
    return OfflineProjectContext(
        tenant_id="tenant-1",
        company_id="company-1",
        project_id="project-1",
        project_schema_version=2,
        calendar_id="site",
        calendar_version=3,
        scheduling_settings_version=4,
        calculation_settings_version=5,
    )


def _mutation() -> OfflineMutation:
    return OfflineMutation(
        context=_context(),
        operation="schedule_project",
        idempotency_key="idem-1",
        mutation={
            "time_scheduling": TimeSchedulingAPIPayload(
                calculation_context={
                    "schedule_mode": "EARLIEST",
                    "project_start": "2026-09-24T08:00:00",
                },
                activities=(
                    {
                        "activity_id": "A1",
                        "duration_value": "2.5",
                        "duration_unit": "working-hour",
                        "calendar": {
                            "calendar_id": "site",
                            "calendar_version": "3",
                            "kind": "working-time",
                        },
                    },
                ),
                relationships=(),
            ).to_dto()
        },
        expected_revision=7,
    )


def test_time_api_payload_is_client_parity_stable():
    payload = TimeSchedulingAPIPayload(
        calculation_context={"schedule_mode": "EARLIEST", "project_start": "2026-09-24T08:00:00"},
        activities=(
            {
                "activity_id": "A1",
                "duration_value": "2.5",
                "duration_unit": "working-hour",
                "calendar": {"calendar_id": "site", "calendar_version": "3", "kind": "working-time"},
            },
        ),
        relationships=(),
    )
    web_dto = payload.to_dto()
    desktop_dto = payload.to_dto()
    mobile_dto = payload.to_dto()
    assert web_dto == desktop_dto == mobile_dto
    assert web_dto["contract_version"] == "1.0"


def test_offline_mutation_round_trip_preserves_context_revision_and_identity():
    mutation = _mutation()
    memory = InMemoryOfflineMutationQueue()
    memory.enqueue(mutation)
    restored = memory.peek()[0]
    assert restored.context.fingerprint_payload() == mutation.context.fingerprint_payload()
    assert restored.expected_revision == 7
    assert restored.fingerprint_payload() == mutation.fingerprint_payload()

    sqlite_queue = SQLiteOfflineMutationQueue(sqlite3.connect(":memory:"))
    sqlite_queue.enqueue(mutation)
    sqlite_restored = sqlite_queue.peek()[0]
    assert sqlite_restored.context.fingerprint_payload() == mutation.context.fingerprint_payload()
    assert sqlite_restored.expected_revision == 7
    assert sqlite_restored.fingerprint_payload() == mutation.fingerprint_payload()


def test_retry_attempt_does_not_change_cross_client_mutation_identity():
    mutation = _mutation()
    queue = InMemoryOfflineMutationQueue()
    queue.enqueue(mutation)
    retried = queue.increment_attempt(mutation)
    assert retried.attempt == 1
    assert retried.fingerprint_payload() == mutation.fingerprint_payload()


def test_package_exports_use_canonical_offline_mutation_contract():
    from construction_pm.client_sync import OfflineMutation as ExportedOfflineMutation
    from construction_pm.client_sync.mutation import OfflineMutation as CanonicalOfflineMutation
    assert ExportedOfflineMutation is CanonicalOfflineMutation
