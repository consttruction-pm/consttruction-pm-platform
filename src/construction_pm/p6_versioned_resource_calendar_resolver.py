from __future__ import annotations

"""Resolve an exact persisted P6 resource calendar into immutable period capacity.

This is an application/repository boundary. It deliberately fails closed when
calendar fields cannot be mapped losslessly; it does not invent a default
calendar or a missing version.
"""

import hashlib
import json
from dataclasses import replace
from datetime import date, datetime, time
from decimal import Decimal
from typing import Iterable

from .backend_p0.models import BackendScope
from .calendar_exception_repository import (
    CalendarException as PersistedCalendarException,
    CalendarExceptionRepository,
    EXCEPTION_DETAILED_WORK_HOURS,
    EXCEPTION_NONWORK,
    EXCEPTION_RESET_STANDARD,
    EXCEPTION_TOTAL_WORK_HOURS,
)
from .calendar_master_repository import CalendarMaster, CalendarMasterRepository, CalendarPersistenceError
from .calendar_snapshot_repository import CalendarDefinition, CalendarSnapshotRepository
from .calendar_work_hours_repository import CalendarWorkHourRepository, CalendarWorkHourRule
from .resources.calendar import ResourceCalendar
from .scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from .scheduling.calendar_context import CalendarReference, CalendarResolverRegistry
from .scheduling.calendar_exception_overlay import CalendarExceptionLayers
from .scheduling.calendar_exceptions import (
    CalendarException as CoreCalendarException,
    CalendarExceptionType,
)
from .scheduling.calendar_system import CalendarSystem
from .scheduling.time_calendar import TimeAwareWorkingTimeResolver, WorkingTimeCalendar


class P6ResourceCalendarResolutionError(ValueError):
    """A persisted calendar cannot be mapped to capacity without guessing."""


def _key(calendar: CalendarMaster) -> str:
    return f"{calendar.calendar_id}@{calendar.calendar_version}"


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _interval_hours(intervals: Iterable[tuple[time, time]]) -> Decimal:
    micros = 0
    for start, end in intervals:
        start_us = ((start.hour * 60 + start.minute) * 60 + start.second) * 1_000_000 + start.microsecond
        end_us = ((end.hour * 60 + end.minute) * 60 + end.second) * 1_000_000 + end.microsecond
        if end_us <= start_us:
            raise P6ResourceCalendarResolutionError("INVALID_WORKING_INTERVAL")
        micros += end_us - start_us
    return Decimal(micros) / Decimal("3600000000")


def _persisted_exception_to_core(item: PersistedCalendarException) -> CoreCalendarException:
    mapping = {
        EXCEPTION_NONWORK: CalendarExceptionType.NONWORK,
        EXCEPTION_TOTAL_WORK_HOURS: CalendarExceptionType.TOTAL_WORK_HOURS,
        EXCEPTION_DETAILED_WORK_HOURS: CalendarExceptionType.DETAILED_WORK_HOURS,
        EXCEPTION_RESET_STANDARD: CalendarExceptionType.RESET_TO_STANDARD,
    }
    kind = mapping.get(item.mode)
    if kind is None:
        raise P6ResourceCalendarResolutionError("UNSUPPORTED_CALENDAR_EXCEPTION_MODE")
    try:
        return CoreCalendarException(
            date=item.exception_date,
            kind=kind,
            calendar_system=item.system,
            total_work_hours=(
                None if kind is not CalendarExceptionType.TOTAL_WORK_HOURS
                else Decimal(str(item.total_work_hours))
            ),
            intervals=tuple(item.intervals) if kind is CalendarExceptionType.DETAILED_WORK_HOURS else (),
        )
    except (TypeError, ValueError) as exc:
        raise P6ResourceCalendarResolutionError("INVALID_PERSISTED_CALENDAR_EXCEPTION") from exc


def _load_work_rules(
    scope: BackendScope,
    calendar_id: str,
    calendar_version: str,
    repo: CalendarWorkHourRepository,
) -> dict[str, tuple[CalendarWorkHourRule, ...]]:
    return {
        kind: tuple(repo.list(scope, calendar_id, calendar_version, kind))
        for kind in (
            "standard_work_week",
            "standard_detailed_work_hours",
            "detailed_work_hours",
            "total_work_hours",
        )
    }


