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

    def to_canonical_request(
        self,
        *,
        tenant_id: str,
        project_id: str,
        revision: int,
        calculation_context: Mapping[str, object],
    ) -> dict[str, object]:
        """Map this legacy portability shape onto canonical scheduling request v1."""
        self.validate()
        if not tenant_id.strip():
            raise ValueError("tenant_id is required")
        if not project_id.strip():
            raise ValueError("project_id is required")
        if not isinstance(revision, int) or revision < 0:
            raise ValueError("revision must be a non-negative integer")
        canonical_activities: list[dict[str, object]] = []
        for activity in self.activities:
            activity_id = str(activity["id"])
            assignment = self.calendar_assignments.get(f"activity:{activity_id}")
            if assignment is None:
                raise ValueError(f"calendar assignment is required for activity {activity_id}")
            duration = activity["duration"]
            assert isinstance(duration, Mapping)
            unit = str(duration["unit"]).lower().replace("_", "-")
            canonical_activities.append({
                "activity_id": activity_id,
                "duration_value": str(duration["value"]),
                "duration_unit": unit,
                "calendar": {
                    "calendar_id": assignment["calendar_id"],
                    "calendar_version": str(assignment["calendar_version"]),
                    "kind": str(assignment.get("kind", "working-time")),
                },
            })
        canonical_relationships: list[dict[str, object]] = []
        for relationship in self.relationships:
            predecessor = str(relationship["predecessor_id"])
            successor = str(relationship["successor_id"])
            lag = relationship["lag"]
            assert isinstance(lag, Mapping)
            item: dict[str, object] = {
                "predecessor_id": predecessor,
                "successor_id": successor,
                "type": relationship["type"],
                "lag_value": str(lag["value"]),
                "lag_unit": str(lag["unit"]).lower().replace("_", "-"),
            }
            assignment = self.calendar_assignments.get(f"relationship:{predecessor}:{successor}")
            if assignment is not None:
                item["lag_calendar"] = {
                    "calendar_id": assignment["calendar_id"],
                    "calendar_version": str(assignment["calendar_version"]),
                    "kind": str(assignment.get("kind", "working-time")),
                }
            canonical_relationships.append(item)
        return {
            "contract_version": "1.0",
            "project_context": {
                "tenant_id": tenant_id,
                "project_id": project_id,
                "revision": revision,
            },
            "calculation_context": {
                **dict(calculation_context),
                "schedule_options": {
                    **dict(calculation_context.get("schedule_options", {})),
                    "project_schema_version": self.project_schema_version,
                },
            },
            "activities": canonical_activities,
            "relationships": canonical_relationships,
            "constraints": [dict(item) for item in self.constraints],
        }
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
