from __future__ import annotations

from dataclasses import dataclass
from .adapter import ClientMutationRequest
from .resource import RESOURCE_OPERATIONS

@dataclass(frozen=True)
class ClientResourceMutationFactory:
    """Builds Resource API mutations from the authoritative project session boundary."""

    @staticmethod
    def create_resource(request: ClientMutationRequest) -> ClientMutationRequest:
        request.validate()
        if request.operation != 'create_resource': raise ValueError('resource request operation mismatch')
        return request

    @staticmethod
    def create_assignment(request: ClientMutationRequest) -> ClientMutationRequest:
        request.validate()
        if request.operation != 'create_assignment': raise ValueError('assignment request operation mismatch')
        return request

def validate_resource_mutation_operation(operation: str) -> None:
    if operation not in RESOURCE_OPERATIONS: raise ValueError('unsupported resource operation')
