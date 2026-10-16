from __future__ import annotations

"""Bounded adapter for scheduling fields stored in ActivityMaster.

This adapter deliberately supports only the DATE_BASED core model and maps only
fields present in ActivityMaster. Activity name/status/type, relationships,
calendars, constraints, and resource assignments live outside this record and
must be joined by an application-layer materializer before production use.
TIME_AWARE records need a separate adapter; this module never truncates them.
"""

from datetime import date, datetime
from decimal import Decimal

from .activity_master_repository import ActivityMaster
from .scheduling.activity import Activity
from .scheduling.time_duration import DurationUnit


class ActivityMasterScheduleAdapterError(ValueError):
    """Raised when an Activity Master record cannot be mapped without loss."""


def _date_only(value: date | datetime | None, field: str) -> date | None:
    if value is None:
        return None
    # datetime is a subclass of date; reject it explicitly to avoid dropping
    # time-of-day or timezone information at the date-based boundary.
    if isinstance(value, datetime) or not isinstance(value, date):
        raise ActivityMasterScheduleAdapterError(f"TIME_AWARE_VALUE_NOT_SUPPORTED:{field}")
    return value


def _whole_working_days(value: Decimal, unit: DurationUnit, field: str) -> int:
    if unit is not DurationUnit.WORKING_DAY:
        raise ActivityMasterScheduleAdapterError(f"UNSUPPORTED_DURATION_UNIT:{field}")
    if value != value.to_integral_value():
        raise ActivityMasterScheduleAdapterError(f"FRACTIONAL_WORKING_DAYS_NOT_SUPPORTED:{field}")
    return int(value)


def activity_master_to_date_activity(record: ActivityMaster) -> Activity:
    """Map the supported fields from one record to a date-based Activity.

    This is not a complete project-activity materializer: fields absent from
    ActivityMaster take the Activity model defaults and must be supplied by the
    caller's broader persistence adapter when authoritative. Unsupported units,
    fractional working days, and datetime values are rejected rather than rounded.
    """
    try:
        record.validate()
    except (TypeError, ValueError) as exc:
        raise ActivityMasterScheduleAdapterError("INVALID_ACTIVITY_MASTER") from exc

    duration = _whole_working_days(record.duration_value, record.duration_unit, "duration")
    return Activity(
        id=record.activity_id,
        duration=duration,
        actual_start=_date_only(record.actual_start, "actual_start"),
        actual_finish=_date_only(record.actual_finish, "actual_finish"),
        remaining_duration=record.remaining_duration,
        remaining_start=_date_only(record.remaining_start, "remaining_start"),
        percent_complete=record.percent_complete,
        percent_complete_type=record.percent_complete_type,
        expected_finish=_date_only(record.expected_finish, "expected_finish"),
        original_duration=record.original_duration,
        planned_finish=_date_only(record.planned_finish, "planned_finish"),
        leveling_priority=record.leveling_priority,
    )


__all__ = ["ActivityMasterScheduleAdapterError", "activity_master_to_date_activity"]
