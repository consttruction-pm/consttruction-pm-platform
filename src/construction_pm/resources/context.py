from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectContext:
    """Validated tenant/company/project boundary for resource application work."""

    tenant_id: str
    company_id: str
    project_id: str

    def validate(self) -> None:
        for name in ("tenant_id", "company_id", "project_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")

    def fingerprint_payload(self) -> tuple[str, str, str]:
        self.validate()
        return (self.tenant_id, self.company_id, self.project_id)
