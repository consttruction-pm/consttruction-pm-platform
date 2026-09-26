from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

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
)
from construction_pm.backend_p0.errors import BackendApplicationError, OptimisticLockError
from construction_pm.backend_p0.models import record_id, resource_type
from construction_pm.backend_p0.idempotency import SQLiteIdempotencyStore


def auth(roles=frozenset({"planner"})) -> AuthorizationContext:
    return AuthorizationContext("tenant-1", "project-1", "user-1", roles)


def policy() -> RoleBasedAuthorizationPolicy:
    return RoleBasedAuthorizationPolicy({
        "planner": frozenset({Permission.PROJECT_READ, Permission.PROJECT_WRITE}),
        "viewer": frozenset({Permission.PROJECT_READ}),
    })


def common(scope_rev=11):
    return (
        BackendScope("tenant-1", "project-1", scope_rev),
        AuditMetadata(
            created_by="user-1",
            created_at=datetime(2026, 9, 26, 8, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 9, 26, 8, 5, tzinfo=timezone.utc),
            correlation_id="c-1",
            source="chatgpt-test",
        ),
        EvidenceRef("doc-1", "photo", "page/1", 1),
    )


def all_records():
    scope, audit, evidence = common()
    return [
        FieldDailyLog(
            "DL-1", scope, date(2026, 9, 25), "zone-a", "submitted",
            (FieldDailyLogEntry("E-1", "labor", "crew.present", ("A-1",), ("R-1",), Decimal("12.50"), "hour"),),
            audit, (evidence,),
        ),
        FieldIssue(
            "I-1", scope, "quality", "high", "open", "issue.title", "user-1", audit,
            detail_key="issue.detail", location_key="zone-a", activity_ids=("A-1",), evidence_refs=(evidence,),
        ),
        ChangeNotice(
            "CN-1", scope, "variation", "submitted", "change.title", "user-1", audit,
            detail_key="change.detail", notice_date=date(2026, 9, 25), schedule_refs=("A-1",), cost_refs=("C-1",),
            dependency_refs=("D-1",), evidence_refs=(evidence,), approval_required=True,
        ),
        ProcurementRFQ(
            "RFQ-1", scope, "issued", "rfq.title", "user-1",
            (ProcurementRFQItem("IT-1", "concrete.m3", Decimal("25.1250"), "m3", ("A-1",)),),
            ("S-1", "S-2"), audit,
            due_at=datetime(2026, 9, 30, 12, 30, tzinfo=timezone.utc),
        ),
    ]


def make_stack():
    connection = sqlite3.connect(":memory:")
    repo = SQLiteBackendP0Repository(connection)
    tm = SQLiteTransactionManager(connection)
    idem = SQLiteIdempotencyStore(connection)
    service = BackendP0ApplicationService(repo, tm, policy(), idem)
    api = BackendP0API(service)
    return connection, repo, service, api


def test_all_four_records_round_trip_and_revision():
    connection, repo, service, _ = make_stack()
    try:
        for record in all_records():
            stored = service.save(record, auth_context=auth(), idempotency_key=f"create-{type(record).__name__}")
            assert stored.record == record
            assert stored.record_revision == 1
            read_back = repo.get(record.scope.tenant_id, record.scope.project_id, resource_type(record), record_id(record))
            assert read_back == stored
    finally:
        connection.close()


def test_persistence_is_atomic_across_multiple_records():
    connection, repo, service, _ = make_stack()
    records = all_records()
    with pytest.raises(RuntimeError):
        with service.transaction_manager.transaction():
            repo.save(records[0])
            repo.save(records[1])
            raise RuntimeError("abort")
    assert repo.get("tenant-1", "project-1", "field_daily_log", "DL-1") is None
    assert repo.get("tenant-1", "project-1", "field_issue", "I-1") is None
    connection.close()


