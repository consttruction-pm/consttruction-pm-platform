from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .application.authorization import AuthorizationContext, AuthorizationError, AuthorizationPolicy, Permission
from .backend_p0.models import BackendScope
from .backend_p0.transactions import TransactionManager
from .calendar_exception_repository import CalendarException, CalendarExceptionRepository
from .calendar_master_repository import CalendarMaster, CalendarMasterRepository, CalendarPersistenceError
from .calendar_snapshot_repository import CalendarSnapshotRepository
from .calendar_work_hours_repository import CalendarWorkHourRepository, CalendarWorkHourRule
from .scheduling.calendar import WorkingCalendar
from .scheduling.calendar_system import CalendarSystem
from .scheduling.time_calendar import WorkingTimeCalendar

P6_CALENDAR_API_VERSION = "p6-calendar.v1"
P6_CALENDAR_DEFINITION_VERSION = "p6-calendar-definition.v1"
P6_CALENDAR_TYPES = frozenset({"global", "resource", "project"})
_CALENDAR_SYSTEMS = frozenset({"gregorian", "jalali"})
_DEFINITION_FIELDS = frozenset(
    {"kind", "system", "working_weekdays", "holidays", "daily_intervals", "time_period_factors"}
)


class P6CalendarAPIError(ValueError):
    pass


@dataclass(frozen=True)
class P6CalendarCreateRequest:
    contract_version: str
    calendar_id: str
    calendar_version: str
    calendar_type: str
    kind: str
    name: str
    expected_revision: int | None = None
    base_calendar_id: str | None = None
    base_calendar_version: str | None = None
    system: str | None = None

    def validate(self) -> None:
        if self.contract_version != P6_CALENDAR_API_VERSION:
            raise P6CalendarAPIError("UNSUPPORTED_P6_CALENDAR_API_VERSION")
        if self.calendar_type not in P6_CALENDAR_TYPES:
            raise P6CalendarAPIError("INVALID_CALENDAR_TYPE")
        if self.expected_revision is not None and (
            isinstance(self.expected_revision, bool) or self.expected_revision < 0
        ):
            raise P6CalendarAPIError("INVALID_EXPECTED_REVISION")
        if self.system is not None and self.system not in _CALENDAR_SYSTEMS:
            raise P6CalendarAPIError("INVALID_CALENDAR_SYSTEM")


