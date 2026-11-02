from datetime import date
from decimal import Decimal

import pytest

from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.evm_source import (
    EVM_PV_METHOD_LINEAR_WORKING_DAYS,
    EVM_PV_METHOD_MIXED,
    EVM_PV_METHOD_PERIOD_BUCKET,
    EVM_TECHNIQUE_ACTIVITY_PERCENT_COMPLETE,
    EVM_TECHNIQUE_FIFTY_FIFTY,
    EVM_TECHNIQUE_RESOURCE_CURVE,
    EVM_TECHNIQUE_WBS_MILESTONE,
    EVM_TECHNIQUE_ZERO_HUNDRED,
    BaselineValueActivity,
    EarnedValuePVBucket,
    EarnedValueProgress,
    EarnedValueSourceError,
    EarnedValueTechniqueOverride,
    EarnedValueWBSMilestone,
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
    ancestry: tuple[str, ...] = (),
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
        wbs_ancestry=ancestry,
        earned_value_technique=technique,
    )


def progress(
    activity_id: str,
    *,
    percent: str = "0",
    started: bool = False,
    completed: bool = False,
    actual_cost: str = "0",
    remaining_cost: str | None = "0",
    units_percent: str | None = None,
) -> EarnedValueProgress:
    return EarnedValueProgress(
        activity_id=activity_id,
        percent_complete=Decimal(percent),
        started=started,
        completed=completed,
        actual_cost=Decimal(actual_cost),
        currency="USD",
        remaining_cost=None if remaining_cost is None else Decimal(remaining_cost),
        units_percent_complete=(
            None if units_percent is None else Decimal(units_percent)
        ),
    )


def test_wbs_technique_overrides_apply_to_descendants_and_nearest_wins():
    result = select_earned_value_sources(
        (
            baseline(
                "CHILD",
                start=date(2026, 11, 2),
                finish=date(2026, 11, 6),
                budget="100",
                wbs_id="W-CHILD",
                ancestry=("W-ROOT",),
            ),
            baseline(
                "ROOT",
                start=date(2026, 11, 2),
                finish=date(2026, 11, 6),
                budget="200",
                wbs_id="W-SIBLING",
                ancestry=("W-ROOT",),
            ),
        ),
        (
            progress("CHILD", percent="20", started=True),
            progress("ROOT", percent="20", started=True),
        ),
        baseline_id="B-1",
        data_date=date(2026, 11, 4),
        currency="USD",
        resolver=resolver(),
        technique_overrides=(
            EarnedValueTechniqueOverride("W-ROOT", EVM_TECHNIQUE_FIFTY_FIFTY),
            EarnedValueTechniqueOverride("W-CHILD", EVM_TECHNIQUE_ZERO_HUNDRED),
        ),
    )

    by_id = {item.activity_id: item for item in result.activities}
    assert by_id["CHILD"].earned_value_technique == EVM_TECHNIQUE_ZERO_HUNDRED
    assert by_id["CHILD"].earned_percent == Decimal("0")
    assert by_id["ROOT"].earned_value_technique == EVM_TECHNIQUE_FIFTY_FIFTY
    assert by_id["ROOT"].earned_percent == Decimal("50")
    assert result.earned_value.earned_value == Decimal("100.00")


def test_weighted_wbs_milestones_earn_completed_weight_over_total_weight():
    result = select_earned_value_sources(
        (
            baseline(
                "A",
                start=date(2026, 11, 2),
                finish=date(2026, 11, 6),
                budget="1000",
                wbs_id="W-1",
                technique=EVM_TECHNIQUE_WBS_MILESTONE,
            ),
        ),
        (progress("A", percent="10", started=True),),
        baseline_id="B-1",
        data_date=date(2026, 11, 4),
        currency="USD",
        resolver=resolver(),
        wbs_milestones=(
            EarnedValueWBSMilestone("W-1", "M-1", Decimal("9"), True),
            EarnedValueWBSMilestone("W-1", "M-2", Decimal("1")),
            EarnedValueWBSMilestone("W-1", "M-3", Decimal("1")),
            EarnedValueWBSMilestone("W-1", "M-4", Decimal("1")),
        ),
    )

    activity = result.activities[0]
    # 9 completed of 12 total possible weight, per the documented formula.
    assert activity.earned_percent == Decimal("75")
    assert activity.earned_value == Decimal("750.00")
    assert result.earned_value.earned_value == Decimal("750.00")


