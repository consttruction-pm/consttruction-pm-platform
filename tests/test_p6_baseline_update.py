from datetime import date
from decimal import Decimal
import sqlite3

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_baseline_activity_repository import (
    P6BaselineActivity,
    SQLiteP6BaselineActivityRepository,
)
from construction_pm.p6_baseline_repository import (
    P6Baseline,
    SQLiteP6BaselineRepository,
)
from construction_pm.p6_baseline_update import (
    BASELINE_COMPARISON_STATUS_ADDED,
    BASELINE_COMPARISON_STATUS_CHANGED,
    BASELINE_COMPARISON_STATUS_DELETED,
    BASELINE_COMPARISON_STATUS_UNCHANGED,
    BASELINE_UPDATE_FIELDS,
    P6BaselineUpdateError,
    P6BaselineUpdateSelection,
    P6BaselineUpdateService,
    compare_baseline_activities,
    plan_selective_baseline_update,
)
from construction_pm.scheduling.evm_source import (
    EVM_TECHNIQUE_ACTIVITY_PERCENT_COMPLETE,
    EVM_TECHNIQUE_FIFTY_FIFTY,
    EVM_TECHNIQUE_ZERO_HUNDRED,
)


def scope(revision: int = 7) -> BackendScope:
    return BackendScope("tenant-a", "project-a", revision)


def item(
    activity_id: str = "A",
    *,
    s: BackendScope | None = None,
    baseline_id: str = "B-1",
    start: date = date(2026, 11, 2),
    finish: date = date(2026, 11, 6),
    budget: str = "1000",
    wbs_id: str | None = "W-1",
    technique: str = EVM_TECHNIQUE_ACTIVITY_PERCENT_COMPLETE,
    currency: str = "USD",
) -> P6BaselineActivity:
    return P6BaselineActivity(
        scope=s or scope(),
        baseline_id=baseline_id,
        activity_id=activity_id,
        planned_start=start,
        planned_finish=finish,
        budgeted_cost=Decimal(budget),
        currency=currency,
        wbs_id=wbs_id,
        earned_value_technique=technique,
    )


def test_selective_field_update_preserves_unselected_fields():
    existing = (item("A"),)
    current = (
        item(
            "A", start=date(2026, 11, 3), finish=date(2026, 11, 10),
            budget="1250", wbs_id="W-2", technique=EVM_TECHNIQUE_ZERO_HUNDRED,
        ),
    )
    plan = plan_selective_baseline_update(
        existing,
        current,
        P6BaselineUpdateSelection(fields=frozenset({"planned_finish"})),
        target_baseline_id="B-2",
    )

    row = plan.rows[0]
    assert row.baseline_id == "B-2"
    assert row.planned_finish == date(2026, 11, 10)
    # Excluded fields keep the stored baseline values.
    assert row.planned_start == date(2026, 11, 2)
    assert row.budgeted_cost == Decimal("1000")
    assert row.wbs_id == "W-1"
    assert row.earned_value_technique == EVM_TECHNIQUE_ACTIVITY_PERCENT_COMPLETE
    assert plan.updated_activity_ids == ("A",)
    assert plan.unchanged_activity_ids == ()


def test_filtered_activity_subset_leaves_other_activities_untouched():
    existing = (item("A"), item("B", budget="200"))
    current = (
        item("A", budget="1500"),
        item("B", budget="900", finish=date(2026, 11, 20)),
    )
    plan = plan_selective_baseline_update(
        existing,
        current,
        P6BaselineUpdateSelection(activity_ids=frozenset({"A"})),
        target_baseline_id="B-2",
    )

    by_id = {row.activity_id: row for row in plan.rows}
    assert by_id["A"].budgeted_cost == Decimal("1500")
    assert by_id["B"].budgeted_cost == Decimal("200")
    assert by_id["B"].planned_finish == date(2026, 11, 6)
    assert plan.updated_activity_ids == ("A",)
    assert plan.unchanged_activity_ids == ("B",)


