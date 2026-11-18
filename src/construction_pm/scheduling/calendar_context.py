from __future__ import annotations

from datetime import date, datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from decimal import Decimal
from typing import Mapping

from .calendar import WorkingTimeResolver
from .calendar_exception_overlay import CalendarExceptionLayers, overlay_day_resolver, overlay_time_resolver
from .calendar_system import CalendarSystem
from .time_calendar import TimeAwareWorkingTimeResolver


class RelationshipLagCalendar(str, Enum):
    PREDECESSOR = "PREDECESSOR_ACTIVITY_CALENDAR"
    SUCCESSOR = "SUCCESSOR_ACTIVITY_CALENDAR"
    TWENTY_FOUR_HOUR = "24_HOUR_CALENDAR"
    PROJECT_DEFAULT = "PROJECT_DEFAULT_CALENDAR"


class Continuous24HourResolver:
    """Exact continuous 24-hour calendar arithmetic for relationship lag."""

    def normalize_start(self, value: date | datetime) -> date:
        if isinstance(value, datetime):
            return value.date()
        if not isinstance(value, date):
            raise TypeError("calendar date must be date or datetime")
        return value

    def normalize_finish(self, value: date | datetime) -> date:
        if isinstance(value, datetime):
            return value.date()
        if not isinstance(value, date):
            raise TypeError("calendar date must be date or datetime")
        return value

    def next_working_day(self, value: date | datetime) -> date:
        return self.normalize_start(value) + timedelta(days=1)

    def previous_working_day(self, value: date | datetime) -> date:
        return self.normalize_finish(value) - timedelta(days=1)

    def add_working_duration(self, start: date | datetime, duration: Decimal | int | float) -> date:
        units = Decimal(str(duration))
        if not units.is_finite() or units < 0 or units != units.to_integral_value():
            raise ValueError("duration must be a non-negative finite whole working day")
        cursor = self.normalize_start(start)
        remaining = int(units)
        if remaining == 0:
            return cursor
        return cursor + timedelta(days=remaining - 1)

    def subtract_working_duration(self, finish: date | datetime, duration: Decimal | int | float) -> date:
        units = Decimal(str(duration))
        if not units.is_finite() or units < 0 or units != units.to_integral_value():
            raise ValueError("duration must be a non-negative finite whole working day")
        cursor = self.normalize_finish(finish)
        remaining = int(units)
        if remaining == 0:
            return cursor
        return cursor - timedelta(days=remaining - 1)

    def calculate_duration(self, start: date | datetime, finish: date | datetime) -> int:
        start_date = self.normalize_start(start)
        finish_date = self.normalize_finish(finish)
        if finish_date < start_date:
            raise ValueError("finish must not precede start")
        return (finish_date - start_date).days + 1

    @staticmethod
    def _hours_microseconds(value: Decimal | int | float) -> int:
        units = Decimal(str(value))
        if not units.is_finite() or units < 0:
            raise ValueError("hours must be a non-negative finite quantity")
        microseconds = units * Decimal("3600000000")
        if microseconds != microseconds.to_integral_value():
            raise ValueError("hours is more precise than one microsecond")
        return int(microseconds)

    @staticmethod
    def _require_datetime(value: datetime, field_name: str) -> datetime:
        if not isinstance(value, datetime):
            raise TypeError(f"{field_name} must be a datetime")
        return value

    def add_working_hours(self, start: datetime, hours: Decimal | int | float) -> datetime:
        start = self._require_datetime(start, "start")
        return start + timedelta(microseconds=self._hours_microseconds(hours))

    def subtract_working_hours(self, finish: datetime, hours: Decimal | int | float) -> datetime:
        finish = self._require_datetime(finish, "finish")
        return finish - timedelta(microseconds=self._hours_microseconds(hours))

    def calculate_working_hours(self, start: datetime, finish: datetime) -> Decimal:
        start = self._require_datetime(start, "start")
        finish = self._require_datetime(finish, "finish")
        if finish < start:
            raise ValueError("finish must not precede start")
        microseconds = (
            (finish - start).days * 86_400_000_000
            + (finish - start).seconds * 1_000_000
            + (finish - start).microseconds
        )
        return Decimal(microseconds) / Decimal("3600000000")


@dataclass(frozen=True)
class CalendarReference:
    """Stable, portable reference to a versioned scheduling calendar."""

    calendar_id: str
    calendar_version: str
    kind: str = "working-day"
    system: CalendarSystem = CalendarSystem.GREGORIAN

    def __post_init__(self) -> None:
        if not isinstance(self.calendar_id, str) or not self.calendar_id.strip():
            raise ValueError("calendar_id must be a non-empty string")
        if not isinstance(self.calendar_version, str) or not self.calendar_version.strip():
            raise ValueError("calendar_version must be a non-empty string")
        if not isinstance(self.kind, str) or self.kind not in {"working-day", "working-time"}:
            raise ValueError("unsupported calendar kind")
        if not isinstance(self.system, CalendarSystem):
            raise ValueError("system must be a CalendarSystem")


