from __future__ import annotations

"""Stable scheduling diagnostics for infeasible or negative-float schedules.

The shared scheduling core never silently rewrites an unsatisfiable input. Each
rejection is raised as :class:`ScheduleInfeasibilityError` carrying one stable
machine code from :class:`ScheduleDiagnosticCode`. Negative float is a valid
reported outcome, not a failure, and is emitted as a warning diagnostic.

``INFEASIBILITY_MATRIX`` is the single codified inventory of the conditions
mapped to each code. Consumers (API/read models) may rely on the codes; the
human-readable message remains explanatory and is not a stable contract.
"""

from dataclasses import dataclass
from enum import Enum


class ScheduleDiagnosticCode(str, Enum):
    DUPLICATE_ACTIVITY_ID = "DUPLICATE_ACTIVITY_ID"
    UNKNOWN_ACTIVITY_REFERENCE = "UNKNOWN_ACTIVITY_REFERENCE"
    NETWORK_CYCLE = "NETWORK_CYCLE"
    CONSTRAINT_WINDOW_EMPTY = "CONSTRAINT_WINDOW_EMPTY"
    CONSTRAINT_MANDATORY_CONFLICT = "CONSTRAINT_MANDATORY_CONFLICT"
    CONSTRAINT_MANDATORY_UNSATISFIABLE = "CONSTRAINT_MANDATORY_UNSATISFIABLE"
    CONSTRAINT_LOWER_BOUND_VIOLATED = "CONSTRAINT_LOWER_BOUND_VIOLATED"
    CONSTRAINT_UPPER_BOUND_VIOLATED = "CONSTRAINT_UPPER_BOUND_VIOLATED"
    BACKWARD_RELATIONSHIP_VIOLATED = "BACKWARD_RELATIONSHIP_VIOLATED"
    BACKWARD_EXCEEDS_PROJECT_FINISH = "BACKWARD_EXCEEDS_PROJECT_FINISH"
    NEGATIVE_FLOAT = "NEGATIVE_FLOAT"
    INVALID_DATA_DATE = "INVALID_DATA_DATE"


class ScheduleDiagnosticSeverity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"


@dataclass(frozen=True)
class ScheduleDiagnostic:
    code: ScheduleDiagnosticCode
    message: str
    activity_id: str | None = None
    predecessor_id: str | None = None
    successor_id: str | None = None
    severity: ScheduleDiagnosticSeverity = ScheduleDiagnosticSeverity.ERROR

    def __post_init__(self) -> None:
        if not isinstance(self.code, ScheduleDiagnosticCode):
            raise TypeError("code must be a ScheduleDiagnosticCode")
        if not isinstance(self.severity, ScheduleDiagnosticSeverity):
            raise TypeError("severity must be a ScheduleDiagnosticSeverity")
        if not isinstance(self.message, str) or not self.message:
            raise ValueError("diagnostic message must be a non-empty string")

    def to_payload(self) -> dict[str, object]:
        return {
            "code": self.code.value,
            "severity": self.severity.value,
            "message": self.message,
            "activity_id": self.activity_id,
            "predecessor_id": self.predecessor_id,
            "successor_id": self.successor_id,
        }


class ScheduleInfeasibilityError(ValueError):
    """A scheduling input that cannot satisfy its own bounds.

    The message keeps the historical human-readable text so existing callers
    remain compatible. ``code`` and ``diagnostic`` are the stable contract.
    """

    def __init__(
        self,
        code: ScheduleDiagnosticCode,
        message: str,
        *,
        activity_id: str | None = None,
        predecessor_id: str | None = None,
        successor_id: str | None = None,
    ) -> None:
        if not isinstance(code, ScheduleDiagnosticCode):
            raise TypeError("code must be a ScheduleDiagnosticCode")
        self.diagnostic = ScheduleDiagnostic(
            code=code,
            message=message,
            activity_id=activity_id,
            predecessor_id=predecessor_id,
            successor_id=successor_id,
        )
        super().__init__(message)

    @property
    def code(self) -> ScheduleDiagnosticCode:
        return self.diagnostic.code


@dataclass(frozen=True)
class InfeasibilityCase:
    condition: str
    code: ScheduleDiagnosticCode
    fail_closed: bool = True
    # A defensive guard protects the invariant even though the current CPM
    # algorithm cannot reach it from valid public inputs. It remains fail
    # closed so a future pass change cannot silently emit an out-of-bound date.
    defensive: bool = False


# Explicit, reviewable matrix of the conditions that can make a schedule
# impossible. It is documentation-as-code: tests enumerate these entries so a
# new rejection path cannot exist without a stable code.
INFEASIBILITY_MATRIX: tuple[InfeasibilityCase, ...] = (
    InfeasibilityCase("duplicate activity identifiers", ScheduleDiagnosticCode.DUPLICATE_ACTIVITY_ID),
    InfeasibilityCase("relationship/constraint references an unknown activity", ScheduleDiagnosticCode.UNKNOWN_ACTIVITY_REFERENCE),
    InfeasibilityCase("directed cycle in the activity network", ScheduleDiagnosticCode.NETWORK_CYCLE),
    InfeasibilityCase("start or finish lower/upper constraint bounds cross", ScheduleDiagnosticCode.CONSTRAINT_WINDOW_EMPTY),
    InfeasibilityCase("two mandatory constraints carry different dates", ScheduleDiagnosticCode.CONSTRAINT_MANDATORY_CONFLICT),
    InfeasibilityCase("mandatory constraint cannot coexist with logic or project finish", ScheduleDiagnosticCode.CONSTRAINT_MANDATORY_UNSATISFIABLE),
    InfeasibilityCase("lower-bound constraint is earlier than the computed event", ScheduleDiagnosticCode.CONSTRAINT_LOWER_BOUND_VIOLATED),
    InfeasibilityCase("upper-bound constraint is later than the computed event", ScheduleDiagnosticCode.CONSTRAINT_UPPER_BOUND_VIOLATED),
    InfeasibilityCase("backward pass cannot satisfy a relationship", ScheduleDiagnosticCode.BACKWARD_RELATIONSHIP_VIOLATED),
    InfeasibilityCase(
        "late dates exceed the project-finish boundary",
        ScheduleDiagnosticCode.BACKWARD_EXCEEDS_PROJECT_FINISH,
        defensive=True,
    ),
    InfeasibilityCase("Data Date is not a valid calendar date", ScheduleDiagnosticCode.INVALID_DATA_DATE),
    InfeasibilityCase("negative total float (reported, not rewritten)", ScheduleDiagnosticCode.NEGATIVE_FLOAT, fail_closed=False),
)


__all__ = [
    "INFEASIBILITY_MATRIX",
    "InfeasibilityCase",
    "ScheduleDiagnostic",
    "ScheduleDiagnosticCode",
    "ScheduleDiagnosticSeverity",
    "ScheduleInfeasibilityError",
]
