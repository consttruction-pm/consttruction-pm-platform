from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class BIIntegrationError(ValueError):
    pass


@dataclass(frozen=True)
class BIOperation:
    tenant_id: str
    project_id: str
    operation_id: str
    dataset: str
    payload: dict[str, object]

    def validate(self) -> None:
        if self.contract_version != "1.0":
            raise BIIntegrationError("UNSUPPORTED_BI_CONTRACT_VERSION")
        for name, value in (
            ("tenant_id", self.tenant_id),
            ("project_id", self.project_id),
            ("operation_id", self.operation_id),
            ("dataset", self.dataset),
        ):
            if not isinstance(value, str) or not value.strip():
                raise BIIntegrationError(f"INVALID_BI_{name.upper()}")
        if not isinstance(self.payload, dict):
            raise BIIntegrationError("INVALID_BI_PAYLOAD")


@dataclass(frozen=True)
class BISyncResult:
    tenant_id: str
    project_id: str
    operation_id: str
    status: str
    external_reference: str | None
    message: str = ""
    contract_version: str = "1.0"

    def validate(self) -> None:
        for name, value in (
            ("tenant_id", self.tenant_id),
            ("project_id", self.project_id),
            ("operation_id", self.operation_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise BIIntegrationError(f"INVALID_BI_{name.upper()}")
        if self.status not in {"accepted", "rejected", "retry"}:
            raise BIIntegrationError("INVALID_BI_STATUS")
        if self.external_reference is not None and not isinstance(self.external_reference, str):
            raise BIIntegrationError("INVALID_BI_EXTERNAL_REFERENCE")


class BIAdapter(Protocol):
    def sync(self, operation: BIOperation) -> BISyncResult: ...


class ReferenceBIAdapter:
    """Provider-neutral BI integration seam; it does not calculate project metrics."""

    def __init__(self, *, status: str = "accepted", external_reference: str | None = "bi-reference-1") -> None:
        self.status = status
        self.external_reference = external_reference

    def sync(self, operation: BIOperation) -> BISyncResult:
        operation.validate()
        result = BISyncResult(
            tenant_id=operation.tenant_id,
            project_id=operation.project_id,
            operation_id=operation.operation_id,
            status=self.status,
            external_reference=self.external_reference,
        )
        result.validate()
        return result
