import pytest
from datetime import date, datetime

from construction_pm.scheduling.constraints import ActivityConstraint, ConstraintType


def test_activity_constraint_requires_typed_fields():
    with pytest.raises(ValueError):
        ActivityConstraint("", ConstraintType.MANDATORY_START, date(2026, 1, 1))
    with pytest.raises(TypeError):
        ActivityConstraint("A", "MANDATORY_START", date(2026, 1, 1))
    with pytest.raises(TypeError):
        ActivityConstraint("A", ConstraintType.MANDATORY_START, datetime(2026, 1, 1))


def test_activity_constraint_accepts_valid_fields():
    item = ActivityConstraint("A", ConstraintType.MANDATORY_START, date(2026, 1, 1))
    assert item.activity_id == "A"