def _apply_weekly_rules(
    definition: CalendarDefinition,
    rules: dict[str, tuple[CalendarWorkHourRule, ...]],
) -> tuple[CalendarDefinition, dict[int, Decimal]]:
    """Apply weekday-keyed records, rejecting schema shapes that lose P6 identity."""
    dated = rules["detailed_work_hours"]
    if dated:
        # P6's DetailedWorkHours is keyed by a calendar date. This repository
        # contract stores only weekday, so applying it as a dated exception
        # would guess which dates it affects.
        raise P6ResourceCalendarResolutionError("DATED_DETAILED_WORK_HOURS_REQUIRE_DATE_KEY")

    if rules["total_work_hours"]:
        # This record has no date or weekday identity and is not the P6
        # Hours-per-Time-Period contract. Do not silently treat it as one.
        raise P6ResourceCalendarResolutionError("CALENDAR_TOTAL_WORK_HOURS_MAPPING_UNVERIFIED")

    week = {item.weekday: item for item in rules["standard_work_week"]}
    detailed = {item.weekday: item for item in rules["standard_detailed_work_hours"]}
    if any(day is None for day in week) or any(day is None for day in detailed):
        raise P6ResourceCalendarResolutionError("WEEKDAY_REQUIRED")
    if set(week) - set(range(7)) or set(detailed) - set(range(7)):
        raise P6ResourceCalendarResolutionError("INVALID_WEEKDAY")

    if isinstance(definition, WorkingCalendar) and detailed:
        raise P6ResourceCalendarResolutionError("DETAILED_WORK_HOURS_REQUIRE_WORKING_TIME_CALENDAR")

    weekdays = set(definition.working_weekdays)
    for weekday, rule in week.items():
        if rule.is_working_day is not None:
            if rule.is_working_day:
                weekdays.add(weekday)
            else:
                weekdays.discard(weekday)

    hours_by_weekday: dict[int, Decimal] = {}
    for weekday, rule in week.items():
        if rule.total_work_hours is not None:
            hours_by_weekday[weekday] = Decimal(str(rule.total_work_hours))

    if isinstance(definition, WorkingCalendar):
        return replace(definition, working_weekdays=frozenset(weekdays)), hours_by_weekday

    intervals = dict(definition.daily_intervals)
    for weekday, rule in detailed.items():
        if rule.is_working_day is not None:
            if rule.is_working_day:
                weekdays.add(weekday)
            else:
                weekdays.discard(weekday)
        if rule.intervals:
            # Repository validation guarantees a sorted, non-overlapping set
            # of HH:MM intervals; parsing failures must block capacity output.
            try:
                intervals[weekday] = tuple(
                    (time.fromisoformat(start), time.fromisoformat(end))
                    for start, end in rule.intervals
                )
            except ValueError as exc:
                raise P6ResourceCalendarResolutionError("INVALID_STANDARD_DETAILED_WORK_HOURS") from exc

    for weekday, hours in hours_by_weekday.items():
        detailed_intervals = intervals.get(weekday, ())
        if detailed_intervals and _interval_hours(detailed_intervals) != hours:
            raise P6ResourceCalendarResolutionError("WORK_HOUR_MODE_CONFLICT")

    return replace(
        definition,
        working_weekdays=frozenset(weekdays),
        daily_intervals=intervals,
    ), hours_by_weekday


def _effective_capacity(
    resolver: object,
    reference: CalendarReference,
    period: date,
    hours_by_weekday: dict[int, Decimal],
) -> Decimal:
    if reference.kind == "working-day":
        calendar = getattr(resolver, "calendar", None)
        if calendar is None:
            raise P6ResourceCalendarResolutionError("DAY_CALENDAR_RESOLVER_MISSING_CALENDAR")
        effective_rule = getattr(calendar, "effective_rule", None)
        if callable(effective_rule):
            rule = effective_rule(period)
            if not rule.is_working:
                return Decimal("0")
            if rule.kind is CalendarExceptionType.TOTAL_WORK_HOURS:
                return Decimal(str(rule.total_work_hours or Decimal("0")))
            if rule.kind is CalendarExceptionType.DETAILED_WORK_HOURS:
                return _interval_hours(rule.intervals)
            if rule.kind is not None and rule.kind is not CalendarExceptionType.RESET_TO_STANDARD:
                raise P6ResourceCalendarResolutionError("UNSUPPORTED_EFFECTIVE_CALENDAR_RULE")
            if rule.source == "standard" or rule.kind is CalendarExceptionType.RESET_TO_STANDARD:
                if period.weekday() in hours_by_weekday:
                    return hours_by_weekday[period.weekday()]
                return Decimal(str(calendar.hours_per_day))
            return Decimal(str(rule.total_work_hours or calendar.hours_per_day))
        if not calendar.is_working_day(period):
            return Decimal("0")
        return hours_by_weekday.get(period.weekday(), Decimal(str(calendar.hours_per_day)))

    calendar = getattr(resolver, "calendar", None)
    intervals_for = getattr(calendar, "intervals_for", None)
    if not callable(intervals_for):
        raise P6ResourceCalendarResolutionError("TIME_CALENDAR_RESOLVER_MISSING_INTERVALS")
    intervals = tuple(intervals_for(period))
    interval_hours = _interval_hours(intervals)
    if not intervals:
        return Decimal("0")
    # A Total work hours/day override in the weekday contract can be used only
    # when it agrees with the actual detailed intervals; otherwise the two
    # persisted work-hour modes conflict and must be resolved by the caller.
    hours = hours_by_weekday.get(period.weekday())
    if hours is not None and interval_hours != hours:
        raise P6ResourceCalendarResolutionError("WORK_HOUR_MODE_CONFLICT")
    return interval_hours