def test_resource_curve_uses_units_percent_complete_instead_of_activity_percent():
    result = select_earned_value_sources(
        (
            baseline(
                "A",
                start=date(2026, 11, 2),
                finish=date(2026, 11, 6),
                budget="1000",
                wbs_id="W-1",
            ),
        ),
        (
            progress(
                "A", percent="10", started=True, actual_cost="100", units_percent="40"
            ),
        ),
        baseline_id="B-1",
        data_date=date(2026, 11, 4),
        currency="USD",
        resolver=resolver(),
        technique_overrides=(
            EarnedValueTechniqueOverride("W-1", EVM_TECHNIQUE_RESOURCE_CURVE),
        ),
    )

    assert result.activities[0].earned_value_technique == EVM_TECHNIQUE_RESOURCE_CURVE
    assert result.activities[0].earned_percent == Decimal("40")
    assert result.activities[0].earned_value == Decimal("400.00")


def test_resource_curve_requires_units_percent_complete():
    with pytest.raises(
        EarnedValueSourceError, match="EVM_UNITS_PERCENT_COMPLETE_REQUIRED"
    ):
        select_earned_value_sources(
            (
                baseline(
                    "A",
                    start=date(2026, 11, 2),
                    finish=date(2026, 11, 6),
                    budget="100",
                    wbs_id="W-1",
                ),
            ),
            (progress("A", percent="10", started=True),),
            baseline_id="B-1",
            data_date=date(2026, 11, 4),
            currency="USD",
            resolver=resolver(),
            technique_overrides=(
                EarnedValueTechniqueOverride("W-1", EVM_TECHNIQUE_RESOURCE_CURVE),
            ),
        )


def test_manual_future_period_buckets_control_pv_and_report_the_method():
    result = select_earned_value_sources(
        (
            baseline(
                "A",
                start=date(2026, 11, 2),
                finish=date(2026, 12, 31),
                budget="1000",
                wbs_id="W-1",
            ),
            baseline(
                "B",
                start=date(2026, 11, 2),
                finish=date(2026, 11, 6),
                budget="500",
                wbs_id="W-1",
            ),
        ),
        (
            progress("A", percent="10", started=True),
            progress("B", percent="10", started=True),
        ),
        baseline_id="B-1",
        data_date=date(2026, 11, 30),
        currency="USD",
        resolver=resolver(),
        pv_buckets=(
            EarnedValuePVBucket(
                "A", date(2026, 11, 2), date(2026, 11, 30), Decimal("400")
            ),
            EarnedValuePVBucket(
                "A", date(2026, 12, 1), date(2026, 12, 31), Decimal("600")
            ),
        ),
    )

    by_id = {item.activity_id: item for item in result.activities}
    assert by_id["A"].planned_value == Decimal("400")
    assert by_id["A"].planned_percent == Decimal("40")
    assert by_id["A"].planned_value_method == EVM_PV_METHOD_PERIOD_BUCKET
    assert by_id["B"].planned_value_method == EVM_PV_METHOD_LINEAR_WORKING_DAYS
    assert result.pv_method == EVM_PV_METHOD_MIXED


def test_future_period_bucket_accrues_linearly_inside_an_open_period():
    result = select_earned_value_sources(
        (
            baseline(
                "A",
                start=date(2026, 11, 2),
                finish=date(2026, 12, 31),
                budget="1000",
                wbs_id="W-1",
            ),
        ),
        (progress("A", percent="10", started=True),),
        baseline_id="B-1",
        data_date=date(2026, 12, 15),
        currency="USD",
        resolver=resolver(),
        pv_buckets=(
            EarnedValuePVBucket(
                "A", date(2026, 11, 2), date(2026, 11, 30), Decimal("400")
            ),
            EarnedValuePVBucket(
                "A", date(2026, 12, 1), date(2026, 12, 31), Decimal("600")
            ),
        ),
    )

    activity = result.activities[0]
    # Closed November bucket plus 14 of 30 December days.
    assert activity.planned_value == Decimal("680")
    assert result.pv_method == EVM_PV_METHOD_PERIOD_BUCKET


