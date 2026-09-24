from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectContext:
    tenant_id: str
    project_id: str
    revision: int

    def __post_init__(self) -> None:
        if not self.tenant_id or not self.project_id:
            raise ValueError("tenant_id and project_id are required")
        if self.revision < 0:
            raise ValueError("revision must be non-negative")
