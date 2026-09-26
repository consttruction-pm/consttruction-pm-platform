from datetime import date, datetime, timezone
from decimal import Decimal

from construction_pm.application.authorization import AuthorizationContext, Permission, RoleBasedAuthorizationPolicy
from construction_pm.backend_p0 import (
    AuditMetadata,
    BackendP0API,
    BackendP0ApplicationService,
    BackendScope,
    ChangeNotice,
    EvidenceRef,
    FieldDailyLog,
    FieldDailyLogEntry,
    FieldIssue,
    ProcurementRFQ,
    ProcurementRFQItem,
    SQLiteBackendP0Repository,
    SQLiteTransactionManager,
    resource_family_for_record,
    resource_type_for_record,
)
from construction_pm.backend_p0.idempotency import SQLiteIdempotencyStore


def _auth() -> AuthorizationContext:
    return AuthorizationContext("tenant-1", "project-1", "user-1", frozenset({"planner"}))


def _policy() -> RoleBasedAuthorizationPolicy:
    return RoleBasedAuthorizationPolicy({
        "planner": frozenset({Permission.PROJECT_READ, Permission.PROJECT_WRITE}),
    })


def _shared():
    scope = BackendScope("tenant-1", "project-1", 12)
    audit = AuditMetadata(
        "user-1",
        datetime(2026, 9, 27, 8, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 27, 8, 0, tzinfo=timezone.utc),
    )
    evidence = EvidenceRef("doc-1", "photo", "page/1", 12)
    return scope, audit, evidence


def _stack():
    import sqlite3
    connection = sqlite3.connect(":memory:")
    repo = SQLiteBackendP0Repository(connection)
    service = BackendP0ApplicationService(
        repo,
        SQLiteTransactionManager(connection),
        _policy(),
        SQLiteIdempotencyStore(connection),
    )
    return connection, BackendP0API(service)


def test_resource_type_mapping_is_deterministic():
    scope, audit, evidence = _shared()
    daily = FieldDailyLog(
        "DL-1", scope, date(2026, 9, 27), "zone-a", "submitted",
        (FieldDailyLogEntry("E-1", "labor", "crew.present", quantity=Decimal("12.50"), unit="hour"),),
        audit, (evidence,),
    )
    issue = FieldIssue(
        "I-1", scope, "quality", "high", "open", "issue.title", "user-1", audit,
        evidence_refs=(evidence,),
    )
    change = ChangeNotice(
        "CN-1", scope, "variation", "submitted", "change.title", "user-1", audit,
        evidence_refs=(evidence,),
    )
    rfq = ProcurementRFQ(
        "RFQ-1", scope, "issued", "rfq.title", "user-1",
        (ProcurementRFQItem("IT-1", "concrete.m3", Decimal("25.1250"), "m3"),),
        ("S-1",), audit,
    )

    assert (resource_family_for_record(daily), resource_type_for_record(daily)) == ("field", "daily_log")
    assert (resource_family_for_record(issue), resource_type_for_record(issue)) == ("field", "issue")
    assert (resource_family_for_record(change), resource_type_for_record(change)) == ("change", "variation")
    claim_notice = ChangeNotice(
        "CN-2", scope, "claim_notice", "submitted", "claim.title", "user-1", audit,
        evidence_refs=(evidence,),
    )
    assert (resource_family_for_record(claim_notice), resource_type_for_record(claim_notice)) == ("change", "notice")
    assert (resource_family_for_record(rfq), resource_type_for_record(rfq)) == ("procurement", "rfq")


def test_resource_api_envelope_keeps_revision_and_exact_decimal_strings():
    connection, api = _stack()
    scope, audit, evidence = _shared()
    record = FieldDailyLog(
        "DL-1", scope, date(2026, 9, 27), "zone-a", "submitted",
        (FieldDailyLogEntry("E-1", "labor", "crew.present", quantity=Decimal("12.5000"), unit="hour"),),
        audit, (evidence,),
    )
    result = api.save_resource(record, auth_context=_auth(), idempotency_key="resource-1")
    assert result["contract_version"] == "1.0"
    assert result["resource_type"] == "daily_log"
    assert result["resource_id"] == "DL-1"
    assert result["tenant_id"] == "tenant-1"
    assert result["project_id"] == "project-1"
    assert result["revision"] == 1
    assert result["payload"]["entries"][0]["quantity"] == Decimal("12.5000")
    connection.close()


def test_existing_api_save_behavior_remains_available():
    connection, api = _stack()
    scope, audit, evidence = _shared()
    record = FieldIssue(
        "I-1", scope, "quality", "medium", "open", "issue.title", "user-1", audit,
        evidence_refs=(evidence,),
    )
    result = api.save(record, auth_context=_auth(), idempotency_key="legacy-save")
    assert result["contract_version"] == "field-issue.v1"
    assert result["record_revision"] == 1
    connection.close()
