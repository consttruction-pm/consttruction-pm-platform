from datetime import date

import pytest

from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.authoritative_schedule import (
    ActivityCalendarAssignment,
    AuthoritativeScheduleInput,
    AuthoritativeScheduleMode,
)
from construction_pm.scheduling.calendar_context import CalendarReference


def make_input(**overrides):
    values = {
        "snapshot_id": "S-1",
        "tenant_id": "T-1",
        "project_id": "P-1",
        "project_revision": 1,
        "mode": AuthoritativeScheduleMode.DATE_BASED,
        "project_calendar": CalendarReference("CAL-1", "1"),
        "activities": (Activity("A-1", 1),),
        "relationships": (),
        "activity_calendar_assignments": (),
        "project_start": date(2026, 10, 1),
    }
    values.update(overrides)
    return AuthoritativeScheduleInput(**values)


@pytest.mark.parametrize("field", ["snapshot_id", "tenant_id", "project_id"])
@pytest.mark.parametrize("value", [None, 1, True, object()])
def test_identity_fields_require_non_empty_strings(field, value):
    with pytest.raises(ValueError, match="must be a non-empty string"):
        make_input(**{field: value})


def test_mode_requires_authoritative_schedule_mode():
    with pytest.raises(TypeError, match="mode must be an AuthoritativeScheduleMode"):
        make_input(mode="DATE_BASED")


def test_activity_calendar_assignment_requires_string_id():
    with pytest.raises(ValueError, match="must be a non-empty string"):
        ActivityCalendarAssignment(None, CalendarReference("CAL-1", "1"))
