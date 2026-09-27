from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from .client_sync.revision_limits import MAX_SAFE_PROJECT_REVISION

FIELD_RESOURCE_TYPES = frozenset(
    {
        "daily_log",
        "issue",
        "observation",
        "inspection",
        "quality_record",
        "safety_record",
        "punch_item",
        "field_photo",
        "timecard",
        "equipment_status",
    }
)


class FieldResourceRevisionConflict(RuntimeError):
    pass


class FieldResourceIdempotencyReuse(ValueError):
    pass


@dataclass(frozen=True)
class FieldResource:
    resource_id: str
    tenant_id: str
    project_id: str
    resource_type: str
    revision: int
    payload: dict[str, Any]

    def validate(self) -> None:
        if not all(
            isinstance(value, str) and value.strip()
            for value in (
                self.resource_id,
                self.tenant_id,
                self.project_id,
                self.resource_type,
            )
        ):
            raise ValueError("INVALID_FIELD_RESOURCE")
        if self.resource_type not in FIELD_RESOURCE_TYPES:
            raise ValueError("INVALID_FIELD_RESOURCE_TYPE")
        if (
            isinstance(self.revision, bool)
            or not isinstance(self.revision, int)
            or self.revision < 0
            or self.revision > MAX_SAFE_PROJECT_REVISION
        ):
            raise ValueError("INVALID_FIELD_RESOURCE_REVISION")
        if not isinstance(self.payload, dict):
            raise ValueError("INVALID_FIELD_RESOURCE_PAYLOAD")


@dataclass(frozen=True)
class StoredFieldResource:
    resource: FieldResource
    project_revision: int


class FieldResourceConnection(Protocol):
    def execute(self, sql: str, params: tuple[Any, ...] = ()): ...


def field_resource_fingerprint(resource: FieldResource) -> str:
    payload = {
        "resource_id": resource.resource_id,
        "tenant_id": resource.tenant_id,
        "project_id": resource.project_id,
        "resource_type": resource.resource_type,
        "revision": resource.revision,
        "payload": resource.payload,
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


@dataclass
class PostgresFieldResourceStore:
    connection: FieldResourceConnection

    def initialize(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS project_field_revisions "
            "(tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, revision BIGINT NOT NULL, "
            "PRIMARY KEY (tenant_id, project_id))"
        )
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS project_field_resources "
            "(tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, resource_id TEXT NOT NULL, "
            "idempotency_key TEXT NOT NULL, fingerprint TEXT NOT NULL, project_revision BIGINT NOT NULL, "
            "resource_json TEXT NOT NULL, PRIMARY KEY (tenant_id, project_id, resource_id), "
            "UNIQUE (tenant_id, project_id, idempotency_key))"
        )
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS project_field_audit "
            "(tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, resource_id TEXT NOT NULL, "
            "project_revision BIGINT NOT NULL, event_type TEXT NOT NULL, actor_id TEXT NOT NULL, "
            "occurred_at TEXT NOT NULL, PRIMARY KEY (tenant_id, project_id, resource_id, project_revision))"
        )

    def ensure_project(self, tenant_id: str, project_id: str) -> None:
        self.connection.execute(
            "INSERT INTO project_field_revisions (tenant_id, project_id, revision) "
            "VALUES (%s,%s,0) ON CONFLICT (tenant_id, project_id) DO NOTHING",
            (tenant_id, project_id),
        )

    def persist(
        self,
        resource: FieldResource,
        *,
        expected_project_revision: int,
        idempotency_key: str,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredFieldResource:
        resource.validate()
        if not idempotency_key.strip() or not actor_id.strip():
            raise ValueError("INVALID_FIELD_RESOURCE_METADATA")
        if occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
            raise ValueError("FIELD_AUDIT_TIMESTAMP_MUST_BE_TIMEZONE_AWARE")

        fingerprint = field_resource_fingerprint(resource)
        existing = self._find_idempotency(resource.tenant_id, resource.project_id, idempotency_key)
        if existing is not None:
            existing_fingerprint, existing_json, existing_revision = existing
            if existing_fingerprint != fingerprint:
                raise FieldResourceIdempotencyReuse("IDEMPOTENCY_KEY_REUSE")
            return StoredFieldResource(_resource_from_json(existing_json), existing_revision)

        row = self.connection.execute(
            "SELECT revision FROM project_field_revisions "
            "WHERE tenant_id=%s AND project_id=%s FOR UPDATE",
            (resource.tenant_id, resource.project_id),
        ).fetchone()
        if row is None:
            raise ValueError("FIELD_PROJECT_NOT_INITIALIZED")
        current = row[0]
        if current != expected_project_revision:
            raise FieldResourceRevisionConflict(
                f"FIELD_REVISION_CONFLICT expected={expected_project_revision} actual={current}"
            )

        next_revision = current + 1
        payload = json.dumps(
            resource.__dict__, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        self.connection.execute(
            "UPDATE project_field_revisions SET revision=%s "
            "WHERE tenant_id=%s AND project_id=%s AND revision=%s",
            (next_revision, resource.tenant_id, resource.project_id, current),
        )
        self.connection.execute(
            "INSERT INTO project_field_resources "
            "(tenant_id, project_id, resource_id, idempotency_key, fingerprint, project_revision, resource_json) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (
                resource.tenant_id,
                resource.project_id,
                resource.resource_id,
                idempotency_key,
                fingerprint,
                next_revision,
                payload,
            ),
        )
        self.connection.execute(
            "INSERT INTO project_field_audit "
            "(tenant_id, project_id, resource_id, project_revision, event_type, actor_id, occurred_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (
                resource.tenant_id,
                resource.project_id,
                resource.resource_id,
                next_revision,
                "created",
                actor_id,
                occurred_at.isoformat(),
            ),
        )
        return StoredFieldResource(resource, next_revision)

    def get(self, tenant_id: str, project_id: str, resource_id: str) -> StoredFieldResource | None:
        row = self.connection.execute(
            "SELECT resource_json, project_revision FROM project_field_resources "
            "WHERE tenant_id=%s AND project_id=%s AND resource_id=%s",
            (tenant_id, project_id, resource_id),
        ).fetchone()
        if row is None:
            return None
        return StoredFieldResource(_resource_from_json(row[0]), row[1])

    def history(self, tenant_id: str, project_id: str, resource_id: str):
        rows = self.connection.execute(
            "SELECT project_revision, event_type, actor_id, occurred_at "
            "FROM project_field_audit WHERE tenant_id=%s AND project_id=%s AND resource_id=%s "
            "ORDER BY project_revision ASC",
            (tenant_id, project_id, resource_id),
        ).fetchall()
        return tuple(
            (row[0], row[1], row[2], datetime.fromisoformat(row[3]))
            for row in rows
        )

    def _find_idempotency(self, tenant_id: str, project_id: str, key: str):
        row = self.connection.execute(
            "SELECT fingerprint, resource_json, project_revision FROM project_field_resources "
            "WHERE tenant_id=%s AND project_id=%s AND idempotency_key=%s",
            (tenant_id, project_id, key),
        ).fetchone()
        return None if row is None else (row[0], row[1], row[2])


def _resource_from_json(payload: str) -> FieldResource:
    data = json.loads(payload)
    return FieldResource(
        resource_id=data["resource_id"],
        tenant_id=data["tenant_id"],
        project_id=data["project_id"],
        resource_type=data["resource_type"],
        revision=int(data["revision"]),
        payload=dict(data["payload"]),
    )
