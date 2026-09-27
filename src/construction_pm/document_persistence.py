from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any, Protocol


MAX_SAFE_REVISION = 9_007_199_254_740_991
DOCUMENT_TYPES = {
    "contract", "drawing", "correspondence", "rfi",
    "submittal", "delay_claim", "evidence",
}
DOCUMENT_STATUSES = {"draft", "submitted", "approved", "rejected", "superseded"}


class DocumentRevisionConflict(ValueError):
    pass


class DocumentIdempotencyReuse(ValueError):
    pass


class DocumentApprovalTransitionError(ValueError):
    pass


class DocumentAuthorizationError(ValueError):
    pass


class DocumentLifecycleAuthorizer(Protocol):
    def authorize_transition(self, *, actor_id: str, tenant_id: str, project_id: str, document_id: str, from_status: str, to_status: str) -> None: ...


class RoleDocumentLifecycleAuthorizer:
    """Application-boundary authorization; persistence remains role-agnostic."""

    def __init__(self, approver_actor_ids: set[str]) -> None:
        self.approver_actor_ids = frozenset(approver_actor_ids)

    def authorize_transition(self, *, actor_id: str, tenant_id: str, project_id: str, document_id: str, from_status: str, to_status: str) -> None:
        if to_status in {"approved", "rejected"} and actor_id not in self.approver_actor_ids:
            raise DocumentAuthorizationError("DOCUMENT_TRANSITION_FORBIDDEN")


DOCUMENT_APPROVAL_TRANSITIONS = {
    "draft": {"submitted"},
    "submitted": {"approved", "rejected"},
    "rejected": {"submitted"},
    "approved": {"superseded"},
    "superseded": set(),
}


@dataclass(frozen=True)
class DocumentRecord:
    document_id: str
    tenant_id: str
    project_id: str
    resource_type: str
    title: str
    status: str
    storage_ref: str
    content_hash: str
    linked_entity_refs: tuple[str, ...] = ()

    def validate(self) -> None:
        for name, value in (
            ("document_id", self.document_id),
            ("tenant_id", self.tenant_id),
            ("project_id", self.project_id),
            ("title", self.title),
            ("storage_ref", self.storage_ref),
            ("content_hash", self.content_hash),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"INVALID_DOCUMENT_{name.upper()}")
        if self.resource_type not in DOCUMENT_TYPES:
            raise ValueError("INVALID_DOCUMENT_RESOURCE_TYPE")
        if self.status not in DOCUMENT_STATUSES:
            raise ValueError("INVALID_DOCUMENT_STATUS")
        if not isinstance(self.linked_entity_refs, tuple):
            raise ValueError("INVALID_DOCUMENT_LINKED_ENTITY_REFS")
        if not all(isinstance(ref, str) and ref.strip() for ref in self.linked_entity_refs):
            raise ValueError("INVALID_DOCUMENT_LINKED_ENTITY_REF")
        if not self.content_hash.startswith("sha256:") or len(self.content_hash) != 71:
            raise ValueError("INVALID_DOCUMENT_CONTENT_HASH")

    def as_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "resource_type": self.resource_type,
            "title": self.title,
            "status": self.status,
            "storage_ref": self.storage_ref,
            "content_hash": self.content_hash,
            "linked_entity_refs": list(self.linked_entity_refs),
        }


@dataclass(frozen=True)
class StoredDocument:
    document: DocumentRecord
    revision: int


@dataclass(frozen=True)
class DocumentAuditEvent:
    document_id: str
    revision: int
    event_type: str
    actor_id: str
    occurred_at: datetime
    reason: str = ""


