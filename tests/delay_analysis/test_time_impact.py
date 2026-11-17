from datetime import date, datetime, timezone
import sqlite3

from construction_pm.delay_analysis.fragnet import (
    DelayEventFragnet,
    FragnetActivity,
    FragnetRelationship,
)
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.delay_analysis.time_impact import TimeImpactAnalysisExecutor
from construction_pm.schedule_input_snapshot_repository import (
    SQLiteScheduleInputSnapshotRepository,
    build_snapshot,
)
from construction_pm.delay_analysis.schedule_run_capture import SQLiteScheduleRunCaptureRepository
from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.authoritative_schedule import (
    AuthoritativeScheduleInput,
    AuthoritativeScheduleMode,
)
from construction_pm.scheduling.calculation_context import CalculationContext
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.calendar_context import (
    CalendarReference,
    CalendarResolverRegistry,
)
from construction_pm.scheduling.relationships import Relationship, RelationshipType


def test_time_impact_inserts_fragnet_and_reexecutes_shared_scheduler():
    connection = sqlite3.connect(":memory:")
    snapshot_repository = SQLiteScheduleInputSnapshotRepository(connection)
    run_repository = SQLiteScheduleRunCaptureRepository(connection)
    scope_calendar = CalendarReference("CAL-1", "1")
    source_input = AuthoritativeScheduleInput(
        snapshot_id="SOURCE-SNAPSHOT",
        tenant_id="TENANT-1",
        project_id="PROJECT-1",
        project_revision=4,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=scope_calendar,
        activities=(Activity("A", 2), Activity("B", 1)),
        relationships=(Relationship("A", "B"),),
        activity_calendar_assignments=(),
        project_start=date(2026, 9, 21),
    )
    source_context = CalculationContext(
        project_id="PROJECT-1",
        project_version=4,
        calendar_id="CAL-1",
        calendar_version="1",
        rules_version="rules-v26",
        engine_version="shared-core-test",
        timezone="UTC",
        calculation_timestamp="2026-09-30T00:00:00+00:00",
        input_snapshot_id="SOURCE-SNAPSHOT",
        tenant_id="TENANT-1",
    )
    source_snapshot = build_snapshot(
        source_input,
        source_context,
        datetime(2026, 9, 30, tzinfo=timezone.utc),
    )
    snapshot_repository.save(source_snapshot)
    registry = CalendarResolverRegistry(
        day_resolvers={"CAL-1@1": WorkingTimeResolver(WorkingCalendar())}
    )
    fragnet = DelayEventFragnet(
        event_id="EVT-ACCESS-01",
        title="Delayed work-front access",
        description="Three working days of access restriction.",
        activities=(FragnetActivity("EVT-ACCESS-01-A", "Access restriction", 3),),
        relationships=(
            FragnetRelationship("A", "EVT-ACCESS-01-A", RelationshipType.FS),
            FragnetRelationship("EVT-ACCESS-01-A", "B", RelationshipType.FS),
        ),
    )
    clock_values = iter((
        datetime(2026, 10, 1, tzinfo=timezone.utc),
        datetime(2026, 10, 2, tzinfo=timezone.utc),
    ))
    executor = TimeImpactAnalysisExecutor(
        snapshot_repository=snapshot_repository,
        run_repository=run_repository,
        transaction_manager=SQLiteTransactionManager(connection),
        snapshot_id_factory=lambda: "IMPACTED-SNAPSHOT",
        clock=lambda: next(clock_values),
    )

    result = executor.execute(source_snapshot, source_context, registry, fragnet)

    assert result.method == "P6_EPPM_STYLE_INSERTED_FRAGNET_WHAT_IF"
    assert result.source_snapshot_id == "SOURCE-SNAPSHOT"
    assert result.impacted_snapshot_id == "IMPACTED-SNAPSHOT"
    assert result.added_activity_ids == ("EVT-ACCESS-01-A",)
    assert result.impacted_run.snapshot_hash == result.impacted_snapshot_hash
    assert result.unimpacted_run.snapshot_hash == source_snapshot.snapshot_hash
    assert result.project_finish_delta_calendar_days > 0
    assert len(result.analysis_hash) == 64
    assert snapshot_repository.get(source_snapshot.scope, "IMPACTED-SNAPSHOT") is not None
    assert run_repository.get(source_snapshot.scope, result.impacted_run.run_id) == result.impacted_run

    replay = executor.execute(source_snapshot, source_context, registry, fragnet)
    assert replay.analysis_hash == result.analysis_hash
    assert replay.unimpacted_run.run_id == result.unimpacted_run.run_id
    assert replay.impacted_run.run_id == result.impacted_run.run_id
