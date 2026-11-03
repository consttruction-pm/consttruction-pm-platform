"""Application service: persisted rate facts -> leveling cost inputs.

The scheduling core must never read a repository. This service runs at the
application boundary, loads the scoped assignments and the active effective-
dated rate facts, and binds them into immutable ``LevelingCostInputs``.

Rules are deliberately strict:

* a resource contributes a price only from its registered rate facts; an
  assignment never invents a rate or converts a currency;
* a priced assignment must carry its planned units, because a demand rate
  (Units/Time) is not a total quantity and cannot be substituted;
* one resource's active facts must share a single unit label, since the shared
  ``Resource`` carries one unit for the resource;
* assignments whose resource has no registered rate fact are left out rather
  than priced with an assumed zero.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .backend_p0.models import BackendScope
from .p6_resource_assignment_repository import (
    P6ResourceAssignment,
    P6ResourceAssignmentRepository,
)
from .p6_resource_rate_repository import (
    P6ResourceRateRecord,
    P6ResourceRateRepository,
)
from .resources.models import Resource, ResourceRate, ResourceType
from .scheduling.leveling_cost_recalculation import (
    LevelingCostAssignment,
    LevelingCostInputs,
)


class P6ResourceLevelingCostError(ValueError):
    """Raised when persisted facts cannot prove post-leveling costs."""


@dataclass(frozen=True)
class P6ResourceLevelingCostService:
    rate_repository: P6ResourceRateRepository
    assignment_repository: P6ResourceAssignmentRepository
    transaction_manager: object

    def build(self, scope: BackendScope) -> LevelingCostInputs:
        with self.transaction_manager.transaction():
            rate_records = self.rate_repository.list(scope)
            assignments = self.assignment_repository.list(scope)

        resources = _resources_from_records(rate_records)
        cost_assignments = tuple(
            _cost_assignment(assignment)
            for assignment in assignments
            if assignment.resource_id in resources
        )
        if not cost_assignments:
            raise P6ResourceLevelingCostError("LEVELING_COST_INPUTS_EMPTY")
        return LevelingCostInputs(
            assignments=cost_assignments,
            resources=resources,
            project_currency=None,
        )


def _resources_from_records(
    records: tuple[P6ResourceRateRecord, ...],
) -> dict[str, Resource]:
    grouped: dict[str, list[P6ResourceRateRecord]] = {}
    for record in records:
        grouped.setdefault(record.fact.resource_id, []).append(record)
    resources: dict[str, Resource] = {}
    for resource_id, items in sorted(grouped.items()):
        ordered = tuple(
            sorted(items, key=lambda item: item.fact.effective_from)
        )
        units = {item.fact.unit for item in ordered}
        if len(units) != 1:
            raise P6ResourceLevelingCostError(
                f"RESOURCE_RATE_UNIT_MISMATCH:{resource_id}"
            )
        resources[resource_id] = Resource(
            id=resource_id,
            code=resource_id,
            name=resource_id,
            resource_type=ResourceType.OTHER,
            unit=next(iter(units)),
            rates=[
                item.fact.to_resource_rate(version=index + 1)
                for index, item in enumerate(ordered)
            ],
        )
    return resources


def _cost_assignment(
    assignment: P6ResourceAssignment,
) -> LevelingCostAssignment:
    if assignment.units is None:
        raise P6ResourceLevelingCostError(
            f"LEVELING_COST_ASSIGNMENT_UNITS_MISSING:{assignment.assignment_id}"
        )
    if not isinstance(assignment.units, Decimal):
        raise P6ResourceLevelingCostError(
            f"INVALID_ASSIGNMENT_UNITS:{assignment.assignment_id}"
        )
    return LevelingCostAssignment(
        assignment_id=assignment.assignment_id,
        activity_id=assignment.activity_id,
        resource_id=assignment.resource_id,
        planned_units=assignment.units,
        currency=assignment.currency,
    )


def resource_rates_for(
    records: tuple[P6ResourceRateRecord, ...],
    resource_id: str,
) -> tuple[ResourceRate, ...]:
    """Project one resource's active facts into shared-model rate versions."""
    resource = _resources_from_records(
        tuple(record for record in records if record.fact.resource_id == resource_id)
    ).get(resource_id)
    if resource is None:
        raise P6ResourceLevelingCostError(
            f"RESOURCE_RATE_NOT_REGISTERED:{resource_id}"
        )
    return tuple(resource.rates)


__all__ = [
    "P6ResourceLevelingCostError",
    "P6ResourceLevelingCostService",
    "resource_rates_for",
]
