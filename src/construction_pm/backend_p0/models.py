from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Mapping

from construction_pm.client_sync.revision_limits import MAX_SAFE_PROJECT_REVISION

MAX_SAFE_REVISION = MAX_SAFE_PROJECT_REVISION


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


@dataclass(frozen=True)
class FieldActivityAllocation:
    activity_id: str
    quantity: Decimal
    unit: str

    def validate(self) -> None:
        _require_text(self.activity_id, "activity_id")
        if self.quantity <= Decimal("0"):
            raise ValueError("allocation quantity must be greater than zero")
        _require_text(self.unit, "unit")

    def as_dict(self) -> dict[str, Any]:
        self.validate()
        return {"activity_id": self.activity_id, "quantity": self.quantity, "unit": self.unit}


@dataclass(frozen=True)
class FieldTimecard:
    timecard_id: str
    scope: BackendScope
    person_id: str
    log_date: date
    workplace_key: str
    attendance_status: str
    audit: AuditMetadata
    start_at: datetime | None = None
    end_at: datetime | None = None
    activity_allocations: tuple[FieldActivityAllocation, ...] = ()
    evidence_refs: tuple[EvidenceRef, ...] = ()
    contract_version: str = "field-timecard.v1"

    def validate(self) -> None:
        _require_text(self.timecard_id, "timecard_id")
        self.scope.validate()
        _require_text(self.person_id, "person_id")
        _require_text(self.workplace_key, "workplace_key")
        if self.attendance_status not in {"present", "absent", "late", "leave", "on_site"}:
            raise ValueError("invalid attendance status")
        if not isinstance(self.log_date, date):
            raise ValueError("log_date must be a date")
        if self.start_at is not None:
            _require_aware(self.start_at, "start_at")
        if self.end_at is not None:
            _require_aware(self.end_at, "end_at")
        if self.start_at and self.end_at and self.end_at < self.start_at:
            raise ValueError("end_at cannot precede start_at")
        for allocation in self.activity_allocations:
            allocation.validate()
        self.audit.validate()
        for evidence in self.evidence_refs:
            evidence.validate()

    def as_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "contract_version": self.contract_version,
            "timecard_id": self.timecard_id,
            "scope": {
                "tenant_id": self.scope.tenant_id,
                "project_id": self.scope.project_id,
                "project_revision": self.scope.project_revision,
            },
            "person_id": self.person_id,
            "log_date": self.log_date.isoformat(),
            "workplace_key": self.workplace_key,
            "attendance_status": self.attendance_status,
            "start_at": self.start_at.isoformat() if self.start_at else None,
            "end_at": self.end_at.isoformat() if self.end_at else None,
            "activity_allocations": [item.as_dict() for item in self.activity_allocations],
            "audit": self.audit.as_dict(),
            "evidence_refs": [item.as_dict() for item in self.evidence_refs],
        }


@dataclass(frozen=True)
class EquipmentStatusReport:
    report_id: str
    scope: BackendScope
    equipment_id: str
    report_date: date
    workplace_key: str
    status: str
    reported_by: str
    audit: AuditMetadata
    breakdown_cause_key: str | None = None
    activity_allocations: tuple[FieldActivityAllocation, ...] = ()
    meter_hours: Decimal | None = None
    evidence_refs: tuple[EvidenceRef, ...] = ()
    contract_version: str = "equipment-status-report.v1"

    def validate(self) -> None:
        _require_text(self.report_id, "report_id")
        self.scope.validate()
        _require_text(self.equipment_id, "equipment_id")
        _require_text(self.workplace_key, "workplace_key")
        _require_text(self.reported_by, "reported_by")
        if self.status not in {"active", "broken", "idle", "maintenance", "offsite"}:
            raise ValueError("invalid equipment status")
        if not isinstance(self.report_date, date):
            raise ValueError("report_date must be a date")
        if self.status == "broken" and not self.breakdown_cause_key:
            raise ValueError("broken equipment requires breakdown cause")
        if self.breakdown_cause_key is not None:
            _require_text(self.breakdown_cause_key, "breakdown_cause_key")
        if self.meter_hours is not None and self.meter_hours < Decimal("0"):
            raise ValueError("meter_hours cannot be negative")
        for allocation in self.activity_allocations:
            allocation.validate()
        self.audit.validate()
        for evidence in self.evidence_refs:
            evidence.validate()

    def as_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "contract_version": self.contract_version,
            "report_id": self.report_id,
            "scope": {
                "tenant_id": self.scope.tenant_id,
                "project_id": self.scope.project_id,
                "project_revision": self.scope.project_revision,
            },
            "equipment_id": self.equipment_id,
            "report_date": self.report_date.isoformat(),
            "workplace_key": self.workplace_key,
            "status": self.status,
            "breakdown_cause_key": self.breakdown_cause_key,
            "reported_by": self.reported_by,
            "activity_allocations": [item.as_dict() for item in self.activity_allocations],
            "meter_hours": self.meter_hours,
            "audit": self.audit.as_dict(),
            "evidence_refs": [item.as_dict() for item in self.evidence_refs],
        }


@dataclass(frozen=True)
class FieldInspectionItem:
    item_id: str
    criterion_key: str
    result: str
    comment_key: str | None = None

    def validate(self) -> None:
        _require_text(self.item_id, "item_id")
        _require_text(self.criterion_key, "criterion_key")
        if self.result not in {"pass", "fail", "na"}:
            raise ValueError("invalid inspection item result")
        if self.comment_key is not None:
            _require_text(self.comment_key, "comment_key")

    def as_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "item_id": self.item_id,
            "criterion_key": self.criterion_key,
            "result": self.result,
            "comment_key": self.comment_key,
        }


