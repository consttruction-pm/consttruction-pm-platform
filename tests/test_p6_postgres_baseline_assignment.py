from __future__ import annotations

import os
import uuid
from datetime import date
from decimal import Decimal

import pytest

psycopg = pytest.importorskip("psycopg")

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_baseline_activity_repository import (
    P6BaselineActivity,
    PostgresP6BaselineActivityRepository,
)
from construction_pm.p6_baseline_assignment import (
    BASELINE_ROLE_PRIMARY,
    P6BaselineAssignmentError,
    P6BaselineAssignmentService,
    PostgresP6BaselineRoleAssignmentRepository,
)
from construction_pm.p6_baseline_conversion import (
    P6BaselineConversionService,
    P6BaselineConversionError,
)
from construction_pm.p6_baseline_repository import (
    P6Baseline,
    PostgresP6BaselineRepository,
)
from construction_pm.p6_current_activity_value_repository import (
    P6CurrentActivityApplicationService,
    P6CurrentActivityValue,
    PostgresP6CurrentActivityRepository,
)


@pytest.fixture(scope="module")
def postgres_dsn() -> str:
    dsn = os.getenv("P6_TEST_POSTGRES_DSN") or os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
    if not dsn:
        pytest.skip("PostgreSQL DSN is not configured")
    return dsn


@pytest.fixture()
def connection(postgres_dsn):
    conn = psycopg.connect(postgres_dsn)
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()


class _ConnectionTx:
    def __init__(self, connection):
        self.connection = connection

    def transaction(self):
        return self.connection.transaction()


def _scope(project_id: str | None = None, revision: int = 7) -> BackendScope:
    suffix = uuid.uuid4().hex
    return BackendScope(
        f"tenant-{suffix}",
        project_id or f"project-{suffix}",
        revision,
    )


def _repositories(connection):
    baselines = PostgresP6BaselineRepository(connection)
    baselines.initialize()
    activities = PostgresP6BaselineActivityRepository(connection)
    activities.initialize()
    assignments = PostgresP6BaselineRoleAssignmentRepository(connection)
    assignments.initialize()
    return baselines, activities, assignments


def _baseline(scope: BackendScope, baseline_id: str = "baseline-1") -> P6Baseline:
    return P6Baseline(
        scope,
        baseline_id,
        f"Baseline {baseline_id}",
        "USER_SELECTED",
        scope.project_revision,
        "2026-11-02T10:00:00Z",
    )


def _activity(scope: BackendScope, activity_id: str, baseline_id: str = "baseline-1"):
    return P6BaselineActivity(
        scope,
        baseline_id,
        activity_id,
        date(2026, 11, 2),
        date(2026, 11, 6),
        Decimal("1000.00"),
        "USD",
        "W-1",
        "ACTIVITY_PERCENT_COMPLETE",
    )


def test_postgres_baseline_role_assignment_round_trip_and_audit(connection):
    baselines, activities, assignments = _repositories(connection)
    scope = _scope()
    tx = _ConnectionTx(connection)
    service = P6BaselineAssignmentService(
        repository=assignments,
        baseline_repository=baselines,
        baseline_activity_repository=activities,
        transaction_manager=tx,
        clock=lambda: "2026-11-03T08:00:00Z",
    )
    with connection.transaction():
        baselines.upsert(_baseline(scope, "baseline-1"))
        baselines.upsert(_baseline(scope, "baseline-2"))
        activities.save_many((_activity(scope, "A"),))

    with connection.transaction():
        first, replaced = service.assign(
            scope, BASELINE_ROLE_PRIMARY, "baseline-1", assigned_by="user-1"
        )
    assert replaced is False
    assert first.previous_baseline_id is None
    summary = service.summary(scope)
    assert summary.to_payload()["roles"]["PRIMARY"]["baseline_id"] == "baseline-1"
    assert summary.to_payload()["roles"]["PRIMARY"]["activity_count"] == 1

    with pytest.raises(
        P6BaselineAssignmentError, match="BASELINE_ROLE_ALREADY_ASSIGNED:PRIMARY"
    ):
        service.assign(
            scope, BASELINE_ROLE_PRIMARY, "baseline-2", assigned_by="user-2"
        )
    with connection.transaction():
        second, replaced = service.assign(
            scope,
            BASELINE_ROLE_PRIMARY,
            "baseline-2",
            assigned_by="user-2",
            replace=True,
        )
    assert replaced is True
    assert second.previous_baseline_id == "baseline-1"
    assert [
        row.baseline_id for row in service.history(scope, BASELINE_ROLE_PRIMARY)
    ] == ["baseline-1", "baseline-2"]

    with pytest.raises(P6BaselineAssignmentError, match="REVISION_CONFLICT"):
        service.read(
            BackendScope(scope.tenant_id, scope.project_id, 8), BASELINE_ROLE_PRIMARY
        )


def test_postgres_cross_project_baseline_conversion(connection):
    baselines, activities, _ = _repositories(connection)
    current_repository = PostgresP6CurrentActivityRepository(connection)
    current_repository.initialize()
    tx = _ConnectionTx(connection)
    current_service = P6CurrentActivityApplicationService(current_repository, tx)
    service = P6BaselineConversionService(
        baseline_repository=baselines,
        baseline_activity_repository=activities,
        current_source=current_service,
        transaction_manager=tx,
        clock=lambda: "2026-11-03T08:00:00Z",
    )
    tenant_suffix = uuid.uuid4().hex
    source = BackendScope(f"tenant-{tenant_suffix}", f"source-{tenant_suffix}", 4)
    target = BackendScope(f"tenant-{tenant_suffix}", f"target-{tenant_suffix}", 2)
    with connection.transaction():
        current_service.save_many(
            (
                P6CurrentActivityValue(
                    source,
                    "A",
                    date(2026, 11, 2),
                    date(2026, 11, 6),
                    Decimal("1000"),
                    "USD",
                    "W-1",
                    "ACTIVITY_PERCENT_COMPLETE",
                ),
                P6CurrentActivityValue(
                    source,
                    "B",
                    date(2026, 11, 9),
                    date(2026, 11, 13),
                    Decimal("2500"),
                    "EUR",
                    "W-2",
                    "ACTIVITY_PERCENT_COMPLETE",
                ),
            )
        )

    result = service.convert(
        source,
        target,
        target_baseline_id="converted-1",
        target_name="Converted Source Project",
        baseline_type="SECONDARY",
    )

    assert result.baseline.scope == target
    assert result.baseline.source_revision == 4
    assert [row.activity_id for row in result.rows] == ["A", "B"]
    assert result.currency_totals() == (
        {"currency": "EUR", "activity_count": 1, "total_budget": "2500"},
        {"currency": "USD", "activity_count": 1, "total_budget": "1000"},
    )
    assert activities.list(target, "converted-1") == result.rows
    assert activities.list(source, "converted-1") == ()

    with pytest.raises(
        P6BaselineConversionError, match="BASELINE_CONVERSION_TARGET_EXISTS"
    ):
        service.convert(
            source,
            target,
            target_baseline_id="converted-1",
            target_name="Different Name",
        )
