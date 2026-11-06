from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
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


_RECORDS_TABLE = "ai_learning_memory_records"
_MIGRATIONS_TABLE = "ai_learning_memory_schema_migrations"

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

_INDEX_NAME = "idx_ai_learning_scope_user"
_INDEX_SCHEMA = (
    f"CREATE INDEX IF NOT EXISTS {_INDEX_NAME} "
    f"ON {_RECORDS_TABLE} (scope, owner_user_id, tenant_id, project_id, status)"
)

_MIGRATIONS_SCHEMA = f"""CREATE TABLE IF NOT EXISTS {_MIGRATIONS_TABLE} (
    version INTEGER PRIMARY KEY,
    migration_name TEXT NOT NULL,
    checksum TEXT NOT NULL,
    applied_at TEXT NOT NULL
)"""

# A migration's checksum is immutable after release. Future schema changes must
# append migration 2+, never edit migration 1 to make existing databases appear
# to have run different DDL.
_MIGRATION_V1_NAME = "create_ai_learning_memory_records"
_MIGRATION_V1_CHECKSUM = hashlib.sha256(
    f"{_SCHEMA}\n{_INDEX_SCHEMA}".encode("utf-8")
).hexdigest()
_MIGRATIONS = ((1, _MIGRATION_V1_NAME, _MIGRATION_V1_CHECKSUM),)

_REQUIRED_RECORD_COLUMNS = {
    "record_id", "record_version", "scope", "status", "signal_kind",
    "owner_user_id", "tenant_id", "project_id", "payload_json",
}
_REQUIRED_MIGRATION_COLUMNS = {"version", "migration_name", "checksum", "applied_at"}


class _RepositoryBase:
    placeholder = "?"

    def __init__(self, connection: object) -> None:
        self.connection = connection

    def _table_columns(self, table_name: str) -> set[str]:
        raise NotImplementedError

    def _require_columns(
        self, table_name: str, required: set[str], error_code: str
    ) -> None:
        actual = self._table_columns(table_name)
        missing = required - actual
        if missing:
            raise AILearningMemoryPersistenceError(
                f"{error_code}:{','.join(sorted(missing))}"
            )

    def _apply_schema_migrations(self) -> None:
        """Apply or adopt known schema versions; never rewrite incompatible data."""
        self.connection.execute(_MIGRATIONS_SCHEMA)
        self._require_columns(
            _MIGRATIONS_TABLE,
            _REQUIRED_MIGRATION_COLUMNS,
            "AI_LEARNING_MIGRATION_HISTORY_SCHEMA_INCOMPATIBLE",
        )

        p = self.placeholder
        rows = self.connection.execute(
            f"SELECT version, migration_name, checksum FROM {_MIGRATIONS_TABLE} ORDER BY version"
        ).fetchall()
        history: dict[int, tuple[str, str]] = {}
        known = {version: (name, checksum) for version, name, checksum in _MIGRATIONS}
        latest_version = max(known)

        for row in rows:
            version = int(row[0])
            name, checksum = str(row[1]), str(row[2])
            if version > latest_version:
                raise AILearningMemoryPersistenceError(
                    "AI_LEARNING_SCHEMA_VERSION_NEWER_THAN_CODE"
                )
            if version not in known:
                raise AILearningMemoryPersistenceError(
                    "AI_LEARNING_SCHEMA_MIGRATION_UNKNOWN"
                )
            if known[version] != (name, checksum):
                raise AILearningMemoryPersistenceError(
                    "AI_LEARNING_SCHEMA_MIGRATION_CHECKSUM_MISMATCH"
                )
            history[version] = (name, checksum)

        for version, name, checksum in _MIGRATIONS:
            if version in history:
                continue

            existing_columns = self._table_columns(_RECORDS_TABLE)
            if not existing_columns:
                self.connection.execute(_SCHEMA)
            else:
                # PR #1542 databases already contain this schema. Adopt them
                # only after proving the complete v1 shape; do not guess at
                # missing columns or silently alter persisted learning data.
                missing = _REQUIRED_RECORD_COLUMNS - existing_columns
                if missing:
                    raise AILearningMemoryPersistenceError(
                        "AI_LEARNING_LEGACY_SCHEMA_INCOMPATIBLE:"
                        + ",".join(sorted(missing))
                    )

            self.connection.execute(_INDEX_SCHEMA)
            self.connection.execute(
                f"INSERT INTO {_MIGRATIONS_TABLE} "
                f"(version, migration_name, checksum, applied_at) "
                f"VALUES ({p},{p},{p},{p}) ON CONFLICT (version) DO NOTHING",
                (version, name, checksum, datetime.now(timezone.utc).isoformat()),
            )
            persisted = self.connection.execute(
                f"SELECT migration_name, checksum FROM {_MIGRATIONS_TABLE} WHERE version={p}",
                (version,),
            ).fetchone()
            if persisted is None or (str(persisted[0]), str(persisted[1])) != (name, checksum):
                raise AILearningMemoryPersistenceError(
                    "AI_LEARNING_SCHEMA_MIGRATION_RACE_OR_CONFLICT"
                )

        self._require_columns(
            _RECORDS_TABLE,
            _REQUIRED_RECORD_COLUMNS,
            "AI_LEARNING_RECORD_SCHEMA_INCOMPATIBLE",
        )
        # Repair a missing non-authoritative index without changing record data.
        self.connection.execute(_INDEX_SCHEMA)

    def initialize(self) -> None:
        """Backend-specific migration transaction ownership."""
        raise NotImplementedError

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
        predicates: list[str] = []
        params: list[object] = []
        if scope.user_private_access_granted:
            predicates.append("(scope = 'user_private' AND owner_user_id = " + p + ")")
            params.append(scope.user_id)
        if scope.project_private_access_granted and scope.tenant_id and scope.project_id:
            # Project ownership is provenance; authorized project membership is
            # the retrieval boundary. Never constrain this branch to creator ID.
            predicates.append(
                "(scope = 'project_private' AND tenant_id = " + p + " AND project_id = " + p + ")"
            )
            params.extend((scope.tenant_id, scope.project_id))
        if scope.general_published_access_granted:
            predicates.append("(scope = 'general_published' AND status = 'published')")
        if scope.tenant_shared_access_granted and scope.tenant_id:
            predicates.append(
                "(scope = 'tenant_shared' AND tenant_id = " + p + " AND status IN ('validated', 'published'))"
            )
            params.append(scope.tenant_id)
        if not predicates:
            return []
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


