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
                    payload["status"],
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
                payload["status"],
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
