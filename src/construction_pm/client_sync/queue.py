from __future__ import annotations

from dataclasses import dataclass
import json
import sqlite3
from threading import RLock
from typing import Protocol

from .mutation import OfflineMutation


class OfflineMutationQueue(Protocol):
    def enqueue(self, mutation: OfflineMutation) -> None: ...
    def peek(self, limit: int = 1) -> list[OfflineMutation]: ...
    def remove(self, idempotency_key: str, operation: str) -> None: ...


class InMemoryOfflineMutationQueue:
    def __init__(self) -> None:
        self._items: dict[tuple[str, str, str, str, str], OfflineMutation] = {}
        self._lock = RLock()

    def enqueue(self, mutation: OfflineMutation) -> None:
        mutation.validate()
        key = (mutation.context.tenant_id, mutation.context.company_id, mutation.context.project_id, mutation.operation, mutation.idempotency_key)
        with self._lock:
            existing = self._items.get(key)
            if existing is not None and existing.fingerprint_payload() != mutation.fingerprint_payload():
                raise ValueError("offline mutation key already contains a different mutation")
            self._items[key] = mutation

    def peek(self, limit: int = 1) -> list[OfflineMutation]:
        if limit < 1:
            raise ValueError("limit must be positive")
        with self._lock:
            return list(self._items.values())[:limit]

    def remove(self, idempotency_key: str, operation: str) -> None:
        with self._lock:
            for key in tuple(self._items):
                if key[1:] == (operation, idempotency_key):
                    del self._items[key]


class SQLiteOfflineMutationQueue:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS offline_mutation_queue (
                tenant_id TEXT NOT NULL, company_id TEXT NOT NULL, project_id TEXT NOT NULL,
                operation TEXT NOT NULL, idempotency_key TEXT NOT NULL,
                payload TEXT NOT NULL, PRIMARY KEY (tenant_id, company_id, project_id, operation, idempotency_key)
            )"""
        )
        self.connection.commit()

    def enqueue(self, mutation: OfflineMutation) -> None:
        mutation.validate()
        payload = json.dumps({
            "contract_version": mutation.contract_version,
            "context": list(mutation.context.fingerprint_payload()),
            "operation": mutation.operation,
            "idempotency_key": mutation.idempotency_key,
            "expected_revision": mutation.expected_revision,
            "mutation": mutation.mutation,
            "attempt": mutation.attempt,
        }, sort_keys=True, separators=(",", ":"), default=str)
        try:
            self.connection.execute(
                """INSERT INTO offline_mutation_queue
                (tenant_id, company_id, project_id, operation, idempotency_key, payload)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (mutation.context.tenant_id, mutation.context.company_id, mutation.context.project_id,
                 mutation.operation, mutation.idempotency_key, payload),
            )
            self.connection.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError("offline mutation key already exists") from exc

    def peek(self, limit: int = 1) -> list[OfflineMutation]:
        if limit < 1:
            raise ValueError("limit must be positive")
        rows = self.connection.execute(
            "SELECT payload FROM offline_mutation_queue ORDER BY rowid LIMIT ?", (limit,)
        ).fetchall()
        result = []
        from .context import OfflineProjectContext
        for (raw,) in rows:
            data = json.loads(raw)
            ctx = data["context"]
            result.append(OfflineMutation(
                context=OfflineProjectContext(
                    tenant_id=ctx[1], company_id=ctx[2], project_id=ctx[3],
                    project_schema_version=ctx[4], calendar_id=ctx[5], calendar_version=ctx[6],
                    scheduling_settings_version=ctx[7], calculation_settings_version=ctx[8],
                ),
                operation=data["operation"], idempotency_key=data["idempotency_key"],
                mutation=data["mutation"], expected_revision=data["expected_revision"], attempt=data["attempt"],
            ))
        return result

    def remove(self, idempotency_key: str, operation: str) -> None:
        self.connection.execute(
            "DELETE FROM offline_mutation_queue WHERE operation=? AND idempotency_key=?",
            (operation, idempotency_key),
        )
        self.connection.commit()
