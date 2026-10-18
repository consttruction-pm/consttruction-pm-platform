from datetime import date, datetime, timezone
import sqlite3

import pytest

from construction_pm.backend_p0.authoritative_schedule_query import AuthoritativeScheduleQueryProvider
from construction_pm.backend_p0.models import BackendScope
from construction_pm.control_intelligence.contracts import ControlScope
from construction_pm.control_intelligence.query import ScheduleQueryRequest
from construction_pm.schedule_calculation_context_repository import build_persisted_context
from construction_pm.schedule_input_snapshot_repository import SQLiteScheduleInputSnapshotRepository, build_snapshot
from construction_pm.schedule_evaluator import ScheduleEvaluationError
from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.authoritative_schedule import AuthoritativeScheduleInput, AuthoritativeScheduleMode
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.calendar_context import CalendarReference, CalendarResolverRegistry
from construction_pm.scheduling.calculation_context import CalculationContext
from construction_pm.scheduling.schedule_options import ScheduleOptions


def test_authoritative_query_fails_closed_when_leveling_input_is_not_bound_to_snapshot():
    conn = sqlite3.connect(":memory:")
    repo = SQLiteScheduleInputSnapshotRepository(conn)
    scope = BackendScope("T-1", "P-1", 9)
    source = AuthoritativeScheduleInput(
        snapshot_id="S-LEVELING-REQUIRED",
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
        project_revision=scope.project_revision,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=CalendarReference("CAL-1", "1"),
        activities=(Activity("A", 1),),
        relationships=(),
        activity_calendar_assignments=(),
        project_start=date(2026, 10, 1),
        schedule_options=ScheduleOptions(level_all_resources=True),
    )
    context = CalculationContext(
        project_id=scope.project_id,
        project_version=scope.project_revision,
        calendar_id="CAL-1",
        calendar_version="1",
        rules_version="rules-1",
        engine_version="engine-1",
        timezone="UTC",
        calculation_timestamp="2026-10-18T00:00:00+00:00",
        input_snapshot_id=source.snapshot_id,
        tenant_id=scope.tenant_id,
    )
    repo.save(build_snapshot(source, context, datetime(2026, 10, 18, tzinfo=timezone.utc)))
    registry = CalendarResolverRegistry(
        day_resolvers={"CAL-1@1": WorkingTimeResolver(WorkingCalendar())}
    )
    provider = AuthoritativeScheduleQueryProvider(repo, lambda: registry)
    request = ScheduleQueryRequest(
        "Q-LEVELING-REQUIRED",
        ControlScope(scope.tenant_id, scope.project_id, scope.project_revision),
        "user-1",
        "show schedule",
        constraints={"snapshot_id": source.snapshot_id},
    )

    with pytest.raises(ScheduleEvaluationError, match="SCHEDULE_LEVELING_INPUT_REQUIRED"):
        provider.execute(request, calculation_context=context)