@dataclass(frozen=True)
class P6CalendarAPI:
    calendar_repository: CalendarMasterRepository
    snapshot_repository: CalendarSnapshotRepository
    exception_repository: CalendarExceptionRepository
    authorization_policy: AuthorizationPolicy
    work_hours_repository: CalendarWorkHourRepository | None = None
    transaction_manager: TransactionManager | None = None

    def list(self, scope: BackendScope, *, auth_context: AuthorizationContext) -> dict[str, Any]:
        self._authorize(scope, auth_context, Permission.PROJECT_READ)
        return self._catalog(scope)

    def get(self, scope: BackendScope, calendar_id: str, calendar_version: str, *, auth_context: AuthorizationContext) -> dict[str, Any] | None:
        self._authorize(scope, auth_context, Permission.PROJECT_READ)
        calendar = self.calendar_repository.get(scope, calendar_id, calendar_version)
        return None if calendar is None else self._calendar_dto(calendar)

    def get_definition(
        self,
        scope: BackendScope,
        calendar_id: str,
        calendar_version: str,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any] | None:
        """Return the stored canonical definition the evaluator consumes.

        A master without a definition returns ``definition: null`` and
        ``schedulable: false`` instead of an invented working week, so a
        half-created calendar can never be mistaken for a usable one.
        """
        self._authorize(scope, auth_context, Permission.PROJECT_READ)
        calendar = self.calendar_repository.get(scope, calendar_id, calendar_version)
        if calendar is None:
            return None
        snapshot = self.snapshot_repository.get(calendar)
        return self._definition_dto(
            calendar, None if snapshot is None else snapshot.snapshot
        )

    def save_definition(
        self,
        scope: BackendScope,
        calendar_id: str,
        calendar_version: str,
        definition: Mapping[str, object],
        *,
        expected_revision: int,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        """Seal a master with its first definition, under optimistic revision.

        A definition is immutable once stored: the published schedule snapshot
        references the exact definition version, so silently rewriting it would
        make an existing calculation unreproducible. A genuine change must
        create a new calendar version. Re-submitting the identical definition is
        idempotent and does not bump the revision.
        """
        self._authorize(scope, auth_context, Permission.PROJECT_WRITE)
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 1:
            raise P6CalendarAPIError("EXPECTED_REVISION_REQUIRED_FOR_DEFINITION")
        master = self.calendar_repository.get(scope, calendar_id, calendar_version)
        if master is None:
            raise CalendarPersistenceError("CALENDAR_NOT_FOUND")
        if master.record_revision != expected_revision:
            raise CalendarPersistenceError("REVISION_CONFLICT")
        parsed = _definition_from_payload(master.kind, definition)
        existing = self.snapshot_repository.get(master)
        if existing is not None:
            if existing.snapshot != parsed.canonical_snapshot():
                raise CalendarPersistenceError("CALENDAR_DEFINITION_IMMUTABLE")
            return self._definition_dto(master, existing.snapshot)
        with self._transaction():
            self.snapshot_repository.save(master, parsed)
            stored = self.calendar_repository.save(
                CalendarMaster(
                    scope=master.scope,
                    calendar_id=master.calendar_id,
                    calendar_version=master.calendar_version,
                    kind=master.kind,
                    name=master.name,
                    base_calendar_id=master.base_calendar_id,
                    base_calendar_version=master.base_calendar_version,
                    calendar_type=master.calendar_type,
                ),
                expected_revision,
            )
        return self._definition_dto(stored, parsed.canonical_snapshot())

    def _resolve_base_calendar(
        self,
        scope: BackendScope,
        request: P6CalendarCreateRequest,
        *,
        target: tuple[str, str] | None = None,
    ) -> CalendarMaster | None:
        """Validate an inheritance reference; ``target`` enables self/cycle checks.

        The V26 edit flow lets a calendar inherit holidays and exceptions from a
        global calendar. The reference must name a stored calendar of the same
        kind with a stored definition, and an update must not point at itself or
        close a chain back onto the edited calendar.
        """
        if request.base_calendar_id is None and request.base_calendar_version is None:
            return None
        if not request.base_calendar_id or not request.base_calendar_version:
            raise P6CalendarAPIError("INCOMPLETE_BASE_CALENDAR_REFERENCE")
        base = self.calendar_repository.get(
            scope, request.base_calendar_id, request.base_calendar_version
        )
        if base is None:
            raise CalendarPersistenceError("BASE_CALENDAR_NOT_FOUND")
        if base.kind != request.kind:
            raise P6CalendarAPIError("BASE_CALENDAR_KIND_MISMATCH")
        if self.snapshot_repository.get(base) is None:
            raise CalendarPersistenceError("BASE_CALENDAR_SNAPSHOT_NOT_FOUND")
        if target is not None:
            if (base.calendar_id, base.calendar_version) == target:
                raise P6CalendarAPIError("CALENDAR_BASE_SELF_REFERENCE")
            seen = {target}
            cursor: CalendarMaster | None = base
            while cursor is not None:
                key = (cursor.calendar_id, cursor.calendar_version)
                if key in seen:
                    raise P6CalendarAPIError("CALENDAR_BASE_CYCLE")
                seen.add(key)
                if cursor.base_calendar_id and cursor.base_calendar_version:
                    cursor = self.calendar_repository.get(
                        scope, cursor.base_calendar_id, cursor.base_calendar_version
                    )
                else:
                    cursor = None
        return base

    def create(self, scope: BackendScope, request: P6CalendarCreateRequest, *, auth_context: AuthorizationContext, definition: Mapping[str, object] | None = None) -> dict[str, Any]:
        request.validate()
        self._authorize(scope, auth_context, Permission.PROJECT_WRITE)
        base = self._resolve_base_calendar(scope, request)
        if definition is not None and base is not None:
            # An inherited calendar already owns a definition (copied from the
            # base). Accepting a second one would leave two sources of truth.
            raise P6CalendarAPIError("CALENDAR_DEFINITION_AND_BASE_ARE_EXCLUSIVE")
        parsed = None
        if definition is not None:
            declared_system = definition.get("system") if isinstance(definition, Mapping) else None
            if request.system is not None and declared_system not in (None, request.system):
                raise P6CalendarAPIError("CALENDAR_SYSTEM_MISMATCH")
            parsed = _definition_from_payload(
                request.kind, definition, default_system=request.system or CalendarSystem.GREGORIAN.value
            )
        calendar = CalendarMaster(
            scope=scope,
            calendar_id=request.calendar_id,
            calendar_version=request.calendar_version,
            kind=request.kind,
            name=request.name,
            base_calendar_id=request.base_calendar_id,
            base_calendar_version=request.base_calendar_version,
            calendar_type=request.calendar_type,
        )
        if parsed is not None:
            # Master and immutable definition commit together: a rejected
            # definition must never leave a bare master behind that looks like
            # a calendar the scheduler could use.
            with self._transaction():
                stored = self.calendar_repository.save(calendar, request.expected_revision)
                self.snapshot_repository.save(stored, parsed)
            return self._calendar_dto(stored)
        if base is None:
            if request.system is not None:
                # A date system belongs to a calendar definition. Creating a
                # bare master without a definition cannot honour the choice.
                raise P6CalendarAPIError("CALENDAR_SYSTEM_REQUIRES_BASE_DEFINITION")
            return self._calendar_dto(self.calendar_repository.save(calendar, request.expected_revision))
        # A new calendar must be resolvable immediately. When a base is chosen
        # the stored definition, work-hour rules and exceptions are copied in
        # the same application transaction so the schedule resolver never sees
        # a master without a snapshot.
        with self._transaction():
            stored = self.calendar_repository.save(calendar, request.expected_revision)
            self._copy_calendar_facts(scope, stored, base, system=request.system)
        return self._calendar_dto(stored)

    def update(self, scope: BackendScope, request: P6CalendarCreateRequest, *, auth_context: AuthorizationContext) -> dict[str, Any]:
        request.validate()
        self._authorize(scope, auth_context, Permission.PROJECT_WRITE)
        if request.expected_revision is None or request.expected_revision < 1:
            raise P6CalendarAPIError("EXPECTED_REVISION_REQUIRED_FOR_UPDATE")
        existing = self.calendar_repository.get(scope, request.calendar_id, request.calendar_version)
        if existing is None:
            raise CalendarPersistenceError("CALENDAR_NOT_FOUND")
        existing_snapshot = self.snapshot_repository.get(existing)
        if existing_snapshot is not None and existing_snapshot.kind != request.kind:
            raise P6CalendarAPIError("CALENDAR_SNAPSHOT_KIND_CONFLICT")
        if request.system is not None and existing_snapshot is not None:
            stored_system = str(existing_snapshot.snapshot.get("system", "gregorian"))
            if stored_system != request.system:
                # The date system changes how typed dates are interpreted, so a
                # stored definition cannot silently switch it during a rename.
                raise P6CalendarAPIError("CALENDAR_SYSTEM_IMMUTABLE")
        self._resolve_base_calendar(
            scope,
            request,
            target=(request.calendar_id, request.calendar_version),
        )
        calendar = CalendarMaster(
            scope=scope,
            calendar_id=request.calendar_id,
            calendar_version=request.calendar_version,
            kind=request.kind,
            name=request.name,
            base_calendar_id=request.base_calendar_id,
            base_calendar_version=request.base_calendar_version,
            calendar_type=request.calendar_type,
        )
        return self._calendar_dto(
            self.calendar_repository.save(calendar, request.expected_revision)
        )

    def delete(self, scope: BackendScope, calendar_id: str, calendar_version: str, *, expected_revision: int, auth_context: AuthorizationContext) -> bool:
        self._authorize(scope, auth_context, Permission.PROJECT_WRITE)
        # Calendar deletion clears the master and all associated rows. Keep
        # those mutations in the same application-owned transaction, just like
        # copy/replace, so any failure rolls the complete deletion back.
        with self._transaction():
            deleter = getattr(self.calendar_repository, "delete", None)
            if deleter is None:
                raise P6CalendarAPIError("CALENDAR_DELETE_NOT_SUPPORTED_BY_REPOSITORY")
            return bool(deleter(scope, calendar_id, calendar_version, expected_revision=expected_revision))

    def copy(self, scope: BackendScope, source_calendar_id: str, source_calendar_version: str, target_calendar_id: str, target_calendar_version: str, *, auth_context: AuthorizationContext) -> dict[str, Any]:
        self._authorize(scope, auth_context, Permission.PROJECT_WRITE)
        with self._transaction():
            source = self.calendar_repository.get(scope, source_calendar_id, source_calendar_version)
            if source is None:
                raise CalendarPersistenceError("CALENDAR_NOT_FOUND")
            if self.calendar_repository.get(scope, target_calendar_id, target_calendar_version) is not None:
                raise CalendarPersistenceError("CALENDAR_ALREADY_EXISTS")
            target = CalendarMaster(
                scope=scope, calendar_id=target_calendar_id, calendar_version=target_calendar_version,
                kind=source.kind, name=source.name, base_calendar_id=source.base_calendar_id,
                base_calendar_version=source.base_calendar_version, calendar_type=source.calendar_type,
            )
            stored = self.calendar_repository.save(target, expected_revision=0)
            self._copy_calendar_facts(scope, stored, source)
            return self._calendar_dto(stored)

    def replace(self, scope: BackendScope, target_calendar_id: str, target_calendar_version: str, source_calendar_id: str, source_calendar_version: str, *, auth_context: AuthorizationContext) -> dict[str, Any]:
        self._authorize(scope, auth_context, Permission.PROJECT_WRITE)
        with self._transaction():
            source = self.calendar_repository.get(scope, source_calendar_id, source_calendar_version)
            if source is None:
                raise CalendarPersistenceError("SOURCE_CALENDAR_NOT_FOUND")
            target = self.calendar_repository.get(scope, target_calendar_id, target_calendar_version)
            if target is None:
                raise CalendarPersistenceError("TARGET_CALENDAR_NOT_FOUND")
            snapshot = self.snapshot_repository.get(source)
            if snapshot is None:
                raise CalendarPersistenceError("SOURCE_CALENDAR_SNAPSHOT_NOT_FOUND")
            target_snapshot = self.snapshot_repository.get(target)
            if target_snapshot is not None and target_snapshot.snapshot != snapshot.snapshot:
                raise CalendarPersistenceError("TARGET_CALENDAR_SNAPSHOT_IMMUTABLE_CONFLICT")
            replacement = CalendarMaster(
                scope=scope, calendar_id=target.calendar_id, calendar_version=target.calendar_version,
                kind=source.kind, name=source.name, base_calendar_id=source.base_calendar_id,
                base_calendar_version=source.base_calendar_version, calendar_type=target.calendar_type,
            )
            stored = self.calendar_repository.save(replacement, expected_revision=target.record_revision)
            self.snapshot_repository.save(stored, _definition_from_snapshot(snapshot.snapshot, source.kind))
            for exception in self.exception_repository.list(scope, source_calendar_id, source_calendar_version):
                self.exception_repository.save(CalendarException(
                    scope, target_calendar_id, target_calendar_version, exception.exception_date,
                    exception.mode, exception.total_work_hours, exception.intervals, exception.system,
                ))
            if self.work_hours_repository is not None:
                for kind in ("standard_work_week", "standard_detailed_work_hours", "detailed_work_hours", "total_work_hours"):
                    for rule in self.work_hours_repository.list(scope, source_calendar_id, source_calendar_version, kind):
                        self.work_hours_repository.save(CalendarWorkHourRule(
                            scope, target_calendar_id, target_calendar_version, rule.kind,
                            rule.weekday, rule.is_working_day, rule.total_work_hours, rule.intervals,
                        ))
            return self._calendar_dto(stored)

    def save_exception(self, exception: CalendarException, *, auth_context: AuthorizationContext) -> dict[str, Any]:
        self._authorize(exception.scope, auth_context, Permission.PROJECT_WRITE)
        stored = self.exception_repository.save(exception)
        return _exception_dto(stored)

    def revise_exception(
        self,
        scope: BackendScope,
        calendar_id: str,
        calendar_version: str,
        exception_date: Any,
        *,
        mode: str,
        total_work_hours: Any,
        intervals: tuple[tuple[Any, Any], ...],
        expected_revision: int,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        """Edit one stored exception behind its record revision.

        The system is taken from the stored row: a Jalali calendar keeps Jalali
        entry semantics, while the canonical date stays ISO Gregorian.
        """
        self._authorize(scope, auth_context, Permission.PROJECT_WRITE)
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 1:
            raise P6CalendarAPIError("EXPECTED_EXCEPTION_REVISION_REQUIRED")
        existing = self.exception_repository.get(scope, calendar_id, calendar_version, exception_date)
        if existing is None:
            raise CalendarPersistenceError("EXCEPTION_NOT_FOUND")
        revised = CalendarException(
            scope, calendar_id, calendar_version, existing.exception_date, mode,
            total_work_hours, intervals, existing.system,
        )
        stored = self.exception_repository.revise(revised, expected_revision=expected_revision)
        return _exception_dto(stored)

    def list_exceptions(self, scope: BackendScope, calendar_id: str, calendar_version: str, *, auth_context: AuthorizationContext) -> tuple[dict[str, Any], ...]:
        self._authorize(scope, auth_context, Permission.PROJECT_READ)
        return tuple(_exception_dto(item) for item in self.exception_repository.list(scope, calendar_id, calendar_version))


    def _copy_calendar_facts(self, scope: BackendScope, target: CalendarMaster, source: CalendarMaster, *, system: str | None = None) -> None:
        """Copy the stored definition, exceptions and work-hour rules to a new master.

        Callers validate the source and open a transaction first, so a partially
        copied calendar is never committed. ``system`` switches the copied
        definition's date system (Gregorian/Jalali); the stored exception dates
        stay canonical ISO dates and only their entry/display interpretation
        changes.
        """
        snapshot = self.snapshot_repository.get(source)
        if snapshot is None:
            raise CalendarPersistenceError("SOURCE_CALENDAR_SNAPSHOT_NOT_FOUND")
        definition = _definition_from_snapshot(snapshot.snapshot, source.kind)
        if system is not None:
            requested = CalendarSystem(system)
            if definition.system is not requested:
                if isinstance(definition, WorkingTimeCalendar):
                    definition = WorkingTimeCalendar(
                        working_weekdays=definition.working_weekdays,
                        holidays=definition.holidays,
                        daily_intervals=definition.daily_intervals,
                        system=requested,
                    )
                else:
                    definition = WorkingCalendar(
                        working_weekdays=definition.working_weekdays,
                        holidays=definition.holidays,
                        system=requested,
                    )
        self.snapshot_repository.save(target, definition)
        for exception in self.exception_repository.list(scope, source.calendar_id, source.calendar_version):
            self.exception_repository.save(CalendarException(
                scope, target.calendar_id, target.calendar_version, exception.exception_date,
                exception.mode, exception.total_work_hours, exception.intervals, exception.system,
            ))
        if self.work_hours_repository is not None:
            for kind in ("standard_work_week", "standard_detailed_work_hours", "detailed_work_hours", "total_work_hours"):
                for rule in self.work_hours_repository.list(scope, source.calendar_id, source.calendar_version, kind):
                    self.work_hours_repository.save(CalendarWorkHourRule(
                        scope, target.calendar_id, target.calendar_version, rule.kind,
                        rule.weekday, rule.is_working_day, rule.total_work_hours, rule.intervals,
                    ))

    def delete_exception(self, scope: BackendScope, calendar_id: str, calendar_version: str, exception_date: Any, *, auth_context: AuthorizationContext) -> bool:
        self._authorize(scope, auth_context, Permission.PROJECT_WRITE)
        return bool(self.exception_repository.delete(scope, calendar_id, calendar_version, exception_date))

    def _transaction(self):
        if self.transaction_manager is None:
            raise P6CalendarAPIError("TRANSACTION_MANAGER_REQUIRED")
        return self.transaction_manager.transaction()

    def _work_hours(self) -> CalendarWorkHourRepository:
        if self.work_hours_repository is None:
            raise P6CalendarAPIError("WORK_HOURS_CONTRACT_NOT_CONFIGURED")
        return self.work_hours_repository

    def save_work_hours(self, rule: CalendarWorkHourRule, *, auth_context: AuthorizationContext) -> dict[str, object]:
        self._authorize(rule.scope, auth_context, Permission.PROJECT_WRITE)
        existing = [
            item for item in self._work_hours().list(rule.scope, rule.calendar_id, rule.calendar_version, rule.kind)
            if item.weekday == rule.weekday
        ]
        with self._transaction():
            stored = self._work_hours().save(rule)
            if not existing:
                # A new work-hour declaration changes the calendar definition;
                # bump the master revision so the definition hash moves and the
                # window can detect the change.
                master = self.calendar_repository.get(rule.scope, rule.calendar_id, rule.calendar_version)
                if master is None:
                    raise CalendarPersistenceError("CALENDAR_NOT_FOUND")
                self.calendar_repository.save(CalendarMaster(
                    scope=master.scope,
                    calendar_id=master.calendar_id,
                    calendar_version=master.calendar_version,
                    kind=master.kind,
                    name=master.name,
                    base_calendar_id=master.base_calendar_id,
                    base_calendar_version=master.base_calendar_version,
                    calendar_type=master.calendar_type,
                ), master.record_revision)
        return stored.canonical_snapshot()

    def list_work_hours(self, scope: BackendScope, calendar_id: str, calendar_version: str, kind: str, *, auth_context: AuthorizationContext) -> tuple[dict[str, object], ...]:
        self._authorize(scope, auth_context, Permission.PROJECT_READ)
        return tuple(item.canonical_snapshot() for item in self._work_hours().list(scope, calendar_id, calendar_version, kind))

    def replace_work_hours(self, rule: CalendarWorkHourRule, *, expected_revision: int, auth_context: AuthorizationContext) -> dict[str, object]:
        """Edit an existing weekday rule and bump the calendar master revision.

        The master revision is the concurrency token for definition changes, so
        a workweek edit is rejected by the same stale-write rule as any other
        calendar update and the resolver's definition hash changes with it.
        """
        self._authorize(rule.scope, auth_context, Permission.PROJECT_WRITE)
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 1:
            raise P6CalendarAPIError("INVALID_EXPECTED_REVISION")
        master = self.calendar_repository.get(rule.scope, rule.calendar_id, rule.calendar_version)
        if master is None:
            raise CalendarPersistenceError("CALENDAR_NOT_FOUND")
        if master.record_revision != expected_revision:
            raise CalendarPersistenceError("REVISION_CONFLICT")
        with self._transaction():
            stored = self._work_hours().replace(rule)
            self.calendar_repository.save(CalendarMaster(
                scope=master.scope,
                calendar_id=master.calendar_id,
                calendar_version=master.calendar_version,
                kind=master.kind,
                name=master.name,
                base_calendar_id=master.base_calendar_id,
                base_calendar_version=master.base_calendar_version,
                calendar_type=master.calendar_type,
            ), expected_revision)
        return stored.canonical_snapshot()

    def _catalog(self, scope: BackendScope) -> dict[str, Any]:
        return {
            "contract_version": P6_CALENDAR_API_VERSION,
            "kind": "calendar_catalog",
            "scope": {"tenant_id": scope.tenant_id, "project_id": scope.project_id, "project_revision": scope.project_revision},
            "calendars": [self._calendar_dto(item) for item in self.calendar_repository.list(scope)],
        }

    def _calendar_dto(self, calendar: CalendarMaster, *, schedulable: bool | None = None) -> dict[str, Any]:
        if schedulable is None:
            schedulable = self.snapshot_repository.get(calendar) is not None
        return {
            "contract_version": P6_CALENDAR_API_VERSION,
            "calendar_id": calendar.calendar_id,
            "calendar_version": calendar.calendar_version,
            "calendar_type": calendar.calendar_type,
            "kind": calendar.kind,
            "name": calendar.name,
            "base_calendar_id": calendar.base_calendar_id,
            "base_calendar_version": calendar.base_calendar_version,
            "record_revision": calendar.record_revision,
            # Only a stored definition can be consumed by the evaluator; a bare
            # master is visible but explicitly not schedulable.
            "schedulable": schedulable,
        }

    def _definition_dto(self, calendar: CalendarMaster, snapshot: dict[str, object] | None) -> dict[str, Any]:
        return {
            "contract_version": P6_CALENDAR_DEFINITION_VERSION,
            "calendar": self._calendar_dto(calendar, schedulable=snapshot is not None),
            "definition": snapshot,
            "schedulable": snapshot is not None,
        }

    def _authorize(self, scope: BackendScope, auth_context: AuthorizationContext, permission: Permission) -> None:
        scope.validate()
        auth_context.validate()
        if scope.tenant_id != auth_context.tenant_id or scope.project_id != auth_context.project_id:
            raise AuthorizationError("CROSS_SCOPE_ACCESS")
        self.authorization_policy.require(auth_context, permission)


def _exception_dto(exception: CalendarException) -> dict[str, Any]:
    """Stored exception payload plus its record revision for guarded edits."""
    payload = exception.canonical_snapshot()
    payload["record_revision"] = exception.record_revision
    return payload


def _definition_from_payload(
    kind: str, payload: Mapping[str, object], *, default_system: str = "gregorian"
) -> Any:
    """Build the canonical calendar model from an HTTP definition payload.

    The payload is the same canonical snapshot the read endpoint returns:
    ``system``, ``working_weekdays`` (0=Monday … 6=Sunday), ``holidays`` as
    canonical ISO Gregorian dates and, for ``working-time`` calendars,
    ``daily_intervals``. Unknown fields are rejected instead of ignored so a
    typo cannot silently produce a calendar the user did not ask for. Holidays
    stay canonical Gregorian dates; ``system`` only changes how typed calendar
    dates are interpreted elsewhere, exactly like the stored exception layer.
    """
    if not isinstance(payload, Mapping):
        raise P6CalendarAPIError("INVALID_CALENDAR_DEFINITION")
    unknown = sorted(set(payload) - _DEFINITION_FIELDS)
    if unknown:
        raise P6CalendarAPIError(f"CALENDAR_DEFINITION_UNSUPPORTED_FIELD:{unknown[0]}")
    if payload.get("kind", kind) != kind:
        raise P6CalendarAPIError("CALENDAR_DEFINITION_KIND_MISMATCH")
    system = str(payload.get("system") or default_system)
    if system not in _CALENDAR_SYSTEMS:
        raise P6CalendarAPIError("INVALID_CALENDAR_SYSTEM")
    weekdays = payload.get("working_weekdays")
    if not isinstance(weekdays, (list, tuple)) or not weekdays:
        raise P6CalendarAPIError("CALENDAR_DEFINITION_WORKING_WEEK_REQUIRED")
    if any(isinstance(value, bool) or not isinstance(value, int) for value in weekdays):
        raise P6CalendarAPIError("CALENDAR_DEFINITION_WEEKDAY_INVALID")
    holidays = payload.get("holidays", [])
    if not isinstance(holidays, (list, tuple)):
        raise P6CalendarAPIError("CALENDAR_DEFINITION_HOLIDAY_INVALID")

    defaults = WorkingCalendar().canonical_snapshot()["time_period_factors"]
    raw_factors = payload.get("time_period_factors") or defaults
    if not isinstance(raw_factors, Mapping):
        raise P6CalendarAPIError("CALENDAR_DEFINITION_PERIOD_FACTORS_INVALID")
    try:
        factors = {
            name: str(raw_factors[name])
            for name in ("hours_per_day", "hours_per_week", "hours_per_month", "hours_per_year")
        }
    except KeyError as exc:
        raise P6CalendarAPIError("CALENDAR_DEFINITION_PERIOD_FACTORS_INVALID") from exc

    snapshot: dict[str, object] = {
        "kind": kind,
        "system": system,
        "working_weekdays": sorted({int(value) for value in weekdays}),
        "holidays": [str(value) for value in holidays],
        "time_period_factors": factors,
    }
    if kind == "working-time":
        intervals = payload.get("daily_intervals")
        if intervals is None:
            if not set(snapshot["working_weekdays"]) <= {0, 1, 2, 3, 4}:
                # The model's implicit 08:00–17:00 week has no intervals for
                # weekend weekdays, so those days could never produce working
                # time. Ask for explicit intervals instead of inventing them.
                raise P6CalendarAPIError("CALENDAR_DEFINITION_INTERVALS_REQUIRED")
        else:
            if not isinstance(intervals, Mapping):
                raise P6CalendarAPIError("CALENDAR_DEFINITION_INTERVALS_INVALID")
            normalized: dict[str, list[list[str]]] = {}
            for weekday, pairs in intervals.items():
                if not isinstance(pairs, (list, tuple)):
                    raise P6CalendarAPIError("CALENDAR_DEFINITION_INTERVALS_INVALID")
                normalized[str(weekday)] = [
                    [str(pair[0]), str(pair[1])]
                    for pair in pairs
                    if isinstance(pair, (list, tuple)) and len(pair) == 2
                ]
                if len(normalized[str(weekday)]) != len(pairs):
                    raise P6CalendarAPIError("CALENDAR_DEFINITION_INTERVALS_INVALID")
            snapshot["daily_intervals"] = normalized
        try:
            return WorkingTimeCalendar.from_canonical_snapshot(snapshot)
        except (TypeError, ValueError, KeyError) as exc:
            raise P6CalendarAPIError("CALENDAR_DEFINITION_INVALID") from exc
    try:
        return WorkingCalendar.from_canonical_snapshot(snapshot)
    except (TypeError, ValueError, KeyError) as exc:
        raise P6CalendarAPIError("CALENDAR_DEFINITION_INVALID") from exc


def _definition_from_snapshot(snapshot: dict[str, object], kind: str) -> Any:
    if kind == "working-time":
        from .scheduling.time_calendar import WorkingTimeCalendar
        return WorkingTimeCalendar.from_canonical_snapshot(snapshot)
    from .scheduling.calendar import WorkingCalendar
    return WorkingCalendar.from_canonical_snapshot(snapshot)


__all__ = ["P6_CALENDAR_API_VERSION", "P6_CALENDAR_DEFINITION_VERSION", "P6_CALENDAR_TYPES", "P6CalendarAPI", "P6CalendarAPIError", "P6CalendarCreateRequest", "CalendarWorkHourRule"]
