from __future__ import annotations

import os
from contextlib import contextmanager
from decimal import Decimal

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    default_project_policy,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_activity_period_actual_api import P6ActivityPeriodActualAPI
from construction_pm.p6_activity_period_actual_repository import (
    P6ActivityPeriodActual,
    P6ActivityPeriodActualApplicationService,
    PostgresP6ActivityPeriodActualRepository,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("CONSTRUCTION_PM_POSTGRES_DSN"),
    reason="CONSTRUCTION_PM_POSTGRES_DSN is not configured",
)


def connect():
    import psycopg

    return psycopg.connect(os.environ["CONSTRUCTION_PM_POSTGRES_DSN"])


class PostgresTransactionManager:
    def __init__(self, connection) -> None:
        self.connection = connection

    @contextmanager
    def transaction(self):
        with self.connection.transaction():
            yield


def auth(tenant_id: str, project_id: str) -> AuthorizationContext:
    return AuthorizationContext(
        tenant_id=tenant_id,
        project_id=project_id,
        user_id="u-api",
        roles=frozenset({"planner"}),
    )


def test_postgres_api_round_trip_scope_revision_and_typed_values() -> None:
    with connect() as connection:
        repository = PostgresP6ActivityPeriodActualRepository(connection)
        repository.initialize()
        connection.commit()

        scope = BackendScope("tenant-period-api", "project-period-api", 11)
        service = P6ActivityPeriodActualApplicationService(
            repository,
            PostgresTransactionManager(connection),
        )
        api = P6ActivityPeriodActualAPI(service, default_project_policy())
        value = P6ActivityPeriodActual(
            scope,
            "X-API-1",
            "A-API-1",
            "2026-09",
            Decimal("3.125"),
            Decimal("20.50"),
            "h",
            "USD",
            "live api",
        )

        created = api.create(value, auth_context=auth(scope.tenant_id, scope.project_id))
        assert api.get(
            scope,
            "X-API-1",
            auth_context=auth(scope.tenant_id, scope.project_id),
        ) == created
        assert api.list(
            scope,
            activity_id="A-API-1",
            period_id="2026-09",
            auth_context=auth(scope.tenant_id, scope.project_id),
        ) == (created,)

        other_scope = BackendScope("tenant-period-api-other", scope.project_id, 11)
        assert api.get(
            other_scope,
            "X-API-1",
            auth_context=auth(other_scope.tenant_id, other_scope.project_id),
        ) is None
        with pytest.raises(Exception, match="REVISION_CONFLICT"):
            api.get(
                BackendScope(scope.tenant_id, scope.project_id, 12),
                "X-API-1",
                auth_context=auth(scope.tenant_id, scope.project_id),
            )