@dataclass(frozen=True)
class FieldInspection:
    inspection_id: str
    scope: BackendScope
    inspection_type_key: str
    subject_type: str
    subject_id: str
    inspection_date: date
    inspector_id: str
    status: str
    result: str
    checklist: tuple[FieldInspectionItem, ...]
    audit: AuditMetadata
    location_key: str | None = None
    evidence_refs: tuple[EvidenceRef, ...] = ()
    contract_version: str = "field-inspection.v1"

    def validate(self) -> None:
        _require_text(self.inspection_id, "inspection_id")
        self.scope.validate()
        _require_text(self.inspection_type_key, "inspection_type_key")
        _require_text(self.subject_type, "subject_type")
        _require_text(self.subject_id, "subject_id")
        _require_text(self.inspector_id, "inspector_id")
        if self.status not in {"draft", "scheduled", "in_progress", "completed", "cancelled"}:
            raise ValueError("invalid inspection status")
        if self.result not in {"pass", "fail", "conditional", "na"}:
            raise ValueError("invalid inspection result")
        if not isinstance(self.inspection_date, date):
            raise ValueError("inspection_date must be a date")
        if not self.checklist:
            raise ValueError("inspection requires at least one checklist item")
        ids: set[str] = set()
        for item in self.checklist:
            item.validate()
            if item.item_id in ids:
                raise ValueError("duplicate inspection item_id")
            ids.add(item.item_id)
        if self.location_key is not None:
            _require_text(self.location_key, "location_key")
        self.audit.validate()
        for evidence in self.evidence_refs:
            evidence.validate()

    def as_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "contract_version": self.contract_version,
            "inspection_id": self.inspection_id,
            "scope": {
                "tenant_id": self.scope.tenant_id,
                "project_id": self.scope.project_id,
                "project_revision": self.scope.project_revision,
            },
            "inspection_type_key": self.inspection_type_key,
            "subject_type": self.subject_type,
            "subject_id": self.subject_id,
            "location_key": self.location_key,
            "inspection_date": self.inspection_date.isoformat(),
            "inspector_id": self.inspector_id,
            "status": self.status,
            "result": self.result,
            "checklist": [item.as_dict() for item in self.checklist],
            "audit": self.audit.as_dict(),
            "evidence_refs": [item.as_dict() for item in self.evidence_refs],
        }


@dataclass(frozen=True)
class QualityRecord:
    record_id: str
    scope: BackendScope
    category_key: str
    severity: str
    status: str
    title_key: str
    reported_by: str
    audit: AuditMetadata
    detail_key: str | None = None
    location_key: str | None = None
    activity_ids: tuple[str, ...] = ()
    inspection_id: str | None = None
    specification_reference: str | None = None
    corrective_action_key: str | None = None
    disposition_key: str | None = None
    evidence_refs: tuple[EvidenceRef, ...] = ()
    contract_version: str = "quality-record.v1"

    def validate(self) -> None:
        _require_text(self.record_id, "record_id")
        self.scope.validate()
        _require_text(self.category_key, "category_key")
        _require_text(self.title_key, "title_key")
        _require_text(self.reported_by, "reported_by")
        if self.severity not in {"low", "medium", "high", "critical"}:
            raise ValueError("invalid quality severity")
        if self.status not in {"open", "in_progress", "pending_verification", "accepted", "rejected", "closed", "cancelled"}:
            raise ValueError("invalid quality status")
        for value in (*self.activity_ids,):
            _require_text(value, "activity_id")
        for value, name in (
            (self.detail_key, "detail_key"),
            (self.location_key, "location_key"),
            (self.inspection_id, "inspection_id"),
            (self.specification_reference, "specification_reference"),
            (self.corrective_action_key, "corrective_action_key"),
            (self.disposition_key, "disposition_key"),
        ):
            if value is not None:
                _require_text(value, name)
        if not self.evidence_refs:
            raise ValueError("quality record requires at least one evidence reference")
        self.audit.validate()
        for evidence in self.evidence_refs:
            evidence.validate()

    def as_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "contract_version": self.contract_version,
            "record_id": self.record_id,
            "scope": {
                "tenant_id": self.scope.tenant_id,
                "project_id": self.scope.project_id,
                "project_revision": self.scope.project_revision,
            },
            "category_key": self.category_key,
            "severity": self.severity,
            "status": self.status,
            "title_key": self.title_key,
            "detail_key": self.detail_key,
            "reported_by": self.reported_by,
            "location_key": self.location_key,
            "activity_ids": list(self.activity_ids),
            "inspection_id": self.inspection_id,
            "specification_reference": self.specification_reference,
            "corrective_action_key": self.corrective_action_key,
            "disposition_key": self.disposition_key,
            "audit": self.audit.as_dict(),
            "evidence_refs": [item.as_dict() for item in self.evidence_refs],
        }


@dataclass(frozen=True)
class SafetyObservation:
    observation_id: str
    scope: BackendScope
    category_key: str
    severity: str
    status: str
    title_key: str
    observed_by: str
    audit: AuditMetadata
    location_key: str | None = None
    activity_ids: tuple[str, ...] = ()
    immediate_action_key: str | None = None
    root_cause_key: str | None = None
    evidence_refs: tuple[EvidenceRef, ...] = ()
    contract_version: str = "safety-observation.v1"

    def validate(self) -> None:
        _require_text(self.observation_id, "observation_id")
        self.scope.validate()
        _require_text(self.category_key, "category_key")
        _require_text(self.title_key, "title_key")
        _require_text(self.observed_by, "observed_by")
        if self.severity not in {"low", "medium", "high", "critical"}:
            raise ValueError("invalid safety severity")
        if self.status not in {"open", "in_progress", "resolved", "closed", "cancelled"}:
            raise ValueError("invalid safety status")
        for value in self.activity_ids:
            _require_text(value, "activity_id")
        for value, name in (
            (self.location_key, "location_key"),
            (self.immediate_action_key, "immediate_action_key"),
            (self.root_cause_key, "root_cause_key"),
        ):
            if value is not None:
                _require_text(value, name)
        if self.severity in {"high", "critical"} and not self.immediate_action_key:
            raise ValueError("high or critical safety observation requires immediate action")
        if not self.evidence_refs:
            raise ValueError("safety observation requires at least one evidence reference")
        self.audit.validate()
        for evidence in self.evidence_refs:
            evidence.validate()

    def as_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "contract_version": self.contract_version,
            "observation_id": self.observation_id,
            "scope": {
                "tenant_id": self.scope.tenant_id,
                "project_id": self.scope.project_id,
                "project_revision": self.scope.project_revision,
            },
            "category_key": self.category_key,
            "severity": self.severity,
            "status": self.status,
            "title_key": self.title_key,
            "observed_by": self.observed_by,
            "location_key": self.location_key,
            "activity_ids": list(self.activity_ids),
            "immediate_action_key": self.immediate_action_key,
            "root_cause_key": self.root_cause_key,
            "audit": self.audit.as_dict(),
            "evidence_refs": [item.as_dict() for item in self.evidence_refs],
        }


