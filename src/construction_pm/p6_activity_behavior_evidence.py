from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class P6ActivityFieldBehaviorEvidence:
    p6_field: str
    behavior_status: str
    source_url: str
    rationale: str

    def __post_init__(self) -> None:
        allowed = {
            "scheduler_computed_explicit",
            "manual_update_explicit",
            "user_entered_or_calculated_explicit",
            "derived_definition_explicit",
            "not_explicit",
        }
        if self.behavior_status not in allowed:
            raise ValueError(f"invalid behavior_status: {self.behavior_status}")
        if not self.p6_field or not self.source_url or not self.rationale:
            raise ValueError("behavior evidence requires field, source, and rationale")


_SOURCE_URL = (
    "https://docs.oracle.com/en/industries/construction-engineering/"
    "primavera-p6-project/26/rest-api/op-activity-put.html"
)

_EXACT_FIELDS = (
    "PlannedStartDate", "PlannedFinishDate", "ActualStartDate", "ActualFinishDate",
    "PlannedDuration", "RemainingDuration", "ActualDuration",
    "DurationPercentComplete", "PhysicalPercentComplete", "PercentCompleteType",
    "TotalFloat", "FreeFloat", "FloatPath", "FloatPathOrder",
    "EarlyStartDate", "EarlyFinishDate", "LateStartDate", "LateFinishDate",
    "PrimaryConstraintType", "PrimaryConstraintDate", "ExpectedFinishDate",
    "PrimaryResourceName", "ProjectId", "ProjectName", "WBSPath",
    "BaselineStartDate", "BaselineFinishDate", "BaselineDuration",
    "Duration1Variance", "CreateUser",
)

_BEHAVIOR = {
    "PlannedStartDate": (
        "manual_update_explicit",
        "Oracle states the scheduler computes this date but the project manager can update it manually.",
    ),
    "PlannedFinishDate": (
        "manual_update_explicit",
        "Oracle states the scheduler computes this date but the project manager can update it manually.",
    ),
    "ActualDuration": (
        "derived_definition_explicit",
        "Oracle defines actual duration as working time between actual dates (or data date) using the activity calendar.",
    ),
    "PhysicalPercentComplete": (
        "user_entered_or_calculated_explicit",
        "Oracle states physical percent complete can be user entered or calculated from weighted steps.",
    ),
    "EarlyStartDate": (
        "scheduler_computed_explicit",
        "Oracle states early start is computed by the project scheduler from network logic, constraints, and resource availability.",
    ),
    "EarlyFinishDate": (
        "scheduler_computed_explicit",
        "Oracle states early finish is computed by the project scheduler from network logic, constraints, and resource availability.",
    ),
    "LateStartDate": (
        "scheduler_computed_explicit",
        "Oracle identifies late start as scheduler-derived schedule output.",
    ),
    "LateFinishDate": (
        "scheduler_computed_explicit",
        "Oracle identifies late finish as scheduler-derived schedule output.",
    ),
    "BaselineStartDate": (
        "derived_definition_explicit",
        "Oracle defines the baseline start from planned start until the activity starts and then from actual start.",
    ),
    "BaselineFinishDate": (
        "derived_definition_explicit",
        "Oracle defines the baseline finish from planned, remaining, or actual finish according to activity state.",
    ),
    "BaselineDuration": (
        "derived_definition_explicit",
        "Oracle defines baseline duration as total working time between the baseline current start and finish using the activity calendar.",
    ),
    "RemainingDuration": (
        "derived_definition_explicit",
        "Oracle defines remaining duration as working time between remaining start and finish using the activity calendar.",
    ),
    "TotalFloat": (
        "derived_definition_explicit",
        "Oracle defines total float as a schedule-derived time allowance; the exact implementation rule remains a separate semantic gate.",
    ),
    "FreeFloat": (
        "derived_definition_explicit",
        "Oracle defines free float as the time the activity can be delayed before delaying a successor's start.",
    ),
    "Duration1Variance": (
        "derived_definition_explicit",
        "Oracle describes variance fields as differences between current and baseline schedule measures; certification still requires exact mapping evidence.",
    ),
}


def activity_behavior_evidence() -> tuple[P6ActivityFieldBehaviorEvidence, ...]:
    result = []
    for field in _EXACT_FIELDS:
        status, rationale = _BEHAVIOR.get(
            field,
            (
                "not_explicit",
                "Release 26 Update Activity documentation in the reviewed evidence does not explicitly establish writable/computed behavior for this field.",
            ),
        )
        result.append(
            P6ActivityFieldBehaviorEvidence(
                p6_field=field,
                behavior_status=status,
                source_url=_SOURCE_URL,
                rationale=rationale,
            )
        )
    return tuple(result)


def get_activity_behavior_evidence(p6_field: str) -> P6ActivityFieldBehaviorEvidence:
    for evidence in activity_behavior_evidence():
        if evidence.p6_field == p6_field:
            return evidence
    raise KeyError(p6_field)
