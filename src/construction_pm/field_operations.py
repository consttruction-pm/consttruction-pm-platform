from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Mapping, Protocol


class FieldOperationType(str, Enum):
    DAILY_LOG = "daily_log"
    ISSUE = "issue"
    OBSERVATION = "observation"
    INSPECTION = "inspection"
    QUALITY = "quality"
    SAFETY = "safety"
    PUNCH = "punch"
    PHOTO = "photo"


class FieldOperationError(ValueError):
    pass


class FieldOperationConflict(FieldOperationError):
    pass


@dataclass(frozen=True)
class FieldOperation:
    tenant_id: str
    project_id: str
    operation_id: str
    revision: int
    operation_type: FieldOperationType
    occurred_at: str
    actor_id: str
    payload: Mapping[str, object]
    location_ref: str | None = None

    def fingerprint(self) -> str:
        canonical = json.dumps(
            {
                "tenant_id": self.tenant_id,
                "project_id": self.project_id,
                "operation_id": self.operation_id,
                "revision": self.revision,
                "operation_type": self.operation_type.value,
                "occurred_at": self.occurred_at,
                "actor_id": self.actor_id,
                "location_ref": self.location_ref,
                "payload": dict(self.payload),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return sha256(canonical.encode("utf-8")).hexdigest()

    def validate(self) -> None:
        for name, value in (
            ("tenant_id", self.tenant_id),
            ("project_id", self.project_id),
            ("operation_id", self.operation_id),
            ("occurred_at", self.occurred_at),
            ("actor_id", self.actor_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise FieldOperationError(f"INVALID_FIELD_OPERATION_{name.upper()}")
        if isinstance(self.revision, bool) or not isinstance(self.revision, int) or self.revision < 0:
            raise FieldOperationError("INVALID_FIELD_OPERATION_REVISION")
        if not isinstance(self.operation_type, FieldOperationType):
            raise FieldOperationError("INVALID_FIELD_OPERATION_TYPE")
        if not isinstance(self.payload, Mapping):
            raise FieldOperationError("INVALID_FIELD_OPERATION_PAYLOAD")


@dataclass(frozen=True)
class FieldOperationAudit:
    tenant_id: str
    project_id: str
    operation_id: str
    revision: int
    actor_id: str
    idempotency_key: str
    fingerprint: str


class FieldOperationRepository(Protocol):
    def get(self, tenant_id: str, project_id: str, operation_id: str) -> FieldOperation | None: ...
    def put(self, operation: FieldOperation) -> None: ...
    def append_audit(self, audit: FieldOperationAudit) -> None: ...
    def get_idempotency(self, tenant_id: str, project_id: str, key: str) -> FieldOperationAudit | None: ...
    def put_idempotency(self, audit: FieldOperationAudit) -> None: ...


class InMemoryFieldOperationRepository:
    def __init__(self) -> None:
        self.operations: dict[tuple[str, str, str], FieldOperation] = {}
        self.audits: list[FieldOperationAudit] = []
        self.idempotency: dict[tuple[str, str, str], FieldOperationAudit] = {}

    def get(self, tenant_id, project_id, operation_id):
        return self.operations.get((tenant_id, project_id, operation_id))

    def put(self, operation):
        operation.validate()
        self.operations[(operation.tenant_id, operation.project_id, operation.operation_id)] = operation

    def append_audit(self, audit):
        self.audits.append(audit)

    def get_idempotency(self, tenant_id, project_id, key):
        return self.idempotency.get((tenant_id, project_id, key))

    def put_idempotency(self, audit):
        self.idempotency[(audit.tenant_id, audit.project_id, audit.idempotency_key)] = audit


class FieldOperationService:
    def __init__(self, repository: FieldOperationRepository) -> None:
        self.repository = repository

    def upsert(
        self,
        operation: FieldOperation,
        *,
        expected_revision: int,
        idempotency_key: str,
    ) -> FieldOperation:
        operation.validate()
        if operation.revision != expected_revision:
            raise FieldOperationConflict("FIELD_OPERATION_REVISION_CONFLICT")

        existing_key = self.repository.get_idempotency(
            operation.tenant_id, operation.project_id, idempotency_key
        )
        if existing_key is not None:
            if existing_key.fingerprint != operation.fingerprint():
                raise FieldOperationConflict("FIELD_OPERATION_IDEMPOTENCY_KEY_REUSE")
            existing = self.repository.get(
                operation.tenant_id, operation.project_id, operation.operation_id
            )
            if existing is None:
                raise FieldOperationConflict("FIELD_OPERATION_IDEMPOTENCY_RECORD_MISSING")
            return existing

        current = self.repository.get(
            operation.tenant_id, operation.project_id, operation.operation_id
        )
        actual_revision = 0 if current is None else current.revision
        if actual_revision != expected_revision:
            raise FieldOperationConflict("FIELD_OPERATION_REVISION_CONFLICT")

        stored = operation
        self.repository.put(stored)
        audit = FieldOperationAudit(
            operation.tenant_id,
            operation.project_id,
            operation.operation_id,
            operation.revision,
            operation.actor_id,
            idempotency_key,
            operation.fingerprint(),
        )
        self.repository.append_audit(audit)
        self.repository.put_idempotency(audit)
        return stored
