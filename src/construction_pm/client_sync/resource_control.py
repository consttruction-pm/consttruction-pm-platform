from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

@dataclass(frozen=True)
class ClientResourceControlDTO:
    planned_units: str
    actual_units: str
    remaining_units: str
    planned_cost: str
    actual_cost: str
    remaining_cost: str
    unit_variance: str
    cost_variance: str

    contract_version = 'resource-control-presentation.v1'

    def validate(self) -> None:
        for value in (self.planned_units,self.actual_units,self.remaining_units,self.planned_cost,self.actual_cost,self.remaining_cost,self.unit_variance,self.cost_variance):
            if not isinstance(value, str): raise ValueError('resource control values must be decimal strings')

    def to_payload(self) -> dict[str, object]:
        self.validate()
        return {'contract_version':self.contract_version,'planned_units':self.planned_units,'actual_units':self.actual_units,'remaining_units':self.remaining_units,'planned_cost':self.planned_cost,'actual_cost':self.actual_cost,'remaining_cost':self.remaining_cost,'unit_variance':self.unit_variance,'cost_variance':self.cost_variance}

def parse_resource_control(payload: Mapping[str, object]) -> ClientResourceControlDTO:
    keys=('planned_units','actual_units','remaining_units','planned_cost','actual_cost','remaining_cost','unit_variance','cost_variance')
    if any(not isinstance(payload.get(k), str) for k in keys): raise ValueError('resource control values must be decimal strings')
    dto=ClientResourceControlDTO(*(payload[k] for k in keys))
    dto.validate(); return dto
