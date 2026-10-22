from __future__ import annotations

"""Revision-scoped persistence for authoritative project scheduling settings.

The settings record is part of schedule-input provenance. It stores the explicit
project calendar reference/version, project start/finish, scheduling mode,
P6-aligned ScheduleOptions, and project leveling priority. Missing settings are
not synthesized by this repository.
"""

import hashlib
import json
import sqlite3
from dataclasses import dataclass, fields, replace
from datetime import date, datetime
from enum import Enum
from typing import Protocol

from .backend_p0.models import BackendScope, MAX_SAFE_REVISION
from .scheduling.authoritative_schedule import AuthoritativeScheduleMode
from .scheduling.calendar_context import CalendarReference, RelationshipLagCalendar
from .scheduling.calendar_system import CalendarSystem
from .scheduling.schedule_options import (
    CriticalActivityPathType,
    OutOfSequenceScheduleType,
    PriorityListItem,
    PrioritySortOrder,
    ScheduleMode,
    ScheduleOptions,
    StartToStartLagCalculationType,
    TotalFloatCalculationType,
)


SCHEMA_VERSION = 1


class ProjectScheduleSettingsPersistenceError(ValueError):
    """Raised when project schedule settings are invalid, stale, or conflicting."""


@dataclass(frozen=True)
class ProjectScheduleSettings:
    """Authoritative scheduling context for one exact tenant/project revision."""

    scope: BackendScope
    mode: AuthoritativeScheduleMode
    project_calendar: CalendarReference
    project_start: date | datetime
    schedule_options: ScheduleOptions
    project_leveling_priority: int
    project_finish: date | datetime | None = None
    record_revision: int = 0

    def validate(self) -> None:
        self.scope.validate()
        if not isinstance(self.mode, AuthoritativeScheduleMode):
            raise ProjectScheduleSettingsPersistenceError("INVALID_SCHEDULE_MODE")
        if not isinstance(self.project_calendar, CalendarReference):
            raise ProjectScheduleSettingsPersistenceError("INVALID_PROJECT_CALENDAR")
        expected_kind = (
            "working-day"
            if self.mode is AuthoritativeScheduleMode.DATE_BASED
            else "working-time"
        )
        if self.project_calendar.kind != expected_kind:
            raise ProjectScheduleSettingsPersistenceError("PROJECT_CALENDAR_KIND_MODE_MISMATCH")
        if not isinstance(self.schedule_options, ScheduleOptions):
            raise ProjectScheduleSettingsPersistenceError("INVALID_SCHEDULE_OPTIONS")
        if (
            isinstance(self.project_leveling_priority, bool)
            or not isinstance(self.project_leveling_priority, int)
            or not 1 <= self.project_leveling_priority <= 100
        ):
            raise ProjectScheduleSettingsPersistenceError("INVALID_PROJECT_LEVELING_PRIORITY")
        if (
            isinstance(self.record_revision, bool)
            or not isinstance(self.record_revision, int)
            or not 0 <= self.record_revision <= MAX_SAFE_REVISION
        ):
            raise ProjectScheduleSettingsPersistenceError("INVALID_RECORD_REVISION")

        if self.mode is AuthoritativeScheduleMode.DATE_BASED:
            if not isinstance(self.project_start, date) or isinstance(self.project_start, datetime):
                raise ProjectScheduleSettingsPersistenceError("DATE_BASED_PROJECT_START_REQUIRED")
            if self.project_finish is not None and (
                not isinstance(self.project_finish, date) or isinstance(self.project_finish, datetime)
            ):
                raise ProjectScheduleSettingsPersistenceError("INVALID_PROJECT_FINISH")
        else:
            if not isinstance(self.project_start, datetime):
                raise ProjectScheduleSettingsPersistenceError("TIME_AWARE_PROJECT_START_REQUIRED")
            if self.project_start.tzinfo is None or self.project_start.utcoffset() is None:
                raise ProjectScheduleSettingsPersistenceError("TIMEZONE_REQUIRED_FOR_PROJECT_START")
            if self.project_finish is not None:
                if not isinstance(self.project_finish, datetime):
                    raise ProjectScheduleSettingsPersistenceError("INVALID_PROJECT_FINISH")
                if self.project_finish.tzinfo is None or self.project_finish.utcoffset() is None:
                    raise ProjectScheduleSettingsPersistenceError("TIMEZONE_REQUIRED_FOR_PROJECT_FINISH")

        if self.project_finish is not None and self.project_finish < self.project_start:
            raise ProjectScheduleSettingsPersistenceError("PROJECT_FINISH_BEFORE_START")


