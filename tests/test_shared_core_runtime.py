from __future__ import annotations

from datetime import date, datetime, timezone
import json
import sqlite3
from decimal import Decimal

from construction_pm.application.authorization import AuthorizationContext, default_project_policy
from construction_pm.backend_p0.models import BackendScope
from construction_pm.schedule_calculation_context_repository import (
    SQLiteCalculationContextRepository,
    build_persisted_context,
)
from construction_pm.schedule_input_snapshot_repository import (
    SQLiteScheduleInputSnapshotRepository,
    build_snapshot,
)
from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.authoritative_schedule import (
    AuthoritativeScheduleInput,
    AuthoritativeScheduleMode,
)
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.calendar_context import CalendarReference, CalendarResolverRegistry
from construction_pm.scheduling.calculation_context import CalculationContext
from construction_pm.shared_core_runtime import (
    CORE_RUNTIME_CONTRACT_VERSION,
    SCHEDULE_QUERY_OPERATION,
    build_shared_core_runtime,
)


def _runtime():
    connection = sqlite3.connect(":memory:")
    snapshot_repository = SQLiteScheduleInputSnapshotRepository(connection)
    context_repository = SQLiteCalculationContextRepository(connection)
    now = datetime(2026, 9, 30, tzinfo=timezone.utc)
    source = AuthoritativeScheduleInput(
        snapshot_id="S-CORE-RUNTIME",
        tenant_id="T-1",
        project_id="P-1",
        project_revision=9,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=CalendarReference("CAL-1", "1"),
        activities=(Activity("A", 2),),
        relationships=(),
        activity_calendar_assignments=(),
        project_start=date(2026, 9, 21),
    )
    context = CalculationContext(
        project_id="P-1",
        project_version=9,
        calendar_id="CAL-1",
        calendar_version="1",
        rules_version="rules-1",
        engine_version="engine-1",
        timezone="UTC",
        calculation_timestamp=now.isoformat(),
        input_snapshot_id="S-CORE-RUNTIME",
        tenant_id="T-1",
        actor_id="u1",
    )
    snapshot_repository.save(build_snapshot(source, context, now))
    context_repository.save(build_persisted_context(BackendScope("T-1", "P-1", 9), context))
    registry = CalendarResolverRegistry(
        day_resolvers={"CAL-1@1": WorkingTimeResolver(WorkingCalendar())}
    )
    runtime = build_shared_core_runtime(
        snapshot_repository=snapshot_repository,
        calendar_registry_factory=lambda: registry,
        calculation_context_repository=context_repository,
        authorization_policy=default_project_policy(),
    )
    auth = AuthorizationContext("T-1", "P-1", "u1", frozenset({"project_admin"}))
    return runtime, auth, connection


def _envelope(**overrides):
    payload = {
        "contract_version": "schedule-query.v1",
        "query_id": "Q-CORE-RUNTIME",
        "scope": {
            "tenant_id": "T-1",
            "project_id": "P-1",
            "project_revision": 9,
        },
        "requested_by": "u1",
        "query_text": "show authoritative schedule facts",
        "kind": "fact",
        "language": "en",
        "constraints": {"snapshot_id": "S-CORE-RUNTIME"},
    }
    payload.update(overrides)
    return {
        "contract_version": CORE_RUNTIME_CONTRACT_VERSION,
        "operation": SCHEDULE_QUERY_OPERATION,
        "payload": payload,
    }


def test_shared_core_runtime_dispatches_authoritative_schedule_without_http():
    runtime, auth, connection = _runtime()
    try:
        response = json.loads(runtime.dispatch_json(json.dumps(_envelope()), auth_context=auth, expected_project_revision=9))
        assert response["contract_version"] == CORE_RUNTIME_CONTRACT_VERSION
        assert response["operation"] == SCHEDULE_QUERY_OPERATION
        result = response["result"]
        assert result["contract_version"] == "schedule-query-result.v1"
        assert result["scope"] == {
            "tenant_id": "T-1",
            "project_id": "P-1",
            "project_revision": 9,
        }
        assert result["data"]["project_finish"] == "2026-09-22"
        assert result["data"]["calculation_run_identity"]
        assert result["data"]["activities"]["A"]["start"] == "2026-09-21"
    finally:
        connection.close()


