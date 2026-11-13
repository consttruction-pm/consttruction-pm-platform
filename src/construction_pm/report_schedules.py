"""Durable, project-scoped report schedules.

There is deliberately no timer or background thread in this module: a trusted
deployment trigger calls :meth:`ReportScheduleRunner.run_due` (for example from
an existing cron/worker tick). The durable contract is the schedule table plus
the claim/lease/complete cycle, so two worker processes cannot execute the same
occurrence and a crashed worker's lease can be reclaimed.

Execution materializes a normal immutable ``ReportRun`` through the report
application service and computes the export checksum for the configured format.
Transport (email/S3/webhook) is not implemented and remains an external
credential gate; the checksum and run identity are recorded for it.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, replace
from datetime import datetime, time, timedelta, timezone
from typing import Protocol
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .api_errors import APIError, authorization_error, conflict_error, validation_error
from .application.authorization import (
    AuthorizationContext,
    AuthorizationPolicy,
    Permission,
)
from .report_export import REPORT_EXPORT_FORMATS, REPORT_EXPORT_LOCALES, build_report_export
from .report_parameters import (
    ReportParameterError,
    resolve_parameters,
)
from .report_persistence import (
    ReportPersistenceError,
    ReportStore,
    ReportAuditEvent,
)
from .observability import OperationalMetrics
from .production_readiness import StructuredEventLogger

SCHEDULE_CADENCES = ("daily", "weekly", "monthly")
SCHEDULE_STATUSES = ("succeeded", "failed")


class ReportScheduleError(ValueError):
    pass


class ReportScheduleAuthorizationError(ValueError):
    pass


class ReportScheduleRevisionConflict(ReportScheduleError):
    pass


@dataclass(frozen=True)
class ReportSchedule:
    tenant_id: str
    project_id: str
    report_id: str
    schedule_id: str
    cadence: str
    run_time: str
    timezone: str
    project_revision: int = 0
    export_format: str = "csv"
    locale: str = "en"
    weekday: int | None = None
    day_of_month: int | None = None
    parameters: tuple[tuple[str, str], ...] = ()
    enabled: bool = True
    revision: int = 1
    next_run_at: datetime | None = None
    last_run_at: datetime | None = None
    last_status: str | None = None
    last_error: str | None = None
    attempts: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def validate(self) -> None:
        for value, code in (
            (self.tenant_id, "INVALID_REPORT_SCHEDULE_TENANT"),
            (self.project_id, "INVALID_REPORT_SCHEDULE_PROJECT"),
            (self.report_id, "INVALID_REPORT_SCHEDULE_REPORT"),
            (self.schedule_id, "INVALID_REPORT_SCHEDULE_ID"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ReportScheduleError(code)
        if self.cadence not in SCHEDULE_CADENCES:
            raise ReportScheduleError("INVALID_REPORT_SCHEDULE_CADENCE")
        _parse_run_time(self.run_time)
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError, TypeError) as exc:
            raise ReportScheduleError("INVALID_REPORT_SCHEDULE_TIMEZONE") from exc
        if self.cadence == "weekly":
            if (
                isinstance(self.weekday, bool)
                or not isinstance(self.weekday, int)
                or not 0 <= self.weekday <= 6
            ):
                raise ReportScheduleError("INVALID_REPORT_SCHEDULE_WEEKDAY")
        elif self.weekday is not None:
            raise ReportScheduleError("INVALID_REPORT_SCHEDULE_WEEKDAY")
        if self.cadence == "monthly":
            if (
                isinstance(self.day_of_month, bool)
                or not isinstance(self.day_of_month, int)
                or not 1 <= self.day_of_month <= 28
            ):
                raise ReportScheduleError("INVALID_REPORT_SCHEDULE_DAY")
        elif self.day_of_month is not None:
            raise ReportScheduleError("INVALID_REPORT_SCHEDULE_DAY")
        if self.export_format not in REPORT_EXPORT_FORMATS:
            raise ReportScheduleError("INVALID_REPORT_SCHEDULE_FORMAT")
        if self.locale not in REPORT_EXPORT_LOCALES:
            raise ReportScheduleError("INVALID_REPORT_SCHEDULE_LOCALE")
        if (
            isinstance(self.project_revision, bool)
            or not isinstance(self.project_revision, int)
            or self.project_revision < 0
        ):
            raise ReportScheduleError("INVALID_REPORT_SCHEDULE_PROJECT_REVISION")
        if not isinstance(self.enabled, bool):
            raise ReportScheduleError("INVALID_REPORT_SCHEDULE_ENABLED")
        if (
            isinstance(self.revision, bool)
            or not isinstance(self.revision, int)
            or self.revision < 1
        ):
            raise ReportScheduleError("INVALID_REPORT_SCHEDULE_REVISION")
        if (
            isinstance(self.attempts, bool)
            or not isinstance(self.attempts, int)
            or self.attempts < 0
        ):
            raise ReportScheduleError("INVALID_REPORT_SCHEDULE_ATTEMPTS")
        keys: list[str] = []
        if not isinstance(self.parameters, tuple):
            raise ReportScheduleError("INVALID_REPORT_SCHEDULE_PARAMETERS")
        for key, value in self.parameters:
            if not isinstance(key, str) or not key or not isinstance(value, str):
                raise ReportScheduleError("INVALID_REPORT_SCHEDULE_PARAMETERS")
            keys.append(key)
        if len(keys) != len(set(keys)):
            raise ReportScheduleError("INVALID_REPORT_SCHEDULE_PARAMETERS")
        if self.enabled and self.next_run_at is None:
            raise ReportScheduleError("INVALID_REPORT_SCHEDULE_NEXT_RUN")
        if self.next_run_at is not None and self.next_run_at.tzinfo is None:
            raise ReportScheduleError("INVALID_REPORT_SCHEDULE_NEXT_RUN")
        if self.last_run_at is not None and self.last_run_at.tzinfo is None:
            raise ReportScheduleError("INVALID_REPORT_SCHEDULE_LAST_RUN")
        if self.last_status is not None and self.last_status not in SCHEDULE_STATUSES:
            raise ReportScheduleError("INVALID_REPORT_SCHEDULE_STATUS")

    def as_dict(self) -> dict[str, object]:
        return {
            "schedule_id": self.schedule_id,
            "report_id": self.report_id,
            "cadence": self.cadence,
            "run_time": self.run_time,
            "weekday": self.weekday,
            "day_of_month": self.day_of_month,
            "timezone": self.timezone,
            "project_revision": self.project_revision,
            "export_format": self.export_format,
            "locale": self.locale,
            "parameters": dict(self.parameters),
            "enabled": self.enabled,
            "revision": self.revision,
            "next_run_at": _iso(self.next_run_at),
            "last_run_at": _iso(self.last_run_at),
            "last_status": self.last_status,
            "last_error": self.last_error,
            "attempts": self.attempts,
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
        }


@dataclass(frozen=True)
class ScheduleClaim:
    schedule: ReportSchedule
    scheduled_for: datetime
    claim_token: str
    claimed_until: datetime


@dataclass(frozen=True)
class ScheduleOutcome:
    schedule_id: str
    scheduled_for: datetime
    state: str
    run_id: str | None = None
    content_sha256: str | None = None
    error: str | None = None


def _iso(value: datetime | None) -> str | None:
    return None if value is None else value.astimezone(timezone.utc).isoformat()


def _parse_run_time(value: str) -> time:
    if not isinstance(value, str) or len(value) != 5 or value[2] != ":":
        raise ReportScheduleError("INVALID_REPORT_SCHEDULE_RUN_TIME")
    hours_text, minutes_text = value.split(":")
    if not (hours_text.isdigit() and minutes_text.isdigit()):
        raise ReportScheduleError("INVALID_REPORT_SCHEDULE_RUN_TIME")
    hours, minutes = int(hours_text), int(minutes_text)
    if hours > 23 or minutes > 59:
        raise ReportScheduleError("INVALID_REPORT_SCHEDULE_RUN_TIME")
    return time(hours, minutes)


def compute_next_run(
    *,
    cadence: str,
    run_time: str,
    timezone_name: str,
    weekday: int | None = None,
    day_of_month: int | None = None,
    after: datetime,
) -> datetime:
    """Return the first occurrence strictly after ``after`` in UTC.

    Local wall-clock time is converted through the zone database. A time that
    falls in a DST gap maps forward with the zone's post-gap offset; a repeated
    time uses ``fold=0``. Both choices are deterministic.
    """
    if after.tzinfo is None:
        raise ReportScheduleError("INVALID_REPORT_SCHEDULE_AFTER")
    if cadence not in SCHEDULE_CADENCES:
        raise ReportScheduleError("INVALID_REPORT_SCHEDULE_CADENCE")
    try:
        zone = ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError, TypeError) as exc:
        raise ReportScheduleError("INVALID_REPORT_SCHEDULE_TIMEZONE") from exc
    local_after = after.astimezone(zone)
    scheduled_time = _parse_run_time(run_time)
    if cadence == "daily":
        candidate = datetime.combine(
            local_after.date(), scheduled_time, tzinfo=zone
        )
        if candidate <= local_after:
            candidate += timedelta(days=1)
    elif cadence == "weekly":
        if (
            isinstance(weekday, bool)
            or not isinstance(weekday, int)
            or not 0 <= weekday <= 6
        ):
            raise ReportScheduleError("INVALID_REPORT_SCHEDULE_WEEKDAY")
        start = local_after.date()
        offset = (weekday - start.weekday()) % 7
        candidate = datetime.combine(
            start + timedelta(days=offset), scheduled_time, tzinfo=zone
        )
        if candidate <= local_after:
            candidate += timedelta(days=7)
    elif cadence == "monthly":
        if (
            isinstance(day_of_month, bool)
            or not isinstance(day_of_month, int)
            or not 1 <= day_of_month <= 28
        ):
            raise ReportScheduleError("INVALID_REPORT_SCHEDULE_DAY")
        year, month = local_after.year, local_after.month
        candidate = datetime(
            year, month, day_of_month, scheduled_time.hour, scheduled_time.minute,
            tzinfo=zone,
        )
        if candidate <= local_after:
            if month == 12:
                year, month = year + 1, 1
            else:
                month += 1
            candidate = datetime(
                year, month, day_of_month, scheduled_time.hour,
                scheduled_time.minute, tzinfo=zone,
            )
    else:
        raise ReportScheduleError("INVALID_REPORT_SCHEDULE_CADENCE")
    return candidate.astimezone(timezone.utc)


class ReportScheduleStore(Protocol):
    def get(
        self, tenant_id: str, project_id: str, report_id: str, schedule_id: str
    ) -> ReportSchedule: ...
    def list(
        self, tenant_id: str, project_id: str, report_id: str
    ) -> tuple[ReportSchedule, ...]: ...
    def create(
        self, schedule: ReportSchedule, *, actor_id: str, occurred_at: datetime
    ) -> ReportSchedule: ...
    def update(
        self,
        schedule: ReportSchedule,
        *,
        expected_revision: int,
        actor_id: str,
        occurred_at: datetime,
    ) -> ReportSchedule: ...
    def delete(
        self,
        *,
        tenant_id: str,
        project_id: str,
        report_id: str,
        schedule_id: str,
        expected_revision: int,
        actor_id: str,
        occurred_at: datetime,
    ) -> None: ...
    def claim_due(
        self,
        *,
        now: datetime,
        worker_id: str,
        lease_seconds: int,
        limit: int,
    ) -> tuple[ScheduleClaim, ...]: ...
    def complete(
        self,
        claim: ScheduleClaim,
        *,
        run_id: str,
        content_sha256: str,
        completed_at: datetime,
        next_run_at: datetime | None,
    ) -> ReportSchedule: ...
    def fail(
        self,
        claim: ScheduleClaim,
        *,
        error: str,
        failed_at: datetime,
        next_run_at: datetime | None,
    ) -> ReportSchedule: ...
    def history(
        self, tenant_id: str, project_id: str, report_id: str, schedule_id: str
    ) -> tuple[ReportAuditEvent, ...]: ...


class SQLiteReportScheduleStore:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS project_report_schedule (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                report_id TEXT NOT NULL,
                schedule_id TEXT NOT NULL,
                cadence TEXT NOT NULL,
                run_time TEXT NOT NULL,
                weekday INTEGER,
                day_of_month INTEGER,
                timezone TEXT NOT NULL,
                project_revision INTEGER NOT NULL DEFAULT 0,
                export_format TEXT NOT NULL,
                locale TEXT NOT NULL,
                parameters_json TEXT NOT NULL,
                enabled INTEGER NOT NULL,
                revision INTEGER NOT NULL,
                next_run_at TEXT,
                last_run_at TEXT,
                last_status TEXT,
                last_error TEXT,
                attempts INTEGER NOT NULL DEFAULT 0,
                claim_token TEXT,
                claimed_until TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, schedule_id)
            )"""
        )
        self.connection.execute(
            """CREATE INDEX IF NOT EXISTS project_report_schedule_due
               ON project_report_schedule (enabled, next_run_at)"""
        )
        _ensure_column(
            self.connection,
            "project_revision",
            "INTEGER NOT NULL DEFAULT 0",
        )
        self.connection.commit()

    def get(self, tenant_id, project_id, report_id, schedule_id) -> ReportSchedule:
        row = self.connection.execute(
            """SELECT tenant_id, project_id, report_id, schedule_id, cadence,
                      run_time, weekday, day_of_month, timezone, project_revision,
                      export_format, locale, parameters_json, enabled, revision,
                      next_run_at, last_run_at, last_status, last_error, attempts,
                      created_at, updated_at
               FROM project_report_schedule
               WHERE tenant_id = ? AND project_id = ? AND report_id = ?
                 AND schedule_id = ?""",
            (tenant_id, project_id, report_id, schedule_id),
        ).fetchone()
        if row is None:
            raise KeyError("REPORT_SCHEDULE_NOT_FOUND")
        return _schedule_from_row(row)

    def list(self, tenant_id, project_id, report_id) -> tuple[ReportSchedule, ...]:
        rows = self.connection.execute(
            """SELECT tenant_id, project_id, report_id, schedule_id, cadence,
                      run_time, weekday, day_of_month, timezone, project_revision,
                      export_format, locale, parameters_json, enabled, revision,
                      next_run_at, last_run_at, last_status, last_error, attempts,
                      created_at, updated_at
               FROM project_report_schedule
               WHERE tenant_id = ? AND project_id = ? AND report_id = ?
               ORDER BY schedule_id""",
            (tenant_id, project_id, report_id),
        ).fetchall()
        return tuple(_schedule_from_row(row) for row in rows)

    def create(self, schedule, *, actor_id, occurred_at) -> ReportSchedule:
        schedule.validate()
        _validate_actor(actor_id)
        if schedule.enabled and schedule.next_run_at is None:
            raise ReportScheduleError("INVALID_REPORT_SCHEDULE_NEXT_RUN")
        existing = self.connection.execute(
            """SELECT 1 FROM project_report_schedule
               WHERE tenant_id = ? AND project_id = ? AND schedule_id = ?""",
            (schedule.tenant_id, schedule.project_id, schedule.schedule_id),
        ).fetchone()
        if existing is not None:
            raise ReportScheduleError("REPORT_SCHEDULE_ALREADY_EXISTS")
        now = occurred_at.astimezone(timezone.utc).isoformat()
        try:
            self.connection.execute(
                """INSERT INTO project_report_schedule
                   (tenant_id, project_id, report_id, schedule_id, cadence, run_time,
                    weekday, day_of_month, timezone, project_revision, export_format,
                    locale, parameters_json, enabled, revision, next_run_at,
                    last_run_at, last_status, last_error, attempts, created_at,
                    updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL,
                           NULL, NULL, 0, ?, ?)""",
                (
                    schedule.tenant_id,
                    schedule.project_id,
                    schedule.report_id,
                    schedule.schedule_id,
                    schedule.cadence,
                    schedule.run_time,
                    schedule.weekday,
                    schedule.day_of_month,
                    schedule.timezone,
                    schedule.project_revision,
                    schedule.export_format,
                    schedule.locale,
                    json.dumps(dict(schedule.parameters), ensure_ascii=False, sort_keys=True),
                    1 if schedule.enabled else 0,
                    1,
                    _iso(schedule.next_run_at),
                    now,
                    now,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise ReportScheduleError("REPORT_SCHEDULE_ALREADY_EXISTS") from exc
        self._audit(schedule, "created", actor_id, occurred_at, "")
        return self.get(
            schedule.tenant_id, schedule.project_id, schedule.report_id,
            schedule.schedule_id,
        )

    def update(self, schedule, *, expected_revision, actor_id, occurred_at) -> ReportSchedule:
        schedule.validate()
        _validate_actor(actor_id)
        current = self.get(
            schedule.tenant_id, schedule.project_id, schedule.report_id,
            schedule.schedule_id,
        )
        if (
            isinstance(expected_revision, bool)
            or not isinstance(expected_revision, int)
            or expected_revision < 1
        ):
            raise ReportScheduleError("INVALID_EXPECTED_REPORT_SCHEDULE_REVISION")
        if current.revision != expected_revision:
            raise ReportScheduleRevisionConflict("REPORT_SCHEDULE_REVISION_CONFLICT")
        new_revision = current.revision + 1
        now = occurred_at.astimezone(timezone.utc).isoformat()
        self.connection.execute(
            """UPDATE project_report_schedule
               SET cadence = ?, run_time = ?, weekday = ?, day_of_month = ?,
                   timezone = ?, project_revision = ?, export_format = ?,
                   locale = ?, parameters_json = ?, enabled = ?, revision = ?,
                   next_run_at = ?, updated_at = ?
               WHERE tenant_id = ? AND project_id = ? AND schedule_id = ?""",
            (
                schedule.cadence,
                schedule.run_time,
                schedule.weekday,
                schedule.day_of_month,
                schedule.timezone,
                schedule.project_revision,
                schedule.export_format,
                schedule.locale,
                json.dumps(dict(schedule.parameters), ensure_ascii=False, sort_keys=True),
                1 if schedule.enabled else 0,
                new_revision,
                _iso(schedule.next_run_at),
                now,
                schedule.tenant_id,
                schedule.project_id,
                schedule.schedule_id,
            ),
        )
        self._audit(schedule, "updated", actor_id, occurred_at, "")
        return self.get(
            schedule.tenant_id, schedule.project_id, schedule.report_id,
            schedule.schedule_id,
        )

    def delete(self, *, tenant_id, project_id, report_id, schedule_id, expected_revision, actor_id, occurred_at) -> None:
        _validate_actor(actor_id)
        current = self.get(tenant_id, project_id, report_id, schedule_id)
        if (
            isinstance(expected_revision, bool)
            or not isinstance(expected_revision, int)
            or expected_revision < 1
        ):
            raise ReportScheduleError("INVALID_EXPECTED_REPORT_SCHEDULE_REVISION")
        if current.revision != expected_revision:
            raise ReportScheduleRevisionConflict("REPORT_SCHEDULE_REVISION_CONFLICT")
        self.connection.execute(
            """DELETE FROM project_report_schedule
               WHERE tenant_id = ? AND project_id = ? AND schedule_id = ?""",
            (tenant_id, project_id, schedule_id),
        )
        self._audit(
            current,
            "deleted",
            actor_id,
            occurred_at,
            "",
        )

    def claim_due(self, *, now, worker_id, lease_seconds, limit) -> tuple[ScheduleClaim, ...]:
        if now.tzinfo is None:
            raise ReportScheduleError("INVALID_REPORT_SCHEDULE_NOW")
        if not isinstance(worker_id, str) or not worker_id.strip():
            raise ReportScheduleError("INVALID_REPORT_SCHEDULE_WORKER")
        if lease_seconds <= 0 or limit <= 0:
            raise ReportScheduleError("INVALID_REPORT_SCHEDULE_CLAIM")
        now_text = now.astimezone(timezone.utc).isoformat()
        claimed_until = now + timedelta(seconds=lease_seconds)
        rows = self.connection.execute(
            """SELECT tenant_id, project_id, report_id, schedule_id, cadence,
                      run_time, weekday, day_of_month, timezone, project_revision,
                      export_format, locale, parameters_json, enabled, revision,
                      next_run_at, last_run_at, last_status, last_error, attempts,
                      created_at, updated_at
               FROM project_report_schedule
               WHERE enabled = 1 AND next_run_at IS NOT NULL AND next_run_at <= ?
                 AND (claim_token IS NULL OR claimed_until IS NULL OR claimed_until <= ?)
               ORDER BY next_run_at, schedule_id
               LIMIT ?""",
            (now_text, now_text, limit),
        ).fetchall()
        claims: list[ScheduleClaim] = []
        for row in rows:
            schedule = _schedule_from_row(row)
            token = uuid.uuid4().hex
            cursor = self.connection.execute(
                """UPDATE project_report_schedule
                   SET claim_token = ?, claimed_until = ?
                   WHERE tenant_id = ? AND project_id = ? AND schedule_id = ?
                     AND (claim_token IS NULL OR claimed_until IS NULL
                          OR claimed_until <= ?)""",
                (
                    token,
                    claimed_until.astimezone(timezone.utc).isoformat(),
                    schedule.tenant_id,
                    schedule.project_id,
                    schedule.schedule_id,
                    now_text,
                ),
            )
            if cursor.rowcount != 1:
                continue
            claims.append(
                ScheduleClaim(
                    schedule=schedule,
                    scheduled_for=schedule.next_run_at,
                    claim_token=token,
                    claimed_until=claimed_until,
                )
            )
        return tuple(claims)

    def complete(self, claim, *, run_id, content_sha256, completed_at, next_run_at) -> ReportSchedule:
        schedule = self.get(
            claim.schedule.tenant_id, claim.schedule.project_id,
            claim.schedule.report_id, claim.schedule.schedule_id,
        )
        self._assert_claim(schedule, claim)
        now = completed_at.astimezone(timezone.utc).isoformat()
        cursor = self.connection.execute(
            """UPDATE project_report_schedule
               SET last_run_at = ?, last_status = 'succeeded', last_error = NULL,
                   attempts = 0, next_run_at = ?, claim_token = NULL,
                   claimed_until = NULL, updated_at = ?
               WHERE tenant_id = ? AND project_id = ? AND schedule_id = ?
                 AND claim_token = ?""",
            (
                now,
                _iso(next_run_at),
                now,
                schedule.tenant_id,
                schedule.project_id,
                schedule.schedule_id,
                claim.claim_token,
            ),
        )
        if cursor.rowcount != 1:
            raise ReportScheduleError("REPORT_SCHEDULE_CLAIM_LOST")
        return self.get(
            schedule.tenant_id, schedule.project_id, schedule.report_id,
            schedule.schedule_id,
        )

    def fail(self, claim, *, error, failed_at, next_run_at) -> ReportSchedule:
        schedule = self.get(
            claim.schedule.tenant_id, claim.schedule.project_id,
            claim.schedule.report_id, claim.schedule.schedule_id,
        )
        self._assert_claim(schedule, claim)
        now = failed_at.astimezone(timezone.utc).isoformat()
        cursor = self.connection.execute(
            """UPDATE project_report_schedule
               SET last_run_at = ?, last_status = 'failed', last_error = ?,
                   attempts = attempts + 1, next_run_at = ?, claim_token = NULL,
                   claimed_until = NULL, updated_at = ?
               WHERE tenant_id = ? AND project_id = ? AND schedule_id = ?
                 AND claim_token = ?""",
            (
                now,
                str(error)[:500],
                _iso(next_run_at),
                now,
                schedule.tenant_id,
                schedule.project_id,
                schedule.schedule_id,
                claim.claim_token,
            ),
        )
        if cursor.rowcount != 1:
            raise ReportScheduleError("REPORT_SCHEDULE_CLAIM_LOST")
        return self.get(
            schedule.tenant_id, schedule.project_id, schedule.report_id,
            schedule.schedule_id,
        )

    def history(self, tenant_id, project_id, report_id, schedule_id):
        rows = self.connection.execute(
            """SELECT entity_type, entity_id, revision, event_type, actor_id,
                      occurred_at, reason
               FROM project_report_audit
               WHERE tenant_id = ? AND project_id = ?
                 AND entity_type = 'report_schedule' AND entity_id = ?
               ORDER BY revision""",
            (tenant_id, project_id, schedule_id),
        ).fetchall()
        return tuple(
            ReportAuditEvent(
                entity_type=str(row[0]),
                entity_id=str(row[1]),
                revision=int(row[2]),
                event_type=str(row[3]),
                actor_id=str(row[4]),
                occurred_at=datetime.fromisoformat(str(row[5])),
                reason=str(row[6]),
            )
            for row in rows
        )

    def _assert_claim(self, schedule: ReportSchedule, claim: ScheduleClaim) -> None:
        token = self.connection.execute(
            """SELECT claim_token, claimed_until FROM project_report_schedule
               WHERE tenant_id = ? AND project_id = ? AND schedule_id = ?""",
            (schedule.tenant_id, schedule.project_id, schedule.schedule_id),
        ).fetchone()
        if token is None or str(token[0] or "") != claim.claim_token:
            raise ReportScheduleError("REPORT_SCHEDULE_CLAIM_LOST")

    def _audit(self, schedule, event_type, actor_id, occurred_at, reason):
        # The audit table is append-only and keyed by revision. A schedule that
        # is deleted and re-created with the same id starts its own revision
        # counter at 1 again, so the audit revision is the next free one for
        # this entity rather than the schedule row's revision.
        row = self.connection.execute(
            """SELECT COALESCE(MAX(revision), 0) + 1
               FROM project_report_audit
               WHERE tenant_id = ? AND project_id = ?
                 AND entity_type = 'report_schedule' AND entity_id = ?""",
            (schedule.tenant_id, schedule.project_id, schedule.schedule_id),
        ).fetchone()
        revision = int(row[0]) if row is not None else 1
        self.connection.execute(
            """INSERT INTO project_report_audit
               (tenant_id, project_id, entity_type, entity_id, revision,
                event_type, actor_id, occurred_at, reason)
               VALUES (?, ?, 'report_schedule', ?, ?, ?, ?, ?, ?)""",
            (
                schedule.tenant_id,
                schedule.project_id,
                schedule.schedule_id,
                revision,
                event_type,
                actor_id,
                occurred_at.isoformat(),
                reason,
            ),
        )


def _schedule_from_row(row) -> ReportSchedule:
    schedule = ReportSchedule(
        tenant_id=str(row[0]),
        project_id=str(row[1]),
        report_id=str(row[2]),
        schedule_id=str(row[3]),
        cadence=str(row[4]),
        run_time=str(row[5]),
        weekday=None if row[6] is None else int(row[6]),
        day_of_month=None if row[7] is None else int(row[7]),
        timezone=str(row[8]),
        project_revision=int(row[9]),
        export_format=str(row[10]),
        locale=str(row[11]),
        parameters=tuple(
            (str(key), str(value))
            for key, value in json.loads(str(row[12])).items()
        ),
        enabled=bool(row[13]),
        revision=int(row[14]),
        next_run_at=(
            None if row[15] is None else datetime.fromisoformat(str(row[15]))
        ),
        last_run_at=(
            None if row[16] is None else datetime.fromisoformat(str(row[16]))
        ),
        last_status=None if row[17] is None else str(row[17]),
        last_error=None if row[18] is None else str(row[18]),
        attempts=int(row[19]),
        created_at=datetime.fromisoformat(str(row[20])),
        updated_at=datetime.fromisoformat(str(row[21])),
    )
    return schedule


def _ensure_column(
    connection: sqlite3.Connection, name: str, definition: str
) -> None:
    columns = {
        str(row[1])
        for row in connection.execute(
            "PRAGMA table_info(project_report_schedule)"
        ).fetchall()
    }
    if name not in columns:
        connection.execute(
            f"ALTER TABLE project_report_schedule ADD COLUMN {name} {definition}"
        )


def _validate_actor(actor_id: str) -> None:
    if not isinstance(actor_id, str) or not actor_id.strip():
        raise ReportScheduleError("INVALID_REPORT_SCHEDULE_ACTOR")


class ReportScheduleService:
    """Authorization and validation boundary for schedule definitions."""

    def __init__(
        self,
        store: ReportScheduleStore,
        reports: ReportStore,
        policy: AuthorizationPolicy,
        transaction_manager,
    ) -> None:
        self.store = store
        self.reports = reports
        self.policy = policy
        self.transaction_manager = transaction_manager

    def list(self, *, tenant_id, project_id, report_id, context) -> tuple[ReportSchedule, ...]:
        self._check(context, tenant_id, project_id, Permission.PROJECT_READ)
        self.reports.get_definition(tenant_id, project_id, report_id)
        return self.store.list(tenant_id, project_id, report_id)

    def get(self, *, tenant_id, project_id, report_id, schedule_id, context) -> ReportSchedule:
        self._check(context, tenant_id, project_id, Permission.PROJECT_READ)
        self.reports.get_definition(tenant_id, project_id, report_id)
        return self.store.get(tenant_id, project_id, report_id, schedule_id)

    def history(self, *, tenant_id, project_id, report_id, schedule_id, context):
        self.get(
            tenant_id=tenant_id,
            project_id=project_id,
            report_id=report_id,
            schedule_id=schedule_id,
            context=context,
        )
        return self.store.history(tenant_id, project_id, report_id, schedule_id)

    def create(
        self,
        schedule: ReportSchedule,
        *,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> ReportSchedule:
        self._authorize_write(schedule, context, actor_id)
        definition = self.reports.get_definition(
            schedule.tenant_id, schedule.project_id, schedule.report_id
        )
        parameters = self._resolve_parameters(definition.definition, schedule)
        prepared = replace(
            schedule,
            parameters=parameters,
            revision=1,
            next_run_at=(
                compute_next_run(
                    cadence=schedule.cadence,
                    run_time=schedule.run_time,
                    timezone_name=schedule.timezone,
                    weekday=schedule.weekday,
                    day_of_month=schedule.day_of_month,
                    after=occurred_at,
                )
                if schedule.enabled
                else None
            ),
            created_at=occurred_at,
            updated_at=occurred_at,
        )
        with self.transaction_manager.transaction():
            return self.store.create(
                prepared, actor_id=actor_id, occurred_at=occurred_at
            )

    def update(
        self,
        schedule: ReportSchedule,
        *,
        expected_revision: int,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> ReportSchedule:
        self._authorize_write(schedule, context, actor_id)
        definition = self.reports.get_definition(
            schedule.tenant_id, schedule.project_id, schedule.report_id
        )
        parameters = self._resolve_parameters(definition.definition, schedule)
        next_run_at = (
            compute_next_run(
                cadence=schedule.cadence,
                run_time=schedule.run_time,
                timezone_name=schedule.timezone,
                weekday=schedule.weekday,
                day_of_month=schedule.day_of_month,
                after=occurred_at,
            )
            if schedule.enabled
            else None
        )
        prepared = replace(
            schedule,
            parameters=parameters,
            next_run_at=next_run_at,
            updated_at=occurred_at,
        )
        with self.transaction_manager.transaction():
            return self.store.update(
                prepared,
                expected_revision=expected_revision,
                actor_id=actor_id,
                occurred_at=occurred_at,
            )

    def delete(
        self,
        *,
        tenant_id,
        project_id,
        report_id,
        schedule_id,
        expected_revision,
        context,
        actor_id,
        occurred_at,
    ) -> None:
        self._check(context, tenant_id, project_id, Permission.PROJECT_WRITE)
        if actor_id != context.user_id:
            raise ReportScheduleAuthorizationError("REPORT_SCHEDULE_ACTOR_MISMATCH")
        with self.transaction_manager.transaction():
            self.store.delete(
                tenant_id=tenant_id,
                project_id=project_id,
                report_id=report_id,
                schedule_id=schedule_id,
                expected_revision=expected_revision,
                actor_id=actor_id,
                occurred_at=occurred_at,
            )

    def _resolve_parameters(self, definition, schedule: ReportSchedule):
        """Validate supplied values and keep only explicit ones.

        Defaults are deliberately not frozen into the schedule: the runner
        re-resolves against the definition that is current at execution time,
        and the resulting run records the real ``explicit``/``default``
        provenance.
        """
        try:
            resolved = resolve_parameters(
                definition.subject,
                definition.parameters,
                dict(schedule.parameters),
            )
        except ReportParameterError:
            raise
        return tuple(
            (key, value)
            for (key, value), (_, source) in zip(resolved.values, resolved.sources)
            if source == "explicit"
        )

    def _check(self, context, tenant_id, project_id, permission) -> None:
        if tenant_id != context.tenant_id or project_id != context.project_id:
            raise ReportScheduleAuthorizationError("REPORT_SCHEDULE_CROSS_SCOPE_ACCESS")
        if not self.policy.is_allowed(context, permission):
            raise ReportScheduleAuthorizationError("REPORT_SCHEDULE_PERMISSION_DENIED")

    def _authorize_write(self, schedule, context, actor_id) -> None:
        if actor_id != context.user_id:
            raise ReportScheduleAuthorizationError("REPORT_SCHEDULE_ACTOR_MISMATCH")
        self._check(
            context, schedule.tenant_id, schedule.project_id, Permission.PROJECT_WRITE
        )

    @staticmethod
    def error_dto(exc: Exception) -> APIError:
        if isinstance(exc, KeyError):
            code = str(exc.args[0]) if exc.args else "REPORT_SCHEDULE_NOT_FOUND"
            return validation_error(code, code)
        if isinstance(exc, ReportScheduleRevisionConflict):
            return conflict_error(
                "REPORT_SCHEDULE_REVISION_CONFLICT", str(exc), retryable=True
            )
        if isinstance(exc, ReportScheduleAuthorizationError):
            return authorization_error(str(exc), str(exc))
        if isinstance(exc, ReportScheduleError):
            code = str(exc)
            if code.endswith("_ALREADY_EXISTS"):
                return conflict_error(code, code)
            return validation_error(code, code)
        if isinstance(exc, ReportParameterError):
            return validation_error(str(exc), str(exc))
        if isinstance(exc, ReportPersistenceError):
            return validation_error(str(exc), str(exc))
        if isinstance(exc, ValueError):
            return validation_error(str(exc) or type(exc).__name__, str(exc))
        return validation_error(type(exc).__name__, str(exc))


class ReportScheduleRunner:
    """Trusted execution entry point for one or more due schedules.

    A deployment scheduler (cron/worker tick) calls :meth:`run_due`. This class
    owns no timer and no background thread.
    """

    def __init__(
        self,
        store: ReportScheduleStore,
        reports,
        *,
        lease_seconds: int = 300,
        retry_base_minutes: int = 5,
        retry_max_minutes: int = 60,
        metrics: OperationalMetrics | None = None,
        logger: StructuredEventLogger | None = None,
    ) -> None:
        self.store = store
        self.reports = reports
        self.lease_seconds = lease_seconds
        self.retry_base_minutes = retry_base_minutes
        self.retry_max_minutes = retry_max_minutes
        self.metrics = metrics
        self.logger = logger

    def run_due(
        self, *, now: datetime, worker_id: str, limit: int = 10
    ) -> tuple[ScheduleOutcome, ...]:
        claims = self.store.claim_due(
            now=now,
            worker_id=worker_id,
            lease_seconds=self.lease_seconds,
            limit=limit,
        )
        outcomes = tuple(self._execute(claim, now) for claim in claims)
        self._record(outcomes)
        return outcomes

    def _record(self, outcomes: tuple[ScheduleOutcome, ...]) -> None:
        for outcome in outcomes:
            if self.metrics is not None:
                try:
                    self.metrics.increment(
                        "report_schedule_runs_total", labels={"state": outcome.state}
                    )
                except ValueError:
                    pass
            if self.logger is not None:
                self.logger.emit(
                    "report.schedule.run",
                    fields={
                        "schedule_id": outcome.schedule_id,
                        "state": outcome.state,
                        "run_id": outcome.run_id or "none",
                        "content_sha256": outcome.content_sha256 or "none",
                    },
                )

    def _execute(self, claim: ScheduleClaim, now: datetime) -> ScheduleOutcome:
        schedule = claim.schedule
        run_id = (
            f"RUN-SCH-{schedule.schedule_id}-"
            f"{claim.scheduled_for.astimezone(timezone.utc):%Y%m%dT%H%M%SZ}"
        )
        try:
            try:
                run = self.reports.run_scheduled(
                    tenant_id=schedule.tenant_id,
                    project_id=schedule.project_id,
                    project_revision=schedule.project_revision,
                    report_id=schedule.report_id,
                    parameters=dict(schedule.parameters),
                    actor_id="scheduler",
                    occurred_at=claim.scheduled_for,
                    run_id=run_id,
                )
            except ReportPersistenceError as exc:
                if str(exc) != "REPORT_RUN_ID_ALREADY_EXISTS":
                    raise
                run = self.reports.store.get_run(
                    schedule.tenant_id,
                    schedule.project_id,
                    schedule.report_id,
                    run_id,
                )
            document = build_report_export(
                run, schedule.export_format, locale=schedule.locale
            )
            next_run_at = (
                compute_next_run(
                    cadence=schedule.cadence,
                    run_time=schedule.run_time,
                    timezone_name=schedule.timezone,
                    weekday=schedule.weekday,
                    day_of_month=schedule.day_of_month,
                    after=now,
                )
                if schedule.enabled
                else None
            )
            self.store.complete(
                claim,
                run_id=run.run_id,
                content_sha256=document.content_sha256,
                completed_at=now,
                next_run_at=next_run_at,
            )
            return ScheduleOutcome(
                schedule_id=schedule.schedule_id,
                scheduled_for=claim.scheduled_for,
                state="succeeded",
                run_id=run.run_id,
                content_sha256=document.content_sha256,
            )
        except Exception as exc:  # noqa: BLE001 - durable failure boundary
            attempts = schedule.attempts + 1
            delay = min(
                self.retry_max_minutes,
                self.retry_base_minutes * (2 ** min(attempts - 1, 4)),
            )
            message = f"{type(exc).__name__}: {exc}"
            try:
                self.store.fail(
                    claim,
                    error=message,
                    failed_at=now,
                    next_run_at=now + timedelta(minutes=delay),
                )
            except Exception as record_exc:  # noqa: BLE001
                # A schedule deleted or re-claimed mid-flight must not abort the
                # whole batch; the outcome still reports the original failure.
                message = f"{message}; failure not recorded: {record_exc}"
            return ScheduleOutcome(
                schedule_id=schedule.schedule_id,
                scheduled_for=claim.scheduled_for,
                state="failed",
                error=message,
            )


__all__ = [
    "SCHEDULE_CADENCES",
    "ReportSchedule",
    "ReportScheduleAuthorizationError",
    "ReportScheduleError",
    "ReportScheduleRevisionConflict",
    "ReportScheduleRunner",
    "ReportScheduleService",
    "ReportScheduleStore",
    "SQLiteReportScheduleStore",
    "ScheduleClaim",
    "ScheduleOutcome",
    "compute_next_run",
]
