from __future__ import annotations

"""Authoritative effective-day projection for one versioned P6 calendar.

The Gantt may shade only days the persisted calendar says are non-working.
Weekends and stored holidays already travel with the immutable snapshot, but
persisted ``calendar_exception`` rows live in a separate, mutable store and a
calendar may inherit them from a base calendar. Classifying those dates in the
browser would duplicate the Shared Core resolution rules, so this projection
asks the very resolvers the scheduler uses and returns only the dates whose
working state an exception changes.

The response is deliberately small: it lists exception dates, not a date range,
so a chart can zoom anywhere without asking for a new window. It never invents a
calendar, a workweek or a missing exception layer; anything it cannot resolve
fails closed with a stable error code.
"""

from dataclasses import dataclass
from datetime import date
from typing import Any

from .application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)
from .backend_p0.models import BackendScope
from .calendar_exception_kernel import (
    CalendarExceptionKernelError,
    persisted_exception_to_kernel,
)
from .calendar_exception_repository import CalendarExceptionRepository
from .calendar_master_repository import (
    CalendarMaster,
    CalendarMasterRepository,
    CalendarPersistenceError,
)
from .calendar_snapshot_repository import CalendarSnapshotRepository
from .calendar_work_hours_repository import CalendarWorkHourRepository
from .p6_versioned_resource_calendar_resolver import (
    P6ResourceCalendarResolutionError,
    apply_weekly_work_hour_rules,
)
from .scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from .scheduling.calendar_context import CalendarReference, CalendarResolverRegistry
from .scheduling.calendar_exception_overlay import CalendarExceptionLayers
from .scheduling.calendar_system import CalendarSystem
from .scheduling.time_calendar import TimeAwareWorkingTimeResolver, WorkingTimeCalendar

P6_CALENDAR_DAY_FACTS_VERSION = "p6-calendar-day-facts.v1"
P6_CALENDAR_DAY_FACTS_KIND = "calendar_day_facts"

_WORK_HOUR_KINDS = (
    "standard_work_week",
    "standard_detailed_work_hours",
    "detailed_work_hours",
    "total_work_hours",
)


class CalendarDayFactsError(ValueError):
    """A persisted calendar cannot be projected without guessing."""


def _key(calendar: CalendarMaster) -> str:
    return f"{calendar.calendar_id}@{calendar.calendar_version}"


def _authorize(
    scope: BackendScope,
    auth_context: AuthorizationContext,
    policy: AuthorizationPolicy,
) -> None:
    scope.validate()
    auth_context.validate()
    if scope.tenant_id != auth_context.tenant_id or scope.project_id != auth_context.project_id:
        raise AuthorizationError("CROSS_SCOPE_ACCESS")
    if not policy.is_allowed(auth_context, Permission.PROJECT_READ):
        raise AuthorizationError("authorization denied for permission=project.read")


def _scope_payload(scope: BackendScope) -> dict[str, object]:
    return {
        "tenant_id": scope.tenant_id,
        "project_id": scope.project_id,
        "project_revision": scope.project_revision,
    }


