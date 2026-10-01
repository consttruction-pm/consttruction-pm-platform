from datetime import date
from decimal import Decimal

import pytest

from construction_pm.scheduling.external_resource_assignments import (
    ExternalResourceAssignment,
    select_resource_assignments_for_scheduling,
)
from construction_pm.scheduling.resource_leveling import ResourceLevelingError


def _assignment(project_id: str, resource_id: str) -> ExternalResourceAssignment:
    return ExternalResourceAssignment(
        project_id=project_id,
        resource_id=resource_id,
        period=date(2026, 10, 1),
        units=Decimal("1"),
        activity_id="A",
    )


def test_external_assignments_are_excluded_when_option_disabled():
    internal = _assignment("P1", "R1")
    external = _assignment("P2", "R2")
    result = select_resource_assignments_for_scheduling(
        (internal, external),
        scheduled_project_id="P1",
        include_external_res_ass=False,
    )
    assert [(d.resource_id, d.units) for d in result] == [("R1", Decimal("1"))]


def test_external_assignments_are_included_when_option_enabled():
    internal = _assignment("P1", "R1")
    external = _assignment("P2", "R2")
    result = select_resource_assignments_for_scheduling(
        (internal, external),
        scheduled_project_id="P1",
        include_external_res_ass=True,
    )
    assert [(d.resource_id, d.units) for d in result] == [
        ("R1", Decimal("1")),
        ("R2", Decimal("1")),
    ]


def test_invalid_assignment_source_is_rejected():
    with pytest.raises(ResourceLevelingError, match="INVALID_EXTERNAL_RESOURCE_ASSIGNMENT"):
        select_resource_assignments_for_scheduling(
            (object(),),
            scheduled_project_id="P1",
            include_external_res_ass=True,
        )