@dataclass(frozen=True)
class SchedulingCalendarContext:
    """Explicit calendar assignment for project, activity and relationship lag."""

    project: CalendarReference
    activity: CalendarReference | None = None
    relationship_lag: CalendarReference | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.project, CalendarReference):
            raise TypeError("project must be a CalendarReference")
        if self.activity is not None and not isinstance(self.activity, CalendarReference):
            raise TypeError("activity must be a CalendarReference or None")
        if self.relationship_lag is not None and not isinstance(self.relationship_lag, CalendarReference):
            raise TypeError("relationship_lag must be a CalendarReference or None")

    def effective_activity(self) -> CalendarReference:
        return self.activity or self.project

    def effective_relationship_lag(self) -> CalendarReference:
        return self.relationship_lag or self.effective_activity()

    def relationship_lag_reference(
        self,
        predecessor: CalendarReference,
        option: RelationshipLagCalendar | None = None,
    ) -> CalendarReference | None:
        selected = option
        if selected is None:
            return self.relationship_lag or self.effective_activity()
        if selected is RelationshipLagCalendar.PREDECESSOR:
            return predecessor
        if selected is RelationshipLagCalendar.SUCCESSOR:
            return self.effective_activity()
        if selected is RelationshipLagCalendar.PROJECT_DEFAULT:
            return self.project
        if selected is RelationshipLagCalendar.TWENTY_FOUR_HOUR:
            return None
        raise ValueError(f"unsupported relationship lag calendar: {selected}")


@dataclass(frozen=True)
class CalendarRegistryEntry:
    """Serializable, version-pinned view of one registered calendar.

    The entry carries the canonical Shared-Core definition plus the exception
    layers and base reference that the registry would apply. It contains no
    resolver and performs no arithmetic, so it can be persisted into an
    offline bundle without changing scheduling semantics.
    """

    reference: CalendarReference
    snapshot: dict[str, object]
    base: CalendarReference | None = None
    local_exceptions: tuple[dict[str, object], ...] = ()
    inherited_exceptions: tuple[dict[str, object], ...] = ()

    @property
    def key(self) -> str:
        return f"{self.reference.calendar_id}@{self.reference.calendar_version}"