def test_shared_core_runtime_rejects_bad_contract_and_unknown_operation():
    runtime, auth, connection = _runtime()
    try:
        bad_contract = _envelope()
        bad_contract["contract_version"] = "cubi.shared-core-runtime.v0"
        response = json.loads(runtime.dispatch_json(json.dumps(bad_contract), auth_context=auth, expected_project_revision=9))
        assert response["result"]["error"]["code"] == "UNSUPPORTED_CORE_RUNTIME_CONTRACT"

        unknown_operation = _envelope()
        unknown_operation["operation"] = "schedule.recalculate.client"
        response = json.loads(runtime.dispatch_json(json.dumps(unknown_operation), auth_context=auth, expected_project_revision=9))
        assert response["result"]["error"]["code"] == "UNSUPPORTED_CORE_RUNTIME_OPERATION"

        response = json.loads(runtime.dispatch_json("{invalid-json", auth_context=auth, expected_project_revision=9))
        assert response["result"]["error"]["code"] == "CORE_RUNTIME_REQUEST_INVALID"
    finally:
        connection.close()


def test_shared_core_runtime_binds_request_actor_and_scope_to_host_identity():
    runtime, auth, connection = _runtime()
    try:
        mismatch = _envelope(requested_by="another-user")
        response = json.loads(runtime.dispatch_json(json.dumps(mismatch), auth_context=auth, expected_project_revision=9))
        assert response["result"]["error"]["code"] == "REQUESTED_BY_MISMATCH"

        stale_revision = _envelope(
            scope={"tenant_id": "T-1", "project_id": "P-1", "project_revision": 8}
        )
        response = json.loads(runtime.dispatch_json(
            json.dumps(stale_revision), auth_context=auth, expected_project_revision=9
        ))
        assert response["result"]["error"]["code"] == "STALE_PROJECT_REVISION"

        cross_scope = _envelope(
            scope={"tenant_id": "OTHER", "project_id": "P-1", "project_revision": 9}
        )
        response = json.loads(runtime.dispatch_json(json.dumps(cross_scope), auth_context=auth, expected_project_revision=9))
        assert response["result"]["error"]["code"] == "CROSS_SCOPE_ACCESS"

        denied_auth = AuthorizationContext("T-1", "P-1", "u1", frozenset({"unprivileged"}))
        response = json.loads(runtime.dispatch_json(json.dumps(_envelope()), auth_context=denied_auth, expected_project_revision=9))
        assert response["result"]["error"]["code"] == "FORBIDDEN"
    finally:
        connection.close()


def test_shared_core_runtime_rejects_duplicate_json_keys_and_non_finite_constants():
    runtime, auth, connection = _runtime()
    try:
        duplicate = (
            '{"contract_version":"cubi.shared-core-runtime.v1",'
            '"contract_version":"cubi.shared-core-runtime.v1",'
            '"operation":"schedule.query","payload":{}}'
        )
        response = json.loads(
            runtime.dispatch_json(duplicate, auth_context=auth, expected_project_revision=9)
        )
        assert response["result"]["error"]["code"] == "CORE_RUNTIME_REQUEST_INVALID"

        non_finite = (
            '{"contract_version":"cubi.shared-core-runtime.v1",'
            '"operation":"schedule.query","payload":{"bad":NaN}}'
        )
        response = json.loads(
            runtime.dispatch_json(non_finite, auth_context=auth, expected_project_revision=9)
        )
        assert response["result"]["error"]["code"] == "CORE_RUNTIME_REQUEST_INVALID"
    finally:
        connection.close()


