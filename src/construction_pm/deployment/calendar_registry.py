"""Fail-closed PostgreSQL calendar registry for the production runtime.

The schedule evaluator needs every persisted calendar, its work-hour overrides
and its exception layers in one resolver registry. The preview runtime built
that registry from SQLite; production had a factory that raised
``SCHEDULE_QUERY_NOT_DEPLOYED``, so every schedule calculation answered 503 and
no float or critical path could exist. This module reads the same durable
tables through the PostgreSQL repositories and fails closed on any calendar the
evaluator could not honour.
"""

from __future__ import annotations

from typing import Any

from ..backend_p0.models import BackendScope
from ..calendar_exception_kernel import persisted_exception_to_kernel
from ..calendar_exception_repository import PostgresCalendarExceptionRepository
from ..calendar_master_repository import PostgresCalendarMasterRepository
from ..calendar_snapshot_repository import PostgresCalendarSnapshotRepository
from ..calendar_work_hours_repository import PostgresCalendarWorkHourRepository
from ..p6_versioned_resource_calendar_resolver import apply_weekly_work_hour_rules
from ..scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from ..scheduling.calendar_context import (
    CalendarReference,
    CalendarResolverRegistry,
)
from ..scheduling.calendar_exception_overlay import CalendarExceptionLayers
from ..scheduling.calendar_system import CalendarSystem
from ..scheduling.time_calendar import (
    TimeAwareWorkingTimeResolver,
    WorkingTimeCalendar,
)

_WORK_HOUR_KINDS = (
    "standard_work_week",
    "standard_detailed_work_hours",
    "detailed_work_hours",
    "total_work_hours",
)


class CalendarRegistryError(ValueError):
    """A persisted calendar cannot be consumed by the evaluator."""


def build_postgres_calendar_registry(connection: Any) -> CalendarResolverRegistry:
    """Read every persisted calendar definition into one fail-closed registry.

    Calendar exceptions become local exception layers and persisted work-hour
    rules are applied to the stored snapshot, so a workweek edit changes the
    resolver the schedule actually uses. Working-day and working-time calendars
    are both registered; base-calendar references are bound after every
    calendar has been read, so row order cannot matter.
    """

    master_repository = PostgresCalendarMasterRepository(connection)
    snapshot_repository = PostgresCalendarSnapshotRepository(connection)
    work_hour_repository = PostgresCalendarWorkHourRepository(connection)
    exception_repository = PostgresCalendarExceptionRepository(connection)

    scopes = connection.execute(
        "SELECT DISTINCT tenant_id, project_id, project_revision FROM calendar_master "
        "ORDER BY tenant_id, project_id, project_revision"
    ).fetchall()

    day_resolvers: dict[str, WorkingTimeResolver] = {}
    time_resolvers: dict[str, TimeAwareWorkingTimeResolver] = {}
    canonical_by_key: dict[str, dict[str, object]] = {}
    exception_layers: dict[str, CalendarExceptionLayers] = {}
    exception_signature_by_key: dict[str, tuple[dict[str, object], ...]] = {}
    base_references: dict[str, CalendarReference] = {}
    pending_bases: list[tuple[str, str, str, str]] = []

    for tenant_id, project_id, revision in scopes:
        scope = BackendScope(str(tenant_id), str(project_id), int(revision))
        for calendar in master_repository.list(scope):
            key = f"{calendar.calendar_id}@{calendar.calendar_version}"
            if calendar.kind not in {"working-day", "working-time"}:
                raise CalendarRegistryError(
                    f"CALENDAR_KIND_UNSUPPORTED:{key}:{calendar.kind}"
                )
            record = snapshot_repository.get(calendar)
            if record is None:
                # A master without a stored definition cannot be consumed and
                # cannot be referenced either: the input composer rejects a
                # settings calendar or activity assignment that points at it,
                # so publication fails closed there. Skipping it here keeps one
                # unrelated empty calendar from breaking every other project's
                # schedule read in the same database.
                continue
            try:
                definition = (
                    WorkingTimeCalendar.from_canonical_snapshot(record.snapshot)
                    if calendar.kind == "working-time"
                    else WorkingCalendar.from_canonical_snapshot(record.snapshot)
                )
            except (TypeError, ValueError) as exc:
                raise CalendarRegistryError(
                    f"CALENDAR_SNAPSHOT_INVALID:{key}"
                ) from exc

            rules = {
                kind: tuple(
                    work_hour_repository.list(
                        scope, calendar.calendar_id, calendar.calendar_version, kind
                    )
                )
                for kind in _WORK_HOUR_KINDS
            }
            try:
                definition, _ = apply_weekly_work_hour_rules(definition, rules)
            except ValueError as exc:
                raise CalendarRegistryError(
                    f"CALENDAR_WORK_HOURS_INVALID:{key}:{exc}"
                ) from exc

            canonical = definition.canonical_snapshot()
            existing = canonical_by_key.get(key)
            if existing is not None and existing != canonical:
                raise CalendarRegistryError(f"CALENDAR_CONFLICT:{key}")
            canonical_by_key[key] = canonical
            if calendar.kind == "working-time":
                time_resolvers[key] = TimeAwareWorkingTimeResolver(definition)
            else:
                day_resolvers[key] = WorkingTimeResolver(definition)

            if (
                calendar.base_calendar_id is not None
                or calendar.base_calendar_version is not None
            ):
                if not calendar.base_calendar_id or not calendar.base_calendar_version:
                    raise CalendarRegistryError(f"CALENDAR_INHERITANCE_INVALID:{key}")
                pending_bases.append(
                    (
                        key,
                        calendar.base_calendar_id,
                        calendar.base_calendar_version,
                        definition.system.value,
                    )
                )

            persisted = exception_repository.list(
                scope, calendar.calendar_id, calendar.calendar_version
            )
            if not persisted:
                continue
            try:
                local_exceptions = tuple(
                    persisted_exception_to_kernel(item) for item in persisted
                )
            except ValueError as exc:
                raise CalendarRegistryError(
                    f"CALENDAR_EXCEPTION_INVALID:{key}:{exc}"
                ) from exc
            signature = tuple(item.canonical_snapshot() for item in persisted)
            previous = exception_signature_by_key.get(key)
            if previous is not None and previous != signature:
                raise CalendarRegistryError(f"CALENDAR_EXCEPTION_CONFLICT:{key}")
            exception_signature_by_key[key] = signature
            exception_layers[key] = CalendarExceptionLayers(local=local_exceptions)

    kinds_by_key = {
        **{key: "working-time" for key in time_resolvers},
        **{key: "working-day" for key in day_resolvers},
    }
    for key, base_id, base_version, system in pending_bases:
        parent_key = f"{base_id}@{base_version}"
        if parent_key not in kinds_by_key:
            raise CalendarRegistryError(f"CALENDAR_BASE_NOT_FOUND:{key}:{parent_key}")
        base_references[key] = CalendarReference(
            base_id, base_version, kinds_by_key[parent_key], CalendarSystem(system)
        )

    return CalendarResolverRegistry(
        day_resolvers=day_resolvers,
        time_resolvers=time_resolvers,
        exception_layers=exception_layers,
        base_calendar_references=base_references,
    )


__all__ = ["CalendarRegistryError", "build_postgres_calendar_registry"]
