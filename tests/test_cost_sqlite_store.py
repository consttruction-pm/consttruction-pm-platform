from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from construction_pm.cost_persistence import (
    EXPENSE_CATEGORIES,
    CostAccount,
    CostIdempotencyReuse,
    CostPersistenceError,
    CostRevisionConflict,
    Expense,
    SQLiteCostStore,
    money_text,
    parse_cost_amount,
    parse_cost_date,
)

NOW = datetime(2026, 11, 12, 9, 30, tzinfo=timezone.utc)


def account(**changes: object) -> CostAccount:
    values = {
        "tenant_id": "T-1",
        "project_id": "P-1",
        "account_id": "CA-1",
        "name": "Direct costs",
        "parent_account_id": None,
        "description": "Direct project costs",
        "is_default": False,
    }
    values.update(changes)
    return CostAccount(**values)


def expense(**changes: object) -> Expense:
    values = {
        "tenant_id": "T-1",
        "project_id": "P-1",
        "expense_id": "EX-1",
        "name": "Concrete delivery",
        "category": "material",
        "currency": "USD",
        "activity_id": "A-1000",
        "wbs_id": "WBS-1",
        "cost_account_id": None,
        "expense_date": "2026-11-01",
        "accrual_date": "2026-11-02",
        "planned_amount": Decimal("12000.00"),
        "actual_amount": Decimal("11800.00"),
        "remaining_amount": Decimal("200.00"),
        "note": "Batch 4",
    }
    values.update(changes)
    return Expense(**values)


@pytest.fixture()
def store() -> SQLiteCostStore:
    connection = sqlite3.connect(":memory:")
    store = SQLiteCostStore(connection)
    store.initialize()
    return store


def test_amount_and_date_parsing_reject_non_decimal_inputs() -> None:
    assert parse_cost_amount("12.30", code="BAD") == Decimal("12.30")
    assert parse_cost_amount(12, code="BAD") == Decimal("12")
    for value in (12.3, True, None, "1e3", "12.345", "NaN", "Infinity", ""):
        with pytest.raises(CostPersistenceError, match="BAD"):
            parse_cost_amount(value, code="BAD")
    with pytest.raises(CostPersistenceError, match="BAD"):
        parse_cost_amount("-1.00", code="BAD")
    assert parse_cost_amount("-1.00", code="BAD", allow_negative=True) == Decimal("-1.00")
    assert money_text(Decimal("7")) == "7.00"
    assert parse_cost_date("2026-11-12", code="BAD") == "2026-11-12"
    for value in ("2026-13-01", "12/11/2026", "", None):
        with pytest.raises(CostPersistenceError, match="BAD"):
            parse_cost_date(value, code="BAD")


def test_create_account_is_idempotent_and_rejects_conflicting_replays(store) -> None:
    first = store.create_account(account(), idempotency_key="k-1", actor_id="u-1", occurred_at=NOW)
    replay = store.create_account(account(), idempotency_key="k-1", actor_id="u-1", occurred_at=NOW)
    assert first == replay
    assert first.revision == 1

    with pytest.raises(CostIdempotencyReuse, match="COST_IDEMPOTENCY_KEY_REUSE"):
        store.create_account(
            account(name="Tampered"),
            idempotency_key="k-1",
            actor_id="u-1",
            occurred_at=NOW,
        )
    with pytest.raises(ValueError, match="COST_ACCOUNT_ALREADY_EXISTS"):
        store.create_account(account(), idempotency_key="k-2", actor_id="u-1", occurred_at=NOW)


def test_account_hierarchy_rejects_unknown_parents_and_cycles(store) -> None:
    store.create_account(account(), idempotency_key="k-1", actor_id="u-1", occurred_at=NOW)
    store.create_account(
        account(account_id="CA-2", name="Concrete", parent_account_id="CA-1"),
        idempotency_key="k-2",
        actor_id="u-1",
        occurred_at=NOW,
    )
    with pytest.raises(ValueError, match="COST_ACCOUNT_PARENT_NOT_FOUND"):
        store.create_account(
            account(account_id="CA-3", parent_account_id="CA-404"),
            idempotency_key="k-3",
            actor_id="u-1",
            occurred_at=NOW,
        )
    with pytest.raises(ValueError, match="COST_ACCOUNT_HIERARCHY_CYCLE"):
        store.update_account(
            account(parent_account_id="CA-2"),
            expected_revision=1,
            actor_id="u-1",
            occurred_at=NOW,
        )
    with pytest.raises(CostPersistenceError, match="COST_ACCOUNT_SELF_PARENT"):
        account(parent_account_id="CA-1").validate()


def test_default_account_is_unique_and_clears_the_previous_default(store) -> None:
    store.create_account(
        account(is_default=True), idempotency_key="k-1", actor_id="u-1", occurred_at=NOW
    )
    store.create_account(
        account(account_id="CA-2", name="Concrete", is_default=True),
        idempotency_key="k-2",
        actor_id="u-1",
        occurred_at=NOW,
    )
    rows = {item.account.account_id: item for item in store.list_accounts("T-1", "P-1")}
    assert rows["CA-2"].account.is_default is True
    assert rows["CA-1"].account.is_default is False
    assert rows["CA-1"].revision == 2
    events = store.account_history("T-1", "P-1", "CA-1")
    assert [event.event_type for event in events] == ["created", "default_cleared"]

    changed = store.set_default_account(
        tenant_id="T-1",
        project_id="P-1",
        account_id="CA-1",
        expected_revision=2,
        actor_id="u-2",
        occurred_at=NOW,
    )
    flags = {item.account.account_id: item.account.is_default for item in changed}
    assert flags == {"CA-1": True, "CA-2": False}


