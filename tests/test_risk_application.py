from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    default_project_policy,
)
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.risk_application import (
    RiskApplicationService,
    RiskAuthorizationError,
)
from construction_pm.risk_persistence import (
    SQLiteRiskStore,
    Risk,
    RiskIdempotencyReuse,
    RiskPersistenceError,
    RiskRevisionConflict,
)

NOW = datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc)


def context(
    role: str = "planner", *, tenant: str = "T-1", project: str = "P-1", user: str = "u-1"
) -> AuthorizationContext:
    return AuthorizationContext(tenant, project, user, frozenset({role}))


def risk(**changes: object) -> Risk:
    values = {
        "tenant_id": "T-1",
        "project_id": "P-1",
        "risk_id": "RK-1",
        "title": "Supplier lead time slips",
        "description": "Primary steel supplier may miss the framed date.",
        "category": "schedule",
        "status": "open",
        "probability": 3,
        "impact": 4,
        "response_strategy": "mitigate",
        "owner": "u-owner",
        "date_identified": "2026-11-01",
        "response_owner": "u-response",
        "response_due_date": "2026-12-01",
        "responsible_manager": "u-manager",
        "closure_note": None,
    }
    values.update(changes)
    return Risk(**values)


@pytest.fixture()
def service() -> RiskApplicationService:
    connection = sqlite3.connect(":memory:")
    store = SQLiteRiskStore(connection)
    store.initialize()
    return RiskApplicationService(
        store, default_project_policy(), SQLiteTransactionManager(connection)
    )


def create(service, **changes):
    return service.create_risk(
        risk(**changes),
        idempotency_key="k-1",
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )


def test_create_read_list_and_history(service) -> None:
    created = create(service)
    assert created.revision == 1 and created.risk.score == 12
    assert created.risk.exposure_level == "high"

    read = service.read_risk(
        tenant_id="T-1",
        project_id="P-1",
        risk_id="RK-1",
        context=context("viewer", user="v-1"),
    )
    assert read.risk.title == "Supplier lead time slips"
    listed = service.list_risks(
        tenant_id="T-1", project_id="P-1", context=context("viewer", user="v-1")
    )
    assert [item.risk.risk_id for item in listed] == ["RK-1"]
    history = service.risk_history(
        tenant_id="T-1",
        project_id="P-1",
        risk_id="RK-1",
        context=context("viewer", user="v-1"),
    )
    assert [event.event_type for event in history] == ["created"]


def test_idempotent_creation_and_revision_guarded_update(service) -> None:
    create(service)
    assert create(service).revision == 1
    with pytest.raises(RiskIdempotencyReuse, match="RISK_IDEMPOTENCY_KEY_REUSE"):
        create(service, title="Tampered")
    updated = service.update_risk(
        risk(status="mitigating"),
        expected_revision=1,
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
        reason="Response plan approved",
    )
    assert updated.revision == 2 and updated.risk.status == "mitigating"
    with pytest.raises(RiskRevisionConflict, match="RISK_REVISION_CONFLICT"):
        service.update_risk(
            risk(status="monitoring"),
            expected_revision=1,
            context=context(),
            actor_id="u-1",
            occurred_at=NOW,
        )
    history = service.risk_history(
        tenant_id="T-1",
        project_id="P-1",
        risk_id="RK-1",
        context=context("viewer", user="v-1"),
    )
    assert [(event.revision, event.event_type) for event in history] == [
        (1, "created"),
        (2, "status_changed"),
    ]


def test_closed_risk_requires_note_and_only_reopens(service) -> None:
    create(service)
    service.update_risk(
        risk(status="mitigating"),
        expected_revision=1,
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    with pytest.raises(RiskPersistenceError, match="RISK_CLOSURE_NOTE_REQUIRED"):
        service.update_risk(
            risk(status="closed"),
            expected_revision=2,
            context=context(),
            actor_id="u-1",
            occurred_at=NOW,
        )
    service.update_risk(
        risk(status="closed", closure_note="Delivered"),
        expected_revision=2,
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    with pytest.raises(RiskPersistenceError, match="RISK_STATUS_TRANSITION_INVALID"):
        service.update_risk(
            risk(status="monitoring"),
            expected_revision=3,
            context=context(),
            actor_id="u-1",
            occurred_at=NOW,
        )
    reopened = service.update_risk(
        risk(status="open"),
        expected_revision=3,
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    assert reopened.revision == 4


def test_viewer_actor_spoofing_and_cross_scope_are_denied(service) -> None:
    create(service)
    viewer = context("viewer", user="v-1")
    with pytest.raises(RiskAuthorizationError, match="RISK_PERMISSION_DENIED"):
        service.create_risk(
            risk(risk_id="RK-2"),
            idempotency_key="k-2",
            context=viewer,
            actor_id="v-1",
            occurred_at=NOW,
        )
    with pytest.raises(RiskAuthorizationError, match="RISK_ACTOR_MISMATCH"):
        service.create_risk(
            risk(risk_id="RK-2"),
            idempotency_key="k-2",
            context=context(),
            actor_id="u-2",
            occurred_at=NOW,
        )
    with pytest.raises(RiskAuthorizationError, match="RISK_CROSS_SCOPE_ACCESS"):
        service.list_risks(tenant_id="T-2", project_id="P-1", context=viewer)
    with pytest.raises(RiskAuthorizationError, match="RISK_CROSS_SCOPE_ACCESS"):
        service.read_risk(
            tenant_id="T-1", project_id="P-2", risk_id="RK-1", context=viewer
        )


def test_delete_requires_current_revision(service) -> None:
    create(service)
    with pytest.raises(RiskRevisionConflict, match="RISK_REVISION_CONFLICT"):
        service.delete_risk(
            tenant_id="T-1",
            project_id="P-1",
            risk_id="RK-1",
            expected_revision=2,
            context=context(),
            actor_id="u-1",
            occurred_at=NOW,
        )
    service.delete_risk(
        tenant_id="T-1",
        project_id="P-1",
        risk_id="RK-1",
        expected_revision=1,
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    with pytest.raises(KeyError, match="RISK_NOT_FOUND"):
        service.read_risk(
            tenant_id="T-1",
            project_id="P-1",
            risk_id="RK-1",
            context=context("viewer", user="v-1"),
        )


def test_error_dto_maps_failures_to_stable_categories() -> None:
    error = RiskApplicationService.error_dto(KeyError("RISK_NOT_FOUND"))
    assert error.code == "RISK_NOT_FOUND" and error.category.value == "validation"
    error = RiskApplicationService.error_dto(
        RiskRevisionConflict("RISK_REVISION_CONFLICT")
    )
    assert error.category.value == "conflict" and error.retryable is True
    error = RiskApplicationService.error_dto(
        RiskIdempotencyReuse("RISK_IDEMPOTENCY_KEY_REUSE")
    )
    assert error.category.value == "conflict" and error.retryable is False
    error = RiskApplicationService.error_dto(ValueError("RISK_ALREADY_EXISTS"))
    assert error.category.value == "conflict"
    error = RiskApplicationService.error_dto(
        RiskAuthorizationError("RISK_PERMISSION_DENIED")
    )
    assert error.category.value == "authorization"
    error = RiskApplicationService.error_dto(ValueError("INVALID_RISK_TITLE"))
    assert error.category.value == "validation"