@dataclass(frozen=True)
class PunchItem:
    punch_id: str
    scope: BackendScope
    category_key: str
    priority: str
    status: str
    title_key: str
    reported_by: str
    audit: AuditMetadata
    location_key: str | None = None
    activity_ids: tuple[str, ...] = ()
    responsible_party_id: str | None = None
    due_date: date | None = None
    verification_by: str | None = None
    closeout_code_key: str | None = None
    evidence_refs: tuple[EvidenceRef, ...] = ()
    contract_version: str = "punch-item.v1"

    def validate(self) -> None:
        _require_text(self.punch_id, "punch_id")
        self.scope.validate()
        _require_text(self.category_key, "category_key")
        _require_text(self.title_key, "title_key")
        _require_text(self.reported_by, "reported_by")
        if self.priority not in {"low", "medium", "high", "critical"}:
            raise ValueError("invalid punch priority")
        if self.status not in {"open", "in_progress", "ready_for_verification", "rejected", "closed", "cancelled"}:
            raise ValueError("invalid punch status")
        for value in self.activity_ids:
            _require_text(value, "activity_id")
        for value, name in (
            (self.location_key, "location_key"),
            (self.responsible_party_id, "responsible_party_id"),
            (self.verification_by, "verification_by"),
            (self.closeout_code_key, "closeout_code_key"),
        ):
            if value is not None:
                _require_text(value, name)
        if self.due_date is not None and not isinstance(self.due_date, date):
            raise ValueError("due_date must be a date")
        if self.status == "closed" and not self.verification_by:
            raise ValueError("closed punch item requires verification_by")
        if not self.evidence_refs:
            raise ValueError("punch item requires at least one evidence reference")
        self.audit.validate()
        for evidence in self.evidence_refs:
            evidence.validate()

    def as_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "contract_version": self.contract_version,
            "punch_id": self.punch_id,
            "scope": {
                "tenant_id": self.scope.tenant_id,
                "project_id": self.scope.project_id,
                "project_revision": self.scope.project_revision,
            },
            "category_key": self.category_key,
            "priority": self.priority,
            "status": self.status,
            "title_key": self.title_key,
            "reported_by": self.reported_by,
            "location_key": self.location_key,
            "activity_ids": list(self.activity_ids),
            "responsible_party_id": self.responsible_party_id,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "verification_by": self.verification_by,
            "closeout_code_key": self.closeout_code_key,
            "audit": self.audit.as_dict(),
            "evidence_refs": [item.as_dict() for item in self.evidence_refs],
        }


@dataclass(frozen=True)
class ChangeCase:
    change_id: str
    scope: BackendScope
    change_type: str
    status: str
    title_key: str
    initiated_by: str
    audit: AuditMetadata
    detail_key: str | None = None
    originating_notice_id: str | None = None
    schedule_refs: tuple[str, ...] = ()
    cost_refs: tuple[str, ...] = ()
    dependency_refs: tuple[str, ...] = ()
    impact_link_ids: tuple[str, ...] = ()
    implementation_activity_ids: tuple[str, ...] = ()
    approval_required: bool = True
    approved_by: str | None = None
    approved_at: datetime | None = None
    evidence_refs: tuple[EvidenceRef, ...] = ()
    contract_version: str = "change-case.v1"

    def validate(self) -> None:
        _require_text(self.change_id, "change_id")
        self.scope.validate()
        _require_text(self.title_key, "title_key")
        _require_text(self.initiated_by, "initiated_by")
        if self.change_type not in {"potential_change", "instruction", "variation", "delay_event"}:
            raise ValueError("invalid change type")
        if self.status not in {"draft", "under_review", "approved", "rejected", "implemented", "closed", "cancelled"}:
            raise ValueError("invalid change status")
        for value, name in (
            (self.detail_key, "detail_key"),
            (self.originating_notice_id, "originating_notice_id"),
        ):
            if value is not None:
                _require_text(value, name)
        for values, name in (
            (self.schedule_refs, "schedule_reference"),
            (self.cost_refs, "cost_reference"),
            (self.dependency_refs, "dependency_reference"),
            (self.impact_link_ids, "impact_link_id"),
            (self.implementation_activity_ids, "activity_id"),
        ):
            for value in values:
                _require_text(value, name)
        if self.status == "approved":
            if not self.approved_by or not self.approved_at:
                raise ValueError("approved change requires approver and timestamp")
        if self.approved_by is not None:
            _require_text(self.approved_by, "approved_by")
        if self.approved_at is not None:
            _require_aware(self.approved_at, "approved_at")
        if not self.evidence_refs:
            raise ValueError("change case requires at least one evidence reference")
        self.audit.validate()
        for evidence in self.evidence_refs:
            evidence.validate()

    def as_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "contract_version": self.contract_version,
            "change_id": self.change_id,
            "scope": {"tenant_id": self.scope.tenant_id, "project_id": self.scope.project_id, "project_revision": self.scope.project_revision},
            "change_type": self.change_type,
            "status": self.status,
            "title_key": self.title_key,
            "detail_key": self.detail_key,
            "initiated_by": self.initiated_by,
            "originating_notice_id": self.originating_notice_id,
            "schedule_refs": list(self.schedule_refs),
            "cost_refs": list(self.cost_refs),
            "dependency_refs": list(self.dependency_refs),
            "impact_link_ids": list(self.impact_link_ids),
            "implementation_activity_ids": list(self.implementation_activity_ids),
            "approval_required": self.approval_required,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "audit": self.audit.as_dict(),
            "evidence_refs": [item.as_dict() for item in self.evidence_refs],
        }


