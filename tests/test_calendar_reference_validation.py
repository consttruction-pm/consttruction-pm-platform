import pytest

from construction_pm.scheduling.calendar_context import CalendarReference
from construction_pm.scheduling.calendar_system import CalendarSystem


@pytest.mark.parametrize("field", ["calendar_id", "calendar_version"])
@pytest.mark.parametrize("value", [None, 1, True, object(), "   "])
def test_calendar_reference_identity_fields_require_non_empty_strings(field, value):
    values = {"calendar_id": "CAL-1", "calendar_version": "1"}
    values[field] = value
    with pytest.raises(ValueError, match="must be a non-empty string"):
        CalendarReference(**values)


@pytest.mark.parametrize("value", [None, 1, True, object()])
def test_calendar_reference_kind_requires_supported_string(value):
    with pytest.raises(ValueError, match="unsupported calendar kind"):
        CalendarReference("CAL-1", "1", kind=value)


def test_calendar_reference_accepts_explicit_system():
    assert CalendarReference("CAL-1", "1", system=CalendarSystem.GREGORIAN).system is CalendarSystem.GREGORIAN
