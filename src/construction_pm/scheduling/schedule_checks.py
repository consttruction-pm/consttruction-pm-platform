from __future__ import annotations

"""Explicit schedule-quality checks over one authoritative calculation.

The check layer never rewrites a schedule and never calculates dates. It reads
the immutable calculation input and the already-computed result, then emits
stable rule identifiers, severities, affected facts and counts. Producers may
add rules only by appending to ``SCHEDULE_CHECK_RULES`` so every emitted
finding has a declared severity and the UI can list zero-count rules too.

This is a deliberately bounded rule set: open ends, negative float, activity
constraints and negative relationship lag. The full Version 26 Check Schedule
rule catalog is not enumerated in the repository yet, so no rule is inferred
from an unavailable vendor fixture.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Mapping

from .constraints import ActivityConstraint, ConstraintType


class ScheduleCheckRuleId(str, Enum):
    NEGATIVE_FLOAT = "NEGATIVE_FLOAT"
    OPEN_START = "OPEN_START"
    OPEN_FINISH = "OPEN_FINISH"
    ACTIVITY_CONSTRAINT = "ACTIVITY_CONSTRAINT"
    MANDATORY_CONSTRAINT = "MANDATORY_CONSTRAINT"
    NEGATIVE_LAG = "NEGATIVE_LAG"


class ScheduleCheckSeverity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass(frozen=True)
class ScheduleCheckRule:
    rule_id: ScheduleCheckRuleId
    severity: ScheduleCheckSeverity


# The order is the presentation and payload order. A rule stays listed even
# when its count is zero so the condition set is explicit to every consumer.
SCHEDULE_CHECK_RULES: tuple[ScheduleCheckRule, ...] = (
    ScheduleCheckRule(ScheduleCheckRuleId.NEGATIVE_FLOAT, ScheduleCheckSeverity.WARNING),
    ScheduleCheckRule(ScheduleCheckRuleId.OPEN_START, ScheduleCheckSeverity.WARNING),
    ScheduleCheckRule(ScheduleCheckRuleId.OPEN_FINISH, ScheduleCheckSeverity.WARNING),
    ScheduleCheckRule(ScheduleCheckRuleId.ACTIVITY_CONSTRAINT, ScheduleCheckSeverity.INFO),
    ScheduleCheckRule(ScheduleCheckRuleId.MANDATORY_CONSTRAINT, ScheduleCheckSeverity.WARNING),
    ScheduleCheckRule(ScheduleCheckRuleId.NEGATIVE_LAG, ScheduleCheckSeverity.INFO),
)

_RULE_ORDER = {rule.rule_id: index for index, rule in enumerate(SCHEDULE_CHECK_RULES)}
_MANDATORY_TYPES = frozenset(
    {ConstraintType.MANDATORY_START, ConstraintType.MANDATORY_FINISH}
)
_DERIVED_ACTIVITY_TYPES = frozenset({"WBS Summary", "Level of Effort"})


@dataclass(frozen=True)
class ScheduleCheckFinding:
    rule_id: ScheduleCheckRuleId
    severity: ScheduleCheckSeverity
    message: str
    activity_id: str | None = None
    relationship_id: str | None = None
    constraint_id: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.rule_id, ScheduleCheckRuleId):
            raise TypeError("rule_id must be a ScheduleCheckRuleId")
        if not isinstance(self.severity, ScheduleCheckSeverity):
            raise TypeError("severity must be a ScheduleCheckSeverity")
        if not isinstance(self.message, str) or not self.message:
            raise ValueError("message must be a non-empty string")

    def to_payload(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id.value,
            "severity": self.severity.value,
            "message": self.message,
            "activity_id": self.activity_id,
            "relationship_id": self.relationship_id,
            "constraint_id": self.constraint_id,
            "details": {str(key): value for key, value in sorted(self.details.items())},
        }


def evaluate_schedule_checks(
    source: object,
    *,
    date_result: object | None = None,
    time_result: object | None = None,
) -> tuple[ScheduleCheckFinding, ...]:
    """Return deterministic findings for one immutable input and result.

    ``date_result`` is a ``ScheduleResult`` and ``time_result`` is a
    ``TimeScheduleResult``. At most one is expected; both are optional so the
    input-only rules can be tested and reused without calculating a schedule.
    """
    activities = tuple(getattr(source, "activities", ()))
    relationships = tuple(getattr(source, "relationships", ()))
    constraints = tuple(getattr(source, "constraints", ()))
    activity_ids = {str(getattr(activity, "id")) for activity in activities}
    excluded = {
        str(getattr(activity, "id"))
        for activity in activities
        if _activity_type_value(activity) in _DERIVED_ACTIVITY_TYPES
    }
    has_predecessor = {
        str(getattr(relationship, "successor_id")) for relationship in relationships
    }
    has_successor = {
        str(getattr(relationship, "predecessor_id")) for relationship in relationships
    }

    findings: list[ScheduleCheckFinding] = []
    for activity_id in sorted(activity_ids - excluded):
        if activity_id not in has_predecessor:
            findings.append(
                ScheduleCheckFinding(
                    rule_id=ScheduleCheckRuleId.OPEN_START,
                    severity=ScheduleCheckSeverity.WARNING,
                    message=f"activity {activity_id} has no predecessor",
                    activity_id=activity_id,
                    details={"predecessor_count": 0},
                )
            )
        if activity_id not in has_successor:
            findings.append(
                ScheduleCheckFinding(
                    rule_id=ScheduleCheckRuleId.OPEN_FINISH,
                    severity=ScheduleCheckSeverity.WARNING,
                    message=f"activity {activity_id} has no successor",
                    activity_id=activity_id,
                    details={"successor_count": 0},
                )
            )

    for constraint in constraints:
        _append_constraint_finding(findings, constraint)

    for relationship in relationships:
        lag = _lag_value(relationship)
        if lag < 0:
            predecessor_id = str(getattr(relationship, "predecessor_id"))
            successor_id = str(getattr(relationship, "successor_id"))
            relationship_type = _enum_value(getattr(relationship, "type", ""))
            findings.append(
                ScheduleCheckFinding(
                    rule_id=ScheduleCheckRuleId.NEGATIVE_LAG,
                    severity=ScheduleCheckSeverity.INFO,
                    message=(
                        f"relationship {predecessor_id} -> {successor_id} "
                        f"({relationship_type}) carries a negative lag of {lag}"
                    ),
                    activity_id=successor_id,
                    relationship_id=f"{predecessor_id}->{successor_id}:{relationship_type}",
                    details={
                        "predecessor_id": predecessor_id,
                        "successor_id": successor_id,
                        "relationship_type": relationship_type,
                        "lag": str(lag),
                    },
                )
            )

    if date_result is not None:
        for activity_id, value in sorted(
            getattr(date_result, "floats", {}).items(), key=lambda item: str(item[0])
        ):
            total_float = getattr(value, "total_float", None)
            if isinstance(total_float, Decimal):
                negative = total_float < 0
            elif isinstance(total_float, (int, float)) and not isinstance(total_float, bool):
                negative = total_float < 0
            else:
                negative = False
            if negative:
                findings.append(_negative_float_finding(str(activity_id), total_float))
    elif time_result is not None:
        for activity_id, value in sorted(
            getattr(time_result, "floats", {}).items(), key=lambda item: str(item[0])
        ):
            total_float = getattr(value, "total_float_value", None)
            if isinstance(total_float, Decimal) and total_float < 0:
                findings.append(_negative_float_finding(str(activity_id), total_float))

    return tuple(
        sorted(
            findings,
            key=lambda item: (
                _RULE_ORDER[item.rule_id],
                item.activity_id or "",
                item.relationship_id or "",
                item.constraint_id or "",
                item.message,
            ),
        )
    )


def build_schedule_check_payload(
    findings: tuple[ScheduleCheckFinding, ...],
    *,
    scope: Mapping[str, object],
    snapshot_id: str,
    snapshot_hash: str,
    calculation_run_identity: str,
) -> dict[str, object]:
    counts: dict[str, int] = {
        ScheduleCheckSeverity.ERROR.value: 0,
        ScheduleCheckSeverity.WARNING.value: 0,
        ScheduleCheckSeverity.INFO.value: 0,
    }
    rule_counts: dict[ScheduleCheckRuleId, int] = {
        rule.rule_id: 0 for rule in SCHEDULE_CHECK_RULES
    }
    for finding in findings:
        counts[finding.severity.value] += 1
        rule_counts[finding.rule_id] += 1
    return {
        "contract_version": "p6-schedule-check.v1",
        "kind": "schedule_check",
        "scope": dict(scope),
        "snapshot_id": snapshot_id,
        "snapshot_hash": snapshot_hash,
        "calculation_run_identity": calculation_run_identity,
        "counts": {"total": len(findings), **counts},
        "rules": [
            {
                "rule_id": rule.rule_id.value,
                "severity": rule.severity.value,
                "count": rule_counts[rule.rule_id],
            }
            for rule in SCHEDULE_CHECK_RULES
        ],
        "findings": [finding.to_payload() for finding in findings],
    }


def _append_constraint_finding(
    findings: list[ScheduleCheckFinding], constraint: object
) -> None:
    if not isinstance(constraint, ActivityConstraint):
        return
    constraint_type = constraint.type.value
    mandatory = constraint.type in _MANDATORY_TYPES
    findings.append(
        ScheduleCheckFinding(
            rule_id=(
                ScheduleCheckRuleId.MANDATORY_CONSTRAINT
                if mandatory
                else ScheduleCheckRuleId.ACTIVITY_CONSTRAINT
            ),
            severity=(
                ScheduleCheckSeverity.WARNING
                if mandatory
                else ScheduleCheckSeverity.INFO
            ),
            message=(
                f"activity {constraint.activity_id} carries "
                f"{constraint_type} on {constraint.date.isoformat()}"
            ),
            activity_id=constraint.activity_id,
            details={
                "constraint_type": constraint_type,
                "constraint_date": constraint.date.isoformat(),
                "mandatory": mandatory,
            },
        )
    )


def _negative_float_finding(activity_id: str, total_float: object) -> ScheduleCheckFinding:
    return ScheduleCheckFinding(
        rule_id=ScheduleCheckRuleId.NEGATIVE_FLOAT,
        severity=ScheduleCheckSeverity.WARNING,
        message=f"activity {activity_id} has negative total float of {total_float}",
        activity_id=activity_id,
        details={"total_float": str(total_float)},
    )


def _activity_type_value(activity: object) -> str | None:
    return _enum_value(getattr(activity, "activity_type", None))


def _enum_value(value: object) -> str | None:
    raw = getattr(value, "value", value)
    return raw if isinstance(raw, str) else None


def _lag_value(relationship: object) -> Decimal:
    raw = getattr(relationship, "lag", 0)
    raw = getattr(raw, "value", raw)
    try:
        return Decimal(str(raw))
    except Exception:
        return Decimal(0)


__all__ = [
    "SCHEDULE_CHECK_RULES",
    "ScheduleCheckFinding",
    "ScheduleCheckRule",
    "ScheduleCheckRuleId",
    "ScheduleCheckSeverity",
    "build_schedule_check_payload",
    "evaluate_schedule_checks",
]