@dataclass(frozen=True)
class ClaimRecord:
    claim_id: str
    scope: BackendScope
    claim_type: str
    status: str
    title_key: str
    submitted_by: str
    audit: AuditMetadata
    detail_key: str | None = None
    originating_notice_id: str | None = None
    change_id: str | None = None
    schedule_refs: tuple[str, ...] = ()
    cost_refs: tuple[str, ...] = ()
    impact_link_ids: tuple[str, ...] = ()
    entitlement_reference: str | None = None
    quantum_reference: str | None = None
    decision_reference: str | None = None
    approval_required: bool = True
    decided_by: str | None = None
    decided_at: datetime | None = None
    evidence_refs: tuple[EvidenceRef, ...] = ()
    contract_version: str = "claim-record.v1"

    def validate(self) -> None:
        _require_text(self.claim_id, "claim_id")
        self.scope.validate()
        _require_text(self.title_key, "title_key")
        _require_text(self.submitted_by, "submitted_by")
        if self.claim_type not in {"extension_of_time", "compensation", "variation", "delay", "other"}:
            raise ValueError("invalid claim type")
        if self.status not in {"draft", "submitted", "under_review", "accepted", "partially_accepted", "rejected", "settled", "closed", "withdrawn"}:
            raise ValueError("invalid claim status")
        for value, name in (
            (self.detail_key, "detail_key"),
            (self.originating_notice_id, "originating_notice_id"),
            (self.change_id, "change_id"),
            (self.entitlement_reference, "entitlement_reference"),
            (self.quantum_reference, "quantum_reference"),
            (self.decision_reference, "decision_reference"),
            (self.decided_by, "decided_by"),
        ):
            if value is not None:
                _require_text(value, name)
        for values, name in (
            (self.schedule_refs, "schedule_reference"),
            (self.cost_refs, "cost_reference"),
            (self.impact_link_ids, "impact_link_id"),
        ):
            for value in values:
                _require_text(value, name)
        if self.status in {"accepted", "partially_accepted", "rejected", "settled", "closed"}:
            if not self.decided_by or not self.decided_at:
                raise ValueError("decided claim requires decision actor and timestamp")
        if self.decided_at is not None:
            _require_aware(self.decided_at, "decided_at")
        if not self.evidence_refs:
            raise ValueError("claim requires at least one evidence reference")
        self.audit.validate()
        for evidence in self.evidence_refs:
            evidence.validate()

    def as_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "contract_version": self.contract_version,
            "claim_id": self.claim_id,
            "scope": {"tenant_id": self.scope.tenant_id, "project_id": self.scope.project_id, "project_revision": self.scope.project_revision},
            "claim_type": self.claim_type,
            "status": self.status,
            "title_key": self.title_key,
            "detail_key": self.detail_key,
            "submitted_by": self.submitted_by,
            "originating_notice_id": self.originating_notice_id,
            "change_id": self.change_id,
            "schedule_refs": list(self.schedule_refs),
            "cost_refs": list(self.cost_refs),
            "impact_link_ids": list(self.impact_link_ids),
            "entitlement_reference": self.entitlement_reference,
            "quantum_reference": self.quantum_reference,
            "decision_reference": self.decision_reference,
            "approval_required": self.approval_required,
            "decided_by": self.decided_by,
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
            "audit": self.audit.as_dict(),
            "evidence_refs": [item.as_dict() for item in self.evidence_refs],
        }


@dataclass(frozen=True)
class ProcurementQuoteItem:
    item_id: str
    description_key: str
    quantity: Decimal
    unit: str
    unit_price: Decimal
    lead_time_days: int | None = None
    activity_ids: tuple[str, ...] = ()
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        _require_text(self.item_id, "item_id")
        _require_text(self.description_key, "description_key")
        if self.quantity <= Decimal("0"):
            raise ValueError("quote quantity must be greater than zero")
        _require_text(self.unit, "unit")
        if self.unit_price < Decimal("0"):
            raise ValueError("unit price cannot be negative")
        if self.lead_time_days is not None and (
            not isinstance(self.lead_time_days, int) or isinstance(self.lead_time_days, bool) or self.lead_time_days < 0
        ):
            raise ValueError("lead_time_days must be a non-negative integer")
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
            "unit_price": self.unit_price,
            "lead_time_days": self.lead_time_days,
            "activity_ids": list(self.activity_ids),
            "attributes": dict(self.attributes),
        }


@dataclass(frozen=True)
class ProcurementQuote:
    quote_id: str
    scope: BackendScope
    rfq_id: str
    supplier_id: str
    status: str
    currency: str
    valid_until: date
    items: tuple[ProcurementQuoteItem, ...]
    audit: AuditMetadata
    delivery_terms_key: str | None = None
    payment_terms_key: str | None = None
    notes_key: str | None = None
    evidence_refs: tuple[EvidenceRef, ...] = ()
    contract_version: str = "procurement-quote.v1"

    def validate(self) -> None:
        _require_text(self.quote_id, "quote_id")
        self.scope.validate()
        _require_text(self.rfq_id, "rfq_id")
        _require_text(self.supplier_id, "supplier_id")
        _require_text(self.currency, "currency")
        if len(self.currency) != 3 or not self.currency.isalpha() or not self.currency.isupper():
            raise ValueError("currency must be a three-letter uppercase code")
        if self.status not in {"draft", "submitted", "under_review", "withdrawn", "accepted", "rejected", "expired"}:
            raise ValueError("invalid quote status")
        if not isinstance(self.valid_until, date):
            raise ValueError("valid_until must be a date")
        if not self.items:
            raise ValueError("quote requires at least one item")
        ids: set[str] = set()
        for item in self.items:
            item.validate()
            if item.item_id in ids:
                raise ValueError("duplicate quote item_id")
            ids.add(item.item_id)
        for value, name in (
            (self.delivery_terms_key, "delivery_terms_key"),
            (self.payment_terms_key, "payment_terms_key"),
            (self.notes_key, "notes_key"),
        ):
            if value is not None:
                _require_text(value, name)
        if not self.evidence_refs:
            raise ValueError("quote requires at least one evidence reference")
        self.audit.validate()
        for evidence in self.evidence_refs:
            evidence.validate()

    def as_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "contract_version": self.contract_version,
            "quote_id": self.quote_id,
            "scope": {
                "tenant_id": self.scope.tenant_id,
                "project_id": self.scope.project_id,
                "project_revision": self.scope.project_revision,
            },
            "rfq_id": self.rfq_id,
            "supplier_id": self.supplier_id,
            "status": self.status,
            "currency": self.currency,
            "valid_until": self.valid_until.isoformat(),
            "items": [item.as_dict() for item in self.items],
            "delivery_terms_key": self.delivery_terms_key,
            "payment_terms_key": self.payment_terms_key,
            "notes_key": self.notes_key,
            "audit": self.audit.as_dict(),
            "evidence_refs": [item.as_dict() for item in self.evidence_refs],
        }


