from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OfflineProjectContext:
    """Portable context required to reproduce project calculations offline."""

    tenant_id: str
    company_id: str
    project_id: str
    project_schema_version: int
    calendar_id: str | None
    calendar_version: int | None
    scheduling_settings_version: int | None
    calculation_settings_version: int | None

    contract_version = "offline-project-context.v1"

    def validate(self) -> None:
        for name in ("tenant_id", "company_id", "project_id"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} is required")
        if self.project_schema_version < 1:
            raise ValueError("project_schema_version must be positive")
        for name in (
            "calendar_version",
            "scheduling_settings_version",
            "calculation_settings_version",
        ):
            value = getattr(self, name)
            if value is not None and value < 1:
                raise ValueError(f"{name} must be positive when provided")
        if self.calendar_id is None and self.calendar_version is not None:
            raise ValueError("calendar_version requires calendar_id")

    def fingerprint_payload(self) -> tuple[object, ...]:
        self.validate()
        return (
            self.contract_version,
            self.tenant_id,
            self.company_id,
            self.project_id,
            self.project_schema_version,
            self.calendar_id,
            self.calendar_version,
            self.scheduling_settings_version,
            self.calculation_settings_version,
        )
