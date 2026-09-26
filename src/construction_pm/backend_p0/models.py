from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Mapping

MAX_SAFE_REVISION = 9_007_199_254_740_991


def _require_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is required")


def _require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


@dataclass(frozen=True)
class BackendScope:
    tenant_id: str
    project_id: str
    project_revision: int

    def validate(self) -> None:
        _require_text(self.tenant_id, "tenant_id")
        _require_text(self.project_id, "project_id")
        if not isinstance(self.project_revision, int) or isinstance(self.project_revision, bool):
            raise ValueError("project_revision must be an integer")
        if not 0 <= self.project_revision <= MAX_SAFE_REVISION:
            raise ValueError("project_revision exceeds supported safe integer range")


@dataclass(frozen=True)
class AuditMetadata:
    created_by: str
    created_at: datetime
    updated_at: datetime
    correlation_id: str | None = None
    source: str | None = None

    def validate(self) -> None:
        _require_text(self.created_by, "created_by")
        _require_aware(self.created_at, "created_at")
        _require_aware(self.updated_at, "updated_at")

    def as_dict(self) -> dict[str, Any]:
        return {
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "correlation_id": self.correlation_id,
            "source": self.source,
        }


@dataclass(frozen=True)
class EvidenceRef:
    source_id: str
    source_type: str
    locator: str
    revision: int

    def validate(self) -> None:
        _require_text(self.source_id, "evidence.source_id")
        _require_text(self.source_type, "evidence.source_type")
        _require_text(self.locator, "evidence.locator")
        if not isinstance(self.revision, int) or isinstance(self.revision, bool):
            raise ValueError("evidence.revision must be an integer")
        if not 0 <= self.revision <= MAX_SAFE_REVISION:
            raise ValueError("evidence.revision exceeds supported safe integer range")

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type,
            "locator": self.locator,
            "revision": self.revision,
        }


@dataclass(frozen=True)
class FieldDailyLogEntry:
    entry_id: str
    category: str
    text_key: str
    activity_ids: tuple[str, ...] = ()
    resource_ids: tuple[str, ...] = ()
    quantity: Decimal | None = None
    unit: str | None = None
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        _require_text(self.entry_id, "entry_id")
        _require_text(self.category, "category")
        _require_text(self.text_key, "text_key")
        for value in (*self.activity_ids, *self.resource_ids):
            _require_text(value, "reference id")
        if self.unit is not None:
            _require_text(self.unit, "unit")
        if not isinstance(self.attributes, Mapping):
            raise ValueError("attributes must be an object")

    def as_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "entry_id": self.entry_id,
            "category": self.category,
            "text_key": self.text_key,
            "activity_ids": list(self.activity_ids),
            "resource_ids": list(self.resource_ids),
            "quantity": self.quantity if self.quantity is not None else None,
            "unit": self.unit,
            "attributes": dict(self.attributes),
        }


@dataclass(frozen=True)
class FieldDailyLog:
    log_id: str
    scope: BackendScope
    log_date: date
    location_key: str
    status: str
    entries: tuple[FieldDailyLogEntry, ...]
    audit: AuditMetadata
    evidence_refs: tuple[EvidenceRef, ...] = ()
    contract_version: str = "field-daily-log.v1"

    def validate(self) -> None:
        _require_text(self.log_id, "log_id")
        self.scope.validate()
        _require_text(self.location_key, "location_key")
        if self.status not in {"draft", "submitted", "approved", "rejected", "void"}:
            raise ValueError("invalid field daily log status")
        if not isinstance(self.log_date, date):
            raise ValueError("log_date must be a date")
        ids: set[str] = set()
        for entry in self.entries:
            entry.validate()
            if entry.entry_id in ids:
                raise ValueError("duplicate entry_id")
            ids.add(entry.entry_id)
        self.audit.validate()
        for evidence in self.evidence_refs:
            evidence.validate()

    def as_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "contract_version": self.contract_version,
            "log_id": self.log_id,
            "scope": {
                "tenant_id": self.scope.tenant_id,
                "project_id": self.scope.project_id,
                "project_revision": self.scope.project_revision,
            },
            "log_date": self.log_date.isoformat(),
            "location_key": self.location_key,
            "status": self.status,
            "entries": [entry.as_dict() for entry in self.entries],
            "audit": self.audit.as_dict(),
            "evidence_refs": [item.as_dict() for item in self.evidence_refs],
        }


