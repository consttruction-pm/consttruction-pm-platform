from datetime import date, datetime, timezone
from decimal import Decimal
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
from construction_pm.scheduling.leveling_boundary import SchedulerLevelingInput
from construction_pm.scheduling.resource_leveling import (
    BackwardLevelingActivity,
    LevelingActivity,
    ResourceCapacity,
    ResourceDemand,
    ResourceLevelingOptions,
)
from construction_pm.scheduling.schedule_options import ScheduleOptions


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
    resolver_calls = []
    provider = AuthoritativeScheduleQueryProvider(
        repo, lambda: registry,
        leveling_input_resolver=lambda *_: resolver_calls.append("unexpected"),
    )
    service = AuthoritativeScheduleQueryApplicationService(
        provider,
        RoleBasedAuthorizationPolicy({"viewer": frozenset({Permission.PROJECT_READ})}),
    )
    request = ScheduleQueryRequest("Q-I", ControlScope("T-1", "P-1", 9), "user-1", "show schedule", constraints={"snapshot_id": "S-I"})
    auth = AuthorizationContext("T-1", "P-1", "user-1", frozenset({"viewer"}))

    answer = service.execute(request, auth_context=auth, calculation_context=context)
    assert answer.data["activity_count"] == 1
    assert answer.data["project_finish"] == "2026-09-22"
    assert isinstance(answer.data["activities"]["A"]["critical"], bool)
    assert resolver_calls == []
    assert answer.source_refs[0].source_id == "S-I"


def test_query_runs_leveling_only_with_snapshot_bound_resource_inputs():
    conn = sqlite3.connect(":memory:")
    repo = SQLiteScheduleInputSnapshotRepository(conn)
    start = date(2026, 9, 21)
    end = date(2026, 9, 22)
    source = AuthoritativeScheduleInput(
        snapshot_id="S-LEVEL", tenant_id="T-1", project_id="P-1", project_revision=9,
        mode=AuthoritativeScheduleMode.DATE_BASED, project_calendar=CalendarReference("CAL-1", "1"),
        activities=(Activity("A", 2),), relationships=(), activity_calendar_assignments=(),
        schedule_options=ScheduleOptions(level_all_resources=True), project_start=start,
    )
    context = CalculationContext(
        project_id="P-1", project_version=9, calendar_id="CAL-1", calendar_version="1",
        rules_version="rules-1", engine_version="engine-1", timezone="UTC",
        calculation_timestamp="2026-09-30T00:00:00+00:00", input_snapshot_id="S-LEVEL", tenant_id="T-1",
    )
    snapshot = build_snapshot(source, context, datetime(2026, 9, 30, tzinfo=timezone.utc))
    repo.save(snapshot)
    registry = CalendarResolverRegistry(day_resolvers={"CAL-1@1": WorkingTimeResolver(WorkingCalendar())})
    demand = ResourceDemand("R-1", start, Decimal("4"), "A")
    leveling = SchedulerLevelingInput(
        forward_activities=(LevelingActivity("A", start, end, 0, (demand,)),),
        backward_activities=(BackwardLevelingActivity("A", start, end, start, end, (demand,)),),
        capacities=(ResourceCapacity("R-1", start, Decimal("8"), "RC-1", "v1", "a" * 64),),
        options=ResourceLevelingOptions(level_all_resources=True),
        source_snapshot_id=snapshot.snapshot_id, source_snapshot_hash=snapshot.snapshot_hash,
        source_calculation_identity=context.calculation_identity,
        resource_facts_hash="b" * 64, calendar_manifest_hash="c" * 64,
    )
    calls = []
    def resolve_leveling_input(loaded_snapshot, loaded_context, loaded_registry):
        calls.append((loaded_snapshot.snapshot_hash, loaded_context.calculation_identity, loaded_registry))
        return leveling

    service = AuthoritativeScheduleQueryApplicationService(
        AuthoritativeScheduleQueryProvider(
            repo, lambda: registry, leveling_input_resolver=resolve_leveling_input
        ),
        RoleBasedAuthorizationPolicy({"viewer": frozenset({Permission.PROJECT_READ})}),
    )
    request = ScheduleQueryRequest(
        "Q-LEVEL", ControlScope("T-1", "P-1", 9), "user-1", "show schedule",
        constraints={"snapshot_id": "S-LEVEL"},
    )
    auth = AuthorizationContext("T-1", "P-1", "user-1", frozenset({"viewer"}))

    answer = service.execute(request, auth_context=auth, calculation_context=context)
    assert calls and calls[0][0] == snapshot.snapshot_hash
    assert answer.data["activity_count"] == 1
    assert answer.data["project_finish"] == "2026-09-22"
    assert answer.data["calculation_run_identity"]


