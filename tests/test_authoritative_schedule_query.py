from datetime import date, datetime, timezone
import sqlite3
from unittest.mock import patch

from construction_pm.application.authorization import AuthorizationContext, Permission, RoleBasedAuthorizationPolicy
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.authoritative_schedule_query import (
    AuthoritativeScheduleQueryApplicationService,
    AuthoritativeScheduleQueryProvider,
)
from construction_pm.control_intelligence.contracts import ControlScope
from construction_pm.control_intelligence.query import ScheduleQueryRequest
from construction_pm.schedule_calculation_context_repository import SQLiteCalculationContextRepository, build_persisted_context
from construction_pm.schedule_input_snapshot_repository import SQLiteScheduleInputSnapshotRepository, build_snapshot
from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.authoritative_schedule import AuthoritativeScheduleInput, AuthoritativeScheduleMode
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.calculation_context import CalculationContext
from construction_pm.scheduling.calendar_context import CalendarReference, CalendarResolverRegistry


def test_query_executes_real_snapshot_evaluation():
    conn = sqlite3.connect(":memory:")
    repo = SQLiteScheduleInputSnapshotRepository(conn)
    calendar = CalendarReference("CAL-1", "1")
    source = AuthoritativeScheduleInput(
        snapshot_id="S-I",
        tenant_id="T-1",
        project_id="P-1",
        project_revision=9,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=calendar,
        activities=(Activity("A", 2),),
        relationships=(),
        activity_calendar_assignments=(),
        project_start=date(2026, 9, 21),
    )
    context = CalculationContext(
        project_id="P-1", project_version=9, calendar_id="CAL-1", calendar_version="1",
        rules_version="rules-1", engine_version="engine-1", timezone="UTC",
        calculation_timestamp="2026-09-30T00:00:00+00:00", input_snapshot_id="S-I", tenant_id="T-1",
    )
    repo.save(build_snapshot(source, context, datetime(2026, 9, 30, tzinfo=timezone.utc)))

    registry = CalendarResolverRegistry(day_resolvers={"CAL-1@1": WorkingTimeResolver(WorkingCalendar())})
    provider = AuthoritativeScheduleQueryProvider(lambda: None, lambda: registry)  # replaced below
    provider = AuthoritativeScheduleQueryProvider(repo, lambda: registry)
    service = AuthoritativeScheduleQueryApplicationService(
        provider,
        RoleBasedAuthorizationPolicy({"viewer": frozenset({Permission.PROJECT_READ})}),
    )
    request = ScheduleQueryRequest("Q-I", ControlScope("T-1", "P-1", 9), "user-1", "show schedule")
    auth = AuthorizationContext("T-1", "P-1", "user-1", frozenset({"viewer"}))

    answer = service.execute(request, auth_context=auth, calculation_context=context)
    assert answer.data["activity_count"] == 1
    assert answer.data["project_finish"] == "2026-09-22"
    assert answer.source_refs[0].source_id == "S-I"


def test_filter_projection_selects_explicit_activity_ids():
    conn = sqlite3.connect(":memory:")
    repo = SQLiteScheduleInputSnapshotRepository(conn)
    source = AuthoritativeScheduleInput(
        snapshot_id="S-F",
        tenant_id="T-1", project_id="P-1", project_revision=9,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=CalendarReference("CAL-1", "1"),
        activities=(Activity("A", 1), Activity("B", 1)),
        relationships=(),
        activity_calendar_assignments=(),
        project_start=date(2026, 9, 21),
    )
    context = CalculationContext(
        project_id="P-1", project_version=9, calendar_id="CAL-1", calendar_version="1",
        rules_version="rules-1", engine_version="engine-1", timezone="UTC",
        calculation_timestamp="2026-09-30T00:00:00+00:00", input_snapshot_id="S-F", tenant_id="T-1",
    )
    repo.save(build_snapshot(source, context, datetime(2026, 9, 30, tzinfo=timezone.utc)))
    registry = CalendarResolverRegistry(day_resolvers={"CAL-1@1": WorkingTimeResolver(WorkingCalendar())})
    service = AuthoritativeScheduleQueryApplicationService(
        AuthoritativeScheduleQueryProvider(repo, lambda: registry),
        RoleBasedAuthorizationPolicy({"viewer": frozenset({Permission.PROJECT_READ})}),
    )
    request = ScheduleQueryRequest(
        "Q-F", ControlScope("T-1", "P-1", 9), "user-1", "filter",
        kind=__import__("construction_pm.control_intelligence.query", fromlist=["ScheduleQueryKind"]).ScheduleQueryKind.FILTER,
        constraints={"activity_ids": ["B"]},
    )
    auth = AuthorizationContext("T-1", "P-1", "user-1", frozenset({"viewer"}))
    answer = service.execute(request, auth_context=auth, calculation_context=context)
    assert list(answer.data["activities"]) == ["B"]


