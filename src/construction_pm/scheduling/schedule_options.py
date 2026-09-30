from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from .calendar_context import RelationshipLagCalendar


class ScheduleMode(str, Enum):
    EARLIEST = "EARLIEST"
    ALAP = "ALAP"


class TotalFloatCalculationType(str, Enum):
    START_FLOAT = "START_FLOAT"
    FINISH_FLOAT = "FINISH_FLOAT"
    SMALLER_FLOAT = "SMALLER_FLOAT"


class CriticalActivityPathType(str, Enum):
    CRITICAL_FLOAT = "CRITICAL_FLOAT"
    LONGEST_PATH = "LONGEST_PATH"


class StartToStartLagCalculationType(str, Enum):
    """P6 start-to-start out-of-sequence lag calculation mode."""

    EARLY_START = "EARLY_START"
    ACTUAL_START = "ACTUAL_START"


class OutOfSequenceScheduleType(str, Enum):
    RETAINED_LOGIC = "RETAINED_LOGIC"
    PROGRESS_OVERRIDE = "PROGRESS_OVERRIDE"
    ACTUAL_DATES = "ACTUAL_DATES"


@dataclass(frozen=True)
class ScheduleOptions:
    """Shared scheduling options with P6-compatible semantics.

    Only options with implemented semantics are applied by this slice.
    Unimplemented P6 options remain explicit in the P6 registry and must not
    be silently ignored by the scheduler.
    """

    mode: ScheduleMode = ScheduleMode.EARLIEST
    compute_total_float_type: TotalFloatCalculationType = (
        TotalFloatCalculationType.START_FLOAT
    )
    critical_activity_float_threshold: int = 0
    critical_activity_path_type: CriticalActivityPathType = (
        CriticalActivityPathType.CRITICAL_FLOAT
    )
    make_open_ended_activities_critical: bool = False
    multiple_float_paths_enabled: bool = False
    maximum_multiple_float_paths: int = 0
    multiple_float_paths_ending_activity_object_id: str | None = None
    multiple_float_paths_use_total_float: bool = True
    start_to_start_lag_calculation_type: StartToStartLagCalculationType = (
        StartToStartLagCalculationType.EARLY_START
    )
    out_of_sequence_schedule_type: OutOfSequenceScheduleType = (
        OutOfSequenceScheduleType.RETAINED_LOGIC
    )
    relationship_lag_calendar: RelationshipLagCalendar = RelationshipLagCalendar.PROJECT_DEFAULT
    use_expected_finish_dates: bool = False
    data_date: date | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.mode, ScheduleMode):
            raise ValueError("mode must be a ScheduleMode")
        if not isinstance(self.compute_total_float_type, TotalFloatCalculationType):
            raise ValueError(
                "compute_total_float_type must be a TotalFloatCalculationType"
            )
        if not isinstance(self.critical_activity_path_type, CriticalActivityPathType):
            raise ValueError(
                "critical_activity_path_type must be a CriticalActivityPathType"
            )
        if isinstance(self.critical_activity_float_threshold, bool):
            raise ValueError("critical_activity_float_threshold must be an integer")
        if not isinstance(self.critical_activity_float_threshold, int):
            raise ValueError("critical_activity_float_threshold must be an integer")
        if self.critical_activity_float_threshold < 0:
            raise ValueError("critical_activity_float_threshold must be non-negative")
        if not isinstance(self.multiple_float_paths_enabled, bool):
            raise ValueError("multiple_float_paths_enabled must be a bool")
        if isinstance(self.maximum_multiple_float_paths, bool) or not isinstance(
            self.maximum_multiple_float_paths, int
        ):
            raise ValueError("maximum_multiple_float_paths must be an integer")
        if not 0 <= self.maximum_multiple_float_paths <= 1000:
            raise ValueError("maximum_multiple_float_paths must be between 0 and 1000")
        if self.multiple_float_paths_ending_activity_object_id is not None and not (
            isinstance(self.multiple_float_paths_ending_activity_object_id, str)
            and self.multiple_float_paths_ending_activity_object_id.strip()
        ):
            raise ValueError("multiple_float_paths_ending_activity_object_id must be a non-empty string")
        if not isinstance(self.multiple_float_paths_use_total_float, bool):
            raise ValueError("multiple_float_paths_use_total_float must be a bool")
        if not isinstance(self.out_of_sequence_schedule_type, OutOfSequenceScheduleType):
            raise ValueError("out_of_sequence_schedule_type must be an OutOfSequenceScheduleType")
        if not isinstance(self.relationship_lag_calendar, RelationshipLagCalendar):
            raise ValueError(
                "relationship_lag_calendar must be a RelationshipLagCalendar"
            )
        if not isinstance(
            self.start_to_start_lag_calculation_type, StartToStartLagCalculationType
        ):
            raise ValueError(
                "start_to_start_lag_calculation_type must be a StartToStartLagCalculationType"
            )
        if not isinstance(self.use_expected_finish_dates, bool):
            raise ValueError("use_expected_finish_dates must be a bool")
        if self.data_date is not None and not isinstance(self.data_date, date):
            raise TypeError("data_date must be a date or None")


def start_to_start_lag_type_from_p6(value: bool) -> StartToStartLagCalculationType:
    """Map the P6 boolean boundary field to the typed Shared Core option."""
    if not isinstance(value, bool):
        raise TypeError("P6 StartToStartLagCalculationType must be a bool")
    return (
        StartToStartLagCalculationType.ACTUAL_START
        if value
        else StartToStartLagCalculationType.EARLY_START
    )


def start_to_start_lag_type_to_p6(value: StartToStartLagCalculationType) -> bool:
    """Map the typed Shared Core option back to the P6 boolean contract."""
    if not isinstance(value, StartToStartLagCalculationType):
        raise TypeError(
            "start_to_start_lag_calculation_type must be a StartToStartLagCalculationType"
        )
    return value is StartToStartLagCalculationType.ACTUAL_START
