from datetime import date
from decimal import Decimal

import pytest

from construction_pm.project_portability import (
    ProjectPortabilitySnapshot,
    export_project,
    import_project,
    portability_fingerprint,
)
from construction_pm.resources.calculator import calculate_assignment_control
from construction_pm.resources.evm_bridge import ResourceEVMInput, build_resource_evm_result
from construction_pm.resources.models import CostBasis, Resource, ResourceAssignment, ResourceRate
from construction_pm.resources.persistence import ContextScopedSQLiteResourceRepository, OptimisticLockError
from construction_pm.resources.context import ProjectContext


AS_OF = date(2026, 9, 27)


def _resource() -> Resource:
    return Resource(
        id="R-1",
        code="LAB-01",
        name="Labor",
        resource_type="labor",
        unit="hour",
        rates=[ResourceRate(Decimal("25.00"), CostBasis.PER_HOUR, effective_from=AS_OF)],
        calendar_id="calendar-1",
    )


def test_stage_33_2_resource_cost_to_evm_bridge_preserves_authoritative_values() -> None:
    resource = _resource()
    assignment = ResourceAssignment(
        activity_id="A-1",
        resource_id="R-1",
        planned_units=Decimal("10"),
        actual_units=Decimal("6"),
        remaining_units=Decimal("4"),
    )

    control = calculate_assignment_control(resource, assignment, AS_OF)
    evm = build_resource_evm_result(
        ResourceEVMInput(
            pv=Decimal("200"),
            ev=Decimal("180"),
            ac=control.actual_cost,
            remaining_resource_cost=control.remaining_cost,
            bac=Decimal("250"),
        )
    )

    assert control.planned_cost == Decimal("250.00")
    assert control.actual_cost == Decimal("150.00")
    assert control.remaining_cost == Decimal("100.00")
    assert evm.ac == control.actual_cost
    assert evm.etc == control.remaining_cost
    assert evm.eac == Decimal("250.00")


def test_stage_33_2_revision_conflict_is_rejected_for_stale_assignment_update() -> None:
    context = ProjectContext("tenant-1", "company-1", "project-1")
    repo = ContextScopedSQLiteResourceRepository(__import__("sqlite3").connect(":memory:"))
    repo.save_resource(context, _resource())
    assignment = ResourceAssignment(
        activity_id="A-1",
        resource_id="R-1",
        planned_units=Decimal("10"),
        actual_units=Decimal("2"),
    )
    repo.save_assignment(context, assignment)

    with pytest.raises(OptimisticLockError):
        repo.save_assignment(context, assignment, expected_revision=0)


def test_stage_33_2_project_context_prevents_cross_project_assignment_leakage() -> None:
    connection = __import__("sqlite3").connect(":memory:")
    repo = ContextScopedSQLiteResourceRepository(connection)
    project_a = ProjectContext("tenant-1", "company-1", "project-a")
    project_b = ProjectContext("tenant-1", "company-1", "project-b")
    repo.save_resource(project_a, _resource())
    repo.save_resource(project_b, _resource())
    assignment = ResourceAssignment(
        activity_id="A-1",
        resource_id="R-1",
        planned_units=Decimal("8"),
        actual_units=Decimal("3"),
    )
    repo.save_assignment(project_a, assignment)

    assert repo.list_assignments(project_a) == [assignment]
    assert repo.list_assignments(project_b) == []


def test_stage_33_2_portability_round_trip_keeps_calculation_context_deterministic() -> None:
    snapshot = ProjectPortabilitySnapshot(
        schema_version="project-portability.v1",
        tenant_id="tenant-1",
        project_id="project-1",
        project_revision=7,
        calendar_context={"calendar_id": "calendar-1", "calendar_version": "3"},
        scheduling_settings={"timezone": "UTC", "week_start": 6},
        calculation_settings={"resource_cost_schema_version": "1", "currency": "USD"},
        resource_cost_config={"rounding": "0.01", "rate_version": 4},
        module_refs={"resource": {"revision": 12}, "evm": {"revision": 9}},
    )

    exported = export_project(snapshot)
    reloaded = import_project(exported)

    assert export_project(reloaded) == exported
    assert portability_fingerprint(reloaded) == portability_fingerprint(snapshot)
    assert reloaded.calendar_context["calendar_version"] == "3"
    assert reloaded.resource_cost_config["rate_version"] == 4
