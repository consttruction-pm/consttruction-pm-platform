from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .application.authorization import AuthorizationContext
from .dependency_graph_application import DependencyGraphApplicationService
from .dependency_graph_persistence import DependencyLink


@dataclass(frozen=True)
class DependencyGraphCreateRequest:
    contract_version: str
    resource_id: str
    tenant_id: str
    project_id: str
    revision: int
    source_resource_id: str
    target_resource_id: str
    dependency_type: str
    metadata: dict[str, Any]
    expected_graph_revision: int
    idempotency_key: str
    actor_id: str
    occurred_at: datetime

    def validate(self) -> None:
        if self.contract_version != "dependency-graph.v1":
            raise ValueError("UNSUPPORTED_DEPENDENCY_CONTRACT_VERSION")
        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise ValueError("DEPENDENCY_AUDIT_TIMESTAMP_MUST_BE_TIMEZONE_AWARE")


@dataclass(frozen=True)
class DependencyGraphAPI:
    service: DependencyGraphApplicationService

    def create(
        self,
        request: DependencyGraphCreateRequest,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        request.validate()
        stored = self.service.create(
            DependencyLink(
                resource_id=request.resource_id,
                tenant_id=request.tenant_id,
                project_id=request.project_id,
                revision=request.revision,
                source_resource_id=request.source_resource_id,
                target_resource_id=request.target_resource_id,
                dependency_type=request.dependency_type,
                metadata=dict(request.metadata),
            ),
            context=auth_context,
            expected_graph_revision=request.expected_graph_revision,
            idempotency_key=request.idempotency_key,
            actor_id=request.actor_id,
            occurred_at=request.occurred_at,
        )
        return {
            "contract_version": "dependency-graph.v1",
            "operation": "create",
            "resource_id": stored.link.resource_id,
            "tenant_id": stored.link.tenant_id,
            "project_id": stored.link.project_id,
            "revision": stored.link.revision,
            "graph_revision": stored.graph_revision,
            "source_resource_id": stored.link.source_resource_id,
            "target_resource_id": stored.link.target_resource_id,
            "dependency_type": stored.link.dependency_type,
            "metadata": dict(stored.link.metadata),
        }