class ProjectScheduleSettingsRepository(Protocol):
    def save(
        self,
        settings: ProjectScheduleSettings,
        expected_revision: int | None = None,
    ) -> ProjectScheduleSettings: ...

    def get(self, scope: BackendScope) -> ProjectScheduleSettings | None: ...


def _schedule_options_payload(options: ScheduleOptions) -> dict[str, object]:
    """Serialize every current ScheduleOptions field using stable typed values."""
    result: dict[str, object] = {}
    for field in fields(ScheduleOptions):
        value = getattr(options, field.name)
        if isinstance(value, Enum):
            result[field.name] = value.value
        elif isinstance(value, (date, datetime)):
            result[field.name] = value.isoformat()
        elif field.name == "priority_list":
            if value is None:
                result[field.name] = None
            else:
                result[field.name] = [
                    {"field_name": item.field_name, "sort_order": item.sort_order.value}
                    for item in value
                ]
        elif field.name == "resource_list":
            result[field.name] = None if value is None else list(value)
        elif isinstance(value, tuple):
            result[field.name] = list(value)
        else:
            result[field.name] = value
    return result


def _schedule_options_from_payload(raw: object) -> ScheduleOptions:
    if not isinstance(raw, dict):
        raise ProjectScheduleSettingsPersistenceError("INVALID_STORED_SCHEDULE_OPTIONS")
    expected_fields = {field.name for field in fields(ScheduleOptions)}
    if set(raw) != expected_fields:
        # Do not silently use dataclass defaults when a stored schema is missing
        # a newly introduced or previously supported option.
        raise ProjectScheduleSettingsPersistenceError("SCHEDULE_OPTIONS_SCHEMA_MISMATCH")
    payload = dict(raw)
    enum_fields: dict[str, type[Enum]] = {
        "mode": ScheduleMode,
        "compute_total_float_type": TotalFloatCalculationType,
        "critical_activity_path_type": CriticalActivityPathType,
        "out_of_sequence_schedule_type": OutOfSequenceScheduleType,
        "start_to_start_lag_calculation_type": StartToStartLagCalculationType,
        "relationship_lag_calendar": RelationshipLagCalendar,
    }
    try:
        for name, enum_type in enum_fields.items():
            payload[name] = enum_type(payload[name])
        if payload["data_date"] is not None:
            if not isinstance(payload["data_date"], str):
                raise ValueError("invalid data_date")
            payload["data_date"] = date.fromisoformat(payload["data_date"])
        if payload["resource_list"] is not None:
            values = payload["resource_list"]
            if not isinstance(values, list) or not all(
                isinstance(item, str) and item.strip() for item in values
            ):
                raise ValueError("invalid resource_list")
            payload["resource_list"] = tuple(values)
        if payload["priority_list"] is not None:
            values = payload["priority_list"]
            if not isinstance(values, list):
                raise ValueError("invalid priority_list")
            priorities: list[PriorityListItem] = []
            for item in values:
                if not isinstance(item, dict) or set(item) != {"field_name", "sort_order"}:
                    raise ValueError("invalid priority item")
                priorities.append(
                    PriorityListItem(
                        field_name=item["field_name"],
                        sort_order=PrioritySortOrder(item["sort_order"]),
                    )
                )
            payload["priority_list"] = tuple(priorities)
        return ScheduleOptions(**payload)
    except (KeyError, TypeError, ValueError) as exc:
        raise ProjectScheduleSettingsPersistenceError("INVALID_STORED_SCHEDULE_OPTIONS") from exc


