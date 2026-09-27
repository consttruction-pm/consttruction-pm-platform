from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from .client_sync.revision_limits import MAX_SAFE_PROJECT_REVISION


class DependencyRevisionConflict(RuntimeError):
    """Raised when the project dependency graph revision is stale."""


class DependencyIdempotencyReuse(ValueError):
    """Raised when an idempotency key is reused for different dependency input."""


@dataclass(frozen=True)
class DependencyLink:
    resource_id: str
    tenant_id: str
    project_id: str
    revision: int
    source_resource_id: str
    target_resource_id: str
    dependency_type: str
    metadata: dict[str, Any]

    def validate(self) -> None:
        if not all(
            isinstance(value, str) and value.strip()
            for value in (
                self.resource_id,
                self.tenant_id,
                self.project_id,
                self.source_resource_id,
                self.target_resource_id,
                self.dependency_type,
            )
        ):
            raise ValueError("INVALID_DEPENDENCY_LINK")
        if self.source_resource_id == self.target_resource_id:
            raise ValueError("DEPENDENCY_SELF_REFERENCE")
        if (
            isinstance(self.revision, bool)
            or not isinstance(self.revision, int)
            or self.revision < 0
            or self.revision > MAX_SAFE_PROJECT_REVISION
        ):
            raise ValueError("INVALID_DEPENDENCY_REVISION")


@dataclass(frozen=True)
class StoredDependencyLink:
    link: DependencyLink
    graph_revision: int


@dataclass(frozen=True)
class DependencyAuditEvent:
    tenant_id: str
    project_id: str
    resource_id: str
    graph_revision: int
    event_type: str
    actor_id: str
    occurred_at: datetime


class DependencyConnection(Protocol):
    def execute(self, sql: str, params: tuple[Any, ...] = ()): ...