class PostgresDocumentStore:
    """Persistence boundary for document metadata; bytes remain behind storage_ref."""

    def __init__(self, connection) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS project_documents (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                revision BIGINT NOT NULL DEFAULT 1,
                document_json TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, document_id),
                UNIQUE (tenant_id, project_id, idempotency_key)
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS project_document_audit (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                revision BIGINT NOT NULL,
                event_type TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                occurred_at TIMESTAMPTZ NOT NULL,
                reason TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (tenant_id, project_id, document_id, revision)
            )"""
        )

    def persist(
        self,
        document: DocumentRecord,
        *,
        idempotency_key: str,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredDocument:
        document.validate()
        self._validate_metadata(idempotency_key, actor_id, occurred_at)
        fingerprint = self._fingerprint(document)
        existing = self._find_by_idempotency(document.tenant_id, document.project_id, idempotency_key)
        if existing is not None:
            if existing[1] != fingerprint:
                raise DocumentIdempotencyReuse("DOCUMENT_IDEMPOTENCY_KEY_REUSE")
            return self.get(document.tenant_id, document.project_id, existing[0])

        self.connection.execute(
            "INSERT INTO project_documents "
            "(tenant_id, project_id, document_id, idempotency_key, fingerprint, revision, document_json) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (
                document.tenant_id, document.project_id, document.document_id,
                idempotency_key, fingerprint, 1,
                json.dumps(document.as_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            ),
        )
        self.connection.execute(
            "INSERT INTO project_document_audit "
            "(tenant_id, project_id, document_id, revision, event_type, actor_id, occurred_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (document.tenant_id, document.project_id, document.document_id, 1, "created", actor_id, occurred_at),
        )
        return StoredDocument(document, 1)

    def get(self, tenant_id: str, project_id: str, document_id: str) -> StoredDocument:
        row = self.connection.execute(
            "SELECT document_json, revision FROM project_documents "
            "WHERE tenant_id=%s AND project_id=%s AND document_id=%s",
            (tenant_id, project_id, document_id),
        ).fetchone()
        if row is None:
            raise KeyError("DOCUMENT_NOT_FOUND")
        return StoredDocument(self._from_json(row[0]), int(row[1]))

    def update(
        self,
        document: DocumentRecord,
        *,
        expected_revision: int,
        actor_id: str,
        occurred_at: datetime,
        event_type: str = "updated",
        audit_reason: str = "",
    ) -> StoredDocument:
        document.validate()
        self._validate_metadata(event_type, actor_id, occurred_at)
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int):
            raise ValueError("INVALID_EXPECTED_DOCUMENT_REVISION")
        if expected_revision < 1 or expected_revision > MAX_SAFE_REVISION:
            raise ValueError("INVALID_EXPECTED_DOCUMENT_REVISION")

        row = self.connection.execute(
            "SELECT document_json, revision FROM project_documents "
            "WHERE tenant_id=%s AND project_id=%s AND document_id=%s FOR UPDATE",
            (document.tenant_id, document.project_id, document.document_id),
        ).fetchone()
        if row is None:
            raise KeyError("DOCUMENT_NOT_FOUND")
        current = int(row[1])
        if expected_revision != current:
            raise DocumentRevisionConflict("DOCUMENT_REVISION_CONFLICT")
        if current >= MAX_SAFE_REVISION:
            raise ValueError("DOCUMENT_REVISION_EXHAUSTED")

        next_revision = current + 1
        self.connection.execute(
            "UPDATE project_documents SET revision=%s, document_json=%s "
            "WHERE tenant_id=%s AND project_id=%s AND document_id=%s",
            (
                next_revision,
                json.dumps(document.as_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                document.tenant_id, document.project_id, document.document_id,
            ),
        )
        self.connection.execute(
            "INSERT INTO project_document_audit "
            "(tenant_id, project_id, document_id, revision, event_type, actor_id, occurred_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                document.tenant_id, document.project_id, document.document_id,
                next_revision, event_type, actor_id, occurred_at, audit_reason,
            ),
        )
        return StoredDocument(document, next_revision)

    def transition_status(
        self,
        document: DocumentRecord,
        *,
        expected_revision: int,
        actor_id: str,
        occurred_at: datetime,
        reason: str = "",
    ) -> StoredDocument:
        """Apply one explicit document lifecycle transition under optimistic locking."""
        current = self.get(document.tenant_id, document.project_id, document.document_id)
        allowed = DOCUMENT_APPROVAL_TRANSITIONS.get(current.document.status, set())
        if document.status not in allowed:
            raise DocumentApprovalTransitionError(
                f"DOCUMENT_INVALID_STATUS_TRANSITION:{current.document.status}->{document.status}"
            )
        transitioned = replace(current.document, status=document.status)
        return self.update(
            transitioned,
            expected_revision=expected_revision,
            actor_id=actor_id,
            occurred_at=occurred_at,
            event_type="status_transition",
            audit_reason=reason,
        )

class DocumentLifecycleService:
    """Application/use-case authorization boundary around the persistence store."""

    def __init__(self, store: PostgresDocumentStore, authorizer: DocumentLifecycleAuthorizer) -> None:
        self.store = store
        self.authorizer = authorizer

    def transition_status(self, document: DocumentRecord, *, expected_revision: int, actor_id: str, occurred_at: datetime, reason: str = "") -> StoredDocument:
        current = self.store.get(document.tenant_id, document.project_id, document.document_id)
        self.authorizer.authorize_transition(
            actor_id=actor_id,
            tenant_id=document.tenant_id,
            project_id=document.project_id,
            document_id=document.document_id,
            from_status=current.document.status,
            to_status=document.status,
        )
        return self.store.transition_status(document, expected_revision=expected_revision, actor_id=actor_id, occurred_at=occurred_at, reason=reason)


    def history(self, tenant_id: str, project_id: str, document_id: str):
        rows = self.connection.execute(
            "SELECT revision, event_type, actor_id, occurred_at, reason "
            "FROM project_document_audit "
            "WHERE tenant_id=%s AND project_id=%s AND document_id=%s ORDER BY revision",
            (tenant_id, project_id, document_id),
        ).fetchall()
        return tuple(
            DocumentAuditEvent(document_id, int(row[0]), row[1], row[2], row[3], row[4])
            for row in rows
        )

    def _find_by_idempotency(self, tenant_id: str, project_id: str, key: str):
        row = self.connection.execute(
            "SELECT document_id, fingerprint, revision FROM project_documents "
            "WHERE tenant_id=%s AND project_id=%s AND idempotency_key=%s",
            (tenant_id, project_id, key),
        ).fetchone()
        return None if row is None else (row[0], row[1], int(row[2]))

    @staticmethod
    def _fingerprint(document: DocumentRecord) -> str:
        return hashlib.sha256(
            json.dumps(document.as_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    @staticmethod
    def _validate_metadata(idempotency_key: str, actor_id: str, occurred_at: datetime) -> None:
        if not isinstance(idempotency_key, str) or not idempotency_key.strip():
            raise ValueError("INVALID_DOCUMENT_IDEMPOTENCY_KEY")
        if not isinstance(actor_id, str) or not actor_id.strip():
            raise ValueError("INVALID_DOCUMENT_ACTOR")
        if not isinstance(occurred_at, datetime) or occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
            raise ValueError("INVALID_DOCUMENT_AUDIT_TIMESTAMP")

    @staticmethod
    def _from_json(payload: str) -> DocumentRecord:
        data = json.loads(payload)
        return DocumentRecord(
            document_id=data["document_id"],
            tenant_id=data["tenant_id"],
            project_id=data["project_id"],
            resource_type=data["resource_type"],
            title=data["title"],
            status=data["status"],
            storage_ref=data["storage_ref"],
            content_hash=data["content_hash"],
            linked_entity_refs=tuple(data.get("linked_entity_refs", ())),
        )
