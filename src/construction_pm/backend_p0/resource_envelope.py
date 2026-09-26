from __future__ import annotations

from typing import Any

from .models import ChangeNotice, FieldDailyLog, FieldIssue, ProcurementRFQ, Record, record_id
from .repository import StoredRecord


def resource_type_for_record(record: Record) -> str:
    if isinstance(record, FieldDailyLog):
        return "daily_log"
    if isinstance(record, FieldIssue):
        return "issue"
    if isinstance(record, ProcurementRFQ):
        return "rfq"
    if isinstance(record, ChangeNotice):
        if record.notice_type == "variation":
            return "variation"
        if record.notice_type == "claim_notice":
            return "claim"
        return "notice"
    raise TypeError(f"Unsupported P0 resource record: {type(record)!r}")


def resource_family_for_record(record: Record) -> str:
    if isinstance(record, (FieldDailyLog, FieldIssue)):
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
        "payload": record.as_dict(),
    }
