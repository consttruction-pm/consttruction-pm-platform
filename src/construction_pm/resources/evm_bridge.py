from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal

from construction_pm.scheduling.earned_value import (
    ETC_REMAINING_COST,
    EarnedValueInput,
    calculate_earned_value,
)

@dataclass(frozen=True)
class ResourceEVMInput:
    pv: Decimal
    ev: Decimal
    ac: Decimal
    remaining_resource_cost: Decimal
    bac: Decimal | None = None

@dataclass(frozen=True)
class ResourceEVMResult:
    pv: Decimal
    ev: Decimal
    ac: Decimal
    etc: Decimal
    eac: Decimal
    vac: Decimal | None
    cv: Decimal
    sv: Decimal
    cpi: Decimal | None = None
    spi: Decimal | None = None

def build_resource_evm_result(data: ResourceEVMInput) -> ResourceEVMResult:
    """Delegate resource EVM arithmetic to the shared Earned Value core."""

    result = calculate_earned_value(
        EarnedValueInput(
            planned_value=data.pv,
            earned_value=data.ev,
            actual_cost=data.ac,
            budget_at_completion=data.bac,
            remaining_cost=data.remaining_resource_cost,
            etc_method=ETC_REMAINING_COST,
        )
    )
    return ResourceEVMResult(
        pv=result.planned_value,
        ev=result.earned_value,
        ac=result.actual_cost,
        etc=result.estimate_to_complete,
        eac=result.estimate_at_completion,
        vac=result.variance_at_completion,
        cv=result.cost_variance,
        sv=result.schedule_variance,
        cpi=result.cost_performance_index,
        spi=result.schedule_performance_index,
    )
