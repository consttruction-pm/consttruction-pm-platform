"""Authoritative observed values for threshold monitoring.

The threshold engine must never ask the browser for the number it compares.
This reader derives each supported parameter from the same project-scoped
repositories the rest of the platform uses:

- ``open_issue_count``: issues in ``open`` or ``in_progress``.
- ``expense_actual_total``: stored actual expense amounts for one currency.
- ``budget_balance``: derived current budget (original + approved changes)
  minus recorded funding for one currency.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .backend_p0.models import BackendScope
from .p6_issue_repository import P6IssueRepository

OPEN_ISSUE_STATUSES = ("open", "in_progress")


@dataclass(frozen=True)
class ProjectMetricReader:
    """Reads threshold parameters from authoritative project stores."""

    issue_repository: P6IssueRepository
    cost_store: object
    budget_store: object

    def observe(
        self,
        *,
        tenant_id: str,
        project_id: str,
        project_revision: int,
        parameter: str,
        currency: str | None = None,
    ) -> Decimal:
        if parameter == "open_issue_count":
            scope = BackendScope(tenant_id, project_id, project_revision)
            total = 0
            for status in OPEN_ISSUE_STATUSES:
                total += len(self.issue_repository.list(scope, status=status))
            return Decimal(total)
        if parameter == "expense_actual_total":
            if not currency:
                raise KeyError("THRESHOLD_CURRENCY_REQUIRED")
            total = Decimal("0")
            for stored in self.cost_store.list_expenses(tenant_id, project_id):  # type: ignore[attr-defined]
                expense = stored.expense
                if expense.currency != currency:
                    continue
                if expense.actual_amount is not None:
                    total += expense.actual_amount
            return total
        if parameter == "budget_balance":
            if not currency:
                raise KeyError("THRESHOLD_CURRENCY_REQUIRED")
            current = Decimal("0")
            funding = Decimal("0")
            for stored in self.budget_store.list_lines(tenant_id, project_id):  # type: ignore[attr-defined]
                if stored.line.currency != currency:
                    continue
                current += stored.line.original_amount
                for change in self.budget_store.list_changes(  # type: ignore[attr-defined]
                    tenant_id, project_id, stored.line.budget_line_id
                ):
                    if change.change.status == "approved":
                        current += change.change.amount
            for stored in self.budget_store.list_funding(  # type: ignore[attr-defined]
                tenant_id, project_id
            ):
                if stored.funding.currency == currency:
                    funding += stored.funding.amount
            return current - funding
        raise KeyError("THRESHOLD_PARAMETER_UNSUPPORTED")


__all__ = ["ProjectMetricReader"]
