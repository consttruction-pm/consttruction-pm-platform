from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .errors import OptimisticLockError
from .models import Record


@dataclass(frozen=True)
class StoredRecord:
    record: Record
    record_revision: int


class BackendP0Repository(Protocol):
    def save(self, record: Record, expected_revision: int | None = None) -> StoredRecord: ...
    def get(self, tenant_id: str, project_id: str, record_type: str, record_id: str) -> StoredRecord | None: ...


class InMemoryBackendP0Repository:
    """Deterministic adapter used for application-level tests."""

    def __init__(self) -> None:
        self._records: dict[tuple[str, str, str, str], StoredRecord] = {}

    def save(self, record: Record, expected_revision: int | None = None) -> StoredRecord:
        scope = record.scope
        key = (scope.tenant_id, scope.project_id, _record_type(record), _record_id(record))
        current = self._records.get(key)
        if current is None:
            if expected_revision not in (None, 0):
                raise OptimisticLockError(f"Record does not exist: expected revision {expected_revision}")
            stored = StoredRecord(record, 1)
        else:
            if expected_revision is None:
                raise OptimisticLockError("expected_revision is required for an update")
            if expected_revision != current.record_revision:
                raise OptimisticLockError(
                    f"Stale record revision: expected {expected_revision}, current {current.record_revision}"
                )
            stored = StoredRecord(record, current.record_revision + 1)
        self._records[key] = stored
        return stored

    def get(self, tenant_id: str, project_id: str, record_type: str, record_id: str) -> StoredRecord | None:
        return self._records.get((tenant_id, project_id, record_type, record_id))


def _record_type(record: Record) -> str:
    from .models import resource_type
    return resource_type(record)


def _record_id(record: Record) -> str:
    from .models import record_id
    return record_id(record)
