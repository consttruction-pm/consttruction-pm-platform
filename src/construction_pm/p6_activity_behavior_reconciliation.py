from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActivityBehaviorReconciliation:
    p6_field: str
    manual_writable: bool | None
    scheduler_derived: bool | None
    registry_writable: bool
    registry_computed: bool
    status: str

    def __post_init__(self) -> None:
        allowed = {
            "consistent",
            "evidence_model_gap",
            "insufficient_evidence",
            "registry_conflict",
        }
        if self.status not in allowed:
            raise ValueError(f"invalid reconciliation status: {self.status}")


def reconcile_activity_behavior(
    *,
    p6_field: str,
    behavior_status: str,
    registry_writable: bool,
    registry_computed: bool,
) -> ActivityBehaviorReconciliation:
    """Reconcile explicit P6 behavior evidence without collapsing semantics.

    Scheduler-derived and manually-writable are independent facts in P6.
    The current registry's computed flag cannot represent both facts for one
    field because the registry rejects writable=True with computed=True.
    """
    if behavior_status == "manual_update_explicit":
        manual_writable = True
        scheduler_derived = True
    elif behavior_status == "scheduler_computed_explicit":
        manual_writable = None
        scheduler_derived = True
    elif behavior_status == "user_entered_or_calculated_explicit":
        manual_writable = True
        scheduler_derived = None
    elif behavior_status in {"derived_definition_explicit", "not_explicit"}:
        manual_writable = None
        scheduler_derived = None
    else:
        raise ValueError(f"unknown behavior evidence status: {behavior_status}")

    if behavior_status == "not_explicit":
        status = "insufficient_evidence"
    elif manual_writable is True and scheduler_derived is True:
        status = (
            "evidence_model_gap"
            if registry_writable and not registry_computed
            else "registry_conflict"
        )
    elif manual_writable is True and not registry_writable:
        status = "registry_conflict"
    elif scheduler_derived is True:
        status = "consistent" if registry_computed else "evidence_model_gap"
    else:
        status = "insufficient_evidence"

    return ActivityBehaviorReconciliation(
        p6_field=p6_field,
        manual_writable=manual_writable,
        scheduler_derived=scheduler_derived,
        registry_writable=registry_writable,
        registry_computed=registry_computed,
        status=status,
    )
