from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    default_project_policy,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_activity_period_actual_api import (
    P6_ACTIVITY_PERIOD_ACTUAL_API_VERSION,
    P6ActivityPeriodActualAPI,
)
from construction_pm.p6_activity_period_actual_repository import (
    P6ActivityPeriodActual,
    P6ActivityPeriodActualApplicationService,
    SQLiteP6ActivityPeriodActualRepository,
)


class TransactionManager:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    @contextmanager
    def transaction(self):
        try:
            yield
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise


def scope(revision: int = 7) -> BackendScope:
    return BackendScope("t1", "p1", revision)


def auth(
    *,
    tenant_id: str = "t1",
    project_id: str = "p1",
    role: str = "planner",
) -> AuthorizationContext:
    return AuthorizationContext(
        tenant_id=tenant_id,
        project_id=project_id,
        user_id="u1",
        roles=frozenset({role}),
    )


def actual(actual_id: str = "X1") -> P6ActivityPeriodActual:
    return P6ActivityPeriodActual(
        scope(),
        actual_id,
        "A1",
        "2026-09",
        Decimal("3.125"),
        Decimal("20.50"),
        "h",
        "USD",
        "period actual",
    )


def api() -> P6ActivityPeriodActualAPI:
    connection = sqlite3.connect(":memory:")
    repository = SQLiteP6ActivityPeriodActualRepository(connection)
    service = P6ActivityPeriodActualApplicationService(repository, TransactionManager(connection))
    return P6ActivityPeriodActualAPI(service, default_project_policy())


def test_versioned_typed_create_get_and_filtered_list_boundary() -> None:
    schema_path = (
        Path(__file__).parents[1]
        / "shared/contracts/p6-activity-period-actual-api.v1.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert (
        P6_ACTIVITY_PERIOD_ACTUAL_API_VERSION
        == schema["properties"]["contract_version"]["const"]
    )

    instance = api()
    created = instance.create(actual(), auth_context=auth())

    assert created["contract_version"] == P6_ACTIVITY_PERIOD_ACTUAL_API_VERSION
    assert created["kind"] == "p6_activity_period_actual"
    assert created["scope"]["project_revision"] == 7
    assert created["activity_period_actual"]["actual_units"] == "3.125"
    assert created["activity_period_actual"]["actual_cost"] == "20.50"
    assert instance.get(scope(), "X1", auth_context=auth()) == created
    assert instance.list(scope(), auth_context=auth()) == (created,)
    assert instance.list(scope(), activity_id="A1", auth_context=auth()) == (created,)
    assert instance.list(scope(), period_id="2026-09", auth_context=auth()) == (created,)


def test_cross_scope_and_missing_permission_are_rejected() -> None:
    instance = api()
    with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
        instance.create(actual(), auth_context=auth(tenant_id="other"))

    with pytest.raises(AuthorizationError, match="authorization denied"):
        instance.get(scope(), "X1", auth_context=auth(role="writer"))