@dataclass(frozen=True)
class ProcurementBidComparisonEntry:
    quote_id: str
    supplier_id: str
    compliance_status: str
    evaluator_notes_key: str | None = None
    technical_reference: str | None = None
    commercial_reference: str | None = None

    def validate(self) -> None:
        _require_text(self.quote_id, "quote_id")
        _require_text(self.supplier_id, "supplier_id")
        if self.compliance_status not in {"compliant", "partial", "non_compliant", "not_evaluated"}:
            raise ValueError("invalid compliance status")
        for value, name in (
            (self.evaluator_notes_key, "evaluator_notes_key"),
            (self.technical_reference, "technical_reference"),
            (self.commercial_reference, "commercial_reference"),
        ):
            if value is not None:
                _require_text(value, name)

    def as_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "quote_id": self.quote_id,
            "supplier_id": self.supplier_id,
            "compliance_status": self.compliance_status,
            "evaluator_notes_key": self.evaluator_notes_key,
            "technical_reference": self.technical_reference,
            "commercial_reference": self.commercial_reference,
        }


@dataclass(frozen=True)
class ProcurementBidComparison:
    comparison_id: str
    scope: BackendScope
    rfq_id: str
    status: str
    entries: tuple[ProcurementBidComparisonEntry, ...]
    audit: AuditMetadata
    selected_quote_id: str | None = None
    selected_supplier_id: str | None = None
    decision_reference: str | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    evidence_refs: tuple[EvidenceRef, ...] = ()
    contract_version: str = "procurement-bid-comparison.v1"

    def validate(self) -> None:
        _require_text(self.comparison_id, "comparison_id")
        self.scope.validate()
        _require_text(self.rfq_id, "rfq_id")
        if self.status not in {"draft", "under_review", "approved", "rejected", "closed"}:
            raise ValueError("invalid bid comparison status")
        if not self.entries:
            raise ValueError("bid comparison requires at least one entry")
        quote_ids: set[str] = set()
        for entry in self.entries:
            entry.validate()
            if entry.quote_id in quote_ids:
                raise ValueError("duplicate comparison quote_id")
            quote_ids.add(entry.quote_id)
        if self.selected_quote_id is not None:
            _require_text(self.selected_quote_id, "selected_quote_id")
            if self.selected_quote_id not in quote_ids:
                raise ValueError("selected quote must be present in comparison")
        if self.selected_supplier_id is not None:
            _require_text(self.selected_supplier_id, "selected_supplier_id")
            if self.selected_quote_id is None:
                raise ValueError("selected supplier requires selected quote")
        if self.status == "approved" and (not self.selected_quote_id or not self.selected_supplier_id or not self.approved_by or not self.approved_at):
            raise ValueError("approved bid comparison requires selection and approval")
        if self.decision_reference is not None:
            _require_text(self.decision_reference, "decision_reference")
        if self.approved_by is not None:
            _require_text(self.approved_by, "approved_by")
        if self.approved_at is not None:
            _require_aware(self.approved_at, "approved_at")
        if not self.evidence_refs:
            raise ValueError("bid comparison requires at least one evidence reference")
        self.audit.validate()
        for evidence in self.evidence_refs:
            evidence.validate()

    def as_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "contract_version": self.contract_version,
            "comparison_id": self.comparison_id,
            "scope": {
                "tenant_id": self.scope.tenant_id,
                "project_id": self.scope.project_id,
                "project_revision": self.scope.project_revision,
            },
            "rfq_id": self.rfq_id,
            "status": self.status,
            "entries": [item.as_dict() for item in self.entries],
            "selected_quote_id": self.selected_quote_id,
            "selected_supplier_id": self.selected_supplier_id,
            "decision_reference": self.decision_reference,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "audit": self.audit.as_dict(),
            "evidence_refs": [item.as_dict() for item in self.evidence_refs],
        }


@dataclass(frozen=True)
class PurchaseOrderItem:
    item_id: str
    description_key: str
    quantity: Decimal
    unit: str
    unit_price: Decimal
    activity_ids: tuple[str, ...] = ()
    delivery_location_key: str | None = None

    def validate(self) -> None:
        _require_text(self.item_id, "item_id")
        _require_text(self.description_key, "description_key")
        if self.quantity <= Decimal("0"):
            raise ValueError("order quantity must be greater than zero")
        _require_text(self.unit, "unit")
        if self.unit_price < Decimal("0"):
            raise ValueError("order unit price cannot be negative")
        for activity_id in self.activity_ids:
            _require_text(activity_id, "activity_id")
        if self.delivery_location_key is not None:
            _require_text(self.delivery_location_key, "delivery_location_key")

    def as_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "item_id": self.item_id,
            "description_key": self.description_key,
            "quantity": self.quantity,
            "unit": self.unit,
            "unit_price": self.unit_price,
            "activity_ids": list(self.activity_ids),
            "delivery_location_key": self.delivery_location_key,
        }


