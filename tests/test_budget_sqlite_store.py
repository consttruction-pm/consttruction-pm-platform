from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from construction_pm.budget_persistence import (
    BUDGET_CHANGE_STATUSES,
    BudgetChange,
    BudgetIdempotencyReuse,
    BudgetLine,
    BudgetPersistenceError,
    BudgetRevisionConflict,
    FundingSource,
    SQLiteBudgetStore,
    money_text,
    parse_budget_amount,
)

NOW = datetime(2026, 11, 12, 9, 30, tzinfo=timezone.utc)


def line(**changes: object) -> BudgetLine:
    values = {
        "tenant_id": "T-1",
        "project_id": "P-1",
        "budget_line_id": "BL-1",
        "description": "Concrete works",
        "currency": "USD",
        "original_amount": Decimal("1500000.00"),
        "cost_account_id": "CA-1",
        "period_id": "2026",
    }
    values.update(changes)
    return BudgetLine(**values)


def change(**changes: object) -> BudgetChange:
    values = {
        "tenant_id": "T-1",
        "project_id": "P-1",
        "budget_line_id": "BL-1",
        "change_id": "BC-1",
        "amount": Decimal("12000.00"),
        "reason": "Additional foundation depth",
    }
    values.update(changes)
    return BudgetChange(**values)


def funding(**changes: object) -> FundingSource:
    values = {
        "tenant_id": "T-1",
        "project_id": "P-1",
        "funding_id": "FS-1",
        "name": "Owner equity 2026",
        "source_type": "internal",
        "currency": "USD",
        "amount": Decimal("900000.00"),
        "period_id": "2026",
    }
    values.update(changes)
    return FundingSource(**values)


@pytest.fixture()
def store() -> SQLiteBudgetStore:
    connection = sqlite3.connect(":memory:")
    store = SQLiteBudgetStore(connection)
    store.initialize()
    return store


def test_amount_parsing_rejects_floats_bools_exponents_and_excess_precision() -> None:
    assert parse_budget_amount("12.30", code="BAD") == Decimal("12.30")
    assert parse_budget_amount(12, code="BAD") == Decimal("12")
    for value in (12.3, True, None, "1e3", "12.345", "NaN", "Infinity", ""):
        with pytest.raises(BudgetPersistenceError, match="BAD"):
            parse_budget_amount(value, code="BAD")
    assert money_text(Decimal("7")) == "7.00"


def test_persist_line_is_idempotent_and_rejects_reused_key(store) -> None:
    first = store.persist_line(line(), idempotency_key="k-1", actor_id="u-1", occurred_at=NOW)
    replay = store.persist_line(line(), idempotency_key="k-1", actor_id="u-1", occurred_at=NOW)
    assert first == replay
    assert first.revision == 1

    with pytest.raises(BudgetIdempotencyReuse, match="BUDGET_IDEMPOTENCY_KEY_REUSE"):
        store.persist_line(
            line(description="Tampered"),
            idempotency_key="k-1",
            actor_id="u-1",
            occurred_at=NOW,
        )
    with pytest.raises(ValueError, match="BUDGET_LINE_ALREADY_EXISTS"):
        store.persist_line(line(), idempotency_key="k-2", actor_id="u-1", occurred_at=NOW)


def test_list_lines_filters_currency_cost_account_and_search(store) -> None:
    store.persist_line(line(), idempotency_key="k-1", actor_id="u-1", occurred_at=NOW)
    store.persist_line(
        line(budget_line_id="BL-2", description="Steel reinforcement", currency="EUR", cost_account_id="CA-2"),
        idempotency_key="k-2",
        actor_id="u-1",
        occurred_at=NOW,
    )

    def ids(**kwargs: object) -> list[str]:
        return [item.line.budget_line_id for item in store.list_lines("T-1", "P-1", **kwargs)]

    assert ids() == ["BL-1", "BL-2"]
    assert ids(currency="EUR") == ["BL-2"]
    assert ids(cost_account_id="CA-1") == ["BL-1"]
    assert ids(search="steel") == ["BL-2"]
    assert ids(currency="GBP") == []
    assert store.list_lines("T-2", "P-1") == ()
    with pytest.raises(ValueError, match="INVALID_BUDGET_CURRENCY"):
        store.list_lines("T-1", "P-1", currency="usd")


def test_update_line_guards_revision_and_records_immutable_history(store) -> None:
    store.persist_line(line(), idempotency_key="k-1", actor_id="u-1", occurred_at=NOW)
    updated = store.update_line(
        line(description="Concrete works revised"),
        expected_revision=1,
        actor_id="u-2",
        occurred_at=NOW,
        audit_reason="scope refinement",
    )
    assert updated.revision == 2
    assert store.get_line("T-1", "P-1", "BL-1").line.description == "Concrete works revised"

    with pytest.raises(BudgetRevisionConflict, match="BUDGET_REVISION_CONFLICT"):
        store.update_line(
            line(description="Stale write"),
            expected_revision=1,
            actor_id="u-2",
            occurred_at=NOW,
        )
    with pytest.raises(KeyError, match="BUDGET_LINE_NOT_FOUND"):
        store.update_line(
            line(budget_line_id="BL-404"),
            expected_revision=1,
            actor_id="u-2",
            occurred_at=NOW,
        )

    events = store.line_history("T-1", "P-1", "BL-1")
    assert [(event.revision, event.event_type, event.actor_id) for event in events] == [
        (1, "created", "u-1"),
        (2, "updated", "u-2"),
    ]
    assert events[1].reason == "scope refinement"
    assert events[1].occurred_at == NOW


