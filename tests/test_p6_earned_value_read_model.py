from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from construction_pm.activity_master_repository import ActivityMaster
from construction_pm.application.authorization import (
    AuthorizationContext,
    default_project_policy,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_activity_period_actual_repository import P6ActivityPeriodActual
from construction_pm.p6_baseline_activity_repository import P6BaselineActivity
from construction_pm.p6_earned_value_read_model import (
    P6_EARNED_VALUE_READ_MODEL_VERSION,
    P6EarnedValueReadModelError,
    P6EarnedValueReadModelService,
)
from construction_pm.p6_earned_value_read_model_api import P6EarnedValueReadModelAPI
from construction_pm.p6_expense_repository import P6Expense
from construction_pm.scheduling.activity import ActivityStatus
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.evm_source import (
    EVM_TECHNIQUE_ACTIVITY_PERCENT_COMPLETE,
    EVM_TECHNIQUE_ZERO_HUNDRED,
)
from construction_pm.scheduling.time_duration import DurationUnit


def scope(revision: int = 7) -> BackendScope:
    return BackendScope("tenant-a", "project-a", revision)


def resolver() -> WorkingTimeResolver:
    return WorkingTimeResolver(
        WorkingCalendar(
            working_weekdays=frozenset({0, 1, 2, 3, 4}),
            holidays=frozenset(),
        )
    )


def baseline(
    activity_id: str,
    wbs_id: str,
    budget: str,
    *,
    start: date = date(2026, 11, 2),
    finish: date = date(2026, 11, 6),
    technique: str = EVM_TECHNIQUE_ACTIVITY_PERCENT_COMPLETE,
) -> P6BaselineActivity:
    return P6BaselineActivity(
        scope=scope(),
        baseline_id="B-1",
        activity_id=activity_id,
        planned_start=start,
        planned_finish=finish,
        budgeted_cost=Decimal(budget),
        currency="USD",
        wbs_id=wbs_id,
        earned_value_technique=technique,
    )


def current(
    activity_id: str,
    *,
    percent: float | None,
    status: ActivityStatus,
    actual_start: date | None = None,
    actual_finish: date | None = None,
) -> ActivityMaster:
    return ActivityMaster(
        scope=scope(),
        activity_id=activity_id,
        duration_value=Decimal("5"),
        duration_unit=DurationUnit.WORKING_DAY,
        actual_start=actual_start,
        percent_complete=percent,
        status=status,
        actual_finish=actual_finish,
    )


def actual(activity_id: str, cost: str, currency: str = "USD") -> P6ActivityPeriodActual:
    return P6ActivityPeriodActual(
        scope=scope(),
        actual_id=f"A-{activity_id}",
        activity_id=activity_id,
        period_id="P1",
        actual_cost=Decimal(cost),
        currency=currency,
    )


def expense(
    activity_id: str | None,
    remaining: str,
    currency: str = "USD",
    *,
    actual: str | None = None,
    wbs_id: str | None = None,
    expense_id: str | None = None,
) -> P6Expense:
    return P6Expense(
        scope=scope(),
        expense_id=expense_id or f"E-{activity_id or wbs_id or 'project'}",
        name="Remaining",
        category="cost",
        activity_id=activity_id,
        wbs_id=wbs_id,
        actual_cost=None if actual is None else Decimal(actual),
        remaining_cost=Decimal(remaining),
        currency=currency,
    )


def service(
    baselines,
    activities,
    actuals=(),
    expenses=(),
) -> P6EarnedValueReadModelService:
    sources = SimpleNamespace(
        list_baselines=lambda scope, baseline_id: tuple(baselines),
        list_activities=lambda scope: tuple(activities),
        list_actuals=lambda scope: tuple(actuals),
        list_expenses=lambda scope: tuple(expenses),
    )
    return P6EarnedValueReadModelService(
        baseline_activities=SimpleNamespace(
            list=sources.list_baselines
        ),
        activities=SimpleNamespace(list=sources.list_activities),
        actuals=SimpleNamespace(list=sources.list_actuals),
        expenses=SimpleNamespace(list=sources.list_expenses),
        resolver=resolver(),
    )


def test_read_model_selects_baseline_pv_ev_ac_and_bac_from_persisted_facts():
    svc = service(
        (
            baseline("A", "W-1", "1000"),
            baseline(
                "B",
                "W-2",
                "500",
                start=date(2026, 11, 9),
                finish=date(2026, 11, 13),
                technique=EVM_TECHNIQUE_ZERO_HUNDRED,
            ),
        ),
        (
            current(
                "A", percent=50.0, status=ActivityStatus.IN_PROGRESS,
                actual_start=date(2026, 11, 2),
            ),
            current(
                "B", percent=100.0, status=ActivityStatus.COMPLETED,
                actual_start=date(2026, 11, 9),
                actual_finish=date(2026, 11, 13),
            ),
        ),
        actuals=(actual("A", "300"), actual("B", "500")),
        expenses=(expense("A", "400"), expense("B", "0")),
    )

    result = svc.read(
        scope(),
        "B-1",
        data_date=date(2026, 11, 4),
        currency="USD",
    )

    assert P6_EARNED_VALUE_READ_MODEL_VERSION == "p6-earned-value-read-model.v1"
    assert result.result.pv_method == "LINEAR_WORKING_DAYS_ACTIVITY_BUDGET"
    assert result.result.earned_value.planned_value == Decimal("600.00")
    assert result.result.earned_value.earned_value == Decimal("1000.00")
    assert result.result.earned_value.actual_cost == Decimal("800")
    assert result.result.earned_value.budget_at_completion == Decimal("1500")
    assert result.result.earned_value.cost_variance == Decimal("200.00")
    assert result.result.earned_value.schedule_variance == Decimal("400.00")
    assert result.result.earned_value.estimate_to_complete == Decimal("400")
    assert result.result.earned_value.estimate_at_completion == Decimal("1200")
    assert result.result.earned_value.variance_at_completion == Decimal("300")
    assert [item.wbs_id for item in result.result.wbs_rollups] == ["W-1", "W-2"]

    payload = result.to_payload()
    assert payload["kind"] == "p6_earned_value_read_model"
    assert payload["scope"]["project_revision"] == 7
    assert payload["baseline_id"] == "B-1"
    assert payload["earned_value"]["estimate_at_completion"] == "1200"


def test_completed_activity_forces_full_earned_value_even_if_percent_is_stale():
    svc = service(
        (baseline("A", "W-1", "100"),),
        (
            current(
                "A", percent=40.0, status=ActivityStatus.COMPLETED,
                actual_start=date(2026, 11, 2),
                actual_finish=date(2026, 11, 6),
            ),
        ),
        actuals=(actual("A", "100"),),
        expenses=(expense("A", "0"),),
    )
    result = svc.read(
        scope(), "B-1", data_date=date(2026, 11, 6), currency="USD"
    )
    assert result.result.activities[0].earned_percent == Decimal("100")
    assert result.result.earned_value.earned_value == Decimal("100.00")


def test_missing_current_activity_and_currency_mismatch_fail_closed():
    svc = service((baseline("A", "W-1", "100"),), ())
    with pytest.raises(
        P6EarnedValueReadModelError, match="EVM_CURRENT_ACTIVITY_MISSING:A"
    ):
        svc.read(scope(), "B-1", data_date=date(2026, 11, 4), currency="USD")

    svc = service(
        (baseline("A", "W-1", "100"),),
        (current("A", percent=10.0, status=ActivityStatus.IN_PROGRESS,
                 actual_start=date(2026, 11, 2)),),
        actuals=(actual("A", "10", currency="EUR"),),
    )
    with pytest.raises(
        P6EarnedValueReadModelError, match="EVM_ACTUAL_CURRENCY_MISMATCH:A"
    ):
        svc.read(scope(), "B-1", data_date=date(2026, 11, 4), currency="USD")


def test_empty_baseline_and_duplicate_current_activity_fail_closed():
    with pytest.raises(
        P6EarnedValueReadModelError, match="EVM_BASELINE_ACTIVITIES_EMPTY:B-1"
    ):
        service((), ()).read(
            scope(), "B-1", data_date=date(2026, 11, 4), currency="USD"
        )

    duplicate = current(
        "A", percent=10.0, status=ActivityStatus.IN_PROGRESS,
        actual_start=date(2026, 11, 2),
    )
    with pytest.raises(
        P6EarnedValueReadModelError, match="EVM_DUPLICATE_CURRENT_ACTIVITY:A"
    ):
        service(
            (baseline("A", "W-1", "100"),), (duplicate, duplicate)
        ).read(scope(), "B-1", data_date=date(2026, 11, 4), currency="USD")


def test_api_enforces_scope_and_returns_the_read_model_payload():
    svc = service(
        (baseline("A", "W-1", "100"),),
        (
            current(
                "A", percent=50.0, status=ActivityStatus.IN_PROGRESS,
                actual_start=date(2026, 11, 2),
            ),
        ),
        actuals=(actual("A", "40"),),
        expenses=(expense("A", "60"),),
    )
    api = P6EarnedValueReadModelAPI(svc, default_project_policy())
    auth = AuthorizationContext(
        user_id="user-1",
        tenant_id="tenant-a",
        project_id="project-a",
        roles=frozenset({"viewer"}),
    )
    payload = api.get(
        scope(),
        "B-1",
        data_date=date(2026, 11, 4),
        currency="USD",
        auth_context=auth,
    )
    assert payload["contract_version"] == P6_EARNED_VALUE_READ_MODEL_VERSION
    assert Decimal(payload["earned_value"]["planned_value"]) == Decimal("60")

    with pytest.raises(PermissionError, match="CROSS_SCOPE_ACCESS"):
        api.get(
            scope(),
            "B-1",
            data_date=date(2026, 11, 4),
            currency="USD",
            auth_context=AuthorizationContext(
                user_id="user-1",
                tenant_id="tenant-b",
                project_id="project-a",
                roles=frozenset({"viewer"}),
            ),
        )


def test_api_rejects_datetime_status_date():
    api = P6EarnedValueReadModelAPI(service((), ()), default_project_policy())
    auth = AuthorizationContext(
        user_id="user-1",
        tenant_id="tenant-a",
        project_id="project-a",
        roles=frozenset({"viewer"}),
    )
    with pytest.raises(P6EarnedValueReadModelError, match="EVM_DATA_DATE_INVALID"):
        api.get(
            scope(),
            "B-1",
            data_date=datetime(2026, 11, 4, 9, 0),
            currency="USD",
            auth_context=auth,
        )


def test_expense_actual_cost_and_wbs_or_project_costs_are_not_dropped():
    svc = service(
        (baseline("A", "W-1", "1000"),),
        (
            current(
                "A", percent=50.0, status=ActivityStatus.IN_PROGRESS,
                actual_start=date(2026, 11, 2),
            ),
        ),
        actuals=(actual("A", "100"),),
        expenses=(
            expense("A", "300", actual="50", expense_id="E-A"),
            expense(None, "100", actual="25", wbs_id="W-1", expense_id="E-WBS"),
            expense(None, "50", actual="75", expense_id="E-PROJECT"),
        ),
    )

    result = svc.read(scope(), "B-1", data_date=date(2026, 11, 4), currency="USD")

    # AC includes period actuals plus activity, WBS and project expense actuals.
    assert result.result.earned_value.actual_cost == Decimal("250")
    assert result.result.earned_value.estimate_to_complete == Decimal("450")
    assert result.result.earned_value.estimate_at_completion == Decimal("700")
    assert result.result.earned_value.variance_at_completion == Decimal("300")
    # The WBS rollup includes its own expense, but not project-level cost.
    assert result.result.wbs_rollups[0].actual_cost == Decimal("175")
    assert len(result.result.cost_adjustments) == 2
    assert result.to_payload()["cost_adjustments"][0]["wbs_id"] == "W-1"


def test_cost_rows_outside_the_selected_baseline_fail_closed():
    common = (
        (baseline("A", "W-1", "100"),),
        (
            current(
                "A", percent=10.0, status=ActivityStatus.IN_PROGRESS,
                actual_start=date(2026, 11, 2),
            ),
        ),
    )
    with pytest.raises(
        P6EarnedValueReadModelError,
        match="EVM_ACTUAL_ACTIVITY_NOT_IN_BASELINE:B",
    ):
        service(*common, actuals=(actual("B", "10"),)).read(
            scope(), "B-1", data_date=date(2026, 11, 4), currency="USD"
        )

    with pytest.raises(
        P6EarnedValueReadModelError,
        match="EVM_EXPENSE_ACTIVITY_NOT_IN_BASELINE:B",
    ):
        service(*common, expenses=(expense("B", "10"),)).read(
            scope(), "B-1", data_date=date(2026, 11, 4), currency="USD"
        )

    with pytest.raises(
        P6EarnedValueReadModelError,
        match="EVM_COST_ADJUSTMENT_WBS_NOT_IN_BASELINE:W-9",
    ):
        service(
            *common,
            expenses=(expense(None, "10", wbs_id="W-9"),),
        ).read(scope(), "B-1", data_date=date(2026, 11, 4), currency="USD")


def test_missing_remaining_cost_for_unfinished_work_fails_closed_but_completed_is_zero():
    svc = service(
        (baseline("A", "W-1", "100"),),
        (
            current(
                "A", percent=50.0, status=ActivityStatus.IN_PROGRESS,
                actual_start=date(2026, 11, 2),
            ),
        ),
        actuals=(actual("A", "40"),),
    )
    with pytest.raises(
        P6EarnedValueReadModelError, match="EARNED_VALUE_REMAINING_COST_REQUIRED"
    ):
        svc.read(scope(), "B-1", data_date=date(2026, 11, 4), currency="USD")

    completed = service(
        (baseline("A", "W-1", "100"),),
        (
            current(
                "A", percent=100.0, status=ActivityStatus.COMPLETED,
                actual_start=date(2026, 11, 2),
                actual_finish=date(2026, 11, 6),
            ),
        ),
        actuals=(actual("A", "90"),),
    ).read(scope(), "B-1", data_date=date(2026, 11, 6), currency="USD")
    assert completed.result.earned_value.estimate_to_complete == Decimal("0")
    assert completed.result.earned_value.estimate_at_completion == Decimal("90")


def test_api_passes_wbs_settings_to_the_authoritative_service():
    from construction_pm.p6_earned_value_read_model import P6EarnedValueSettings
    from construction_pm.scheduling.evm_source import (
        EVM_TECHNIQUE_FIFTY_FIFTY,
        EarnedValueTechniqueOverride,
    )
    from construction_pm.wbs_master_repository import WBSMaster, WBSParentKind

    svc = P6EarnedValueReadModelService(
        baseline_activities=SimpleNamespace(
            list=lambda scope, baseline_id: (baseline("A", "W-1", "1000"),)
        ),
        activities=SimpleNamespace(
            list=lambda scope: (
                current(
                    "A", percent=10.0, status=ActivityStatus.IN_PROGRESS,
                    actual_start=date(2026, 11, 2),
                ),
            )
        ),
        actuals=SimpleNamespace(list=lambda scope: ()),
        expenses=SimpleNamespace(
            list=lambda scope: (expense("A", "0", actual="100"),)
        ),
        resolver=resolver(),
        wbs_repository=SimpleNamespace(
            list=lambda scope: (
                WBSMaster(
                    scope, "W-ROOT", WBSParentKind.PROJECT, None, "1", "Root", 0
                ),
                WBSMaster(
                    scope, "W-1", WBSParentKind.WBS, "W-ROOT", "1.1", "Child", 0
                ),
            )
        ),
    )
    api = P6EarnedValueReadModelAPI(svc, default_project_policy())
    payload = api.get(
        scope(),
        "B-1",
        data_date=date(2026, 11, 4),
        currency="USD",
        auth_context=AuthorizationContext(
            user_id="user-1",
            tenant_id="tenant-a",
            project_id="project-a",
            roles=frozenset({"viewer"}),
        ),
        settings=P6EarnedValueSettings(
            technique_overrides=(
                EarnedValueTechniqueOverride("W-ROOT", EVM_TECHNIQUE_FIFTY_FIFTY),
            ),
        ),
    )
    assert payload["activities"][0]["earned_value_technique"] == (
        EVM_TECHNIQUE_FIFTY_FIFTY
    )
    assert Decimal(payload["earned_value"]["earned_value"]) == Decimal("500.00")
