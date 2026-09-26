from __future__ import annotations

import json
import sqlite3
from decimal import Decimal

from .errors import OptimisticLockError
from .models import Record, record_id, resource_type
from .repository import BackendP0Repository, StoredRecord

SCHEMA_VERSION = 1

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS backend_p0_schema_version (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    version INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS backend_p0_records (
    tenant_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    record_type TEXT NOT NULL,
    record_id TEXT NOT NULL,
    contract_version TEXT NOT NULL,
    project_revision INTEGER NOT NULL,
    record_revision INTEGER NOT NULL,
    status TEXT NOT NULL,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    PRIMARY KEY (tenant_id, project_id, record_type, record_id)
);
CREATE INDEX IF NOT EXISTS idx_backend_p0_project
    ON backend_p0_records (tenant_id, project_id, record_type, project_revision);
"""


class SQLiteBackendP0Repository(BackendP0Repository):
    """Durable P0 persistence; application layer owns transaction boundaries."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.executescript(SCHEMA_SQL)
        self.connection.execute(
            "INSERT INTO backend_p0_schema_version (id, version) VALUES (1, ?) "
            "ON CONFLICT(id) DO UPDATE SET version=excluded.version",
            (SCHEMA_VERSION,),
        )
        self.connection.commit()

    def save(self, record: Record, expected_revision: int | None = None) -> StoredRecord:
        record.validate()
        rtype = resource_type(record)
        rid = record_id(record)
        payload = record.as_dict()
        scope = record.scope
        audit = record.audit

        row = self.connection.execute(
            "SELECT record_revision FROM backend_p0_records "
            "WHERE tenant_id=? AND project_id=? AND record_type=? AND record_id=?",
            (scope.tenant_id, scope.project_id, rtype, rid),
        ).fetchone()
        if row is None:
            if expected_revision not in (None, 0):
                raise OptimisticLockError(
                    f"Record does not exist: expected revision {expected_revision}"
                )
            revision = 1
            self.connection.execute(
                "INSERT INTO backend_p0_records "
                "(tenant_id, project_id, record_type, record_id, contract_version, "
                "project_revision, record_revision, status, created_by, created_at, updated_at, payload_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    scope.tenant_id,
                    scope.project_id,
                    rtype,
                    rid,
                    payload["contract_version"],
                    scope.project_revision,
                    revision,
                    _record_status(payload),
                    audit.created_by,
                    audit.created_at.isoformat(),
                    audit.updated_at.isoformat(),
                    json.dumps(payload, sort_keys=True, separators=(",", ":"), default=_json_default),
                ),
            )
            return StoredRecord(record, revision)

        current_revision = int(row[0])
        if expected_revision is None:
            raise OptimisticLockError("expected_revision is required for an update")
        if expected_revision != current_revision:
            raise OptimisticLockError(
                f"Stale record revision: expected {expected_revision}, current {current_revision}"
            )
        revision = current_revision + 1
        cursor = self.connection.execute(
            "UPDATE backend_p0_records SET contract_version=?, project_revision=?, record_revision=?, "
            "status=?, created_by=?, created_at=?, updated_at=?, payload_json=? "
            "WHERE tenant_id=? AND project_id=? AND record_type=? AND record_id=? AND record_revision=?",
            (
                payload["contract_version"],
                scope.project_revision,
                revision,
                _record_status(payload),
                audit.created_by,
                audit.created_at.isoformat(),
                audit.updated_at.isoformat(),
                json.dumps(payload, sort_keys=True, separators=(",", ":"), default=_json_default),
                scope.tenant_id,
                scope.project_id,
                rtype,
                rid,
                expected_revision,
            ),
        )
        if cursor.rowcount != 1:
            raise OptimisticLockError("Concurrent record update detected")
        return StoredRecord(record, revision)

    def get(self, tenant_id: str, project_id: str, record_type: str, record_id: str) -> StoredRecord | None:
        row = self.connection.execute(
            "SELECT payload_json, record_revision FROM backend_p0_records "
            "WHERE tenant_id=? AND project_id=? AND record_type=? AND record_id=?",
            (tenant_id, project_id, record_type, record_id),
        ).fetchone()
        if row is None:
            return None
        return StoredRecord(_record_from_payload(json.loads(row[0])), int(row[1]))



