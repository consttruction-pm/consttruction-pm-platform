import sqlite3
from dataclasses import dataclass
from typing import Any
from .conflict import ConflictContext
from .server_idempotency import IdempotencyRecord

@dataclass
class SQLiteSyncStateStore:
    connection: sqlite3.Connection

    def initialize(self) -> None:
        self.connection.execute("CREATE TABLE IF NOT EXISTS sync_idempotency (tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, idempotency_key TEXT NOT NULL, mutation_id TEXT NOT NULL, fingerprint TEXT NOT NULL, outcome_json TEXT NOT NULL, PRIMARY KEY (tenant_id, project_id, idempotency_key))")
        self.connection.execute("CREATE TABLE IF NOT EXISTS sync_conflicts (tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, mutation_id TEXT NOT NULL, error_code TEXT NOT NULL, expected_revision INTEGER NOT NULL, actual_revision INTEGER, available_actions_json TEXT NOT NULL, details_json TEXT NOT NULL, PRIMARY KEY (tenant_id, project_id, mutation_id))")
        self.connection.commit()

    def put_idempotency(self, record: IdempotencyRecord) -> None:
        row = self.connection.execute("SELECT fingerprint FROM sync_idempotency WHERE tenant_id=? AND project_id=? AND idempotency_key=?", (record.tenant_id, record.project_id, record.idempotency_key)).fetchone()
        if row is not None and row[0] != record.fingerprint: raise ValueError("IDEMPOTENCY_KEY_REUSE")
        self.connection.execute("INSERT OR REPLACE INTO sync_idempotency VALUES (?, ?, ?, ?, ?, ?)", (record.tenant_id, record.project_id, record.idempotency_key, record.mutation_id, record.fingerprint, _json(record.outcome)))
        self.connection.commit()

    def get_idempotency(self, tenant_id: str, project_id: str, key: str) -> IdempotencyRecord | None:
        row = self.connection.execute("SELECT mutation_id, fingerprint, outcome_json FROM sync_idempotency WHERE tenant_id=? AND project_id=? AND idempotency_key=?", (tenant_id, project_id, key)).fetchone()
        return None if row is None else IdempotencyRecord(tenant_id, project_id, key, row[0], row[1], _loads(row[2]))

    def save_conflict(self, mutation_id: str, tenant_id: str, project_id: str, context: ConflictContext) -> None:
        self.connection.execute("INSERT OR REPLACE INTO sync_conflicts VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (tenant_id, project_id, mutation_id, context.error_code, context.expected_revision, context.actual_revision, _json(context.available_actions), _json(context.details)))
        self.connection.commit()

    def get_conflict(self, mutation_id: str, tenant_id: str, project_id: str) -> ConflictContext | None:
        row = self.connection.execute("SELECT error_code, expected_revision, actual_revision, available_actions_json, details_json FROM sync_conflicts WHERE tenant_id=? AND project_id=? AND mutation_id=?", (tenant_id, project_id, mutation_id)).fetchone()
        return None if row is None else ConflictContext(row[0], row[1], row[2], tuple(_loads(row[3])), _loads(row[4]))

def _json(value: Any) -> str:
    import json
    return json.dumps(value, sort_keys=True, separators=(",", ":"))

def _loads(value: str) -> Any:
    import json
    return json.loads(value)
