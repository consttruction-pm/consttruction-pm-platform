import pytest
from datetime import date, datetime, timezone

from construction_pm.scheduling.constraints import ActivitySecondaryConstraint, SecondaryConstraintType


def test_secondary_constraint_requires_non_empty_string_id():
    for value in (None, "", " " , 1):
        with pytest.raises(ValueError):
            ActivitySecondaryConstraint(value, SecondaryConstraintType.START_ON, date(2026, 1, 1))


def test_secondary_constraint_rejects_datetime_as_date():
    with pytest.raises(TypeError):
        ActivitySecondaryConstraint("A", SecondaryConstraintType.START_ON, datetime(2026, 1, 1, tzinfo=timezone.utc))


def test_secondary_constraint_requires_enum_type():
    with pytest.raises(TypeError):
        ActivitySecondaryConstraint("A", "Start On", date(2026, 1, 1))


def test_secondary_constraint_accepts_valid_fields():
    item = ActivitySecondaryConstraint("A", SecondaryConstraintType.START_ON, date(2026, 1, 1))
    assert item.activity_id == "A"
