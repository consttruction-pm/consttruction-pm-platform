from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Mapping, Protocol


class ChangeClaimType(str, Enum):
    CHANGE = "change"
    VARIATION = "variation"
    NOTICE = "notice"
    CLAIM = "claim"


class ChangeClaimStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class ChangeClaimError(ValueError):
    pass


class ChangeClaimConflict(ChangeClaimError):
    pass


@dataclass(frozen=True)
class ChangeClaim:
    tenant_id: str
    project_id: str
    resource_id: str
    revision: int
    resource_type: ChangeClaimType
    status: ChangeClaimStatus
    actor_id: str
    occurred_at: str
    payload: Mapping[str, object]
    evidence_refs: tuple[str, ...] = ()

    def fingerprint(self) -> str:
        canonical = json.dumps({
            "tenant_id": self.tenant_id, "project_id": self.project_id,
            "resource_id": self.resource_id, "revision": self.revision,
            "resource_type": self.resource_type.value, "status": self.status.value,
            "actor_id": self.actor_id, "occurred_at": self.occurred_at,
            "payload": dict(self.payload), "evidence_refs": list(self.evidence_refs),
        }, sort_keys=True, separators=(",", ":"))
        return sha256(canonical.encode("utf-8")).hexdigest()

    def validate(self) -> None:
        for name, value in (
            ("tenant_id", self.tenant_id), ("project_id", self.project_id),
            ("resource_id", self.resource_id), ("actor_id", self.actor_id),
            ("occurred_at", self.occurred_at),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ChangeClaimError(f"INVALID_CHANGE_CLAIM_{name.upper()}")
        if isinstance(self.revision, bool) or not isinstance(self.revision, int) or self.revision < 0:
            raise ChangeClaimError("INVALID_CHANGE_CLAIM_REVISION")
        if not isinstance(self.resource_type, ChangeClaimType):
            raise ChangeClaimError("INVALID_CHANGE_CLAIM_TYPE")
        if not isinstance(self.status, ChangeClaimStatus):
            raise ChangeClaimError("INVALID_CHANGE_CLAIM_STATUS")
        if not isinstance(self.payload, Mapping):
            raise ChangeClaimError("INVALID_CHANGE_CLAIM_PAYLOAD")
        if not isinstance(self.evidence_refs, tuple) or any(
            not isinstance(ref, str) or not ref.strip() for ref in self.evidence_refs
        ):
            raise ChangeClaimError("INVALID_CHANGE_CLAIM_EVIDENCE_REFS")


@dataclass(frozen=True)
class ChangeClaimAudit:
    tenant_id: str
    project_id: str
    resource_id: str
    revision: int
    actor_id: str
    status: ChangeClaimStatus
    idempotency_key: str
    fingerprint: str


class ChangeClaimRepository(Protocol):
    def get(self, tenant_id: str, project_id: str, resource_id: str) -> ChangeClaim | None: ...
    def put(self, resource: ChangeClaim) -> None: ...
    def append_audit(self, audit: ChangeClaimAudit) -> None: ...
    def get_idempotency(self, tenant_id: str, project_id: str, key: str) -> ChangeClaimAudit | None: ...
    def put_idempotency(self, audit: ChangeClaimAudit) -> None: ...


class InMemoryChangeClaimRepository:
    def __init__(self) -> None:
        self.resources: dict[tuple[str, str, str], ChangeClaim] = {}
        self.audits: list[ChangeClaimAudit] = []
        self.idempotency: dict[tuple[str, str, str], ChangeClaimAudit] = {}

    def get(self, tenant_id, project_id, resource_id):
        return self.resources.get((tenant_id, project_id, resource_id))

    def put(self, resource):
        resource.validate()
        self.resources[(resource.tenant_id, resource.project_id, resource.resource_id)] = resource

    def append_audit(self, audit):
        self.audits.append(audit)

    def get_idempotency(self, tenant_id, project_id, key):
        return self.idempotency.get((tenant_id, project_id, key))

    def put_idempotency(self, audit):
        self.idempotency[(audit.tenant_id, audit.project_id, audit.idempotency_key)] = audit


class ChangeClaimService:
    def __init__(self, repository: ChangeClaimRepository) -> None:
        self.repository = repository

    def upsert(
        self,
        resource: ChangeClaim,
        *,
        expected_revision: int,
        idempotency_key: str,
    ) -> ChangeClaim:
        resource.validate()
        if resource.revision != expected_revision:
            raise ChangeClaimConflict("CHANGE_CLAIM_REVISION_CONFLICT")
        existing_key = self.repository.get_idempotency(
            resource.tenant_id, resource.project_id, idempotency_key
        )
        if existing_key is not None:
            if existing_key.fingerprint != resource.fingerprint():
                raise ChangeClaimConflict("CHANGE_CLAIM_IDEMPOTENCY_KEY_REUSE")
            existing = self.repository.get(
                resource.tenant_id, resource.project_id, resource.resource_id
            )
            if existing is None:
                raise ChangeClaimConflict("CHANGE_CLAIM_IDEMPOTENCY_RECORD_MISSING")
            return existing
        current = self.repository.get(
            resource.tenant_id, resource.project_id, resource.resource_id
        )
        actual_revision = 0 if current is None else current.revision
        if actual_revision != expected_revision:
            raise ChangeClaimConflict("CHANGE_CLAIM_REVISION_CONFLICT")
        self.repository.put(resource)
        audit = ChangeClaimAudit(
            resource.tenant_id, resource.project_id, resource.resource_id,
            resource.revision, resource.actor_id, resource.status,
            idempotency_key, resource.fingerprint(),
        )
        self.repository.append_audit(audit)
        self.repository.put_idempotency(audit)
        return resource


from contextlib import AbstractContextManager
from typing import Any

class ChangeClaimIdempotencyReuse(ChangeClaimConflict):
    pass

class ChangeClaimRevisionConflict(ChangeClaimConflict):
    pass

@dataclass(frozen=True)
class StoredChangeClaim:
    resource: ChangeClaim
    project_revision: int

class ChangeClaimConnection(Protocol):
    def execute(self, sql: str, params: tuple[Any, ...] = ()): ...
    def transaction(self) -> AbstractContextManager[None]: ...

@dataclass
class PostgresChangeClaimStore:
    connection: ChangeClaimConnection

    def initialize(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS project_change_revisions "
            "(tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, revision BIGINT NOT NULL, "
            "PRIMARY KEY (tenant_id, project_id))"
        )
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS project_change_claims "
            "(tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, resource_id TEXT NOT NULL, "
            "idempotency_key TEXT NOT NULL, fingerprint TEXT NOT NULL, project_revision BIGINT NOT NULL, "
            "resource_json TEXT NOT NULL, PRIMARY KEY (tenant_id, project_id, resource_id), "
            "UNIQUE (tenant_id, project_id, idempotency_key))"
        )
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS project_change_claim_audit "
            "(tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, resource_id TEXT NOT NULL, "
            "project_revision BIGINT NOT NULL, actor_id TEXT NOT NULL, status TEXT NOT NULL, "
            "idempotency_key TEXT NOT NULL, occurred_at TEXT NOT NULL, "
            "PRIMARY KEY (tenant_id, project_id, resource_id, project_revision))"
        )

    def ensure_project(self, tenant_id: str, project_id: str) -> None:
        self.connection.execute(
            "INSERT INTO project_change_revisions (tenant_id, project_id, revision) "
            "VALUES (%s,%s,0) ON CONFLICT (tenant_id, project_id) DO NOTHING",
            (tenant_id, project_id),
        )

    def persist(self, resource: ChangeClaim, *, expected_project_revision: int, idempotency_key: str) -> StoredChangeClaim:
        resource.validate()
        if not idempotency_key.strip():
            raise ChangeClaimError("INVALID_CHANGE_CLAIM_IDEMPOTENCY_KEY")
        with self.connection.transaction():
            row = self.connection.execute(
                "SELECT revision FROM project_change_revisions WHERE tenant_id=%s AND project_id=%s FOR UPDATE",
                (resource.tenant_id, resource.project_id),
            ).fetchone()
            if row is None:
                raise ChangeClaimError("CHANGE_CLAIM_PROJECT_NOT_INITIALIZED")
            existing = self._find_idempotency(resource.tenant_id, resource.project_id, idempotency_key)
            fingerprint = resource.fingerprint()
            if existing is not None:
                old_fingerprint, old_json, old_revision = existing
                if old_fingerprint != fingerprint:
                    raise ChangeClaimIdempotencyReuse("CHANGE_CLAIM_IDEMPOTENCY_KEY_REUSE")
                return StoredChangeClaim(_from_json(old_json), old_revision)
            current = row[0]
            if current != expected_project_revision:
                raise ChangeClaimRevisionConflict(
                    f"CHANGE_CLAIM_REVISION_CONFLICT expected={expected_project_revision} actual={current}"
                )
            next_revision = current + 1
            payload = json.dumps(
                {
                    "tenant_id": resource.tenant_id, "project_id": resource.project_id,
                    "resource_id": resource.resource_id, "revision": resource.revision,
                    "resource_type": resource.resource_type.value, "status": resource.status.value,
                    "actor_id": resource.actor_id, "occurred_at": resource.occurred_at,
                    "payload": dict(resource.payload), "evidence_refs": list(resource.evidence_refs),
                },
                sort_keys=True, separators=(",", ":")
            )
            self.connection.execute(
                "UPDATE project_change_revisions SET revision=%s "
                "WHERE tenant_id=%s AND project_id=%s AND revision=%s",
                (next_revision, resource.tenant_id, resource.project_id, current),
            )
            self.connection.execute(
                "INSERT INTO project_change_claims "
                "(tenant_id, project_id, resource_id, idempotency_key, fingerprint, project_revision, resource_json) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (resource.tenant_id, resource.project_id, resource.resource_id, idempotency_key,
                 fingerprint, next_revision, payload),
            )
            self.connection.execute(
                "INSERT INTO project_change_claim_audit "
                "(tenant_id, project_id, resource_id, project_revision, actor_id, status, idempotency_key, occurred_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (resource.tenant_id, resource.project_id, resource.resource_id, next_revision,
                 resource.actor_id, resource.status.value, idempotency_key, resource.occurred_at),
            )
            return StoredChangeClaim(resource, next_revision)

    def get(self, tenant_id: str, project_id: str, resource_id: str) -> StoredChangeClaim | None:
        row = self.connection.execute(
            "SELECT resource_json, project_revision FROM project_change_claims "
            "WHERE tenant_id=%s AND project_id=%s AND resource_id=%s",
            (tenant_id, project_id, resource_id),
        ).fetchone()
        if row is None:
            return None
        return StoredChangeClaim(_from_json(row[0]), row[1])

    def _find_idempotency(self, tenant_id: str, project_id: str, key: str):
        row = self.connection.execute(
            "SELECT fingerprint, resource_json, project_revision FROM project_change_claims "
            "WHERE tenant_id=%s AND project_id=%s AND idempotency_key=%s",
            (tenant_id, project_id, key),
        ).fetchone()
        return None if row is None else (row[0], row[1], row[2])


def _from_json(payload: str) -> ChangeClaim:
    data = json.loads(payload)
    return ChangeClaim(
        tenant_id=data["tenant_id"], project_id=data["project_id"],
        resource_id=data["resource_id"], revision=int(data["revision"]),
        resource_type=ChangeClaimType(data["resource_type"]),
        status=ChangeClaimStatus(data["status"]),
        actor_id=data["actor_id"], occurred_at=data["occurred_at"],
        payload=dict(data["payload"]), evidence_refs=tuple(data.get("evidence_refs", ())),
    )
