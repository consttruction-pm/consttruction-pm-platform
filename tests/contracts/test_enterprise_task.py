import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from construction_pm.enterprise_task import (
    EnterpriseTask,
    EnterpriseTaskError,
    EnterpriseTaskPriority,
    EnterpriseTaskReference,
    EnterpriseTaskReferenceType,
    EnterpriseTaskStatus,
)


NOW = datetime(2026, 11, 14, 8, 0, tzinfo=timezone.utc)


def task(**overrides: object) -> EnterpriseTask:
    values: dict[str, object] = {
        "task_id": "task-1",
        "tenant_id": "tenant-1",
        "title": "Review submitted progress",
        "created_by_user_id": "user-1",
        "created_at": NOW,
    }
    values.update(overrides)
    return EnterpriseTask(**values)


def test_contract_is_versioned_closed_and_has_explicit_tenant_scope() -> None:
    contract = json.loads(
        (Path(__file__).parents[2] / "shared/contracts/enterprise-task.v1.schema.json").read_text()
    )
    assert contract["$schema"].endswith("/draft/2020-12/schema")
    assert contract["$id"].endswith("/enterprise-task/v1")
    assert contract["additionalProperties"] is False
    assert contract["properties"]["contract_version"]["const"] == "cubi-enterprise-task.v1"
    assert "tenant_id" in contract["required"]
    assert contract["properties"]["related_refs"]["items"]["$ref"] == "#/$defs/taskReference"


def test_valid_personal_team_and_project_tasks_are_supported() -> None:
    task().validate()
    task(assigned_user_id="user-2").validate()
    task(assigned_team_id="team-1").validate()
    task(project_id="project-1").validate()


def test_assignment_cannot_target_both_a_person_and_a_team() -> None:
    with pytest.raises(EnterpriseTaskError, match="ENTERPRISE_TASK_MULTIPLE_ASSIGNEES"):
        task(assigned_user_id="user-2", assigned_team_id="team-1").validate()


def test_timestamps_must_be_timezone_aware() -> None:
    with pytest.raises(EnterpriseTaskError, match="CREATED_AT_MUST_BE_TIMEZONE_AWARE"):
        task(created_at=datetime(2026, 11, 14, 8, 0)).validate()
    with pytest.raises(EnterpriseTaskError, match="DUE_AT_MUST_BE_TIMEZONE_AWARE"):
        task(due_at=datetime(2026, 11, 15, 8, 0)).validate()


def test_revision_rejects_bool_negative_and_unsafe_integer() -> None:
    for revision in (True, -1, 9_007_199_254_740_992):
        with pytest.raises(EnterpriseTaskError, match="INVALID_ENTERPRISE_TASK_REVISION"):
            task(revision=revision).validate()


def test_dependencies_reject_self_reference_and_duplicates() -> None:
    with pytest.raises(EnterpriseTaskError, match="ENTERPRISE_TASK_SELF_DEPENDENCY"):
        task(dependency_ids=("task-1",)).validate()
    with pytest.raises(EnterpriseTaskError, match="DUPLICATE_ENTERPRISE_TASK_DEPENDENCY"):
        task(dependency_ids=("task-2", "task-2")).validate()


def test_completion_requires_actor_and_aware_timestamp() -> None:
    with pytest.raises(EnterpriseTaskError, match="COMPLETION_METADATA_REQUIRED"):
        task(status=EnterpriseTaskStatus.COMPLETED).validate()
    with pytest.raises(EnterpriseTaskError, match="COMPLETED_AT_MUST_BE_TIMEZONE_AWARE"):
        task(
            status=EnterpriseTaskStatus.COMPLETED,
            completed_at=datetime(2026, 11, 14, 9, 0),
            completed_by_user_id="user-2",
        ).validate()
    with pytest.raises(EnterpriseTaskError, match="COMPLETION_METADATA_NOT_ALLOWED"):
        task(completed_at=NOW, completed_by_user_id="user-2").validate()


def test_completion_metadata_cannot_precede_creation() -> None:
    with pytest.raises(EnterpriseTaskError, match="COMPLETED_BEFORE_CREATED"):
        task(
            status=EnterpriseTaskStatus.COMPLETED,
            completed_at=NOW - timedelta(seconds=1),
            completed_by_user_id="user-2",
        ).validate()


def test_related_references_are_opaque_revision_aware_and_unique() -> None:
    reference = EnterpriseTaskReference(
        EnterpriseTaskReferenceType.ENGINEERING_ACTIVITY, "activity-7", 12
    )
    item = task(related_refs=(reference,))
    payload = item.as_dict()
    assert payload["contract_version"] == "cubi-enterprise-task.v1"
    assert payload["related_refs"] == [
        {
            "reference_type": "engineering_activity",
            "reference_id": "activity-7",
            "revision": 12,
        }
    ]
    with pytest.raises(EnterpriseTaskError, match="DUPLICATE_ENTERPRISE_TASK_REFERENCE"):
        task(related_refs=(reference, reference)).validate()


def test_reference_does_not_accept_an_arbitrary_reference_type() -> None:
    reference = EnterpriseTaskReference("project", "project-1")  # type: ignore[arg-type]
    with pytest.raises(EnterpriseTaskError, match="INVALID_ENTERPRISE_TASK_REFERENCE_TYPE"):
        reference.validate()


def test_updated_time_cannot_precede_creation() -> None:
    with pytest.raises(EnterpriseTaskError, match="UPDATED_BEFORE_CREATED"):
        task(updated_at=NOW - timedelta(seconds=1)).validate()