@dataclass(frozen=True)
class PurchaseOrder:
    po_id: str
    scope: BackendScope
    supplier_id: str
    status: str
    currency: str
    items: tuple[PurchaseOrderItem, ...]
    audit: AuditMetadata
    rfq_id: str | None = None
    quote_id: str | None = None
    order_date: date | None = None
    required_delivery_date: date | None = None
    commitment_id: str | None = None
    approval_reference: str | None = None
    evidence_refs: tuple[EvidenceRef, ...] = ()
    contract_version: str = "purchase-order.v1"

    def validate(self) -> None:
        _require_text(self.po_id, "po_id")
        self.scope.validate()
        _require_text(self.supplier_id, "supplier_id")
        _require_text(self.currency, "currency")
        if len(self.currency) != 3 or not self.currency.isalpha() or not self.currency.isupper():
            raise ValueError("currency must be a three-letter uppercase code")
        if self.status not in {"draft", "approved", "issued", "partially_received", "closed", "cancelled"}:
            raise ValueError("invalid purchase order status")
        if not self.items:
            raise ValueError("purchase order requires at least one item")
        ids: set[str] = set()
        for item in self.items:
            item.validate()
            if item.item_id in ids:
                raise ValueError("duplicate purchase order item_id")
            ids.add(item.item_id)
        for value, name in (
            (self.rfq_id, "rfq_id"),
            (self.quote_id, "quote_id"),
            (self.commitment_id, "commitment_id"),
            (self.approval_reference, "approval_reference"),
        ):
            if value is not None:
                _require_text(value, name)
        if self.order_date is not None and not isinstance(self.order_date, date):
            raise ValueError("order_date must be a date")
        if self.required_delivery_date is not None and not isinstance(self.required_delivery_date, date):
            raise ValueError("required_delivery_date must be a date")
        if self.order_date and self.required_delivery_date and self.required_delivery_date < self.order_date:
            raise ValueError("required delivery date cannot precede order date")
        if self.status == "approved" and not self.approval_reference:
            raise ValueError("approved purchase order requires approval reference")
        if not self.evidence_refs:
            raise ValueError("purchase order requires at least one evidence reference")
        self.audit.validate()
        for evidence in self.evidence_refs:
            evidence.validate()

    def as_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "contract_version": self.contract_version,
            "po_id": self.po_id,
            "scope": {
                "tenant_id": self.scope.tenant_id,
                "project_id": self.scope.project_id,
                "project_revision": self.scope.project_revision,
            },
            "rfq_id": self.rfq_id,
            "quote_id": self.quote_id,
            "supplier_id": self.supplier_id,
            "status": self.status,
            "currency": self.currency,
            "order_date": self.order_date.isoformat() if self.order_date else None,
            "required_delivery_date": self.required_delivery_date.isoformat() if self.required_delivery_date else None,
            "items": [item.as_dict() for item in self.items],
            "commitment_id": self.commitment_id,
            "approval_reference": self.approval_reference,
            "audit": self.audit.as_dict(),
            "evidence_refs": [item.as_dict() for item in self.evidence_refs],
        }


@dataclass(frozen=True)
class ProcurementCommitment:
    commitment_id: str
    scope: BackendScope
    status: str
    supplier_id: str
    currency: str
    committed_amount: Decimal
    audit: AuditMetadata
    po_id: str | None = None
    cost_refs: tuple[str, ...] = ()
    activity_ids: tuple[str, ...] = ()
    release_reference: str | None = None
    notes_key: str | None = None
    evidence_refs: tuple[EvidenceRef, ...] = ()
    contract_version: str = "procurement-commitment.v1"

    def validate(self) -> None:
        _require_text(self.commitment_id, "commitment_id")
        self.scope.validate()
        _require_text(self.supplier_id, "supplier_id")
        _require_text(self.currency, "currency")
        if len(self.currency) != 3 or not self.currency.isalpha() or not self.currency.isupper():
            raise ValueError("currency must be a three-letter uppercase code")
        if self.committed_amount < Decimal("0"):
            raise ValueError("committed amount cannot be negative")
        if self.status not in {"planned", "committed", "partially_released", "released", "closed", "cancelled"}:
            raise ValueError("invalid commitment status")
        if self.po_id is not None:
            _require_text(self.po_id, "po_id")
        for values, name in ((self.cost_refs, "cost_reference"), (self.activity_ids, "activity_id")):
            for value in values:
                _require_text(value, name)
        if self.status in {"partially_released", "released"} and not self.release_reference:
            raise ValueError("released commitment requires release reference")
        if self.release_reference is not None:
            _require_text(self.release_reference, "release_reference")
        if self.notes_key is not None:
            _require_text(self.notes_key, "notes_key")
        if not self.evidence_refs:
            raise ValueError("commitment requires at least one evidence reference")
        self.audit.validate()
        for evidence in self.evidence_refs:
            evidence.validate()

    def as_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "contract_version": self.contract_version,
            "commitment_id": self.commitment_id,
            "scope": {
                "tenant_id": self.scope.tenant_id,
                "project_id": self.scope.project_id,
                "project_revision": self.scope.project_revision,
            },
            "po_id": self.po_id,
            "supplier_id": self.supplier_id,
            "status": self.status,
            "currency": self.currency,
            "committed_amount": self.committed_amount,
            "cost_refs": list(self.cost_refs),
            "activity_ids": list(self.activity_ids),
            "release_reference": self.release_reference,
            "notes_key": self.notes_key,
            "audit": self.audit.as_dict(),
            "evidence_refs": [item.as_dict() for item in self.evidence_refs],
        }


@dataclass(frozen=True)
class ProcurementDeliveryItem:
    item_id: str
    quantity_received: Decimal
    unit: str
    inspection_id: str | None = None
    punch_id: str | None = None
    acceptance_status: str = "pending"

    def validate(self) -> None:
        _require_text(self.item_id, "item_id")
        if self.quantity_received <= Decimal("0"):
            raise ValueError("received quantity must be greater than zero")
        _require_text(self.unit, "unit")
        for value, name in ((self.inspection_id, "inspection_id"), (self.punch_id, "punch_id")):
            if value is not None:
                _require_text(value, name)
        if self.acceptance_status not in {"pending", "accepted", "rejected", "partial"}:
            raise ValueError("invalid acceptance status")

    def as_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "item_id": self.item_id,
            "quantity_received": self.quantity_received,
            "unit": self.unit,
            "inspection_id": self.inspection_id,
            "punch_id": self.punch_id,
            "acceptance_status": self.acceptance_status,
        }


