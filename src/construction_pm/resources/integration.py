from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ResourceIntegrationSnapshot:
    planned_cost: Decimal
    actual_cost: Decimal
    remaining_cost: Decimal
    at_completion_cost: Decimal

    @property
    def is_non_negative(self) -> bool:
        return min(self.planned_cost, self.actual_cost, self.remaining_cost) >= Decimal("0")

    def fingerprint_payload(self) -> tuple[str, str, str, str]:
        return tuple(str(v) for v in (self.planned_cost, self.actual_cost, self.remaining_cost, self.at_completion_cost))


@dataclass(frozen=True)
class ResourcePortabilityContext:
    tenant_id: str
    project_id: str
    resource_schema_version: int
    calendar_id: str | None
    calendar_version: int | None
    calculation_settings_version: int | None

    def validate(self) -> None:
        if not self.tenant_id:
            raise ValueError("tenant_id is required")
        if not self.project_id:
            raise ValueError("project_id is required")
        if self.resource_schema_version < 1:
            raise ValueError("resource_schema_version must be positive")
        if self.calendar_version is not None and self.calendar_version < 1:
            raise ValueError("calendar_version must be positive")
        if self.calculation_settings_version is not None and self.calculation_settings_version < 1:
            raise ValueError("calculation_settings_version must be positive")

    def fingerprint_payload(self) -> tuple[str, ...]:
        self.validate()
        return (
            self.tenant_id,
            self.project_id,
            str(self.resource_schema_version),
            self.calendar_id or "",
            "" if self.calendar_version is None else str(self.calendar_version),
            "" if self.calculation_settings_version is None else str(self.calculation_settings_version),
        )


@dataclass(frozen=True)
class ResourceIntegrationEnvelope:
    context: ResourcePortabilityContext
    snapshot: ResourceIntegrationSnapshot

    def fingerprint_payload(self) -> tuple[str, ...]:
        return self.context.fingerprint_payload() + self.snapshot.fingerprint_payload()


def build_integration_snapshot(
    planned_cost: Decimal,
    actual_cost: Decimal,
    remaining_cost: Decimal,
) -> ResourceIntegrationSnapshot:
    if min(planned_cost, actual_cost, remaining_cost) < Decimal("0"):
        raise ValueError("Resource costs cannot be negative")
    return ResourceIntegrationSnapshot(
        planned_cost=planned_cost,
        actual_cost=actual_cost,
        remaining_cost=remaining_cost,
        at_completion_cost=actual_cost + remaining_cost,
    )
