from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
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
        schedule_mode = self.calculation_context.get("schedule_mode")
        if schedule_mode not in {"EARLIEST", "ALAP"}:
            raise ValueError("calculation_context.schedule_mode is invalid")
        project_start = self.calculation_context.get("project_start")
        self._iso_datetime(project_start, "calculation_context.project_start")

        for activity in self.activities:
            self._required(activity, "activity_id")
            duration = self._required(activity, "duration_value")
            try:
                Decimal(duration)
            except (InvalidOperation, ValueError):
                raise ValueError("duration_value must be a canonical decimal string")
            self._enum(activity, "duration_unit", {"working-hour", "working-day"})
            self._calendar(activity.get("calendar"), "activity.calendar")

        for relationship in self.relationships:
            self._required(relationship, "predecessor_id")
            self._required(relationship, "successor_id")
            self._enum(relationship, "type", {"FS", "SS", "FF", "SF"})
            lag = self._required(relationship, "lag_value")
            try:
                Decimal(lag)
            except (InvalidOperation, ValueError):
                raise ValueError("lag_value must be a canonical decimal string")
            self._enum(relationship, "lag_unit", {"working-hour", "working-day"})
            if "lag_calendar" in relationship:
                self._calendar(relationship["lag_calendar"], "relationship.lag_calendar")

        for constraint in self.constraints:
            self._required(constraint, "activity_id")
            self._enum(constraint, "type", {"START_NO_EARLIER_THAN", "START_NO_LATER_THAN", "FINISH_NO_EARLIER_THAN", "FINISH_NO_LATER_THAN", "MANDATORY_START", "MANDATORY_FINISH"})
            target = self._required(constraint, "target")
            self._iso_datetime(target, "constraint.target")

    @staticmethod
    def _required(item: Mapping[str, object], name: str) -> None:
        value = item.get(name)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} is required")

    @staticmethod
    def _calendar(value: object, name: str) -> None:
        if not isinstance(value, Mapping):
            raise ValueError(f"{name} is required")
        for key in ("calendar_id", "calendar_version", "kind"):
            item = value.get(key)
            if not isinstance(item, str) or not item.strip():
                raise ValueError(f"{name}.{key} is required")
        if value["kind"] not in {"working-day", "working-time"}:
            raise ValueError(f"{name}.kind is invalid")

    @staticmethod
    def _iso_datetime(value: object, name: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} is required")
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"{name} must be ISO-8601 date-time") from exc

    @staticmethod
    def _enum(item: Mapping[str, object], name: str, values: set[str]) -> None:
        value = item.get(name)
        if value not in values:
            raise ValueError(f"{name} is invalid")