def test_scenario_projection_does_not_invoke_scheduler():
    from construction_pm.backend_p0 import authoritative_schedule_query
    from construction_pm.control_intelligence.query import ScheduleQueryKind

    conn = sqlite3.connect(":memory:")
    repo = SQLiteScheduleInputSnapshotRepository(conn)
    source = AuthoritativeScheduleInput(
        snapshot_id="S-SKIP",
        tenant_id="T-1",
        project_id="P-1",
        project_revision=9,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=CalendarReference("CAL-1", "1"),
        activities=(Activity("A", 1),),
        relationships=(),
        activity_calendar_assignments=(),
        project_start=date(2026, 9, 21),
    )
    context = CalculationContext(
        project_id="P-1",
        project_version=9,
        calendar_id="CAL-1",
        calendar_version="1",
        rules_version="rules-1",
        engine_version="engine-1",
        timezone="UTC",
        calculation_timestamp="2026-09-30T00:00:00+00:00",
        input_snapshot_id="S-SKIP",
        tenant_id="T-1",
    )
    repo.save(build_snapshot(source, context, datetime(2026, 9, 30, tzinfo=timezone.utc)))
    registry = CalendarResolverRegistry(
        day_resolvers={"CAL-1@1": WorkingTimeResolver(WorkingCalendar())}
    )
    service = AuthoritativeScheduleQueryApplicationService(
        AuthoritativeScheduleQueryProvider(repo, lambda: registry),
        RoleBasedAuthorizationPolicy({"viewer": frozenset({Permission.PROJECT_READ})}),
    )
    request = ScheduleQueryRequest(
        "Q-SKIP",
        ControlScope("T-1", "P-1", 9),
        "user-1",
        "scenario purpose",
        kind=ScheduleQueryKind.SCENARIO,
        constraints={
            "changes": [
                {
                    "change_id": "C-1",
                    "domain": "schedule",
                    "entity_type": "activity",
                    "entity_id": "A",
                    "operation": "set_duration",
                    "proposed_value": {"duration": 3},
                }
            ]
        },
    )
    auth = AuthorizationContext("T-1", "P-1", "user-1", frozenset({"viewer"}))

    with patch.object(
        authoritative_schedule_query,
        "evaluate_schedule_snapshot",
        side_effect=AssertionError("scenario proposals must not invoke CPM evaluation"),
    ):
        answer = service.execute(
            request,
            auth_context=auth,
            calculation_context=context,
        )

    assert answer.data["status"] == "proposal_only"
    assert answer.data["authoritative_mutation_allowed"] is False
    assert answer.source_refs[0].source_id == "S-SKIP"
    assert answer.source_refs[0].source_type == "schedule-input-snapshot"
    assert answer.source_refs[0].content_hash is not None


