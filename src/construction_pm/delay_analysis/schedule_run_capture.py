from __future__ import annotations

"""Immutable, reproducible capture of authoritative Shared Core schedule runs.

This module records the output of evaluate_schedule_snapshot; it never runs a
second scheduler and never mutates a project, baseline, or source snapshot.
"""

import hashlib
import json
import sqlite3
from dataclasses import asdict, dataclass, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Mapping, Protocol

from ..backend_p0.models import BackendScope
from ..schedule_evaluator import ScheduleEvaluationResult
from ..schedule_input_snapshot_repository import ScheduleInputSnapshot
from ..scheduling.calculation_context import CalculationContext


class ScheduleRunCaptureError(ValueError):
    """Raised when an authoritative run cannot be captured or verified."""


def _canonical_value(value: object) -> object:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Enum):
        return _canonical_value(value.value)
    if isinstance(value, Mapping):
        return {
            str(key): _canonical_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [_canonical_value(item) for item in value]
    if is_dataclass(value):
        return {
            field: _canonical_value(item)
            for field, item in asdict(value).items()
        }
    raise ScheduleRunCaptureError("UNSUPPORTED_SCHEDULE_RUN_VALUE")


def _canonical_json(value: object) -> str:
    return json.dumps(
        _canonical_value(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _required_payload_section(payload: object, key: str) -> object:
    if not isinstance(payload, dict) or key not in payload:
        raise ScheduleRunCaptureError(f"SCHEDULE_SNAPSHOT_MISSING_{key.upper()}")
    return payload[key]


@dataclass(frozen=True)
class ScheduleRunCapture:
    """A content-addressed, immutable execution record.

    The log envelope contains the settings, scheduler diagnostics, Schedule
    Check findings, and output statistics available from the current evaluator.
    It is explicitly not represented as a complete native P6 Schedule Project
    Log because native errors/warnings/exceptions and all P6 statistics are not
    yet produced by the current Shared Core evaluator.
    """

    scope: BackendScope
    run_id: str
    snapshot_id: str
    snapshot_hash: str
    calculation_identity: str
    calculation_run_identity: str
    engine_version: str
    schedule_mode: str
    project_finish: str
    schedule_settings_json: str
    schedule_settings_hash: str
    calendar_context_json: str
    calendar_context_hash: str
    result_json: str
    result_hash: str
    diagnostics_json: str
    diagnostics_hash: str
    check_findings_json: str
    check_findings_hash: str
    log_envelope_json: str
    log_envelope_hash: str
    captured_at: str

    def validate(self) -> None:
        self.scope.validate()
        for name in (
            "run_id", "snapshot_id", "engine_version", "schedule_mode",
            "project_finish", "captured_at",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ScheduleRunCaptureError(f"INVALID_{name.upper()}")
        try:
            captured = datetime.fromisoformat(self.captured_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ScheduleRunCaptureError("INVALID_CAPTURE_TIMESTAMP") from exc
        if captured.tzinfo is None or captured.utcoffset() is None:
            raise ScheduleRunCaptureError("INVALID_CAPTURE_TIMESTAMP")
        for name in (
            "snapshot_hash", "calculation_identity", "calculation_run_identity",
            "schedule_settings_hash", "calendar_context_hash", "result_hash",
            "diagnostics_hash", "check_findings_hash", "log_envelope_hash",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, str) or len(value) != 64
                or any(char not in "0123456789abcdef" for char in value)
            ):
                raise ScheduleRunCaptureError(f"INVALID_{name.upper()}")
        for payload_name, hash_name in (
            ("schedule_settings_json", "schedule_settings_hash"),
            ("calendar_context_json", "calendar_context_hash"),
            ("result_json", "result_hash"),
            ("diagnostics_json", "diagnostics_hash"),
            ("check_findings_json", "check_findings_hash"),
            ("log_envelope_json", "log_envelope_hash"),
        ):
            raw = getattr(self, payload_name)
            try:
                parsed = json.loads(raw)
            except (TypeError, json.JSONDecodeError) as exc:
                raise ScheduleRunCaptureError(f"INVALID_{payload_name.upper()}") from exc
            if _canonical_json(parsed) != raw or _sha256(raw) != getattr(self, hash_name):
                raise ScheduleRunCaptureError(f"{payload_name.upper()}_HASH_MISMATCH")
        if self.run_id != _sha256(
            f"{self.snapshot_hash}:{self.calculation_identity}:{self.calculation_run_identity}"
        ):
            raise ScheduleRunCaptureError("SCHEDULE_RUN_IDENTITY_MISMATCH")


def build_schedule_run_capture(
    snapshot: ScheduleInputSnapshot,
    calculation_context: CalculationContext,
    evaluation: ScheduleEvaluationResult,
    *,
    captured_at: datetime,
) -> ScheduleRunCapture:
    """Bind an evaluator result to the exact immutable snapshot and context."""
    snapshot.validate()
    if not isinstance(captured_at, datetime) or captured_at.tzinfo is None or captured_at.utcoffset() is None:
        raise ScheduleRunCaptureError("INVALID_CAPTURE_TIMESTAMP")
    if (
        calculation_context.input_snapshot_id != snapshot.snapshot_id
        or calculation_context.project_id != snapshot.scope.project_id
        or calculation_context.project_version != snapshot.scope.project_revision
        or calculation_context.tenant_id not in (None, snapshot.scope.tenant_id)
        or (
            calculation_context.calculation_identity != snapshot.calculation_identity
            if snapshot.calculation_identity_version == 2
            else calculation_context.legacy_calculation_identity != snapshot.calculation_identity
        )
    ):
        raise ScheduleRunCaptureError("CALCULATION_CONTEXT_SNAPSHOT_MISMATCH")
    if (
        evaluation.snapshot_id != snapshot.snapshot_id
        or evaluation.snapshot_hash != snapshot.snapshot_hash
        or evaluation.calculation_identity != calculation_context.calculation_identity
        or evaluation.project_id != snapshot.scope.project_id
        or evaluation.project_revision != snapshot.scope.project_revision
    ):
        raise ScheduleRunCaptureError("EVALUATION_SNAPSHOT_MISMATCH")
    if not evaluation.calculation_run_identity or not evaluation.mode:
        raise ScheduleRunCaptureError("INCOMPLETE_SCHEDULE_EVALUATION")

    try:
        snapshot_payload = json.loads(snapshot.canonical_payload)
    except json.JSONDecodeError as exc:
        raise ScheduleRunCaptureError("INVALID_SCHEDULE_SNAPSHOT_PAYLOAD") from exc

    settings = _required_payload_section(snapshot_payload, "schedule_options")
    calendar_context = {
        key: _required_payload_section(snapshot_payload, key)
        for key in (
            "project_calendar",
            "activity_calendar_assignments",
            "relationship_lag_calendar_assignments",
        )
    }
    settings_json = _canonical_json(settings)
    calendar_json = _canonical_json(calendar_context)
    result_json = _canonical_json({
        "date_result": evaluation.date_result,
        "time_result": evaluation.time_result,
        "time_activities": evaluation.time_activities,
        "resource_dependent_placement": evaluation.resource_dependent_placement,
        "project_finish": evaluation.project_finish,
    })
    diagnostics_json = _canonical_json(evaluation.diagnostics)
    findings_json = _canonical_json(evaluation.schedule_check_findings)
    log_envelope_json = _canonical_json({
        "record_type": "CUBI_SHARED_CORE_SCHEDULE_RUN_LOG_ENVELOPE_V1",
        "settings": json.loads(settings_json),
        "diagnostics": json.loads(diagnostics_json),
        "check_schedule_findings": json.loads(findings_json),
        "statistics": {
            "activity_count": (
                len(evaluation.date_result.floats)
                if evaluation.date_result is not None
                else len(evaluation.time_activities or {})
            ),
            "project_finish": evaluation.project_finish,
            "mode": evaluation.mode,
        },
        "native_p6_log_parity": "PARTIAL",
        "unavailable_native_sections": [
            "native_scheduler_errors",
            "native_scheduler_warnings",
            "native_scheduler_exceptions",
            "complete_native_scheduler_statistics",
        ],
    })
    run_id = _sha256(
        f"{snapshot.snapshot_hash}:{calculation_context.calculation_identity}:"
        f"{evaluation.calculation_run_identity}"
    )
    record = ScheduleRunCapture(
        scope=snapshot.scope,
        run_id=run_id,
        snapshot_id=snapshot.snapshot_id,
        snapshot_hash=snapshot.snapshot_hash,
        calculation_identity=calculation_context.calculation_identity,
        calculation_run_identity=evaluation.calculation_run_identity,
        engine_version=calculation_context.engine_version,
        schedule_mode=evaluation.mode,
        project_finish=evaluation.project_finish.isoformat(),
        schedule_settings_json=settings_json,
        schedule_settings_hash=_sha256(settings_json),
        calendar_context_json=calendar_json,
        calendar_context_hash=_sha256(calendar_json),
        result_json=result_json,
        result_hash=_sha256(result_json),
        diagnostics_json=diagnostics_json,
        diagnostics_hash=_sha256(diagnostics_json),
        check_findings_json=findings_json,
        check_findings_hash=_sha256(findings_json),
        log_envelope_json=log_envelope_json,
        log_envelope_hash=_sha256(log_envelope_json),
        captured_at=captured_at.isoformat(),
    )
    record.validate()
    return record


class ScheduleRunCaptureRepository(Protocol):
    def save(self, record: ScheduleRunCapture) -> ScheduleRunCapture: ...
    def get(self, scope: BackendScope, run_id: str) -> ScheduleRunCapture | None: ...


class SQLiteScheduleRunCaptureRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS engineering_schedule_run_capture (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                project_revision INTEGER NOT NULL,
                run_id TEXT NOT NULL,
                record_json TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, run_id)
            )"""
        )
        self.connection.commit()

    def save(self, record: ScheduleRunCapture) -> ScheduleRunCapture:
        record.validate()
        payload = _canonical_json({
            key: value for key, value in record.__dict__.items() if key != "scope"
        })
        key = (record.scope.tenant_id, record.scope.project_id, record.run_id)
        self.connection.execute(
            "INSERT OR IGNORE INTO engineering_schedule_run_capture "
            "(tenant_id,project_id,project_revision,run_id,record_json) VALUES (?,?,?,?,?)",
            (*key[:2], record.scope.project_revision, key[2], payload),
        )
        row = self.connection.execute(
            "SELECT project_revision,record_json FROM engineering_schedule_run_capture "
            "WHERE tenant_id=? AND project_id=? AND run_id=?",
            key,
        ).fetchone()
        if row is None:
            raise ScheduleRunCaptureError("SCHEDULE_RUN_CAPTURE_SAVE_FAILED")
        if int(row[0]) != record.scope.project_revision or row[1] != payload:
            raise ScheduleRunCaptureError("IMMUTABLE_SCHEDULE_RUN_CAPTURE_CONFLICT")
        return record

    def get(self, scope: BackendScope, run_id: str) -> ScheduleRunCapture | None:
        scope.validate()
        if not isinstance(run_id, str) or not run_id.strip():
            raise ScheduleRunCaptureError("INVALID_RUN_ID")
        row = self.connection.execute(
            "SELECT project_revision,record_json FROM engineering_schedule_run_capture "
            "WHERE tenant_id=? AND project_id=? AND run_id=?",
            (scope.tenant_id, scope.project_id, run_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[0]) != scope.project_revision:
            raise ScheduleRunCaptureError("REVISION_CONFLICT")
        try:
            values = json.loads(row[1])
            record = ScheduleRunCapture(scope=scope, **values)
        except (TypeError, KeyError, json.JSONDecodeError) as exc:
            raise ScheduleRunCaptureError("INVALID_STORED_SCHEDULE_RUN_CAPTURE") from exc
        record.validate()
        return record


class PostgresScheduleRunCaptureRepository:
    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS engineering_schedule_run_capture ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, "
            "project_revision BIGINT NOT NULL, run_id TEXT NOT NULL, "
            "record_json TEXT NOT NULL, "
            "PRIMARY KEY (tenant_id,project_id,run_id))"
        )

    def save(self, record: ScheduleRunCapture) -> ScheduleRunCapture:
        record.validate()
        payload = _canonical_json({
            key: value for key, value in record.__dict__.items() if key != "scope"
        })
        key = (record.scope.tenant_id, record.scope.project_id, record.run_id)
        self.connection.execute(
            "INSERT INTO engineering_schedule_run_capture "
            "(tenant_id,project_id,project_revision,run_id,record_json) "
            "VALUES (%s,%s,%s,%s,%s) ON CONFLICT "
            "(tenant_id,project_id,run_id) DO NOTHING",
            (*key[:2], record.scope.project_revision, key[2], payload),
        )
        row = self.connection.execute(
            "SELECT project_revision,record_json FROM engineering_schedule_run_capture "
            "WHERE tenant_id=%s AND project_id=%s AND run_id=%s",
            key,
        ).fetchone()
        if row is None:
            raise ScheduleRunCaptureError("SCHEDULE_RUN_CAPTURE_SAVE_FAILED")
        if int(row[0]) != record.scope.project_revision or row[1] != payload:
            raise ScheduleRunCaptureError("IMMUTABLE_SCHEDULE_RUN_CAPTURE_CONFLICT")
        return record

    def get(self, scope: BackendScope, run_id: str) -> ScheduleRunCapture | None:
        scope.validate()
        if not isinstance(run_id, str) or not run_id.strip():
            raise ScheduleRunCaptureError("INVALID_RUN_ID")
        row = self.connection.execute(
            "SELECT project_revision,record_json FROM engineering_schedule_run_capture "
            "WHERE tenant_id=%s AND project_id=%s AND run_id=%s",
            (scope.tenant_id, scope.project_id, run_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[0]) != scope.project_revision:
            raise ScheduleRunCaptureError("REVISION_CONFLICT")
        try:
            values = json.loads(row[1])
            record = ScheduleRunCapture(scope=scope, **values)
        except (TypeError, KeyError, json.JSONDecodeError) as exc:
            raise ScheduleRunCaptureError("INVALID_STORED_SCHEDULE_RUN_CAPTURE") from exc
        record.validate()
        return record