def test_stale_revision_is_rejected():
    connection, repo, _, _ = make_stack()
    record = all_records()[0]
    with SQLiteTransactionManager(connection).transaction():
        stored = repo.save(record)
    updated = FieldDailyLog(
        record.log_id, record.scope, record.log_date, record.location_key, "approved",
        record.entries, record.audit, record.evidence_refs,
    )
    with pytest.raises(OptimisticLockError):
        with SQLiteTransactionManager(connection).transaction():
            repo.save(updated, expected_revision=2)
    connection.close()


def test_idempotency_replays_without_reexecution():
    connection, _, service, _ = make_stack()
    calls = {"n": 0}
    record = all_records()[0]
    original = service.repository.save

    def counted(*args, **kwargs):
        calls["n"] += 1
        return original(*args, **kwargs)

    service.repository.save = counted  # type: ignore[attr-defined]
    first = service.save(record, auth_context=auth(), idempotency_key="same-key")
    second = service.save(record, auth_context=auth(), idempotency_key="same-key")
    changed = FieldDailyLog(record.log_id, record.scope, record.log_date, record.location_key, "approved", record.entries, record.audit, record.evidence_refs)
    updated = service.save(changed, auth_context=auth(), expected_revision=1, idempotency_key="update-key")
    replay_after_update = service.save(record, auth_context=auth(), idempotency_key="same-key")
    assert first.record_revision == second.record_revision == 1
    assert updated.record_revision == 2
    assert replay_after_update.record_revision == 1
    assert replay_after_update.record == record
    assert calls["n"] == 2
    connection.close()


def test_idempotency_key_reuse_is_rejected():
    connection, _, service, _ = make_stack()
    record = all_records()[0]
    service.save(record, auth_context=auth(), idempotency_key="reuse")
    changed = FieldDailyLog(record.log_id, record.scope, record.log_date, record.location_key, "approved", record.entries, record.audit, record.evidence_refs)
    with pytest.raises(BackendApplicationError) as exc:
        service.save(changed, auth_context=auth(), idempotency_key="reuse")
    assert exc.value.code == "IDEMPOTENCY_KEY_REUSE"
    connection.close()


def test_read_requires_project_read_permission():
    connection, _, service, _ = make_stack()
    record = all_records()[0]
    service.save(record, auth_context=auth(), idempotency_key="read-seed")
    assert service.get(record, auth_context=auth(frozenset({"viewer"}))) is not None
    with pytest.raises(BackendApplicationError) as exc:
        service.get(record, auth_context=auth(frozenset({"unknown-role"})))
    assert exc.value.code == "FORBIDDEN"
    connection.close()


def test_cross_tenant_and_viewer_write_are_blocked():
    connection, _, service, _ = make_stack()
    record = all_records()[0]
    with pytest.raises(BackendApplicationError) as exc:
        service.save(record, auth_context=AuthorizationContext("tenant-2", "project-1", "user-1", frozenset({"planner"})), idempotency_key="x")
    assert exc.value.code == "CROSS_SCOPE_MUTATION"
    with pytest.raises(BackendApplicationError) as exc:
        service.save(record, auth_context=AuthorizationContext("tenant-1", "project-1", "user-1", frozenset({"viewer"})), idempotency_key="y")
    assert exc.value.code == "FORBIDDEN"
    connection.close()


def test_required_evidence_and_revision_boundaries():
    scope, audit, _ = common()
    with pytest.raises(ValueError, match="requires at least one evidence"):
        FieldIssue("I-2", scope, "quality", "low", "open", "title", "user", audit).validate()
    with pytest.raises(ValueError, match="safe integer"):
        BackendScope("tenant-1", "project-1", 9_007_199_254_740_992).validate()
    with pytest.raises(ValueError, match="integer"):
        BackendScope("tenant-1", "project-1", True).validate()
    with pytest.raises(ValueError, match="greater than zero"):
        ProcurementRFQItem("x", "y", Decimal("0"), "m3").validate()


