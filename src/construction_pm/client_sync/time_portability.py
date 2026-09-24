from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping


@dataclass(frozen=True)
class TimeSchedulingPortability:
    """Versioned backend contract for portable time-aware scheduling data.

    This is a transport/persistence contract only. Scheduling semantics remain
    owned by the Shared Scheduling Core.
    """

    project_schema_version: int
    calendar_assignments: Mapping[str, Mapping[str, object]]
    activities: tuple[Mapping[str, object], ...]
    relationships: tuple[Mapping[str, object], ...]
    constraints: tuple[Mapping[str, object], ...]
    contract_version = "time-scheduling-portability.v1"

    def validate(self) -> None:
        if self.project_schema_version < 1:
            raise ValueError("project_schema_version must be positive")

        for activity in self.activities:
            self._require_non_empty(activity, "id")
            duration = activity.get("duration")
            if not isinstance(duration, Mapping):
                raise ValueError("activity duration must be an object")
            if not isinstance(duration.get("value"), str):
                raise ValueError("activity duration value must be a canonical decimal string")
            Decimal(duration["value"])
            if duration.get("unit") not in {"WORKING_DAY", "WORKING_HOUR"}:
                raise ValueError("activity duration unit is invalid")

        for relationship in self.relationships:
            self._require_non_empty(relationship, "predecessor_id")
            self._require_non_empty(relationship, "successor_id")
            lag = relationship.get("lag")
            if not isinstance(lag, Mapping):
                raise ValueError("relationship lag must be an object")
            if not isinstance(lag.get("value"), str):
                raise ValueError("relationship lag value must be a canonical decimal string")
            Decimal(lag["value"])
            if lag.get("unit") not in {"WORKING_DAY", "WORKING_HOUR"}:
                raise ValueError("relationship lag unit is invalid")

        for constraint in self.constraints:
            self._require_non_empty(constraint, "activity_id")
            if not isinstance(constraint.get("type"), str) or not constraint["type"]:
                raise ValueError("constraint type is required")
            if not isinstance(constraint.get("target"), str) or not constraint["target"]:
                raise ValueError("constraint target must be an ISO-8601 string")

        for key, assignment in self.calendar_assignments.items():
            if not key.strip():
                raise ValueError("calendar assignment key is required")
            if not isinstance(assignment, Mapping):
                raise ValueError("calendar assignment must be an object")
            if not isinstance(assignment.get("calendar_id"), str) or not assignment["calendar_id"]:
                raise ValueError("calendar_id is required")
            version = assignment.get("calendar_version")
            if not isinstance(version, int) or version < 1:
                raise ValueError("calendar_version must be positive")

    @staticmethod
    def _require_non_empty(value: Mapping[str, object], name: str) -> None:
        item = value.get(name)
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{name} is required")

    def fingerprint_payload(self) -> tuple[object, ...]:
        self.validate()
        return (
            self.contract_version,
            self.project_schema_version,
            tuple(sorted((key, tuple(sorted(value.items()))) for key, value in self.calendar_assignments.items())),
            tuple(sorted(tuple(sorted(item.items())) for item in self.activities)),
            tuple(sorted(tuple(sorted(item.items())) for item in self.relationships)),
            tuple(sorted(tuple(sorted(item.items())) for item in self.constraints)),
        )