@dataclass(frozen=True)
class FieldIssue:
    issue_id: str
    scope: BackendScope
    category: str
    severity: str
    status: str
    title_key: str
    reported_by: str
    audit: AuditMetadata
    detail_key: str | None = None
    location_key: str | None = None
    activity_ids: tuple[str, ...] = ()
    evidence_refs: tuple[EvidenceRef, ...] = ()
    attributes: Mapping[str, Any] = field(default_factory=dict)
    contract_version: str = "field-issue.v1"

    def validate(self) -> None:
        _require_text(self.issue_id, "issue_id")
        self.scope.validate()
        _require_text(self.category, "category")
        if self.severity not in {"low", "medium", "high", "critical"}:
            raise ValueError("invalid field issue severity")
        if self.status not in {"open", "in_progress", "resolved", "closed", "cancelled"}:
            raise ValueError("invalid field issue status")
        _require_text(self.title_key, "title_key")
        _require_text(self.reported_by, "reported_by")
        if self.detail_key is not None:
            _require_text(self.detail_key, "detail_key")
        if self.location_key is not None:
            _require_text(self.location_key, "location_key")
        for activity_id in self.activity_ids:
            _require_text(activity_id, "activity_id")
        if not self.evidence_refs:
            raise ValueError("field issue requires at least one evidence reference")
        for evidence in self.evidence_refs:
            evidence.validate()
        self.audit.validate()
        if not isinstance(self.attributes, Mapping):
            raise ValueError("attributes must be an object")

    def as_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "contract_version": self.contract_version,
            "issue_id": self.issue_id,
            "scope": {
                "tenant_id": self.scope.tenant_id,
                "project_id": self.scope.project_id,
                "project_revision": self.scope.project_revision,
            },
            "category": self.category,
            "severity": self.severity,
            "status": self.status,
            "title_key": self.title_key,
            "detail_key": self.detail_key,
            "reported_by": self.reported_by,
            "location_key": self.location_key,
            "activity_ids": list(self.activity_ids),
            "evidence_refs": [item.as_dict() for item in self.evidence_refs],
            "audit": self.audit.as_dict(),
            "attributes": dict(self.attributes),
        }


@dataclass(frozen=True)
class ChangeNotice:
    notice_id: str
    scope: BackendScope
    notice_type: str
    status: str
    title_key: str
    submitted_by: str
    audit: AuditMetadata
    detail_key: str | None = None
    notice_date: date | None = None
    schedule_refs: tuple[str, ...] = ()
    cost_refs: tuple[str, ...] = ()
    dependency_refs: tuple[str, ...] = ()
    evidence_refs: tuple[EvidenceRef, ...] = ()
    approval_required: bool = True
    attributes: Mapping[str, Any] = field(default_factory=dict)
    contract_version: str = "change-notice.v1"

    def validate(self) -> None:
        _require_text(self.notice_id, "notice_id")
        self.scope.validate()
        if self.notice_type not in {"potential_change", "instruction", "variation", "delay_notice", "claim_notice"}:
            raise ValueError("invalid change notice type")
        if self.status not in {"draft", "submitted", "under_review", "approved", "rejected", "withdrawn", "closed"}:
            raise ValueError("invalid change notice status")
        _require_text(self.title_key, "title_key")
        _require_text(self.submitted_by, "submitted_by")
        if self.detail_key is not None:
            _require_text(self.detail_key, "detail_key")
        if self.notice_date is not None and not isinstance(self.notice_date, date):
            raise ValueError("notice_date must be a date")
        for ref in (*self.schedule_refs, *self.cost_refs, *self.dependency_refs):
            _require_text(ref, "reference")
        if not self.evidence_refs:
            raise ValueError("change notice requires at least one evidence reference")
        for evidence in self.evidence_refs:
            evidence.validate()
        self.audit.validate()
        if not isinstance(self.attributes, Mapping):
            raise ValueError("attributes must be an object")

    def as_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "contract_version": self.contract_version,
            "notice_id": self.notice_id,
            "scope": {
                "tenant_id": self.scope.tenant_id,
                "project_id": self.scope.project_id,
                "project_revision": self.scope.project_revision,
            },
            "notice_type": self.notice_type,
            "status": self.status,
            "title_key": self.title_key,
            "detail_key": self.detail_key,
            "submitted_by": self.submitted_by,
            "notice_date": self.notice_date.isoformat() if self.notice_date else None,
            "schedule_refs": list(self.schedule_refs),
            "cost_refs": list(self.cost_refs),
            "dependency_refs": list(self.dependency_refs),
            "evidence_refs": [item.as_dict() for item in self.evidence_refs],
            "audit": self.audit.as_dict(),
            "approval_required": self.approval_required,
            "attributes": dict(self.attributes),
        }


