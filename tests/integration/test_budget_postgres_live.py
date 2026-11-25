"""Live PostgreSQL acceptance for the durable budget register.

The preview store is SQLite. The production composition now serves the same
tables through ``PostgresBudgetStore``; this module proves the full register —
lines, changes, funding, revision CAS, idempotency and the audit trail — over
real PostgreSQL, not the preview adapter.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from construction_pm.budget_persistence import (
    BudgetChange,
    BudgetIdempotencyReuse,
    BudgetLine,
    BudgetRevisionConflict,
    FundingSource,
    PostgresBudgetStore,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("CONSTRUCTION_PM_POSTGRES_DSN"),
    reason="CONSTRUCTION_PM_POSTGRES_DSN is not configured",
)

AT = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)


def _connect():
    import psycopg

    return psycopg.connect(os.environ["CONSTRUCTION_PM_POSTGRES_DSN"])


def _scope():
    suffix = uuid.uuid4().hex
    return f"tenant-budget-{suffix}", f"project-budget-{suffix}"


def _line(tenant, project, *, line_id="BL-1", amount="1000.00", currency="USD"):
    return BudgetLine(
        tenant_id=tenant,
        project_id=project,
        budget_line_id=line_id,
        description="Civil works",
        currency=currency,
        original_amount=Decimal(amount),
        cost_account_id="CA-1",
        period_id="FY26",
    )


def test_postgres_budget_line_change_and_funding_round_trip():
    tenant, project = _scope()
    with _connect() as conn:
        store = PostgresBudgetStore(conn)
        store.initialize()

        stored = store.persist_line(
            _line(tenant, project), idempotency_key="k-1", actor_id="u-1", occurred_at=AT
        )
        assert stored.revision == 1
        assert store.get_line(tenant, project, "BL-1").line.original_amount == Decimal("1000.00")

        # Identical idempotent replay; a different payload under the same key is
        # a key reuse, never a silent second line.
        replay = store.persist_line(
            _line(tenant, project), idempotency_key="k-1", actor_id="u-1", occurred_at=AT
        )
        assert replay.revision == 1
        with pytest.raises(BudgetIdempotencyReuse, match="BUDGET_IDEMPOTENCY_KEY_REUSE"):
            store.persist_line(
                _line(tenant, project, amount="2000.00"),
                idempotency_key="k-1",
                actor_id="u-1",
                occurred_at=AT,
            )

        # Filters run in PostgreSQL JSON operators, not SQLite json_extract.
        assert [item.line.budget_line_id for item in store.list_lines(tenant, project)] == ["BL-1"]
        assert len(store.list_lines(tenant, project, currency="USD")) == 1
        assert store.list_lines(tenant, project, currency="EUR") == ()
        assert len(store.list_lines(tenant, project, cost_account_id="CA-1")) == 1
        assert len(store.list_lines(tenant, project, search="civil")) == 1
        assert store.list_lines(tenant, project, search="missing") == ()
        assert store.list_lines("other-tenant", project) == ()

        # Revision CAS on update.
        updated = store.update_line(
            _line(tenant, project, amount="1250.00"),
            expected_revision=1,
            actor_id="u-1",
            occurred_at=AT,
            audit_reason="approved re-estimate",
        )
        assert updated.revision == 2
        with pytest.raises(BudgetRevisionConflict, match="BUDGET_REVISION_CONFLICT"):
            store.update_line(
                _line(tenant, project, amount="1500.00"),
                expected_revision=1,
                actor_id="u-1",
                occurred_at=AT,
            )

        # Changes: created pending, identical replay is idempotent, a changed
        # payload under the same change id is rejected.
        change = BudgetChange(
            tenant_id=tenant,
            project_id=project,
            budget_line_id="BL-1",
            change_id="CH-1",
            amount=Decimal("250.00"),
            reason="scope increase",
            status="pending",
        )
        assert store.create_change(change, actor_id="u-1", occurred_at=AT).revision == 1
        assert store.create_change(change, actor_id="u-1", occurred_at=AT).revision == 1
        with pytest.raises(ValueError, match="BUDGET_CHANGE_ALREADY_EXISTS"):
            store.create_change(
                BudgetChange(
                    tenant_id=tenant,
                    project_id=project,
                    budget_line_id="BL-1",
                    change_id="CH-1",
                    amount=Decimal("999.00"),
                    reason="changed",
                    status="pending",
                ),
                actor_id="u-1",
                occurred_at=AT,
            )
        approved = store.transition_change(
            tenant_id=tenant,
            project_id=project,
            change_id="CH-1",
            status="approved",
            expected_revision=1,
            actor_id="u-admin",
            occurred_at=AT,
            reason="owner approved",
        )
        assert approved.revision == 2
        assert approved.change.status == "approved"
        with pytest.raises(ValueError, match="BUDGET_INVALID_CHANGE_STATUS_TRANSITION"):
            store.transition_change(
                tenant_id=tenant,
                project_id=project,
                change_id="CH-1",
                status="rejected",
                expected_revision=2,
                actor_id="u-admin",
                occurred_at=AT,
            )
        # A change that already left pending is rejected by the status guard,
        # so a second approval can never restate the budget.
        assert [item.change.change_id for item in store.list_changes(tenant, project, "BL-1")] == ["CH-1"]

        # Funding: idempotent create, revision CAS on update.
        funding = FundingSource(
            tenant_id=tenant,
            project_id=project,
            funding_id="FD-1",
            name="Owner capital",
            source_type="internal",
            currency="USD",
            amount=Decimal("500.00"),
            period_id="FY26",
        )
        assert store.persist_funding(
            funding, idempotency_key="f-1", actor_id="u-1", occurred_at=AT
        ).revision == 1
        assert store.persist_funding(
            funding, idempotency_key="f-1", actor_id="u-1", occurred_at=AT
        ).revision == 1
        with pytest.raises(BudgetIdempotencyReuse, match="BUDGET_IDEMPOTENCY_KEY_REUSE"):
            store.persist_funding(
                FundingSource(
                    tenant_id=tenant,
                    project_id=project,
                    funding_id="FD-1",
                    name="Owner capital",
                    source_type="internal",
                    currency="USD",
                    amount=Decimal("900.00"),
                ),
                idempotency_key="f-1",
                actor_id="u-1",
                occurred_at=AT,
            )
        assert store.update_funding(
            FundingSource(
                tenant_id=tenant,
                project_id=project,
                funding_id="FD-1",
                name="Owner capital",
                source_type="internal",
                currency="USD",
                amount=Decimal("750.00"),
                period_id="FY26",
            ),
            expected_revision=1,
            actor_id="u-1",
            occurred_at=AT,
        ).revision == 2
        with pytest.raises(BudgetRevisionConflict, match="BUDGET_REVISION_CONFLICT"):
            store.update_funding(funding, expected_revision=1, actor_id="u-1", occurred_at=AT)
        assert [item.funding.funding_id for item in store.list_funding(tenant, project)] == ["FD-1"]

        # The audit trail is written with a real timestamp and ordered by
        # revision: created then updated.
        events = store.line_history(tenant, project, "BL-1")
        assert [event.event_type for event in events] == ["created", "updated"]
        assert [event.revision for event in events] == [1, 2]
        assert all(event.occurred_at.tzinfo is not None for event in events)


def test_postgres_budget_writes_roll_back_with_the_transaction():
    tenant, project = _scope()
    with _connect() as conn:
        store = PostgresBudgetStore(conn)
        store.initialize()
        try:
            store.persist_line(
                _line(tenant, project), idempotency_key="rollback", actor_id="u-1", occurred_at=AT
            )
            raise RuntimeError("force rollback")
        except RuntimeError:
            conn.rollback()
        assert store.list_lines(tenant, project) == ()
