from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class ERPAccountingIntegrationError(ValueError):
    pass


@dataclass(frozen=True)
class ERPAccountingOperation:
    tenant_id: str
    project_id: str
    operation_id: str
    operation_type: str
    payload: dict[str, object]

    def validate(self) -> None:
        for name, value in (
            ("tenant_id", self.tenant_id),
            ("project_id", self.project_id),
            ("operation_id", self.operation_id),
            ("operation_type", self.operation_type),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ERPAccountingIntegrationError(f"INVALID_ERP_ACCOUNTING_{name.upper()}")
        if not isinstance(self.payload, dict):
            raise ERPAccountingIntegrationError("INVALID_ERP_ACCOUNTING_PAYLOAD")


@dataclass(frozen=True)
class ERPAccountingSyncResult:
    tenant_id: str
    project_id: str
    operation_id: str
    status: str
    external_reference: str | None
    message: str = ""

    def validate(self) -> None:
        for name, value in (
            ("tenant_id", self.tenant_id),
            ("project_id", self.project_id),
            ("operation_id", self.operation_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ERPAccountingIntegrationError(f"INVALID_ERP_ACCOUNTING_{name.upper()}")
        if self.status not in {"accepted", "rejected", "retry"}:
            raise ERPAccountingIntegrationError("INVALID_ERP_ACCOUNTING_STATUS")
        if self.external_reference is not None and not isinstance(self.external_reference, str):
            raise ERPAccountingIntegrationError("INVALID_ERP_ACCOUNTING_EXTERNAL_REFERENCE")


class ERPAccountingAdapter(Protocol):
    def sync(self, operation: ERPAccountingOperation) -> ERPAccountingSyncResult: ...


class ReferenceERPAccountingAdapter:
    """Deterministic integration seam; no vendor SDK or accounting semantics live here."""

    def __init__(self, *, status: str = "accepted", external_reference: str | None = "reference-1") -> None:
        self.status = status
        self.external_reference = external_reference

    def sync(self, operation: ERPAccountingOperation) -> ERPAccountingSyncResult:
        operation.validate()
        result = ERPAccountingSyncResult(
            tenant_id=operation.tenant_id,
            project_id=operation.project_id,
            operation_id=operation.operation_id,
            status=self.status,
            external_reference=self.external_reference,
        )
        result.validate()
        return result
