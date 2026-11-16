from __future__ import annotations

import json
import socket
from datetime import date, datetime, timezone

import pytest

from construction_pm.offline_schedule_runtime import (
    OfflineNetworkAccessError,
    OfflineRuntimeError,
    OfflineScheduleBundle,
    OfflineSchedulingRuntime,
    build_offline_bundle,
    deny_network_access,
)
from construction_pm.schedule_evaluator import evaluate_schedule_snapshot
from construction_pm.schedule_input_snapshot_repository import build_snapshot
from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.authoritative_schedule import (
    ActivityCalendarAssignment,
    AuthoritativeScheduleInput,
    AuthoritativeScheduleMode,
)
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.calendar_context import (
    CalendarReference,
    CalendarResolverRegistry,
    SchedulingCalendarContext,
)
from construction_pm.scheduling.calendar_exception_overlay import CalendarExceptionLayers
from construction_pm.scheduling.calendar_exceptions import CalendarException, CalendarExceptionType
from construction_pm.scheduling.calculation_context import CalculationContext
from construction_pm.scheduling.constraints import ActivityConstraint, ConstraintType
from construction_pm.scheduling.relationships import Relationship
from construction_pm.scheduling.time_duration import TimeQuantity
from construction_pm.scheduling.time_forward_pass import TimeActivity, TimeRelationship

from construction_pm.scheduling import benchmark_fixtures


CREATED_AT = datetime(2026, 9, 21, 8, tzinfo=timezone.utc)
CAL = CalendarReference("CAL-1", "1")


def _context(snapshot_id: str, *, revision: int = 3, calendar: CalendarReference = CAL) -> CalculationContext:
    return CalculationContext(
        project_id="P-1",
        project_version=revision,
        calendar_id=calendar.calendar_id,
        calendar_version=calendar.calendar_version,
        rules_version="rules-1",
        engine_version="engine-1",
        timezone="UTC",
        calculation_timestamp="2026-09-21T08:00:00+00:00",
        input_snapshot_id=snapshot_id,
        tenant_id="T-1",
    )


def _date_input(snapshot_id: str = "S-OFFLINE-DATE") -> AuthoritativeScheduleInput:
    return AuthoritativeScheduleInput(
        snapshot_id=snapshot_id,
        tenant_id="T-1",
        project_id="P-1",
        project_revision=3,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=CAL,
        activities=(
            Activity("A", 2),
            Activity("B", 1),
            Activity("C", 3),
            Activity("D", 1),
        ),
        relationships=(
            Relationship("A", "B"),
            Relationship("B", "C"),
            Relationship("C", "D", lag=2),
        ),
        activity_calendar_assignments=(
            ActivityCalendarAssignment("A", CAL),
            ActivityCalendarAssignment("B", CAL),
            ActivityCalendarAssignment("C", CAL),
            ActivityCalendarAssignment("D", CAL),
        ),
        constraints=(
            ActivityConstraint("C", ConstraintType.START_NO_EARLIER_THAN, date(2026, 9, 24)),
        ),
        project_start=date(2026, 9, 21),
    )


def _date_snapshot(snapshot_id: str = "S-OFFLINE-DATE"):
    return build_snapshot(_date_input(snapshot_id), _context(snapshot_id), CREATED_AT)


def _date_registry() -> CalendarResolverRegistry:
    return CalendarResolverRegistry(
        day_resolvers={
            "CAL-1@1": WorkingTimeResolver(
                WorkingCalendar(holidays=frozenset({date(2026, 9, 23)}))
            )
        }
    )


def _time_input(snapshot_id: str = "S-OFFLINE-TIME") -> AuthoritativeScheduleInput:
    reference = CalendarReference("site", "1", "working-time")
    context = SchedulingCalendarContext(project=reference, activity=reference)
    return AuthoritativeScheduleInput(
        snapshot_id=snapshot_id,
        tenant_id="T-1",
        project_id="P-1",
        project_revision=4,
        mode=AuthoritativeScheduleMode.TIME_AWARE,
        project_calendar=reference,
        activities=(
            TimeActivity("A", TimeQuantity.working_hours(16), context),
            TimeActivity("B", TimeQuantity.working_hours(8), context),
        ),
        relationships=(TimeRelationship("A", "B"),),
        activity_calendar_assignments=(),
        project_start=datetime(2026, 1, 5, 8, tzinfo=timezone.utc),
    )


def _time_snapshot(snapshot_id: str = "S-OFFLINE-TIME"):
    reference = CalendarReference("site", "1", "working-time")
    return build_snapshot(
        _time_input(snapshot_id),
        _context(snapshot_id, revision=4, calendar=reference),
        CREATED_AT,
    )


