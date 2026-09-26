from __future__ import annotations

from decimal import Decimal
from typing import Any

from .models import ChangeNotice, EquipmentStatusReport, FieldDailyLog, FieldIssue, FieldInspection, FieldTimecard, ProcurementRFQ, PunchItem, QualityRecord, Record, SafetyObservation, record_id
from .repository import StoredRecord


def resource_type_for_record(record: Record) -> str:
    if isinstance(record, FieldDailyLog):
        return "daily_log"
    if isinstance(record, FieldIssue):
        return "issue"
    if isinstance(record, ProcurementRFQ):
        return "rfq"
    if isinstance(record, FieldTimecard):
        return "timecard"
    if isinstance(record, EquipmentStatusReport):
        return "equipment_status"
    if isinstance(record, FieldInspection):
        return "inspection"
    if isinstance(record, QualityRecord):
        return "quality_record"
    if isinstance(record, SafetyObservation):
        return "safety_record"
    if isinstance(record, PunchItem):
        return "punch_item"
    if isinstance(record, ChangeNotice):
        if record.notice_type == "variation":
            return "variation"
        if record.notice_type == "claim_notice":
            return "notice"
        return "notice"
    raise TypeError(f"Unsupported P0 resource record: {type(record)!r}")


def resource_family_for_record(record: Record) -> str:
    if isinstance(record, (FieldDailyLog, FieldIssue, FieldTimecard, EquipmentStatusReport, FieldInspection, QualityRecord, SafetyObservation, PunchItem)):
        return "field"
    if isinstance(record, ChangeNotice):
        return "change"
    if isinstance(record, ProcurementRFQ):
        return "procurement"
    raise TypeError(f"Unsupported P0 resource record: {type(record)!r}")


def to_resource_envelope(stored: StoredRecord) -> dict[str, Any]:
    record = stored.record
    record.validate()
    return {
        "contract_version": "1.0",
        "resource_type": resource_type_for_record(record),
        "resource_id": record_id(record),
        "tenant_id": record.scope.tenant_id,
        "project_id": record.scope.project_id,
        "revision": stored.record_revision,
        "payload": _json_safe(record.as_dict()),
    }


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value
