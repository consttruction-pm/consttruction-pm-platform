from dataclasses import dataclass
from typing import Protocol

from .server_idempotency import IdempotencyRecord


class IdempotencyStore(Protocol):
    def get(self, tenant_id: str, project_id: str, idempotency_key: str) -> IdempotencyRecord | None: ...
    def put(self, record: IdempotencyRecord) -> None: ...


@dataclass
class InMemoryDurableIdempotencyStore:
    _records: dict[tuple[str, str, str], IdempotencyRecord]

    def __init__(self) -> None:
        self._records = {}

    def get(self, tenant_id: str, project_id: str, idempotency_key: str) -> IdempotencyRecord | None:
        return self._records.get((tenant_id, project_id, idempotency_key))

    def put(self, record: IdempotencyRecord) -> None:
        key = (record.tenant_id, record.project_id, record.idempotency_key)
        existing = self._records.get(key)
        if existing is not None and existing.fingerprint != record.fingerprint:
            raise ValueError("IDEMPOTENCY_KEY_REUSE")
        self._records[key] = record