def _time_registry() -> CalendarResolverRegistry:
    return benchmark_fixtures.time_registry()


def _online(snapshot, context, registry):
    return evaluate_schedule_snapshot(snapshot, context, registry)


def test_date_bundle_round_trip_produces_identical_canonical_output():
    snapshot = _date_snapshot()
    context = _context(snapshot.snapshot_id)
    registry = _date_registry()

    online = _online(snapshot, context, registry)
    bundle = build_offline_bundle(snapshot, context, registry)
    restored = OfflineScheduleBundle.from_json(bundle.to_json())
    offline = OfflineSchedulingRuntime(restored).execute()

    assert restored.bundle_hash == bundle.bundle_hash
    assert offline.bundle_hash == bundle.bundle_hash
    assert offline.snapshot_hash == snapshot.snapshot_hash
    assert offline.calculation_run_identity == online.calculation_run_identity
    assert offline.evaluation.date_result == online.date_result


def test_time_aware_bundle_round_trip_produces_identical_canonical_output():
    snapshot = _time_snapshot()
    context = _context(snapshot.snapshot_id, revision=4, calendar=CalendarReference("site", "1", "working-time"))
    registry = _time_registry()

    online = _online(snapshot, context, registry)
    bundle = build_offline_bundle(snapshot, context, registry)
    offline = OfflineSchedulingRuntime.from_json(bundle.to_json()).execute()

    assert offline.calculation_run_identity == online.calculation_run_identity
    assert offline.evaluation.time_activities == online.time_activities


def test_bundle_preserves_calendar_exception_layers_and_inheritance():
    base = CalendarReference("base", "1")
    child = CalendarReference("child", "1")
    registry = CalendarResolverRegistry(
        day_resolvers={
            "base@1": WorkingTimeResolver(WorkingCalendar()),
            "child@1": WorkingTimeResolver(WorkingCalendar()),
        },
        exception_layers={
            "child@1": CalendarExceptionLayers(
                local=(
                    CalendarException(date(2026, 9, 29), CalendarExceptionType.NONWORK),
                )
            )
        },
        base_calendar_references={"child@1": base},
    )
    source = AuthoritativeScheduleInput(
        snapshot_id="S-OFFLINE-CAL",
        tenant_id="T-1",
        project_id="P-1",
        project_revision=5,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=child,
        activities=(Activity("A", 2), Activity("B", 1)),
        relationships=(Relationship("A", "B"),),
        activity_calendar_assignments=(
            ActivityCalendarAssignment("A", child),
            ActivityCalendarAssignment("B", child),
        ),
        project_start=date(2026, 9, 28),
    )
    context = _context("S-OFFLINE-CAL", revision=5, calendar=child)
    snapshot = build_snapshot(source, context, CREATED_AT)

    online = _online(snapshot, context, registry)
    bundle = build_offline_bundle(snapshot, context, registry)
    payload = json.loads(bundle.to_json())
    keys = [item["reference"]["calendar_id"] for item in payload["calendars"]]
    assert keys == ["base", "child"]
    child_entry = next(item for item in payload["calendars"] if item["reference"]["calendar_id"] == "child")
    assert child_entry["base"]["calendar_id"] == "base"
    assert child_entry["local_exceptions"][0]["kind"] == "NONWORK"

    offline = OfflineSchedulingRuntime.from_json(bundle.to_json()).execute()
    assert offline.calculation_run_identity == online.calculation_run_identity
    assert offline.evaluation.date_result.project_finish == online.date_result.project_finish


def test_bundle_is_deterministic_for_the_same_inputs():
    snapshot = _date_snapshot()
    context = _context(snapshot.snapshot_id)
    registry = _date_registry()

    first = build_offline_bundle(snapshot, context, registry)
    second = build_offline_bundle(snapshot, context, registry)
    assert first.to_json() == second.to_json()
    assert first.bundle_hash == second.bundle_hash


def test_missing_calendar_fails_closed_at_bundle_construction():
    snapshot = _date_snapshot()
    context = _context(snapshot.snapshot_id)
    with pytest.raises(OfflineRuntimeError) as caught:
        build_offline_bundle(snapshot, context, CalendarResolverRegistry())
    assert caught.value.code == "OFFLINE_CALENDAR_MISSING"
    assert "CAL-1@1" in str(caught.value)