def test_query_rejects_leveling_input_from_a_different_snapshot():
    conn = sqlite3.connect(":memory:")
    repo = SQLiteScheduleInputSnapshotRepository(conn)
    source = AuthoritativeScheduleInput(
        snapshot_id="S-BIND", tenant_id="T-1", project_id="P-1", project_revision=9,
        mode=AuthoritativeScheduleMode.DATE_BASED, project_calendar=CalendarReference("CAL-1", "1"),
        activities=(Activity("A", 1),), relationships=(), activity_calendar_assignments=(),
        project_start=date(2026, 9, 21),
    )
    context = CalculationContext(
        project_id="P-1", project_version=9, calendar_id="CAL-1", calendar_version="1",
        rules_version="rules-1", engine_version="engine-1", timezone="UTC",
        calculation_timestamp="2026-09-30T00:00:00+00:00", input_snapshot_id="S-BIND", tenant_id="T-1",
    )
    snapshot = build_snapshot(source, context, datetime(2026, 9, 30, tzinfo=timezone.utc))
    repo.save(snapshot)
    stale = SchedulerLevelingInput(
        forward_activities=(LevelingActivity("A", date(2026, 9, 21), date(2026, 9, 21), 0),),
        backward_activities=(BackwardLevelingActivity(
            "A", date(2026, 9, 21), date(2026, 9, 21), date(2026, 9, 21), date(2026, 9, 21)
        ),),
        capacities=(ResourceCapacity("R-1", date(2026, 9, 21), Decimal("8"), "RC-1", "v1", "a" * 64),),
        options=ResourceLevelingOptions(level_all_resources=True),
        source_snapshot_id="STALE", source_snapshot_hash="d" * 64,
        source_calculation_identity=context.calculation_identity,
        resource_facts_hash="b" * 64, calendar_manifest_hash="c" * 64,
    )
    registry = CalendarResolverRegistry(day_resolvers={"CAL-1@1": WorkingTimeResolver(WorkingCalendar())})
    service = AuthoritativeScheduleQueryApplicationService(
        AuthoritativeScheduleQueryProvider(
            repo, lambda: registry, leveling_input_resolver=lambda *_: stale
        ),
        RoleBasedAuthorizationPolicy({"viewer": frozenset({Permission.PROJECT_READ})}),
    )
    request = ScheduleQueryRequest(
        "Q-BIND", ControlScope("T-1", "P-1", 9), "user-1", "show schedule",
        constraints={"snapshot_id": "S-BIND"},
    )
    auth = AuthorizationContext("T-1", "P-1", "user-1", frozenset({"viewer"}))
    try:
        service.execute(request, auth_context=auth, calculation_context=context)
    except Exception as exc:
        assert "LEVELING_INPUT_SNAPSHOT_ID_MISMATCH" in str(exc)
    else:
        raise AssertionError("provider accepted resource inputs bound to a different snapshot")


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
        constraints={"activity_ids": ["B"], "snapshot_id": "S-F"},
    )
    auth = AuthorizationContext("T-1", "P-1", "user-1", frozenset({"viewer"}))
    answer = service.execute(request, auth_context=auth, calculation_context=context)
    assert list(answer.data["activities"]) == ["B"]
    assert isinstance(answer.data["activities"]["B"]["critical"], bool)


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
            "snapshot_id": "S-SKIP",
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
        constraints={"snapshot_id": "S-S", "changes": [{"change_id": "C-1", "domain": "schedule", "entity_type": "activity",
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
        {"snapshot_id": "   "},
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
