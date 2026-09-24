from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from threading import RLock
from typing import Callable, Generic, Protocol, TypeVar

from .context import ProjectContext
from .errors import conflict_error

T = TypeVar("T")


@dataclass(frozen=True)
class IdempotencyRecord(Generic[T]):
    fingerprint: str
    result: T


class MutationIdempotencyStore(Protocol):
    """Application contract for atomic mutation idempotency."""

    def execute(
        self,
        context: ProjectContext,
        key: str,
        operation: str,
        fingerprint: str,
        mutation: Callable[[], T],
    ) -> T: ...


class InMemoryMutationIdempotencyStore:
    """Deterministic test adapter; persistent adapters own durable records."""

    def __init__(self) -> None:
        self._records: dict[tuple[str, str, str, str], IdempotencyRecord[object]] = {}
        self._lock = RLock()

    def execute(
        self,
        context: ProjectContext,
        key: str,
        operation: str,
        fingerprint: str,
        mutation: Callable[[], T],
    ) -> T:
        if not key or not key.strip():
            raise conflict_error("INVALID_IDEMPOTENCY_KEY", "Idempotency key is required")
        context.validate()
        record_key = (context.tenant_id, context.company_id, context.project_id, operation + ":" + key)
        with self._lock:
            existing = self._records.get(record_key)
            if existing is not None:
                if existing.fingerprint != fingerprint:
                    raise conflict_error(
                        "IDEMPOTENCY_KEY_REUSE",
                        "Idempotency key was already used for a different mutation",
                    )
                return existing.result  # type: ignore[return-value]

            result = mutation()
            self._records[record_key] = IdempotencyRecord(fingerprint, result)
            return result


def resource_fingerprint(resource: object) -> str:
    return _fingerprint({"kind": "resource", "value": _canonical(resource)})


def assignment_fingerprint(assignment: object) -> str:
    return _fingerprint({"kind": "assignment", "value": _canonical(assignment)})


def _fingerprint(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(payload.encode("utf-8")).hexdigest()


def _canonical(value: object) -> object:
    if hasattr(value, "__dataclass_fields__"):
        return {
            name: _canonical(getattr(value, name))
            for name in value.__dataclass_fields__
        }
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
