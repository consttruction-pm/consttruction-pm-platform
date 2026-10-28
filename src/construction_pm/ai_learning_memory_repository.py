from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime
from typing import Protocol

from .ai_learning_memory import (
    AILearningMemoryError,
    AILearningMemoryRecord,
    LearningRetrievalScope,
    LearningScope,
    LearningSignalKind,
    LearningStatus,
)


class AILearningMemoryPersistenceError(ValueError):
    """Raised for invalid, conflicting or unreadable durable learning records."""


class AILearningMemoryRepository(Protocol):
    def append(self, record: AILearningMemoryRecord) -> AILearningMemoryRecord: ...
    def get(self, record_id: str, record_version: int, scope: LearningRetrievalScope) -> AILearningMemoryRecord | None: ...
    def list_retrievable(self, scope: LearningRetrievalScope) -> tuple[AILearningMemoryRecord, ...]: ...
    def list_general_candidates(self) -> tuple[AILearningMemoryRecord, ...]: ...
    def get_general_candidate(self, record_id: str, record_version: int) -> AILearningMemoryRecord | None: ...


def _encode(record: AILearningMemoryRecord) -> str:
    payload = asdict(record)
    payload["scope"] = record.scope.value
    payload["status"] = record.status.value
    payload["signal_kind"] = record.signal_kind.value
    payload["evidence_refs"] = list(record.evidence_refs)
    payload["validation_evidence_refs"] = list(record.validation_evidence_refs)
    payload["captured_at"] = record.captured_at.isoformat()
    payload["updated_at"] = record.updated_at.isoformat()
    payload["approved_at"] = None if record.approved_at is None else record.approved_at.isoformat()
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _decode(payload: object) -> AILearningMemoryRecord:
    try:
        raw = json.loads(str(payload))
        if not isinstance(raw, dict):
            raise ValueError("payload must be an object")
        raw["scope"] = LearningScope(raw["scope"])
        raw["status"] = LearningStatus(raw["status"])
        raw["signal_kind"] = LearningSignalKind(raw["signal_kind"])
        raw["evidence_refs"] = tuple(raw["evidence_refs"])
        raw["validation_evidence_refs"] = tuple(raw["validation_evidence_refs"])
        raw["captured_at"] = datetime.fromisoformat(raw["captured_at"])
        raw["updated_at"] = datetime.fromisoformat(raw["updated_at"])
        raw["approved_at"] = None if raw["approved_at"] is None else datetime.fromisoformat(raw["approved_at"])
        return AILearningMemoryRecord(**raw)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError, AILearningMemoryError) as exc:
        raise AILearningMemoryPersistenceError("INVALID_STORED_AI_LEARNING_MEMORY") from exc


_SCHEMA = """CREATE TABLE IF NOT EXISTS ai_learning_memory_records (
    record_id TEXT NOT NULL,
    record_version INTEGER NOT NULL,
    scope TEXT NOT NULL,
    status TEXT NOT NULL,
    signal_kind TEXT NOT NULL,
    owner_user_id TEXT,
    tenant_id TEXT,
    project_id TEXT,
    payload_json TEXT NOT NULL,
    PRIMARY KEY (record_id, record_version)
)"""