def test_concurrent_same_idempotency_key_executes_mutation_once(tmp_path: Path):
    db = tmp_path / "backend-p0.sqlite"
    barrier = threading.Barrier(2)
    calls = {"n": 0}
    call_lock = threading.Lock()
    services = []
    conns = []
    for _ in range(2):
        conn = sqlite3.connect(db, timeout=5, check_same_thread=False)
        repo = SQLiteBackendP0Repository(conn)
        tm = SQLiteTransactionManager(conn)
        idem = SQLiteIdempotencyStore(conn)
        services.append(BackendP0ApplicationService(repo, tm, policy(), idem))
        conns.append(conn)

    record = all_records()[0]
    def run(service_index: int):
        barrier.wait()
        return services[service_index].save(record, auth_context=auth(), idempotency_key="concurrent")

    # Wrap each repository save without introducing a second transaction boundary.
    for service in services:
        original = service.repository.save
        def counted(record_arg, expected_revision=None, _original=original):
            with call_lock:
                calls["n"] += 1
            return _original(record_arg, expected_revision=expected_revision)
        service.repository.save = counted  # type: ignore[attr-defined]

    results = [None, None]
    errors = []
    def worker(i):
        try:
            results[i] = run(i)
        except Exception as exc:  # pragma: no cover - diagnostic path
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(2)]
    for thread in threads: thread.start()
    for thread in threads: thread.join()
    try:
        assert errors == []
        assert [result.record_revision for result in results] == [1, 1]
        assert calls["n"] == 1
    finally:
        for conn in conns: conn.close()


def test_api_returns_machine_readable_revision():
    connection, _, _, api = make_stack()
    result = api.save(all_records()[0], auth_context=auth(), idempotency_key="api-key")
    assert result["contract_version"] == "field-daily-log.v1"
    assert result["record_revision"] == 1
    assert result["operation"] == "save"
    json_payload = json.dumps(result, ensure_ascii=False)
    assert '"quantity": "12.50"' in json_payload
    connection.close()


def test_failed_idempotent_mutation_rolls_back_both_record_and_key():
    connection, repo, _, _ = make_stack()
    record = all_records()[0]
    original = repo.save
    try:
        def fail(*args, **kwargs):
            raise RuntimeError("simulated persistence failure")
        repo.save = fail  # type: ignore[method-assign]
        service = BackendP0ApplicationService(
            repo, SQLiteTransactionManager(connection), policy(), SQLiteIdempotencyStore(connection)
        )
        with pytest.raises(RuntimeError, match="simulated persistence failure"):
            service.save(record, auth_context=auth(), idempotency_key="rollback")
        assert repo.get("tenant-1", "project-1", "field_daily_log", "DL-1") is None
        assert connection.execute(
            "SELECT 1 FROM backend_p0_idempotency WHERE idempotency_key='rollback'"
        ).fetchone() is None
    finally:
        repo.save = original  # type: ignore[method-assign]
        connection.close()


def test_tenant_and_project_are_part_of_persistence_key():
    connection = sqlite3.connect(":memory:")
    repo = SQLiteBackendP0Repository(connection)
    scope, audit, evidence = common()
    record = FieldIssue("I-9", scope, "quality", "low", "open", "title", "user-1", audit, evidence_refs=(evidence,))
    with SQLiteTransactionManager(connection).transaction():
        repo.save(record)
    assert repo.get("tenant-2", "project-1", "field_issue", "I-9") is None
    assert repo.get("tenant-1", "project-2", "field_issue", "I-9") is None
    assert repo.get("tenant-1", "project-1", "field_issue", "I-9") is not None
    connection.close()


def test_contract_dtos_are_closed_and_versioned():
    for record in all_records():
        dto = record.as_dict()
        assert dto["contract_version"] == record.contract_version
        assert dto["scope"]["tenant_id"]
        assert dto["scope"]["project_id"]
        assert 0 <= dto["scope"]["project_revision"] <= 9_007_199_254_740_991
        assert set(dto) <= {
            "contract_version", "log_id", "issue_id", "notice_id", "rfq_id", "scope", "log_date",
            "location_key", "status", "entries", "audit", "evidence_refs", "category", "severity", "title_key",
            "detail_key", "reported_by", "activity_ids", "attributes", "notice_type", "submitted_by", "notice_date",
            "schedule_refs", "cost_refs", "dependency_refs", "approval_required", "requested_by", "due_at", "items",
            "supplier_ids",
        }