@dataclass(frozen=True)
class ProcurementDelivery:
    delivery_id: str
    scope: BackendScope
    po_id: str
    supplier_id: str
    status: str
    delivery_date: date
    items: tuple[ProcurementDeliveryItem, ...]
    audit: AuditMetadata
    location_key: str | None = None
    receipt_reference: str | None = None
    evidence_refs: tuple[EvidenceRef, ...] = ()
    contract_version: str = "procurement-delivery.v1"

    def validate(self) -> None:
        _require_text(self.delivery_id, "delivery_id")
        self.scope.validate()
        _require_text(self.po_id, "po_id")
        _require_text(self.supplier_id, "supplier_id")
        if self.status not in {"scheduled", "partial", "received", "rejected", "cancelled"}:
            raise ValueError("invalid delivery status")
        if not isinstance(self.delivery_date, date):
            raise ValueError("delivery_date must be a date")
        if not self.items:
            raise ValueError("delivery requires at least one item")
        for item in self.items:
            item.validate()
        if self.location_key is not None:
            _require_text(self.location_key, "location_key")
        if self.receipt_reference is not None:
            _require_text(self.receipt_reference, "receipt_reference")
        if self.status == "received" and not self.receipt_reference:
            raise ValueError("received delivery requires receipt reference")
        if not self.evidence_refs:
            raise ValueError("delivery requires at least one evidence reference")
        self.audit.validate()
        for evidence in self.evidence_refs:
            evidence.validate()

    def as_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "contract_version": self.contract_version,
            "delivery_id": self.delivery_id,
            "scope": {
                "tenant_id": self.scope.tenant_id,
                "project_id": self.scope.project_id,
                "project_revision": self.scope.project_revision,
            },
            "po_id": self.po_id,
            "supplier_id": self.supplier_id,
            "status": self.status,
            "delivery_date": self.delivery_date.isoformat(),
            "location_key": self.location_key,
            "items": [item.as_dict() for item in self.items],
            "receipt_reference": self.receipt_reference,
            "audit": self.audit.as_dict(),
            "evidence_refs": [item.as_dict() for item in self.evidence_refs],
        }


@dataclass(frozen=True)
class Portfolio:
    portfolio_id: str
    tenant_id: str
    status: str
    name_key: str
    audit: AuditMetadata
    description_key: str | None = None
    contract_version: str = "portfolio.v1"

    def validate(self) -> None:
        _require_text(self.portfolio_id, "portfolio_id")
        _require_text(self.tenant_id, "tenant_id")
        _require_text(self.name_key, "name_key")
        if self.status not in {"draft", "active", "archived"}:
            raise ValueError("invalid portfolio status")
        if self.description_key is not None:
            _require_text(self.description_key, "description_key")
        self.audit.validate()

    def as_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "contract_version": self.contract_version,
            "portfolio_id": self.portfolio_id,
            "tenant_id": self.tenant_id,
            "status": self.status,
            "name_key": self.name_key,
            "description_key": self.description_key,
            "audit": self.audit.as_dict(),
        }


@dataclass(frozen=True)
class PortfolioProjectLink:
    link_id: str
    portfolio_id: str
    tenant_id: str
    project_id: str
    project_revision: int
    status: str
    role: str
    audit: AuditMetadata
    display_name_key: str | None = None
    manager_id: str | None = None
    tags: tuple[str, ...] = ()
    contract_version: str = "portfolio-project-link.v1"

    def validate(self) -> None:
        _require_text(self.link_id, "link_id")
        _require_text(self.portfolio_id, "portfolio_id")
        _require_text(self.tenant_id, "tenant_id")
        _require_text(self.project_id, "project_id")
        if not isinstance(self.project_revision, int) or isinstance(self.project_revision, bool) or not 0 <= self.project_revision <= MAX_SAFE_REVISION:
            raise ValueError("invalid project revision")
        if self.status not in {"included", "on_hold", "excluded"}:
            raise ValueError("invalid portfolio project link status")
        if self.role not in {"member", "program", "priority", "reference"}:
            raise ValueError("invalid portfolio project link role")
        for value, name in ((self.display_name_key, "display_name_key"), (self.manager_id, "manager_id")):
            if value is not None:
                _require_text(value, name)
        for tag in self.tags:
            _require_text(tag, "tag")
        self.audit.validate()

    def as_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "contract_version": self.contract_version,
            "link_id": self.link_id,
            "portfolio_id": self.portfolio_id,
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "project_revision": self.project_revision,
            "status": self.status,
            "role": self.role,
            "display_name_key": self.display_name_key,
            "manager_id": self.manager_id,
            "tags": list(self.tags),
            "audit": self.audit.as_dict(),
        }


@dataclass(frozen=True)
class PortfolioSnapshotProject:
    project_id: str
    project_revision: int
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
        _require_text(self.project_id, "project_id")
        if not isinstance(self.project_revision, int) or isinstance(self.project_revision, bool) or not 0 <= self.project_revision <= MAX_SAFE_REVISION:
            raise ValueError("invalid project revision")
        _require_text(self.status, "project status")
        if self.name_key is not None:
            _require_text(self.name_key, "name_key")
        for value, name in (
            (self.schedule_result_ref, "schedule_result_ref"),
            (self.progress_result_ref, "progress_result_ref"),
            (self.cost_result_ref, "cost_result_ref"),
            (self.resource_result_ref, "resource_result_ref"),
            (self.risk_result_ref, "risk_result_ref"),
            (self.claim_result_ref, "claim_result_ref"),
            (self.procurement_result_ref, "procurement_result_ref"),
        ):
            if value is not None:
                _require_text(value, name)

    def as_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "project_id": self.project_id,
            "project_revision": self.project_revision,
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
    generated_at: datetime
    projects: tuple[PortfolioSnapshotProject, ...]
    source_refs: tuple[EvidenceRef, ...]
    audit: AuditMetadata
    contract_version: str = "portfolio-control-snapshot.v1"

    def validate(self) -> None:
        _require_text(self.snapshot_id, "snapshot_id")
        _require_text(self.portfolio_id, "portfolio_id")
        _require_aware(self.generated_at, "generated_at")
        if not self.projects:
            raise ValueError("portfolio snapshot requires at least one project")
        ids: set[str] = set()
        for project in self.projects:
            project.validate()
            if project.project_id in ids:
                raise ValueError("duplicate portfolio project")
            ids.add(project.project_id)
        if not self.source_refs:
            raise ValueError("portfolio snapshot requires at least one source reference")
        self.audit.validate()
        for evidence in self.source_refs:
            evidence.validate()

    def as_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "contract_version": self.contract_version,
            "snapshot_id": self.snapshot_id,
            "portfolio_id": self.portfolio_id,
            "generated_at": self.generated_at.isoformat(),
            "projects": [item.as_dict() for item in self.projects],
            "source_refs": [item.as_dict() for item in self.source_refs],
            "audit": self.audit.as_dict(),
        }