class _RepositoryBase:
    placeholder = "?"

    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(_SCHEMA)
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_ai_learning_scope_user "
            "ON ai_learning_memory_records (scope, owner_user_id, tenant_id, project_id, status)"
        )

    def append(self, record: AILearningMemoryRecord) -> AILearningMemoryRecord:
        if not isinstance(record, AILearningMemoryRecord):
            raise AILearningMemoryPersistenceError("INVALID_AI_LEARNING_RECORD")
        payload = _encode(record)
        p = self.placeholder
        self.connection.execute(
            "INSERT INTO ai_learning_memory_records "
            "(record_id, record_version, scope, status, signal_kind, owner_user_id, tenant_id, project_id, payload_json) "
            f"VALUES ({p},{p},{p},{p},{p},{p},{p},{p},{p}) ON CONFLICT (record_id, record_version) DO NOTHING",
            (
                record.record_id,
                record.record_version,
                record.scope.value,
                record.status.value,
                record.signal_kind.value,
                record.owner_user_id,
                record.tenant_id,
                record.project_id,
                payload,
            ),
        )
        row = self.connection.execute(
            "SELECT payload_json FROM ai_learning_memory_records WHERE record_id="
            + p
            + " AND record_version="
            + p,
            (record.record_id, record.record_version),
        ).fetchone()
        if row is None:
            raise AILearningMemoryPersistenceError("AI_LEARNING_APPEND_NOT_PERSISTED")
        if str(row[0]) != payload:
            raise AILearningMemoryPersistenceError("AI_LEARNING_RECORD_VERSION_CONFLICT")
        return record

    def _read_payloads(self, scope: LearningRetrievalScope) -> list[object]:
        if not isinstance(scope, LearningRetrievalScope):
            raise AILearningMemoryPersistenceError("TRUSTED_AI_LEARNING_RETRIEVAL_SCOPE_REQUIRED")
        p = self.placeholder
        predicates = [
            "(scope = 'user_private' AND owner_user_id = " + p + ")",
            "(scope = 'project_private' AND owner_user_id = " + p + " AND tenant_id = " + p + " AND project_id = " + p + ")",
            "(scope = 'general_published' AND status = 'published')",
        ]
        params: list[object] = [scope.user_id, scope.user_id, scope.tenant_id, scope.project_id]
        if scope.tenant_shared_access_granted and scope.tenant_id:
            predicates.append(
                "(scope = 'tenant_shared' AND tenant_id = " + p + " AND status IN ('validated', 'published'))"
            )
            params.append(scope.tenant_id)
        rows = self.connection.execute(
            "SELECT payload_json FROM ai_learning_memory_records WHERE " + " OR ".join(predicates)
            + " ORDER BY record_id, record_version",
            tuple(params),
        ).fetchall()
        return [row[0] for row in rows]

    def list_retrievable(self, scope: LearningRetrievalScope) -> tuple[AILearningMemoryRecord, ...]:
        records = tuple(
            record
            for record in (_decode(payload) for payload in self._read_payloads(scope))
            if record.is_retrievable_for(scope)
        )
        return records

    def get(
        self, record_id: str, record_version: int, scope: LearningRetrievalScope
    ) -> AILearningMemoryRecord | None:
        if not isinstance(record_id, str) or not record_id.strip():
            raise AILearningMemoryPersistenceError("INVALID_AI_LEARNING_RECORD_ID")
        if isinstance(record_version, bool) or not isinstance(record_version, int) or record_version < 1:
            raise AILearningMemoryPersistenceError("INVALID_AI_LEARNING_RECORD_VERSION")
        for record in self.list_retrievable(scope):
            if record.record_id == record_id and record.record_version == record_version:
                return record
        return None


    def list_general_candidates(self) -> tuple[AILearningMemoryRecord, ...]:
        """List only latest reviewable candidates; never expose private records."""
        rows = self.connection.execute(
            "SELECT candidate_record.payload_json FROM ai_learning_memory_records AS candidate_record "
            "WHERE candidate_record.scope='general_candidate' AND candidate_record.status='candidate' "
            "AND candidate_record.record_version=("
            "SELECT MAX(history_record.record_version) FROM ai_learning_memory_records AS history_record "
            "WHERE history_record.record_id=candidate_record.record_id"
            ") ORDER BY candidate_record.record_id",
            (),
        ).fetchall()
        return tuple(_decode(row[0]) for row in rows)

    def get_general_candidate(
        self, record_id: str, record_version: int
    ) -> AILearningMemoryRecord | None:
        if not isinstance(record_id, str) or not record_id.strip() or len(record_id) > 128:
            raise AILearningMemoryPersistenceError("INVALID_AI_LEARNING_RECORD_ID")
        if isinstance(record_version, bool) or not isinstance(record_version, int) or record_version < 1:
            raise AILearningMemoryPersistenceError("INVALID_AI_LEARNING_RECORD_VERSION")
        p = self.placeholder
        row = self.connection.execute(
            "SELECT candidate_record.payload_json FROM ai_learning_memory_records AS candidate_record "
            f"WHERE candidate_record.record_id={p} AND candidate_record.record_version={p} "
            "AND candidate_record.scope='general_candidate' AND candidate_record.status='candidate' "
            "AND candidate_record.record_version=("
            "SELECT MAX(history_record.record_version) FROM ai_learning_memory_records AS history_record "
            "WHERE history_record.record_id=candidate_record.record_id"
            ")",
            (record_id, record_version),
        ).fetchone()
        return None if row is None else _decode(row[0])


class SQLiteAILearningMemoryRepository(_RepositoryBase):
    """SQLite durable store; caller owns transactions and commit/rollback."""

    placeholder = "?"

    def __init__(self, connection: sqlite3.Connection) -> None:
        super().__init__(connection)
        self.initialize()


class PostgresAILearningMemoryRepository(_RepositoryBase):
    """PostgreSQL durable store; caller owns transactions and commit/rollback."""

    placeholder = "%s"

    def __init__(self, connection: object) -> None:
        super().__init__(connection)

    def initialize(self) -> None:
        self.connection.execute(_SCHEMA)
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_ai_learning_scope_user "
            "ON ai_learning_memory_records (scope, owner_user_id, tenant_id, project_id, status)"
        )


__all__ = [
    "AILearningMemoryPersistenceError",
    "AILearningMemoryRepository",
    "SQLiteAILearningMemoryRepository",
    "PostgresAILearningMemoryRepository",
]
