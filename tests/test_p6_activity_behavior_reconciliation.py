from construction_pm.p6_activity_behavior_evidence import activity_behavior_evidence
from construction_pm.p6_activity_behavior_reconciliation import reconcile_activity_behavior
from construction_pm.p6_field_registry import get_field


def test_planned_start_exposes_registry_model_gap():
    registry = get_field("activity.planned_start")
    evidence = next(
        item for item in activity_behavior_evidence()
        if item.p6_field == "PlannedStartDate"
    )
    result = reconcile_activity_behavior(
        p6_field=evidence.p6_field,
        behavior_status=evidence.behavior_status,
        registry_writable=registry.writable,
        registry_computed=registry.computed,
    )
    assert result.manual_writable is True
    assert result.scheduler_derived is True
    assert result.status == "evidence_model_gap"


def test_early_start_is_scheduler_derived_and_registry_computed():
    registry = get_field("activity.early_start")
    result = reconcile_activity_behavior(
        p6_field="EarlyStartDate",
        behavior_status="scheduler_computed_explicit",
        registry_writable=registry.writable,
        registry_computed=registry.computed,
    )
    assert result.manual_writable is None
    assert result.scheduler_derived is True
    assert result.status == "consistent"


def test_unknown_behavior_stays_unclassified():
    result = reconcile_activity_behavior(
        p6_field="ActualStartDate",
        behavior_status="not_explicit",
        registry_writable=True,
        registry_computed=False,
    )
    assert result.status == "insufficient_evidence"
    assert result.manual_writable is None
    assert result.scheduler_derived is None


def test_explicit_writability_conflict_is_detected():
    result = reconcile_activity_behavior(
        p6_field="PlannedStartDate",
        behavior_status="manual_update_explicit",
        registry_writable=False,
        registry_computed=False,
    )
    assert result.status == "registry_conflict"