def dependency_fingerprint(link: DependencyLink) -> str:
    payload = {
        "resource_id": link.resource_id,
        "tenant_id": link.tenant_id,
        "project_id": link.project_id,
        "source_resource_id": link.source_resource_id,
        "target_resource_id": link.target_resource_id,
        "dependency_type": link.dependency_type,
        "metadata": link.metadata,
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


@dataclass
class PostgresDependencyGraphStore:
    connection: DependencyConnection

    def initialize(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS project_dependency_revisions "
            "(tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, revision BIGINT NOT NULL, "
            "PRIMARY KEY (tenant_id, project_id))"
        )
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS project_dependency_links "
            "(tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, resource_id TEXT NOT NULL, "
            "idempotency_key TEXT NOT NULL, fingerprint TEXT NOT NULL, graph_revision BIGINT NOT NULL, "
            "link_json TEXT NOT NULL, PRIMARY KEY (tenant_id, project_id, resource_id), "
            "UNIQUE (tenant_id, project_id, idempotency_key))"
        )
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS project_dependency_audit "
            "(tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, resource_id TEXT NOT NULL, "
            "graph_revision BIGINT NOT NULL, event_type TEXT NOT NULL, actor_id TEXT NOT NULL, "
            "occurred_at TEXT NOT NULL, PRIMARY KEY (tenant_id, project_id, resource_id, graph_revision))"
        )

    def ensure_project(self, tenant_id: str, project_id: str) -> None:
        self.connection.execute(
            "INSERT INTO project_dependency_revisions (tenant_id, project_id, revision) "
            "VALUES (%s,%s,0) ON CONFLICT (tenant_id, project_id) DO NOTHING",
            (tenant_id, project_id),
        )

    def persist(
        self,
        link: DependencyLink,
        *,
        expected_graph_revision: int,
        idempotency_key: str,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredDependencyLink:
        link.validate()
        if not idempotency_key.strip() or not actor_id.strip():
            raise ValueError("INVALID_DEPENDENCY_METADATA")
        if occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
            raise ValueError("DEPENDENCY_AUDIT_TIMESTAMP_MUST_BE_TIMEZONE_AWARE")

        existing = self._find_idempotency(link.tenant_id, link.project_id, idempotency_key)
        fingerprint = dependency_fingerprint(link)
        if existing is not None:
            existing_fingerprint, existing_json, existing_revision = existing
            if existing_fingerprint != fingerprint:
                raise DependencyIdempotencyReuse("IDEMPOTENCY_KEY_REUSE")
            return StoredDependencyLink(_link_from_json(existing_json), existing_revision)

        row = self.connection.execute(
            "SELECT revision FROM project_dependency_revisions "
            "WHERE tenant_id=%s AND project_id=%s FOR UPDATE",
            (link.tenant_id, link.project_id),
        ).fetchone()
        if row is None:
            raise ValueError("DEPENDENCY_PROJECT_NOT_INITIALIZED")
        current = row[0]
        if current != expected_graph_revision:
            raise DependencyRevisionConflict(
                f"DEPENDENCY_REVISION_CONFLICT expected={expected_graph_revision} actual={current}"
            )

        next_revision = current + 1
        payload = json.dumps(link.__dict__, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        self.connection.execute(
            "UPDATE project_dependency_revisions SET revision=%s "
            "WHERE tenant_id=%s AND project_id=%s AND revision=%s",
            (next_revision, link.tenant_id, link.project_id, current),
        )
        self.connection.execute(
            "INSERT INTO project_dependency_links "
            "(tenant_id, project_id, resource_id, idempotency_key, fingerprint, graph_revision, link_json) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (link.tenant_id, link.project_id, link.resource_id, idempotency_key, fingerprint, next_revision, payload),
        )
        self.connection.execute(
            "INSERT INTO project_dependency_audit "
            "(tenant_id, project_id, resource_id, graph_revision, event_type, actor_id, occurred_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (link.tenant_id, link.project_id, link.resource_id, next_revision, "created", actor_id, occurred_at.isoformat()),
        )
        return StoredDependencyLink(link, next_revision)

    def get(self, tenant_id: str, project_id: str, resource_id: str) -> StoredDependencyLink | None:
        row = self.connection.execute(
            "SELECT link_json, graph_revision FROM project_dependency_links "
            "WHERE tenant_id=%s AND project_id=%s AND resource_id=%s",
            (tenant_id, project_id, resource_id),
        ).fetchone()
        if row is None:
            return None
        return StoredDependencyLink(_link_from_json(row[0]), row[1])

    def history(self, tenant_id: str, project_id: str, resource_id: str) -> tuple[DependencyAuditEvent, ...]:
        rows = self.connection.execute(
            "SELECT graph_revision, event_type, actor_id, occurred_at "
            "FROM project_dependency_audit WHERE tenant_id=%s AND project_id=%s AND resource_id=%s "
            "ORDER BY graph_revision ASC",
            (tenant_id, project_id, resource_id),
        ).fetchall()
        return tuple(
            DependencyAuditEvent(
                tenant_id, project_id, resource_id, row[0], row[1], row[2], datetime.fromisoformat(row[3])
            )
            for row in rows
        )

    def _find_idempotency(self, tenant_id: str, project_id: str, key: str):
        row = self.connection.execute(
            "SELECT fingerprint, link_json, graph_revision FROM project_dependency_links "
            "WHERE tenant_id=%s AND project_id=%s AND idempotency_key=%s",
            (tenant_id, project_id, key),
        ).fetchone()
        return None if row is None else (row[0], row[1], row[2])


def _link_from_json(payload: str) -> DependencyLink:
    data = json.loads(payload)
    return DependencyLink(
        resource_id=data["resource_id"],
        tenant_id=data["tenant_id"],
        project_id=data["project_id"],
        revision=int(data["revision"]),
        source_resource_id=data["source_resource_id"],
        target_resource_id=data["target_resource_id"],
        dependency_type=data["dependency_type"],
        metadata=dict(data["metadata"]),
    )