@pytest.mark.parametrize(
    ("buckets", "error"),
    (
        (
            (
                EarnedValuePVBucket(
                    "A", date(2026, 11, 2), date(2026, 11, 30), Decimal("100")
                ),
            ),
            "EVM_PV_BUCKETS_DO_NOT_RECONCILE:A",
        ),
        (
            (
                EarnedValuePVBucket(
                    "A", date(2026, 11, 2), date(2026, 11, 30), Decimal("500")
                ),
                EarnedValuePVBucket(
                    "A", date(2026, 11, 30), date(2026, 12, 31), Decimal("500")
                ),
            ),
            "EVM_PV_BUCKETS_OVERLAP:A",
        ),
        (
            (
                EarnedValuePVBucket(
                    "A", date(2026, 10, 1), date(2026, 10, 31), Decimal("1000")
                ),
            ),
            "EVM_PV_BUCKET_OUTSIDE_BASELINE_WINDOW:A",
        ),
        (
            (
                EarnedValuePVBucket(
                    "OTHER", date(2026, 11, 2), date(2026, 12, 31), Decimal("1000")
                ),
            ),
            "EVM_PV_BUCKET_ACTIVITY_NOT_IN_BASELINE:OTHER",
        ),
    ),
)
def test_pv_bucket_validation_fails_closed(buckets, error):
    with pytest.raises(EarnedValueSourceError, match=error):
        select_earned_value_sources(
            (
                baseline(
                    "A",
                    start=date(2026, 11, 2),
                    finish=date(2026, 12, 31),
                    budget="1000",
                    wbs_id="W-1",
                ),
            ),
            (progress("A", percent="10", started=True),),
            baseline_id="B-1",
            data_date=date(2026, 11, 4),
            currency="USD",
            resolver=resolver(),
            pv_buckets=buckets,
        )


def test_wbs_settings_must_reference_baseline_wbs_and_be_unique():
    item = baseline(
        "A",
        start=date(2026, 11, 2),
        finish=date(2026, 11, 6),
        budget="100",
        wbs_id="W-1",
    )
    base_kwargs = dict(
        baseline_id="B-1",
        data_date=date(2026, 11, 4),
        currency="USD",
        resolver=resolver(),
    )
    with pytest.raises(
        EarnedValueSourceError,
        match="EVM_TECHNIQUE_OVERRIDE_WBS_NOT_IN_BASELINE:W-9",
    ):
        select_earned_value_sources(
            (item,),
            (progress("A"),),
            technique_overrides=(
                EarnedValueTechniqueOverride("W-9", EVM_TECHNIQUE_ZERO_HUNDRED),
            ),
            **base_kwargs,
        )
    with pytest.raises(
        EarnedValueSourceError, match="EVM_DUPLICATE_TECHNIQUE_OVERRIDE"
    ):
        select_earned_value_sources(
            (item,),
            (progress("A"),),
            technique_overrides=(
                EarnedValueTechniqueOverride("W-1", EVM_TECHNIQUE_ZERO_HUNDRED),
                EarnedValueTechniqueOverride("W-1", EVM_TECHNIQUE_FIFTY_FIFTY),
            ),
            **base_kwargs,
        )
    with pytest.raises(
        EarnedValueSourceError, match="EVM_WBS_MILESTONE_WBS_NOT_IN_BASELINE:W-9"
    ):
        select_earned_value_sources(
            (item,),
            (progress("A"),),
            wbs_milestones=(EarnedValueWBSMilestone("W-9", "M-1", Decimal("1")),),
            **base_kwargs,
        )
    with pytest.raises(
        EarnedValueSourceError, match="EVM_DUPLICATE_WBS_MILESTONE"
    ):
        select_earned_value_sources(
            (item,),
            (progress("A"),),
            wbs_milestones=(
                EarnedValueWBSMilestone("W-1", "M-1", Decimal("1")),
                EarnedValueWBSMilestone("W-1", "M-1", Decimal("2")),
            ),
            **base_kwargs,
        )
    with pytest.raises(
        EarnedValueSourceError, match="EVM_WBS_MILESTONE_WEIGHT_INVALID"
    ):
        EarnedValueWBSMilestone("W-1", "M-1", Decimal("0"))
