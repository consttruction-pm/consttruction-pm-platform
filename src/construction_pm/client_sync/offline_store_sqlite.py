from __future__ import annotations

import json
import sqlite3
from typing import Any

from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.client_sync.offline_mutation import OfflineMutation


class SQLiteOfflineMutationStore:
    """Durable outbox adapter sharing the local project's SQLite transaction.

    The store never commits a transaction owned by its caller. This allows a
    native host to commit a domain mutation and its outbox event atomically.
    """

    def __init__(
        self,
        connection: sqlite3.Connection,
        transaction_manager: SQLiteTransactionManager | None = None,
    ) -> None:
        self.connection = connection
        self.transaction_manager = transaction_manager or SQLiteTransactionManager(connection)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self.transaction_manager.transaction():
            self.connection.execute(
                """CREATE TABLE IF NOT EXISTS cubi_local_schema_versions (
                    component TEXT PRIMARY KEY,
                    version INTEGER NOT NULL CHECK (version >= 1)
                )"""
            )
            row = self.connection.execute(
                "SELECT version FROM cubi_local_schema_versions WHERE component=?",
                ("offline_mutation_store",),
            ).fetchone()
            version = 0 if row is None else int(row[0])
            if version not in (0, 1):
                raise ValueError("UNSUPPORTED_OFFLINE_MUTATION_STORE_SCHEMA_VERSION")
            self.connection.execute(
                """CREATE TABLE IF NOT EXISTS cubi_offline_mutations (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    mutation_id TEXT NOT NULL UNIQUE,
                    tenant_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    expected_revision INTEGER NOT NULL CHECK (expected_revision >= 0),
                    operation TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    UNIQUE (tenant_id, project_id, idempotency_key)
                )"""
            )
            if version == 0:
                self.connection.execute(
                    "INSERT INTO cubi_local_schema_versions(component, version) VALUES (?, ?)",
                    ("offline_mutation_store", 1),
                )

    @staticmethod
    def _payload_json(mutation: OfflineMutation) -> str:
        if not isinstance(mutation.payload, dict) and not hasattr(mutation.payload, "items"):
            raise ValueError("OFFLINE_MUTATION_PAYLOAD_MUST_BE_OBJECT")
        return json.dumps(
            dict(mutation.payload),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )

    def append(self, mutation: OfflineMutation) -> None:
        payload_json = self._payload_json(mutation)
        try:
            with self.transaction_manager.transaction():
                self.connection.execute(
                    """INSERT INTO cubi_offline_mutations
                    (mutation_id, tenant_id, project_id, expected_revision,
                     operation, payload_json, idempotency_key)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        mutation.mutation_id,
                        mutation.tenant_id,
                        mutation.project_id,
                        mutation.expected_revision,
                        mutation.operation,
                        payload_json,
                        mutation.idempotency_key,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            duplicate_id = self.connection.execute(
                "SELECT 1 FROM cubi_offline_mutations WHERE mutation_id=?",
                (mutation.mutation_id,),
            ).fetchone()
            if duplicate_id is not None:
                raise ValueError("DUPLICATE_MUTATION_ID") from exc
            duplicate_key = self.connection.execute(
                """SELECT 1 FROM cubi_offline_mutations
                WHERE tenant_id=? AND project_id=? AND idempotency_key=?""",
                (mutation.tenant_id, mutation.project_id, mutation.idempotency_key),
            ).fetchone()
            if duplicate_key is not None:
                raise ValueError("DUPLICATE_IDEMPOTENCY_KEY") from exc
            raise

    def pending(self) -> tuple[OfflineMutation, ...]:
        rows = self.connection.execute(
            """SELECT mutation_id, tenant_id, project_id, expected_revision,
                      operation, payload_json, idempotency_key
               FROM cubi_offline_mutations ORDER BY sequence"""
        ).fetchall()
        return tuple(
            OfflineMutation(
                mutation_id=str(row[0]),
                tenant_id=str(row[1]),
                project_id=str(row[2]),
                expected_revision=int(row[3]),
                operation=str(row[4]),
                payload=json.loads(row[5]),
                idempotency_key=str(row[6]),
            )
            for row in rows
        )

    def acknowledge(self, mutation_id: str) -> None:
        with self.transaction_manager.transaction():
            self.connection.execute(
                "DELETE FROM cubi_offline_mutations WHERE mutation_id=?",
                (mutation_id,),
            )