class SQLiteAILearningMemoryRepository(_RepositoryBase):
    """SQLite durable store; preserves caller-owned transactions."""

    placeholder = "?"

    def __init__(self, connection: sqlite3.Connection) -> None:
        super().__init__(connection)
        self.initialize()

    def _table_columns(self, table_name: str) -> set[str]:
        # Table names are internal constants, never caller-provided identifiers.
        return {
            str(row[1])
            for row in self.connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        }

    def initialize(self) -> None:
        # Atomic DDL + migration-history write. When a caller already owns a
        # transaction, a savepoint lets initialization roll back only its work.
        owns_transaction = not self.connection.in_transaction
        savepoint = "cubi_ai_learning_memory_migration"
        if owns_transaction:
            self.connection.execute("BEGIN IMMEDIATE")
        else:
            self.connection.execute(f"SAVEPOINT {savepoint}")
        try:
            self._apply_schema_migrations()
        except Exception:
            if owns_transaction:
                self.connection.rollback()
            else:
                self.connection.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
                self.connection.execute(f"RELEASE SAVEPOINT {savepoint}")
            raise
        else:
            if owns_transaction:
                self.connection.commit()
            else:
                self.connection.execute(f"RELEASE SAVEPOINT {savepoint}")


class PostgresAILearningMemoryRepository(_RepositoryBase):
    """PostgreSQL durable store; caller owns transactions and commit/rollback."""

    placeholder = "%s"

    def __init__(self, connection: object) -> None:
        super().__init__(connection)

    def _table_columns(self, table_name: str) -> set[str]:
        rows = self.connection.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = current_schema() AND table_name = %s",
            (table_name,),
        ).fetchall()
        return {str(row[0]) for row in rows}

    def initialize(self) -> None:
        # Do not commit here: callers own PostgreSQL transaction boundaries.
        self._apply_schema_migrations()


__all__ = [
    "AILearningMemoryPersistenceError",
    "AILearningMemoryRepository",
    "SQLiteAILearningMemoryRepository",
    "PostgresAILearningMemoryRepository",
]
