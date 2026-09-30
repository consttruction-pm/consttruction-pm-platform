from __future__ import annotations

from dataclasses import dataclass

from .activity import Activity
from .out_of_sequence import OutOfSequenceState, ProgressRelationAction, resolve_out_of_sequence_action
from .progress_state import ProgressState
from .schedule_options import OutOfSequenceScheduleType


@dataclass(frozen=True)
class OOSPolicyResult:
    state: OutOfSequenceState
    action: ProgressRelationAction
    apply_relationship_logic: bool
    preserve_actual_dates: bool
    preserve_remaining_work: bool


def resolve_oos_policy(
    activity: Activity,
    progress: ProgressState,
    *,
    relationship_required_start,
    data_date,
    mode: OutOfSequenceScheduleType,
) -> OOSPolicyResult:
    action = resolve_out_of_sequence_action(
        activity,
        relationship_required_start=relationship_required_start,
        data_date=data_date,
        mode=mode,
    )
    # Progress state remains authoritative in every mode. The OOS mode only
    # decides how the predecessor relationship constrains the progressed work.
    if action is ProgressRelationAction.IGNORE_LOGIC:
        return OOSPolicyResult(
            OutOfSequenceState.OUT_OF_SEQUENCE,
            action,
            apply_relationship_logic=False,
            preserve_actual_dates=True,
            preserve_remaining_work=True,
        )
    if action is ProgressRelationAction.USE_ACTUAL_DATES:
        return OOSPolicyResult(
            OutOfSequenceState.OUT_OF_SEQUENCE,
            action,
            apply_relationship_logic=False,
            preserve_actual_dates=True,
            preserve_remaining_work=True,
        )
    state = (
        OutOfSequenceState.OUT_OF_SEQUENCE
        if activity.actual_start is not None
        and activity.actual_start < relationship_required_start
        else OutOfSequenceState.IN_SEQUENCE
        if activity.actual_start is not None
        else OutOfSequenceState.NOT_STARTED
    )
    return OOSPolicyResult(
        state,
        action,
        apply_relationship_logic=True,
        preserve_actual_dates=True,
        preserve_remaining_work=True,
    )
