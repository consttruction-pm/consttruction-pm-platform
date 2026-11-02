from datetime import date
from decimal import Decimal
import sqlite3

from construction_pm.activity_master_repository import (
    ActivityMaster,
    SQLiteActivityMasterRepository,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_activity_period_actual_repository import (
    P6ActivityPeriodActual,
    SQLiteP6ActivityPeriodActualRepository,
)
from construction_pm.p6_baseline_activity_repository import (
    P6BaselineActivity,
    SQLiteP6BaselineActivityRepository,
)
from construction_pm.p6_baseline_repository import (
    P6Baseline,
    SQLiteP6BaselineRepository,
)
from construction_pm.p6_earned_value_read_model import P6EarnedValueReadModelService
from construction_pm.p6_expense_repository import P6Expense, SQLiteP6ExpenseRepository
from construction_pm.scheduling.activity import ActivityStatus
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.evm_source import EVM_TECHNIQUE_ZERO_HUNDRED
from construction_pm.scheduling.time_duration import DurationUnit


def test_evm_read_model_reconciles_real_sqlite_persistence():
    scope = BackendScope("tenant-a", "project-a", 7)
    connection = sqlite3.connect(":memory:")

    baselines = SQLiteP6BaselineRepository(connection)
    baselines.upsert(
        P6Baseline(
            scope, "B-1", "Approved Baseline", "PRIMARY", 3,
            "2026-11-01T10:00:00Z", None,
        )
    )
    baseline_activities = SQLiteP6BaselineActivityRepository(connection)
    baseline_activities.save_many(
        (
            P6BaselineActivity(
                scope, "B-1", "A", date(2026, 11, 2), date(2026, 11, 6),
                Decimal("1000"), "USD", "W-1", "ACTIVITY_PERCENT_COMPLETE",
            ),
            P6BaselineActivity(
                scope, "B-1", "B", date(2026, 11, 9), date(2026, 11, 13),
                Decimal("500"), "USD", "W-2", EVM_TECHNIQUE_ZERO_HUNDRED,
            ),
        )
    )

    activities = SQLiteActivityMasterRepository(connection)
    activities.save(
        ActivityMaster(
            scope=scope,
            activity_id="A",
            duration_value=Decimal("5"),
            duration_unit=DurationUnit.WORKING_DAY,
            actual_start=date(2026, 11, 2),
            percent_complete=50.0,
            status=ActivityStatus.IN_PROGRESS,
        )
    )
    activities.save(
        ActivityMaster(
            scope=scope,
            activity_id="B",
            duration_value=Decimal("5"),
            duration_unit=DurationUnit.WORKING_DAY,
            actual_start=date(2026, 11, 9),
            actual_finish=date(2026, 11, 13),
            percent_complete=100.0,
            status=ActivityStatus.COMPLETED,
        )
    )

    actuals = SQLiteP6ActivityPeriodActualRepository(connection)
    actuals.upsert(
        P6ActivityPeriodActual(
            scope, "P-A", "A", "P1", actual_cost=Decimal("300"), currency="USD"
        )
    )
    actuals.upsert(
        P6ActivityPeriodActual(
            scope, "P-B", "B", "P1", actual_cost=Decimal("500"), currency="USD"
        )
    )

    expenses = SQLiteP6ExpenseRepository(connection)
    for row in (
        P6Expense(
            scope, "E-A", "Activity expense", "cost", activity_id="A",
            actual_cost=Decimal("50"), remaining_cost=Decimal("400"), currency="USD",
        ),
        P6Expense(
            scope, "E-B", "Completed expense", "cost", activity_id="B",
            actual_cost=None, remaining_cost=Decimal("0"), currency="USD",
        ),
        P6Expense(
            scope, "E-W1", "WBS expense", "cost", wbs_id="W-1",
            actual_cost=Decimal("25"), remaining_cost=Decimal("100"), currency="USD",
        ),
    ):
        expenses.upsert(row)

    service = P6EarnedValueReadModelService(
        baseline_activities=baseline_activities,
        activities=activities,
        actuals=actuals,
        expenses=expenses,
        resolver=WorkingTimeResolver(
            WorkingCalendar(
                working_weekdays=frozenset({0, 1, 2, 3, 4}),
                holidays=frozenset(),
            )
        ),
    )

    result = service.read(
        scope, "B-1", data_date=date(2026, 11, 4), currency="USD"
    ).result

    assert result.earned_value.planned_value == Decimal("600.00")
    assert result.earned_value.earned_value == Decimal("1000.00")
    assert result.earned_value.actual_cost == Decimal("875")
    assert result.earned_value.budget_at_completion == Decimal("1500")
    assert result.earned_value.estimate_to_complete == Decimal("500")
    assert result.earned_value.estimate_at_completion == Decimal("1375")
    assert result.earned_value.variance_at_completion == Decimal("125")
    assert [row.wbs_id for row in result.wbs_rollups] == ["W-1", "W-2"]
    assert [row.actual_cost for row in result.wbs_rollups] == [
        Decimal("375"), Decimal("500")
    ]


def _wbs_project(connection, scope):
    from construction_pm.wbs_master_repository import (
        SQLiteWBSMasterRepository,
        WBSMaster,
        WBSParentKind,
    )

    wbs = SQLiteWBSMasterRepository(connection)
    wbs.save(
        WBSMaster(
            scope, "W-ROOT", WBSParentKind.PROJECT, None, "1", "Project", 0
        )
    )
    wbs.save(
        WBSMaster(
            scope, "W-CHILD", WBSParentKind.WBS, "W-ROOT", "1.1", "Child", 0
        )
    )
    return wbs


def _evm_service(connection, scope, *, wbs_repository, wbs_id="W-CHILD"):
    from construction_pm.p6_earned_value_read_model import (
        P6EarnedValueReadModelService,
    )

    baselines = SQLiteP6BaselineRepository(connection)
    baselines.upsert(
        P6Baseline(
            scope, "B-1", "Approved Baseline", "PRIMARY", 3,
            "2026-11-01T10:00:00Z", None,
        )
    )
    baseline_activities = SQLiteP6BaselineActivityRepository(connection)
    baseline_activities.save_many(
        (
            P6BaselineActivity(
                scope, "B-1", "A", date(2026, 11, 2), date(2026, 11, 6),
                Decimal("1000"), "USD", "W-CHILD", "ACTIVITY_PERCENT_COMPLETE",
            ),
        )
    )
    activities = SQLiteActivityMasterRepository(connection)
    activities.save(
        ActivityMaster(
            scope=scope,
            activity_id="A",
            duration_value=Decimal("5"),
            duration_unit=DurationUnit.WORKING_DAY,
            actual_start=date(2026, 11, 2),
            percent_complete=10.0,
            status=ActivityStatus.IN_PROGRESS,
            wbs_id=wbs_id,
        )
    )
    expenses = SQLiteP6ExpenseRepository(connection)
    expenses.upsert(
        P6Expense(
            scope, "E-A", "Activity expense", "cost", activity_id="A",
            actual_cost=Decimal("100"), remaining_cost=Decimal("500"),
            currency="USD",
        )
    )
    return P6EarnedValueReadModelService(
        baseline_activities=baseline_activities,
        activities=activities,
        actuals=SQLiteP6ActivityPeriodActualRepository(connection),
        expenses=expenses,
        resolver=WorkingTimeResolver(
            WorkingCalendar(
                working_weekdays=frozenset({0, 1, 2, 3, 4}),
                holidays=frozenset(),
            )
        ),
        wbs_repository=wbs_repository,
    )


def test_persisted_wbs_override_inherits_to_descendant_activities():
    from construction_pm.p6_earned_value_read_model import P6EarnedValueSettings
    from construction_pm.scheduling.evm_source import (
        EarnedValueTechniqueOverride,
        EVM_TECHNIQUE_FIFTY_FIFTY,
    )

    scope = BackendScope("tenant-a", "project-a", 7)
    connection = sqlite3.connect(":memory:")
    wbs = _wbs_project(connection, scope)
    service = _evm_service(connection, scope, wbs_repository=wbs)

    result = service.read(
        scope,
        "B-1",
        data_date=date(2026, 11, 4),
        currency="USD",
        settings=P6EarnedValueSettings(
            technique_overrides=(
                EarnedValueTechniqueOverride("W-ROOT", EVM_TECHNIQUE_FIFTY_FIFTY),
            ),
        ),
    ).result

    # The activity stores Activity % Complete and 10%, but the persisted
    # ancestor WBS override earns it at 50% (started).
    assert result.activities[0].earned_value_technique == EVM_TECHNIQUE_FIFTY_FIFTY
    assert result.activities[0].earned_percent == Decimal("50")
    assert result.earned_value.earned_value == Decimal("500.00")
    assert result.wbs_rollups[0].earned_value == Decimal("500.00")


def test_persisted_weighted_milestones_earn_nearest_wbs_percentage():
    from construction_pm.p6_earned_value_read_model import P6EarnedValueSettings
    from construction_pm.scheduling.evm_source import (
        EVM_TECHNIQUE_WBS_MILESTONE,
        EarnedValueTechniqueOverride,
        EarnedValueWBSMilestone,
    )

    scope = BackendScope("tenant-a", "project-a", 7)
    connection = sqlite3.connect(":memory:")
    wbs = _wbs_project(connection, scope)
    service = _evm_service(connection, scope, wbs_repository=wbs)

    result = service.read(
        scope,
        "B-1",
        data_date=date(2026, 11, 4),
        currency="USD",
        settings=P6EarnedValueSettings(
            technique_overrides=(
                EarnedValueTechniqueOverride("W-CHILD", EVM_TECHNIQUE_WBS_MILESTONE),
            ),
            wbs_milestones=(
                EarnedValueWBSMilestone("W-CHILD", "M-1", Decimal("30"), True),
                EarnedValueWBSMilestone("W-CHILD", "M-2", Decimal("10"), False),
            ),
        ),
    ).result

    assert result.activities[0].earned_percent == Decimal("75")
    assert result.earned_value.earned_value == Decimal("750.00")


def test_wbs_settings_require_the_persisted_hierarchy():
    import pytest

    from construction_pm.p6_earned_value_read_model import (
        P6EarnedValueReadModelError,
        P6EarnedValueSettings,
    )
    from construction_pm.scheduling.evm_source import (
        EarnedValueTechniqueOverride,
        EVM_TECHNIQUE_FIFTY_FIFTY,
    )

    scope = BackendScope("tenant-a", "project-a", 7)
    connection = sqlite3.connect(":memory:")
    service = _evm_service(connection, scope, wbs_repository=None, wbs_id=None)

    with pytest.raises(
        P6EarnedValueReadModelError, match="EVM_WBS_REPOSITORY_REQUIRED"
    ):
        service.read(
            scope,
            "B-1",
            data_date=date(2026, 11, 4),
            currency="USD",
            settings=P6EarnedValueSettings(
                technique_overrides=(
                    EarnedValueTechniqueOverride("W-CHILD", EVM_TECHNIQUE_FIFTY_FIFTY),
                ),
            ),
        )