def _payload(settings: ProjectScheduleSettings) -> dict[str, object]:
    settings.validate()
    return {
        "schema_version": SCHEMA_VERSION,
        "scope": {
            "tenant_id": settings.scope.tenant_id,
            "project_id": settings.scope.project_id,
            "project_revision": settings.scope.project_revision,
        },
        "mode": settings.mode.value,
        "project_calendar": {
            "calendar_id": settings.project_calendar.calendar_id,
            "calendar_version": settings.project_calendar.calendar_version,
            "kind": settings.project_calendar.kind,
            "system": settings.project_calendar.system.value,
        },
        "project_start": settings.project_start.isoformat(),
        "project_finish": None if settings.project_finish is None else settings.project_finish.isoformat(),
        "schedule_options": _schedule_options_payload(settings.schedule_options),
        "project_leveling_priority": settings.project_leveling_priority,
    }


def _canonical_payload(settings: ProjectScheduleSettings) -> str:
    return json.dumps(_payload(settings), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _decode_datetime_or_date(value: object, mode: AuthoritativeScheduleMode, field_name: str):
    if not isinstance(value, str) or not value.strip():
        raise ProjectScheduleSettingsPersistenceError(f"INVALID_STORED_{field_name.upper()}")
    try:
        if mode is AuthoritativeScheduleMode.DATE_BASED:
            parsed = date.fromisoformat(value)
            if isinstance(parsed, datetime):
                raise ValueError("date-only value required")
            return parsed
        parsed_datetime = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed_datetime.tzinfo is None or parsed_datetime.utcoffset() is None:
            raise ValueError("timezone required")
        return parsed_datetime
    except (TypeError, ValueError) as exc:
        raise ProjectScheduleSettingsPersistenceError(f"INVALID_STORED_{field_name.upper()}") from exc


def _from_payload(
    scope: BackendScope,
    raw: str,
    record_revision: int,
) -> ProjectScheduleSettings:
    try:
        payload = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ProjectScheduleSettingsPersistenceError("INVALID_STORED_SETTINGS_JSON") from exc
    required = {
        "schema_version",
        "scope",
        "mode",
        "project_calendar",
        "project_start",
        "project_finish",
        "schedule_options",
        "project_leveling_priority",
    }
    if not isinstance(payload, dict) or set(payload) != required:
        raise ProjectScheduleSettingsPersistenceError("INVALID_STORED_SETTINGS_PAYLOAD")
    if payload["schema_version"] != SCHEMA_VERSION:
        raise ProjectScheduleSettingsPersistenceError("UNSUPPORTED_SETTINGS_SCHEMA_VERSION")
    expected_scope = {
        "tenant_id": scope.tenant_id,
        "project_id": scope.project_id,
        "project_revision": scope.project_revision,
    }
    if payload["scope"] != expected_scope:
        raise ProjectScheduleSettingsPersistenceError("SETTINGS_SCOPE_MISMATCH")
    try:
        mode = AuthoritativeScheduleMode(payload["mode"])
        calendar_raw = payload["project_calendar"]
        if not isinstance(calendar_raw, dict) or set(calendar_raw) != {
            "calendar_id", "calendar_version", "kind", "system"
        }:
            raise ValueError("invalid project calendar")
        project_calendar = CalendarReference(
            calendar_id=calendar_raw["calendar_id"],
            calendar_version=calendar_raw["calendar_version"],
            kind=calendar_raw["kind"],
            system=CalendarSystem(calendar_raw["system"]),
        )
        project_start = _decode_datetime_or_date(payload["project_start"], mode, "project_start")
        project_finish = (
            None
            if payload["project_finish"] is None
            else _decode_datetime_or_date(payload["project_finish"], mode, "project_finish")
        )
        if isinstance(payload["project_leveling_priority"], bool) or not isinstance(
            payload["project_leveling_priority"], int
        ):
            raise ValueError("invalid project leveling priority")
        result = ProjectScheduleSettings(
            scope=scope,
            mode=mode,
            project_calendar=project_calendar,
            project_start=project_start,
            project_finish=project_finish,
            schedule_options=_schedule_options_from_payload(payload["schedule_options"]),
            project_leveling_priority=payload["project_leveling_priority"],
            record_revision=record_revision,
        )
        result.validate()
        return result
    except ProjectScheduleSettingsPersistenceError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise ProjectScheduleSettingsPersistenceError("INVALID_STORED_SETTINGS_PAYLOAD") from exc


def _content_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _validate_expected_revision(value: int | None) -> None:
    if value is not None and (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 0 <= value <= MAX_SAFE_REVISION
    ):
        raise ProjectScheduleSettingsPersistenceError("INVALID_EXPECTED_REVISION")


class SQLiteProjectScheduleSettingsRepository:
    """SQLite adapter; preserves an outer caller-owned transaction."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        was_in_transaction = self.connection.in_transaction
        try:
            self.connection.execute(
                """CREATE TABLE IF NOT EXISTS project_schedule_settings (
                    tenant_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    project_revision INTEGER NOT NULL,
                    record_revision INTEGER NOT NULL,
                    canonical_payload TEXT NOT NULL,
                    settings_hash TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, project_id)
                )"""
            )
            self.connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_project_schedule_settings_revision "
                "ON project_schedule_settings(tenant_id, project_id, project_revision)"
            )
            if not was_in_transaction:
                self.connection.commit()
        except Exception:
            if not was_in_transaction:
                self.connection.rollback()
            raise

    def save(
        self,
        settings: ProjectScheduleSettings,
        expected_revision: int | None = None,
    ) -> ProjectScheduleSettings:
        settings.validate()
        _validate_expected_revision(expected_revision)
        was_in_transaction = self.connection.in_transaction
        existing = self.connection.execute(
            "SELECT project_revision,record_revision,canonical_payload,settings_hash "
            "FROM project_schedule_settings WHERE tenant_id=? AND project_id=?",
            (settings.scope.tenant_id, settings.scope.project_id),
        ).fetchone()
        if existing is None:
            if expected_revision not in (None, 0):
                raise ProjectScheduleSettingsPersistenceError("REVISION_CONFLICT")
            payload = _canonical_payload(replace(settings, record_revision=1))
            stored_hash = _content_hash(payload)
            self.connection.execute(
                "INSERT INTO project_schedule_settings "
                "(tenant_id,project_id,project_revision,record_revision,canonical_payload,settings_hash) "
                "VALUES (?,?,?,?,?,?)",
                (
                    settings.scope.tenant_id, settings.scope.project_id, settings.scope.project_revision,
                    1, payload, stored_hash,
                ),
            )
            if not was_in_transaction:
                self.connection.commit()
            return replace(settings, record_revision=1)

        if int(existing[0]) != settings.scope.project_revision:
            raise ProjectScheduleSettingsPersistenceError("REVISION_CONFLICT")
        if _content_hash(str(existing[2])) != str(existing[3]):
            raise ProjectScheduleSettingsPersistenceError("SETTINGS_HASH_MISMATCH")
        current = _from_payload(settings.scope, str(existing[2]), int(existing[1]))
        if expected_revision is None or expected_revision != current.record_revision:
            raise ProjectScheduleSettingsPersistenceError("REVISION_CONFLICT")
        stored = replace(settings, record_revision=current.record_revision + 1)
        payload = _canonical_payload(stored)
        cursor = self.connection.execute(
            "UPDATE project_schedule_settings SET project_revision=?,record_revision=?,canonical_payload=?,settings_hash=? "
            "WHERE tenant_id=? AND project_id=? AND project_revision=? AND record_revision=?",
            (
                stored.scope.project_revision, stored.record_revision, payload, _content_hash(payload),
                stored.scope.tenant_id, stored.scope.project_id, stored.scope.project_revision,
                current.record_revision,
            ),
        )
        if cursor.rowcount != 1:
            if not was_in_transaction:
                self.connection.rollback()
            raise ProjectScheduleSettingsPersistenceError("REVISION_CONFLICT")
        if not was_in_transaction:
            self.connection.commit()
        return stored

    def get(self, scope: BackendScope) -> ProjectScheduleSettings | None:
        scope.validate()
        row = self.connection.execute(
            "SELECT project_revision,record_revision,canonical_payload,settings_hash "
            "FROM project_schedule_settings WHERE tenant_id=? AND project_id=?",
            (scope.tenant_id, scope.project_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[0]) != scope.project_revision:
            raise ProjectScheduleSettingsPersistenceError("REVISION_CONFLICT")
        raw = str(row[2])
        if _content_hash(raw) != str(row[3]):
            raise ProjectScheduleSettingsPersistenceError("SETTINGS_HASH_MISMATCH")
        return _from_payload(scope, raw, int(row[1]))


class PostgresProjectScheduleSettingsRepository:
    """PostgreSQL adapter; transaction ownership remains with the caller."""

    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS project_schedule_settings ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision BIGINT NOT NULL, "
            "record_revision BIGINT NOT NULL, canonical_payload TEXT NOT NULL, settings_hash TEXT NOT NULL, "
            "PRIMARY KEY (tenant_id, project_id))"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_project_schedule_settings_revision "
            "ON project_schedule_settings(tenant_id, project_id, project_revision)"
        )

    def save(
        self,
        settings: ProjectScheduleSettings,
        expected_revision: int | None = None,
    ) -> ProjectScheduleSettings:
        settings.validate()
        _validate_expected_revision(expected_revision)
        existing = self.connection.execute(
            "SELECT project_revision,record_revision,canonical_payload,settings_hash "
            "FROM project_schedule_settings WHERE tenant_id=%s AND project_id=%s FOR UPDATE",
            (settings.scope.tenant_id, settings.scope.project_id),
        ).fetchone()
        if existing is None:
            if expected_revision not in (None, 0):
                raise ProjectScheduleSettingsPersistenceError("REVISION_CONFLICT")
            stored = replace(settings, record_revision=1)
            payload = _canonical_payload(stored)
            self.connection.execute(
                "INSERT INTO project_schedule_settings "
                "(tenant_id,project_id,project_revision,record_revision,canonical_payload,settings_hash) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (
                    stored.scope.tenant_id, stored.scope.project_id, stored.scope.project_revision,
                    stored.record_revision, payload, _content_hash(payload),
                ),
            )
            return stored
        if int(existing[0]) != settings.scope.project_revision:
            raise ProjectScheduleSettingsPersistenceError("REVISION_CONFLICT")
        current_raw = str(existing[2])
        if _content_hash(current_raw) != str(existing[3]):
            raise ProjectScheduleSettingsPersistenceError("SETTINGS_HASH_MISMATCH")
        current = _from_payload(settings.scope, current_raw, int(existing[1]))
        if expected_revision is None or expected_revision != current.record_revision:
            raise ProjectScheduleSettingsPersistenceError("REVISION_CONFLICT")
        stored = replace(settings, record_revision=current.record_revision + 1)
        payload = _canonical_payload(stored)
        cursor = self.connection.execute(
            "UPDATE project_schedule_settings SET project_revision=%s,record_revision=%s,canonical_payload=%s,settings_hash=%s "
            "WHERE tenant_id=%s AND project_id=%s AND project_revision=%s AND record_revision=%s",
            (
                stored.scope.project_revision, stored.record_revision, payload, _content_hash(payload),
                stored.scope.tenant_id, stored.scope.project_id, stored.scope.project_revision,
                current.record_revision,
            ),
        )
        if getattr(cursor, "rowcount", 1) != 1:
            raise ProjectScheduleSettingsPersistenceError("REVISION_CONFLICT")
        return stored

    def get(self, scope: BackendScope) -> ProjectScheduleSettings | None:
        scope.validate()
        row = self.connection.execute(
            "SELECT project_revision,record_revision,canonical_payload,settings_hash "
            "FROM project_schedule_settings WHERE tenant_id=%s AND project_id=%s",
            (scope.tenant_id, scope.project_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[0]) != scope.project_revision:
            raise ProjectScheduleSettingsPersistenceError("REVISION_CONFLICT")
        raw = str(row[2])
        if _content_hash(raw) != str(row[3]):
            raise ProjectScheduleSettingsPersistenceError("SETTINGS_HASH_MISMATCH")
        return _from_payload(scope, raw, int(row[1]))


__all__ = [
    "ProjectScheduleSettings",
    "ProjectScheduleSettingsPersistenceError",
    "ProjectScheduleSettingsRepository",
    "SQLiteProjectScheduleSettingsRepository",
    "PostgresProjectScheduleSettingsRepository",
]
