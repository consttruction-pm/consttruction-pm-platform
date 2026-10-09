from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass
from typing import Any

from .application.authorization import AuthorizationContext, AuthorizationError, AuthorizationPolicy, Permission
from .backend_p0.models import BackendScope
from .backend_p0.transactions import TransactionManager
from .calendar_exception_repository import CalendarException, CalendarExceptionRepository
from .calendar_master_repository import CalendarMaster, CalendarMasterRepository, CalendarPersistenceError
from .calendar_snapshot_repository import CalendarSnapshotRepository
from .calendar_work_hours_repository import CalendarWorkHourRepository, CalendarWorkHourRule

P6_CALENDAR_API_VERSION = "p6-calendar.v1"
P6_CALENDAR_TYPES = frozenset({"global", "resource", "project"})


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

    def validate(self) -> None:
        if self.contract_version != P6_CALENDAR_API_VERSION:
            raise P6CalendarAPIError("UNSUPPORTED_P6_CALENDAR_API_VERSION")
        if self.calendar_type not in P6_CALENDAR_TYPES:
            raise P6CalendarAPIError("INVALID_CALENDAR_TYPE")
        if self.expected_revision is not None and (
            isinstance(self.expected_revision, bool) or self.expected_revision < 0
        ):
            raise P6CalendarAPIError("INVALID_EXPECTED_REVISION")


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

    def create(self, scope: BackendScope, request: P6CalendarCreateRequest, *, auth_context: AuthorizationContext) -> dict[str, Any]:
        request.validate()
        self._authorize(scope, auth_context, Permission.PROJECT_WRITE)
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
        return self._calendar_dto(self.calendar_repository.save(calendar, request.expected_revision))

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
            snapshot = self.snapshot_repository.get(source)
            if snapshot is not None:
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
        return stored.canonical_snapshot()

    def list_exceptions(self, scope: BackendScope, calendar_id: str, calendar_version: str, *, auth_context: AuthorizationContext) -> tuple[dict[str, Any], ...]:
        self._authorize(scope, auth_context, Permission.PROJECT_READ)
        return tuple(item.canonical_snapshot() for item in self.exception_repository.list(scope, calendar_id, calendar_version))


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
        stored = self._work_hours().save(rule)
        return stored.canonical_snapshot()

    def list_work_hours(self, scope: BackendScope, calendar_id: str, calendar_version: str, kind: str, *, auth_context: AuthorizationContext) -> tuple[dict[str, object], ...]:
        self._authorize(scope, auth_context, Permission.PROJECT_READ)
        return tuple(item.canonical_snapshot() for item in self._work_hours().list(scope, calendar_id, calendar_version, kind))

    def _catalog(self, scope: BackendScope) -> dict[str, Any]:
        return {
            "contract_version": P6_CALENDAR_API_VERSION,
            "kind": "calendar_catalog",
            "scope": {"tenant_id": scope.tenant_id, "project_id": scope.project_id, "project_revision": scope.project_revision},
            "calendars": [self._calendar_dto(item) for item in self.calendar_repository.list(scope)],
        }

    @staticmethod
    def _calendar_dto(calendar: CalendarMaster) -> dict[str, Any]:
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
        }

    def _authorize(self, scope: BackendScope, auth_context: AuthorizationContext, permission: Permission) -> None:
        scope.validate()
        auth_context.validate()
        if scope.tenant_id != auth_context.tenant_id or scope.project_id != auth_context.project_id:
            raise AuthorizationError("CROSS_SCOPE_ACCESS")
        self.authorization_policy.require(auth_context, permission)


def _definition_from_snapshot(snapshot: dict[str, object], kind: str) -> Any:
    if kind == "working-time":
        from .scheduling.time_calendar import WorkingTimeCalendar
        return WorkingTimeCalendar.from_canonical_snapshot(snapshot)
    from .scheduling.calendar import WorkingCalendar
    return WorkingCalendar.from_canonical_snapshot(snapshot)


__all__ = ["P6_CALENDAR_API_VERSION", "P6_CALENDAR_TYPES", "P6CalendarAPI", "P6CalendarAPIError", "P6CalendarCreateRequest", "CalendarWorkHourRule"]
