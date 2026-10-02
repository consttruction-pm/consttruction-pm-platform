from datetime import date
from decimal import Decimal

import pytest

from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.authoritative_schedule import (
    ActivityCalendarAssignment,
    AuthoritativeScheduleInput,
    AuthoritativeScheduleMode,
)
from construction_pm.scheduling.authoritative_schedule_batch import (
    UnsupportedMultiProjectSchedulingError,
    execute_authoritative_schedule_batch,
)
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.calendar_context import CalendarReference
from construction_pm.scheduling.external_resource_assignments import ExternalResourceAssignment
from construction_pm.scheduling.relationships import Relationship
from construction_pm.scheduling.schedule_options import ScheduleOptions


def snapshot(project_id, finish, *, options=None, priority=10):
    reference = CalendarReference('CAL', '1')
    return AuthoritativeScheduleInput(
        snapshot_id=f's-{project_id}',
        tenant_id='tenant',
        project_id=project_id,
        project_revision=1,
        project_leveling_priority=priority,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=reference,
        activities=(Activity(id=f'{project_id}-A', duration=1),),
        relationships=(),
        activity_calendar_assignments=(
            ActivityCalendarAssignment(f'{project_id}-A', reference),
        ),
        project_finish=finish,
        project_start=date(2026, 10, 1),
        schedule_options=options or ScheduleOptions(),
    )


def resolver():
    return WorkingTimeResolver(WorkingCalendar())


def test_batch_uses_each_project_finish_when_option_enabled():
    result = execute_authoritative_schedule_batch(
        [
            snapshot('P1', date(2026, 10, 10), options=ScheduleOptions(calculate_float_based_on_finish_date=True)),
            snapshot('P2', date(2026, 10, 20), options=ScheduleOptions(calculate_float_based_on_finish_date=True)),
        ],
        resolvers={'P1': resolver(), 'P2': resolver()},
    )
    assert result.project('P1').result.floats['P1-A'].total_float == 6
    assert result.project('P2').result.floats['P2-A'].total_float == 13


def test_batch_uses_latest_finish_when_option_disabled():
    result = execute_authoritative_schedule_batch(
        [
            snapshot('P1', date(2026, 10, 10)),
            snapshot('P2', date(2026, 10, 20)),
        ],
        resolvers={'P1': resolver(), 'P2': resolver()},
    )
    assert result.batch.finish_boundary_for('P1') == date(2026, 10, 20)
    assert result.project('P1').result.floats['P1-A'].total_float == 13


def test_cross_project_relationship_is_explicitly_unsupported_when_not_ignored():
    relationship = Relationship('P1-A', 'P2-A')
    with pytest.raises(UnsupportedMultiProjectSchedulingError, match='cross-project relationship execution'):
        execute_authoritative_schedule_batch(
            [
                snapshot('P1', date(2026, 10, 10)),
                snapshot('P2', date(2026, 10, 20)),
            ],
            resolvers={'P1': resolver(), 'P2': resolver()},
            external_relationships=(relationship,),
            activity_project_ids={'P1-A': 'P1', 'P2-A': 'P2'},
        )


def test_cross_project_relationship_is_ignored_when_option_enabled():
    options = ScheduleOptions(ignore_other_project_relationships=True)
    result = execute_authoritative_schedule_batch(
        [
            snapshot('P1', date(2026, 10, 10), options=options),
            snapshot('P2', date(2026, 10, 20), options=options),
        ],
        resolvers={'P1': resolver(), 'P2': resolver()},
        external_relationships=(Relationship('P1-A', 'P2-A'),),
        activity_project_ids={'P1-A': 'P1', 'P2-A': 'P2'},
    )
    assert len(result.projects) == 2


def assignment(project_id, resource_id):
    return ExternalResourceAssignment(
        project_id=project_id,
        resource_id=resource_id,
        period=date(2026, 10, 1),
        units=Decimal('1'),
        activity_id=f'{project_id}-A',
    )


