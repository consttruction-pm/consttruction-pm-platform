from datetime import datetime, time
from decimal import Decimal

from construction_pm.scheduling.calendar_context import (
    CalendarReference,
    CalendarResolverRegistry,
    SchedulingCalendarContext,
)
from construction_pm.scheduling.relationships import RelationshipType
from construction_pm.scheduling.time_calendar import (
    TimeAwareWorkingTimeResolver,
    WorkingTimeCalendar,
)
from construction_pm.scheduling.time_duration import LagQuantity, TimeQuantity
from construction_pm.scheduling.time_forward_pass import TimeActivity, TimeRelationship
from construction_pm.scheduling.time_schedule import time_schedule


def registry():
    calendar = WorkingTimeCalendar(
        daily_intervals={
            0: ((time(8), time(12)), (time(13), time(17))),
            1: ((time(8), time(12)), (time(13), time(17))),
            2: ((time(8), time(12)), (time(13), time(17))),
            3: ((time(8), time(12)), (time(13), time(17))),
            4: ((time(8), time(12)), (time(13), time(17))),
        }
    )
    return CalendarResolverRegistry(
        time_resolvers={"site@1": TimeAwareWorkingTimeResolver(calendar)}
    )


def context():
    ref = CalendarReference("site", "1", "working-time")
    return SchedulingCalendarContext(project=ref, activity=ref, relationship_lag=ref)


def result_projection(result):
    return {
        key: (
            value.start.isoformat(),
            value.finish.isoformat(),
            str(result.floats[key].total_float_hours),
            str(result.floats[key].free_float_hours),
            result.floats[key].critical,
        )
        for key, value in sorted(result.early_activities.items())
    }


def test_same_shared_core_input_produces_identical_web_desktop_mobile_result_fixture():
    ctx = context()
    activities = [
        TimeActivity("A", TimeQuantity.working_hours(4), ctx),
        TimeActivity("B", TimeQuantity.working_hours(2), ctx),
        TimeActivity("C", TimeQuantity.working_hours(1.5), ctx),
    ]
    relationships = [
        TimeRelationship("A", "B", RelationshipType.FS, LagQuantity.working_hours(1)),
        TimeRelationship("A", "C", RelationshipType.SS, LagQuantity.working_hours(0.5)),
    ]

    results = [
        time_schedule(
            activities,
            relationships,
            datetime(2026, 9, 22, 8),
            datetime(2026, 9, 23, 17),
            registry(),
        )
        for _ in range(3)
    ]

    projections = [result_projection(result) for result in results]
    assert projections[0] == projections[1] == projections[2]
    assert projections[0]["B"][0] == "2026-09-22T13:00:00"
    assert projections[0]["B"][1] == "2026-09-22T15:00:00"
    assert projections[0]["C"][0] == "2026-09-22T08:30:00"


