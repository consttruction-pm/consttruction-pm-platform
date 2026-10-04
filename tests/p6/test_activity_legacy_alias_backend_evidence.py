from dataclasses import fields

from construction_pm.activity_master_repository import ActivityMaster
from construction_pm.p6_field_registry import canonical_activity_field_id, fields_by_subject


def test_activity_legacy_alias_evidence_keeps_early_and_late_finish_distinct() -> None:
    activity_fields = {field.p6_field for field in fields_by_subject("Activity")}

    assert "RemainingFinishDate" in activity_fields
    assert "RemainingEarlyFinishDate" in activity_fields
    assert "RemainingLateFinishDate" in activity_fields

    # The compatibility metadata currently points the legacy name at the
    # early-finish identity, but this is not sufficient for final certification.
    assert canonical_activity_field_id("activity.remaining_finish") == (
        "activity.remaining_early_finish_date"
    )
    assert canonical_activity_field_id("activity.remaining_finish") != (
        "activity.remaining_late_finish_date"
    )


def test_activity_owner_and_calendar_are_not_activity_master_persistence_fields() -> None:
    persisted = {field.name for field in fields(ActivityMaster)}

    assert "activity_owner" not in persisted
    assert "owner" not in persisted
    assert "calendar" not in persisted
    assert "calendar_name" not in persisted
    assert "calendar_object_id" not in persisted
