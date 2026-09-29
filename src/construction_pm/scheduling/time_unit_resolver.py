from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from decimal import Decimal

from .calendar_context import CalendarReference, CalendarResolverRegistry
from .time_duration import DurationUnit, LagQuantity, TimeQuantity


@dataclass(frozen=True)
class CalendarAwareResolver:
    """Unit-aware adapter over a versioned scheduling calendar resolver.

    Working-day arithmetic stays date based; working-time arithmetic stays
    interval based. No fixed hours-per-day conversion is performed.
    """

    reference: CalendarReference
    resolver: object

    @property
    def kind(self) -> str:
        return self.reference.kind

    @property
    def is_working_day_calendar(self) -> bool:
        return self.kind == "working-day"

    def normalize_start(self, value: datetime) -> datetime:
        if self.is_working_day_calendar:
            return datetime.combine(self.resolver.normalize_start(value.date()), time.min)
        return self.resolver.normalize_start(value)

    def normalize_finish(self, value: datetime) -> datetime:
        if self.is_working_day_calendar:
            return datetime.combine(self.resolver.normalize_finish(value.date()), time.min)
        return self.resolver.normalize_finish(value)

    def add_duration(self, start: datetime, duration: TimeQuantity) -> datetime:
        if self.is_working_day_calendar:
            if duration.unit is not DurationUnit.WORKING_DAY:
                raise ValueError("working-day calendar requires working-day duration")
            return datetime.combine(
                self.resolver.add_working_duration(start.date(), int(duration.value)),
                time.min,
            )
        if duration.unit is not DurationUnit.WORKING_HOUR:
            raise ValueError("working-time calendar requires working-hour duration")
        return self.resolver.add_working_hours(start, duration.value)

    def subtract_duration(self, finish: datetime, duration: TimeQuantity) -> datetime:
        if self.is_working_day_calendar:
            if duration.unit is not DurationUnit.WORKING_DAY:
                raise ValueError("working-day calendar requires working-day duration")
            return datetime.combine(
                self.resolver.subtract_working_duration(finish.date(), int(duration.value)),
                time.min,
            )
        if duration.unit is not DurationUnit.WORKING_HOUR:
            raise ValueError("working-time calendar requires working-hour duration")
        return self.resolver.subtract_working_hours(finish, duration.value)

    def calculate_duration(
        self, start: datetime, finish: datetime, unit: DurationUnit
    ) -> Decimal:
        if self.is_working_day_calendar:
            if unit is not DurationUnit.WORKING_DAY:
                raise ValueError("working-day calendar requires working-day duration")
            return Decimal(
                self.resolver.calculate_duration(start.date(), finish.date())
            )
        if unit is not DurationUnit.WORKING_HOUR:
            raise ValueError("working-time calendar requires working-hour duration")
        return self.resolver.calculate_working_hours(start, finish)

    def add_lag(self, anchor: datetime, lag: LagQuantity) -> datetime:
        if self.is_working_day_calendar:
            if lag.unit is not DurationUnit.WORKING_DAY:
                raise ValueError("working-day lag calendar requires working-day lag")
            if lag.value >= 0:
                return datetime.combine(
                    self.resolver.add_working_duration(anchor.date(), int(lag.value)),
                    time.min,
                )
            return datetime.combine(
                self.resolver.subtract_working_duration(anchor.date(), int(-lag.value)),
                time.min,
            )
        if lag.unit is not DurationUnit.WORKING_HOUR:
            raise ValueError("working-time lag calendar requires working-hour lag")
        if lag.value >= 0:
            return self.resolver.add_working_hours(anchor, lag.value)
        return self.resolver.subtract_working_hours(anchor, -lag.value)

    def subtract_lag(self, event: datetime, lag: LagQuantity) -> datetime:
        if self.is_working_day_calendar:
            if lag.unit is not DurationUnit.WORKING_DAY:
                raise ValueError("working-day lag calendar requires working-day lag")
            if lag.value >= 0:
                return datetime.combine(
                    self.resolver.subtract_working_duration(event.date(), int(lag.value)),
                    time.min,
                )
            return datetime.combine(
                self.resolver.add_working_duration(event.date(), int(-lag.value)),
                time.min,
            )
        if lag.unit is not DurationUnit.WORKING_HOUR:
            raise ValueError("working-time lag calendar requires working-hour lag")
        if lag.value >= 0:
            return self.resolver.subtract_working_hours(event, lag.value)
        return self.resolver.add_working_hours(event, -lag.value)


def resolve_calendar_aware(
    registry: CalendarResolverRegistry, reference: CalendarReference
) -> CalendarAwareResolver:
    return CalendarAwareResolver(reference, registry.resolve(reference))
