from __future__ import annotations

from construction_pm.backend_p0.errors import BackendApplicationError, ErrorCategory
from construction_pm.backend_p0.models import (
    ProcurementBidComparison,
    ProcurementCommitment,
    ProcurementDelivery,
    ProcurementQuote,
    PurchaseOrder,
    Record,
)
from construction_pm.backend_p0.repository import BackendP0Repository


class ProcurementReferenceResolver:
    """Validate procurement record references inside the caller's transaction."""

    def __init__(self, repository: BackendP0Repository) -> None:
        self.repository = repository

    def validate(self, record: Record) -> None:
        if isinstance(record, ProcurementQuote):
            self._require(record, "procurement_rfq", record.rfq_id, "RFQ")
            return

        if isinstance(record, ProcurementBidComparison):
            rfq = self._require(record, "procurement_rfq", record.rfq_id, "RFQ")
            for entry in record.entries:
                quote = self._require(record, "procurement_quote", entry.quote_id, "quote")
                if quote.record.rfq_id != record.rfq_id:
                    raise BackendApplicationError(
                        ErrorCategory.VALIDATION,
                        "PROCUREMENT_REFERENCE_MISMATCH",
                        f"Quote {entry.quote_id!r} does not belong to RFQ {record.rfq_id!r}",
                    )
            return

        if isinstance(record, PurchaseOrder):
            rfq = None
            quote = None
            if record.rfq_id is not None:
                rfq = self._require(record, "procurement_rfq", record.rfq_id, "RFQ")
            if record.quote_id is not None:
                quote = self._require(record, "procurement_quote", record.quote_id, "quote")
            if record.commitment_id is not None:
                self._require(record, "procurement_commitment", record.commitment_id, "commitment")
            if rfq is not None and quote is not None and quote.record.rfq_id != record.rfq_id:
                raise BackendApplicationError(
                    ErrorCategory.VALIDATION,
                    "PROCUREMENT_REFERENCE_MISMATCH",
                    f"Quote {record.quote_id!r} does not belong to RFQ {record.rfq_id!r}",
                )
            return

        if isinstance(record, ProcurementCommitment):
            if record.po_id is not None:
                self._require(record, "purchase_order", record.po_id, "purchase order")
            return

        if isinstance(record, ProcurementDelivery):
            self._require(record, "purchase_order", record.po_id, "purchase order")
            return

    def _require(self, record: Record, record_type: str, referenced_id: str, label: str):
        stored = self.repository.get(
            record.scope.tenant_id,
            record.scope.project_id,
            record_type,
            referenced_id,
        )
        if stored is None:
            raise BackendApplicationError(
                ErrorCategory.NOT_FOUND,
                "PROCUREMENT_REFERENCE_NOT_FOUND",
                f"Referenced {label} {referenced_id!r} was not found in the current tenant/project scope",
            )
        return stored