def test_add_new_activities_respects_the_selection_flag():
    existing = (item("A"),)
    current = (item("A"), item("C", budget="300"))

    without_add = plan_selective_baseline_update(
        existing,
        current,
        P6BaselineUpdateSelection(add_new_activities=False),
        target_baseline_id="B-2",
    )
    assert [row.activity_id for row in without_add.rows] == ["A"]
    assert without_add.added_activity_ids == ()

    with_add = plan_selective_baseline_update(
        existing,
        current,
        P6BaselineUpdateSelection(),
        target_baseline_id="B-2",
    )
    assert [row.activity_id for row in with_add.rows] == ["A", "C"]
    assert with_add.added_activity_ids == ("C",)
    assert {row.activity_id: row for row in with_add.rows}["C"].baseline_id == "B-2"


def test_removal_only_happens_for_selected_activities_when_enabled():
    existing = (item("A"), item("B", budget="200"))

    kept = plan_selective_baseline_update(
        existing,
        (item("A"),),
        P6BaselineUpdateSelection(
            activity_ids=frozenset({"A"}), remove_missing_activities=True
        ),
        target_baseline_id="B-2",
    )
    # B is missing from current but is outside the selected filter, so it is
    # preserved instead of being deleted.
    assert [row.activity_id for row in kept.rows] == ["A", "B"]
    assert kept.removed_activity_ids == ()

    deleted = plan_selective_baseline_update(
        existing,
        (item("A"),),
        P6BaselineUpdateSelection(
            activity_ids=frozenset({"B"}), remove_missing_activities=True
        ),
        target_baseline_id="B-2",
    )
    assert [row.activity_id for row in deleted.rows] == ["A"]
    assert deleted.removed_activity_ids == ("B",)


@pytest.mark.parametrize(
    ("selection", "error"),
    (
        (P6BaselineUpdateSelection(fields=frozenset()), "BASELINE_UPDATE_FIELDS_EMPTY"),
        (
            P6BaselineUpdateSelection(fields=frozenset({"actual_cost"})),
            "BASELINE_UPDATE_FIELD_UNSUPPORTED:actual_cost",
        ),
        (
            P6BaselineUpdateSelection(activity_ids=frozenset()),
            "BASELINE_UPDATE_ACTIVITY_IDS_EMPTY",
        ),
        (
            P6BaselineUpdateSelection(add_new_activities="yes"),  # type: ignore[arg-type]
            "BASELINE_UPDATE_ADD_FLAG_INVALID",
        ),
    ),
)
def test_invalid_selections_fail_closed(selection, error):
    with pytest.raises(P6BaselineUpdateError, match=error):
        plan_selective_baseline_update(
            (item("A"),),
            (item("A"),),
            selection,
            target_baseline_id="B-2",
        )


def test_target_scope_and_currency_mismatches_fail_closed():
    with pytest.raises(
        P6BaselineUpdateError, match="BASELINE_UPDATE_TARGET_MUST_DIFFER"
    ):
        plan_selective_baseline_update(
            (item("A"),),
            (item("A"),),
            P6BaselineUpdateSelection(),
            target_baseline_id="B-1",
        )

    with pytest.raises(
        P6BaselineUpdateError, match="BASELINE_UPDATE_CURRENCY_MISMATCH:A"
    ):
        plan_selective_baseline_update(
            (item("A"),),
            (item("A", currency="EUR"),),
            P6BaselineUpdateSelection(),
            target_baseline_id="B-2",
        )

    with pytest.raises(
        P6BaselineUpdateError, match="BASELINE_UPDATE_CURRENT_SCOPE_MISMATCH"
    ):
        plan_selective_baseline_update(
            (item("A"),),
            (item("A", s=BackendScope("tenant-a", "project-b", 7)),),
            P6BaselineUpdateSelection(fields=frozenset({"planned_finish"})),
            target_baseline_id="B-2",
        )


