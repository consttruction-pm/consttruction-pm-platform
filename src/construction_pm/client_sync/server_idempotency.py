import hashlib
import json
from dataclasses import dataclass, field
from threading import RLock
from typing import Callable

from .offline_mutation import OfflineMutation
from .sync_outcome import SyncOutcome


def mutation_fingerprint(mutation: OfflineMutation) -> str:
    canonical = json.dumps(
        {
            "mutation_id": mutation.mutation_id,
            "tenant_id": mutation.tenant_id,
            "project_id": mutation.project_id,
            "expected_revision": mutation.expected_revision,
            "operation": mutation.operation,
            "payload": dict(mutation.payload),
            "idempotency_key": mutation.idempotency_key,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass
class IdempotencyRecord:
    tenant_id: str
    project_id: str
    idempotency_key: str
    mutation_id: str
    fingerprint: str
    outcome: object


@dataclass
class InMemoryServerIdempotencyStore:
    _records: dict[tuple[str, str, str], IdempotencyRecord] = field(default_factory=dict)
    _lock: RLock = field(default_factory=RLock, repr=False)

    def lookup(self, mutation: OfflineMutation) -> IdempotencyRecord | None:
        with self._lock:
            return self._records.get(
                (mutation.tenant_id, mutation.project_id, mutation.idempotency_key)
            )

    def remember(self, mutation: OfflineMutation, outcome: SyncOutcome) -> None:
        with self._lock:
            self._remember_locked(mutation, outcome)

    def execute_once(
        self,
        mutation: OfflineMutation,
        producer: Callable[[], SyncOutcome],
    ) -> SyncOutcome:
        with self._lock:
            key = (mutation.tenant_id, mutation.project_id, mutation.idempotency_key)
            existing = self._records.get(key)
            if existing is not None:
                if existing.fingerprint != mutation_fingerprint(mutation):
                    raise ValueError("IDEMPOTENCY_KEY_REUSE")
                return existing.outcome  # type: ignore[return-value]

            outcome = producer()
            self._remember_locked(mutation, outcome)
            return outcome

    def _remember_locked(self, mutation: OfflineMutation, outcome: SyncOutcome) -> None:
        key = (mutation.tenant_id, mutation.project_id, mutation.idempotency_key)
        existing = self._records.get(key)
        fingerprint = mutation_fingerprint(mutation)
        if existing is not None and existing.fingerprint != fingerprint:
            raise ValueError("IDEMPOTENCY_KEY_REUSE")
        self._records[key] = IdempotencyRecord(
            mutation.tenant_id,
            mutation.project_id,
            mutation.idempotency_key,
            mutation.mutation_id,
            fingerprint,
            outcome,
        )
