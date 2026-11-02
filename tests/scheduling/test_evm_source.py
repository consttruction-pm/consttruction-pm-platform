from datetime import date, datetime
from decimal import Decimal

import pytest

from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.earned_value import (
    ETC_PF_CPI,
    ETC_REMAINING_COST,
)
from construction_pm.scheduling.evm_source import (
    EVM_PV_METHOD_LINEAR_WORKING_DAYS,
    EVM_TECHNIQUE_ACTIVITY_PERCENT_COMPLETE,
    EVM_TECHNIQUE_FIFTY_FIFTY,
    EVM_TECHNIQUE_WBS_MILESTONE,
    EVM_TECHNIQUE_ZERO_HUNDRED,
    BaselineValueActivity,
    EarnedValueCostAdjustment,
    EarnedValueProgress,
    EarnedValueSourceError,
    select_earned_value_sources,
)


def resolver() -> WorkingTimeResolver:
    return WorkingTimeResolver(
        WorkingCalendar(
            working_weekdays=frozenset({0, 1, 2, 3, 4}),
            holidays=frozenset(),
        )
    )


def baseline(
    activity_id: str,
    *,
    start: date,
    finish: date,
    budget: str,
    wbs_id: str | None = "W-1",
    technique: str = EVM_TECHNIQUE_ACTIVITY_PERCENT_COMPLETE,
    baseline_id: str = "B-1",
    currency: str = "USD",
) -> BaselineValueActivity:
    return BaselineValueActivity(
        baseline_id=baseline_id,
        activity_id=activity_id,
        planned_start=start,
        planned_finish=finish,
        budgeted_cost=Decimal(budget),
        currency=currency,
        wbs_id=wbs_id,
        earned_value_technique=technique,
    )


def progress(
    activity_id: str,
    *,
    percent: str = "0",
    started: bool = False,
    completed: bool = False,
    actual_cost: str = "0",
    remaining_cost: str | None = None,
    currency: str = "USD",
) -> EarnedValueProgress:
    return EarnedValueProgress(
        activity_id=activity_id,
        percent_complete=Decimal(percent),
        started=started,
        completed=completed,
        actual_cost=Decimal(actual_cost),
        currency=currency,
        remaining_cost=(
            None if remaining_cost is None else Decimal(remaining_cost)
        ),
    )


def test_selects_pv_ev_ac_and_bac_from_the_chosen_baseline_and_data_date():
    result = select_earned_value_sources(
        (
            baseline(
                "A",
                start=date(2026, 11, 2),
                finish=date(2026, 11, 6),
                budget="1000",
            ),
            baseline(
                "B",
                start=date(2026, 11, 9),
                finish=date(2026, 11, 13),
                budget="500",
                technique=EVM_TECHNIQUE_ZERO_HUNDRED,
            ),
        ),
        (
            progress(
                "A", percent="50", started=True, actual_cost="300",
                remaining_cost="400",
            ),
            progress("B", remaining_cost="500"),
        ),
        baseline_id="B-1",
        data_date=date(2026, 11, 4),
        currency="USD",
        resolver=resolver(),
    )

    assert result.pv_method == EVM_PV_METHOD_LINEAR_WORKING_DAYS
    assert [item.activity_id for item in result.activities] == ["A", "B"]
    first, second = result.activities
    # A runs Monday-Friday: Wednesday is the third of five working days.
    assert first.planned_percent == Decimal("60")
    assert first.planned_value == Decimal("600.00")
    assert first.earned_percent == Decimal("50")
    assert first.earned_value == Decimal("500.00")
    assert first.actual_cost == Decimal("300")
    assert first.budget_at_completion == Decimal("1000")
    # B starts after the Data Date and has not earned under 0/100.
    assert second.planned_percent == Decimal("0")
    assert second.planned_value == Decimal("0")
    assert second.earned_percent == Decimal("0")

    value = result.earned_value
    assert value.planned_value == Decimal("600.00")
    assert value.earned_value == Decimal("500.00")
    assert value.actual_cost == Decimal("300")
    assert value.cost_variance == Decimal("200.00")
    assert value.schedule_variance == Decimal("-100.00")
    assert value.estimate_to_complete == Decimal("900")
    assert value.estimate_at_completion == Decimal("1200")
    assert value.variance_at_completion == Decimal("300")

    assert len(result.wbs_rollups) == 1
    rollup = result.wbs_rollups[0]
    assert rollup.wbs_id == "W-1"
    assert rollup.activity_count == 2
    assert rollup.planned_value == Decimal("600.00")
    assert rollup.earned_value == Decimal("500.00")
    assert rollup.actual_cost == Decimal("300")
    assert rollup.budget_at_completion == Decimal("1500")


