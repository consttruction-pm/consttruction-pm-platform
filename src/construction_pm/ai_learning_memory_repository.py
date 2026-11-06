from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from dataclasses import asdict, dataclass
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


@dataclass(frozen=True)
class AILearningMemoryAuditEvent:
    event_id: str
    actor_user_id: str
    tenant_id: str
    project_id: str
    action: str
    outcome: str
    occurred_at: datetime
    scope: str | None = None
    record_id: str | None = None
    record_version: int | None = None
    reason_code: str | None = None
    result_count: int | None = None

    def validate(self) -> None:
        for name, value in (
            ("event_id", self.event_id),
            ("actor_user_id", self.actor_user_id),
            ("tenant_id", self.tenant_id),
            ("project_id", self.project_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise AILearningMemoryPersistenceError(
                    f"INVALID_AI_LEARNING_AUDIT_{name.upper()}"
                )
        if self.action not in {"list", "get", "append"}:
            raise AILearningMemoryPersistenceError("INVALID_AI_LEARNING_AUDIT_ACTION")
        if self.outcome not in {"allowed", "denied", "empty"}:
            raise AILearningMemoryPersistenceError("INVALID_AI_LEARNING_AUDIT_OUTCOME")
        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise AILearningMemoryPersistenceError("AI_LEARNING_AUDIT_TIMEZONE_REQUIRED")
        if (self.record_id is None) != (self.record_version is None):
            raise AILearningMemoryPersistenceError("AI_LEARNING_AUDIT_RECORD_REFERENCE_INVALID")
        if self.record_id is not None and (
            not isinstance(self.record_id, str) or not self.record_id.strip()
            or isinstance(self.record_version, bool)
            or not isinstance(self.record_version, int)
            or self.record_version < 1
        ):
            raise AILearningMemoryPersistenceError("AI_LEARNING_AUDIT_RECORD_REFERENCE_INVALID")
        if self.result_count is not None and (
            isinstance(self.result_count, bool)
            or not isinstance(self.result_count, int)
            or self.result_count < 0
        ):
            raise AILearningMemoryPersistenceError("AI_LEARNING_AUDIT_RESULT_COUNT_INVALID")
        for name, value in (("scope", self.scope), ("reason_code", self.reason_code)):
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise AILearningMemoryPersistenceError(
                    f"INVALID_AI_LEARNING_AUDIT_{name.upper()}"
                )


class AILearningMemoryRepository(Protocol):
    def initialize(self) -> None: ...
    def append(self, record: AILearningMemoryRecord) -> AILearningMemoryRecord: ...
    def append_with_audit(
        self, record: AILearningMemoryRecord, event: AILearningMemoryAuditEvent
    ) -> AILearningMemoryRecord: ...
    def get(self, record_id: str, record_version: int, scope: LearningRetrievalScope) -> AILearningMemoryRecord | None: ...
    def list_retrievable(self, scope: LearningRetrievalScope) -> tuple[AILearningMemoryRecord, ...]: ...
    def append_audit_event(self, event: AILearningMemoryAuditEvent) -> AILearningMemoryAuditEvent: ...


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

_AUDIT_TABLE = "ai_learning_memory_audit_events"
_AUDIT_SCHEMA = f"""CREATE TABLE IF NOT EXISTS {_AUDIT_TABLE} (
    event_id TEXT PRIMARY KEY,
    actor_user_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    action TEXT NOT NULL,
    outcome TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    scope TEXT,
    record_id TEXT,
    record_version INTEGER,
    reason_code TEXT,
    result_count INTEGER
)"""
_AUDIT_INDEX_SCHEMA = (
    f"CREATE INDEX IF NOT EXISTS idx_ai_learning_audit_scope "
    f"ON {_AUDIT_TABLE} (tenant_id, project_id, occurred_at, event_id)"
)

_SQLITE_APPEND_ONLY_TRIGGERS = (
    """CREATE TRIGGER IF NOT EXISTS cubi_ai_learning_records_no_update
    BEFORE UPDATE ON ai_learning_memory_records
    BEGIN SELECT RAISE(ABORT, 'AI_LEARNING_RECORDS_APPEND_ONLY'); END""",
    """CREATE TRIGGER IF NOT EXISTS cubi_ai_learning_records_no_delete
    BEFORE DELETE ON ai_learning_memory_records
    BEGIN SELECT RAISE(ABORT, 'AI_LEARNING_RECORDS_APPEND_ONLY'); END""",
    """CREATE TRIGGER IF NOT EXISTS cubi_ai_learning_audit_no_update
    BEFORE UPDATE ON ai_learning_memory_audit_events
    BEGIN SELECT RAISE(ABORT, 'AI_LEARNING_AUDIT_APPEND_ONLY'); END""",
    """CREATE TRIGGER IF NOT EXISTS cubi_ai_learning_audit_no_delete
    BEFORE DELETE ON ai_learning_memory_audit_events
    BEGIN SELECT RAISE(ABORT, 'AI_LEARNING_AUDIT_APPEND_ONLY'); END""",
)
_POSTGRES_APPEND_ONLY_FUNCTION = """CREATE OR REPLACE FUNCTION cubi_reject_ai_learning_mutation()
RETURNS trigger LANGUAGE plpgsql AS $
BEGIN
    RAISE EXCEPTION 'AI_LEARNING_ROWS_APPEND_ONLY' USING ERRCODE = '55000';
END;
$"""
_POSTGRES_APPEND_ONLY_TRIGGERS = (
    "DROP TRIGGER IF EXISTS cubi_ai_learning_records_no_update_delete ON ai_learning_memory_records",
    "CREATE TRIGGER cubi_ai_learning_records_no_update_delete "
    "BEFORE UPDATE OR DELETE ON ai_learning_memory_records "
    "FOR EACH ROW EXECUTE FUNCTION cubi_reject_ai_learning_mutation()",
    "DROP TRIGGER IF EXISTS cubi_ai_learning_audit_no_update_delete ON ai_learning_memory_audit_events",
    "CREATE TRIGGER cubi_ai_learning_audit_no_update_delete "
    "BEFORE UPDATE OR DELETE ON ai_learning_memory_audit_events "
    "FOR EACH ROW EXECUTE FUNCTION cubi_reject_ai_learning_mutation()",
)
# Migration 1 is immutable. Do not edit its DDL or checksum after release.
_MIGRATION_V1_NAME = "create_ai_learning_memory_records"
_MIGRATION_V1_CHECKSUM = hashlib.sha256(
    f"{_SCHEMA}\n{_INDEX_SCHEMA}".encode("utf-8")
).hexdigest()
_MIGRATION_V2_NAME = "create_ai_learning_memory_audit_events"
_MIGRATION_V2_CHECKSUM = hashlib.sha256(
    f"{_AUDIT_SCHEMA}\n{_AUDIT_INDEX_SCHEMA}".encode("utf-8")
).hexdigest()
_MIGRATION_V3_NAME = "enforce_append_only_learning_memory_and_audit_rows"
_MIGRATION_V3_CHECKSUM = hashlib.sha256(
    "\\n".join((
        *_SQLITE_APPEND_ONLY_TRIGGERS,
        _POSTGRES_APPEND_ONLY_FUNCTION,
        *_POSTGRES_APPEND_ONLY_TRIGGERS,
    )).encode("utf-8")
).hexdigest()
_MIGRATIONS = (
    (1, _MIGRATION_V1_NAME, _MIGRATION_V1_CHECKSUM),
    (2, _MIGRATION_V2_NAME, _MIGRATION_V2_CHECKSUM),
    (3, _MIGRATION_V3_NAME, _MIGRATION_V3_CHECKSUM),
)

_REQUIRED_RECORD_COLUMNS = {
    "record_id", "record_version", "scope", "status", "signal_kind",
    "owner_user_id", "tenant_id", "project_id", "payload_json",
}
_REQUIRED_MIGRATION_COLUMNS = {"version", "migration_name", "checksum", "applied_at"}
_REQUIRED_AUDIT_COLUMNS = {
    "event_id", "actor_user_id", "tenant_id", "project_id", "action",
    "outcome", "occurred_at", "scope", "record_id", "record_version",
    "reason_code", "result_count",
}


class _RepositoryBase:
    placeholder = "?"

    def __init__(self, connection: object) -> None:
        self.connection = connection

    def _table_columns(self, table_name: str) -> set[str]:
        raise NotImplementedError

    def _table_primary_key_columns(self, table_name: str) -> tuple[str, ...]:
        raise NotImplementedError

    def _ensure_append_only_guards(self) -> None:
        raise NotImplementedError

    def _require_primary_key(
        self, table_name: str, expected: tuple[str, ...], error_code: str
    ) -> None:
        actual = self._table_primary_key_columns(table_name)
        if actual != expected:
            raise AILearningMemoryPersistenceError(
                f"{error_code}:expected={','.join(expected)}:actual={','.join(actual)}"
            )

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
        self._require_primary_key(
            _MIGRATIONS_TABLE,
            ("version",),
            "AI_LEARNING_MIGRATION_HISTORY_PRIMARY_KEY_INCOMPATIBLE",
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

            if version == 1:
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
                    self._require_primary_key(
                        _RECORDS_TABLE,
                        ("record_id", "record_version"),
                        "AI_LEARNING_LEGACY_PRIMARY_KEY_INCOMPATIBLE",
                    )
                self.connection.execute(_INDEX_SCHEMA)
            elif version == 2:
                audit_columns = self._table_columns(_AUDIT_TABLE)
                if not audit_columns:
                    self.connection.execute(_AUDIT_SCHEMA)
                else:
                    missing = _REQUIRED_AUDIT_COLUMNS - audit_columns
                    if missing:
                        raise AILearningMemoryPersistenceError(
                            "AI_LEARNING_AUDIT_LEGACY_SCHEMA_INCOMPATIBLE:"
                            + ",".join(sorted(missing))
                        )
                    self._require_primary_key(
                        _AUDIT_TABLE,
                        ("event_id",),
                        "AI_LEARNING_AUDIT_PRIMARY_KEY_INCOMPATIBLE",
                    )
                self.connection.execute(_AUDIT_INDEX_SCHEMA)
            elif version == 3:
                self._ensure_append_only_guards()
            else:
                raise AILearningMemoryPersistenceError(
                    "AI_LEARNING_SCHEMA_MIGRATION_IMPLEMENTATION_MISSING"
                )

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
        self._require_primary_key(
            _RECORDS_TABLE,
            ("record_id", "record_version"),
            "AI_LEARNING_RECORD_PRIMARY_KEY_INCOMPATIBLE",
        )
        # Repair only non-authoritative indexes; never rewrite existing records.
        self.connection.execute(_INDEX_SCHEMA)
        self._require_columns(
            _AUDIT_TABLE,
            _REQUIRED_AUDIT_COLUMNS,
            "AI_LEARNING_AUDIT_SCHEMA_INCOMPATIBLE",
        )
        self._require_primary_key(
            _AUDIT_TABLE,
            ("event_id",),
            "AI_LEARNING_AUDIT_PRIMARY_KEY_INCOMPATIBLE",
        )
        self.connection.execute(_AUDIT_INDEX_SCHEMA)
        # Recreate missing append-only guards on startup without changing rows.
        self._ensure_append_only_guards()

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
        # A newer immutable version supersedes every earlier version, including
        # when the newer version is rejected or retired. Never resurrect stale
        # published/validated knowledge by filtering old versions independently.
        latest: dict[str, AILearningMemoryRecord] = {}
        for payload in self._read_payloads(scope):
            record = _decode(payload)
            current = latest.get(record.record_id)
            if current is None or record.record_version > current.record_version:
                latest[record.record_id] = record
        return tuple(
            record
            for record in sorted(latest.values(), key=lambda item: item.record_id)
            if record.is_retrievable_for(scope)
        )

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

    def append_with_audit(
        self,
        record: AILearningMemoryRecord,
        event: AILearningMemoryAuditEvent,
    ) -> AILearningMemoryRecord:
        raise NotImplementedError

    def append_audit_event(
        self, event: AILearningMemoryAuditEvent
    ) -> AILearningMemoryAuditEvent:
        if not isinstance(event, AILearningMemoryAuditEvent):
            raise AILearningMemoryPersistenceError("INVALID_AI_LEARNING_AUDIT_EVENT")
        event.validate()
        p = self.placeholder
        values = (
            event.event_id, event.actor_user_id, event.tenant_id, event.project_id,
            event.action, event.outcome, event.occurred_at.isoformat(), event.scope,
            event.record_id, event.record_version, event.reason_code, event.result_count,
        )
        self.connection.execute(
            f"INSERT INTO {_AUDIT_TABLE} "
            "(event_id, actor_user_id, tenant_id, project_id, action, outcome, occurred_at, "
            "scope, record_id, record_version, reason_code, result_count) "
            f"VALUES ({','.join([p] * 12)}) ON CONFLICT (event_id) DO NOTHING",
            values,
        )
        persisted = self.connection.execute(
            f"SELECT event_id, actor_user_id, tenant_id, project_id, action, outcome, "
            f"occurred_at, scope, record_id, record_version, reason_code, result_count "
            f"FROM {_AUDIT_TABLE} WHERE event_id={p}",
            (event.event_id,),
        ).fetchone()
        if persisted is None or tuple(persisted) != values:
            raise AILearningMemoryPersistenceError("AI_LEARNING_AUDIT_EVENT_ID_CONFLICT")
        return event

    def list_audit_events(
        self, *, tenant_id: str, project_id: str, limit: int = 500
    ) -> tuple[AILearningMemoryAuditEvent, ...]:
        for name, value in (("tenant_id", tenant_id), ("project_id", project_id)):
            if not isinstance(value, str) or not value.strip():
                raise AILearningMemoryPersistenceError(
                    f"AI_LEARNING_AUDIT_{name.upper()}_REQUIRED"
                )
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 5000:
            raise AILearningMemoryPersistenceError("AI_LEARNING_AUDIT_LIMIT_INVALID")
        p = self.placeholder
        rows = self.connection.execute(
            f"SELECT event_id, actor_user_id, tenant_id, project_id, action, outcome, "
            f"occurred_at, scope, record_id, record_version, reason_code, result_count "
            f"FROM {_AUDIT_TABLE} WHERE tenant_id={p} AND project_id={p} "
            f"ORDER BY occurred_at, event_id LIMIT {limit}",
            (tenant_id, project_id),
        ).fetchall()
        events = []
        for row in rows:
            try:
                event = AILearningMemoryAuditEvent(
                    event_id=str(row[0]), actor_user_id=str(row[1]),
                    tenant_id=str(row[2]), project_id=str(row[3]),
                    action=str(row[4]), outcome=str(row[5]),
                    occurred_at=datetime.fromisoformat(str(row[6])),
                    scope=None if row[7] is None else str(row[7]),
                    record_id=None if row[8] is None else str(row[8]),
                    record_version=None if row[9] is None else int(row[9]),
                    reason_code=None if row[10] is None else str(row[10]),
                    result_count=None if row[11] is None else int(row[11]),
                )
                event.validate()
            except (TypeError, ValueError) as exc:
                raise AILearningMemoryPersistenceError(
                    "INVALID_STORED_AI_LEARNING_AUDIT_EVENT"
                ) from exc
            events.append(event)
        return tuple(events)


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

    def _table_primary_key_columns(self, table_name: str) -> tuple[str, ...]:
        rows = self.connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        keyed = sorted(
            ((int(row[5]), str(row[1])) for row in rows if int(row[5]) > 0),
            key=lambda item: item[0],
        )
        return tuple(name for _, name in keyed)

    def _ensure_append_only_guards(self) -> None:
        for statement in _SQLITE_APPEND_ONLY_TRIGGERS:
            self.connection.execute(statement)

    def append_with_audit(
        self,
        record: AILearningMemoryRecord,
        event: AILearningMemoryAuditEvent,
    ) -> AILearningMemoryRecord:
        owns_transaction = not self.connection.in_transaction
        savepoint = "cubi_ai_learning_memory_append_audit"
        if owns_transaction:
            self.connection.execute("BEGIN IMMEDIATE")
        else:
            self.connection.execute(f"SAVEPOINT {savepoint}")
        try:
            stored = self.append(record)
            self.append_audit_event(event)
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
            return stored

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

    def _table_primary_key_columns(self, table_name: str) -> tuple[str, ...]:
        rows = self.connection.execute(
            "SELECT kcu.column_name FROM information_schema.table_constraints tc "
            "JOIN information_schema.key_column_usage kcu "
            "ON tc.constraint_name = kcu.constraint_name "
            "AND tc.constraint_schema = kcu.constraint_schema "
            "AND tc.table_name = kcu.table_name "
            "WHERE tc.constraint_type = 'PRIMARY KEY' "
            "AND tc.table_schema = current_schema() AND tc.table_name = %s "
            "ORDER BY kcu.ordinal_position",
            (table_name,),
        ).fetchall()
        return tuple(str(row[0]) for row in rows)

    def _ensure_append_only_guards(self) -> None:
        self.connection.execute(_POSTGRES_APPEND_ONLY_FUNCTION)
        for statement in _POSTGRES_APPEND_ONLY_TRIGGERS:
            self.connection.execute(statement)

    def append_with_audit(
        self,
        record: AILearningMemoryRecord,
        event: AILearningMemoryAuditEvent,
    ) -> AILearningMemoryRecord:
        savepoint = "cubi_ai_learning_memory_append_audit"
        self.connection.execute(f"SAVEPOINT {savepoint}")
        try:
            stored = self.append(record)
            self.append_audit_event(event)
        except Exception:
            self.connection.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
            self.connection.execute(f"RELEASE SAVEPOINT {savepoint}")
            raise
        else:
            self.connection.execute(f"RELEASE SAVEPOINT {savepoint}")
            return stored

    def initialize(self) -> None:
        # Do not commit here: callers own PostgreSQL transaction boundaries.
        self._apply_schema_migrations()


__all__ = [
    "AILearningMemoryPersistenceError",
    "AILearningMemoryAuditEvent",
    "AILearningMemoryRepository",
    "SQLiteAILearningMemoryRepository",
    "PostgresAILearningMemoryRepository",
]
