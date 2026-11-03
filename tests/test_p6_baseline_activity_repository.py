from datetime import date
from decimal import Decimal

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_baseline_activity_repository import (
    P6BaselineActivity,
    P6BaselineActivityApplicationService,
    P6BaselineActivityPersistenceError,
    SQLiteP6BaselineActivityRepository,
)
from construction_pm.p6_baseline_repository import (
    P6Baseline,
    SQLiteP6BaselineRepository,
)
from construction_pm.scheduling.evm_source import (
    EVM_TECHNIQUE_ACTIVITY_PERCENT_COMPLETE,
    EVM_TECHNIQUE_ZERO_HUNDRED,
)


def scope(revision: int = 7) -> BackendScope:
    return BackendScope("tenant-a", "project-a", revision)


def seed_baseline(connection, s: BackendScope, baseline_id: str = "b-1") -> None:
    SQLiteP6BaselineRepository(connection).upsert(
        P6Baseline(
            s,
            baseline_id,
            "Approved Baseline",
            "PRIMARY",
            3,
            "2026-09-28T10:00:00Z",
        )
    )


def activity(
    activity_id: str = "A",
    *,
    s: BackendScope | None = None,
    baseline_id: str = "b-1",
    wbs_id: str | None = "W-1",
    budgeted_cost: str = "1000",
    technique: str = EVM_TECHNIQUE_ACTIVITY_PERCENT_COMPLETE,
) -> P6BaselineActivity:
    return P6BaselineActivity(
        scope=s or scope(),
        baseline_id=baseline_id,
        activity_id=activity_id,
        planned_start=date(2026, 11, 2),
        planned_finish=date(2026, 11, 6),
        budgeted_cost=Decimal(budgeted_cost),
        currency="USD",
        wbs_id=wbs_id,
        earned_value_technique=technique,
    )


def repository(connection) -> SQLiteP6BaselineActivityRepository:
    return SQLiteP6BaselineActivityRepository(connection)


def test_round_trip_and_deterministic_list():
    import sqlite3

    connection = sqlite3.connect(":memory:")
    seed_baseline(connection, scope())
    repo = repository(connection)
    repo.save_many(
        (
            activity("B", budgeted_cost="200", technique=EVM_TECHNIQUE_ZERO_HUNDRED),
            activity("A"),
        )
    )

    stored = repo.list(scope(), "b-1")
    assert [item.activity_id for item in stored] == ["A", "B"]
    assert stored[0].to_value().budgeted_cost == Decimal("1000")
    assert stored[1].earned_value_technique == EVM_TECHNIQUE_ZERO_HUNDRED


def test_scope_isolation_and_revision_conflict():
    import sqlite3

    connection = sqlite3.connect(":memory:")
    seed_baseline(connection, scope())
    repo = repository(connection)
    repo.save_many((activity(),))

    assert repo.list(BackendScope("tenant-b", "project-a", 7), "b-1") == ()
    assert repo.list(BackendScope("tenant-a", "project-b", 7), "b-1") == ()
    with pytest.raises(
        P6BaselineActivityPersistenceError, match="REVISION_CONFLICT"
    ):
        repo.list(scope(8), "b-1")


def test_baseline_activity_set_is_immutable_and_identical_replay_is_idempotent():
    import sqlite3

    connection = sqlite3.connect(":memory:")
    seed_baseline(connection, scope())
    repo = repository(connection)
    item = activity()
    assert repo.save_many((item,)) == (item,)
    assert repo.save_many((item,)) == (item,)

    with pytest.raises(
        P6BaselineActivityPersistenceError, match="IMMUTABLE_BASELINE_ACTIVITIES"
    ):
        repo.save_many((activity(budgeted_cost="999"),))


def test_parent_baseline_is_required():
    import sqlite3

    connection = sqlite3.connect(":memory:")
    repo = repository(connection)

    with pytest.raises(
        P6BaselineActivityPersistenceError,
        match="BASELINE_ACTIVITY_PARENT_BASELINE_REQUIRED",
    ):
        repo.save_many((activity(),))


def test_batch_validation_rejects_duplicates_and_cross_scope_rows():
    import sqlite3

    connection = sqlite3.connect(":memory:")
    seed_baseline(connection, scope())
    repo = repository(connection)

    with pytest.raises(
        P6BaselineActivityPersistenceError, match="DUPLICATE_BASELINE_ACTIVITY"
    ):
        repo.save_many((activity("A"), activity("A", budgeted_cost="2")))
    with pytest.raises(
        P6BaselineActivityPersistenceError, match="BASELINE_ACTIVITY_SCOPE_MISMATCH"
    ):
        repo.save_many(
            (
                activity("A"),
                activity("B", s=BackendScope("tenant-b", "project-a", 7)),
            )
        )
    with pytest.raises(
        P6BaselineActivityPersistenceError, match="BASELINE_ACTIVITIES_EMPTY"
    ):
        repo.save_many(())


@pytest.mark.parametrize(
    ("kwargs", "error"),
    (
        ({"planned_start": date(2026, 11, 7)}, "INVALID_PLANNED_WINDOW"),
        ({"budgeted_cost": Decimal("-1")}, "INVALID_BUDGETED_COST"),
        ({"currency": ""}, "INVALID_CURRENCY"),
        ({"earned_value_technique": "UNKNOWN"}, "INVALID_EARNED_VALUE_TECHNIQUE"),
    ),
)
def test_invalid_baseline_activity_values_fail_closed(kwargs, error):
    import sqlite3

    connection = sqlite3.connect(":memory:")
    seed_baseline(connection, scope())
    repo = repository(connection)
    values = {
        "scope": scope(),
        "baseline_id": "b-1",
        "activity_id": "A",
        "planned_start": date(2026, 11, 2),
        "planned_finish": date(2026, 11, 6),
        "budgeted_cost": Decimal("100"),
        "currency": "USD",
        "wbs_id": "W-1",
        "earned_value_technique": EVM_TECHNIQUE_ACTIVITY_PERCENT_COMPLETE,
    }
    values.update(kwargs)
    with pytest.raises(P6BaselineActivityPersistenceError, match=error):
        P6BaselineActivity(**values).validate()


class _Tx:
    def __init__(self):
        self.entered = 0
        self.exited = 0

    def transaction(self):
        owner = self

        class Ctx:
            def __enter__(self):
                owner.entered += 1

            def __exit__(self, exc_type, exc, tb):
                owner.exited += 1

        return Ctx()


def test_application_service_owns_transaction_boundary():
    import sqlite3

    connection = sqlite3.connect(":memory:")
    seed_baseline(connection, scope())
    tx = _Tx()
    service = P6BaselineActivityApplicationService(repository(connection), tx)

    item = activity()
    assert service.save_many((item,)) == (item,)
    assert service.list(scope(), "b-1") == (item,)
    assert tx.entered == 2
    assert tx.exited == 2
