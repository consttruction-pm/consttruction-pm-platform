from __future__ import annotations

import json

from construction_pm.control_intelligence.quality_audit import build_schedule_quality_audit


def snapshot_payload() -> str:
    return json.dumps({
        "snapshot_id": "snapshot-import-audit",
        "tenant_id": "tenant-1",
        "project_id": "project-1",
        "project_revision": 9,
        "mode": "DATE_BASED",
        "activities": [
            {"id": "A-1", "duration": 2, "activity_type": "Task Dependent"},
            {"id": "A-2", "duration": 3, "activity_type": "Task Dependent"},
        ],
        "relationships": [
            {"predecessor_id": "A-1", "successor_id": "A-2", "type": "FS", "lag": 0}
        ],
        "constraints": [],
        "activity_calendar_assignments": [],
        "schedule_options": {},
    }, sort_keys=True, separators=(",", ":"))


def test_import_parse_ledger_reports_preserved_unknown_fields_and_unapplied_batch() -> None:
    report = build_schedule_quality_audit(
        snapshot_payload(),
        audit_context={
            "interchange_import_ledger_configured": True,
            "interchange_import_batches": [
                {
                    "batch_id": "batch-1",
                    "project_revision": 9,
                    "format": "XER_PROJECT",
                    "source_sha256": "a" * 64,
                    "source_byte_count": 1200,
                    "row_count": 2,
                    "mapping_snapshot": [
                        {
                            "mapping_id": "task-code",
                            "source_field": "task_code",
                            "canonical_field": "activity.activity_id",
                            "status": "SUPPORTED",
                        },
                        {
                            "mapping_id": "vendor-cost",
                            "source_field": "vendor_cost",
                            "canonical_field": "activity.vendor_cost",
                            "status": "UNSUPPORTED_PRESERVE",
                        },
                    ],
                    "row_summaries": [
                        {
                            "row_index": 0,
                            "source_fields": ["task_code", "vendor_cost"],
                            "canonical_fields": ["activity.activity_id"],
                            "preserved_extension_fields": ["p6.interchange.vendor_cost"],
                            "warnings": ["PRESERVED_UNSUPPORTED_FIELD:vendor_cost"],
                        },
                        {
                            "row_index": 1,
                            "source_fields": ["task_code", "unknown_field"],
                            "canonical_fields": ["activity.activity_id"],
                            "preserved_extension_fields": ["p6.interchange.unknown_field"],
                            "warnings": ["PRESERVED_UNKNOWN_FIELD:unknown_field"],
                        },
                    ],
                    "imported_by": "user-1",
                    "imported_at": "2026-11-04T20:00:00+00:00",
                    "target_application_status": "PARSED_NOT_APPLIED",
                }
            ],
        },
    )
    rules = [finding["rule_id"] for finding in report["findings"]]
    assert rules.count("INTERCHANGE_UNSUPPORTED_SOURCE_FIELD_PRESERVED") == 1
    assert rules.count("INTERCHANGE_UNKNOWN_SOURCE_FIELD_PRESERVED") == 1
    assert rules.count("INTERCHANGE_BATCH_NOT_APPLIED") == 1
    preserved = next(
        finding for finding in report["findings"]
        if finding["rule_id"] == "INTERCHANGE_UNKNOWN_SOURCE_FIELD_PRESERVED"
    )
    assert preserved["evidence"]["source_field"] == "unknown_field"
    assert preserved["evidence"]["mapping_status"] == "UNKNOWN"
    pending = next(
        finding for finding in report["findings"]
        if finding["rule_id"] == "INTERCHANGE_BATCH_NOT_APPLIED"
    )
    assert pending["evidence"]["target_application_status"] == "PARSED_NOT_APPLIED"
    assert report["coverage"]["import_interchange_loss"] == (
        "partial_source_mapping_audited_target_records_not_applied"
    )
    assert report["status"] == "partial"
    assert report["summary"]["import_batch_count"] == 1
    assert report["summary"]["import_row_count"] == 2
    assert report["summary"]["import_preservation_warning_count"] == 2


def test_import_audit_distinguishes_unconfigured_ledger_from_empty_configured_ledger() -> None:
    unconfigured = build_schedule_quality_audit(snapshot_payload())
    assert unconfigured["coverage"]["import_interchange_loss"] == "not_evaluated_import_ledger_not_configured"

    empty = build_schedule_quality_audit(
        snapshot_payload(),
        audit_context={
            "interchange_import_ledger_configured": True,
            "interchange_import_batches": [],
        },
    )
    assert empty["coverage"]["import_interchange_loss"] == "not_evaluated_no_import_batches"