def test_change_replay_is_identical_and_conflicting_replay_is_rejected(store) -> None:
    store.persist_line(line(), idempotency_key="k-1", actor_id="u-1", occurred_at=NOW)
    created = store.create_change(change(), actor_id="u-1", occurred_at=NOW)
    replay = store.create_change(change(), actor_id="u-1", occurred_at=NOW)
    assert created == replay
    assert created.revision == 1

    with pytest.raises(ValueError, match="BUDGET_CHANGE_ALREADY_EXISTS"):
        store.create_change(change(amount=Decimal("99.00")), actor_id="u-1", occurred_at=NOW)
    with pytest.raises(KeyError, match="BUDGET_LINE_NOT_FOUND"):
        store.create_change(
            change(budget_line_id="BL-404", change_id="BC-2"),
            actor_id="u-1",
            occurred_at=NOW,
        )


def test_change_status_transition_is_one_way_and_revision_guarded(store) -> None:
    store.persist_line(line(), idempotency_key="k-1", actor_id="u-1", occurred_at=NOW)
    store.create_change(change(), actor_id="u-1", occurred_at=NOW)

    with pytest.raises(BudgetRevisionConflict, match="BUDGET_REVISION_CONFLICT"):
        store.transition_change(
            tenant_id="T-1",
            project_id="P-1",
            change_id="BC-1",
            status="approved",
            expected_revision=2,
            actor_id="admin",
            occurred_at=NOW,
        )
    approved = store.transition_change(
        tenant_id="T-1",
        project_id="P-1",
        change_id="BC-1",
        status="approved",
        expected_revision=1,
        actor_id="admin",
        occurred_at=NOW,
        reason="approved in change board",
    )
    assert approved.change.status == "approved"
    assert approved.revision == 2
    assert store.list_changes("T-1", "P-1", "BL-1")[0].change.status == "approved"

    with pytest.raises(ValueError, match="BUDGET_INVALID_CHANGE_STATUS_TRANSITION"):
        store.transition_change(
            tenant_id="T-1",
            project_id="P-1",
            change_id="BC-1",
            status="rejected",
            expected_revision=2,
            actor_id="admin",
            occurred_at=NOW,
        )
    with pytest.raises(ValueError, match="INVALID_BUDGET_CHANGE_STATUS"):
        store.transition_change(
            tenant_id="T-1",
            project_id="P-1",
            change_id="BC-1",
            status="pending",
            expected_revision=2,
            actor_id="admin",
            occurred_at=NOW,
        )
    assert set(BUDGET_CHANGE_STATUSES) == {"pending", "approved", "rejected"}


def test_funding_persists_and_updates_with_revision_guard(store) -> None:
    first = store.persist_funding(funding(), idempotency_key="f-1", actor_id="u-1", occurred_at=NOW)
    replay = store.persist_funding(funding(), idempotency_key="f-1", actor_id="u-1", occurred_at=NOW)
    assert first == replay
    assert first.revision == 1
    with pytest.raises(BudgetIdempotencyReuse, match="BUDGET_IDEMPOTENCY_KEY_REUSE"):
        store.persist_funding(
            funding(amount=Decimal("1.00")),
            idempotency_key="f-1",
            actor_id="u-1",
            occurred_at=NOW,
        )
    assert [item.funding.funding_id for item in store.list_funding("T-1", "P-1")] == ["FS-1"]

    updated = store.update_funding(
        funding(amount=Decimal("950000.00")),
        expected_revision=1,
        actor_id="u-2",
        occurred_at=NOW,
    )
    assert updated.revision == 2
    with pytest.raises(BudgetRevisionConflict, match="BUDGET_REVISION_CONFLICT"):
        store.update_funding(
            funding(amount=Decimal("1.00")),
            expected_revision=1,
            actor_id="u-2",
            occurred_at=NOW,
        )
    with pytest.raises(KeyError, match="BUDGET_FUNDING_NOT_FOUND"):
        store.update_funding(
            funding(funding_id="FS-404"),
            expected_revision=1,
            actor_id="u-2",
            occurred_at=NOW,
        )


def test_invalid_documents_are_rejected_before_insert(store) -> None:
    for bad in (
        line(currency="usd"),
        line(original_amount=Decimal("-1.00")),
        line(original_amount=Decimal("1.005")),
        line(description="   "),
    ):
        with pytest.raises(BudgetPersistenceError):
            store.persist_line(bad, idempotency_key="bad", actor_id="u-1", occurred_at=NOW)
    with pytest.raises(BudgetPersistenceError, match="INVALID_BUDGET_CHANGE_AMOUNT"):
        change(amount=Decimal("0.00")).validate()
    with pytest.raises(BudgetPersistenceError, match="INVALID_BUDGET_FUNDING_TYPE"):
        funding(source_type="barter").validate()
    with pytest.raises(BudgetPersistenceError, match="INVALID_BUDGET_AUDIT_TIMESTAMP"):
        store.persist_line(
            line(), idempotency_key="k-1", actor_id="u-1", occurred_at=datetime(2026, 11, 12)
        )
    assert store.list_lines("T-1", "P-1") == ()
