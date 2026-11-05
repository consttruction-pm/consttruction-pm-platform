from decimal import Decimal
import sqlite3

import pytest

from construction_pm.application.authorization import AuthorizationContext, AuthorizationError, default_project_policy
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.p6_activity_step_api import P6_ACTIVITY_STEP_API_VERSION, P6ActivityStepAPI
from construction_pm.p6_activity_step_repository import P6ActivityStep, P6ActivityStepApplicationService, SQLiteP6ActivityStepRepository


def auth(tenant="t1", project="p1", roles=("planner",)):
    return AuthorizationContext(tenant, project, "u1", frozenset(roles))


def api(connection):
    repository = SQLiteP6ActivityStepRepository(connection)
    service = P6ActivityStepApplicationService(repository, SQLiteTransactionManager(connection))
    return P6ActivityStepAPI(service, default_project_policy()), service


def step(scope, step_id, sequence, activity_id="A-100"):
    return P6ActivityStep(
        scope=scope,
        step_id=step_id,
        activity_id=activity_id,
        sequence=sequence,
        description=f"Step {sequence}",
        weight=Decimal("12.50"),
        start_date="2026-11-01",
        finish_date="2026-11-02",
        udf_values=(("crew", "C-01"),),
    )


def test_activity_step_api_lists_scoped_records_in_deterministic_sequence_and_preserves_decimal_and_udf_values():
    service_api, service = api(sqlite3.connect(":memory:"))
    scope = BackendScope("t1", "p1", 3)
    service.save(step(scope, "STEP-02", 2))
    service.save(step(scope, "STEP-01", 1))

    records = service_api.list(scope, activity_id="A-100", auth_context=auth())

    assert len(records) == 2
    assert records[0]["contract_version"] == P6_ACTIVITY_STEP_API_VERSION
    assert records[0]["scope"] == {"tenant_id": "t1", "project_id": "p1", "project_revision": 3}
    assert records[0]["step"] == {
        "step_id": "STEP-01",
        "activity_id": "A-100",
        "sequence": 1,
        "description": "Step 1",
        "weight": "12.50",
        "start_date": "2026-11-01",
        "finish_date": "2026-11-02",
        "udf_values": [{"field_id": "crew", "value": "C-01"}],
    }


def test_activity_step_api_get_returns_none_for_unknown_step():
    service_api, _ = api(sqlite3.connect(":memory:"))
    assert service_api.get(BackendScope("t1", "p1", 1), "MISSING", auth_context=auth()) is None


def test_activity_step_api_rejects_cross_tenant_project_and_read_permission_mismatch():
    service_api, service = api(sqlite3.connect(":memory:"))
    scope = BackendScope("t1", "p1", 3)
    service.save(step(scope, "STEP-01", 1))

    with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
        service_api.list(scope, auth_context=auth(tenant="t2"))
    with pytest.raises(AuthorizationError):
        service_api.list(scope, auth_context=auth(roles=("unknown",)))


def test_activity_step_api_rejects_stale_revision_instead_of_reading_another_revision():
    service_api, service = api(sqlite3.connect(":memory:"))
    stored_scope = BackendScope("t1", "p1", 2)
    service.save(step(stored_scope, "STEP-01", 1))

    with pytest.raises(ValueError, match="REVISION_CONFLICT"):
        service_api.get(BackendScope("t1", "p1", 3), "STEP-01", auth_context=auth())
