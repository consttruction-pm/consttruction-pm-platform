from __future__ import annotations

from typing import Any

from .backend_p0.models import FieldInspection, PunchItem, QualityRecord, SafetyObservation


_TRANSITIONS: dict[str, dict[str, frozenset[str]]] = {
    "field_inspection": {
        "draft": frozenset({"scheduled", "in_progress", "cancelled"}),
        "scheduled": frozenset({"in_progress", "cancelled"}),
        "in_progress": frozenset({"completed", "cancelled"}),
        "completed": frozenset(),
        "cancelled": frozenset(),
    },
    "quality_record": {
        "open": frozenset({"in_progress", "cancelled"}),
        "in_progress": frozenset({"pending_verification", "rejected", "cancelled"}),
        "pending_verification": frozenset({"accepted", "rejected"}),
        "accepted": frozenset({"closed"}),
        "rejected": frozenset({"open", "in_progress", "cancelled"}),
        "closed": frozenset(),
        "cancelled": frozenset(),
    },
    "safety_observation": {
        "open": frozenset({"in_progress", "resolved", "cancelled"}),
        "in_progress": frozenset({"resolved", "cancelled"}),
        "resolved": frozenset({"closed"}),
        "closed": frozenset(),
        "cancelled": frozenset(),
    },
    "punch_item": {
        "open": frozenset({"in_progress", "cancelled"}),
        "in_progress": frozenset({"ready_for_verification", "cancelled"}),
        "ready_for_verification": frozenset({"closed", "rejected"}),
        "rejected": frozenset({"in_progress", "cancelled"}),
        "closed": frozenset(),
        "cancelled": frozenset(),
    },
}

_RESOURCE_TYPES = {
    FieldInspection: "field_inspection",
    QualityRecord: "quality_record",
    SafetyObservation: "safety_observation",
    PunchItem: "punch_item",
}


class FieldAssuranceTransitionError(ValueError):
    pass


def assert_transition(current: Any, proposed: Any) -> None:
    resource_type = _RESOURCE_TYPES.get(type(proposed))
    if resource_type is None or type(current) is not type(proposed):
        return

    current_status = current.status
    proposed_status = proposed.status
    if current_status == proposed_status:
        return

    allowed = _TRANSITIONS[resource_type].get(current_status, frozenset())
    if proposed_status not in allowed:
        code = resource_type.upper()
        raise FieldAssuranceTransitionError(
            f"INVALID_{code}_TRANSITION:{current_status}->{proposed_status}"
        )