def test_missing_base_calendar_fails_closed_at_bundle_construction():
    child = CalendarReference("child", "1")
    registry = CalendarResolverRegistry(
        day_resolvers={"child@1": WorkingTimeResolver(WorkingCalendar())},
        base_calendar_references={"child@1": CalendarReference("base", "1")},
    )
    source = AuthoritativeScheduleInput(
        snapshot_id="S-OFFLINE-BASE",
        tenant_id="T-1",
        project_id="P-1",
        project_revision=2,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=child,
        activities=(Activity("A", 1),),
        relationships=(),
        activity_calendar_assignments=(),
        project_start=date(2026, 9, 21),
    )
    context = _context("S-OFFLINE-BASE", revision=2, calendar=child)
    snapshot = build_snapshot(source, context, CREATED_AT)
    with pytest.raises(OfflineRuntimeError) as caught:
        build_offline_bundle(snapshot, context, registry)
    assert caught.value.code == "OFFLINE_CALENDAR_BASE_MISSING"


def test_tampered_snapshot_payload_is_rejected():
    snapshot = _date_snapshot()
    context = _context(snapshot.snapshot_id)
    bundle = build_offline_bundle(snapshot, context, _date_registry())
    payload = json.loads(bundle.to_json())
    payload["snapshot_payload"] = payload["snapshot_payload"].replace(
        '"project_start":"2026-09-21"', '"project_start":"2026-09-22"'
    )
    payload["bundle_hash"] = _rehash(payload)

    with pytest.raises(OfflineRuntimeError) as caught:
        OfflineSchedulingRuntime(OfflineScheduleBundle.from_payload(payload))
    assert caught.value.code == "OFFLINE_SNAPSHOT_HASH_MISMATCH"


def test_tampered_bundle_is_rejected():
    snapshot = _date_snapshot()
    bundle = build_offline_bundle(snapshot, _context(snapshot.snapshot_id), _date_registry())
    payload = json.loads(bundle.to_json())
    payload["snapshot_hash"] = "0" * 64

    with pytest.raises(OfflineRuntimeError) as caught:
        OfflineScheduleBundle.from_payload(payload)
    assert caught.value.code == "OFFLINE_BUNDLE_HASH_MISMATCH"


def test_unsupported_bundle_schema_is_rejected():
    snapshot = _date_snapshot()
    bundle = build_offline_bundle(snapshot, _context(snapshot.snapshot_id), _date_registry())
    payload = json.loads(bundle.to_json())
    payload["schema"] = "construction-pm/offline-schedule-bundle/v2"
    payload["bundle_hash"] = _rehash(payload)

    with pytest.raises(OfflineRuntimeError) as caught:
        OfflineScheduleBundle.from_payload(payload)
    assert caught.value.code == "OFFLINE_BUNDLE_SCHEMA_UNSUPPORTED"


def test_network_guard_denies_connections_and_restores_socket():
    original_connect = socket.socket.connect
    original_create = socket.create_connection
    original_lookup = socket.getaddrinfo

    with pytest.raises(OfflineNetworkAccessError):
        with deny_network_access():
            socket.create_connection(("127.0.0.1", 9), timeout=0.1)
    with pytest.raises(OfflineNetworkAccessError):
        with deny_network_access():
            socket.getaddrinfo("example.invalid", 443)

    assert socket.socket.connect is original_connect
    assert socket.create_connection is original_create
    assert socket.getaddrinfo is original_lookup


def test_execute_holds_the_network_guard(monkeypatch):
    import construction_pm.offline_schedule_runtime as runtime_module

    def _attempt_network(*args, **kwargs):
        socket.create_connection(("127.0.0.1", 9), timeout=0.1)

    original_create = socket.create_connection
    monkeypatch.setattr(runtime_module, "evaluate_schedule_snapshot", _attempt_network)
    snapshot = _date_snapshot()
    bundle = build_offline_bundle(snapshot, _context(snapshot.snapshot_id), _date_registry())
    runtime = OfflineSchedulingRuntime(bundle)

    with pytest.raises(OfflineNetworkAccessError):
        runtime.execute()
    assert socket.create_connection is original_create


def test_leveling_snapshot_is_rejected_explicitly():
    source = _date_input("S-OFFLINE-LEVEL")
    leveling_input = source.__class__(
        **{
            **source.__dict__,
            "snapshot_id": "S-OFFLINE-LEVEL",
            "schedule_options": source.schedule_options.__class__(
                level_all_resources=True
            ),
        }
    )
    context = _context("S-OFFLINE-LEVEL")
    snapshot = build_snapshot(leveling_input, context, CREATED_AT)
    bundle = build_offline_bundle(snapshot, context, _date_registry())
    runtime = OfflineSchedulingRuntime(bundle)

    with pytest.raises(OfflineRuntimeError) as caught:
        runtime.execute()
    assert caught.value.code == "OFFLINE_LEVELING_INPUT_REQUIRED"



def _rehash(payload: dict) -> str:
    import hashlib

    payload = {key: value for key, value in payload.items() if key != "bundle_hash"}
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
