from datetime import date, datetime, timezone
from decimal import Decimal
import sqlite3
from unittest.mock import patch

from construction_pm.application.authorization import AuthorizationContext, Permission, RoleBasedAuthorizationPolicy
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.authoritative_schedule_query import (
    AuthoritativeScheduleQueryApplicationService,
    AuthoritativeScheduleQueryProvider,
    _snapshot_requests_resource_leveling,
)
from construction_pm.control_intelligence.contracts import ControlScope
from construction_pm.control_intelligence.query import ScheduleQueryRequest
from construction_pm.schedule_calculation_context_repository import SQLiteCalculationContextRepository, build_persisted_context
from construction_pm.schedule_input_snapshot_repository import SQLiteScheduleInputSnapshotRepository, build_snapshot
from construction_pm.scheduling.activity import Activity, ActivityStatus, ActivityType
from construction_pm.scheduling.authoritative_schedule import AuthoritativeScheduleInput, AuthoritativeScheduleMode
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.calculation_context import CalculationContext
from construction_pm.scheduling.calendar_context import CalendarReference, CalendarResolverRegistry
from construction_pm.scheduling.constraints import ActivityConstraint, ConstraintType
from construction_pm.scheduling.leveling_boundary import SchedulerLevelingInput
from construction_pm.scheduling.relationships import Relationship, RelationshipType
from construction_pm.scheduling.resource_dependent import (
    ResourceDependentDemandPeriod,
    ResourceDependentDriverFact,
)
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


def test_query_requires_authorized_resource_input_for_resource_dependent_facts():
    conn = sqlite3.connect(":memory:")
    repo = SQLiteScheduleInputSnapshotRepository(conn)
    calendar = CalendarReference("CAL-1", "1")
    fact = ResourceDependentDriverFact(
        assignment_id="AS-RD",
        activity_id="RD-1",
        resource_id="R-1",
        calendar_id="RC-1",
        calendar_version="v1",
        unit_of_measure="labor-unit",
        planned_units=Decimal("8"),
        is_driving=True,
        units_per_time=Decimal("4"),
        units_per_time_period="day",
        hours_per_units_time_period=Decimal("8"),
        demand_periods=(
            ResourceDependentDemandPeriod(date(2026, 9, 21), Decimal("4")),
        ),
    )
    source = AuthoritativeScheduleInput(
        snapshot_id="S-RD-ONLY",
        tenant_id="T-1",
        project_id="P-1",
        project_revision=9,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=calendar,
        activities=(
            Activity(
                "RD-1",
                2,
                activity_type=ActivityType.RESOURCE_DEPENDENT,
                resource_dependent_input_hash="a" * 64,
            ),
        ),
        relationships=(),
        activity_calendar_assignments=(),
        resource_dependent_assignment_facts=(fact,),
        project_start=date(2026, 9, 21),
    )
    context = CalculationContext(
        project_id="P-1", project_version=9, calendar_id="CAL-1", calendar_version="1",
        rules_version="rules-1", engine_version="engine-1", timezone="UTC",
        calculation_timestamp="2026-09-30T00:00:00+00:00", input_snapshot_id="S-RD-ONLY", tenant_id="T-1",
    )
    repo.save(build_snapshot(source, context, datetime(2026, 9, 30, tzinfo=timezone.utc)))
    registry = CalendarResolverRegistry(day_resolvers={"CAL-1@1": WorkingTimeResolver(WorkingCalendar())})
    service = AuthoritativeScheduleQueryApplicationService(
        AuthoritativeScheduleQueryProvider(repo, lambda: registry),
        RoleBasedAuthorizationPolicy({"viewer": frozenset({Permission.PROJECT_READ})}),
    )
    request = ScheduleQueryRequest(
        "Q-RD-ONLY", ControlScope("T-1", "P-1", 9), "user-1", "show schedule",
        constraints={"snapshot_id": "S-RD-ONLY"},
    )
    auth = AuthorizationContext("T-1", "P-1", "user-1", frozenset({"viewer"}))

    try:
        service.execute(request, auth_context=auth, calculation_context=context)
    except Exception as exc:
        assert getattr(exc, "code", None) == "SCHEDULE_RESOURCE_INPUT_REQUIRED"
    else:
        raise AssertionError(
            "provider evaluated resource-dependent facts without authorized resource input"
        )


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
    def resolve_leveling_input(loaded_snapshot, loaded_context, loaded_registry, loaded_auth_context):
        calls.append((loaded_snapshot.snapshot_hash, loaded_context.calculation_identity, loaded_registry, loaded_auth_context))
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
    assert calls[0][3] == auth
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
        schedule_options=ScheduleOptions(level_all_resources=True),
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
        assert getattr(exc, "code", None) == "LEVELING_INPUT_SNAPSHOT_ID_MISMATCH"
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