def test_shared_core_runtime_registered_operation_is_versioned_scoped_and_permission_checked():
    from construction_pm.application.authorization import Permission
    from construction_pm.shared_core_runtime import SharedCoreOperation, SharedCoreRuntime

    base, auth, connection = _runtime()
    try:
        operation = SharedCoreOperation(
            contract_version="p6-test-read.v1",
            permission=Permission.PROJECT_READ,
            required_fields=frozenset({"value"}),
            allowed_fields=frozenset({"value"}),
            handler=lambda payload, actor, revision: {
                "value": payload["value"],
                "host_user": actor.user_id,
                "project_revision": revision,
            },
        )
        runtime = SharedCoreRuntime(
            schedule_query_api=base.schedule_query_api,
            authorization_policy=base.authorization_policy,
            operations={"project.test_read": operation},
        )
        envelope = {
            "contract_version": CORE_RUNTIME_CONTRACT_VERSION,
            "operation": "project.test_read",
            "payload": {
                "contract_version": "p6-test-read.v1",
                "scope": {
                    "tenant_id": "T-1",
                    "project_id": "P-1",
                    "project_revision": 9,
                },
                "value": "ok",
            },
        }
        response = json.loads(
            runtime.dispatch_json(json.dumps(envelope), auth_context=auth, expected_project_revision=9)
        )
        assert response["operation"] == "project.test_read"
        assert response["result"] == {
            "value": "ok",
            "host_user": "u1",
            "project_revision": 9,
        }

        bad_version = json.loads(json.dumps(envelope))
        bad_version["payload"]["contract_version"] = "p6-test-read.v0"
        response = json.loads(
            runtime.dispatch_json(json.dumps(bad_version), auth_context=auth, expected_project_revision=9)
        )
        assert response["result"]["error"]["code"] == "UNSUPPORTED_OPERATION_CONTRACT"

        unknown_field = json.loads(json.dumps(envelope))
        unknown_field["payload"]["is_admin"] = True
        response = json.loads(
            runtime.dispatch_json(json.dumps(unknown_field), auth_context=auth, expected_project_revision=9)
        )
        assert response["result"]["error"]["code"] == "CORE_RUNTIME_REQUEST_INVALID"

        cross_scope = json.loads(json.dumps(envelope))
        cross_scope["payload"]["scope"]["tenant_id"] = "OTHER"
        response = json.loads(
            runtime.dispatch_json(json.dumps(cross_scope), auth_context=auth, expected_project_revision=9)
        )
        assert response["result"]["error"]["code"] == "CROSS_SCOPE_ACCESS"

        denied = AuthorizationContext("T-1", "P-1", "u1", frozenset({"unprivileged"}))
        response = json.loads(
            runtime.dispatch_json(json.dumps(envelope), auth_context=denied, expected_project_revision=9)
        )
        assert response["result"]["error"]["code"] == "FORBIDDEN"

        assert any(
            item["operation"] == "project.test_read"
            and item["contract_version"] == "p6-test-read.v1"
            for item in runtime.supported_operations
        )
    finally:
        connection.close()


def test_shared_core_runtime_encodes_decimal_response_without_float_rounding():
    from construction_pm.application.authorization import Permission
    from construction_pm.shared_core_runtime import SharedCoreOperation, SharedCoreRuntime

    base, auth, connection = _runtime()
    try:
        operation = SharedCoreOperation(
            contract_version="p6-financial-read.v1",
            permission=Permission.PROJECT_READ,
            required_fields=frozenset({"amount"}),
            allowed_fields=frozenset({"amount"}),
            handler=lambda payload, actor, revision: {
                "amount": Decimal(payload["amount"]),
            },
        )
        runtime = SharedCoreRuntime(
            schedule_query_api=base.schedule_query_api,
            authorization_policy=base.authorization_policy,
            operations={"finance.amount": operation},
        )
        envelope = {
            "contract_version": CORE_RUNTIME_CONTRACT_VERSION,
            "operation": "finance.amount",
            "payload": {
                "contract_version": "p6-financial-read.v1",
                "scope": {
                    "tenant_id": "T-1",
                    "project_id": "P-1",
                    "project_revision": 9,
                },
                "amount": "123456789.1200300",
            },
        }
        response = json.loads(
            runtime.dispatch_json(json.dumps(envelope), auth_context=auth, expected_project_revision=9)
        )
        assert response["result"]["amount"] == "123456789.1200300"
    finally:
        connection.close()