def test_data_date_on_a_weekend_measures_through_the_previous_working_day():
    result = select_earned_value_sources(
        (
            baseline(
                "A",
                start=date(2026, 11, 2),
                finish=date(2026, 11, 13),
                budget="1000",
            ),
        ),
        (progress("A", percent="10", started=True, actual_cost="100", remaining_cost="0"),),
        baseline_id="B-1",
        data_date=date(2026, 11, 7),  # Saturday
        currency="USD",
        resolver=resolver(),
    )

    assert result.activities[0].planned_percent == Decimal("50")
    assert result.activities[0].planned_value == Decimal("500.00")


def test_zero_hundred_and_fifty_fifty_use_actual_start_and_finish():
    result = select_earned_value_sources(
        (
            baseline(
                "ZERO", start=date(2026, 11, 2), finish=date(2026, 11, 6),
                budget="100", technique=EVM_TECHNIQUE_ZERO_HUNDRED,
            ),
            baseline(
                "HALF", start=date(2026, 11, 2), finish=date(2026, 11, 6),
                budget="100", technique=EVM_TECHNIQUE_FIFTY_FIFTY,
            ),
            baseline(
                "DONE", start=date(2026, 11, 2), finish=date(2026, 11, 6),
                budget="100", technique=EVM_TECHNIQUE_FIFTY_FIFTY,
            ),
        ),
        (
            progress("ZERO", percent="90", started=True, actual_cost="50", remaining_cost="0"),
            progress("HALF", percent="20", started=True, actual_cost="20", remaining_cost="0"),
            progress(
                "DONE", percent="100", started=True, completed=True,
                actual_cost="100", remaining_cost="0",
            ),
        ),
        baseline_id="B-1",
        data_date=date(2026, 11, 4),
        currency="USD",
        resolver=resolver(),
    )

    by_id = {item.activity_id: item for item in result.activities}
    assert by_id["ZERO"].earned_percent == Decimal("0")
    assert by_id["HALF"].earned_percent == Decimal("50")
    assert by_id["DONE"].earned_percent == Decimal("100")
    # The selected technique wins; stored percent does not override 0/100.
    assert result.earned_value.earned_value == Decimal("150.00")


def test_performance_factor_estimator_uses_selected_sources_without_remaining_cost():
    result = select_earned_value_sources(
        (
            baseline(
                "A", start=date(2026, 11, 2), finish=date(2026, 11, 6),
                budget="1500",
            ),
        ),
        (progress("A", percent="50", started=True, actual_cost="300"),),
        baseline_id="B-1",
        data_date=date(2026, 11, 4),
        currency="USD",
        resolver=resolver(),
        etc_method=ETC_PF_CPI,
    )

    assert result.earned_value.etc_method == ETC_PF_CPI
    assert result.earned_value.estimate_to_complete == Decimal("300")
    assert result.earned_value.estimate_at_completion == Decimal("600")


def test_wbs_rollup_keeps_unassigned_activities_in_their_own_bucket():
    result = select_earned_value_sources(
        (
            baseline(
                "A", start=date(2026, 11, 2), finish=date(2026, 11, 6),
                budget="100", wbs_id="W-1",
            ),
            baseline(
                "B", start=date(2026, 11, 2), finish=date(2026, 11, 6),
                budget="200", wbs_id=None,
            ),
        ),
        (
            progress("A", percent="100", started=True, completed=True, actual_cost="100", remaining_cost="0"),
            progress("B", percent="50", started=True, actual_cost="50", remaining_cost="0"),
        ),
        baseline_id="B-1",
        data_date=date(2026, 11, 6),
        currency="USD",
        resolver=resolver(),
    )

    assert [(item.wbs_id, item.activity_count) for item in result.wbs_rollups] == [
        ("W-1", 1),
        (None, 1),
    ]


