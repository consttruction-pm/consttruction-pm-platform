from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class P6OptionDefinition:
    subject_area: str
    field: str
    allowed_values: tuple[str, ...]
    source: str = "Oracle P6 EPPM REST API Release 26"


P6_SCHEDULE_OPTION_CHOICES: tuple[P6OptionDefinition, ...] = (
    P6OptionDefinition(
        "ScheduleOptions",
        "ComputeTotalFloatType",
        ("Start Float", "Finish Float", "Smallest of Start Float and Finish Float"),
    ),
    P6OptionDefinition(
        "ScheduleOptions",
        "CriticalActivityPathType",
        ("Critical Float", "Longest Path"),
    ),
    P6OptionDefinition(
        "ScheduleOptions",
        "OutOfSequenceScheduleType",
        ("Retained Logic", "Progress Override", "Actual Dates"),
    ),
    P6OptionDefinition(
        "ScheduleOptions",
        "RelationshipLagCalendar",
        (
            "Predecessor Activity Calendar",
            "Successor Activity Calendar",
            "24 Hour Calendar",
            "Project Default Calendar",
        ),
    ),
    P6OptionDefinition(
        "Activity",
        "PercentCompleteType",
        ("Physical", "Duration", "Units"),
    ),
)


def schedule_option_choices(field: str) -> tuple[str, ...]:
    for option in P6_SCHEDULE_OPTION_CHOICES:
        if option.field == field:
            return option.allowed_values
    raise KeyError(field)
