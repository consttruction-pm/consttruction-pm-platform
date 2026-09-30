from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class P6ActivityFieldTypeEvidence:
    p6_field: str
    source_wire_type: str
    source_url: str
    status: str = "type_verified_not_certified"

    def __post_init__(self) -> None:
        if not self.p6_field or not self.source_wire_type or not self.source_url:
            raise ValueError("field type evidence requires field, source type, and source URL")
        if self.status != "type_verified_not_certified":
            raise ValueError("type evidence cannot imply full field certification")


_SOURCE_URL = (
    "https://docs.oracle.com/en/industries/construction-engineering/"
    "primavera-p6-project/26/rest-api/op-activity-get.html"
)

_ACTIVITY_EXACT_TYPE_EVIDENCE = {
    "PlannedStartDate": "date-time",
    "PlannedFinishDate": "date-time",
    "ActualStartDate": "date-time",
    "ActualFinishDate": "date-time",
    "PlannedDuration": "double",
    "RemainingDuration": "double",
    "ActualDuration": "double",
    "DurationPercentComplete": "double",
    "PhysicalPercentComplete": "double",
    "PercentCompleteType": "string",
    "TotalFloat": "double",
    "FreeFloat": "double",
    "FloatPath": "integer",
    "FloatPathOrder": "integer",
    "EarlyStartDate": "date-time",
    "EarlyFinishDate": "date-time",
    "LateStartDate": "date-time",
    "LateFinishDate": "date-time",
    "PrimaryConstraintType": "string",
    "PrimaryConstraintDate": "date-time",
    "ExpectedFinishDate": "date-time",
    "PrimaryResourceName": "string",
    "ProjectId": "string",
    "ProjectName": "string",
    "WBSPath": "string",
    "BaselineStartDate": "date-time",
    "BaselineFinishDate": "date-time",
    "BaselineDuration": "double",
    "Duration1Variance": "double",
    "CreateUser": "string",
}


def activity_exact_type_evidence() -> tuple[P6ActivityFieldTypeEvidence, ...]:
    return tuple(
        P6ActivityFieldTypeEvidence(
            p6_field=field,
            source_wire_type=wire_type,
            source_url=_SOURCE_URL,
        )
        for field, wire_type in _ACTIVITY_EXACT_TYPE_EVIDENCE.items()
    )


def get_activity_type_evidence(p6_field: str) -> P6ActivityFieldTypeEvidence:
    for evidence in activity_exact_type_evidence():
        if evidence.p6_field == p6_field:
            return evidence
    raise KeyError(p6_field)
