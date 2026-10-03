from datetime import date
from decimal import Decimal

from construction_pm.portfolio_query import InMemoryPortfolioQueryAdapter, PortfolioProjectSnapshot
from construction_pm.resources.calendar import ResourceCalendar
from construction_pm.resources.curves import build_resource_curve
from construction_pm.resources.models import ResourcePeriodValue
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.calendar_context import CalendarReference, CalendarResolverRegistry, SchedulingCalendarContext


def test_stage_33_2_calendar_context_selects_versioned_authoritative_resolver() -> None:
    ref = CalendarReference("project-calendar", "v7")
    resolver = WorkingTimeResolver(WorkingCalendar())
    registry = CalendarResolverRegistry(day_resolvers={"project-calendar@v7": resolver})
    context = SchedulingCalendarContext(project=ref)

    assert context.effective_activity() == ref
    assert context.effective_relationship_lag() == ref
    assert registry.resolve(context.effective_activity()) is resolver


def test_stage_33_2_calendar_context_preserves_time_phased_resource_values() -> None:
    calendar = ResourceCalendar(
        id="resource-calendar-v7",
        working_weekdays=frozenset({0, 1, 2, 3, 4}),
        daily_capacity=Decimal("8"),
    )
    values = [
        ResourcePeriodValue("R-1", date(2026, 9, 28), Decimal("8"), Decimal("200")),
        ResourcePeriodValue("R-1", date(2026, 9, 29), Decimal("4"), Decimal("100")),
    ]

    assert calendar.capacity_on(date(2026, 9, 28)) == Decimal("8")
    assert calendar.capacity_on(date(2026, 9, 27)) == Decimal("0")
    curve = build_resource_curve(values)
    assert curve[date(2026, 9, 28)] == (Decimal("8"), Decimal("200"))
    assert curve[date(2026, 9, 29)] == (Decimal("4"), Decimal("100"))


def test_stage_33_2_reporting_read_model_passes_authoritative_metrics_through() -> None:
    metrics = {
        "planned_cost": "250.00",
        "actual_cost": "150.00",
        "remaining_cost": "100.00",
        "source_revision": 12,
    }
    snapshot = PortfolioProjectSnapshot(
        tenant_id="tenant-1",
        project_id="project-1",
        as_of="2026-09-29",
        status="active",
        metrics=metrics,
    )
    result = InMemoryPortfolioQueryAdapter((snapshot,)).list_projects("tenant-1")

    assert result[0].metrics is metrics
    assert result[0].metrics["planned_cost"] == "250.00"
    assert result[0].metrics["actual_cost"] == "150.00"
    assert result[0].metrics["remaining_cost"] == "100.00"
    assert result[0].metrics["source_revision"] == 12
