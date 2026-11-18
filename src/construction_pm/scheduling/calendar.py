from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import FrozenSet, Iterable, Mapping

from .calendar_system import CalendarSystem, JalaliDate
from .calendar_periods import CalendarTimePeriodFactors


CalendarInputDate = date | JalaliDate


@dataclass(frozen=True)
class WorkingCalendar:
    """Framework-neutral working-day calendar with explicit date-system input.

    The Shared Core stores canonical Gregorian dates for arithmetic. When the
    calendar system is Jalali, public calendar-date inputs and holiday inputs
    are converted to Gregorian at the boundary; weekday and arithmetic rules
    therefore remain identical across calendar systems.
    """

    working_weekdays: FrozenSet[int] = frozenset({0, 1, 2, 3, 4})
    holidays: FrozenSet[date] = field(default_factory=frozenset)
    system: CalendarSystem = CalendarSystem.GREGORIAN
    time_period_factors: CalendarTimePeriodFactors = field(default_factory=CalendarTimePeriodFactors)

    def __post_init__(self) -> None:
        if not isinstance(self.working_weekdays, (frozenset, set)):
            raise ValueError("working_weekdays must be a set of weekday numbers")
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > 6
            for value in self.working_weekdays
        ):
            raise ValueError("working_weekdays must contain integer values from 0 through 6")
        if not isinstance(self.system, CalendarSystem):
            raise ValueError("system must be a CalendarSystem")
        if any(not isinstance(value, date) or isinstance(value, (datetime, JalaliDate)) for value in self.holidays):
            raise ValueError("holidays must contain canonical Gregorian dates")
        if not isinstance(self.time_period_factors, CalendarTimePeriodFactors):
            raise ValueError("time_period_factors must be CalendarTimePeriodFactors")

    @property
    def hours_per_day(self) -> Decimal:
        return self.time_period_factors.hours_per_day

    @property
    def hours_per_week(self) -> Decimal:
        return self.time_period_factors.hours_per_week

    @property
    def hours_per_month(self) -> Decimal:
        return self.time_period_factors.hours_per_month

    @property
    def hours_per_year(self) -> Decimal:
        return self.time_period_factors.hours_per_year

    def canonical_snapshot(self) -> dict[str, object]:
        """Return deterministic, JSON-safe calendar metadata for persistence/sync.

        Dates are stored in canonical Gregorian form; Decimal factors are
        serialized as strings so round-trips do not depend on JSON number
        precision. This is representation metadata only and does not perform
        scheduling calculations.
        """
        return {
            "system": self.system.value,
            "working_weekdays": sorted(self.working_weekdays),
            "holidays": [value.isoformat() for value in sorted(self.holidays)],
            "time_period_factors": {
                "hours_per_day": str(self.hours_per_day),
                "hours_per_week": str(self.hours_per_week),
                "hours_per_month": str(self.hours_per_month),
                "hours_per_year": str(self.hours_per_year),
            },
        }

    @classmethod
    def from_canonical_snapshot(cls, snapshot: Mapping[str, object]) -> "WorkingCalendar":
        """Rebuild a calendar from its deterministic canonical snapshot."""
        if not isinstance(snapshot, Mapping):
            raise ValueError("calendar snapshot must be a mapping")
        try:
            system = CalendarSystem(str(snapshot["system"]))
            weekdays_raw = snapshot["working_weekdays"]
            holidays_raw = snapshot["holidays"]
            factors_raw = snapshot["time_period_factors"]
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError("invalid calendar snapshot") from exc

        if not isinstance(weekdays_raw, (list, tuple)):
            raise ValueError("working_weekdays must be a list")
        if not isinstance(holidays_raw, (list, tuple)):
            raise ValueError("holidays must be a list")
        if not isinstance(factors_raw, Mapping):
            raise ValueError("time_period_factors must be a mapping")

        try:
            weekdays = frozenset(int(value) for value in weekdays_raw)
            holidays = frozenset(date.fromisoformat(str(value)) for value in holidays_raw)
            factors = CalendarTimePeriodFactors(
                hours_per_day=str(factors_raw["hours_per_day"]),
                hours_per_week=str(factors_raw["hours_per_week"]),
                hours_per_month=str(factors_raw["hours_per_month"]),
                hours_per_year=str(factors_raw["hours_per_year"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("invalid calendar snapshot") from exc

        return cls(
            working_weekdays=weekdays,
            holidays=holidays,
            system=system,
            time_period_factors=factors,
        )

    @classmethod
    def from_calendar_dates(
        cls,
        *,
        system: CalendarSystem,
        working_weekdays: FrozenSet[int] = frozenset({0, 1, 2, 3, 4}),
        holidays: Iterable[CalendarInputDate] = (),
    ) -> "WorkingCalendar":
        """Build a calendar from dates expressed in the selected system."""
        canonical_holidays = set()
        for value in holidays:
            if isinstance(value, JalaliDate):
                canonical_holidays.add(value.to_gregorian())
            elif isinstance(value, date) and not isinstance(value, datetime):
                canonical_holidays.add(value)
            else:
                raise TypeError("holidays must contain date or JalaliDate values")
        canonical_holidays = frozenset(canonical_holidays)
        return cls(
            working_weekdays=working_weekdays,
            holidays=canonical_holidays,
            system=system,
        )

    def to_gregorian(self, value: CalendarInputDate) -> date:
        if type(value) is date:
            return value
        if isinstance(value, JalaliDate):
            if self.system is not CalendarSystem.JALALI:
                raise ValueError("Jalali input requires a Jalali calendar")
            return value.to_gregorian()
        if not isinstance(value, date) or isinstance(value, datetime):
            raise TypeError("calendar date must be date or JalaliDate")
        return value

    def holiday_from_calendar_date(self, value: CalendarInputDate) -> date:
        return self.to_gregorian(value)

    def is_working_day(self, value: CalendarInputDate) -> bool:
        canonical = self.to_gregorian(value)
        return canonical.weekday() in self.working_weekdays and canonical not in self.holidays

    def working_day_index(self) -> "_WorkingDayIndex | None":
        """Return an exact index for working-day arithmetic, or ``None``.

        The index is a pure function of ``working_weekdays`` and ``holidays``,
        so it cannot diverge from :meth:`is_working_day`. It is offered only
        when the calendar actually contains working days; a calendar without
        any working day keeps the historical loop behaviour rather than
        gaining a new error path.
        """
        if not self.working_weekdays:
            return None
        return _WorkingDayIndex.build(self.working_weekdays, self.holidays)


_MAX_ORDINAL = date.max.toordinal()


class _WorkingDayIndex:
    """Exact working-day arithmetic over integer ordinals for one calendar.

    Every operation here is a closed form over the calendar's own definition
    (working weekdays and holiday dates), not an approximation:

    * ``is_working`` is the same predicate as ``WorkingCalendar.is_working_day``
      expressed on ordinals (``weekday == (ordinal - 1) % 7``, holidays as
      ordinals, which compares and hashes identically to the dates);
    * ``rank`` counts working days in ``[1, ordinal]`` as
      ``weekday_count - holiday_count`` where only holidays that fall on a
      working weekday are counted (a holiday on a weekend removes nothing);
    * ``add``/``subtract`` invert ``rank`` with a bracket derived from the day
      arithmetic and a few bisection steps, so cumulative quantities replace
      day-by-day stepping.

    ``next``/``previous``/``normalize`` need at most a few steps and use the
    direct predicate instead, which is cheaper than a rank inversion.
    """

    __slots__ = ("_mask", "_holidays", "_holiday_count", "_per_week", "_prefix")

    def __init__(self, weekdays: FrozenSet[int], holiday_ordinals: tuple[int, ...]) -> None:
        self._mask = tuple(index in weekdays for index in range(7))
        self._holidays = frozenset(holiday_ordinals)
        self._holiday_count = holiday_ordinals
        self._per_week = len(weekdays)
        prefix = [0]
        for flag in self._mask:
            prefix.append(prefix[-1] + (1 if flag else 0))
        self._prefix = tuple(prefix)

    @classmethod
    def build(cls, weekdays: FrozenSet[int], holidays: FrozenSet[date]) -> "_WorkingDayIndex":
        effective = sorted(
            ordinal
            for ordinal in (value.toordinal() for value in holidays)
            if (ordinal - 1) % 7 in weekdays
        )
        return cls(weekdays, tuple(effective))

    # -- predicate --------------------------------------------------------

    def is_working(self, ordinal: int) -> bool:
        return self._mask[(ordinal - 1) % 7] and ordinal not in self._holidays

    # -- cumulative counts ------------------------------------------------

    def rank(self, ordinal: int) -> int:
        """Working days in ``[1, ordinal]``."""
        if ordinal <= 0:
            return 0
        if ordinal > _MAX_ORDINAL:
            ordinal = _MAX_ORDINAL
        full, remainder = divmod(ordinal, 7)
        weekdays = full * self._per_week + self._prefix[remainder]
        return weekdays - bisect_right(self._holiday_count, ordinal)

    def _search_rank(self, target: int, low: int, high: int) -> int:
        """Smallest ordinal in ``(low, high]`` whose rank is ``target``.

        The caller derives ``low`` and ``high`` from day arithmetic, so the
        bracket already lies next to the answer and the search visits only the
        few ordinals between the earliest and latest possible results.
        ``rank(low) < target <= rank(high)`` is guaranteed by the caller.
        """
        while low + 1 < high:
            middle = (low + high) // 2
            if self.rank(middle) >= target:
                high = middle
            else:
                low = middle
        return high

    # -- operations -------------------------------------------------------

    def next_working_ordinal(self, ordinal: int) -> int:
        """Smallest working ordinal strictly greater than ``ordinal``."""
        cursor = ordinal + 1
        mask = self._mask
        holidays = self._holidays
        while cursor <= _MAX_ORDINAL:
            if mask[(cursor - 1) % 7] and cursor not in holidays:
                return cursor
            cursor += 1
        raise OverflowError("date value out of range")

    def previous_working_ordinal(self, ordinal: int) -> int:
        """Largest working ordinal strictly less than ``ordinal``."""
        cursor = ordinal - 1
        mask = self._mask
        holidays = self._holidays
        while cursor >= 1:
            if mask[(cursor - 1) % 7] and cursor not in holidays:
                return cursor
            cursor -= 1
        raise OverflowError("date value out of range")

    def normalize_start_ordinal(self, ordinal: int) -> int:
        if self.is_working(ordinal):
            return ordinal
        return self.next_working_ordinal(ordinal)

    def normalize_finish_ordinal(self, ordinal: int) -> int:
        if self.is_working(ordinal):
            return ordinal
        return self.previous_working_ordinal(ordinal)

    def add_working_ordinal(self, start_ordinal: int, days: int) -> int:
        first = self.normalize_start_ordinal(start_ordinal)
        if days == 0:
            return first
        target = self.rank(first) + days - 1
        span = days - 1
        # ``first + span`` is the earliest possible answer; weekend density and
        # holidays can only push it later, which gives a tight upper bracket.
        low = first + span - 1
        high = first + span
        if self._per_week < 7:
            high += -(-span * (7 - self._per_week) // self._per_week)
        previous = first
        while True:
            skipped = bisect_right(self._holiday_count, high) - bisect_right(
                self._holiday_count, previous
            )
            if not skipped:
                break
            previous = high
            high += skipped
        if high > _MAX_ORDINAL:
            high = _MAX_ORDINAL
        while self.rank(high) < target:
            if high >= _MAX_ORDINAL:
                raise OverflowError("date value out of range")
            low = high
            high = min(_MAX_ORDINAL, first + 2 * (high - first) + 7)
        return self._search_rank(target, low, high)

    def subtract_working_ordinal(self, finish_ordinal: int, days: int) -> int:
        last = self.normalize_finish_ordinal(finish_ordinal)
        if days == 0:
            return last
        target = self.rank(last) - days + 1
        if target < 1:
            raise OverflowError("date value out of range")
        span = days - 1
        # Mirror of ``add``: ``last - span`` is the latest possible answer.
        high = last - span
        low = high - 1
        if self._per_week < 7:
            low -= -(-span * (7 - self._per_week) // self._per_week)
        previous = last
        while True:
            skipped = bisect_right(self._holiday_count, previous) - bisect_right(
                self._holiday_count, low
            )
            if not skipped:
                break
            previous = low
            low -= skipped
            if low <= 0:
                low = 0
                break
        while self.rank(low) >= target:
            if low <= 0:
                raise OverflowError("date value out of range")
            high = low
            low = max(0, 2 * low - last - 7)
        return self._search_rank(target, low, high)

    def duration_ordinal(self, start_ordinal: int, finish_ordinal: int) -> int:
        start = self.normalize_start_ordinal(start_ordinal)
        finish = self.normalize_finish_ordinal(finish_ordinal)
        if finish < start:
            raise ValueError("finish must not precede start")
        return self.rank(finish) - self.rank(start) + 1


class WorkingTimeResolver:
    """Single source of truth for working-day arithmetic in the Shared Core.

    When the calendar exposes :meth:`WorkingCalendar.working_day_index` the
    resolver answers working-day questions through that exact index; every
    other calendar object (for example an exception overlay, whose effective
    holidays are not its ``holidays`` attribute) keeps the original day-by-day
    loops verbatim. Both paths compute the same function of the same calendar;
    ``tests/scheduling/test_working_day_index_equivalence.py`` proves it by
    running the loops as an oracle.
    """

    def __init__(self, calendar: WorkingCalendar) -> None:
        self.calendar = calendar
        index_factory = getattr(calendar, "working_day_index", None)
        self._day_index = index_factory() if callable(index_factory) else None

    def is_working_day(self, value: CalendarInputDate) -> bool:
        return self.calendar.is_working_day(value)

    def next_working_day(self, value: CalendarInputDate) -> date:
        canonical = self.calendar.to_gregorian(value)
        if self._day_index is not None:
            return date.fromordinal(
                self._day_index.next_working_ordinal(canonical.toordinal())
            )
        cursor = canonical + timedelta(days=1)
        while not self.is_working_day(cursor):
            cursor += timedelta(days=1)
        return cursor

    def previous_working_day(self, value: CalendarInputDate) -> date:
        canonical = self.calendar.to_gregorian(value)
        if self._day_index is not None:
            return date.fromordinal(
                self._day_index.previous_working_ordinal(canonical.toordinal())
            )
        cursor = canonical - timedelta(days=1)
        while not self.is_working_day(cursor):
            cursor -= timedelta(days=1)
        return cursor

    def normalize_start(self, value: CalendarInputDate) -> date:
        """Move a start date forward to the first working day."""
        canonical = self.calendar.to_gregorian(value)
        if self._day_index is not None:
            return date.fromordinal(
                self._day_index.normalize_start_ordinal(canonical.toordinal())
            )
        cursor = canonical
        while not self.is_working_day(cursor):
            cursor += timedelta(days=1)
        return cursor

    def normalize_finish(self, value: CalendarInputDate) -> date:
        """Move a finish date backward to the last working day."""
        canonical = self.calendar.to_gregorian(value)
        if self._day_index is not None:
            return date.fromordinal(
                self._day_index.normalize_finish_ordinal(canonical.toordinal())
            )
        cursor = canonical
        while not self.is_working_day(cursor):
            cursor -= timedelta(days=1)
        return cursor

    def add_working_duration(self, start: CalendarInputDate, duration: Decimal | int | float) -> date:
        """Return the finish date for a working-day duration."""
        if type(duration) is int:
            if duration < 0:
                raise ValueError("duration must be a non-negative finite whole working day")
            remaining = duration
        else:
            units = Decimal(str(duration))
            if not units.is_finite() or units < 0 or units != units.to_integral_value():
                raise ValueError("duration must be a non-negative finite whole working day")
            remaining = int(units)
        if self._day_index is not None:
            return date.fromordinal(
                self._day_index.add_working_ordinal(
                    self.calendar.to_gregorian(start).toordinal(), remaining
                )
            )
        cursor = self.normalize_start(start)
        if remaining == 0:
            return cursor
        for _ in range(remaining - 1):
            cursor = self.next_working_day(cursor)
        return cursor

    def subtract_working_duration(self, finish: CalendarInputDate, duration: Decimal | int | float) -> date:
        """Return the start date corresponding to a working-day duration."""
        if type(duration) is int:
            if duration < 0:
                raise ValueError("duration must be a non-negative finite whole working day")
            remaining = duration
        else:
            units = Decimal(str(duration))
            if not units.is_finite() or units < 0 or units != units.to_integral_value():
                raise ValueError("duration must be a non-negative finite whole working day")
            remaining = int(units)
        if self._day_index is not None:
            return date.fromordinal(
                self._day_index.subtract_working_ordinal(
                    self.calendar.to_gregorian(finish).toordinal(), remaining
                )
            )
        cursor = self.normalize_finish(finish)
        if remaining == 0:
            return cursor
        for _ in range(remaining - 1):
            cursor = self.previous_working_day(cursor)
        return cursor

    def calculate_duration(self, start: CalendarInputDate, finish: CalendarInputDate) -> int:
        """Calculate inclusive working-day duration between two activity dates."""
        if self._day_index is not None:
            return self._day_index.duration_ordinal(
                self.calendar.to_gregorian(start).toordinal(),
                self.calendar.to_gregorian(finish).toordinal(),
            )
        start = self.normalize_start(start)
        finish = self.normalize_finish(finish)
        if finish < start:
            raise ValueError("finish must not precede start")
        total = 0
        cursor = start
        while cursor <= finish:
            if self.is_working_day(cursor):
                total += 1
            cursor += timedelta(days=1)
        return total

    def working_days_between(self, start: CalendarInputDate, finish: CalendarInputDate) -> int:
        """Count working days strictly after start and up to finish."""
        start = self.calendar.to_gregorian(start)
        finish = self.calendar.to_gregorian(finish)
        if finish < start:
            raise ValueError("finish must not precede start")
        if self._day_index is not None:
            return self._day_index.rank(finish.toordinal()) - self._day_index.rank(
                start.toordinal()
            )
        total = 0
        cursor = start + timedelta(days=1)
        while cursor <= finish:
            if self.is_working_day(cursor):
                total += 1
            cursor += timedelta(days=1)
        return total
