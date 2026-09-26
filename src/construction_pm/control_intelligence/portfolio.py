from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping

from .contracts import MAX_SAFE_REVISION, SourceReference


_RESULT_FIELDS = (
    "schedule_result_ref",
    "progress_result_ref",
    "cost_result_ref",
    "resource_result_ref",
    "risk_result_ref",
    "claim_result_ref",
    "procurement_result_ref",
)


@dataclass(frozen=True)
class PortfolioProjectControlInput:
    project_id: str
    project_revision: int
    membership_status: str
    status: str
    name_key: str | None = None
    schedule_result_ref: str | None = None
    progress_result_ref: str | None = None
    cost_result_ref: str | None = None
    resource_result_ref: str | None = None
    risk_result_ref: str | None = None
    claim_result_ref: str | None = None
    procurement_result_ref: str | None = None

    def validate(self) -> None:
        if not isinstance(self.project_id, str) or not self.project_id.strip():
            raise ValueError("INVALID_PORTFOLIO_PROJECT_ID")
        if (
            isinstance(self.project_revision, bool)
            or not isinstance(self.project_revision, int)
            or not 0 <= self.project_revision <= MAX_SAFE_REVISION
        ):
            raise ValueError("INVALID_PORTFOLIO_PROJECT_REVISION")
        if self.membership_status not in {"included", "on_hold", "excluded"}:
            raise ValueError("INVALID_PORTFOLIO_MEMBERSHIP_STATUS")
        if not isinstance(self.status, str) or not self.status.strip():
            raise ValueError("INVALID_PORTFOLIO_PROJECT_STATUS")
        values = [(self.name_key, "name_key")]
        values.extend((getattr(self, name), name) for name in _RESULT_FIELDS)
        for value, field_name in values:
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"INVALID_{field_name.upper()}")

    def as_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "project_id": self.project_id,
            "project_revision": self.project_revision,
            "membership_status": self.membership_status,
            "status": self.status,
            "name_key": self.name_key,
            "schedule_result_ref": self.schedule_result_ref,
            "progress_result_ref": self.progress_result_ref,
            "cost_result_ref": self.cost_result_ref,
            "resource_result_ref": self.resource_result_ref,
            "risk_result_ref": self.risk_result_ref,
            "claim_result_ref": self.claim_result_ref,
            "procurement_result_ref": self.procurement_result_ref,
        }


@dataclass(frozen=True)
class PortfolioControlSnapshot:
    snapshot_id: str
    portfolio_id: str
    tenant_id: str
    generated_at: datetime
    projects: tuple[PortfolioProjectControlInput, ...]
    source_refs: tuple[SourceReference, ...]

    def validate(self) -> None:
        for value, name in (
            (self.snapshot_id, "snapshot_id"),
            (self.portfolio_id, "portfolio_id"),
            (self.tenant_id, "tenant_id"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"INVALID_{name.upper()}")
        if self.generated_at.tzinfo is None or self.generated_at.utcoffset() is None:
            raise ValueError("PORTFOLIO_SNAPSHOT_TIMESTAMP_MUST_BE_TIMEZONE_AWARE")
        if not self.projects:
            raise ValueError("PORTFOLIO_SNAPSHOT_PROJECTS_REQUIRED")
        ids: set[str] = set()
        for project in self.projects:
            project.validate()
            if project.project_id in ids:
                raise ValueError("DUPLICATE_PORTFOLIO_PROJECT")
            ids.add(project.project_id)
        if not self.source_refs:
            raise ValueError("PORTFOLIO_SNAPSHOT_SOURCE_REQUIRED")
        for source in self.source_refs:
            if source.revision < 0 or source.revision > MAX_SAFE_REVISION:
                raise ValueError("INVALID_PORTFOLIO_SOURCE_REVISION")

    @property
    def summary(self) -> Mapping[str, int]:
        counts = {
            "total_projects": len(self.projects),
            "included_projects": 0,
            "on_hold_projects": 0,
            "excluded_projects": 0,
        }
        for project in self.projects:
            counts[f"{project.membership_status}_projects"] += 1
        return counts

    def as_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "contract_version": "portfolio-control-snapshot.v1",
            "snapshot_id": self.snapshot_id,
            "portfolio_id": self.portfolio_id,
            "tenant_id": self.tenant_id,
            "generated_at": self.generated_at.isoformat(),
            "summary": dict(self.summary),
            "projects": [project.as_dict() for project in self.projects],
            "source_refs": [
                {
                    "source_id": source.source_id,
                    "source_type": source.source_type,
                    "locator": source.locator,
                    "revision": source.revision,
                    "excerpt_key": source.excerpt_key,
                    "content_hash": source.content_hash,
                }
                for source in self.source_refs
            ],
        }


def build_portfolio_control_snapshot(
    *,
    snapshot_id: str,
    portfolio_id: str,
    tenant_id: str,
    generated_at: datetime,
    projects: list[PortfolioProjectControlInput],
    source_refs: list[SourceReference],
) -> dict[str, object]:
    snapshot = PortfolioControlSnapshot(
        snapshot_id=snapshot_id,
        portfolio_id=portfolio_id,
        tenant_id=tenant_id,
        generated_at=generated_at,
        projects=tuple(projects),
        source_refs=tuple(source_refs),
    )
    return snapshot.as_dict()
