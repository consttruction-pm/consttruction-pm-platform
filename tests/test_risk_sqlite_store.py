from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pytest

from construction_pm.risk_persistence import (
    SQLiteRiskStore,
    Risk,
    RiskIdempotencyReuse,
    RiskPersistenceError,
    RiskRevisionConflict,
    risk_exposure_level,
    validate_risk_transition,
)

NOW = datetime(2026, 11, 12, 10, 0, tzinfo=timezone.utc)


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
def store() -> SQLiteRiskStore:
    connection = sqlite3.connect(":memory:")
    store = SQLiteRiskStore(connection)
    store.initialize()
    return store


def test_exposure_levels_and_transition_graph() -> None:
    assert risk_exposure_level(1, 1) == "low"
    assert risk_exposure_level(2, 2) == "low"
    assert risk_exposure_level(3, 2) == "medium"
    assert risk_exposure_level(3, 3) == "medium"
    assert risk_exposure_level(4, 3) == "high"
    assert risk_exposure_level(4, 4) == "high"
    assert risk_exposure_level(5, 4) == "critical"
    assert risk_exposure_level(5, 5) == "critical"

    item = risk(probability=4, impact=4)
    assert item.score == 16 and item.exposure_level == "high"

    validate_risk_transition("open", "mitigating")
    validate_risk_transition("closed", "open")
    with pytest.raises(RiskPersistenceError, match="RISK_STATUS_TRANSITION_INVALID"):
        validate_risk_transition("closed", "mitigating")
    with pytest.raises(RiskPersistenceError, match="INVALID_RISK_STATUS"):
        validate_risk_transition("open", "unknown")


def test_risk_validation_rules() -> None:
    risk().validate()
    for bad in (
        risk(title="   "),
        risk(category="unknown"),
        risk(status="archived"),
        risk(response_strategy="ignore"),
        risk(probability=0),
        risk(probability=6),
        risk(probability=True),  # type: ignore[arg-type]
        risk(impact="4"),  # type: ignore[arg-type]
        risk(date_identified="2026-02-30"),
        risk(response_due_date="2026-10-01"),
        risk(response_owner="  "),
        risk(owner=""),
        risk(status="closed"),
    ):
        with pytest.raises(RiskPersistenceError):
            bad.validate()
    risk(status="closed", closure_note="Accepted and monitored").validate()


def test_create_is_idempotent_and_rejects_conflicting_replays(store) -> None:
    first = store.create_risk(
        risk(), idempotency_key="k-1", actor_id="u-1", occurred_at=NOW
    )
    replay = store.create_risk(
        risk(), idempotency_key="k-1", actor_id="u-1", occurred_at=NOW
    )
    assert first == replay and first.revision == 1
    with pytest.raises(RiskIdempotencyReuse, match="RISK_IDEMPOTENCY_KEY_REUSE"):
        store.create_risk(
            risk(title="Tampered"), idempotency_key="k-1", actor_id="u-1", occurred_at=NOW
        )
    with pytest.raises(RiskPersistenceError, match="RISK_ALREADY_EXISTS"):
        store.create_risk(
            risk(), idempotency_key="k-2", actor_id="u-1", occurred_at=NOW
        )


def test_list_filters_and_orders_by_score(store) -> None:
    store.create_risk(risk(), idempotency_key="k-1", actor_id="u-1", occurred_at=NOW)
    store.create_risk(
        risk(
            risk_id="RK-2",
            title="Currency exposure",
            category="commercial",
            status="monitoring",
            probability=5,
            impact=5,
            response_strategy="transfer",
            owner="u-other",
        ),
        idempotency_key="k-2",
        actor_id="u-1",
        occurred_at=NOW,
    )
    store.create_risk(
        risk(
            risk_id="RK-3",
            title="Minor access delay",
            category="external",
            probability=1,
            impact=2,
            status="closed",
            closure_note="Permit granted",
            response_strategy="accept",
        ),
        idempotency_key="k-3",
        actor_id="u-1",
        occurred_at=NOW,
    )

    def ids(**filters: object) -> list[str]:
        return [item.risk.risk_id for item in store.list_risks("T-1", "P-1", **filters)]

    assert ids() == ["RK-2", "RK-1", "RK-3"]
    assert ids(category="commercial") == ["RK-2"]
    assert ids(status="closed") == ["RK-3"]
    assert ids(response_strategy="mitigate") == ["RK-1"]
    assert ids(exposure="critical") == ["RK-2"]
    assert ids(search="currency") == ["RK-2"]
    assert ids(search="u-other") == ["RK-2"]
    assert store.list_risks("T-2", "P-1") == ()
    with pytest.raises(RiskPersistenceError, match="INVALID_RISK_CATEGORY"):
        store.list_risks("T-1", "P-1", category="bogus")
    with pytest.raises(RiskPersistenceError, match="INVALID_RISK_EXPOSURE"):
        store.list_risks("T-1", "P-1", exposure="extreme")


def test_update_delete_and_history_are_revision_guarded(store) -> None:
    store.create_risk(risk(), idempotency_key="k-1", actor_id="u-1", occurred_at=NOW)
    updated = store.update_risk(
        risk(status="mitigating"),
        expected_revision=1,
        actor_id="u-2",
        occurred_at=NOW,
        reason="Response plan approved",
    )
    assert updated.revision == 2
    assert updated.risk.status == "mitigating"
    with pytest.raises(RiskRevisionConflict, match="RISK_REVISION_CONFLICT"):
        store.update_risk(
            risk(status="monitoring"), expected_revision=1, actor_id="u-2", occurred_at=NOW
        )
    closed = store.update_risk(
        risk(status="closed", closure_note="Done"),
        expected_revision=2,
        actor_id="u-2",
        occurred_at=NOW,
        reason="Closed after delivery",
    )
    assert closed.revision == 3
    with pytest.raises(RiskPersistenceError, match="RISK_STATUS_TRANSITION_INVALID"):
        store.update_risk(
            risk(status="mitigating"),
            expected_revision=3,
            actor_id="u-2",
            occurred_at=NOW,
        )
    reopened = store.update_risk(
        risk(status="open"), expected_revision=3, actor_id="u-2", occurred_at=NOW
    )
    assert reopened.revision == 4
    store.delete_risk(
        tenant_id="T-1",
        project_id="P-1",
        risk_id="RK-1",
        expected_revision=4,
        actor_id="u-3",
        occurred_at=NOW,
        reason="duplicate",
    )
    with pytest.raises(KeyError, match="RISK_NOT_FOUND"):
        store.get_risk("T-1", "P-1", "RK-1")
    events = store.risk_history("T-1", "P-1", "RK-1")
    assert [(event.revision, event.event_type) for event in events] == [
        (1, "created"),
        (2, "status_changed"),
        (3, "status_changed"),
        (4, "status_changed"),
        (5, "deleted"),
    ]
    assert events[1].reason == "Response plan approved"
    assert events[-1].reason == "duplicate"
