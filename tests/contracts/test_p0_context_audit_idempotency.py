from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from construction_pm.p0_boundary import (
    AuditEvent,
    IdempotencyScope,
    ProjectContext,
    RevisionPrecondition,
)


ROOT = Path(__file__).parents[2]
CONTRACT = ROOT / "shared" / "contracts" / "p0-context-audit-idempotency.v1.schema.json"
MAX_SAFE = 9007199254740991


def test_context_and_idempotency_are_scoped_by_tenant_and_project() -> None:
    context = ProjectContext("tenant-a", "project-a")
    scope = IdempotencyScope(context, "request-1", "fingerprint-1")
    assert scope.storage_key == ("tenant-a", "project-a", "request-1")


@pytest.mark.parametrize("revision", [-1, MAX_SAFE + 1, True])
def test_revision_precondition_rejects_invalid_values(revision: object) -> None:
    with pytest.raises(ValueError, match="INVALID_EXPECTED_REVISION"):
        RevisionPrecondition(ProjectContext("tenant", "project"), revision)  # type: ignore[arg-type]


def test_audit_event_requires_context_actor_action_and_utc_capable_timestamp() -> None:
    event = AuditEvent(
        context=ProjectContext("tenant", "project"),
        actor_id="user-1",
        action="change.created",
        resource_type="change",
        resource_id="change-1",
        revision=3,
        metadata={"source": "api"},
        occurred_at=datetime.now(timezone.utc),
    )
    assert event.context.tenant_id == "tenant"
    assert event.revision == 3


def test_audit_event_rejects_naive_timestamp() -> None:
    with pytest.raises(ValueError, match="AUDIT_TIMESTAMP_MUST_BE_TIMEZONE_AWARE"):
        AuditEvent(
            context=ProjectContext("tenant", "project"),
            actor_id="user-1",
            action="change.created",
            resource_type="change",
            resource_id="change-1",
            revision=3,
            occurred_at=datetime(2026, 9, 27),
        )


def test_contract_is_versioned_and_bounded() -> None:
    contract = json.loads(CONTRACT.read_text())
    assert "/v1/" in contract["$id"]
    assert contract["properties"]["contract_version"]["const"] == "1.0"
    assert contract["properties"]["revision"]["maximum"] == MAX_SAFE
    assert {
        "contract_version",
        "tenant_id",
        "project_id",
        "resource_type",
        "resource_id",
        "revision",
        "actor_id",
        "action",
        "idempotency_key",
    } == set(contract["required"])
