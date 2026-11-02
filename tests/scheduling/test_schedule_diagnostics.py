from datetime import date

import pytest

from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.constraints import (
    ActivityConstraint,
    ConstraintType,
    ConstraintViolation,
)
from construction_pm.scheduling.diagnostics import (
    INFEASIBILITY_MATRIX,
    ScheduleDiagnosticCode,
    ScheduleDiagnosticSeverity,
    ScheduleInfeasibilityError,
)
from construction_pm.scheduling.forward_pass import SchedulingCycleError, forward_pass
from construction_pm.scheduling.relationships import Relationship, RelationshipType
from construction_pm.scheduling.schedule import schedule


@pytest.fixture
def resolver():
    return WorkingTimeResolver(WorkingCalendar())


def _code(exc: BaseException) -> ScheduleDiagnosticCode:
    assert isinstance(exc, ScheduleInfeasibilityError)
    return exc.code


def test_infeasibility_matrix_is_unique_and_covers_every_code():
    codes = [case.code for case in INFEASIBILITY_MATRIX]
    assert len(codes) == len(set(codes))
    # Every declared code has exactly one documented condition.
    assert set(codes) == set(ScheduleDiagnosticCode)
    negative = next(
        case for case in INFEASIBILITY_MATRIX
        if case.code is ScheduleDiagnosticCode.NEGATIVE_FLOAT
    )
    assert negative.fail_closed is False


def test_duplicate_activity_ids_fail_closed_with_stable_code(resolver):
    with pytest.raises(ScheduleInfeasibilityError) as caught:
        forward_pass(
            [Activity("A", 1), Activity("A", 2)],
            [],
            date(2026, 11, 2),
            resolver,
        )
    assert _code(caught.value) is ScheduleDiagnosticCode.DUPLICATE_ACTIVITY_ID


def test_unknown_relationship_reference_fails_closed_with_stable_code(resolver):
    with pytest.raises(ScheduleInfeasibilityError) as caught:
        forward_pass(
            [Activity("A", 1)],
            [Relationship("A", "MISSING", RelationshipType.FS)],
            date(2026, 11, 2),
            resolver,
        )
    assert _code(caught.value) is ScheduleDiagnosticCode.UNKNOWN_ACTIVITY_REFERENCE
    assert caught.value.diagnostic.successor_id == "MISSING"


def test_unknown_constraint_reference_fails_closed_with_stable_code(resolver):
    with pytest.raises(ScheduleInfeasibilityError) as caught:
        forward_pass(
            [Activity("A", 1)],
            [],
            date(2026, 11, 2),
            resolver,
            constraints=[
                ActivityConstraint("MISSING", ConstraintType.START_NO_EARLIER_THAN, date(2026, 11, 3))
            ],
        )
    assert _code(caught.value) is ScheduleDiagnosticCode.UNKNOWN_ACTIVITY_REFERENCE


def test_network_cycle_has_stable_code(resolver):
    with pytest.raises(SchedulingCycleError) as caught:
        forward_pass(
            [Activity("A", 1), Activity("B", 1)],
            [
                Relationship("A", "B", RelationshipType.FS),
                Relationship("B", "A", RelationshipType.FS),
            ],
            date(2026, 11, 2),
            resolver,
        )
    assert _code(caught.value) is ScheduleDiagnosticCode.NETWORK_CYCLE


def test_crossing_constraint_window_has_stable_code(resolver):
    with pytest.raises(ConstraintViolation) as caught:
        schedule(
            [Activity("A", 1)],
            [],
            date(2026, 11, 2),
            resolver,
            constraints=[
                ActivityConstraint("A", ConstraintType.START_NO_EARLIER_THAN, date(2026, 11, 5)),
                ActivityConstraint("A", ConstraintType.START_NO_LATER_THAN, date(2026, 11, 3)),
            ],
        )
    assert _code(caught.value) is ScheduleDiagnosticCode.CONSTRAINT_WINDOW_EMPTY


def test_conflicting_mandatory_dates_have_stable_code(resolver):
    with pytest.raises(ConstraintViolation) as caught:
        schedule(
            [Activity("A", 1)],
            [],
            date(2026, 11, 2),
            resolver,
            constraints=[
                ActivityConstraint("A", ConstraintType.MANDATORY_START, date(2026, 11, 3)),
                ActivityConstraint("A", ConstraintType.MANDATORY_START, date(2026, 11, 4)),
            ],
        )
    assert _code(caught.value) is ScheduleDiagnosticCode.CONSTRAINT_MANDATORY_CONFLICT


