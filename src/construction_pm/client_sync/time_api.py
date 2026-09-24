from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

TIME_SCHEDULING_API_CONTRACT_VERSION = "1.0"


@dataclass(frozen=True)
class TimeSchedulingAPIPayload:
    """Typed API boundary for the canonical time-scheduling contract.

    This adapter validates shape/typing only. Scheduling calculations remain in
    the Shared Scheduling Core.
    """

    calculation_context: Mapping[str, object]
    activities: tuple[Mapping[str, object], ...]
    relationships: tuple[Mapping[str, object], ...]
    constraints: tuple[Mapping[str, object], ...] = ()

    contract_version = TIME_SCHEDULING_API_CONTRACT_VERSION

    def to_dto(self) -> dict[str, object]:
        self.validate()
        return {
            "contract_version": self.contract_version,
            "calculation_context": dict(self.calculation_context),
            "activities": [dict(item) for item in self.activities],
            "relationships": [dict(item) for item in self.relationships],
            "constraints": [dict(item) for item in self.constraints],
        }

    def validate(self) -> None:
        required_context = ("schedule_mode", "project_start")
        for name in required_context:
            value = self.calculation_context.get(name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"calculation_context.{name} is required")

        for activity in self.activities:
            self._required(activity, "activity_id")
            self._required(activity, "duration_value")
            self._enum(activity, "duration_unit", {"working-hour", "working-day"})
            calendar = activity.get("calendar")
            if not isinstance(calendar, Mapping):
                raise ValueError("activity.calendar is required")

        for relationship in self.relationships:
            self._required(relationship, "predecessor_id")
            self._required(relationship, "successor_id")
            self._enum(relationship, "type", {"FS", "SS", "FF", "SF"})
            self._required(relationship, "lag_value")
            self._enum(relationship, "lag_unit", {"working-hour", "working-day"})

        for constraint in self.constraints:
            self._required(constraint, "activity_id")
            self._required(constraint, "type")
            self._required(constraint, "target")

    @staticmethod
    def _required(item: Mapping[str, object], name: str) -> None:
        value = item.get(name)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} is required")

    @staticmethod
    def _enum(item: Mapping[str, object], name: str, values: set[str]) -> None:
        value = item.get(name)
        if value not in values:
            raise ValueError(f"{name} is invalid")
