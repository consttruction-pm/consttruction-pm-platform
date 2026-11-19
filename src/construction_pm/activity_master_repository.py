from __future__ import annotations

"""Authoritative Activity Master persistence.

This repository owns the schedule Activity entity. P6 child repositories such as
activity steps and period actuals remain dependent records and are not replaced
by this master store.
"""

import json
import math
import sqlite3
from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol
from uuid import uuid4

from .backend_p0.models import BackendScope, MAX_SAFE_REVISION
from .wbs_master_repository import PostgresWBSMasterRepository, SQLiteWBSMasterRepository
from .scheduling.activity import (
    ActivityDurationType,
    ActivityLevelingPriority,
    ActivityStatus,
    ActivityStatusCode,
    ActivityType,
    PercentCompleteType,
)
from .scheduling.time_duration import DurationUnit


class ActivityPersistenceError(ValueError):
    """Raised when an Activity Master record is invalid or conflicts."""


@dataclass(frozen=True)
class ActivityMaster:
    scope: BackendScope
    activity_id: str
    duration_value: Decimal
    duration_unit: DurationUnit
    actual_start: date | datetime | None = None
    record_revision: int = 0
    expected_finish: date | datetime | None = None
    actual_finish: date | datetime | None = None
    remaining_duration: int | None = None
    remaining_start: date | datetime | None = None
    percent_complete: float | None = None
    percent_complete_type: PercentCompleteType = PercentCompleteType.DURATION
    planned_finish: date | datetime | None = None
    leveling_priority: ActivityLevelingPriority = ActivityLevelingPriority.NORMAL
    original_duration: int | None = None
    name: str = ""
    short_name: str | None = None
    activity_type: ActivityType = ActivityType.TASK_DEPENDENT
    status: ActivityStatus = ActivityStatus.NOT_STARTED
    status_code: ActivityStatusCode = ActivityStatusCode.PLANNED
    wbs_id: str | None = None
    duration_type: ActivityDurationType = ActivityDurationType.FIXED_DURATION_UNITS
    cost_account_id: str | None = None

    def validate(self) -> None:
        self.scope.validate()
        if not isinstance(self.activity_id, str) or not self.activity_id.strip():
            raise ActivityPersistenceError("INVALID_ACTIVITY_ID")
        if not isinstance(self.name, str):
            raise ActivityPersistenceError("INVALID_ACTIVITY_NAME")
        if self.short_name is not None and (
            not isinstance(self.short_name, str) or not self.short_name.strip()
        ):
            raise ActivityPersistenceError("INVALID_SHORT_NAME")
        if not isinstance(self.activity_type, ActivityType):
            raise ActivityPersistenceError("INVALID_ACTIVITY_TYPE")
        if not isinstance(self.status, ActivityStatus):
            raise ActivityPersistenceError("INVALID_ACTIVITY_STATUS")
        if not isinstance(self.status_code, ActivityStatusCode):
            raise ActivityPersistenceError("INVALID_ACTIVITY_STATUS_CODE")
        if not isinstance(self.duration_value, Decimal) or not self.duration_value.is_finite():
            raise ActivityPersistenceError("INVALID_DURATION_VALUE")
        if self.duration_value < 0:
            raise ActivityPersistenceError("INVALID_DURATION_VALUE")
        if not isinstance(self.duration_unit, DurationUnit):
            raise ActivityPersistenceError("INVALID_DURATION_UNIT")
        if not isinstance(self.duration_type, ActivityDurationType):
            raise ActivityPersistenceError("INVALID_DURATION_TYPE")
        if self.actual_start is not None and not isinstance(self.actual_start, (date, datetime)):
            raise ActivityPersistenceError("INVALID_ACTUAL_START")
        if self.expected_finish is not None and not isinstance(self.expected_finish, (date, datetime)):
            raise ActivityPersistenceError("INVALID_EXPECTED_FINISH")
        if self.planned_finish is not None and not isinstance(self.planned_finish, (date, datetime)):
            raise ActivityPersistenceError("INVALID_PLANNED_FINISH")
        if not isinstance(self.leveling_priority, ActivityLevelingPriority):
            raise ActivityPersistenceError("INVALID_LEVELING_PRIORITY")
        if self.original_duration is not None and (
            isinstance(self.original_duration, bool)
            or not isinstance(self.original_duration, int)
            or self.original_duration < 0
        ):
            raise ActivityPersistenceError("INVALID_ORIGINAL_DURATION")
        if self.actual_finish is not None and not isinstance(self.actual_finish, (date, datetime)):
            raise ActivityPersistenceError("INVALID_ACTUAL_FINISH")
        if self.remaining_duration is not None:
            if isinstance(self.remaining_duration, bool) or not isinstance(self.remaining_duration, int) or self.remaining_duration < 0:
                raise ActivityPersistenceError("INVALID_REMAINING_DURATION")
        if self.remaining_start is not None and not isinstance(self.remaining_start, (date, datetime)):
            raise ActivityPersistenceError("INVALID_REMAINING_START")
        if self.percent_complete is not None:
            if isinstance(self.percent_complete, bool) or not isinstance(self.percent_complete, (int, float)):
                raise ActivityPersistenceError("INVALID_PERCENT_COMPLETE")
            if not math.isfinite(float(self.percent_complete)) or not 0 <= float(self.percent_complete) <= 100:
                raise ActivityPersistenceError("INVALID_PERCENT_COMPLETE")
        if not isinstance(self.percent_complete_type, PercentCompleteType):
            raise ActivityPersistenceError("INVALID_PERCENT_COMPLETE_TYPE")
        if isinstance(self.record_revision, bool) or not isinstance(self.record_revision, int) or self.record_revision < 0:
            raise ActivityPersistenceError("INVALID_RECORD_REVISION")
        if self.record_revision > MAX_SAFE_REVISION:
            raise ActivityPersistenceError("INVALID_RECORD_REVISION")
        if self.wbs_id is not None and (
            not isinstance(self.wbs_id, str) or not self.wbs_id.strip()
        ):
            raise ActivityPersistenceError("INVALID_WBS_ID")
        if self.cost_account_id is not None and (
            not isinstance(self.cost_account_id, str)
            or not self.cost_account_id.strip()
            or len(self.cost_account_id) > 120
        ):
            raise ActivityPersistenceError("INVALID_COST_ACCOUNT_ID")

    def payload(self) -> tuple[object, ...]:
        return (
            self.activity_id,
            str(self.duration_value),
            self.duration_unit.value,
            None if self.actual_start is None else self.actual_start.isoformat(),
            None if self.expected_finish is None else self.expected_finish.isoformat(),
            None if self.actual_finish is None else self.actual_finish.isoformat(),
            self.remaining_duration,
            None if self.remaining_start is None else self.remaining_start.isoformat(),
            self.percent_complete,
            self.percent_complete_type.value,
            None if self.planned_finish is None else self.planned_finish.isoformat(),
            self.leveling_priority.value,
            self.original_duration,
            self.name,
            self.activity_type.value,
            self.status.value,
            self.status_code.value,
            self.wbs_id,
            self.short_name,
            self.duration_type.value,
            self.cost_account_id,
        )