class CalendarResolverRegistry:
    """Resolves stable calendar references to authoritative Shared Core resolvers."""

    def __init__(
        self,
        day_resolvers: Mapping[str, WorkingTimeResolver] | None = None,
        time_resolvers: Mapping[str, TimeAwareWorkingTimeResolver] | None = None,
        exception_layers: Mapping[str, CalendarExceptionLayers] | None = None,
        base_calendar_references: Mapping[str, CalendarReference] | None = None,
    ) -> None:
        self._day = dict(day_resolvers or {})
        self._time = dict(time_resolvers or {})
        self._exception_layers = dict(exception_layers or {})
        self._base_calendar_references = dict(base_calendar_references or {})
        # Resolved views are cached because every input mapping is copied here
        # and no mutator exists; the cache therefore cannot go stale.
        self._resolve_cache: dict[tuple[str, str, str, CalendarSystem], object] = {}
        for key, layers in self._exception_layers.items():
            if not isinstance(key, str) or not key.strip():
                raise ValueError("exception layer keys must be non-empty strings")
            if not isinstance(layers, CalendarExceptionLayers):
                raise TypeError("exception layers must be CalendarExceptionLayers")
        for key, parent in self._base_calendar_references.items():
            if not isinstance(key, str) or not key.strip():
                raise ValueError("base calendar reference keys must be non-empty strings")
            if not isinstance(parent, CalendarReference):
                raise TypeError("base calendar references must be CalendarReference values")

    @staticmethod
    def _key(reference: CalendarReference) -> str:
        return f"{reference.calendar_id}@{reference.calendar_version}"

    @staticmethod
    def _split_key(key: str) -> tuple[str, str]:
        if not isinstance(key, str) or "@" not in key:
            raise ValueError(
                f"calendar registry key must be calendar_id@version: {key!r}"
            )
        calendar_id, calendar_version = key.rsplit("@", 1)
        if not calendar_id or not calendar_version:
            raise ValueError(
                f"calendar registry key must be calendar_id@version: {key!r}"
            )
        return calendar_id, calendar_version

    def entries(self) -> tuple[CalendarRegistryEntry, ...]:
        """Return a deterministic, serializable view of every registered calendar.

        Definitions, exception layers and base references are exposed exactly
        as registered. No calculation is performed, and no mutable repository
        is consulted; this is the export seam used by the offline runtime
        boundary.
        """
        entries = [
            self._entry(key, resolver, "working-day")
            for key, resolver in sorted(self._day.items())
        ]
        entries.extend(
            self._entry(key, resolver, "working-time")
            for key, resolver in sorted(self._time.items())
        )
        return tuple(entries)

    def _entry(self, key: str, resolver, kind: str) -> CalendarRegistryEntry:
        calendar_id, calendar_version = self._split_key(key)
        calendar = getattr(resolver, "calendar", None)
        if calendar is None:
            raise ValueError(f"calendar resolver has no definition: {key}")
        layers = self._exception_layers.get(key)
        return CalendarRegistryEntry(
            reference=CalendarReference(
                calendar_id,
                calendar_version,
                kind,
                calendar.system,
            ),
            snapshot=calendar.canonical_snapshot(),
            base=self._base_calendar_references.get(key),
            local_exceptions=(
                () if layers is None
                else tuple(item.canonical_snapshot() for item in layers.local)
            ),
            inherited_exceptions=(
                () if layers is None
                else tuple(item.canonical_snapshot() for item in layers.inherited)
            ),
        )

    @staticmethod
    def _merge_inherited_layers(groups: tuple[tuple, ...]) -> tuple:
        """Merge nearest inherited exception layers first, by date.

        Duplicate dates inside one source layer are invalid. When parent and
        grandparent layers describe the same date, the closest parent wins.
        """
        merged = []
        seen_dates = set()
        for group in groups:
            layer_dates = set()
            for exception in group:
                if exception.date in layer_dates:
                    raise ValueError(
                        f"duplicate calendar exception for {exception.date.isoformat()}"
                    )
                layer_dates.add(exception.date)
                if exception.date not in seen_dates:
                    merged.append(exception)
                    seen_dates.add(exception.date)
        return tuple(merged)

    def _registered_resolver(self, reference: CalendarReference):
        key = self._key(reference)
        if reference.kind == "working-day":
            resolver = self._day.get(key)
            expected_type = WorkingTimeResolver
        else:
            resolver = self._time.get(key)
            expected_type = TimeAwareWorkingTimeResolver
        if resolver is None:
            raise KeyError(f"calendar not registered: {key}")
        if not isinstance(resolver, expected_type):
            raise ValueError(
                f"calendar resolver kind mismatch for {key}: reference={reference.kind}"
            )
        calendar = getattr(resolver, "calendar", None)
        resolver_system = getattr(calendar, "system", None)
        if resolver_system is not None:
            if not isinstance(resolver_system, CalendarSystem):
                raise ValueError(f"invalid resolver calendar system for {key}")
            if resolver_system is not reference.system:
                raise ValueError(
                    f"calendar system mismatch for {key}: "
                    f"reference={reference.system.value}, resolver={resolver_system.value}"
                )
        return resolver

    def _resolved_exception_layers(
        self,
        reference: CalendarReference,
        ancestry: tuple[str, ...] = (),
    ) -> tuple[tuple, tuple]:
        key = self._key(reference)
        if key in ancestry:
            cycle = "->".join((*ancestry, key))
            raise ValueError(f"CALENDAR_INHERITANCE_CYCLE:{cycle}")

        layers = self._exception_layers.get(key)
        local = layers.local if layers is not None else ()
        explicit_inherited = layers.inherited if layers is not None else ()
        parent = self._base_calendar_references.get(key)
        if parent is None:
            # Preserve strict duplicate detection for explicitly supplied inheritance.
            self._merge_inherited_layers((explicit_inherited,))
            return local, tuple(explicit_inherited)

        if parent.kind != reference.kind:
            raise ValueError(f"CALENDAR_INHERITANCE_KIND_MISMATCH:{key}")
        if parent.system is not reference.system:
            raise ValueError(f"CALENDAR_INHERITANCE_SYSTEM_MISMATCH:{key}")

        # Pin the parent version explicitly and fail if its calendar is not registered.
        self._registered_resolver(parent)
        parent_local, parent_inherited = self._resolved_exception_layers(
            parent, (*ancestry, key)
        )
        inherited = self._merge_inherited_layers(
            (tuple(explicit_inherited), parent_local, parent_inherited)
        )
        return tuple(local), inherited

    def resolve(self, reference: CalendarReference):
        # The registry copies every mapping in ``__init__`` and exposes no
        # mutator, so a resolved view is a pure function of the reference.
        # Memoising it keeps the validation and overlay construction identical
        # for the first call and avoids rebuilding them per activity/event.
        key = (
            reference.calendar_id,
            reference.calendar_version,
            reference.kind,
            reference.system,
        )
        cached = self._resolve_cache.get(key)
        if cached is not None:
            return cached
        resolver = self._registered_resolver(reference)
        local, inherited = self._resolved_exception_layers(reference)
        if not local and not inherited:
            result = resolver
        elif reference.kind == "working-day":
            result = overlay_day_resolver(
                resolver,
                local_exceptions=local,
                inherited_exceptions=inherited,
            )
        else:
            result = overlay_time_resolver(
                resolver,
                local_exceptions=local,
                inherited_exceptions=inherited,
            )
        self._resolve_cache[key] = result
        return result

    def resolve_relationship_lag(
        self,
        successor_context: SchedulingCalendarContext,
        predecessor_reference: CalendarReference,
        option: RelationshipLagCalendar | None = None,
    ):
        if option is None and successor_context.relationship_lag is not None:
            return self.resolve(successor_context.relationship_lag)
        selected = option or RelationshipLagCalendar.SUCCESSOR
        reference = successor_context.relationship_lag_reference(
            predecessor_reference, selected
        )
        if reference is None:
            return Continuous24HourResolver()
        return self.resolve(reference)