@pytest.mark.parametrize(
    ("changes", "error"),
    (
        ({"baseline_id": "B-2"}, "EVM_BASELINE_SELECTION_MISMATCH"),
        ({"currency": "EUR"}, "EVM_BASELINE_CURRENCY_MISMATCH"),
        ({"planned_start": date(2026, 11, 1)}, "EVM_BASELINE_NON_WORKING_DATE"),
    ),
)
def test_baseline_selection_and_calendar_errors_fail_closed(changes, error):
    item = baseline(
        "A", start=date(2026, 11, 2), finish=date(2026, 11, 6), budget="100"
    )
    broken = BaselineValueActivity(
        baseline_id=changes.get("baseline_id", item.baseline_id),
        activity_id="A",
        planned_start=changes.get("planned_start", item.planned_start),
        planned_finish=changes.get("planned_finish", item.planned_finish),
        budgeted_cost=item.budgeted_cost,
        currency=changes.get("currency", item.currency),
        wbs_id="W-1",
        earned_value_technique=item.earned_value_technique,
    )
    with pytest.raises(EarnedValueSourceError, match=error):
        select_earned_value_sources(
            (broken,),
            (progress("A"),),
            baseline_id="B-1",
            data_date=date(2026, 11, 4),
            currency="USD",
            resolver=resolver(),
        )


def test_invalid_baseline_window_is_rejected_at_construction():
    with pytest.raises(EarnedValueSourceError, match="EVM_BASELINE_PLANNED_WINDOW_INVALID"):
        baseline(
            "A", start=date(2026, 11, 2), finish=date(2026, 10, 30), budget="100"
        )


def test_duplicate_rows_and_orphaned_or_missing_progress_fail_closed():
    item = baseline(
        "A", start=date(2026, 11, 2), finish=date(2026, 11, 6), budget="100"
    )
    with pytest.raises(EarnedValueSourceError, match="EVM_DUPLICATE_BASELINE_ACTIVITY"):
        select_earned_value_sources(
            (item, item), (progress("A"),),
            baseline_id="B-1", data_date=date(2026, 11, 4),
            currency="USD", resolver=resolver(),
        )
    with pytest.raises(
        EarnedValueSourceError, match="EVM_PROGRESS_ACTIVITY_NOT_IN_BASELINE"
    ):
        select_earned_value_sources(
            (item,), (progress("A"), progress("OTHER")),
            baseline_id="B-1", data_date=date(2026, 11, 4),
            currency="USD", resolver=resolver(),
        )
    with pytest.raises(
        EarnedValueSourceError, match="EVM_PROGRESS_MISSING_FOR_BASELINE_ACTIVITY"
    ):
        select_earned_value_sources(
            (item,), (), baseline_id="B-1", data_date=date(2026, 11, 4),
            currency="USD", resolver=resolver(),
        )


def test_wbs_milestone_requires_facts_instead_of_approximating():
    with pytest.raises(EarnedValueSourceError, match="EVM_WBS_MILESTONE_FACTS_REQUIRED"):
        select_earned_value_sources(
            (
                baseline(
                    "A", start=date(2026, 11, 2), finish=date(2026, 11, 6),
                    budget="100", technique=EVM_TECHNIQUE_WBS_MILESTONE,
                ),
            ),
            (progress("A", percent="50", started=True),),
            baseline_id="B-1", data_date=date(2026, 11, 4),
            currency="USD", resolver=resolver(),
        )


def test_remaining_cost_estimator_requires_every_remaining_value():
    with pytest.raises(
        EarnedValueSourceError, match="EARNED_VALUE_REMAINING_COST_REQUIRED"
    ):
        select_earned_value_sources(
            (
                baseline(
                    "A", start=date(2026, 11, 2), finish=date(2026, 11, 6),
                    budget="100",
                ),
            ),
            (progress("A", percent="50", started=True, actual_cost="50"),),
            baseline_id="B-1", data_date=date(2026, 11, 4),
            currency="USD", resolver=resolver(),
            etc_method=ETC_REMAINING_COST,
        )