_ACTIVITY_MASTER_SELECT_COLUMNS = (
    "activity_id,duration_value,duration_unit,actual_start,actual_finish,"
    "remaining_duration,remaining_start,percent_complete,percent_complete_type,"
    "record_revision,expected_finish,planned_finish,leveling_priority,"
    "original_duration,name,activity_type,status,status_code,"
    "(SELECT assignment.wbs_id FROM activity_wbs_assignment AS assignment "
    "WHERE assignment.tenant_id=activity_master.tenant_id "
    "AND assignment.project_id=activity_master.project_id "
    "AND assignment.activity_id=activity_master.activity_id) AS wbs_id,"
    "short_name,duration_type,cost_account_id"
)


class ActivityMasterRepository(Protocol):
    def save(self, activity: ActivityMaster, expected_revision: int | None = None) -> ActivityMaster: ...
    def get(self, scope: BackendScope, activity_id: str) -> ActivityMaster | None: ...
    def list(self, scope: BackendScope) -> tuple[ActivityMaster, ...]: ...
    def delete(self, scope: BackendScope, activity_id: str, *, expected_revision: int) -> bool: ...
    def renumber(
        self,
        scope: BackendScope,
        entries: tuple[tuple[str, str, int], ...],
        *,
        include_baselines: bool = True,
    ) -> dict[str, object]: ...


def _decode_actual_start(value: object) -> date | datetime | None:
    if value is None:
        return None
    text = str(value)
    try:
        return datetime.fromisoformat(text) if "T" in text else date.fromisoformat(text)
    except ValueError as exc:
        raise ActivityPersistenceError("INVALID_STORED_ACTUAL_START") from exc


def _decode_actual_finish(value: object) -> date | datetime | None:
    if value is None:
        return None
    text = str(value)
    try:
        return datetime.fromisoformat(text) if "T" in text else date.fromisoformat(text)
    except ValueError as exc:
        raise ActivityPersistenceError("INVALID_STORED_ACTUAL_FINISH") from exc


def _decode_remaining_start(value: object) -> date | datetime | None:
    if value is None:
        return None
    text = str(value)
    try:
        return datetime.fromisoformat(text) if "T" in text else date.fromisoformat(text)
    except ValueError as exc:
        raise ActivityPersistenceError("INVALID_STORED_REMAINING_START") from exc


def _decode_expected_finish(value: object) -> date | datetime | None:
    if value is None:
        return None
    text = str(value)
    try:
        return datetime.fromisoformat(text) if "T" in text else date.fromisoformat(text)
    except ValueError as exc:
        raise ActivityPersistenceError("INVALID_STORED_EXPECTED_FINISH") from exc


def _decode_planned_finish(value: object) -> date | datetime | None:
    if value is None:
        return None
    text = str(value)
    try:
        return datetime.fromisoformat(text) if "T" in text else date.fromisoformat(text)
    except ValueError as exc:
        raise ActivityPersistenceError("INVALID_STORED_PLANNED_FINISH") from exc


def _decode_activity_leveling_priority(value: object) -> ActivityLevelingPriority:
    # P6 defaults an activity's leveling priority to Normal unless overridden.
    if value is None:
        return ActivityLevelingPriority.NORMAL
    try:
        return ActivityLevelingPriority.from_p6_value(str(value))
    except ValueError as exc:
        raise ActivityPersistenceError("INVALID_STORED_LEVELING_PRIORITY") from exc


