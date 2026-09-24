from __future__ import annotations

import json
import sqlite3
from threading import RLock
from typing import Protocol

from .context import OfflineProjectContext
from .mutation import OfflineMutation


class OfflineMutationQueue(Protocol):
    def enqueue(self, mutation: OfflineMutation) -> None: ...
    def peek(self, limit: int = 1) -> list[OfflineMutation]: ...
    def remove(self, mutation: OfflineMutation) -> None: ...
    def increment_attempt(self, mutation: OfflineMutation) -> OfflineMutation: ...


def _queue_key(mutation: OfflineMutation) -> tuple[str, str, str, str, str]:
    return (
        mutation.context.tenant_id,
        mutation.context.company_id,
        mutation.context.project_id,
        mutation.operation,
        mutation.idempotency_key,
    )


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

    def remove(self, mutation: OfflineMutation) -> None:
        mutation.validate()
        with self._lock:
            self._items.pop(_queue_key(mutation), None)

    def increment_attempt(self, mutation: OfflineMutation) -> OfflineMutation:
        mutation.validate()
        key = _queue_key(mutation)
        with self._lock:
            existing = self._items.get(key)
            if existing is None:
                raise KeyError("offline mutation is not queued")
            updated = OfflineMutation(
                context=existing.context,
                operation=existing.operation,
                idempotency_key=existing.idempotency_key,
                mutation=existing.mutation,
                expected_revision=existing.expected_revision,
                attempt=existing.attempt + 1,
            )
            self._items[key] = updated
            return updated


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

    @staticmethod
    def _encode(mutation: OfflineMutation) -> str:
        mutation.validate()
        return json.dumps({
            "contract_version": mutation.contract_version,
            "context": list(mutation.context.fingerprint_payload()),
            "operation": mutation.operation,
            "idempotency_key": mutation.idempotency_key,
            "expected_revision": mutation.expected_revision,
            "mutation": mutation.mutation,
            "attempt": mutation.attempt,
        }, sort_keys=True, separators=(",", ":"), default=str)

    @staticmethod
    def _decode(raw: str) -> OfflineMutation:
        data = json.loads(raw)
        ctx = data["context"]
        return OfflineMutation(
            context=OfflineProjectContext(
                tenant_id=ctx[1], company_id=ctx[2], project_id=ctx[3],
                project_schema_version=ctx[4], calendar_id=ctx[5], calendar_version=ctx[6],
                scheduling_settings_version=ctx[7], calculation_settings_version=ctx[8],
            ),
            operation=data["operation"], idempotency_key=data["idempotency_key"],
            mutation=data["mutation"], expected_revision=data["expected_revision"], attempt=data["attempt"],
        )

    def _commit_if_owned(self) -> None:
        if not self.connection.in_transaction:
            self.connection.commit()

    def enqueue(self, mutation: OfflineMutation) -> None:
        mutation.validate()
        payload = self._encode(mutation)
        try:
            self.connection.execute(
                """INSERT INTO offline_mutation_queue
                (tenant_id, company_id, project_id, operation, idempotency_key, payload)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (mutation.context.tenant_id, mutation.context.company_id, mutation.context.project_id,
                 mutation.operation, mutation.idempotency_key, payload),
            )
            self._commit_if_owned()
        except sqlite3.IntegrityError as exc:
            raise ValueError("offline mutation key already exists") from exc

    def peek(self, limit: int = 1) -> list[OfflineMutation]:
        if limit < 1:
            raise ValueError("limit must be positive")
        rows = self.connection.execute(
            "SELECT payload FROM offline_mutation_queue ORDER BY rowid LIMIT ?", (limit,)
        ).fetchall()
        return [self._decode(raw) for (raw,) in rows]

    def remove(self, mutation: OfflineMutation) -> None:
        mutation.validate()
        self.connection.execute(
            """DELETE FROM offline_mutation_queue
            WHERE tenant_id=? AND company_id=? AND project_id=? AND operation=? AND idempotency_key=?""",
            _queue_key(mutation),
        )
        self._commit_if_owned()

    def increment_attempt(self, mutation: OfflineMutation) -> OfflineMutation:
        mutation.validate()
        key = _queue_key(mutation)
        row = self.connection.execute(
            """SELECT payload FROM offline_mutation_queue
            WHERE tenant_id=? AND company_id=? AND project_id=? AND operation=? AND idempotency_key=?""",
            key,
        ).fetchone()
        if row is None:
            raise KeyError("offline mutation is not queued")
        existing = self._decode(row[0])
        updated = OfflineMutation(
            context=existing.context,
            operation=existing.operation,
            idempotency_key=existing.idempotency_key,
            mutation=existing.mutation,
            expected_revision=existing.expected_revision,
            attempt=existing.attempt + 1,
        )
        self.connection.execute(
            """UPDATE offline_mutation_queue SET payload=?
            WHERE tenant_id=? AND company_id=? AND project_id=? AND operation=? AND idempotency_key=?""",
            (self._encode(updated), *key),
        )
        self._commit_if_owned()
        return updated
