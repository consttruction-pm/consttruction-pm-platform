from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

RESOURCE_CONTRACT_VERSION = 'resource.v1'

@dataclass(frozen=True)
class ClientResourceDTO:
    id: str
    code: str
    name: str
    resource_type: str
    unit: str
    calendar_id: str | None
    active: bool
    revision: int
    contract_version: str = RESOURCE_CONTRACT_VERSION

    def validate(self) -> None:
        if not self.id.strip() or not self.code.strip() or not self.name.strip(): raise ValueError('resource identity fields are required')
        if not self.unit.strip(): raise ValueError('unit is required')
        if self.revision < 1: raise ValueError('revision must be positive')
        if self.contract_version != RESOURCE_CONTRACT_VERSION: raise ValueError('unsupported resource contract version')

@dataclass(frozen=True)
class ClientResourceAssignmentDTO:
    activity_id: str
    resource_id: str
    planned_units: str
    actual_units: str
    remaining_units: str
    planned_cost: str | None
    actual_cost: str | None
    remaining_cost: str | None
    revision: int
    contract_version: str = RESOURCE_CONTRACT_VERSION

    def validate(self) -> None:
        if not self.activity_id.strip() or not self.resource_id.strip(): raise ValueError('assignment identity fields are required')
        for value in (self.planned_units, self.actual_units, self.remaining_units):
            if not isinstance(value, str): raise ValueError('resource unit values must be decimal strings')
        for value in (self.planned_cost, self.actual_cost, self.remaining_cost):
            if value is not None and not isinstance(value, str): raise ValueError('resource cost values must be decimal strings')
        if self.revision < 1: raise ValueError('revision must be positive')
        if self.contract_version != RESOURCE_CONTRACT_VERSION: raise ValueError('unsupported resource contract version')

def parse_resource(payload: Mapping[str, object]) -> ClientResourceDTO:
    dto = ClientResourceDTO(str(payload['id']), str(payload['code']), str(payload['name']), str(payload['type']), str(payload['unit']), payload.get('calendar_id') if payload.get('calendar_id') is None else str(payload['calendar_id']), bool(payload['active']), int(payload['revision']), str(payload.get('contract_version', '')))
    dto.validate(); return dto

def parse_assignment(payload: Mapping[str, object]) -> ClientResourceAssignmentDTO:
    dto = ClientResourceAssignmentDTO(str(payload['activity_id']), str(payload['resource_id']), str(payload['planned_units']), str(payload['actual_units']), str(payload['remaining_units']), None if payload.get('planned_cost') is None else str(payload['planned_cost']), None if payload.get('actual_cost') is None else str(payload['actual_cost']), None if payload.get('remaining_cost') is None else str(payload['remaining_cost']), int(payload['revision']), str(payload.get('contract_version', '')))
    dto.validate(); return dto
