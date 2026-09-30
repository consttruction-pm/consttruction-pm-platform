from construction_pm.p6_activity_behavior_evidence import (
    activity_behavior_evidence,
    get_activity_behavior_evidence,
)
from construction_pm.p6_field_registry import fields_by_subject


def test_behavior_evidence_covers_all_current_exact_activity_fields():
    registry = {field.p6_field for field in fields_by_subject("Activity")}
    evidence = {item.p6_field for item in activity_behavior_evidence()}
    assert len(evidence) == 30
    assert evidence == {
        "PlannedStartDate", "PlannedFinishDate", "ActualStartDate", "ActualFinishDate",
        "PlannedDuration", "RemainingDuration", "ActualDuration",
        "DurationPercentComplete", "PhysicalPercentComplete", "PercentCompleteType",
        "TotalFloat", "FreeFloat", "FloatPath", "FloatPathOrder",
        "EarlyStartDate", "EarlyFinishDate", "LateStartDate", "LateFinishDate",
        "PrimaryConstraintType", "PrimaryConstraintDate", "ExpectedFinishDate",
        "PrimaryResourceName", "ProjectId", "ProjectName", "WBSPath",
        "BaselineStartDate", "BaselineFinishDate", "BaselineDuration",
        "Duration1Variance", "CreateUser",
    }
    assert evidence <= registry


def test_explicit_manual_and_scheduler_behavior_is_preserved():
    assert (
        get_activity_behavior_evidence("PlannedStartDate").behavior_status
        == "manual_update_explicit"
    )
    assert (
        get_activity_behavior_evidence("PlannedFinishDate").behavior_status
        == "manual_update_explicit"
    )
    assert (
        get_activity_behavior_evidence("EarlyStartDate").behavior_status
        == "scheduler_computed_explicit"
    )
    assert (
        get_activity_behavior_evidence("EarlyFinishDate").behavior_status
        == "scheduler_computed_explicit"
    )


def test_physical_percent_complete_allows_two_documented_modes():
    evidence = get_activity_behavior_evidence("PhysicalPercentComplete")
    assert evidence.behavior_status == "user_entered_or_calculated_explicit"


def test_unproven_fields_remain_unclassified():
    for field in ("ActivityStartDateDoesNotExist",):
        try:
            get_activity_behavior_evidence(field)
        except KeyError:
            pass
        else:
            raise AssertionError("unknown field must not be manufactured")


def test_behavior_evidence_has_no_certification_status():
    assert all(
        item.behavior_status != "certified"
        for item in activity_behavior_evidence()
    )
