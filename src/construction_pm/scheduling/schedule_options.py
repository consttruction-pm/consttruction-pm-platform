from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import math
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


class PrioritySortOrder(str, Enum):
    """P6 resource-leveling priority direction."""

    ASCENDING = "ASCENDING"
    DESCENDING = "DESCENDING"


@dataclass(frozen=True)
class PriorityListItem:
    """Typed P6 resource-leveling priority entry."""

    field_name: str
    sort_order: PrioritySortOrder = PrioritySortOrder.ASCENDING

    def __post_init__(self) -> None:
        if not isinstance(self.field_name, str) or not self.field_name.strip():
            raise ValueError("field_name must be a non-empty string")
        if not isinstance(self.sort_order, PrioritySortOrder):
            raise ValueError("sort_order must be a PrioritySortOrder")


class OutOfSequenceScheduleType(str, Enum):
    RETAINED_LOGIC = "RETAINED_LOGIC"
    PROGRESS_OVERRIDE = "PROGRESS_OVERRIDE"
    ACTUAL_DATES = "ACTUAL_DATES"


@dataclass(frozen=True)
class ScheduleOptions:
    """Shared scheduling options with P6-compatible typed semantics.

    Fields that require multi-project/resource-leveling infrastructure are
    represented explicitly here so persistence/API layers cannot silently
    discard them. Their calculation behavior is enabled only by the
    corresponding scheduler capability; they must not fall back to another
    option's semantics.
    """

    mode: ScheduleMode = ScheduleMode.EARLIEST
    compute_total_float_type: TotalFloatCalculationType = (
        TotalFloatCalculationType.START_FLOAT
    )
    critical_activity_float_threshold: float = 0.0
    critical_activity_path_type: CriticalActivityPathType = (
        CriticalActivityPathType.CRITICAL_FLOAT
    )
    make_open_ended_activities_critical: bool = False
    multiple_float_paths_enabled: bool = False
    maximum_multiple_float_paths: int = 0
    multiple_float_paths_ending_activity_object_id: str | None = None
    multiple_float_paths_ending_activity_short_name: str | None = None
    multiple_float_paths_use_total_float: bool = True
    min_float_to_preserve: int = 0
    out_of_sequence_schedule_type: OutOfSequenceScheduleType = (
        OutOfSequenceScheduleType.RETAINED_LOGIC
    )
    start_to_start_lag_calculation_type: StartToStartLagCalculationType = (
        StartToStartLagCalculationType.EARLY_START
    )
    relationship_lag_calendar: RelationshipLagCalendar = RelationshipLagCalendar.PROJECT_DEFAULT
    use_expected_finish_dates: bool = False
    recalculate_resource_costs: bool = False
    calculate_float_based_on_finish_date: bool = False
    ignore_other_project_relationships: bool = False
    include_external_res_ass: bool = False
    level_all_resources: bool = False
    level_within_float: bool = False
    over_allocation_percentage: float = 0.0
    resource_list: str | None = None
    priority_list: tuple[PriorityListItem, ...] | None = None
    external_project_priority_limit: int = 0
    preserve_scheduled_early_and_late_dates: bool = False
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
        if isinstance(self.critical_activity_float_threshold, bool) or not isinstance(self.critical_activity_float_threshold, (int, float)):
            raise ValueError("critical_activity_float_threshold must be numeric")
        if not math.isfinite(float(self.critical_activity_float_threshold)):
            raise ValueError("critical_activity_float_threshold must be finite")
        if float(self.critical_activity_float_threshold) < 0:
            raise ValueError("critical_activity_float_threshold must be non-negative")

        for name in (
            "make_open_ended_activities_critical",
            "multiple_float_paths_enabled",
            "multiple_float_paths_use_total_float",
            "use_expected_finish_dates",
            "recalculate_resource_costs",
            "calculate_float_based_on_finish_date",
            "ignore_other_project_relationships",
            "include_external_res_ass",
            "level_all_resources",
            "level_within_float",
            "preserve_scheduled_early_and_late_dates",
        ):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"{name} must be a bool")

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
            raise ValueError(
                "multiple_float_paths_ending_activity_object_id must be a non-empty string"
            )

        if self.multiple_float_paths_ending_activity_short_name is not None and not (isinstance(self.multiple_float_paths_ending_activity_short_name, str) and self.multiple_float_paths_ending_activity_short_name.strip()):
            raise ValueError("multiple_float_paths_ending_activity_short_name must be a non-empty string")

        if isinstance(self.min_float_to_preserve, bool) or not isinstance(
            self.min_float_to_preserve, int
        ):
            raise ValueError("min_float_to_preserve must be an integer")
        if self.min_float_to_preserve < 0:
            raise ValueError("min_float_to_preserve must be non-negative")

        if not isinstance(
            self.out_of_sequence_schedule_type, OutOfSequenceScheduleType
        ):
            raise ValueError(
                "out_of_sequence_schedule_type must be an OutOfSequenceScheduleType"
            )
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

        if isinstance(self.over_allocation_percentage, bool) or not isinstance(
            self.over_allocation_percentage, (int, float)
        ):
            raise ValueError("over_allocation_percentage must be numeric")
        if not math.isfinite(float(self.over_allocation_percentage)):
            raise ValueError("over_allocation_percentage must be finite")
        if not 0 <= float(self.over_allocation_percentage) <= 100:
            raise ValueError("over_allocation_percentage must be between 0 and 100")

        if isinstance(self.external_project_priority_limit, bool) or not isinstance(
            self.external_project_priority_limit, int
        ):
            raise ValueError("external_project_priority_limit must be an integer")
        if not 0 <= self.external_project_priority_limit <= 100:
            raise ValueError("external_project_priority_limit must be between 0 and 100")

        if self.resource_list is not None and not (
            isinstance(self.resource_list, str) and self.resource_list.strip()
        ):
            raise ValueError("resource_list must be a non-empty string or None")

        if self.priority_list is not None:
            if not isinstance(self.priority_list, tuple) or not self.priority_list:
                raise ValueError("priority_list must be a non-empty tuple of PriorityListItem")
            if not all(isinstance(item, PriorityListItem) for item in self.priority_list):
                raise ValueError("priority_list must contain only PriorityListItem values")

        if self.data_date is not None and (not isinstance(self.data_date, date) or isinstance(self.data_date, datetime)):
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