@dataclass(frozen=True)
class ProcurementRFQItem:
    item_id: str
    description_key: str
    quantity: Decimal
    unit: str
    activity_ids: tuple[str, ...] = ()
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        _require_text(self.item_id, "item_id")
        _require_text(self.description_key, "description_key")
        if self.quantity <= Decimal("0"):
            raise ValueError("quantity must be greater than zero")
        _require_text(self.unit, "unit")
        for activity_id in self.activity_ids:
            _require_text(activity_id, "activity_id")
        if not isinstance(self.attributes, Mapping):
            raise ValueError("attributes must be an object")

    def as_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "item_id": self.item_id,
            "description_key": self.description_key,
            "quantity": self.quantity,
            "unit": self.unit,
            "activity_ids": list(self.activity_ids),
            "attributes": dict(self.attributes),
        }


@dataclass(frozen=True)
class ProcurementRFQ:
    rfq_id: str
    scope: BackendScope
    status: str
    title_key: str
    requested_by: str
    items: tuple[ProcurementRFQItem, ...]
    supplier_ids: tuple[str, ...]
    audit: AuditMetadata
    due_at: datetime | None = None
    attributes: Mapping[str, Any] = field(default_factory=dict)
    contract_version: str = "procurement-rfq.v1"

    def validate(self) -> None:
        _require_text(self.rfq_id, "rfq_id")
        self.scope.validate()
        if self.status not in {"draft", "issued", "clarification", "closed", "cancelled", "awarded"}:
            raise ValueError("invalid procurement RFQ status")
        _require_text(self.title_key, "title_key")
        _require_text(self.requested_by, "requested_by")
        if not self.items:
            raise ValueError("at least one RFQ item is required")
        item_ids: set[str] = set()
        for item in self.items:
            item.validate()
            if item.item_id in item_ids:
                raise ValueError("duplicate RFQ item_id")
            item_ids.add(item.item_id)
        for supplier_id in self.supplier_ids:
            _require_text(supplier_id, "supplier_id")
        if self.due_at is not None:
            _require_aware(self.due_at, "due_at")
        self.audit.validate()
        if not isinstance(self.attributes, Mapping):
            raise ValueError("attributes must be an object")

    def as_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "contract_version": self.contract_version,
            "rfq_id": self.rfq_id,
            "scope": {
                "tenant_id": self.scope.tenant_id,
                "project_id": self.scope.project_id,
                "project_revision": self.scope.project_revision,
            },
            "status": self.status,
            "title_key": self.title_key,
            "requested_by": self.requested_by,
            "due_at": self.due_at.isoformat() if self.due_at else None,
            "items": [item.as_dict() for item in self.items],
            "supplier_ids": list(self.supplier_ids),
            "audit": self.audit.as_dict(),
            "attributes": dict(self.attributes),
        }


Record = FieldDailyLog | FieldIssue | ChangeNotice | ProcurementRFQ


def resource_type(record: Record) -> str:
    if isinstance(record, FieldDailyLog):
        return "field_daily_log"
    if isinstance(record, FieldIssue):
        return "field_issue"
    if isinstance(record, ChangeNotice):
        return "change_notice"
    if isinstance(record, ProcurementRFQ):
        return "procurement_rfq"
    raise TypeError(f"Unsupported record type: {type(record)!r}")


def record_id(record: Record) -> str:
    if isinstance(record, FieldDailyLog):
        return record.log_id
    if isinstance(record, FieldIssue):
        return record.issue_id
    if isinstance(record, ChangeNotice):
        return record.notice_id
    if isinstance(record, ProcurementRFQ):
        return record.rfq_id
    raise TypeError(f"Unsupported record type: {type(record)!r}")