@dataclass(frozen=True)
class PortfolioDecision:
    decision_id: str
    portfolio_id: str
    tenant_id: str
    status: str
    decision_type: str
    title_key: str
    audit: AuditMetadata
    detail_key: str | None = None
    affected_project_ids: tuple[str, ...] = ()
    source_snapshot_id: str | None = None
    impact_link_ids: tuple[str, ...] = ()
    requires_approval: bool = True
    approved_by: str | None = None
    approved_at: datetime | None = None
    evidence_refs: tuple[EvidenceRef, ...] = ()
    contract_version: str = "portfolio-decision.v1"

    def validate(self) -> None:
        _require_text(self.decision_id, "decision_id")
        _require_text(self.portfolio_id, "portfolio_id")
        _require_text(self.tenant_id, "tenant_id")
        _require_text(self.title_key, "title_key")
        if self.status not in {"proposed", "under_review", "approved", "rejected", "implemented", "closed", "cancelled"}:
            raise ValueError("invalid portfolio decision status")
        if self.decision_type not in {"escalate", "prioritize", "hold", "review", "sequence", "approve"}:
            raise ValueError("invalid portfolio decision type")
        for value, name in ((self.detail_key, "detail_key"), (self.source_snapshot_id, "source_snapshot_id"), (self.approved_by, "approved_by")):
            if value is not None:
                _require_text(value, name)
        for value in (*self.affected_project_ids, *self.impact_link_ids):
            _require_text(value, "reference")
        if self.status == "approved" and (not self.approved_by or not self.approved_at):
            raise ValueError("approved portfolio decision requires approval")
        if self.approved_at is not None:
            _require_aware(self.approved_at, "approved_at")
        if not self.evidence_refs:
            raise ValueError("portfolio decision requires at least one evidence reference")
        self.audit.validate()
        for evidence in self.evidence_refs:
            evidence.validate()

    def as_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "contract_version": self.contract_version,
            "decision_id": self.decision_id,
            "portfolio_id": self.portfolio_id,
            "tenant_id": self.tenant_id,
            "status": self.status,
            "decision_type": self.decision_type,
            "title_key": self.title_key,
            "detail_key": self.detail_key,
            "affected_project_ids": list(self.affected_project_ids),
            "source_snapshot_id": self.source_snapshot_id,
            "impact_link_ids": list(self.impact_link_ids),
            "requires_approval": self.requires_approval,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "audit": self.audit.as_dict(),
            "evidence_refs": [item.as_dict() for item in self.evidence_refs],
        }


Record = FieldDailyLog | FieldIssue | ChangeNotice | ProcurementRFQ | FieldTimecard | EquipmentStatusReport | FieldInspection | QualityRecord | SafetyObservation | PunchItem | ChangeCase | ClaimRecord | ProcurementQuote | ProcurementBidComparison | PurchaseOrder | ProcurementCommitment | ProcurementDelivery | Portfolio | PortfolioProjectLink | PortfolioControlSnapshot | PortfolioDecision


def resource_type(record: Record) -> str:
    if isinstance(record, FieldDailyLog):
        return "field_daily_log"
    if isinstance(record, FieldIssue):
        return "field_issue"
    if isinstance(record, ChangeNotice):
        return "change_notice"
    if isinstance(record, ProcurementRFQ):
        return "procurement_rfq"
    if isinstance(record, FieldTimecard):
        return "field_timecard"
    if isinstance(record, EquipmentStatusReport):
        return "equipment_status_report"
    if isinstance(record, FieldInspection):
        return "field_inspection"
    if isinstance(record, QualityRecord):
        return "quality_record"
    if isinstance(record, SafetyObservation):
        return "safety_observation"
    if isinstance(record, PunchItem):
        return "punch_item"
    if isinstance(record, ChangeCase):
        return "change_case"
    if isinstance(record, ClaimRecord):
        return "claim_record"
    if isinstance(record, ProcurementQuote):
        return "procurement_quote"
    if isinstance(record, ProcurementBidComparison):
        return "procurement_bid_comparison"
    if isinstance(record, PurchaseOrder):
        return "purchase_order"
    if isinstance(record, ProcurementCommitment):
        return "procurement_commitment"
    if isinstance(record, ProcurementDelivery):
        return "procurement_delivery"
    if isinstance(record, Portfolio):
        return "portfolio"
    if isinstance(record, PortfolioProjectLink):
        return "portfolio_project_link"
    if isinstance(record, PortfolioControlSnapshot):
        return "portfolio_control_snapshot"
    if isinstance(record, PortfolioDecision):
        return "portfolio_decision"
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
    if isinstance(record, FieldTimecard):
        return record.timecard_id
    if isinstance(record, EquipmentStatusReport):
        return record.report_id
    if isinstance(record, FieldInspection):
        return record.inspection_id
    if isinstance(record, QualityRecord):
        return record.record_id
    if isinstance(record, SafetyObservation):
        return record.observation_id
    if isinstance(record, PunchItem):
        return record.punch_id
    if isinstance(record, ChangeCase):
        return record.change_id
    if isinstance(record, ClaimRecord):
        return record.claim_id
    if isinstance(record, ProcurementQuote):
        return record.quote_id
    if isinstance(record, ProcurementBidComparison):
        return record.comparison_id
    if isinstance(record, PurchaseOrder):
        return record.po_id
    if isinstance(record, ProcurementCommitment):
        return record.commitment_id
    if isinstance(record, ProcurementDelivery):
        return record.delivery_id
    if isinstance(record, Portfolio):
        return record.portfolio_id
    if isinstance(record, PortfolioProjectLink):
        return record.link_id
    if isinstance(record, PortfolioControlSnapshot):
        return record.snapshot_id
    if isinstance(record, PortfolioDecision):
        return record.decision_id
    raise TypeError(f"Unsupported record type: {type(record)!r}")