def test_account_update_and_delete_are_revision_guarded(store) -> None:
    store.create_account(account(), idempotency_key="k-1", actor_id="u-1", occurred_at=NOW)
    store.create_account(
        account(account_id="CA-2", name="Concrete", parent_account_id="CA-1"),
        idempotency_key="k-2",
        actor_id="u-1",
        occurred_at=NOW,
    )
    updated = store.update_account(
        account(name="Direct project costs"),
        expected_revision=1,
        actor_id="u-2",
        occurred_at=NOW,
    )
    assert updated.revision == 2
    with pytest.raises(CostRevisionConflict, match="COST_REVISION_CONFLICT"):
        store.update_account(account(name="Stale"), expected_revision=1, actor_id="u-2", occurred_at=NOW)
    with pytest.raises(ValueError, match="COST_ACCOUNT_HAS_CHILDREN"):
        store.delete_account(
            tenant_id="T-1",
            project_id="P-1",
            account_id="CA-1",
            expected_revision=2,
            actor_id="u-2",
            occurred_at=NOW,
        )
    store.delete_account(
        tenant_id="T-1",
        project_id="P-1",
        account_id="CA-2",
        expected_revision=1,
        actor_id="u-2",
        occurred_at=NOW,
    )
    with pytest.raises(KeyError, match="COST_ACCOUNT_NOT_FOUND"):
        store.get_account("T-1", "P-1", "CA-2")
    assert [event.event_type for event in store.account_history("T-1", "P-1", "CA-2")] == [
        "created",
        "deleted",
    ]


def test_account_referenced_by_an_expense_cannot_be_deleted(store) -> None:
    store.create_account(account(), idempotency_key="k-1", actor_id="u-1", occurred_at=NOW)
    store.create_expense(
        expense(cost_account_id="CA-1"),
        idempotency_key="e-1",
        actor_id="u-1",
        occurred_at=NOW,
    )
    with pytest.raises(ValueError, match="COST_ACCOUNT_IN_USE"):
        store.delete_account(
            tenant_id="T-1",
            project_id="P-1",
            account_id="CA-1",
            expected_revision=1,
            actor_id="u-1",
            occurred_at=NOW,
        )


def test_expense_create_lists_with_filters_and_audits(store) -> None:
    store.create_expense(expense(), idempotency_key="e-1", actor_id="u-1", occurred_at=NOW)
    store.create_expense(
        expense(
            expense_id="EX-2",
            name="Excavator rental",
            category="equipment",
            currency="EUR",
            activity_id="A-2000",
        ),
        idempotency_key="e-2",
        actor_id="u-1",
        occurred_at=NOW,
    )

    def ids(**kwargs: object) -> list[str]:
        return [
            item.expense.expense_id
            for item in store.list_expenses("T-1", "P-1", **kwargs)
        ]

    assert ids() == ["EX-1", "EX-2"]
    assert ids(category="equipment") == ["EX-2"]
    assert ids(activity_id="A-1000") == ["EX-1"]
    assert ids(search="excavator") == ["EX-2"]
    assert store.list_expenses("T-2", "P-1") == ()
    assert [event.event_type for event in store.expense_history("T-1", "P-1", "EX-1")] == [
        "created"
    ]


def test_expense_update_conflict_delete_and_history_after_delete(store) -> None:
    store.create_expense(expense(), idempotency_key="e-1", actor_id="u-1", occurred_at=NOW)
    updated = store.update_expense(
        expense(name="Concrete delivery revised", actual_amount=Decimal("12000.00")),
        expected_revision=1,
        actor_id="u-2",
        occurred_at=NOW,
    )
    assert updated.revision == 2
    with pytest.raises(CostRevisionConflict, match="COST_REVISION_CONFLICT"):
        store.update_expense(expense(name="Stale"), expected_revision=1, actor_id="u-2", occurred_at=NOW)
    store.delete_expense(
        tenant_id="T-1",
        project_id="P-1",
        expense_id="EX-1",
        expected_revision=2,
        actor_id="u-2",
        occurred_at=NOW,
        reason="duplicate entry",
    )
    with pytest.raises(KeyError, match="EXPENSE_NOT_FOUND"):
        store.get_expense("T-1", "P-1", "EX-1")
    events = store.expense_history("T-1", "P-1", "EX-1")
    assert [(event.revision, event.event_type) for event in events] == [
        (1, "created"),
        (2, "updated"),
        (3, "deleted"),
    ]
    assert events[-1].reason == "duplicate entry"


def test_invalid_expense_documents_are_rejected_before_insert(store) -> None:
    store.create_account(account(), idempotency_key="k-1", actor_id="u-1", occurred_at=NOW)
    for bad in (
        expense(category="travel"),
        expense(currency="usd"),
        expense(expense_date="2026-02-30"),
        expense(planned_amount=Decimal("1.005")),
        expense(cost_account_id="CA-404"),
        expense(name="   "),
    ):
        with pytest.raises((CostPersistenceError, ValueError)):
            store.create_expense(bad, idempotency_key="bad", actor_id="u-1", occurred_at=NOW)
    with pytest.raises(CostPersistenceError, match="INVALID_COST_AUDIT_TIMESTAMP"):
        store.create_expense(
            expense(),
            idempotency_key="e-1",
            actor_id="u-1",
            occurred_at=datetime(2026, 11, 12),
        )
    assert set(EXPENSE_CATEGORIES) == {
        "labor",
        "material",
        "equipment",
        "subcontract",
        "overhead",
        "other",
    }
    assert store.list_expenses("T-1", "P-1") == ()
