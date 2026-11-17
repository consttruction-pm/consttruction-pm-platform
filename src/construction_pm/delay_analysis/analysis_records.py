from __future__ import annotations

"""Append-only governance records for Engineering delay-analysis revisions.

This module stores analysis provenance and independent review decisions only.
It does not calculate schedules, grant contractual entitlement, or publish to
Enterprise/ENT-13. Callers must supply trusted server-side snapshot references.
"""

import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

from ..backend_p0.models import BackendScope


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class DelayAnalysisRecordError(ValueError):
    """Raised when an analysis record violates provenance or governance rules."""


def _text(value: str, code: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise DelayAnalysisRecordError(code)


def _hash(value: str, code: str) -> None:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise DelayAnalysisRecordError(code)


def _aware(value: datetime, code: str) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise DelayAnalysisRecordError(code)


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@dataclass(frozen=True)
class DelayAnalysisCase:
    scope: BackendScope
    case_id: str
    idempotency_key: str
    request_hash: str
    created_by: str
    created_at: datetime

    def validate(self) -> None:
        self.scope.validate()
        for value, code in (
            (self.case_id, "CASE_ID_REQUIRED"),
            (self.idempotency_key, "IDEMPOTENCY_KEY_REQUIRED"),
            (self.created_by, "CREATED_BY_REQUIRED"),
        ):
            _text(value, code)
        _hash(self.request_hash, "INVALID_REQUEST_HASH")
        _aware(self.created_at, "INVALID_CREATED_AT")


@dataclass(frozen=True)
class DelayAnalysisRevision:
    scope: BackendScope
    case_id: str
    revision: int
    revision_key: str
    method: str
    baseline_snapshot_id: str
    baseline_snapshot_hash: str
    baseline_data_date: date
    current_snapshot_id: str
    current_snapshot_hash: str
    current_data_date: date
    data_date_basis: str
    data_date_rationale: str
    statused_update_evidence_hash: str
    event_evidence_manifest_hash: str
    result_hash: str
    created_by: str
    created_at: datetime

    def validate(self) -> None:
        self.scope.validate()
        for value, code in (
            (self.case_id, "CASE_ID_REQUIRED"),
            (self.revision_key, "REVISION_KEY_REQUIRED"),
            (self.method, "METHOD_REQUIRED"),
            (self.baseline_snapshot_id, "BASELINE_SNAPSHOT_ID_REQUIRED"),
            (self.current_snapshot_id, "CURRENT_SNAPSHOT_ID_REQUIRED"),
            (self.created_by, "CREATED_BY_REQUIRED"),
        ):
            _text(value, code)
        if isinstance(self.revision, bool) or not isinstance(self.revision, int) or self.revision < 1:
            raise DelayAnalysisRecordError("INVALID_ANALYSIS_REVISION")
        for value, code in (
            (self.baseline_snapshot_hash, "INVALID_BASELINE_SNAPSHOT_HASH"),
            (self.current_snapshot_hash, "INVALID_CURRENT_SNAPSHOT_HASH"),
            (self.statused_update_evidence_hash, "INVALID_STATUS_UPDATE_EVIDENCE_HASH"),
            (self.event_evidence_manifest_hash, "INVALID_EVENT_EVIDENCE_HASH"),
            (self.result_hash, "INVALID_ANALYSIS_RESULT_HASH"),
        ):
            _hash(value, code)
        if not isinstance(self.baseline_data_date, date) or isinstance(self.baseline_data_date, datetime):
            raise DelayAnalysisRecordError("INVALID_BASELINE_DATA_DATE")
        if not isinstance(self.current_data_date, date) or isinstance(self.current_data_date, datetime):
            raise DelayAnalysisRecordError("INVALID_CURRENT_DATA_DATE")
        if self.current_data_date < self.baseline_data_date:
            raise DelayAnalysisRecordError("CURRENT_DATA_DATE_PRECEDES_BASELINE")
        if self.baseline_snapshot_hash == self.current_snapshot_hash:
            raise DelayAnalysisRecordError("BASELINE_AND_CURRENT_SNAPSHOT_IDENTICAL")
        if self.data_date_basis not in {"APPROVED_CONTEMPORANEOUS_UPDATE", "RECONSTRUCTED"}:
            raise DelayAnalysisRecordError("INVALID_DATA_DATE_BASIS")
        if self.data_date_basis == "RECONSTRUCTED" and not self.data_date_rationale.strip():
            raise DelayAnalysisRecordError("RECONSTRUCTED_DATA_DATE_REQUIRES_RATIONALE")
        _aware(self.created_at, "INVALID_CREATED_AT")
        if self.current_data_date > self.created_at.date():
            raise DelayAnalysisRecordError("DATA_DATE_IN_FUTURE")


@dataclass(frozen=True)
class DelayAnalysisReview:
    scope: BackendScope
    case_id: str
    revision: int
    reviewer_id: str
    decision: str
    rationale: str
    reviewed_at: datetime

    def validate(self, author_id: str) -> None:
        self.scope.validate()
        _text(self.case_id, "CASE_ID_REQUIRED")
        _text(self.reviewer_id, "REVIEWER_REQUIRED")
        _text(self.rationale, "REVIEW_RATIONALE_REQUIRED")
        if self.reviewer_id == author_id:
            raise DelayAnalysisRecordError("SELF_REVIEW_NOT_ALLOWED")
        if self.decision not in {"APPROVE", "REJECT"}:
            raise DelayAnalysisRecordError("INVALID_REVIEW_DECISION")
        if isinstance(self.revision, bool) or not isinstance(self.revision, int) or self.revision < 1:
            raise DelayAnalysisRecordError("INVALID_ANALYSIS_REVISION")
        _aware(self.reviewed_at, "INVALID_REVIEW_TIMESTAMP")


class DelayAnalysisRecordRepository(Protocol):
    def create_case(self, case: DelayAnalysisCase) -> DelayAnalysisCase: ...
    def append_revision(self, revision: DelayAnalysisRevision) -> DelayAnalysisRevision: ...
    def record_review(self, review: DelayAnalysisReview) -> DelayAnalysisReview: ...
    def get_case(self, scope: BackendScope, case_id: str) -> DelayAnalysisCase | None: ...
    def list_revisions(self, scope: BackendScope, case_id: str) -> tuple[DelayAnalysisRevision, ...]: ...
    def is_review_approved(self, scope: BackendScope, case_id: str, revision: int) -> bool: ...


class _SQLDelayAnalysisRecordRepository:
    def __init__(self, connection: object, *, postgres: bool) -> None:
        self.connection = connection
        self.postgres = postgres

    def _q(self, sql: str) -> str:
        return sql.replace("?", "%s") if self.postgres else sql

    def initialize(self) -> None:
        self.connection.execute(self._q("""
            CREATE TABLE IF NOT EXISTS eng_delay_analysis_case (
                tenant_id TEXT NOT NULL, project_id TEXT NOT NULL,
                project_revision BIGINT NOT NULL, case_id TEXT NOT NULL,
                idempotency_key TEXT NOT NULL, request_hash TEXT NOT NULL,
                created_by TEXT NOT NULL, created_at TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, case_id),
                UNIQUE (tenant_id, project_id, idempotency_key)
            )
        """))
        self.connection.execute(self._q("""
            CREATE TABLE IF NOT EXISTS eng_delay_analysis_revision (
                tenant_id TEXT NOT NULL, project_id TEXT NOT NULL,
                case_id TEXT NOT NULL, revision BIGINT NOT NULL,
                revision_key TEXT NOT NULL, payload_json TEXT NOT NULL,
                author_id TEXT NOT NULL, created_at TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, case_id, revision),
                UNIQUE (tenant_id, project_id, case_id, revision_key)
            )
        """))
        self.connection.execute(self._q("""
            CREATE TABLE IF NOT EXISTS eng_delay_analysis_review (
                tenant_id TEXT NOT NULL, project_id TEXT NOT NULL,
                case_id TEXT NOT NULL, revision BIGINT NOT NULL,
                reviewer_id TEXT NOT NULL, decision TEXT NOT NULL,
                rationale TEXT NOT NULL, reviewed_at TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, case_id, revision, reviewer_id)
            )
        """))
        if not self.postgres:
            self.connection.execute("""
                CREATE TRIGGER IF NOT EXISTS eng_delay_revision_no_update
                BEFORE UPDATE ON eng_delay_analysis_revision
                BEGIN SELECT RAISE(ABORT, 'APPEND_ONLY_ANALYSIS_REVISION'); END
            """)
            self.connection.execute("""
                CREATE TRIGGER IF NOT EXISTS eng_delay_revision_no_delete
                BEFORE DELETE ON eng_delay_analysis_revision
                BEGIN SELECT RAISE(ABORT, 'APPEND_ONLY_ANALYSIS_REVISION'); END
            """)
            self.connection.execute("""
                CREATE TRIGGER IF NOT EXISTS eng_delay_review_no_update
                BEFORE UPDATE ON eng_delay_analysis_review
                BEGIN SELECT RAISE(ABORT, 'APPEND_ONLY_ANALYSIS_REVIEW'); END
            """)
            self.connection.execute("""
                CREATE TRIGGER IF NOT EXISTS eng_delay_review_no_delete
                BEFORE DELETE ON eng_delay_analysis_review
                BEGIN SELECT RAISE(ABORT, 'APPEND_ONLY_ANALYSIS_REVIEW'); END
            """)
        if not self.postgres:
            self.connection.commit()

    def create_case(self, case: DelayAnalysisCase) -> DelayAnalysisCase:
        case.validate()
        was_in_transaction = self.connection.in_transaction
        params = (case.scope.tenant_id, case.scope.project_id, case.scope.project_revision,
                  case.case_id, case.idempotency_key, case.request_hash,
                  case.created_by, case.created_at.isoformat())
        self.connection.execute(self._q("""
            INSERT INTO eng_delay_analysis_case
            (tenant_id,project_id,project_revision,case_id,idempotency_key,request_hash,created_by,created_at)
            VALUES (?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING
        """), params)
        row = self.connection.execute(self._q("""
            SELECT project_revision,case_id,idempotency_key,request_hash,created_by,created_at
            FROM eng_delay_analysis_case WHERE tenant_id=? AND project_id=?
            AND (case_id=? OR idempotency_key=?)
        """), (case.scope.tenant_id, case.scope.project_id, case.case_id, case.idempotency_key)).fetchone()
        if row is None or tuple(row) != (case.scope.project_revision, case.case_id, case.idempotency_key,
                                        case.request_hash, case.created_by, case.created_at.isoformat()):
            raise DelayAnalysisRecordError("CASE_IDEMPOTENCY_CONFLICT")
        if not self.postgres and not was_in_transaction:
            self.connection.commit()
        return case

    def append_revision(self, revision: DelayAnalysisRevision) -> DelayAnalysisRevision:
        revision.validate()
        case = self.get_case(revision.scope, revision.case_id)
        if case is None:
            raise DelayAnalysisRecordError("ANALYSIS_CASE_NOT_FOUND")
        was_in_transaction = self.connection.in_transaction
        existing_revision = self.connection.execute(self._q("""
            SELECT payload_json FROM eng_delay_analysis_revision
            WHERE tenant_id=? AND project_id=? AND case_id=? AND revision_key=?
        """), (revision.scope.tenant_id, revision.scope.project_id, revision.case_id, revision.revision_key)).fetchone()
        payload = _revision_payload(revision)
        if existing_revision is not None:
            if existing_revision[0] != payload:
                raise DelayAnalysisRecordError("ANALYSIS_REVISION_IDEMPOTENCY_CONFLICT")
            return revision
        rows = self.connection.execute(self._q("""
            SELECT revision FROM eng_delay_analysis_revision
            WHERE tenant_id=? AND project_id=? AND case_id=? ORDER BY revision
        """), (revision.scope.tenant_id, revision.scope.project_id, revision.case_id)).fetchall()
        expected = (int(rows[-1][0]) + 1) if rows else 1
        if revision.revision != expected:
            raise DelayAnalysisRecordError("ANALYSIS_REVISION_SEQUENCE_CONFLICT")
        inserted = self.connection.execute(self._q("""
            INSERT INTO eng_delay_analysis_revision
            (tenant_id,project_id,case_id,revision,revision_key,payload_json,author_id,created_at)
            VALUES (?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING
        """), (revision.scope.tenant_id, revision.scope.project_id, revision.case_id,
              revision.revision, revision.revision_key, payload, revision.created_by,
              revision.created_at.isoformat()))
        if getattr(inserted, "rowcount", 1) == 0:
            row = self.connection.execute(self._q("""
                SELECT payload_json FROM eng_delay_analysis_revision
                WHERE tenant_id=? AND project_id=? AND case_id=? AND revision_key=?
            """), (revision.scope.tenant_id, revision.scope.project_id, revision.case_id,
                  revision.revision_key)).fetchone()
            if row is None or row[0] != payload:
                raise DelayAnalysisRecordError("ANALYSIS_REVISION_IDEMPOTENCY_CONFLICT")
        if not self.postgres and not was_in_transaction:
            self.connection.commit()
        return revision

    def record_review(self, review: DelayAnalysisReview) -> DelayAnalysisReview:
        was_in_transaction = self.connection.in_transaction
        revisions = self.list_revisions(review.scope, review.case_id)
        revision = next((item for item in revisions if item.revision == review.revision), None)
        if revision is None:
            raise DelayAnalysisRecordError("ANALYSIS_REVISION_NOT_FOUND")
        review.validate(revision.created_by)
        if review.reviewed_at < revision.created_at:
            raise DelayAnalysisRecordError("REVIEW_PRECEDES_ANALYSIS_REVISION")
        self.connection.execute(self._q("""
            INSERT INTO eng_delay_analysis_review
            (tenant_id,project_id,case_id,revision,reviewer_id,decision,rationale,reviewed_at)
            VALUES (?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING
        """), (review.scope.tenant_id, review.scope.project_id, review.case_id,
              review.revision, review.reviewer_id, review.decision, review.rationale,
              review.reviewed_at.isoformat()))
        row = self.connection.execute(self._q("""
            SELECT decision,rationale,reviewed_at FROM eng_delay_analysis_review
            WHERE tenant_id=? AND project_id=? AND case_id=? AND revision=? AND reviewer_id=?
        """), (review.scope.tenant_id, review.scope.project_id, review.case_id,
              review.revision, review.reviewer_id)).fetchone()
        if row is None or tuple(row) != (review.decision, review.rationale, review.reviewed_at.isoformat()):
            raise DelayAnalysisRecordError("REVIEW_DECISION_IMMUTABLE_CONFLICT")
        if not self.postgres and not was_in_transaction:
            self.connection.commit()
        return review

    def get_case(self, scope: BackendScope, case_id: str) -> DelayAnalysisCase | None:
        scope.validate()
        row = self.connection.execute(self._q("""
            SELECT project_revision,case_id,idempotency_key,request_hash,created_by,created_at
            FROM eng_delay_analysis_case WHERE tenant_id=? AND project_id=? AND case_id=?
        """), (scope.tenant_id, scope.project_id, case_id)).fetchone()
        if row is None:
            return None
        if int(row[0]) != scope.project_revision:
            raise DelayAnalysisRecordError("PROJECT_REVISION_SCOPE_CONFLICT")
        return DelayAnalysisCase(scope, row[1], row[2], row[3], row[4],
                                 datetime.fromisoformat(row[5]))

    def list_revisions(self, scope: BackendScope, case_id: str) -> tuple[DelayAnalysisRevision, ...]:
        scope.validate()
        rows = self.connection.execute(self._q("""
            SELECT payload_json FROM eng_delay_analysis_revision
            WHERE tenant_id=? AND project_id=? AND case_id=? ORDER BY revision
        """), (scope.tenant_id, scope.project_id, case_id)).fetchall()
        return tuple(_revision_from_payload(scope, json.loads(row[0])) for row in rows)

    def is_review_approved(self, scope: BackendScope, case_id: str, revision: int) -> bool:
        row = self.connection.execute(self._q("""
            SELECT 1 FROM eng_delay_analysis_review
            WHERE tenant_id=? AND project_id=? AND case_id=? AND revision=? AND decision='APPROVE'
            LIMIT 1
        """), (scope.tenant_id, scope.project_id, case_id, revision)).fetchone()
        return row is not None


def _revision_payload(item: DelayAnalysisRevision) -> str:
    return _json({
        "case_id": item.case_id, "revision": item.revision, "revision_key": item.revision_key, "method": item.method,
        "baseline_snapshot_id": item.baseline_snapshot_id,
        "baseline_snapshot_hash": item.baseline_snapshot_hash,
        "baseline_data_date": item.baseline_data_date.isoformat(),
        "current_snapshot_id": item.current_snapshot_id,
        "current_snapshot_hash": item.current_snapshot_hash,
        "current_data_date": item.current_data_date.isoformat(),
        "data_date_basis": item.data_date_basis, "data_date_rationale": item.data_date_rationale,
        "statused_update_evidence_hash": item.statused_update_evidence_hash,
        "event_evidence_manifest_hash": item.event_evidence_manifest_hash,
        "result_hash": item.result_hash, "created_by": item.created_by,
        "created_at": item.created_at.isoformat(),
    })


def _revision_from_payload(scope: BackendScope, value: dict) -> DelayAnalysisRevision:
    revision = DelayAnalysisRevision(
        scope=scope, case_id=value["case_id"],
        revision=value["revision"], revision_key=value["revision_key"], method=value["method"],
        baseline_snapshot_id=value["baseline_snapshot_id"],
        baseline_snapshot_hash=value["baseline_snapshot_hash"],
        baseline_data_date=date.fromisoformat(value["baseline_data_date"]),
        current_snapshot_id=value["current_snapshot_id"],
        current_snapshot_hash=value["current_snapshot_hash"],
        current_data_date=date.fromisoformat(value["current_data_date"]),
        data_date_basis=value["data_date_basis"], data_date_rationale=value["data_date_rationale"],
        statused_update_evidence_hash=value["statused_update_evidence_hash"],
        event_evidence_manifest_hash=value["event_evidence_manifest_hash"],
        result_hash=value["result_hash"], created_by=value["created_by"],
        created_at=datetime.fromisoformat(value["created_at"]),
    )
    revision.validate()
    return revision


class SQLiteDelayAnalysisRecordRepository(_SQLDelayAnalysisRecordRepository):
    def __init__(self, connection: sqlite3.Connection) -> None:
        super().__init__(connection, postgres=False)


class PostgresDelayAnalysisRecordRepository(_SQLDelayAnalysisRecordRepository):
    def __init__(self, connection: object) -> None:
        super().__init__(connection, postgres=True)

    def initialize(self) -> None:
        super().initialize()
