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
        return tuple(str(v) for v in (
            self.planned_cost, self.actual_cost,
            self.remaining_cost, self.at_completion_cost,
        ))

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