def test_preserve_scheduled_dates_option_does_not_enable_resource_leveling_by_itself():
    from types import SimpleNamespace
    import json

    snapshot = SimpleNamespace(
        canonical_payload=json.dumps({
            "mode": "DATE_BASED",
            "schedule_options": {
                "level_all_resources": False,
                "level_within_float": False,
                "preserve_scheduled_early_and_late_dates": True,
                "min_float_to_preserve": 0,
                "over_allocation_percentage": 0,
                "resource_list": None,
                "priority_list": None,
            },
        })
    )

    assert _snapshot_requests_resource_leveling(snapshot) is False


def test_resource_leveling_activation_options_still_request_leveling():
    from types import SimpleNamespace
    import json

    snapshot = SimpleNamespace(
        canonical_payload=json.dumps({
            "mode": "DATE_BASED",
            "schedule_options": {
                "level_all_resources": True,
                "preserve_scheduled_early_and_late_dates": False,
            },
        })
    )

    assert _snapshot_requests_resource_leveling(snapshot) is True


def _negative_float_query_service(snapshot_id: str = "S-NF"):
    conn = sqlite3.connect(":memory:")
    repo = SQLiteScheduleInputSnapshotRepository(conn)
    calendar = CalendarReference("CAL-1", "1")
    source = AuthoritativeScheduleInput(
        snapshot_id=snapshot_id,
        tenant_id="T-1",
        project_id="P-1",
        project_revision=9,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=calendar,
        activities=(Activity("A", 5), Activity("B", 1)),
        relationships=(),
        activity_calendar_assignments=(),
        project_start=date(2026, 9, 21),
        project_finish=date(2026, 9, 23),
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
        input_snapshot_id=snapshot_id,
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
    return service, context


def test_query_exposes_negative_float_diagnostic_in_fact_and_explanation():
    from construction_pm.control_intelligence.query import ScheduleQueryKind

    service, context = _negative_float_query_service("S-NF-FACT")
    auth = AuthorizationContext("T-1", "P-1", "user-1", frozenset({"viewer"}))
    scope = ControlScope("T-1", "P-1", 9)

    fact = service.execute(
        ScheduleQueryRequest(
            "Q-NF-F",
            scope,
            "user-1",
            "show negative float",
            constraints={"snapshot_id": "S-NF-FACT"},
        ),
        auth_context=auth,
        calculation_context=context,
    )
    findings = fact.data["diagnostics"]
    assert [item["code"] for item in findings] == ["NEGATIVE_FLOAT"]
    assert findings[0]["activity_id"] == "A"
    assert findings[0]["severity"] == "WARNING"

    explanation = service.execute(
        ScheduleQueryRequest(
            "Q-NF-E",
            scope,
            "user-1",
            "explain negative float",
            kind=ScheduleQueryKind.EXPLANATION,
            constraints={"snapshot_id": "S-NF-FACT"},
        ),
        auth_context=auth,
        calculation_context=context,
    )
    assert [item["code"] for item in explanation.data["diagnostics"]] == [
        "NEGATIVE_FLOAT"
    ]


def test_filter_projection_scopes_diagnostics_to_selected_activity():
    from construction_pm.control_intelligence.query import ScheduleQueryKind

    service, context = _negative_float_query_service("S-NF-FILTER")
    auth = AuthorizationContext("T-1", "P-1", "user-1", frozenset({"viewer"}))
    scope = ControlScope("T-1", "P-1", 9)

    def run(query_id: str, activity_ids: list[str]):
        return service.execute(
            ScheduleQueryRequest(
                query_id,
                scope,
                "user-1",
                "filter",
                kind=ScheduleQueryKind.FILTER,
                constraints={
                    "activity_ids": activity_ids,
                    "snapshot_id": "S-NF-FILTER",
                },
            ),
            auth_context=auth,
            calculation_context=context,
        )

    selected_a = run("Q-NF-FA", ["A"])
    assert [item["code"] for item in selected_a.data["diagnostics"]] == [
        "NEGATIVE_FLOAT"
    ]

    # B has float under the same constraint, so its answer must not inherit A's
    # activity-scoped warning.
    selected_b = run("Q-NF-FB", ["B"])
    assert selected_b.data["diagnostics"] == []


def test_query_translates_infeasible_snapshot_into_stable_validation_code():
    from construction_pm.backend_p0.errors import BackendApplicationError

    conn = sqlite3.connect(":memory:")
    repo = SQLiteScheduleInputSnapshotRepository(conn)
    calendar = CalendarReference("CAL-1", "1")
    source = AuthoritativeScheduleInput(
        snapshot_id="S-INFEASIBLE-QUERY",
        tenant_id="T-1",
        project_id="P-1",
        project_revision=9,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=calendar,
        activities=(Activity("A", 2),),
        relationships=(),
        activity_calendar_assignments=(),
        constraints=(
            ActivityConstraint(
                "A", ConstraintType.START_NO_EARLIER_THAN, date(2026, 9, 25)
            ),
            ActivityConstraint(
                "A", ConstraintType.START_NO_LATER_THAN, date(2026, 9, 22)
            ),
        ),
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
        input_snapshot_id="S-INFEASIBLE-QUERY",
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
        "Q-INFEASIBLE",
        ControlScope("T-1", "P-1", 9),
        "user-1",
        "show schedule",
        constraints={"snapshot_id": "S-INFEASIBLE-QUERY"},
    )
    auth = AuthorizationContext("T-1", "P-1", "user-1", frozenset({"viewer"}))
    try:
        service.execute(request, auth_context=auth, calculation_context=context)
    except BackendApplicationError as exc:
        assert exc.code == "SCHEDULE_INFEASIBLE:CONSTRAINT_WINDOW_EMPTY"
    else:
        raise AssertionError("infeasible snapshot was accepted")


def test_query_exposes_wbs_summary_aggregated_progress_from_persisted_ancestry():
    conn = sqlite3.connect(":memory:")
    repo = SQLiteScheduleInputSnapshotRepository(conn)
    calendar = CalendarReference("CAL-1", "1")
    source = AuthoritativeScheduleInput(
        snapshot_id="S-WBS-PROGRESS",
        tenant_id="T-1",
        project_id="P-1",
        project_revision=9,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=calendar,
        activities=(
            Activity(
                "DONE",
                2,
                actual_start=date(2026, 11, 2),
                actual_finish=date(2026, 11, 3),
                remaining_duration=0,
                percent_complete=100,
                status=ActivityStatus.COMPLETED,
                wbs_id="W-CHILD",
                wbs_ancestry=("W-ROOT",),
            ),
            Activity(
                "HALF",
                4,
                actual_start=date(2026, 11, 2),
                remaining_duration=2,
                percent_complete=50,
                status=ActivityStatus.IN_PROGRESS,
                wbs_id="W-ROOT",
            ),
            Activity("NEW", 3, wbs_id="W-ROOT"),
            Activity(
                "WBS",
                0,
                activity_type=ActivityType.WBS_SUMMARY,
                wbs_id="W-ROOT",
            ),
        ),
        relationships=(),
        activity_calendar_assignments=(),
        project_start=date(2026, 11, 2),
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
        input_snapshot_id="S-WBS-PROGRESS",
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
        "Q-WBS-PROGRESS",
        ControlScope("T-1", "P-1", 9),
        "user-1",
        "wbs summary progress",
        constraints={"snapshot_id": "S-WBS-PROGRESS"},
    )
    answer = service.execute(
        request,
        auth_context=AuthorizationContext(
            "T-1", "P-1", "user-1", frozenset({"viewer"})
        ),
        calculation_context=context,
    )

    summary = answer.data["activities"]["WBS"]
    # (100 + 50 + 0) / 3 over the same and subordinate WBS descendants.
    assert summary["percent_complete"] == 50.0
    assert summary["status"] == "In Progress"
    # Task rows do not duplicate persisted progress in the schedule answer.
    assert answer.data["activities"]["NEW"]["percent_complete"] is None
    assert answer.data["activities"]["NEW"]["status"] is None


def test_persisted_start_and_finish_milestones_place_successors_from_their_event():
    conn = sqlite3.connect(":memory:")
    repo = SQLiteScheduleInputSnapshotRepository(conn)
    calendar = CalendarReference("CAL-1", "1")
    source = AuthoritativeScheduleInput(
        snapshot_id="S-MILESTONES",
        tenant_id="T-1",
        project_id="P-1",
        project_revision=9,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=calendar,
        activities=(
            Activity(
                "SM",
                0,
                activity_type=ActivityType.START_MILESTONE,
                wbs_id="W-ROOT",
            ),
            Activity("A", 3, wbs_id="W-ROOT"),
            Activity(
                "FM",
                0,
                activity_type=ActivityType.FINISH_MILESTONE,
                wbs_id="W-ROOT",
            ),
        ),
        relationships=(
            Relationship("SM", "A", RelationshipType.FS),
            Relationship("A", "FM", RelationshipType.FS),
        ),
        activity_calendar_assignments=(),
        project_start=date(2026, 11, 2),
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
        input_snapshot_id="S-MILESTONES",
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
        "Q-MILESTONES",
        ControlScope("T-1", "P-1", 9),
        "user-1",
        "milestone placement",
        constraints={"snapshot_id": "S-MILESTONES"},
    )
    answer = service.execute(
        request,
        auth_context=AuthorizationContext(
            "T-1", "P-1", "user-1", frozenset({"viewer"})
        ),
        calculation_context=context,
    )

    facts = answer.data["activities"]
    assert (facts["SM"]["start"], facts["SM"]["finish"]) == (
        "2026-11-02",
        "2026-11-02",
    )
    assert (facts["A"]["start"], facts["A"]["finish"]) == (
        "2026-11-03",
        "2026-11-05",
    )
    assert (facts["FM"]["start"], facts["FM"]["finish"]) == (
        "2026-11-06",
        "2026-11-06",
    )


def _cost_recalculation_case():
    from construction_pm.resources.models import CostBasis, Resource, ResourceRate, ResourceType
    from construction_pm.scheduling.leveling_cost_recalculation import (
        LevelingCostAssignment,
        LevelingCostInputs,
    )
    from construction_pm.scheduling.schedule_options import PriorityListItem, PrioritySortOrder

    conn = sqlite3.connect(":memory:")
    repo = SQLiteScheduleInputSnapshotRepository(conn)
    start = date(2026, 9, 21)
    end = date(2026, 9, 22)
    source = AuthoritativeScheduleInput(
        snapshot_id="S-COST", tenant_id="T-1", project_id="P-1", project_revision=9,
        mode=AuthoritativeScheduleMode.DATE_BASED, project_calendar=CalendarReference("CAL-1", "1"),
        activities=(Activity("A", 2),), relationships=(), activity_calendar_assignments=(),
        schedule_options=ScheduleOptions(
            level_all_resources=True,
            preserve_scheduled_early_and_late_dates=True,
            recalculate_resource_costs=True,
            priority_list=(
                PriorityListItem("activity_priority", PrioritySortOrder.ASCENDING),
            ),
        ),
        project_start=start,
    )
    context = CalculationContext(
        project_id="P-1", project_version=9, calendar_id="CAL-1", calendar_version="1",
        rules_version="rules-1", engine_version="engine-1", timezone="UTC",
        calculation_timestamp="2026-09-30T00:00:00+00:00", input_snapshot_id="S-COST", tenant_id="T-1",
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
    cost_inputs = LevelingCostInputs(
        assignments=(LevelingCostAssignment("AS-A", "A", "R-1", Decimal("4")),),
        resources={
            "R-1": Resource(
                id="R-1", code="R-1", name="Labor", resource_type=ResourceType.LABOR,
                unit="day",
                rates=[ResourceRate(Decimal("10"), CostBasis.PER_DAY, "USD", effective_from=start)],
            )
        },
    )
    request = ScheduleQueryRequest(
        "Q-COST", ControlScope("T-1", "P-1", 9), "user-1", "show schedule",
        constraints={"snapshot_id": "S-COST"},
    )
    auth = AuthorizationContext("T-1", "P-1", "user-1", frozenset({"viewer"}))
    return conn, repo, registry, leveling, cost_inputs, request, auth, context, snapshot


def _cost_error_code(exc):
    return getattr(exc, "code", None) or str(exc)


def test_query_requires_bound_cost_inputs_when_snapshot_recalculates_costs():
    conn, repo, registry, leveling, _cost_inputs, request, auth, context, _snapshot = (
        _cost_recalculation_case()
    )
    service = AuthoritativeScheduleQueryApplicationService(
        AuthoritativeScheduleQueryProvider(
            repo, lambda: registry, leveling_input_resolver=lambda *_: leveling
        ),
        RoleBasedAuthorizationPolicy({"viewer": frozenset({Permission.PROJECT_READ})}),
    )
    try:
        service.execute(request, auth_context=auth, calculation_context=context)
    except Exception as exc:
        assert _cost_error_code(exc) == "SCHEDULE_COST_INPUTS_REQUIRED", exc
    else:
        raise AssertionError(
            "provider evaluated a cost-recalculation snapshot without cost inputs"
        )
    conn.close()


def test_query_passes_application_bound_cost_inputs_to_the_evaluator():
    conn, repo, registry, leveling, cost_inputs, request, auth, context, snapshot = (
        _cost_recalculation_case()
    )
    calls = []

    def resolve_cost_inputs(loaded_snapshot, loaded_context, loaded_auth_context):
        calls.append(
            (
                loaded_snapshot.snapshot_hash,
                loaded_context.calculation_identity,
                loaded_auth_context,
            )
        )
        return cost_inputs

    service = AuthoritativeScheduleQueryApplicationService(
        AuthoritativeScheduleQueryProvider(
            repo,
            lambda: registry,
            leveling_input_resolver=lambda *_: leveling,
            cost_inputs_resolver=resolve_cost_inputs,
        ),
        RoleBasedAuthorizationPolicy({"viewer": frozenset({Permission.PROJECT_READ})}),
    )

    answer = service.execute(request, auth_context=auth, calculation_context=context)

    assert calls == [(snapshot.snapshot_hash, context.calculation_identity, auth)]
    assert answer.data["activity_count"] == 1
    assert answer.data["project_finish"] == "2026-09-22"
    conn.close()