def _record_status(payload: dict) -> str:
    status = payload.get("status")
    if isinstance(status, str):
        return status
    attendance_status = payload.get("attendance_status")
    if isinstance(attendance_status, str):
        return attendance_status
    raise ValueError("Record payload does not expose a persistence status")


def _json_default(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _record_from_payload(payload: dict) -> Record:
    from datetime import date, datetime
    from .models import (
        AuditMetadata,
        BackendScope,
        ChangeNotice,
        EvidenceRef,
        FieldDailyLog,
        FieldDailyLogEntry,
        FieldIssue,
        ProcurementRFQ,
        ProcurementRFQItem,
        FieldActivityAllocation,
        FieldTimecard,
        EquipmentStatusReport,
        FieldInspectionItem,
        FieldInspection,
        QualityRecord,
        SafetyObservation,
        PunchItem,
        ChangeCase,
        ClaimRecord,
    )

    scope_data = payload["scope"]
    scope = BackendScope(
        scope_data["tenant_id"],
        scope_data["project_id"],
        int(scope_data["project_revision"]),
    )
    a = payload["audit"]
    audit = AuditMetadata(
        created_by=a["created_by"],
        created_at=datetime.fromisoformat(a["created_at"]),
        updated_at=datetime.fromisoformat(a["updated_at"]),
        correlation_id=a.get("correlation_id"),
        source=a.get("source"),
    )
    evidence = tuple(EvidenceRef(**item) for item in payload.get("evidence_refs", []))
    if payload["contract_version"] == "field-daily-log.v1":
        entries = tuple(
            FieldDailyLogEntry(
                entry_id=item["entry_id"],
                category=item["category"],
                text_key=item["text_key"],
                activity_ids=tuple(item.get("activity_ids", [])),
                resource_ids=tuple(item.get("resource_ids", [])),
                quantity=None if item.get("quantity") is None else Decimal(str(item["quantity"])),
                unit=item.get("unit"),
                attributes=item.get("attributes", {}),
            )
            for item in payload["entries"]
        )
        return FieldDailyLog(
            log_id=payload["log_id"],
            scope=scope,
            log_date=date.fromisoformat(payload["log_date"]),
            location_key=payload["location_key"],
            status=payload["status"],
            entries=entries,
            audit=audit,
            evidence_refs=evidence,
        )
    if payload["contract_version"] == "field-issue.v1":
        return FieldIssue(
            issue_id=payload["issue_id"],
            scope=scope,
            category=payload["category"],
            severity=payload["severity"],
            status=payload["status"],
            title_key=payload["title_key"],
            reported_by=payload["reported_by"],
            audit=audit,
            detail_key=payload.get("detail_key"),
            location_key=payload.get("location_key"),
            activity_ids=tuple(payload.get("activity_ids", [])),
            evidence_refs=evidence,
            attributes=payload.get("attributes", {}),
        )
    if payload["contract_version"] == "change-notice.v1":
        return ChangeNotice(
            notice_id=payload["notice_id"],
            scope=scope,
            notice_type=payload["notice_type"],
            status=payload["status"],
            title_key=payload["title_key"],
            submitted_by=payload["submitted_by"],
            audit=audit,
            detail_key=payload.get("detail_key"),
            notice_date=date.fromisoformat(payload["notice_date"]) if payload.get("notice_date") else None,
            schedule_refs=tuple(payload.get("schedule_refs", [])),
            cost_refs=tuple(payload.get("cost_refs", [])),
            dependency_refs=tuple(payload.get("dependency_refs", [])),
            evidence_refs=evidence,
            approval_required=payload.get("approval_required", True),
            attributes=payload.get("attributes", {}),
        )



    if payload["contract_version"] == "change-case.v1":
        return ChangeCase(
            change_id=payload["change_id"],
            scope=scope,
            change_type=payload["change_type"],
            status=payload["status"],
            title_key=payload["title_key"],
            initiated_by=payload["initiated_by"],
            audit=audit,
            detail_key=payload.get("detail_key"),
            originating_notice_id=payload.get("originating_notice_id"),
            schedule_refs=tuple(payload.get("schedule_refs", [])),
            cost_refs=tuple(payload.get("cost_refs", [])),
            dependency_refs=tuple(payload.get("dependency_refs", [])),
            impact_link_ids=tuple(payload.get("impact_link_ids", [])),
            implementation_activity_ids=tuple(payload.get("implementation_activity_ids", [])),
            approval_required=payload.get("approval_required", True),
            approved_by=payload.get("approved_by"),
            approved_at=datetime.fromisoformat(payload["approved_at"]) if payload.get("approved_at") else None,
            evidence_refs=evidence,
        )
    if payload["contract_version"] == "claim-record.v1":
        return ClaimRecord(
            claim_id=payload["claim_id"],
            scope=scope,
            claim_type=payload["claim_type"],
            status=payload["status"],
            title_key=payload["title_key"],
            submitted_by=payload["submitted_by"],
            audit=audit,
            detail_key=payload.get("detail_key"),
            originating_notice_id=payload.get("originating_notice_id"),
            change_id=payload.get("change_id"),
            schedule_refs=tuple(payload.get("schedule_refs", [])),
            cost_refs=tuple(payload.get("cost_refs", [])),
            impact_link_ids=tuple(payload.get("impact_link_ids", [])),
            entitlement_reference=payload.get("entitlement_reference"),
            quantum_reference=payload.get("quantum_reference"),
            decision_reference=payload.get("decision_reference"),
            approval_required=payload.get("approval_required", True),
            decided_by=payload.get("decided_by"),
            decided_at=datetime.fromisoformat(payload["decided_at"]) if payload.get("decided_at") else None,
            evidence_refs=evidence,
        )
    if payload["contract_version"] == "field-inspection.v1":
        checklist = tuple(
            FieldInspectionItem(
                item_id=item["item_id"],
                criterion_key=item["criterion_key"],
                result=item["result"],
                comment_key=item.get("comment_key"),
            )
            for item in payload.get("checklist", [])
        )
        return FieldInspection(
            inspection_id=payload["inspection_id"],
            scope=scope,
            inspection_type_key=payload["inspection_type_key"],
            subject_type=payload["subject_type"],
            subject_id=payload["subject_id"],
            inspection_date=date.fromisoformat(payload["inspection_date"]),
            inspector_id=payload["inspector_id"],
            status=payload["status"],
            result=payload["result"],
            checklist=checklist,
            audit=audit,
            location_key=payload.get("location_key"),
            evidence_refs=evidence,
        )
    if payload["contract_version"] == "quality-record.v1":
        return QualityRecord(
            record_id=payload["record_id"],
            scope=scope,
            category_key=payload["category_key"],
            severity=payload["severity"],
            status=payload["status"],
            title_key=payload["title_key"],
            reported_by=payload["reported_by"],
            audit=audit,
            detail_key=payload.get("detail_key"),
            location_key=payload.get("location_key"),
            activity_ids=tuple(payload.get("activity_ids", [])),
            inspection_id=payload.get("inspection_id"),
            specification_reference=payload.get("specification_reference"),
            corrective_action_key=payload.get("corrective_action_key"),
            disposition_key=payload.get("disposition_key"),
            evidence_refs=evidence,
        )
    if payload["contract_version"] == "safety-observation.v1":
        return SafetyObservation(
            observation_id=payload["observation_id"],
            scope=scope,
            category_key=payload["category_key"],
            severity=payload["severity"],
            status=payload["status"],
            title_key=payload["title_key"],
            observed_by=payload["observed_by"],
            audit=audit,
            location_key=payload.get("location_key"),
            activity_ids=tuple(payload.get("activity_ids", [])),
            immediate_action_key=payload.get("immediate_action_key"),
            root_cause_key=payload.get("root_cause_key"),
            evidence_refs=evidence,
        )
    if payload["contract_version"] == "punch-item.v1":
        return PunchItem(
            punch_id=payload["punch_id"],
            scope=scope,
            category_key=payload["category_key"],
            priority=payload["priority"],
            status=payload["status"],
            title_key=payload["title_key"],
            reported_by=payload["reported_by"],
            audit=audit,
            location_key=payload.get("location_key"),
            activity_ids=tuple(payload.get("activity_ids", [])),
            responsible_party_id=payload.get("responsible_party_id"),
            due_date=date.fromisoformat(payload["due_date"]) if payload.get("due_date") else None,
            verification_by=payload.get("verification_by"),
            closeout_code_key=payload.get("closeout_code_key"),
            evidence_refs=evidence,
        )
    if payload["contract_version"] == "field-timecard.v1":
        allocations = tuple(
            FieldActivityAllocation(
                activity_id=item["activity_id"],
                quantity=Decimal(str(item["quantity"])),
                unit=item["unit"],
            )
            for item in payload.get("activity_allocations", [])
        )
        return FieldTimecard(
            timecard_id=payload["timecard_id"],
            scope=scope,
            person_id=payload["person_id"],
            log_date=date.fromisoformat(payload["log_date"]),
            workplace_key=payload["workplace_key"],
            attendance_status=payload["attendance_status"],
            audit=audit,
            start_at=datetime.fromisoformat(payload["start_at"]) if payload.get("start_at") else None,
            end_at=datetime.fromisoformat(payload["end_at"]) if payload.get("end_at") else None,
            activity_allocations=allocations,
            evidence_refs=evidence,
        )
    if payload["contract_version"] == "equipment-status-report.v1":
        allocations = tuple(
            FieldActivityAllocation(
                activity_id=item["activity_id"],
                quantity=Decimal(str(item["quantity"])),
                unit=item["unit"],
            )
            for item in payload.get("activity_allocations", [])
        )
        return EquipmentStatusReport(
            report_id=payload["report_id"],
            scope=scope,
            equipment_id=payload["equipment_id"],
            report_date=date.fromisoformat(payload["report_date"]),
            workplace_key=payload["workplace_key"],
            status=payload["status"],
            reported_by=payload["reported_by"],
            audit=audit,
            breakdown_cause_key=payload.get("breakdown_cause_key"),
            activity_allocations=allocations,
            meter_hours=Decimal(str(payload["meter_hours"])) if payload.get("meter_hours") is not None else None,
            evidence_refs=evidence,
        )
    if payload["contract_version"] == "procurement-rfq.v1":
        items = tuple(
            ProcurementRFQItem(
                item_id=item["item_id"],
                description_key=item["description_key"],
                quantity=Decimal(str(item["quantity"])),
                unit=item["unit"],
                activity_ids=tuple(item.get("activity_ids", [])),
                attributes=item.get("attributes", {}),
            )
            for item in payload["items"]
        )
        return ProcurementRFQ(
            rfq_id=payload["rfq_id"],
            scope=scope,
            status=payload["status"],
            title_key=payload["title_key"],
            requested_by=payload["requested_by"],
            items=items,
            supplier_ids=tuple(payload.get("supplier_ids", [])),
            audit=audit,
            due_at=datetime.fromisoformat(payload["due_at"]) if payload.get("due_at") else None,
            attributes=payload.get("attributes", {}),
        )
    raise ValueError(f"Unsupported contract version: {payload['contract_version']}")
