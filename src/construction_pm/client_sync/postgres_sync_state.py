from dataclasses import dataclass
from typing import Any, Protocol

from .conflict import ConflictContext
from .server_idempotency import IdempotencyRecord

class PostgresConnection(Protocol):
    def execute(self, sql: str, params: tuple[Any, ...] = ()): ...

@dataclass
class PostgresSyncStateStore:
    connection: PostgresConnection

    def initialize(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS sync_idempotency (tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, idempotency_key TEXT NOT NULL, mutation_id TEXT NOT NULL, fingerprint TEXT NOT NULL, outcome_json TEXT NOT NULL, PRIMARY KEY (tenant_id, project_id, idempotency_key))"
        )
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS sync_conflicts (tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, mutation_id TEXT NOT NULL, error_code TEXT NOT NULL, expected_revision INTEGER NOT NULL, actual_revision INTEGER, available_actions_json TEXT NOT NULL, details_json TEXT NOT NULL, PRIMARY KEY (tenant_id, project_id, mutation_id))"
        )

    def lock_idempotency(self, tenant_id: str, project_id: str, key: str) -> None:
        lock_key = _idempotency_lock_identity(tenant_id, project_id, key)
        self.connection.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
            (lock_key,),
        )

    def get_idempotency(self, tenant_id: str, project_id: str, key: str) -> IdempotencyRecord | None:
        row = self.connection.execute(
            "SELECT mutation_id, fingerprint, outcome_json FROM sync_idempotency WHERE tenant_id=%s AND project_id=%s AND idempotency_key=%s",
            (tenant_id, project_id, key),
        ).fetchone()
        if row is None:
            return None
        return IdempotencyRecord(tenant_id, project_id, key, row[0], row[1], _loads(row[2]))

    def put_idempotency(self, record: IdempotencyRecord) -> None:
        self.connection.execute(
            "INSERT INTO sync_idempotency (tenant_id, project_id, idempotency_key, mutation_id, fingerprint, outcome_json) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (tenant_id, project_id, idempotency_key) DO NOTHING",
            (record.tenant_id, record.project_id, record.idempotency_key, record.mutation_id, record.fingerprint, _json(record.outcome)),
        )
        row = self.connection.execute(
            "SELECT fingerprint FROM sync_idempotency WHERE tenant_id=%s AND project_id=%s AND idempotency_key=%s",
            (record.tenant_id, record.project_id, record.idempotency_key),
        ).fetchone()
        if row is not None and row[0] != record.fingerprint:
            raise ValueError("IDEMPOTENCY_KEY_REUSE")

    def save_conflict(self, mutation_id: str, tenant_id: str, project_id: str, context: ConflictContext) -> None:
        self.connection.execute(
            "INSERT INTO sync_conflicts (tenant_id, project_id, mutation_id, error_code, expected_revision, actual_revision, available_actions_json, details_json) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (tenant_id, project_id, mutation_id) DO UPDATE SET error_code=EXCLUDED.error_code, expected_revision=EXCLUDED.expected_revision, actual_revision=EXCLUDED.actual_revision, available_actions_json=EXCLUDED.available_actions_json, details_json=EXCLUDED.details_json",
            (tenant_id, project_id, mutation_id, context.error_code, context.expected_revision, context.actual_revision, _json(context.available_actions), _json(context.details)),
        )

    def get_conflict(self, mutation_id: str, tenant_id: str, project_id: str) -> ConflictContext | None:
        row = self.connection.execute(
            "SELECT error_code, expected_revision, actual_revision, available_actions_json, details_json FROM sync_conflicts WHERE tenant_id=%s AND project_id=%s AND mutation_id=%s",
            (tenant_id, project_id, mutation_id),
        ).fetchone()
        if row is None:
            return None
        return ConflictContext(row[0], row[1], row[2], tuple(_loads(row[3])), _loads(row[4]))

def _json(value: Any) -> str:
    import json
    return json.dumps(value, sort_keys=True, separators=(",", ":"))

def _loads(value: str) -> Any:
    import json
    return json.loads(value)


def _idempotency_lock_identity(tenant_id: str, project_id: str, key: str) -> str:
    """Build an unambiguous advisory-lock identity for the mutation scope."""
    return "|".join(
        f"{len(value)}:{value}"
        for value in (tenant_id, project_id, key)
    )
