from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol


@dataclass(frozen=True)
class ProjectRevision:
    """Authoritative project revision snapshot exposed at the API boundary."""

    contract_version = "sync-project-revision.v1"

    tenant_id: str
    project_id: str
    revision: int

    def validate(self) -> None:
        if not self.tenant_id.strip() or not self.project_id.strip():
            raise ValueError("INVALID_PROJECT_CONTEXT")
        if self.revision < 0:
            raise ValueError("INVALID_PROJECT_REVISION")


class ProjectRevisionReader(Protocol):
    def get_revision(self, tenant_id: str, project_id: str) -> int: ...


@dataclass(frozen=True)
class InMemoryProjectRevisionReader:
    """Deterministic reader used by tests and local integration harnesses."""

    revisions: Mapping[tuple[str, str], int]

    def get_revision(self, tenant_id: str, project_id: str) -> int:
        key = (tenant_id, project_id)
        if key not in self.revisions:
            raise ValueError("PROJECT_NOT_FOUND")
        revision = self.revisions[key]
        if revision < 0:
            raise ValueError("INVALID_PROJECT_REVISION")
        return revision


@dataclass(frozen=True)
class VersionedSyncRevisionEndpoint:
    """Framework-neutral GET /api/v1/sync/revision handler."""

    reader: ProjectRevisionReader

    def get(self, context: Mapping[str, object]) -> dict[str, object]:
        tenant_id = str(context["tenant_id"])
        project_id = str(context["project_id"])
        if not tenant_id or not project_id:
            raise ValueError("INVALID_PROJECT_CONTEXT")

        revision = self.reader.get_revision(tenant_id, project_id)
        snapshot = ProjectRevision(
            tenant_id=tenant_id,
            project_id=project_id,
            revision=revision,
        )
        snapshot.validate()
        return {
            "contract_version": snapshot.contract_version,
            "tenant_id": snapshot.tenant_id,
            "project_id": snapshot.project_id,
            "revision": snapshot.revision,
        }
