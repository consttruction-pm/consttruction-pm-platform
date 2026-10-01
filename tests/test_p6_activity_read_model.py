from decimal import Decimal
from types import SimpleNamespace

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_activity_read_model import P6_ACTIVITY_READ_MODEL_VERSION, P6ActivityReadModelService


def test_activity_read_model_maps_authoritative_sources_without_calculation():
    scope = BackendScope("tenant-a", "project-a", 7)
    sources = SimpleNamespace(
        list_expenses=lambda scope, activity_id: (
            SimpleNamespace(expense_id="e-2", name="B", category="material", activity_id=activity_id, expense_date="2026-10-02",
                            planned_cost=Decimal("20.50"), actual_cost=Decimal("3.25"), remaining_cost=Decimal("17.25"), currency="USD"),
            SimpleNamespace(expense_id="e-1", name="A", category="labor", activity_id=activity_id, expense_date="2026-10-01",
                            planned_cost=Decimal("10.00"), actual_cost=None, remaining_cost=Decimal("10.00"), currency="USD"),
        ),
        list_actuals=lambda scope, activity_id: (
            SimpleNamespace(actual_id="a-2", activity_id=activity_id, period_id="p-2", actual_units=Decimal("2.5"), actual_cost=Decimal("8.00"), unit="h", currency="USD"),
            SimpleNamespace(actual_id="a-1", activity_id=activity_id, period_id="p-1", actual_units=Decimal("1.5"), actual_cost=Decimal("4.00"), unit="h", currency="USD"),
        ),
        list_baselines=lambda scope: (
            SimpleNamespace(baseline_id="b-2", name="Secondary", baseline_type="SECONDARY", source_revision=6, created_at="2026-10-01T02:00:00Z", notes=None),
            SimpleNamespace(baseline_id="b-1", name="Primary", baseline_type="PRIMARY", source_revision=5, created_at="2026-10-01T01:00:00Z", notes="baseline"),
        ),
    )
    result = P6ActivityReadModelService(sources).read(scope, "A-100")

    assert P6_ACTIVITY_READ_MODEL_VERSION == "p6-activity-read-model.v1"
    assert result.scope == scope
    assert result.activity_id == "A-100"
    assert [item["expense_id"] for item in result.cost_entries] == ["e-1", "e-2"]
    assert [item["actual_id"] for item in result.actual_entries] == ["a-1", "a-2"]
    assert [item["baseline_id"] for item in result.baseline_entries] == ["b-1", "b-2"]
    assert result.cost_entries[0]["planned_cost"] == "10.00"
    assert result.actual_entries[1]["actual_cost"] == "8.00"
    assert result.evm["status"] == "unavailable"
    assert result.evm["calculation_owner"] == "shared_core"