def test_invalid_period_and_progress_states_are_rejected():
    with pytest.raises(EarnedValueSourceError, match="EVM_DATA_DATE_INVALID"):
        select_earned_value_sources(
            (
                baseline(
                    "A", start=date(2026, 11, 2), finish=date(2026, 11, 6),
                    budget="100",
                ),
            ),
            (progress("A"),),
            baseline_id="B-1", data_date=datetime(2026, 11, 4, 10, 0),
            currency="USD", resolver=resolver(),
        )
    with pytest.raises(EarnedValueSourceError, match="EVM_PROGRESS_COMPLETED_REQUIRES_START"):
        progress("A", percent="100", completed=True)
    with pytest.raises(EarnedValueSourceError, match="EVM_PROGRESS_NOT_STARTED_REQUIRES_ZERO"):
        progress("A", percent="10")
    with pytest.raises(EarnedValueSourceError, match="EVM_PROGRESS_COMPLETED_REQUIRES_100"):
        progress("A", percent="50", started=True, completed=True)


def test_result_payload_is_canonical_and_includes_the_pv_method():
    result = select_earned_value_sources(
        (
            baseline(
                "A", start=date(2026, 11, 2), finish=date(2026, 11, 6),
                budget="100",
            ),
        ),
        (progress("A", percent="50", started=True, actual_cost="40"),),
        baseline_id="B-1", data_date=date(2026, 11, 4),
        currency="USD", resolver=resolver(),
        etc_method="PF_ONE",
    )

    payload = result.canonical_payload()
    assert payload["pv_method"] == EVM_PV_METHOD_LINEAR_WORKING_DAYS
    assert payload["data_date"] == "2026-11-04"
    assert Decimal(payload["activities"][0]["planned_value"]) == Decimal("60")
    assert payload["earned_value"]["etc_method"] == "PF_ONE"
    assert payload["cost_adjustments"] == []


def test_wbs_and_project_cost_adjustments_are_attributed_without_rebudgeting():
    result = select_earned_value_sources(
        (
            baseline(
                "A", start=date(2026, 11, 2), finish=date(2026, 11, 6),
                budget="1000", wbs_id="W-1",
            ),
        ),
        (progress("A", percent="50", started=True, actual_cost="100",
                  remaining_cost="300"),),
        baseline_id="B-1", data_date=date(2026, 11, 4),
        currency="USD", resolver=resolver(),
        cost_adjustments=(
            EarnedValueCostAdjustment("W-1", Decimal("25"), Decimal("100")),
            EarnedValueCostAdjustment(None, Decimal("75"), Decimal("50")),
        ),
    )

    assert result.earned_value.actual_cost == Decimal("200")
    assert result.earned_value.estimate_to_complete == Decimal("450")
    assert result.earned_value.estimate_at_completion == Decimal("650")
    assert result.earned_value.budget_at_completion == Decimal("1000")
    # The WBS adjustment is in its own rollup; the project adjustment is only
    # in the project total and must not be spread across activity/WBS rows.
    assert result.wbs_rollups[0].actual_cost == Decimal("125")
    assert result.wbs_rollups[0].budget_at_completion == Decimal("1000")


def test_cost_adjustment_must_reference_a_baseline_wbs():
    with pytest.raises(
        EarnedValueSourceError,
        match="EVM_COST_ADJUSTMENT_WBS_NOT_IN_BASELINE:W-9",
    ):
        select_earned_value_sources(
            (
                baseline(
                    "A", start=date(2026, 11, 2), finish=date(2026, 11, 6),
                    budget="100", wbs_id="W-1",
                ),
            ),
            (progress("A"),),
            baseline_id="B-1", data_date=date(2026, 11, 4),
            currency="USD", resolver=resolver(),
            cost_adjustments=(EarnedValueCostAdjustment("W-9", Decimal("5")),),
        )
