from datetime import date

from construction_pm.scheduling.activity import Activity


def test_activity_supports_canonical_p6_activity_name() -> None:
    activity = Activity(id="A100", duration=5, name="Foundation Excavation")

    assert activity.name == "Foundation Excavation"


def test_activity_name_is_backward_compatible_with_existing_positional_constructor() -> None:
    activity = Activity("A100", 5, date(2026, 1, 5))

    assert activity.name == ""
    assert activity.actual_start == date(2026, 1, 5)


def test_activity_name_requires_string() -> None:
    try:
        Activity(id="A100", duration=5, name=None)  # type: ignore[arg-type]
    except TypeError as exc:
        assert str(exc) == "name must be a string"
    else:
        raise AssertionError("non-string Activity.name must be rejected")
