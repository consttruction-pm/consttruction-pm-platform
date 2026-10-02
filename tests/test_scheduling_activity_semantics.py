from __future__ import annotations

import pytest

from construction_pm.scheduling.activity import (
    Activity,
    ActivityStatus,
    ActivityType,
)


def test_activity_status_uses_p6_semantic_values() -> None:
    assert [item.value for item in ActivityStatus] == [
        "Not Started",
        "In Progress",
        "Completed",
    ]


def test_activity_type_uses_p6_semantic_values() -> None:
    assert [item.value for item in ActivityType] == [
        "Task Dependent",
        "Resource Dependent",
        "Level of Effort",
        "Start Milestone",
        "Finish Milestone",
        "WBS Summary",
    ]


def test_activity_defaults_preserve_backward_compatible_task_semantics() -> None:
    activity = Activity(id="A-1", duration=2)

    assert activity.status is ActivityStatus.NOT_STARTED
    assert activity.activity_type is ActivityType.TASK_DEPENDENT


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("status", "In Progress"),
        ("activity_type", "Task Dependent"),
    ],
)
def test_activity_rejects_untyped_p6_status_and_type_values(
    field_name: str,
    value: str,
) -> None:
    kwargs = {field_name: value}
    with pytest.raises(TypeError, match=field_name):
        Activity(id="A-1", duration=2, **kwargs)


def test_activity_status_and_type_map_only_supported_p6_wire_values() -> None:
    assert ActivityStatus.from_p6_value("In Progress") is ActivityStatus.IN_PROGRESS
    assert ActivityType.from_p6_value("WBS Summary") is ActivityType.WBS_SUMMARY


def test_activity_status_and_type_reject_unknown_wire_values() -> None:
    with pytest.raises(ValueError, match="unsupported P6 Activity.Status"):
        ActivityStatus.from_p6_value("Running")
    with pytest.raises(ValueError, match="unsupported P6 Activity.Type"):
        ActivityType.from_p6_value("Unknown")
