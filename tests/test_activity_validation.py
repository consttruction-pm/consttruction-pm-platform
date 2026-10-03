import pytest
from datetime import date

from construction_pm.scheduling.activity import Activity


@pytest.mark.parametrize("value", [True, False])
def test_activity_rejects_boolean_integer_fields(value):
    with pytest.raises(TypeError):
        Activity("A", value)
    with pytest.raises(TypeError):
        Activity("A", 1, remaining_duration=value)


@pytest.mark.parametrize("value", [True, False])
def test_activity_rejects_boolean_percent_complete(value):
    with pytest.raises(TypeError):
        Activity("A", 1, percent_complete=value)


@pytest.mark.parametrize("value", [None, "", 1, True])
def test_activity_requires_non_empty_string_id(value):
    with pytest.raises(ValueError):
        Activity(value, 1)


def test_activity_accepts_valid_primitive_fields():
    activity = Activity("A", 2, remaining_duration=1, percent_complete=50)
    assert activity.duration == 2