def test_unsatisfiable_mandatory_finish_has_stable_code(resolver):
    with pytest.raises(ConstraintViolation) as caught:
        schedule(
            [Activity("A", 2), Activity("B", 1)],
            [Relationship("A", "B", RelationshipType.FS)],
            date(2026, 11, 2),
            resolver,
            constraints=[
                ActivityConstraint("A", ConstraintType.MANDATORY_FINISH, date(2026, 11, 2))
            ],
        )
    assert _code(caught.value) is ScheduleDiagnosticCode.CONSTRAINT_MANDATORY_UNSATISFIABLE


def test_upper_bound_violation_has_stable_code(resolver):
    with pytest.raises(ConstraintViolation) as caught:
        schedule(
            [Activity("A", 3)],
            [],
            date(2026, 11, 2),
            resolver,
            constraints=[
                ActivityConstraint("A", ConstraintType.FINISH_NO_LATER_THAN, date(2026, 11, 2))
            ],
        )
    assert _code(caught.value) is ScheduleDiagnosticCode.CONSTRAINT_UPPER_BOUND_VIOLATED


def test_negative_float_is_reported_without_rewriting_dates(resolver):
    result = schedule(
        [Activity("A", 5)],
        [],
        date(2026, 11, 2),
        resolver,
        project_finish=date(2026, 11, 4),
    )

    # The impossible finish is reported, not silently moved: early dates keep
    # their computed values and the late dates expose the negative float.
    assert result.activities["A"].start == date(2026, 11, 2)
    assert result.activities["A"].finish == date(2026, 11, 6)
    assert result.floats["A"].late_finish == date(2026, 11, 4)
    assert result.floats["A"].total_float == -2
    finding = next(
        item for item in result.diagnostics
        if item.code is ScheduleDiagnosticCode.NEGATIVE_FLOAT
    )
    assert finding.activity_id == "A"
    assert finding.severity is ScheduleDiagnosticSeverity.WARNING
    assert finding.to_payload()["code"] == "NEGATIVE_FLOAT"


def test_feasible_schedule_has_no_error_diagnostics(resolver):
    result = schedule(
        [Activity("A", 2), Activity("B", 1)],
        [Relationship("A", "B", RelationshipType.FS)],
        date(2026, 11, 2),
        resolver,
    )
    assert result.diagnostics == ()


def test_driving_relationship_filter_reports_unknown_reference(resolver):
    from construction_pm.scheduling.forward_pass import driving_relationships

    with pytest.raises(ScheduleInfeasibilityError) as caught:
        driving_relationships(
            [Activity("A", 1)],
            [Relationship("MISSING", "A", RelationshipType.FS)],
        )
    assert _code(caught.value) is ScheduleDiagnosticCode.UNKNOWN_ACTIVITY_REFERENCE
    assert caught.value.diagnostic.predecessor_id == "MISSING"


def test_out_of_sequence_ss_without_data_date_has_stable_code(resolver):
    from construction_pm.scheduling.forward_pass import (
        ScheduledActivity,
        _successor_start,
    )

    predecessor = ScheduledActivity(
        activity_id="A",
        start=date(2026, 11, 2),
        finish=date(2026, 11, 3),
        duration=2,
    )
    predecessor_activity = Activity(
        "A", 2, actual_start=date(2026, 11, 5), remaining_duration=2
    )

    with pytest.raises(ScheduleInfeasibilityError) as caught:
        _successor_start(
            Relationship("A", "B", RelationshipType.SS),
            predecessor,
            1,
            resolver,
            predecessor_activity,
            data_date=None,
        )
    assert _code(caught.value) is ScheduleDiagnosticCode.INVALID_DATA_DATE
    assert caught.value.diagnostic.predecessor_id == "A"


def test_out_of_sequence_ss_with_data_date_before_actual_start_has_stable_code(resolver):
    from construction_pm.scheduling.forward_pass import (
        ScheduledActivity,
        _successor_start,
    )

    predecessor = ScheduledActivity(
        activity_id="A",
        start=date(2026, 11, 2),
        finish=date(2026, 11, 3),
        duration=2,
    )
    predecessor_activity = Activity(
        "A", 2, actual_start=date(2026, 11, 5), remaining_duration=2
    )

    with pytest.raises(ScheduleInfeasibilityError) as caught:
        _successor_start(
            Relationship("A", "B", RelationshipType.SS),
            predecessor,
            1,
            resolver,
            predecessor_activity,
            data_date=date(2026, 11, 4),
        )
    assert _code(caught.value) is ScheduleDiagnosticCode.INVALID_DATA_DATE
