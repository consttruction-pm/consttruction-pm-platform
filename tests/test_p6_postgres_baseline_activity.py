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
    P6BaselineActivityPersistenceError,
    PostgresP6BaselineActivityRepository,
)
from construction_pm.p6_baseline_repository import (
    P6Baseline,
    PostgresP6BaselineRepository,
)
from construction_pm.p6_current_activity_value_repository import (
    P6CurrentActivityApplicationService,
    P6CurrentActivityPersistenceError,
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


def _scope(revision: int = 7) -> BackendScope:
    suffix = uuid.uuid4().hex
    return BackendScope(f"tenant-{suffix}", f"project-{suffix}", revision)


def _baseline(scope: BackendScope) -> P6Baseline:
    return P6Baseline(
        scope,
        "baseline-1",
        "Approved Baseline",
        "PRIMARY",
        scope.project_revision,
        "2026-11-02T10:00:00Z",
        "immutable metadata",
    )


def _activity(
    scope: BackendScope,
    activity_id: str = "A-1",
    budget: str = "1000.00",
    wbs_id: str | None = "W-1",
) -> P6BaselineActivity:
    return P6BaselineActivity(
        scope,
        "baseline-1",
        activity_id,
        date(2026, 11, 2),
        date(2026, 11, 6),
        Decimal(budget),
        "USD",
        wbs_id,
        "ACTIVITY_PERCENT_COMPLETE",
    )


def _repositories(connection):
    baselines = PostgresP6BaselineRepository(connection)
    baselines.initialize()
    activities = PostgresP6BaselineActivityRepository(connection)
    activities.initialize()
    return baselines, activities


def _current_value(
    scope: BackendScope,
    activity_id: str = "A-1",
    budget: str = "1000.00",
) -> P6CurrentActivityValue:
    from construction_pm.scheduling.evm_source import (
        EVM_TECHNIQUE_ACTIVITY_PERCENT_COMPLETE,
    )

    return P6CurrentActivityValue(
        scope,
        activity_id,
        date(2026, 11, 2),
        date(2026, 11, 6),
        Decimal(budget),
        "USD",
        "W-1",
        EVM_TECHNIQUE_ACTIVITY_PERCENT_COMPLETE,
    )


def test_postgres_baseline_activities_round_trip_and_are_immutable(connection):
    baselines, repository = _repositories(connection)
    scope = _scope()
    with connection.transaction():
        baselines.upsert(_baseline(scope))
        first = repository.save_many((_activity(scope, "B", "500"), _activity(scope, "A")))
        assert [item.activity_id for item in first] == ["A", "B"]
        assert repository.save_many((_activity(scope, "A"), _activity(scope, "B", "500"))) == first

    stored = repository.list(scope, "baseline-1")
    assert stored == first

    with pytest.raises(
        P6BaselineActivityPersistenceError, match="IMMUTABLE_BASELINE_ACTIVITIES"
    ):
        repository.save_many((_activity(scope, "A", "1200"),))


def test_postgres_baseline_activity_scope_and_revision_are_enforced(connection):
    baselines, repository = _repositories(connection)
    scope = _scope()
    with connection.transaction():
        baselines.upsert(_baseline(scope))
        repository.save_many((_activity(scope),))

    assert repository.list(BackendScope("tenant-other", scope.project_id, 7), "baseline-1") == ()
    assert (
        repository.list(BackendScope(scope.tenant_id, "project-other", 7), "baseline-1")
        == ()
    )
    with pytest.raises(P6BaselineActivityPersistenceError, match="REVISION_CONFLICT"):
        repository.list(BackendScope(scope.tenant_id, scope.project_id, 8), "baseline-1")


def test_postgres_baseline_activity_requires_the_parent_baseline(connection):
    _, repository = _repositories(connection)
    scope = _scope()

    with pytest.raises(
        P6BaselineActivityPersistenceError,
        match="BASELINE_ACTIVITY_PARENT_BASELINE_REQUIRED",
    ):
        repository.save_many((_activity(scope),))


def test_postgres_selective_update_persists_a_new_baseline(connection):
    from construction_pm.p6_baseline_update import (
        P6BaselineUpdateSelection,
        P6BaselineUpdateService,
    )

    class _Tx:
        def transaction(self):
            return connection.transaction()

    baselines, repository = _repositories(connection)
    scope = _scope()
    with connection.transaction():
        baselines.upsert(_baseline(scope))
        baselines.upsert(
            P6Baseline(
                scope,
                "baseline-2",
                "Updated Baseline",
                "USER_SELECTED",
                scope.project_revision,
                "2026-11-02T11:00:00Z",
            )
        )
    original = (_activity(scope, "A"), _activity(scope, "B", "500"))
    repository.save_many(original)

    service = P6BaselineUpdateService(repository, _Tx())
    plan = service.apply(
        scope,
        "baseline-1",
        "baseline-2",
        (
            P6BaselineActivity(
                scope, "baseline-1", "A", date(2026, 11, 3),
                date(2026, 11, 10), Decimal("1500"), "USD", "W-2",
                "ACTIVITY_PERCENT_COMPLETE",
            ),
            P6BaselineActivity(
                scope, "baseline-1", "B", date(2026, 11, 2),
                date(2026, 11, 6), Decimal("900"), "USD", "W-1",
                "ACTIVITY_PERCENT_COMPLETE",
            ),
        ),
        P6BaselineUpdateSelection(
            activity_ids=frozenset({"A"}),
            fields=frozenset({"budgeted_cost"}),
        ),
    )

    assert plan.updated_activity_ids == ("A",)
    stored = repository.list(scope, "baseline-2")
    assert [(row.activity_id, row.budgeted_cost) for row in stored] == [
        ("A", Decimal("1500")),
        ("B", Decimal("500")),
    ]
    assert repository.list(scope, "baseline-1") == original


def test_postgres_current_values_round_trip_and_enforce_scope_and_revision(
    connection,
):
    repository = PostgresP6CurrentActivityRepository(connection)
    repository.initialize()
    scope = _scope()
    service = P6CurrentActivityApplicationService(repository, _ConnectionTx(connection))

    with connection.transaction():
        first = service.save_many(
            (_current_value(scope, "B", "250"), _current_value(scope, "A"))
        )
    assert [row.activity_id for row in first] == ["A", "B"]
    assert service.list_as_baseline(scope)[0].baseline_id == "CURRENT"

    assert service.list(BackendScope("tenant-other", scope.project_id, 7)) == ()
    assert service.list(BackendScope(scope.tenant_id, "project-other", 7)) == ()
    with pytest.raises(P6CurrentActivityPersistenceError, match="REVISION_CONFLICT"):
        service.list(BackendScope(scope.tenant_id, scope.project_id, 8))

    with connection.transaction():
        service.save_many(
            (_current_value(BackendScope(scope.tenant_id, scope.project_id, 8), "A", "300"),)
        )
    with pytest.raises(P6CurrentActivityPersistenceError, match="REVISION_CONFLICT"):
        service.list(scope)


class _ConnectionTx:
    def __init__(self, connection):
        self.connection = connection

    def transaction(self):
        return self.connection.transaction()


def test_postgres_selective_update_api_uses_persisted_current_values(connection):
    from construction_pm.application.authorization import (
        AuthorizationContext,
        default_project_policy,
    )
    from construction_pm.p6_baseline_update import P6BaselineUpdateSelection
    from construction_pm.p6_baseline_update import P6BaselineUpdateService
    from construction_pm.p6_baseline_update_api import P6BaselineUpdateAPI

    baselines, activities = _repositories(connection)
    current_repository = PostgresP6CurrentActivityRepository(connection)
    current_repository.initialize()
    scope = _scope()
    tx = _ConnectionTx(connection)
    current_service = P6CurrentActivityApplicationService(
        current_repository, tx
    )
    service = P6BaselineUpdateService(
        repository=activities,
        transaction_manager=tx,
        baseline_repository=baselines,
        current_source=current_service,
        clock=lambda: "2026-11-02T12:00:00+00:00",
    )
    api = P6BaselineUpdateAPI(service, default_project_policy())
    auth = AuthorizationContext(
        scope.tenant_id, scope.project_id, "user-1", frozenset({"planner"})
    )

    with connection.transaction():
        baselines.upsert(_baseline(scope))
        activities.save_many((_activity(scope, "A"), _activity(scope, "B", "500")))
        current_service.save_many(
            (
                P6CurrentActivityValue(
                    scope,
                    "A",
                    date(2026, 11, 4),
                    date(2026, 11, 10),
                    Decimal("1500"),
                    "USD",
                    "W-2",
                    "ACTIVITY_PERCENT_COMPLETE",
                ),
                _current_value(scope, "B", "500"),
            )
        )

    preview = api.preview(
        scope,
        "baseline-1",
        "baseline-2",
        P6BaselineUpdateSelection(fields=frozenset({"budgeted_cost"})),
        expected_revision=scope.project_revision,
        auth_context=auth,
    )
    assert preview["updated_activity_ids"] == ["A"]
    assert preview["counts"]["unchanged"] == 1

    applied = api.apply(
        scope,
        "baseline-1",
        "baseline-2",
        P6BaselineUpdateSelection(fields=frozenset({"budgeted_cost"})),
        target_name="Updated Baseline",
        expected_revision=scope.project_revision,
        auth_context=auth,
    )
    assert applied["baseline"]["baseline_id"] == "baseline-2"
    stored = activities.list(scope, "baseline-2")
    assert [(row.activity_id, row.budgeted_cost) for row in stored] == [
        ("A", Decimal("1500")),
        ("B", Decimal("500")),
    ]

    compared = api.compare(
        scope,
        "baseline-1",
        expected_revision=scope.project_revision,
        auth_context=auth,
    )
    rows = {row["activity_id"]: row for row in compared["rows"]}
    assert rows["A"]["budget_variance"] == "500"
    assert rows["A"]["status"] == "CHANGED"
