from __future__ import annotations

"""Fail-closed adapter from persisted schedule relationships to DATE_BASED core."""

from .relationship_master_repository import RelationshipMaster
from .scheduling.relationships import Relationship
from .scheduling.time_duration import DurationUnit


class RelationshipMasterScheduleAdapterError(ValueError):
    """Raised when a stored relationship cannot be represented without loss."""


def relationship_master_to_date_relationship(record: RelationshipMaster) -> Relationship:
    """Convert a persisted relationship only when its lag is whole working days.

    Working-hour and fractional-day lags need a calendar-aware conversion and
    are deliberately rejected rather than rounded or interpreted by assumption.
    """
    try:
        record.validate()
    except (TypeError, ValueError) as exc:
        raise RelationshipMasterScheduleAdapterError("INVALID_RELATIONSHIP_MASTER") from exc

    if record.lag_unit is not DurationUnit.WORKING_DAY:
        raise RelationshipMasterScheduleAdapterError("UNSUPPORTED_LAG_UNIT")
    if record.lag_value != record.lag_value.to_integral_value():
        raise RelationshipMasterScheduleAdapterError("FRACTIONAL_WORKING_DAY_LAG_NOT_SUPPORTED")

    return Relationship(
        predecessor_id=record.predecessor_id,
        successor_id=record.successor_id,
        type=record.relationship_type,
        lag=int(record.lag_value),
    )


__all__ = [
    "RelationshipMasterScheduleAdapterError",
    "relationship_master_to_date_relationship",
]
