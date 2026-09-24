from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal

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

def build_resource_evm_result(data: ResourceEVMInput) -> ResourceEVMResult:
    etc = data.remaining_resource_cost
    eac = data.ac + etc
    vac = None if data.bac is None else data.bac - eac
    return ResourceEVMResult(
        pv=data.pv, ev=data.ev, ac=data.ac,
        etc=etc, eac=eac, vac=vac,
        cv=data.ev - data.ac, sv=data.ev - data.pv,
    )