def _decode_original_duration(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ActivityPersistenceError("INVALID_STORED_ORIGINAL_DURATION")
    return value


def _decode_activity_name(value: object) -> str:
    if not isinstance(value, str):
        raise ActivityPersistenceError("INVALID_STORED_ACTIVITY_NAME")
    return value


def _decode_short_name(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ActivityPersistenceError("INVALID_STORED_SHORT_NAME")
    return value


def _decode_activity_type(value: object) -> ActivityType:
    try:
        return ActivityType.from_p6_value(str(value))
    except ValueError as exc:
        raise ActivityPersistenceError("INVALID_STORED_ACTIVITY_TYPE") from exc


def _decode_activity_status(value: object) -> ActivityStatus:
    try:
        return ActivityStatus.from_p6_value(str(value))
    except ValueError as exc:
        raise ActivityPersistenceError("INVALID_STORED_ACTIVITY_STATUS") from exc


def _decode_activity_status_code(value: object) -> ActivityStatusCode:
    try:
        return ActivityStatusCode.from_p6_value(str(value))
    except ValueError as exc:
        raise ActivityPersistenceError("INVALID_STORED_ACTIVITY_STATUS_CODE") from exc


def _decode_activity_duration_type(value: object) -> ActivityDurationType:
    if value is None:
        return ActivityDurationType.FIXED_DURATION_UNITS
    try:
        return ActivityDurationType.from_p6_value(str(value))
    except ValueError as exc:
        raise ActivityPersistenceError("INVALID_STORED_ACTIVITY_DURATION_TYPE") from exc


def _from_row(scope: BackendScope, row: tuple[object, ...]) -> ActivityMaster:
    try:
        result = ActivityMaster(
            scope=scope,
            activity_id=str(row[0]),
            duration_value=Decimal(str(row[1])),
            duration_unit=DurationUnit(str(row[2])),
            actual_start=_decode_actual_start(row[3]),
            record_revision=int(row[9]),
            expected_finish=_decode_expected_finish(row[10]),
            actual_finish=_decode_actual_finish(row[4]),
            remaining_duration=None if row[5] is None else int(row[5]),
            remaining_start=_decode_remaining_start(row[6]),
            percent_complete=None if row[7] is None else float(row[7]),
            percent_complete_type=PercentCompleteType(str(row[8])),
            planned_finish=_decode_planned_finish(row[11]),
            leveling_priority=_decode_activity_leveling_priority(row[12]),
            original_duration=_decode_original_duration(row[13]),
            name=_decode_activity_name(row[14]),
            activity_type=_decode_activity_type(row[15]),
            status=_decode_activity_status(row[16]),
            status_code=_decode_activity_status_code(row[17]),
            wbs_id=None if row[18] is None else str(row[18]),
            short_name=None if row[19] is None else _decode_short_name(row[19]),
            duration_type=_decode_activity_duration_type(row[20]),
            cost_account_id=(
                None
                if row[21] is None or not str(row[21]).strip()
                else str(row[21])
            ),
        )
        result.validate()
        return result
    except (TypeError, ValueError, ArithmeticError) as exc:
        raise ActivityPersistenceError("INVALID_STORED_ACTIVITY") from exc


_RENUMBER_COLUMNS = (
    "tenant_id,project_id,project_revision,activity_id,duration_value,duration_unit,"
    "actual_start,actual_finish,remaining_duration,remaining_start,percent_complete,"
    "percent_complete_type,record_revision,expected_finish,planned_finish,"
    "leveling_priority,original_duration,name,activity_type,status,status_code,"
    "short_name,duration_type,cost_account_id"
)
_RENUMBER_COLUMN_NAMES = tuple(_RENUMBER_COLUMNS.split(","))
# The activity ID value is written at this index of a renumber row.
_RENUMBER_ID_INDEX = _RENUMBER_COLUMN_NAMES.index("activity_id")


def _validated_renumber_entries(
    entries: object,
) -> tuple[tuple[str, str, int], ...]:
    if not isinstance(entries, (list, tuple)) or not entries:
        raise ActivityPersistenceError("INVALID_RENUMBER_ENTRIES")
    normalized: list[tuple[str, str, int]] = []
    old_ids: set[str] = set()
    new_ids: set[str] = set()
    for entry in entries:
        if not isinstance(entry, (list, tuple)) or len(entry) != 3:
            raise ActivityPersistenceError("INVALID_RENUMBER_ENTRIES")
        old_id, new_id, expected_revision = entry
        if not isinstance(old_id, str) or not old_id.strip():
            raise ActivityPersistenceError("INVALID_ACTIVITY_ID")
        if not isinstance(new_id, str) or not new_id.strip() or len(new_id) > 80:
            raise ActivityPersistenceError("INVALID_NEW_ACTIVITY_ID")
        if old_id == new_id:
            raise ActivityPersistenceError("INVALID_RENUMBER_ENTRIES")
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 1:
            raise ActivityPersistenceError("INVALID_EXPECTED_REVISION")
        if old_id in old_ids or new_id in new_ids:
            raise ActivityPersistenceError("INVALID_RENUMBER_ENTRIES")
        old_ids.add(old_id)
        new_ids.add(new_id)
        normalized.append((old_id, new_id, expected_revision))
    return tuple(normalized)


def _renumber_collision(
    existing_ids: set[str],
    selected_ids: set[str],
    new_ids: set[str],
) -> None:
    # A selected activity may take an ID another selected activity is leaving;
    # the two-phase move makes that safe. It may never take an ID owned by an
    # activity outside the renumber set.
    for new_id in new_ids:
        if new_id in existing_ids and new_id not in selected_ids:
            raise ActivityPersistenceError("RENUMBER_TARGET_EXISTS")


def _replace_document_activity_refs(value: object, old_id: str, new_id: str) -> bool:
    """Rewrite activity references inside one stored document JSON value.

    Document records keep their links in `linked_entity_refs`; a few payloads
    also carry explicit activity/predecessor/successor ids. Only exact identity
    values are replaced so free text is never rewritten.
    """
    changed = False
    if isinstance(value, dict):
        for key, item in list(value.items()):
            if key == "linked_entity_refs" and isinstance(item, list):
                next_items = [new_id if entry == old_id else entry for entry in item]
                if next_items != item:
                    value[key] = next_items
                    changed = True
            elif key in {"activity_id", "predecessor_id", "successor_id"} and item == old_id:
                value[key] = new_id
                changed = True
            elif isinstance(item, (dict, list)):
                changed = _replace_document_activity_refs(item, old_id, new_id) or changed
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, (dict, list)):
                changed = _replace_document_activity_refs(item, old_id, new_id) or changed
    return changed


class SQLiteActivityMasterRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        was_in_transaction = self.connection.in_transaction
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        SQLiteWBSMasterRepository(self.connection)
        self.connection.execute("""CREATE TABLE IF NOT EXISTS activity_master (
            tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision INTEGER NOT NULL,
            activity_id TEXT NOT NULL, duration_value TEXT NOT NULL, duration_unit TEXT NOT NULL,
            actual_start TEXT, actual_finish TEXT, remaining_duration INTEGER, remaining_start TEXT,
            percent_complete REAL, percent_complete_type TEXT NOT NULL DEFAULT 'DURATION',
            record_revision INTEGER NOT NULL, expected_finish TEXT, planned_finish TEXT,
            leveling_priority TEXT NOT NULL DEFAULT 'Normal', original_duration INTEGER,
            name TEXT NOT NULL DEFAULT '', activity_type TEXT NOT NULL DEFAULT 'Task Dependent',
            status TEXT NOT NULL DEFAULT 'Not Started', status_code TEXT NOT NULL DEFAULT 'Planned',
            duration_type TEXT NOT NULL DEFAULT 'Fixed Duration & Units',
            short_name TEXT,
            cost_account_id TEXT,
            PRIMARY KEY (tenant_id, project_id, activity_id))""")
        columns = {row[1] for row in self.connection.execute("PRAGMA table_info(activity_master)").fetchall()}
        if "expected_finish" not in columns:
            self.connection.execute("ALTER TABLE activity_master ADD COLUMN expected_finish TEXT")
        if "planned_finish" not in columns:
            self.connection.execute("ALTER TABLE activity_master ADD COLUMN planned_finish TEXT")
        if "leveling_priority" not in columns:
            self.connection.execute(
                "ALTER TABLE activity_master ADD COLUMN leveling_priority TEXT NOT NULL DEFAULT 'Normal'"
            )
        if "original_duration" not in columns:
            self.connection.execute("ALTER TABLE activity_master ADD COLUMN original_duration INTEGER")
        for column, definition in (
            ("name", "TEXT NOT NULL DEFAULT ''"),
            ("activity_type", "TEXT NOT NULL DEFAULT 'Task Dependent'"),
            ("status", "TEXT NOT NULL DEFAULT 'Not Started'"),
            ("status_code", "TEXT NOT NULL DEFAULT 'Planned'"),
            ("short_name", "TEXT"),
            ("duration_type", "TEXT NOT NULL DEFAULT 'Fixed Duration & Units'"),
            ("cost_account_id", "TEXT"),
        ):
            if column not in columns:
                self.connection.execute(f"ALTER TABLE activity_master ADD COLUMN {column} {definition}")
        self.connection.execute(
            "UPDATE activity_master SET leveling_priority='Normal' WHERE leveling_priority IS NULL"
        )
        if "actual_finish" not in columns:
            self.connection.execute("ALTER TABLE activity_master ADD COLUMN actual_finish TEXT")
        if "remaining_duration" not in columns:
            self.connection.execute("ALTER TABLE activity_master ADD COLUMN remaining_duration INTEGER")
        if "remaining_start" not in columns:
            self.connection.execute("ALTER TABLE activity_master ADD COLUMN remaining_start TEXT")
        if "percent_complete" not in columns:
            self.connection.execute("ALTER TABLE activity_master ADD COLUMN percent_complete REAL")
        if "percent_complete_type" not in columns:
            self.connection.execute("ALTER TABLE activity_master ADD COLUMN percent_complete_type TEXT NOT NULL DEFAULT 'DURATION'")
        self.connection.execute("CREATE INDEX IF NOT EXISTS idx_activity_master_revision ON activity_master(tenant_id, project_id, project_revision, activity_id)")
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS activity_wbs_assignment (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                activity_id TEXT NOT NULL,
                wbs_id TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, activity_id),
                FOREIGN KEY (tenant_id, project_id, activity_id)
                    REFERENCES activity_master (tenant_id, project_id, activity_id) ON DELETE CASCADE,
                FOREIGN KEY (tenant_id, project_id, wbs_id)
                    REFERENCES wbs_master (tenant_id, project_id, wbs_id) ON DELETE RESTRICT
            )"""
        )
        self.connection.execute("CREATE INDEX IF NOT EXISTS idx_activity_wbs_assignment_wbs ON activity_wbs_assignment(tenant_id, project_id, wbs_id)")
        # Schema setup must not accidentally commit a transaction owned by the caller.
        if not was_in_transaction:
            self.connection.commit()

    def _validate_wbs_assignment(
        self, scope: BackendScope, wbs_id: str | None, *, require_assignment: bool = True
    ) -> None:
        if wbs_id is None:
            if not require_assignment:
                # Reads must still surface legacy rows that predate the
                # canonical WBS tree so the Workspace provider can fail closed
                # with an explicit contract error instead of hiding data.
                return
            # A project that has a canonical WBS tree must not gain an activity
            # without a hierarchy link. Projects with no WBS rows keep the
            # legacy unassigned behaviour so existing data remains writable.
            exists = self.connection.execute(
                "SELECT 1 FROM wbs_master WHERE tenant_id=? AND project_id=? LIMIT 1",
                (scope.tenant_id, scope.project_id),
            ).fetchone()
            if exists is not None:
                raise ActivityPersistenceError("WBS_REQUIRED")
            return
        row = self.connection.execute("SELECT project_revision FROM wbs_master WHERE tenant_id=? AND project_id=? AND wbs_id=?", (scope.tenant_id, scope.project_id, wbs_id)).fetchone()
        if row is None:
            raise ActivityPersistenceError("WBS_NOT_FOUND_OR_SCOPE_MISMATCH")
        if int(row[0]) != scope.project_revision:
            raise ActivityPersistenceError("REVISION_CONFLICT")

    def _sync_wbs_assignment(self, activity: ActivityMaster) -> None:
        if activity.wbs_id is None:
            self.connection.execute("DELETE FROM activity_wbs_assignment WHERE tenant_id=? AND project_id=? AND activity_id=?", (activity.scope.tenant_id, activity.scope.project_id, activity.activity_id))
            return
        self.connection.execute("INSERT INTO activity_wbs_assignment (tenant_id,project_id,activity_id,wbs_id) VALUES (?,?,?,?) ON CONFLICT(tenant_id,project_id,activity_id) DO UPDATE SET wbs_id=excluded.wbs_id", (activity.scope.tenant_id, activity.scope.project_id, activity.activity_id, activity.wbs_id))

    def save(self, activity: ActivityMaster, expected_revision: int | None = None) -> ActivityMaster:
        activity.validate()
        if expected_revision is not None and (
            isinstance(expected_revision, bool)
            or not isinstance(expected_revision, int)
            or expected_revision < 0
        ):
            raise ActivityPersistenceError("INVALID_EXPECTED_REVISION")

        # A standalone write owns its transaction and takes an immediate write lock
        # before the read/insert-or-update sequence. If the caller already owns a
        # transaction, all operations stay inside it and its commit/rollback policy.
        was_in_transaction = self.connection.in_transaction
        if not was_in_transaction:
            self.connection.execute("BEGIN IMMEDIATE")
        try:
            self._validate_wbs_assignment(activity.scope, activity.wbs_id)
            row = self.connection.execute(
                f"SELECT {_ACTIVITY_MASTER_SELECT_COLUMNS},project_revision FROM activity_master "
                "WHERE tenant_id=? AND project_id=? AND activity_id=?",
                (activity.scope.tenant_id, activity.scope.project_id, activity.activity_id),
            ).fetchone()
            if row is None:
                if expected_revision not in (None, 0):
                    raise ActivityPersistenceError("REVISION_CONFLICT")
                stored = replace(activity, record_revision=1)
                self.connection.execute(
                    "INSERT INTO activity_master "
                    "(tenant_id,project_id,project_revision,activity_id,duration_value,duration_unit,"
                    "actual_start,actual_finish,remaining_duration,remaining_start,percent_complete,"
                    "percent_complete_type,record_revision,expected_finish,planned_finish,leveling_priority,"
                    "original_duration,name,activity_type,status,status_code,short_name,duration_type,cost_account_id) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        stored.scope.tenant_id, stored.scope.project_id,
                        stored.scope.project_revision, stored.activity_id,
                        str(stored.duration_value), stored.duration_unit.value,
                        None if stored.actual_start is None else stored.actual_start.isoformat(),
                        None if stored.actual_finish is None else stored.actual_finish.isoformat(),
                        stored.remaining_duration,
                        None if stored.remaining_start is None else stored.remaining_start.isoformat(),
                        stored.percent_complete, stored.percent_complete_type.value,
                        stored.record_revision,
                        None if stored.expected_finish is None else stored.expected_finish.isoformat(),
                        None if stored.planned_finish is None else stored.planned_finish.isoformat(),
                        stored.leveling_priority.value, stored.original_duration,
                        stored.name, stored.activity_type.value, stored.status.value,
                        stored.status_code.value, stored.short_name,
                        stored.duration_type.value, stored.cost_account_id,
                    ),
                )
            else:
                current = _from_row(activity.scope, row[:22])
                if int(row[22]) != activity.scope.project_revision:
                    raise ActivityPersistenceError("REVISION_CONFLICT")
                if expected_revision is None or expected_revision != current.record_revision:
                    raise ActivityPersistenceError("REVISION_CONFLICT")
                stored = replace(activity, record_revision=current.record_revision + 1)
                update_cursor = self.connection.execute(
                    "UPDATE activity_master SET project_revision=?,duration_value=?,duration_unit=?,"
                    "actual_start=?,actual_finish=?,remaining_duration=?,remaining_start=?,percent_complete=?,"
                    "percent_complete_type=?,record_revision=?,expected_finish=?,planned_finish=?,"
                    "leveling_priority=?,original_duration=?,name=?,activity_type=?,status=?,status_code=?,"
                    "short_name=?,duration_type=?,cost_account_id=? "
                    "WHERE tenant_id=? AND project_id=? AND activity_id=? AND record_revision=?",
                    (
                        stored.scope.project_revision, str(stored.duration_value), stored.duration_unit.value,
                        None if stored.actual_start is None else stored.actual_start.isoformat(),
                        None if stored.actual_finish is None else stored.actual_finish.isoformat(),
                        stored.remaining_duration, None if stored.remaining_start is None else stored.remaining_start.isoformat(),
                        stored.percent_complete, stored.percent_complete_type.value, stored.record_revision,
                        None if stored.expected_finish is None else stored.expected_finish.isoformat(),
                        None if stored.planned_finish is None else stored.planned_finish.isoformat(),
                        stored.leveling_priority.value, stored.original_duration, stored.name,
                        stored.activity_type.value, stored.status.value, stored.status_code.value,
                        stored.short_name, stored.duration_type.value, stored.cost_account_id,
                        stored.scope.tenant_id, stored.scope.project_id, stored.activity_id,
                        current.record_revision,
                    ),
                )
                if update_cursor.rowcount != 1:
                    raise ActivityPersistenceError("REVISION_CONFLICT")
            self._sync_wbs_assignment(stored)

            if not was_in_transaction:
                self.connection.commit()
            return stored
        except Exception:
            if not was_in_transaction and self.connection.in_transaction:
                self.connection.rollback()
            raise

    def get(self, scope: BackendScope, activity_id: str) -> ActivityMaster | None:
        scope.validate()
        if not isinstance(activity_id, str) or not activity_id.strip():
            raise ActivityPersistenceError("INVALID_ACTIVITY_ID")
        row = self.connection.execute(
            f"SELECT {_ACTIVITY_MASTER_SELECT_COLUMNS},project_revision FROM activity_master WHERE tenant_id=? AND project_id=? AND activity_id=?",
            (scope.tenant_id, scope.project_id, activity_id)).fetchone()
        if row is None:
            return None
        if int(row[22]) != scope.project_revision:
            raise ActivityPersistenceError("REVISION_CONFLICT")
        result = _from_row(scope, row[:22])
        self._validate_wbs_assignment(scope, result.wbs_id, require_assignment=False)
        return result

    def list(self, scope: BackendScope) -> tuple[ActivityMaster, ...]:
        scope.validate()
        rows = self.connection.execute(
            f"SELECT {_ACTIVITY_MASTER_SELECT_COLUMNS} FROM activity_master WHERE tenant_id=? AND project_id=? AND project_revision=? ORDER BY activity_id",
            (scope.tenant_id, scope.project_id, scope.project_revision)).fetchall()
        result = tuple(_from_row(scope, row) for row in rows)
        for item in result:
            self._validate_wbs_assignment(scope, item.wbs_id, require_assignment=False)
        return result

    def delete(self, scope: BackendScope, activity_id: str, *, expected_revision: int) -> bool:
        """Remove one activity row and its WBS link.

        Child records, relationships, assignments and document links are checked
        by the application boundary before this call; the repository only owns
        the activity row so a stale revision can never delete the wrong record.
        """
        scope.validate()
        if not isinstance(activity_id, str) or not activity_id.strip():
            raise ActivityPersistenceError("INVALID_ACTIVITY_ID")
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 1:
            raise ActivityPersistenceError("INVALID_EXPECTED_REVISION")
        row = self.connection.execute(
            "SELECT record_revision,project_revision FROM activity_master "
            "WHERE tenant_id=? AND project_id=? AND activity_id=?",
            (scope.tenant_id, scope.project_id, activity_id),
        ).fetchone()
        if row is None:
            raise ActivityPersistenceError("ACTIVITY_NOT_FOUND")
        if int(row[1]) != scope.project_revision or int(row[0]) != expected_revision:
            raise ActivityPersistenceError("REVISION_CONFLICT")
        self.connection.execute(
            "DELETE FROM activity_wbs_assignment WHERE tenant_id=? AND project_id=? AND activity_id=?",
            (scope.tenant_id, scope.project_id, activity_id),
        )
        cursor = self.connection.execute(
            "DELETE FROM activity_master WHERE tenant_id=? AND project_id=? "
            "AND project_revision=? AND activity_id=? AND record_revision=?",
            (scope.tenant_id, scope.project_id, scope.project_revision, activity_id, expected_revision),
        )
        if cursor.rowcount != 1:
            self.connection.rollback()
            raise ActivityPersistenceError("REVISION_CONFLICT")
        self.connection.commit()
        return True

    def _renumber_reference_tables(self, *, include_baselines: bool) -> tuple[str, ...]:
        names: list[str] = []
        for (name,) in self.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall():
            if not name or name == "activity_master":
                continue
            if not include_baselines and name == "p6_baseline_activity":
                continue
            columns = {
                row[1]
                for row in self.connection.execute(f'PRAGMA table_info("{name}")').fetchall()
            }
            if {"activity_id", "tenant_id", "project_id"} <= columns:
                names.append(str(name))
        return tuple(names)

    def _move_activity_row(
        self,
        scope: BackendScope,
        source_id: str,
        target_id: str,
        *,
        include_baselines: bool,
    ) -> int:
        """Copy one activity to a new identity, repoint every reference, then remove the source.

        Copying before deleting keeps foreign keys satisfied in either direction,
        so a renumber never leaves a window where a child row has no parent.
        """
        row = self.connection.execute(
            f"SELECT {_RENUMBER_COLUMNS} FROM activity_master "
            "WHERE tenant_id=? AND project_id=? AND project_revision=? AND activity_id=?",
            (scope.tenant_id, scope.project_id, scope.project_revision, source_id),
        ).fetchone()
        if row is None:
            raise ActivityPersistenceError("ACTIVITY_NOT_FOUND")
        values = list(row)
        values[_RENUMBER_ID_INDEX] = target_id
        placeholders = ",".join("?" for _ in _RENUMBER_COLUMN_NAMES)
        self.connection.execute(
            f"INSERT INTO activity_master ({_RENUMBER_COLUMNS}) VALUES ({placeholders})",
            tuple(values),
        )
        updated = 0
        for table in self._renumber_reference_tables(include_baselines=include_baselines):
            cursor = self.connection.execute(
                f'UPDATE "{table}" SET activity_id=? '
                "WHERE tenant_id=? AND project_id=? AND activity_id=?",
                (target_id, scope.tenant_id, scope.project_id, source_id),
            )
            updated += max(0, cursor.rowcount)
        has_relationships = self.connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='relationship_master'"
        ).fetchone() is not None
        if has_relationships:
            for column in ("predecessor_id", "successor_id"):
                cursor = self.connection.execute(
                    f"UPDATE relationship_master SET {column}=? "
                    "WHERE tenant_id=? AND project_id=? AND "
                    f"{column}=?",
                    (target_id, scope.tenant_id, scope.project_id, source_id),
                )
                updated += max(0, cursor.rowcount)
        # Document links live inside the stored JSON payload, not in a column.
        has_documents = self.connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='project_documents'"
        ).fetchone() is not None
        document_rows = (
            self.connection.execute(
                "SELECT document_id,document_json FROM project_documents "
                "WHERE tenant_id=? AND project_id=?",
                (scope.tenant_id, scope.project_id),
            ).fetchall()
            if has_documents
            else ()
        )
        for document_id, raw in document_rows:
            try:
                document = json.loads(raw)
            except (TypeError, ValueError):
                continue
            if _replace_document_activity_refs(document, source_id, target_id):
                self.connection.execute(
                    "UPDATE project_documents SET document_json=? "
                    "WHERE tenant_id=? AND project_id=? AND document_id=?",
                    (json.dumps(document, ensure_ascii=False, sort_keys=True), scope.tenant_id, scope.project_id, document_id),
                )
                updated += 1
        cursor = self.connection.execute(
            "DELETE FROM activity_master "
            "WHERE tenant_id=? AND project_id=? AND project_revision=? AND activity_id=?",
            (scope.tenant_id, scope.project_id, scope.project_revision, source_id),
        )
        if cursor.rowcount != 1:
            raise ActivityPersistenceError("REVISION_CONFLICT")
        return updated

    def renumber(
        self,
        scope: BackendScope,
        entries: tuple[tuple[str, str, int], ...],
        *,
        include_baselines: bool = True,
    ) -> dict[str, object]:
        """Renumber activity IDs and keep every dependent reference intact.

        P6 Professional renumbers from the largest ID down so a selected ID can
        be reused by another selected activity. CUBI stages each move through a
        unique temporary identity, which gives the same result for any mapping
        (including swaps) while every reference stays inside one transaction.
        """
        scope.validate()
        normalized = _validated_renumber_entries(entries)
        was_in_transaction = self.connection.in_transaction
        if not was_in_transaction:
            self.connection.execute("BEGIN IMMEDIATE")
        try:
            rows = {
                str(row[0]): int(row[1])
                for row in self.connection.execute(
                    "SELECT activity_id,record_revision FROM activity_master "
                    "WHERE tenant_id=? AND project_id=? AND project_revision=?",
                    (scope.tenant_id, scope.project_id, scope.project_revision),
                ).fetchall()
            }
            selected = {old_id for old_id, _new_id, _revision in normalized}
            for old_id, new_id, expected_revision in normalized:
                if old_id not in rows:
                    raise ActivityPersistenceError("ACTIVITY_NOT_FOUND")
                if rows[old_id] != expected_revision:
                    raise ActivityPersistenceError("REVISION_CONFLICT")
            _renumber_collision(set(rows), selected, {new_id for _old, new_id, _rev in normalized})
            references_updated = 0
            for old_id, new_id, _expected_revision in normalized:
                temporary = f"__CUBI_RENUMBER_{uuid4().hex.upper()}__"
                references_updated += self._move_activity_row(
                    scope, old_id, temporary, include_baselines=include_baselines
                )
                references_updated += self._move_activity_row(
                    scope, temporary, new_id, include_baselines=include_baselines
                )
            if not was_in_transaction:
                self.connection.commit()
            return {
                "mappings": [
                    {"activity_id": old_id, "new_activity_id": new_id, "record_revision": revision}
                    for old_id, new_id, revision in normalized
                ],
                "renumbered": len(normalized),
                "references_updated": references_updated,
                "baselines_renumbered": include_baselines,
            }
        except Exception:
            if not was_in_transaction and self.connection.in_transaction:
                self.connection.rollback()
            raise


class PostgresActivityMasterRepository:
    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        PostgresWBSMasterRepository(self.connection).initialize()
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS activity_master ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision BIGINT NOT NULL, "
            "activity_id TEXT NOT NULL, duration_value TEXT NOT NULL, duration_unit TEXT NOT NULL, "
            "actual_start TEXT, actual_finish TEXT, remaining_duration INTEGER, remaining_start TEXT, "
            "percent_complete DOUBLE PRECISION, percent_complete_type TEXT NOT NULL DEFAULT 'DURATION', "
            "record_revision BIGINT NOT NULL, expected_finish TEXT, planned_finish TEXT, "
            "leveling_priority TEXT NOT NULL DEFAULT 'Normal', original_duration INTEGER, "
            "name TEXT NOT NULL DEFAULT '', activity_type TEXT NOT NULL DEFAULT 'Task Dependent', "
            "status TEXT NOT NULL DEFAULT 'Not Started', status_code TEXT NOT NULL DEFAULT 'Planned', "
            "short_name TEXT, duration_type TEXT NOT NULL DEFAULT 'Fixed Duration & Units', "
            "cost_account_id TEXT, "
            "PRIMARY KEY (tenant_id, project_id, activity_id))")
        self.connection.execute("ALTER TABLE activity_master ADD COLUMN IF NOT EXISTS expected_finish TEXT")
        self.connection.execute("ALTER TABLE activity_master ADD COLUMN IF NOT EXISTS planned_finish TEXT")
        self.connection.execute(
            "ALTER TABLE activity_master ADD COLUMN IF NOT EXISTS leveling_priority TEXT NOT NULL DEFAULT 'Normal'"
        )
        self.connection.execute("ALTER TABLE activity_master ADD COLUMN IF NOT EXISTS original_duration INTEGER")
        self.connection.execute("ALTER TABLE activity_master ADD COLUMN IF NOT EXISTS name TEXT NOT NULL DEFAULT ''")
        self.connection.execute("ALTER TABLE activity_master ADD COLUMN IF NOT EXISTS activity_type TEXT NOT NULL DEFAULT 'Task Dependent'")
        self.connection.execute("ALTER TABLE activity_master ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'Not Started'")
        self.connection.execute("ALTER TABLE activity_master ADD COLUMN IF NOT EXISTS status_code TEXT NOT NULL DEFAULT 'Planned'")
        self.connection.execute("ALTER TABLE activity_master ADD COLUMN IF NOT EXISTS short_name TEXT")
        self.connection.execute(
            "ALTER TABLE activity_master ADD COLUMN IF NOT EXISTS duration_type TEXT NOT NULL DEFAULT 'Fixed Duration & Units'"
        )
        self.connection.execute("ALTER TABLE activity_master ADD COLUMN IF NOT EXISTS cost_account_id TEXT")
        self.connection.execute(
            "ALTER TABLE activity_master ALTER COLUMN leveling_priority SET DEFAULT 'Normal'"
        )
        self.connection.execute(
            "UPDATE activity_master SET leveling_priority='Normal' WHERE leveling_priority IS NULL"
        )
        self.connection.execute(
            "ALTER TABLE activity_master ALTER COLUMN leveling_priority SET NOT NULL"
        )
        self.connection.execute("ALTER TABLE activity_master ADD COLUMN IF NOT EXISTS actual_finish TEXT")
        self.connection.execute("ALTER TABLE activity_master ADD COLUMN IF NOT EXISTS remaining_duration INTEGER")
        self.connection.execute("ALTER TABLE activity_master ADD COLUMN IF NOT EXISTS remaining_start TEXT")
        self.connection.execute("ALTER TABLE activity_master ADD COLUMN IF NOT EXISTS percent_complete DOUBLE PRECISION")
        self.connection.execute("ALTER TABLE activity_master ADD COLUMN IF NOT EXISTS percent_complete_type TEXT NOT NULL DEFAULT 'DURATION'")
        self.connection.execute("CREATE INDEX IF NOT EXISTS idx_activity_master_revision ON activity_master(tenant_id, project_id, project_revision, activity_id)")
        self.connection.execute("""CREATE TABLE IF NOT EXISTS activity_wbs_assignment (
            tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, activity_id TEXT NOT NULL,
            wbs_id TEXT NOT NULL, PRIMARY KEY (tenant_id, project_id, activity_id),
            FOREIGN KEY (tenant_id, project_id, activity_id) REFERENCES activity_master(tenant_id, project_id, activity_id) ON DELETE CASCADE,
            FOREIGN KEY (tenant_id, project_id, wbs_id) REFERENCES wbs_master(tenant_id, project_id, wbs_id) ON DELETE RESTRICT
        )""")
        self.connection.execute("CREATE INDEX IF NOT EXISTS idx_activity_wbs_assignment_wbs ON activity_wbs_assignment(tenant_id, project_id, wbs_id)")

    def _validate_wbs_assignment(
        self, scope: BackendScope, wbs_id: str | None, *, require_assignment: bool = True
    ) -> None:
        if wbs_id is None:
            if not require_assignment:
                return
            exists = self.connection.execute(
                "SELECT 1 FROM wbs_master WHERE tenant_id=%s AND project_id=%s LIMIT 1",
                (scope.tenant_id, scope.project_id),
            ).fetchone()
            if exists is not None:
                raise ActivityPersistenceError("WBS_REQUIRED")
            return
        row = self.connection.execute("SELECT project_revision FROM wbs_master WHERE tenant_id=%s AND project_id=%s AND wbs_id=%s", (scope.tenant_id, scope.project_id, wbs_id)).fetchone()
        if row is None:
            raise ActivityPersistenceError("WBS_NOT_FOUND_OR_SCOPE_MISMATCH")
        if int(row[0]) != scope.project_revision:
            raise ActivityPersistenceError("REVISION_CONFLICT")

    def _sync_wbs_assignment(self, activity: ActivityMaster) -> None:
        if activity.wbs_id is None:
            self.connection.execute("DELETE FROM activity_wbs_assignment WHERE tenant_id=%s AND project_id=%s AND activity_id=%s", (activity.scope.tenant_id, activity.scope.project_id, activity.activity_id))
            return
        self.connection.execute("INSERT INTO activity_wbs_assignment (tenant_id,project_id,activity_id,wbs_id) VALUES (%s,%s,%s,%s) ON CONFLICT (tenant_id,project_id,activity_id) DO UPDATE SET wbs_id=EXCLUDED.wbs_id", (activity.scope.tenant_id, activity.scope.project_id, activity.activity_id, activity.wbs_id))

    def save(self, activity: ActivityMaster, expected_revision: int | None = None) -> ActivityMaster:
        activity.validate()
        self._validate_wbs_assignment(activity.scope, activity.wbs_id)
        row = self.connection.execute(
            f"SELECT {_ACTIVITY_MASTER_SELECT_COLUMNS},project_revision FROM activity_master WHERE tenant_id=%s AND project_id=%s AND activity_id=%s FOR UPDATE",
            (activity.scope.tenant_id, activity.scope.project_id, activity.activity_id)).fetchone()
        if row is None:
            if expected_revision not in (None, 0):
                raise ActivityPersistenceError("REVISION_CONFLICT")
            revision = 1
            self.connection.execute(
                "INSERT INTO activity_master (tenant_id,project_id,project_revision,activity_id,duration_value,duration_unit,actual_start,actual_finish,remaining_duration,remaining_start,percent_complete,percent_complete_type,record_revision,expected_finish,planned_finish,leveling_priority,original_duration,name,activity_type,status,status_code,short_name,duration_type,cost_account_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (activity.scope.tenant_id, activity.scope.project_id, activity.scope.project_revision, activity.activity_id,
                 str(activity.duration_value), activity.duration_unit.value,
                 None if activity.actual_start is None else activity.actual_start.isoformat(),
                 None if activity.actual_finish is None else activity.actual_finish.isoformat(),
                 activity.remaining_duration,
                 None if activity.remaining_start is None else activity.remaining_start.isoformat(),
                 activity.percent_complete,
                 activity.percent_complete_type.value,
                 revision,
                 None if activity.expected_finish is None else activity.expected_finish.isoformat(),
                 None if activity.planned_finish is None else activity.planned_finish.isoformat(),
                 activity.leveling_priority.value,
                 activity.original_duration,
                 activity.name, activity.activity_type.value, activity.status.value, activity.status_code.value,
                 activity.short_name, activity.duration_type.value, activity.cost_account_id))
            stored = replace(activity, record_revision=revision)
            self._sync_wbs_assignment(stored)
            return stored
        current = _from_row(activity.scope, row[:22])
        if int(row[22]) != activity.scope.project_revision:
            raise ActivityPersistenceError("REVISION_CONFLICT")
        if expected_revision is None or expected_revision != current.record_revision:
            raise ActivityPersistenceError("REVISION_CONFLICT")
        revision = current.record_revision + 1
        stored = replace(activity, record_revision=revision)
        self.connection.execute(
            "UPDATE activity_master SET project_revision=%s,duration_value=%s,duration_unit=%s,actual_start=%s,actual_finish=%s,remaining_duration=%s,remaining_start=%s,percent_complete=%s,percent_complete_type=%s,record_revision=%s,expected_finish=%s,planned_finish=%s,leveling_priority=%s,original_duration=%s,name=%s,activity_type=%s,status=%s,status_code=%s,short_name=%s,duration_type=%s,cost_account_id=%s WHERE tenant_id=%s AND project_id=%s AND activity_id=%s AND record_revision=%s",
            (activity.scope.project_revision, str(activity.duration_value), activity.duration_unit.value,
             None if activity.actual_start is None else activity.actual_start.isoformat(),
             None if activity.actual_finish is None else activity.actual_finish.isoformat(),
             activity.remaining_duration,
             None if activity.remaining_start is None else activity.remaining_start.isoformat(),
             activity.percent_complete,
             activity.percent_complete_type.value,
             revision,
             None if activity.expected_finish is None else activity.expected_finish.isoformat(),
             None if activity.planned_finish is None else activity.planned_finish.isoformat(),
             activity.leveling_priority.value,
             activity.original_duration,
             activity.name, activity.activity_type.value, activity.status.value, activity.status_code.value,
             activity.short_name, activity.duration_type.value, activity.cost_account_id,
             activity.scope.tenant_id, activity.scope.project_id, activity.activity_id, current.record_revision))
        self._sync_wbs_assignment(stored)
        return stored

    def get(self, scope: BackendScope, activity_id: str) -> ActivityMaster | None:
        scope.validate()
        row = self.connection.execute(
            f"SELECT {_ACTIVITY_MASTER_SELECT_COLUMNS},project_revision FROM activity_master WHERE tenant_id=%s AND project_id=%s AND activity_id=%s",
            (scope.tenant_id, scope.project_id, activity_id)).fetchone()
        if row is None:
            return None
        if int(row[22]) != scope.project_revision:
            raise ActivityPersistenceError("REVISION_CONFLICT")
        result = _from_row(scope, row[:22])
        self._validate_wbs_assignment(scope, result.wbs_id, require_assignment=False)
        return result

    def list(self, scope: BackendScope) -> tuple[ActivityMaster, ...]:
        scope.validate()
        rows = self.connection.execute(
            f"SELECT {_ACTIVITY_MASTER_SELECT_COLUMNS} FROM activity_master WHERE tenant_id=%s AND project_id=%s AND project_revision=%s ORDER BY activity_id",
            (scope.tenant_id, scope.project_id, scope.project_revision)).fetchall()
        result = tuple(_from_row(scope, row) for row in rows)
        for item in result:
            self._validate_wbs_assignment(scope, item.wbs_id, require_assignment=False)
        return result

    def delete(self, scope: BackendScope, activity_id: str, *, expected_revision: int) -> bool:
        scope.validate()
        if not isinstance(activity_id, str) or not activity_id.strip():
            raise ActivityPersistenceError("INVALID_ACTIVITY_ID")
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 1:
            raise ActivityPersistenceError("INVALID_EXPECTED_REVISION")
        row = self.connection.execute(
            "SELECT record_revision,project_revision FROM activity_master "
            "WHERE tenant_id=%s AND project_id=%s AND activity_id=%s",
            (scope.tenant_id, scope.project_id, activity_id),
        ).fetchone()
        if row is None:
            raise ActivityPersistenceError("ACTIVITY_NOT_FOUND")
        if int(row[1]) != scope.project_revision or int(row[0]) != expected_revision:
            raise ActivityPersistenceError("REVISION_CONFLICT")
        self.connection.execute(
            "DELETE FROM activity_wbs_assignment WHERE tenant_id=%s AND project_id=%s AND activity_id=%s",
            (scope.tenant_id, scope.project_id, activity_id),
        )
        cursor = self.connection.execute(
            "DELETE FROM activity_master WHERE tenant_id=%s AND project_id=%s "
            "AND project_revision=%s AND activity_id=%s AND record_revision=%s",
            (scope.tenant_id, scope.project_id, scope.project_revision, activity_id, expected_revision),
        )
        if getattr(cursor, "rowcount", 1) != 1:
            self.connection.rollback()
            raise ActivityPersistenceError("REVISION_CONFLICT")
        return True

    def _renumber_reference_tables(self, *, include_baselines: bool) -> tuple[str, ...]:
        candidates = [
            str(row[0])
            for row in self.connection.execute(
                "SELECT table_name FROM information_schema.columns "
                "WHERE table_schema=current_schema() AND column_name='activity_id' "
                "AND table_name<>'activity_master'"
            ).fetchall()
        ]
        names: list[str] = []
        for name in candidates:
            if not include_baselines and name == "p6_baseline_activity":
                continue
            columns = {
                str(row[0])
                for row in self.connection.execute(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema=current_schema() AND table_name=%s "
                    "AND column_name IN ('tenant_id','project_id')",
                    (name,),
                ).fetchall()
            }
            if {"tenant_id", "project_id"} <= columns:
                names.append(name)
        return tuple(names)

    def _move_activity_row(
        self,
        scope: BackendScope,
        source_id: str,
        target_id: str,
        *,
        include_baselines: bool,
    ) -> int:
        row = self.connection.execute(
            f"SELECT {_RENUMBER_COLUMNS} FROM activity_master "
            "WHERE tenant_id=%s AND project_id=%s AND project_revision=%s AND activity_id=%s",
            (scope.tenant_id, scope.project_id, scope.project_revision, source_id),
        ).fetchone()
        if row is None:
            raise ActivityPersistenceError("ACTIVITY_NOT_FOUND")
        values = list(row)
        values[_RENUMBER_ID_INDEX] = target_id
        placeholders = ",".join("%s" for _ in _RENUMBER_COLUMN_NAMES)
        self.connection.execute(
            f"INSERT INTO activity_master ({_RENUMBER_COLUMNS}) VALUES ({placeholders})",
            tuple(values),
        )
        updated = 0
        for table in self._renumber_reference_tables(include_baselines=include_baselines):
            cursor = self.connection.execute(
                f'UPDATE "{table}" SET activity_id=%s '
                "WHERE tenant_id=%s AND project_id=%s AND activity_id=%s",
                (target_id, scope.tenant_id, scope.project_id, source_id),
            )
            updated += max(0, getattr(cursor, "rowcount", 0) or 0)
        for column in ("predecessor_id", "successor_id"):
            cursor = self.connection.execute(
                f"UPDATE relationship_master SET {column}=%s "
                "WHERE tenant_id=%s AND project_id=%s AND "
                f"{column}=%s",
                (target_id, scope.tenant_id, scope.project_id, source_id),
            )
            updated += max(0, getattr(cursor, "rowcount", 0) or 0)
        try:
            document_rows = self.connection.execute(
                "SELECT document_id,document_json FROM project_documents "
                "WHERE tenant_id=%s AND project_id=%s",
                (scope.tenant_id, scope.project_id),
            ).fetchall()
        except Exception:
            document_rows = ()
        for document_id, raw in document_rows:
            try:
                document = json.loads(raw)
            except (TypeError, ValueError):
                continue
            if _replace_document_activity_refs(document, source_id, target_id):
                self.connection.execute(
                    "UPDATE project_documents SET document_json=%s "
                    "WHERE tenant_id=%s AND project_id=%s AND document_id=%s",
                    (json.dumps(document, ensure_ascii=False, sort_keys=True), scope.tenant_id, scope.project_id, document_id),
                )
                updated += 1
        cursor = self.connection.execute(
            "DELETE FROM activity_master "
            "WHERE tenant_id=%s AND project_id=%s AND project_revision=%s AND activity_id=%s",
            (scope.tenant_id, scope.project_id, scope.project_revision, source_id),
        )
        if getattr(cursor, "rowcount", 1) != 1:
            raise ActivityPersistenceError("REVISION_CONFLICT")
        return updated

    def renumber(
        self,
        scope: BackendScope,
        entries: tuple[tuple[str, str, int], ...],
        *,
        include_baselines: bool = True,
    ) -> dict[str, object]:
        scope.validate()
        normalized = _validated_renumber_entries(entries)
        rows = {
            str(row[0]): int(row[1])
            for row in self.connection.execute(
                "SELECT activity_id,record_revision FROM activity_master "
                "WHERE tenant_id=%s AND project_id=%s AND project_revision=%s",
                (scope.tenant_id, scope.project_id, scope.project_revision),
            ).fetchall()
        }
        selected = {old_id for old_id, _new_id, _revision in normalized}
        for old_id, _new_id, expected_revision in normalized:
            if old_id not in rows:
                raise ActivityPersistenceError("ACTIVITY_NOT_FOUND")
            if rows[old_id] != expected_revision:
                raise ActivityPersistenceError("REVISION_CONFLICT")
        _renumber_collision(set(rows), selected, {new_id for _old, new_id, _rev in normalized})
        references_updated = 0
        for old_id, new_id, _expected_revision in normalized:
            temporary = f"__CUBI_RENUMBER_{uuid4().hex.upper()}__"
            references_updated += self._move_activity_row(
                scope, old_id, temporary, include_baselines=include_baselines
            )
            references_updated += self._move_activity_row(
                scope, temporary, new_id, include_baselines=include_baselines
            )
        return {
            "mappings": [
                {"activity_id": old_id, "new_activity_id": new_id, "record_revision": revision}
                for old_id, new_id, revision in normalized
            ],
            "renumbered": len(normalized),
            "references_updated": references_updated,
            "baselines_renumbered": include_baselines,
        }