def test_scenario_projection_is_proposal_only_and_traceable():
    from construction_pm.control_intelligence.query import ScheduleQueryKind

    conn = sqlite3.connect(":memory:")
    repo = SQLiteScheduleInputSnapshotRepository(conn)
    source = AuthoritativeScheduleInput(
        snapshot_id="S-S", tenant_id="T-1", project_id="P-1", project_revision=9,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=CalendarReference("CAL-1", "1"),
        activities=(Activity("A", 1),),
        relationships=(),
        activity_calendar_assignments=(),
        project_start=date(2026, 9, 21),
    )
    context = CalculationContext(
        project_id="P-1", project_version=9, calendar_id="CAL-1", calendar_version="1",
        rules_version="rules-1", engine_version="engine-1", timezone="UTC",
        calculation_timestamp="2026-09-30T00:00:00+00:00", input_snapshot_id="S-S", tenant_id="T-1",
    )
    repo.save(build_snapshot(source, context, datetime(2026, 9, 30, tzinfo=timezone.utc)))
    registry = CalendarResolverRegistry(day_resolvers={"CAL-1@1": WorkingTimeResolver(WorkingCalendar())})
    service = AuthoritativeScheduleQueryApplicationService(
        AuthoritativeScheduleQueryProvider(repo, lambda: registry),
        RoleBasedAuthorizationPolicy({"viewer": frozenset({Permission.PROJECT_READ})}),
    )
    request = ScheduleQueryRequest(
        "Q-S", ControlScope("T-1", "P-1", 9), "user-1", "scenario purpose",
        kind=ScheduleQueryKind.SCENARIO,
        constraints={"changes": [{"change_id": "C-1", "domain": "schedule", "entity_type": "activity",
                                  "entity_id": "A", "operation": "set_duration", "proposed_value": {"duration": 3}}]},
    )
    auth = AuthorizationContext("T-1", "P-1", "user-1", frozenset({"viewer"}))
    answer = service.execute(request, auth_context=auth, calculation_context=context)
    assert answer.data["status"] == "proposal_only"
    assert answer.data["authoritative_mutation_allowed"] is False
    assert answer.data["proposed_changes"][0]["entity_id"] == "A"
    assert answer.source_refs[0].source_id == "S-S"


def test_query_resolves_authoritative_context_from_persisted_state():
    conn = sqlite3.connect(":memory:")
    snapshot_repo = SQLiteScheduleInputSnapshotRepository(conn)
    context_repo = SQLiteCalculationContextRepository(conn)
    calendar = CalendarReference("CAL-1", "1")
    source = AuthoritativeScheduleInput(
        snapshot_id="S-PERSISTED",
        tenant_id="T-1",
        project_id="P-1",
        project_revision=9,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=calendar,
        activities=(Activity("A", 2),),
        relationships=(),
        activity_calendar_assignments=(),
        project_start=date(2026, 9, 21),
    )
    persisted_context = CalculationContext(
        project_id="P-1",
        project_version=9,
        calendar_id="CAL-1",
        calendar_version="1",
        rules_version="rules-1",
        engine_version="engine-1",
        timezone="UTC",
        calculation_timestamp="2026-09-30T00:00:00+00:00",
        input_snapshot_id="S-PERSISTED",
        tenant_id="T-1",
        actor_id="authoritative-actor",
    )
    snapshot = build_snapshot(
        source,
        persisted_context,
        datetime(2026, 9, 30, tzinfo=timezone.utc),
    )
    snapshot_repo.save(snapshot)
    context_repo.save(build_persisted_context(
        BackendScope("T-1", "P-1", 9),
        persisted_context,
    ))

    registry = CalendarResolverRegistry(
        day_resolvers={"CAL-1@1": WorkingTimeResolver(WorkingCalendar())}
    )
    provider = AuthoritativeScheduleQueryProvider(
        snapshot_repo,
        lambda: registry,
        calculation_context_repository=context_repo,
    )
    service = AuthoritativeScheduleQueryApplicationService(
        provider,
        RoleBasedAuthorizationPolicy({"viewer": frozenset({Permission.PROJECT_READ})}),
    )
    request = ScheduleQueryRequest(
        "Q-PERSISTED",
        ControlScope("T-1", "P-1", 9),
        "user-1",
        "show schedule",
        constraints={"snapshot_id": "S-PERSISTED"},
    )
    auth = AuthorizationContext("T-1", "P-1", "user-1", frozenset({"viewer"}))

    answer = service.execute(
        request,
        auth_context=auth,
        calculation_context=None,
    )
    assert answer.data["calculation_run_identity"]
    assert answer.data["project_finish"] == "2026-09-22"


