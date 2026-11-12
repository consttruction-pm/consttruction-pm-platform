from __future__ import annotations

import sqlite3
from decimal import Decimal
from types import SimpleNamespace

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_issue_repository import P6Issue, SQLiteP6IssueRepository
from construction_pm.threshold_metrics import ProjectMetricReader

SCOPE = BackendScope("T-1", "P-1", 7)


class CostStore:
    def __init__(self, *amounts: tuple[str, object]) -> None:
        self.rows = [
            SimpleNamespace(expense=SimpleNamespace(currency=currency, actual_amount=amount))
            for currency, amount in amounts
        ]

    def list_expenses(self, tenant_id: str, project_id: str):
        return tuple(self.rows)


class BudgetStore:
    def __init__(self) -> None:
        self.lines = [
            SimpleNamespace(line=SimpleNamespace(currency="USD", original_amount=Decimal("1000"), budget_line_id="BL-1")),
            SimpleNamespace(line=SimpleNamespace(currency="EUR", original_amount=Decimal("500"), budget_line_id="BL-2")),
        ]
        self.changes = {
            "BL-1": [
                SimpleNamespace(change=SimpleNamespace(status="approved", amount=Decimal("200"))),
                SimpleNamespace(change=SimpleNamespace(status="pending", amount=Decimal("999"))),
            ],
            "BL-2": [],
        }
        self.funding = [
            SimpleNamespace(funding=SimpleNamespace(currency="USD", amount=Decimal("300"))),
            SimpleNamespace(funding=SimpleNamespace(currency="EUR", amount=Decimal("50"))),
        ]

    def list_lines(self, tenant_id: str, project_id: str):
        return tuple(self.lines)

    def list_changes(self, tenant_id: str, project_id: str, budget_line_id: str):
        return tuple(self.changes[budget_line_id])

    def list_funding(self, tenant_id: str, project_id: str):
        return tuple(self.funding)


def reader(*amounts: tuple[str, object]) -> ProjectMetricReader:
    connection = sqlite3.connect(":memory:")
    issues = SQLiteP6IssueRepository(connection)
    return ProjectMetricReader(issues, CostStore(*amounts), BudgetStore())


def test_open_issue_count_reads_open_and_in_progress_only() -> None:
    metric = reader()
    repository = metric.issue_repository
    for issue_id, status in (
        ("I-1", "open"),
        ("I-2", "in_progress"),
        ("I-3", "resolved"),
        ("I-4", "closed"),
    ):
        repository.create(
            P6Issue(
                scope=SCOPE,
                issue_id=issue_id,
                title=f"Issue {issue_id}",
                description="",
                issue_type="quality",
                status=status,
                priority="normal",
                owner="u-1",
                date_identified="2026-11-12",
                resolution_note="closed out" if status in {"resolved", "closed"} else None,
            ),
            actor_id="u-1",
            occurred_at="2026-11-12T10:00:00+00:00",
        )
    observed = metric.observe(
        tenant_id="T-1",
        project_id="P-1",
        project_revision=7,
        parameter="open_issue_count",
    )
    assert observed == Decimal("2")


def test_expense_actual_total_sums_only_the_requested_currency() -> None:
    metric = reader(
        ("USD", Decimal("900.00")),
        ("USD", None),
        ("USD", Decimal("100.50")),
        ("EUR", Decimal("50.00")),
    )
    assert (
        metric.observe(
            tenant_id="T-1",
            project_id="P-1",
            project_revision=7,
            parameter="expense_actual_total",
            currency="USD",
        )
        == Decimal("1000.50")
    )
    with pytest.raises(KeyError, match="THRESHOLD_CURRENCY_REQUIRED"):
        metric.observe(
            tenant_id="T-1",
            project_id="P-1",
            project_revision=7,
            parameter="expense_actual_total",
        )


def test_budget_balance_applies_approved_changes_and_funding() -> None:
    metric = reader()
    assert (
        metric.observe(
            tenant_id="T-1",
            project_id="P-1",
            project_revision=7,
            parameter="budget_balance",
            currency="USD",
        )
        == Decimal("900")
    )
    assert (
        metric.observe(
            tenant_id="T-1",
            project_id="P-1",
            project_revision=7,
            parameter="budget_balance",
            currency="EUR",
        )
        == Decimal("450")
    )
    with pytest.raises(KeyError, match="THRESHOLD_PARAMETER_UNSUPPORTED"):
        metric.observe(
            tenant_id="T-1",
            project_id="P-1",
            project_revision=7,
            parameter="schedule_variance",
        )