def test_comparison_reports_variances_and_one_sided_rows_explicitly():
    baseline = (
        item("A"),
        item("B", budget="200"),
        item("D", budget="400"),
    )
    current = (
        item(
            "A", start=date(2026, 11, 4), finish=date(2026, 11, 7),
            budget="1050", wbs_id="W-2", technique=EVM_TECHNIQUE_FIFTY_FIFTY,
        ),
        item("B", budget="200"),
        item("C", budget="300"),
    )
    rows = {
        row.activity_id: row
        for row in compare_baseline_activities(baseline, current)
    }

    changed = rows["A"]
    assert changed.status == BASELINE_COMPARISON_STATUS_CHANGED
    assert changed.start_variance_days == 2
    assert changed.finish_variance_days == 1
    assert changed.budget_variance == Decimal("50")
    assert changed.wbs_changed is True
    assert changed.technique_changed is True

    unchanged = rows["B"]
    assert unchanged.status == BASELINE_COMPARISON_STATUS_UNCHANGED
    assert unchanged.start_variance_days == 0
    assert unchanged.finish_variance_days == 0
    assert unchanged.budget_variance == Decimal("0")

    added = rows["C"]
    assert added.status == BASELINE_COMPARISON_STATUS_ADDED
    assert added.start_variance_days is None
    assert added.budget_variance is None
    assert added.current_budgeted_cost == Decimal("300")

    deleted = rows["D"]
    assert deleted.status == BASELINE_COMPARISON_STATUS_DELETED
    assert deleted.current_planned_start is None
    assert deleted.budget_variance is None


def test_update_plan_payload_is_deterministic_and_lists_the_scope():
    plan = plan_selective_baseline_update(
        (item("B", budget="200"), item("A")),
        (item("A", budget="1500"),),
        P6BaselineUpdateSelection(
            activity_ids=frozenset({"A"}),
            fields=frozenset({"budgeted_cost"}),
        ),
        target_baseline_id="B-2",
    )
    payload = plan.canonical_payload()
    assert payload["source_baseline_id"] == "B-1"
    assert payload["target_baseline_id"] == "B-2"
    assert payload["selection"]["activity_ids"] == ["A"]
    assert payload["selection"]["fields"] == ["budgeted_cost"]
    assert payload["updated_activity_ids"] == ["A"]
    assert [row["activity_id"] for row in payload["activities"]] == ["A", "B"]
    assert payload["activities"][0]["budgeted_cost"] == "1500"
    assert payload["activities"][1]["budgeted_cost"] == "200"


class _Tx:
    def transaction(self):
        class Ctx:
            def __enter__(self):
                return None

            def __exit__(self, exc_type, exc, tb):
                return False

        return Ctx()


def _seed_target(connection, baseline_id: str) -> None:
    SQLiteP6BaselineRepository(connection).upsert(
        P6Baseline(
            scope(), baseline_id, "Updated Baseline", "USER_SELECTED", 3,
            "2026-11-02T10:00:00Z",
        )
    )


def test_apply_persists_a_new_immutable_baseline_from_a_real_sqlite_store():
    connection = sqlite3.connect(":memory:")
    _seed_target(connection, "B-1")
    _seed_target(connection, "B-2")
    repo = SQLiteP6BaselineActivityRepository(connection)
    original = (item("A"), item("B", budget="200"))
    repo.save_many(original)
    service = P6BaselineUpdateService(repo, _Tx())

    plan = service.apply(
        scope(),
        "B-1",
        "B-2",
        (
            item("A", budget="1500", finish=date(2026, 11, 10)),
            item("B", budget="900"),
        ),
        P6BaselineUpdateSelection(
            activity_ids=frozenset({"A"}),
            fields=frozenset({"budgeted_cost"}),
        ),
    )

    assert plan.updated_activity_ids == ("A",)
    stored = repo.list(scope(), "B-2")
    assert stored == (
        item("A", baseline_id="B-2", budget="1500"),
        item("B", baseline_id="B-2", budget="200"),
    )
    # The source baseline is never mutated by the update.
    assert repo.list(scope(), "B-1") == original


def test_compare_service_reads_the_persisted_baseline():
    connection = sqlite3.connect(":memory:")
    _seed_target(connection, "B-1")
    repo = SQLiteP6BaselineActivityRepository(connection)
    repo.save_many((item("A"),))
    service = P6BaselineUpdateService(repo, _Tx())

    rows = service.compare(scope(), "B-1", (item("A", budget="1250"),))
    assert len(rows) == 1
    assert rows[0].budget_variance == Decimal("250")
    assert rows[0].status == BASELINE_COMPARISON_STATUS_CHANGED