def test_persisted_replay_requires_request_snapshot_id_only():
    conn = sqlite3.connect(":memory:")
    snapshot_repo = SQLiteScheduleInputSnapshotRepository(conn)
    context_repo = SQLiteCalculationContextRepository(conn)
    context = CalculationContext(
        project_id="P-1",
        project_version=9,
        calendar_id="CAL-1",
        calendar_version="1",
        rules_version="rules-1",
        engine_version="engine-1",
        timezone="UTC",
        calculation_timestamp="2026-09-30T00:00:00+00:00",
        input_snapshot_id="S-CONTEXT-ONLY",
        tenant_id="T-1",
    )
    provider = AuthoritativeScheduleQueryProvider(
        snapshot_repo,
        lambda: CalendarResolverRegistry(),
        calculation_context_repository=context_repo,
    )
    service = AuthoritativeScheduleQueryApplicationService(
        provider,
        RoleBasedAuthorizationPolicy({"viewer": frozenset({Permission.PROJECT_READ})}),
    )
    auth = AuthorizationContext("T-1", "P-1", "user-1", frozenset({"viewer"}))

    for constraints in (
        {"input_snapshot_id": "S-CONTEXT-ONLY"},
        {},
    ):
        request = ScheduleQueryRequest(
            "Q-REQUIRE-SNAPSHOT-ID",
            ControlScope("T-1", "P-1", 9),
            "user-1",
            "show schedule",
            constraints=constraints,
        )
        try:
            service.execute(
                request,
                auth_context=auth,
                calculation_context=context,
            )
        except ValueError as exc:
            assert str(exc) == "SCHEDULE_INPUT_SNAPSHOT_ID_REQUIRED"
        else:
            raise AssertionError("persisted replay accepted a non-authoritative lookup identifier")


def test_query_ignores_client_calculation_metadata_when_persisted_context_exists():
    conn = sqlite3.connect(":memory:")
    snapshot_repo = SQLiteScheduleInputSnapshotRepository(conn)
    context_repo = SQLiteCalculationContextRepository(conn)
    calendar = CalendarReference("CAL-1", "1")
    source = AuthoritativeScheduleInput(
        snapshot_id="S-TRUST",
        tenant_id="T-1",
        project_id="P-1",
        project_revision=9,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=calendar,
        activities=(Activity("A", 2),),
        relationships=(),
        activity_calendar_assignments=(),
        project_start=date(2026, 9, 21),
    )
    authoritative = CalculationContext(
        project_id="P-1",
        project_version=9,
        calendar_id="CAL-1",
        calendar_version="1",
        rules_version="rules-1",
        engine_version="engine-1",
        timezone="UTC",
        calculation_timestamp="2026-09-30T00:00:00+00:00",
        input_snapshot_id="S-TRUST",
        tenant_id="T-1",
        actor_id="authoritative-actor",
    )
    snapshot_repo.save(
        build_snapshot(
            source,
            authoritative,
            datetime(2026, 9, 30, tzinfo=timezone.utc),
        )
    )
    context_repo.save(build_persisted_context(
        BackendScope("T-1", "P-1", 9),
        authoritative,
    ))
    registry = CalendarResolverRegistry(
        day_resolvers={"CAL-1@1": WorkingTimeResolver(WorkingCalendar())}
    )
    provider = AuthoritativeScheduleQueryProvider(
        snapshot_repo,
        lambda: registry,
        calculation_context_repository=context_repo,
    )
    service = AuthoritativeScheduleQueryApplicationService(
        provider,
        RoleBasedAuthorizationPolicy({"viewer": frozenset({Permission.PROJECT_READ})}),
    )
    request = ScheduleQueryRequest(
        "Q-TRUST",
        ControlScope("T-1", "P-1", 9),
        "user-1",
        "show schedule",
        constraints={"snapshot_id": "S-TRUST"},
    )
    spoofed = CalculationContext(
        **{
            **authoritative.to_dict(),
            "calendar_id": "CLIENT-SPOOFED",
            "rules_version": "client-spoofed-rules",
            "engine_version": "client-spoofed-engine",
        }
    )
    auth = AuthorizationContext("T-1", "P-1", "user-1", frozenset({"viewer"}))
    answer = service.execute(
        request,
        auth_context=auth,
        calculation_context=spoofed,
    )
    assert answer.data["project_finish"] == "2026-09-22"