def resolve_p6_resource_calendar(
    *,
    scope: BackendScope,
    calendar_id: str,
    calendar_version: str,
    periods: Iterable[date],
    calendar_repository: CalendarMasterRepository,
    snapshot_repository: CalendarSnapshotRepository,
    exception_repository: CalendarExceptionRepository,
    work_hours_repository: CalendarWorkHourRepository,
) -> ResourceCalendar:
    """Resolve exact calendar ID+version into hash-bound, date-specific capacity.

    Scope, version, snapshots, ancestry, exceptions and weekly rule records are
    all bound into the resulting hash. Missing or ambiguous semantics fail closed.
    """
    scope.validate()
    if not isinstance(calendar_id, str) or not calendar_id.strip():
        raise P6ResourceCalendarResolutionError("INVALID_CALENDAR_ID")
    if not isinstance(calendar_version, str) or not calendar_version.strip():
        raise P6ResourceCalendarResolutionError("INVALID_CALENDAR_VERSION")
    requested_periods = tuple(periods)
    if not requested_periods:
        raise P6ResourceCalendarResolutionError("RESOURCE_CALENDAR_PERIODS_REQUIRED")
    if any(not isinstance(value, date) or isinstance(value, datetime) for value in requested_periods):
        raise P6ResourceCalendarResolutionError("INVALID_RESOURCE_CALENDAR_PERIOD")
    if len(set(requested_periods)) != len(requested_periods):
        raise P6ResourceCalendarResolutionError("DUPLICATE_RESOURCE_CALENDAR_PERIOD")

    chain: list[CalendarMaster] = []
    seen: set[tuple[str, str]] = set()
    current_id, current_version = calendar_id, calendar_version
    while True:
        identity = (current_id, current_version)
        if identity in seen:
            raise P6ResourceCalendarResolutionError("CALENDAR_INHERITANCE_CYCLE")
        seen.add(identity)
        master = calendar_repository.get(scope, current_id, current_version)
        if master is None:
            code = "RESOURCE_CALENDAR_NOT_FOUND" if not chain else "BASE_CALENDAR_NOT_FOUND"
            raise P6ResourceCalendarResolutionError(code)
        master.validate()
        if master.scope != scope or master.scope.project_revision != scope.project_revision:
            raise P6ResourceCalendarResolutionError("RESOURCE_CALENDAR_SCOPE_OR_REVISION_MISMATCH")
        chain.append(master)
        if master.base_calendar_id is None:
            break
        if master.base_calendar_version is None:
            raise P6ResourceCalendarResolutionError("INCOMPLETE_BASE_CALENDAR_REFERENCE")
        current_id, current_version = master.base_calendar_id, master.base_calendar_version

    root = chain[0]
    if root.calendar_type not in {"resource", "global"}:
        raise P6ResourceCalendarResolutionError("ACTIVITY_CALENDAR_CANNOT_BACK_RESOURCE_CAPACITY")

    day_resolvers: dict[str, WorkingTimeResolver] = {}
    time_resolvers: dict[str, TimeAwareWorkingTimeResolver] = {}
    exception_layers: dict[str, CalendarExceptionLayers] = {}
    base_refs: dict[str, CalendarReference] = {}
    root_definition: CalendarDefinition | None = None
    root_hours_by_weekday: dict[int, Decimal] = {}
    hash_records: list[dict[str, object]] = []

    for master in chain:
        snapshot = snapshot_repository.get(master)
        if snapshot is None:
            raise P6ResourceCalendarResolutionError(
                f"CALENDAR_SNAPSHOT_NOT_FOUND:{master.calendar_id}@{master.calendar_version}"
            )
        snapshot.validate()
        if snapshot.scope != scope or snapshot.calendar_id != master.calendar_id or snapshot.calendar_version != master.calendar_version:
            raise P6ResourceCalendarResolutionError("CALENDAR_SNAPSHOT_IDENTITY_MISMATCH")
        if snapshot.kind != master.kind:
            raise P6ResourceCalendarResolutionError("CALENDAR_SNAPSHOT_KIND_MISMATCH")

        try:
            definition: CalendarDefinition = (
                WorkingTimeCalendar.from_canonical_snapshot(snapshot.snapshot)
                if master.kind == "working-time"
                else WorkingCalendar.from_canonical_snapshot(snapshot.snapshot)
            )
        except (TypeError, ValueError) as exc:
            raise P6ResourceCalendarResolutionError("INVALID_CALENDAR_SNAPSHOT") from exc

        rules = _load_work_rules(scope, master.calendar_id, master.calendar_version, work_hours_repository)
        definition, hours_by_weekday = _apply_weekly_rules(definition, rules)
        reference = CalendarReference(
            master.calendar_id, master.calendar_version, master.kind, definition.system
        )
        key = _key(master)
        if isinstance(definition, WorkingCalendar):
            day_resolvers[key] = WorkingTimeResolver(definition)
        else:
            time_resolvers[key] = TimeAwareWorkingTimeResolver(definition)

        persisted_exceptions = tuple(
            exception_repository.list(scope, master.calendar_id, master.calendar_version)
        )
        core_exceptions = tuple(_persisted_exception_to_core(item) for item in persisted_exceptions)
        exception_layers[key] = CalendarExceptionLayers(local=core_exceptions)

        if master.base_calendar_id is not None:
            parent = next(
                (
                    item for item in chain
                    if item.calendar_id == master.base_calendar_id
                    and item.calendar_version == master.base_calendar_version
                ),
                None,
            )
            if parent is None:
                raise P6ResourceCalendarResolutionError("BASE_CALENDAR_REFERENCE_NOT_RESOLVED")
            if parent.kind != master.kind:
                raise P6ResourceCalendarResolutionError("CALENDAR_INHERITANCE_KIND_MISMATCH")
            if definition.system != (
                WorkingTimeCalendar.from_canonical_snapshot(
                    snapshot_repository.get(parent).snapshot
                ).system if parent.kind == "working-time"
                else WorkingCalendar.from_canonical_snapshot(
                    snapshot_repository.get(parent).snapshot
                ).system
            ):
                raise P6ResourceCalendarResolutionError("CALENDAR_INHERITANCE_SYSTEM_MISMATCH")
            base_refs[key] = CalendarReference(
                parent.calendar_id, parent.calendar_version, parent.kind, definition.system
            )

        hash_records.append({
            "calendar_id": master.calendar_id,
            "calendar_version": master.calendar_version,
            "kind": master.kind,
            "calendar_type": master.calendar_type,
            "record_revision": master.record_revision,
            "base_calendar_id": master.base_calendar_id,
            "base_calendar_version": master.base_calendar_version,
            "snapshot": definition.canonical_snapshot(),
            "work_hour_rules": {
                kind: [rule.canonical_snapshot() for rule in rules[kind]]
                for kind in sorted(rules)
            },
            "exceptions": [item.canonical_snapshot() for item in persisted_exceptions],
        })

        if master is root:
            root_definition = definition
            root_hours_by_weekday = hours_by_weekday

    registry = CalendarResolverRegistry(
        day_resolvers=day_resolvers,
        time_resolvers=time_resolvers,
        exception_layers=exception_layers,
        base_calendar_references=base_refs,
    )
    assert root_definition is not None
    root_reference = CalendarReference(
        root.calendar_id, root.calendar_version, root.kind, root_definition.system
    )
    try:
        resolver = registry.resolve(root_reference)
        capacity_slices = tuple(sorted(
            (
                period,
                _effective_capacity(resolver, root_reference, period, root_hours_by_weekday),
            )
            for period in requested_periods
        ))
    except (KeyError, TypeError, ValueError) as exc:
        raise P6ResourceCalendarResolutionError(
            f"RESOURCE_CALENDAR_RESOLUTION_FAILED:{exc}"
        ) from exc

    canonical_payload = {
        "scope": {
            "tenant_id": scope.tenant_id,
            "project_id": scope.project_id,
            "project_revision": scope.project_revision,
        },
        "requested_calendar": {"calendar_id": calendar_id, "calendar_version": calendar_version},
        "calendar_chain": hash_records,
        "requested_periods": [value.isoformat() for value in sorted(requested_periods)],
        "effective_capacity_slices": [
            {"period": value.isoformat(), "units": str(units)}
            for value, units in capacity_slices
        ],
    }
    snapshot_hash = hashlib.sha256(_canonical_json(canonical_payload).encode("utf-8")).hexdigest()
    assert isinstance(root_definition, (WorkingCalendar, WorkingTimeCalendar))
    return ResourceCalendar(
        id=calendar_id,
        working_weekdays=frozenset(root_definition.working_weekdays),
        daily_capacity=(
            Decimal(str(root_definition.hours_per_day))
            if isinstance(root_definition, WorkingCalendar)
            else Decimal("0")
        ),
        calendar_version=calendar_version,
        canonical_snapshot_hash=snapshot_hash,
        capacity_slices=capacity_slices,
    )


__all__ = ["P6ResourceCalendarResolutionError", "resolve_p6_resource_calendar"]