@dataclass(frozen=True)
class P6CalendarDayFactsAPI:
    """Project, for one calendar version, which dates an exception changes."""

    calendar_repository: CalendarMasterRepository
    snapshot_repository: CalendarSnapshotRepository
    exception_repository: CalendarExceptionRepository
    work_hours_repository: CalendarWorkHourRepository
    authorization_policy: AuthorizationPolicy

    def get_day_facts(
        self,
        scope: BackendScope,
        calendar_id: str,
        calendar_version: str,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _authorize(scope, auth_context, self.authorization_policy)
        if not isinstance(calendar_id, str) or not calendar_id.strip():
            raise CalendarPersistenceError("INVALID_CALENDAR_REFERENCE")
        if not isinstance(calendar_version, str) or not calendar_version.strip():
            raise CalendarPersistenceError("INVALID_CALENDAR_REFERENCE")

        chain = self._resolve_chain(scope, calendar_id, calendar_version)
        registry, layers, system_by_key = self._build_registry(scope, chain)
        root = chain[0]
        reference = CalendarReference(
            root.calendar_id,
            root.calendar_version,
            root.kind,
            system_by_key[_key(root)],
        )
        resolver = registry.resolve(reference)

        dates = sorted({item.date for layer in layers.values() for item in layer.local})
        overrides = [self._override(resolver, root.kind, day) for day in dates]

        return {
            "contract_version": P6_CALENDAR_DAY_FACTS_VERSION,
            "kind": P6_CALENDAR_DAY_FACTS_KIND,
            "scope": _scope_payload(scope),
            "calendar": {
                "calendar_id": root.calendar_id,
                "calendar_version": root.calendar_version,
                "kind": root.kind,
                "system": system_by_key[_key(root)].value,
                "record_revision": root.record_revision,
            },
            "overrides": overrides,
        }

    def _resolve_chain(
        self,
        scope: BackendScope,
        calendar_id: str,
        calendar_version: str,
    ) -> list[CalendarMaster]:
        chain: list[CalendarMaster] = []
        seen: set[tuple[str, str]] = set()
        current_id, current_version = calendar_id, calendar_version
        while True:
            identity = (current_id, current_version)
            if identity in seen:
                raise CalendarPersistenceError("CALENDAR_INHERITANCE_CYCLE")
            seen.add(identity)
            master = self.calendar_repository.get(scope, current_id, current_version)
            if master is None:
                code = "CALENDAR_NOT_FOUND" if not chain else "BASE_CALENDAR_NOT_FOUND"
                raise CalendarPersistenceError(code)
            if master.scope != scope:
                raise CalendarPersistenceError("CALENDAR_SCOPE_MISMATCH")
            chain.append(master)
            if master.base_calendar_id is None and master.base_calendar_version is None:
                break
            if not master.base_calendar_id or not master.base_calendar_version:
                raise CalendarPersistenceError("INCOMPLETE_BASE_CALENDAR_REFERENCE")
            current_id, current_version = master.base_calendar_id, master.base_calendar_version
        return chain

    def _build_registry(
        self,
        scope: BackendScope,
        chain: list[CalendarMaster],
    ) -> tuple[
        CalendarResolverRegistry,
        dict[str, CalendarExceptionLayers],
        dict[str, CalendarSystem],
    ]:
        day_resolvers: dict[str, WorkingTimeResolver] = {}
        time_resolvers: dict[str, TimeAwareWorkingTimeResolver] = {}
        exception_layers: dict[str, CalendarExceptionLayers] = {}
        system_by_key: dict[str, CalendarSystem] = {}

        for master in chain:
            key = _key(master)
            record = self.snapshot_repository.get(master)
            if record is None:
                raise CalendarPersistenceError("CALENDAR_SNAPSHOT_NOT_FOUND")
            try:
                definition = (
                    WorkingTimeCalendar.from_canonical_snapshot(record.snapshot)
                    if master.kind == "working-time"
                    else WorkingCalendar.from_canonical_snapshot(record.snapshot)
                )
            except (TypeError, ValueError) as exc:
                raise CalendarPersistenceError("INVALID_CALENDAR_SNAPSHOT") from exc

            rules = {
                kind: tuple(
                    self.work_hours_repository.list(
                        scope, master.calendar_id, master.calendar_version, kind
                    )
                )
                for kind in _WORK_HOUR_KINDS
            }
            try:
                definition, _ = apply_weekly_work_hour_rules(definition, rules)
            except (P6ResourceCalendarResolutionError, ValueError) as exc:
                raise CalendarDayFactsError(str(exc)) from exc

            if master.kind == "working-time":
                time_resolvers[key] = TimeAwareWorkingTimeResolver(definition)
            else:
                day_resolvers[key] = WorkingTimeResolver(definition)
            system_by_key[key] = definition.system

            persisted = self.exception_repository.list(
                scope, master.calendar_id, master.calendar_version
            )
            if not persisted:
                continue
            try:
                local = tuple(persisted_exception_to_kernel(item) for item in persisted)
            except CalendarExceptionKernelError as exc:
                raise CalendarDayFactsError(str(exc)) from exc
            exception_layers[key] = CalendarExceptionLayers(local=local)

        base_references: dict[str, CalendarReference] = {}
        for index in range(len(chain) - 1):
            child = chain[index]
            parent = chain[index + 1]
            base_references[_key(child)] = CalendarReference(
                parent.calendar_id,
                parent.calendar_version,
                parent.kind,
                system_by_key[_key(parent)],
            )

        registry = CalendarResolverRegistry(
            day_resolvers=day_resolvers,
            time_resolvers=time_resolvers,
            exception_layers=exception_layers,
            base_calendar_references=base_references,
        )
        return registry, exception_layers, system_by_key

    @staticmethod
    def _override(resolver: object, kind: str, day: date) -> dict[str, object]:
        calendar_view = getattr(resolver, "calendar", None)
        effective = getattr(calendar_view, "effective_rule", None)
        if callable(effective):
            rule = effective(day)
            working = bool(rule.is_working)
            source = str(rule.source)
        elif kind == "working-time":
            intervals_for = getattr(resolver, "intervals_for", None)
            if not callable(intervals_for):
                raise CalendarDayFactsError("CALENDAR_RESOLVER_UNSUPPORTED")
            working = bool(intervals_for(day))
            source = "standard"
        else:
            raise CalendarDayFactsError("CALENDAR_RESOLVER_UNSUPPORTED")
        return {
            "date": day.isoformat(),
            "working": working,
            "source": source,
        }


__all__ = [
    "CalendarDayFactsError",
    "P6_CALENDAR_DAY_FACTS_KIND",
    "P6_CALENDAR_DAY_FACTS_VERSION",
    "P6CalendarDayFactsAPI",
]
