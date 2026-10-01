from __future__ import annotations

from dataclasses import replace
from datetime import date
from typing import Mapping, Sequence

from .application.authorization import AuthorizationContext
from .backend_p0.models import BackendScope
from .p6_resource_assignment_repository import P6ResourceAssignment
from .p6_resource_capacity_contract import build_resource_capacity_slices
from .p6_resource_read_api import P6ResourceReadAPI
from .resources.calendar import ResourceCalendar
from .scheduling.leveling_boundary import SchedulerLevelingInput
from .scheduling.resource_leveling import (
    BackwardLevelingActivity,
    LevelingActivity,
    ResourceCapacity,
    ResourceDemand,
    ResourceLevelingOptions,
)


class P6ResourceLevelingReadAdapterError(ValueError):
    """Raised when authoritative P6 resource data cannot form scheduler input."""


def _scope_dict(scope: BackendScope) -> dict[str, object]:
    return {
        "tenant_id": scope.tenant_id,
        "project_id": scope.project_id,
        "project_revision": scope.project_revision,
    }


def _assignment_from_dto(scope: BackendScope, item: dict) -> dict:
    if item.get("contract_version") != "p6-resource-read-api.v1" or item.get("kind") != "resource_assignment":
        raise P6ResourceLevelingReadAdapterError("INVALID_RESOURCE_ASSIGNMENT_CONTRACT")
    if item.get("scope") != _scope_dict(scope):
        raise P6ResourceLevelingReadAdapterError("RESOURCE_ASSIGNMENT_SCOPE_MISMATCH")
    assignment = item.get("assignment")
    if not isinstance(assignment, dict):
        raise P6ResourceLevelingReadAdapterError("INVALID_RESOURCE_ASSIGNMENT")
    return assignment


def _period_from_dto(scope: BackendScope, item: dict) -> dict:
    if item.get("contract_version") != "p6-resource-read-api.v1" or item.get("kind") != "resource_assignment_period":
        raise P6ResourceLevelingReadAdapterError("INVALID_RESOURCE_PERIOD_CONTRACT")
    if item.get("scope") != _scope_dict(scope):
        raise P6ResourceLevelingReadAdapterError("RESOURCE_PERIOD_SCOPE_MISMATCH")
    period = item.get("period")
    if not isinstance(period, dict):
        raise P6ResourceLevelingReadAdapterError("INVALID_RESOURCE_PERIOD")
    return period


def build_scheduler_leveling_input(
    *,
    read_api: P6ResourceReadAPI,
    scope: BackendScope,
    auth_context: AuthorizationContext,
    forward_activities: tuple[LevelingActivity, ...],
    backward_activities: tuple[BackwardLevelingActivity, ...],
    calendars: Mapping[str, ResourceCalendar],
    periods: Sequence[date],
    options: ResourceLevelingOptions,
) -> SchedulerLevelingInput:
    """Adapt authoritative resource read data into the existing Shared Core boundary.

    The adapter performs transport mapping only. Demand comes from
    ResourceAssignment period values exposed by p6-resource-read-api.v1.
    Capacity comes exclusively from ResourceCalendar through the authoritative
    p6-resource-capacity contract. No scheduling, calendar, or leveling
    calculation is performed here.
    """
    scope.validate()
    assignments_dto = read_api.list_assignments(scope, auth_context=auth_context)
    periods_dto = read_api.list_assignment_periods(scope, auth_context=auth_context)

    assignments_by_id: dict[str, dict] = {}
    typed_assignments: list[P6ResourceAssignment] = []
    for item in assignments_dto:
        assignment = _assignment_from_dto(scope, item)
        assignment_id = assignment.get("assignment_id")
        if not isinstance(assignment_id, str) or not assignment_id.strip():
            raise P6ResourceLevelingReadAdapterError("INVALID_ASSIGNMENT_ID")
        if assignment_id in assignments_by_id:
            raise P6ResourceLevelingReadAdapterError("DUPLICATE_ASSIGNMENT_ID")
        assignments_by_id[assignment_id] = assignment
        typed_assignments.append(
            P6ResourceAssignment(
                scope=scope,
                assignment_id=assignment_id,
                activity_id=assignment["activity_id"],
                resource_id=assignment["resource_id"],
                role_id=assignment.get("role_id"),
                units=assignment.get("units"),
                actual_units=assignment.get("actual_units"),
                remaining_units=assignment.get("remaining_units"),
                planned_cost=assignment.get("planned_cost"),
                actual_cost=assignment.get("actual_cost"),
                remaining_cost=assignment.get("remaining_cost"),
                unit=assignment.get("unit"),
                currency=assignment.get("currency"),
                calendar_id=assignment.get("calendar_id"),
                note=assignment.get("note"),
            )
        )
    typed_assignments.sort(key=lambda item: item.assignment_id)

    demand_by_activity: dict[str, list[ResourceDemand]] = {}
    demand_periods: set[date] = set()
    for item in periods_dto:
        period = _period_from_dto(scope, item)
        assignment_id = period.get("assignment_id")
        assignment = assignments_by_id.get(assignment_id)
        if assignment is None:
            raise P6ResourceLevelingReadAdapterError("RESOURCE_PERIOD_ASSIGNMENT_NOT_FOUND")
        period_start = period.get("period_start")
        if not isinstance(period_start, str):
            raise P6ResourceLevelingReadAdapterError("INVALID_PERIOD_START")
        try:
            period_date = date.fromisoformat(period_start)
        except ValueError as exc:
            raise P6ResourceLevelingReadAdapterError("INVALID_PERIOD_START") from exc
        activity_id = period.get("activity_id")
        resource_id = period.get("resource_id")
        if activity_id != assignment["activity_id"] or resource_id != assignment["resource_id"]:
            raise P6ResourceLevelingReadAdapterError("RESOURCE_PERIOD_ASSIGNMENT_MISMATCH")
        demand_periods.add(period_date)
        demand_by_activity.setdefault(activity_id, []).append(
            ResourceDemand(
                resource_id=resource_id,
                period=period_date,
                units=period["units"],
                activity_id=activity_id,
            )
        )

    def attach(activity: LevelingActivity | BackwardLevelingActivity):
        return replace(
            activity,
            resource_demands=tuple(
                sorted(
                    demand_by_activity.get(activity.activity_id, ()),
                    key=lambda item: (item.period, item.resource_id, item.activity_id or ""),
                )
            ),
        )

    forward = tuple(attach(activity) for activity in forward_activities)
    backward = tuple(attach(activity) for activity in backward_activities)

    capacity_periods = tuple(sorted(set(periods) | demand_periods))
    capacity_slices = build_resource_capacity_slices(
        scope,
        tuple(typed_assignments),
        calendars,
        capacity_periods,
    )
    capacities = tuple(
        ResourceCapacity(item.resource_id, item.period, item.units)
        for item in capacity_slices
    )

    return SchedulerLevelingInput(
        forward_activities=forward,
        backward_activities=backward,
        capacities=capacities,
        options=options,
    )


__all__ = [
    "P6ResourceLevelingReadAdapterError",
    "build_scheduler_leveling_input",
]
