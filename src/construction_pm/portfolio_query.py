from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol


class PortfolioQueryError(ValueError):
    pass


@dataclass(frozen=True)
class PortfolioProjectSnapshot:
    tenant_id: str
    project_id: str
    as_of: str
    status: str
    metrics: Mapping[str, object]

    def validate(self) -> None:
        for name, value in (
            ("tenant_id", self.tenant_id),
            ("project_id", self.project_id),
            ("as_of", self.as_of),
            ("status", self.status),
        ):
            if not isinstance(value, str) or not value.strip():
                raise PortfolioQueryError(f"INVALID_PORTFOLIO_{name.upper()}")
        if not isinstance(self.metrics, Mapping):
            raise PortfolioQueryError("INVALID_PORTFOLIO_METRICS")


class PortfolioQueryAdapter(Protocol):
    def list_projects(self, tenant_id: str) -> tuple[PortfolioProjectSnapshot, ...]: ...


class InMemoryPortfolioQueryAdapter:
    """Reference read-model adapter; metrics are supplied by authoritative domain/read models."""

    def __init__(self, snapshots: tuple[PortfolioProjectSnapshot, ...] = ()) -> None:
        self._snapshots = snapshots

    def list_projects(self, tenant_id: str) -> tuple[PortfolioProjectSnapshot, ...]:
        if not isinstance(tenant_id, str) or not tenant_id.strip():
            raise PortfolioQueryError("INVALID_PORTFOLIO_TENANT_ID")
        for snapshot in self._snapshots:
            snapshot.validate()
        return tuple(snapshot for snapshot in self._snapshots if snapshot.tenant_id == tenant_id)
