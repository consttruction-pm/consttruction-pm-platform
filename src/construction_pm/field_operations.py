from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Any, Mapping, Protocol


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

        self.repository.put(operation)
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
        return operation


class FieldOperationIdempotencyReuse(FieldOperationConflict):
    pass


class FieldOperationRevisionConflict(FieldOperationConflict):
    pass


@dataclass(frozen=True)
class StoredFieldOperation:
    operation: FieldOperation
    project_revision: int


class FieldOperationConnection(Protocol):
    def execute(self, sql: str, params: tuple[Any, ...] = ()): ...


@dataclass
class PostgresFieldOperationStore:
    connection: FieldOperationConnection

    def initialize(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS project_field_operation_revisions "
            "(tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, revision BIGINT NOT NULL, "
            "PRIMARY KEY (tenant_id, project_id))"
        )
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS project_field_operations "
            "(tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, operation_id TEXT NOT NULL, "
            "idempotency_key TEXT NOT NULL, fingerprint TEXT NOT NULL, project_revision BIGINT NOT NULL, "
            "operation_json TEXT NOT NULL, PRIMARY KEY (tenant_id, project_id, operation_id), "
            "UNIQUE (tenant_id, project_id, idempotency_key))"
        )
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS project_field_operation_audit "
            "(tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, operation_id TEXT NOT NULL, "
            "project_revision BIGINT NOT NULL, actor_id TEXT NOT NULL, idempotency_key TEXT NOT NULL, "
            "occurred_at TEXT NOT NULL, PRIMARY KEY (tenant_id, project_id, operation_id, project_revision))"
        )

    def ensure_project(self, tenant_id: str, project_id: str) -> None:
        self.connection.execute(
            "INSERT INTO project_field_operation_revisions (tenant_id, project_id, revision) "
            "VALUES (%s,%s,0) ON CONFLICT (tenant_id, project_id) DO NOTHING",
            (tenant_id, project_id),
        )

    def persist(
        self,
        operation: FieldOperation,
        *,
        expected_project_revision: int,
        idempotency_key: str,
    ) -> StoredFieldOperation:
        operation.validate()
        if not isinstance(idempotency_key, str) or not idempotency_key.strip():
            raise FieldOperationError("INVALID_FIELD_OPERATION_IDEMPOTENCY_KEY")

        row = self.connection.execute(
                "SELECT revision FROM project_field_operation_revisions "
                "WHERE tenant_id=%s AND project_id=%s FOR UPDATE",
                (operation.tenant_id, operation.project_id),
            ).fetchone()
            if row is None:
                raise FieldOperationError("FIELD_OPERATION_PROJECT_NOT_INITIALIZED")

            existing = self._find_idempotency(
                operation.tenant_id, operation.project_id, idempotency_key
            )
            fingerprint = operation.fingerprint()
            if existing is not None:
                old_fingerprint, old_json, old_revision = existing
                if old_fingerprint != fingerprint:
                    raise FieldOperationIdempotencyReuse(
                        "FIELD_OPERATION_IDEMPOTENCY_KEY_REUSE"
                    )
                return StoredFieldOperation(_from_json(old_json), old_revision)

            current = row[0]
            if current != expected_project_revision:
                raise FieldOperationRevisionConflict(
                    f"FIELD_OPERATION_REVISION_CONFLICT expected={expected_project_revision} actual={current}"
                )

            next_revision = current + 1
            payload = json.dumps(
                {
                    "tenant_id": operation.tenant_id,
                    "project_id": operation.project_id,
                    "operation_id": operation.operation_id,
                    "revision": operation.revision,
                    "operation_type": operation.operation_type.value,
                    "occurred_at": operation.occurred_at,
                    "actor_id": operation.actor_id,
                    "location_ref": operation.location_ref,
                    "payload": dict(operation.payload),
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            self.connection.execute(
                "UPDATE project_field_operation_revisions SET revision=%s "
                "WHERE tenant_id=%s AND project_id=%s AND revision=%s",
                (next_revision, operation.tenant_id, operation.project_id, current),
            )
            self.connection.execute(
                "INSERT INTO project_field_operations "
                "(tenant_id, project_id, operation_id, idempotency_key, fingerprint, project_revision, operation_json) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (
                    operation.tenant_id,
                    operation.project_id,
                    operation.operation_id,
                    idempotency_key,
                    fingerprint,
                    next_revision,
                    payload,
                ),
            )
            self.connection.execute(
                "INSERT INTO project_field_operation_audit "
                "(tenant_id, project_id, operation_id, project_revision, actor_id, idempotency_key, occurred_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (
                    operation.tenant_id,
                    operation.project_id,
                    operation.operation_id,
                    next_revision,
                    operation.actor_id,
                    idempotency_key,
                    operation.occurred_at,
                ),
            )
            return StoredFieldOperation(operation, next_revision)

    def get(self, tenant_id: str, project_id: str, operation_id: str) -> StoredFieldOperation | None:
        row = self.connection.execute(
            "SELECT operation_json, project_revision FROM project_field_operations "
            "WHERE tenant_id=%s AND project_id=%s AND operation_id=%s",
            (tenant_id, project_id, operation_id),
        ).fetchone()
        if row is None:
            return None
        return StoredFieldOperation(_from_json(row[0]), row[1])

    def _find_idempotency(self, tenant_id: str, project_id: str, key: str):
        row = self.connection.execute(
            "SELECT fingerprint, operation_json, project_revision "
            "FROM project_field_operations "
            "WHERE tenant_id=%s AND project_id=%s AND idempotency_key=%s",
            (tenant_id, project_id, key),
        ).fetchone()
        return None if row is None else (row[0], row[1], row[2])


def _from_json(payload: str) -> FieldOperation:
    data = json.loads(payload)
    return FieldOperation(
        tenant_id=data["tenant_id"],
        project_id=data["project_id"],
        operation_id=data["operation_id"],
        revision=int(data["revision"]),
        operation_type=FieldOperationType(data["operation_type"]),
        occurred_at=data["occurred_at"],
        actor_id=data["actor_id"],
        location_ref=data.get("location_ref"),
        payload=dict(data["payload"]),
    )