@pytest.mark.parametrize(
    ('external_priority', 'expected_external'),
    [(4, True), (5, True), (6, False)],
)
def test_external_resource_assignment_priority_limit_boundary(
    external_priority, expected_external
):
    options = ScheduleOptions(include_external_res_ass=True, external_project_priority_limit=5)
    result = execute_authoritative_schedule_batch(
        [
            snapshot('P1', date(2026, 10, 10), options=options, priority=10),
            snapshot('P2', date(2026, 10, 20), priority=external_priority),
        ],
        resolvers={'P1': resolver(), 'P2': resolver()},
        resource_assignments=(assignment('P1', 'R1'), assignment('P2', 'R2')),
    )
    resource_ids = [d.resource_id for d in result.project('P1').resource_demands]
    assert ('R2' in resource_ids) is expected_external

def test_external_resource_assignment_is_excluded_when_option_disabled():
    options = ScheduleOptions(include_external_res_ass=False, external_project_priority_limit=5)
    result = execute_authoritative_schedule_batch(
        [
            snapshot('P1', date(2026, 10, 10), options=options, priority=10),
            snapshot('P2', date(2026, 10, 20), priority=1),
        ],
        resolvers={'P1': resolver(), 'P2': resolver()},
        resource_assignments=(assignment('P1', 'R1'), assignment('P2', 'R2')),
    )
    assert [d.resource_id for d in result.project('P1').resource_demands] == []


def test_single_project_preserves_existing_behavior_with_multi_project_options_disabled():
    result = execute_authoritative_schedule_batch(
        [snapshot('P1', date(2026, 10, 10))],
        resolvers={'P1': resolver()},
    )
    assert result.project('P1').result.project_finish == date(2026, 10, 9)


def test_combined_external_boundary_options_are_deterministic():
    options = ScheduleOptions(
        calculate_float_based_on_finish_date=False,
        ignore_other_project_relationships=True,
        include_external_res_ass=True,
        external_project_priority_limit=5,
    )
    kwargs = dict(
        resolvers={'P1': resolver(), 'P2': resolver()},
        external_relationships=(Relationship('P1-A', 'P2-A'),),
        activity_project_ids={'P1-A': 'P1', 'P2-A': 'P2'},
        resource_assignments=(assignment('P1', 'R1'), assignment('P2', 'R2')),
    )
    first = execute_authoritative_schedule_batch(
        [
            snapshot('P1', date(2026, 10, 10), options=options),
            snapshot('P2', date(2026, 10, 20), options=options, priority=5),
        ],
        **kwargs,
    )
    second = execute_authoritative_schedule_batch(
        [
            snapshot('P1', date(2026, 10, 10), options=options),
            snapshot('P2', date(2026, 10, 20), options=options, priority=5),
        ],
        **kwargs,
    )
    assert first.project('P1').result == second.project('P1').result
    assert first.project('P1').resource_demands == second.project('P1').resource_demands
    assert first.batch.finish_boundary_for('P1') == date(2026, 10, 20)
    assert first.project('P1').result.floats['P1-A'].total_float == 13
    assert [d.resource_id for d in first.project('P1').resource_demands] == ['R1', 'R2']


def test_unsupported_multi_project_resource_leveling_never_silently_falls_back():
    with pytest.raises(ValueError, match='unsupported schedule options') as exc:
        execute_authoritative_schedule_batch(
            [snapshot('P1', date(2026, 10, 10), options=ScheduleOptions(level_all_resources=True))],
            resolvers={'P1': resolver()},
        )
    assert 'level_all_resources' in str(exc.value)


def test_missing_external_project_membership_is_explicit():
    with pytest.raises(ValueError, match='MISSING_PROJECT_ID_FOR_RELATIONSHIP_ENDPOINT'):
        execute_authoritative_schedule_batch(
            [snapshot('P1', date(2026, 10, 10), options=ScheduleOptions(ignore_other_project_relationships=True))],
            resolvers={'P1': resolver()},
            external_relationships=(Relationship('P1-A', 'UNKNOWN-A'),),
        )
