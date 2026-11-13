"""Retention policy, eligibility and deliberate content disposition.

Retention is per document. A policy states how many days a content version is
kept and whether a legal hold prevents disposition. Eligibility is computed,
never assumed: a version is eligible only when the hold is clear and the
retention window has elapsed. Disposition is a separate, explicitly confirmed
action that deletes the object bytes and records an append-only disposition so
downloads can be refused afterwards.

Nothing here runs on a timer. A deployment may call ``plan`` for reporting and
must invoke ``dispose`` deliberately through the authorized API.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol

from .api_errors import (
    APIError,
    authorization_error,
    conflict_error,
    persistence_error,
    validation_error,
)
from .document_persistence import DocumentAuthorizationError
from .document_storage import DocumentContentNotFound, DocumentContentQuarantined

MAX_RETENTION_DAYS = 36_500
MAX_RETENTION_REASON = 500


class DocumentRetentionError(ValueError):
    pass


class DocumentRetentionNotFound(DocumentRetentionError):
    pass


class DocumentRetentionRevisionConflict(DocumentRetentionError):
    pass


class DocumentRetentionLegalHold(DocumentRetentionError):
    pass


class DocumentRetentionNotEligible(DocumentRetentionError):
    pass


class DocumentContentAlreadyDisposed(DocumentRetentionError):
    pass


class DocumentContentDisposed(DocumentRetentionError):
    """The bytes were deliberately removed under retention; do not serve."""


def _iso(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise DocumentRetentionError("INVALID_DOCUMENT_RETENTION_TIMESTAMP")
    return value.astimezone(timezone.utc).isoformat()


def _parse(value: object) -> datetime:
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class DocumentRetentionPolicy:
    tenant_id: str
    project_id: str
    document_id: str
    retain_days: int
    legal_hold: bool
    reason: str
    updated_by: str
    updated_at: datetime
    revision: int = 1

    def validate(self) -> None:
        for name, value in (
            ("TENANT_ID", self.tenant_id),
            ("PROJECT_ID", self.project_id),
            ("DOCUMENT_ID", self.document_id),
            ("UPDATED_BY", self.updated_by),
        ):
            if not isinstance(value, str) or not value.strip():
                raise DocumentRetentionError(f"INVALID_DOCUMENT_RETENTION_{name}")
        if (
            isinstance(self.retain_days, bool)
            or not isinstance(self.retain_days, int)
            or not 0 <= self.retain_days <= MAX_RETENTION_DAYS
        ):
            raise DocumentRetentionError("INVALID_DOCUMENT_RETENTION_DAYS")
        if not isinstance(self.legal_hold, bool):
            raise DocumentRetentionError("INVALID_DOCUMENT_RETENTION_LEGAL_HOLD")
        if (
            not isinstance(self.reason, str)
            or not self.reason.strip()
            or len(self.reason) > MAX_RETENTION_REASON
        ):
            raise DocumentRetentionError("INVALID_DOCUMENT_RETENTION_REASON")
        if (
            isinstance(self.revision, bool)
            or not isinstance(self.revision, int)
            or self.revision < 1
        ):
            raise DocumentRetentionError("INVALID_DOCUMENT_RETENTION_REVISION")

    def as_dict(self) -> dict[str, object]:
        return {
            "document_id": self.document_id,
            "retain_days": self.retain_days,
            "legal_hold": self.legal_hold,
            "reason": self.reason,
            "updated_by": self.updated_by,
            "updated_at": _iso(self.updated_at),
            "revision": self.revision,
        }


@dataclass(frozen=True)
class DocumentDisposition:
    tenant_id: str
    project_id: str
    document_id: str
    version: int
    content_hash: str
    reason: str
    actor_id: str
    disposed_at: datetime

    def validate(self) -> None:
        for name, value in (
            ("TENANT_ID", self.tenant_id),
            ("PROJECT_ID", self.project_id),
            ("DOCUMENT_ID", self.document_id),
            ("CONTENT_HASH", self.content_hash),
            ("REASON", self.reason),
            ("ACTOR_ID", self.actor_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise DocumentRetentionError(f"INVALID_DOCUMENT_DISPOSITION_{name}")
        if not self.content_hash.startswith("sha256:") or len(self.content_hash) != 71:
            raise DocumentRetentionError("INVALID_DOCUMENT_DISPOSITION_HASH")
        if not isinstance(self.disposed_at, datetime) or self.disposed_at.tzinfo is None:
            raise DocumentRetentionError("INVALID_DOCUMENT_DISPOSITION_TIMESTAMP")
        if (
            isinstance(self.version, bool)
            or not isinstance(self.version, int)
            or self.version < 1
        ):
            raise DocumentRetentionError("INVALID_DOCUMENT_DISPOSITION_VERSION")

    def as_dict(self) -> dict[str, object]:
        return {
            "document_id": self.document_id,
            "version": self.version,
            "content_hash": self.content_hash,
            "reason": self.reason,
            "actor_id": self.actor_id,
            "disposed_at": _iso(self.disposed_at),
        }


@dataclass(frozen=True)
class RetentionEligibility:
    version: int
    uploaded_at: datetime
    expires_at: datetime
    eligible: bool
    reason: str

    def as_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "uploaded_at": _iso(self.uploaded_at),
            "expires_at": _iso(self.expires_at),
            "eligible": self.eligible,
            "reason": self.reason,
        }


class DocumentRetentionStore(Protocol):
    def get_policy(
        self, tenant_id: str, project_id: str, document_id: str
    ) -> DocumentRetentionPolicy | None: ...

    def set_policy(
        self, policy: DocumentRetentionPolicy, *, expected_revision: int
    ) -> DocumentRetentionPolicy: ...

    def get_disposition(
        self, tenant_id: str, project_id: str, document_id: str, version: int
    ) -> DocumentDisposition | None: ...

    def list_dispositions(
        self, tenant_id: str, project_id: str, document_id: str
    ) -> tuple[DocumentDisposition, ...]: ...

    def list_all_policies(
        self,
        *,
        tenant_id: str | None = None,
        project_id: str | None = None,
    ) -> tuple[DocumentRetentionPolicy, ...]: ...

    def list_all_dispositions(
        self,
        *,
        tenant_id: str | None = None,
        project_id: str | None = None,
    ) -> tuple[DocumentDisposition, ...]: ...

    def record_disposition(
        self, disposition: DocumentDisposition
    ) -> DocumentDisposition: ...


class _DocumentRetentionStore:
    placeholder = "?"

    def __init__(self, connection) -> None:
        self.connection = connection

    @property
    def q(self) -> str:
        return self.placeholder

    def initialize(self) -> None:
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS project_document_retention (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                retain_days INTEGER NOT NULL,
                legal_hold INTEGER NOT NULL,
                reason TEXT NOT NULL,
                updated_by TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                revision INTEGER NOT NULL,
                PRIMARY KEY (tenant_id, project_id, document_id)
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS project_document_disposition (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                version BIGINT NOT NULL,
                content_hash TEXT NOT NULL,
                reason TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                disposed_at TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, document_id, version)
            )"""
        )

    def _policy(self, row) -> DocumentRetentionPolicy:
        return DocumentRetentionPolicy(
            tenant_id=row[0],
            project_id=row[1],
            document_id=row[2],
            retain_days=int(row[3]),
            legal_hold=bool(row[4]),
            reason=row[5],
            updated_by=row[6],
            updated_at=_parse(row[7]),
            revision=int(row[8]),
        )

    def _disposition(self, row) -> DocumentDisposition:
        return DocumentDisposition(
            tenant_id=row[0],
            project_id=row[1],
            document_id=row[2],
            version=int(row[3]),
            content_hash=row[4],
            reason=row[5],
            actor_id=row[6],
            disposed_at=_parse(row[7]),
        )

    def get_policy(self, tenant_id: str, project_id: str, document_id: str):
        rows = self.connection.execute(
            f"""SELECT tenant_id, project_id, document_id, retain_days, legal_hold,
                       reason, updated_by, updated_at, revision
                FROM project_document_retention
                WHERE tenant_id={self.q} AND project_id={self.q}
                  AND document_id={self.q}""",
            (tenant_id, project_id, document_id),
        ).fetchall()
        return None if not rows else self._policy(rows[0])

    def set_policy(
        self, policy: DocumentRetentionPolicy, *, expected_revision: int
    ) -> DocumentRetentionPolicy:
        policy.validate()
        if (
            isinstance(expected_revision, bool)
            or not isinstance(expected_revision, int)
            or expected_revision < 0
        ):
            raise DocumentRetentionError("INVALID_DOCUMENT_RETENTION_REVISION")
        existing = self.get_policy(
            policy.tenant_id, policy.project_id, policy.document_id
        )
        if existing is None:
            if expected_revision != 0:
                raise DocumentRetentionRevisionConflict(
                    "DOCUMENT_RETENTION_REVISION_CONFLICT"
                )
            cur = self.connection.execute(
                f"""INSERT INTO project_document_retention
                    (tenant_id, project_id, document_id, retain_days,
                     legal_hold, reason, updated_by, updated_at, revision)
                    VALUES ({", ".join([self.q] * 9)})
                    ON CONFLICT (tenant_id, project_id, document_id) DO NOTHING""",
                (
                    policy.tenant_id,
                    policy.project_id,
                    policy.document_id,
                    policy.retain_days,
                    1 if policy.legal_hold else 0,
                    policy.reason,
                    policy.updated_by,
                    _iso(policy.updated_at),
                    1,
                ),
            )
            if cur.rowcount != 1:
                raise DocumentRetentionRevisionConflict(
                    "DOCUMENT_RETENTION_REVISION_CONFLICT"
                )
        else:
            if existing.revision != expected_revision:
                raise DocumentRetentionRevisionConflict(
                    "DOCUMENT_RETENTION_REVISION_CONFLICT"
                )
            cur = self.connection.execute(
                f"""UPDATE project_document_retention
                    SET retain_days={self.q}, legal_hold={self.q}, reason={self.q},
                        updated_by={self.q}, updated_at={self.q},
                        revision=revision + 1
                    WHERE tenant_id={self.q} AND project_id={self.q}
                      AND document_id={self.q} AND revision={self.q}""",
                (
                    policy.retain_days,
                    1 if policy.legal_hold else 0,
                    policy.reason,
                    policy.updated_by,
                    _iso(policy.updated_at),
                    policy.tenant_id,
                    policy.project_id,
                    policy.document_id,
                    expected_revision,
                ),
            )
            if cur.rowcount != 1:
                raise DocumentRetentionRevisionConflict(
                    "DOCUMENT_RETENTION_REVISION_CONFLICT"
                )
        stored = self.get_policy(
            policy.tenant_id, policy.project_id, policy.document_id
        )
        if stored is None:
            raise DocumentRetentionError("DOCUMENT_RETENTION_WRITE_FAILED")
        return stored

    def get_disposition(
        self, tenant_id: str, project_id: str, document_id: str, version: int
    ):
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            return None
        rows = self.connection.execute(
            f"""SELECT tenant_id, project_id, document_id, version, content_hash,
                       reason, actor_id, disposed_at
                FROM project_document_disposition
                WHERE tenant_id={self.q} AND project_id={self.q}
                  AND document_id={self.q} AND version={self.q}""",
            (tenant_id, project_id, document_id, version),
        ).fetchall()
        return None if not rows else self._disposition(rows[0])

    def list_dispositions(
        self, tenant_id: str, project_id: str, document_id: str
    ) -> tuple[DocumentDisposition, ...]:
        rows = self.connection.execute(
            f"""SELECT tenant_id, project_id, document_id, version, content_hash,
                       reason, actor_id, disposed_at
                FROM project_document_disposition
                WHERE tenant_id={self.q} AND project_id={self.q}
                  AND document_id={self.q} ORDER BY version""",
            (tenant_id, project_id, document_id),
        ).fetchall()
        return tuple(self._disposition(row) for row in rows)

    def list_all_policies(
        self, *, tenant_id: str | None = None, project_id: str | None = None
    ) -> tuple[DocumentRetentionPolicy, ...]:
        statement = (
            "SELECT tenant_id, project_id, document_id, retain_days, legal_hold, "
            "reason, updated_by, updated_at, revision FROM project_document_retention"
        )
        clauses: list[str] = []
        parameters: list[object] = []
        if tenant_id is not None:
            clauses.append(f"tenant_id={self.q}")
            parameters.append(tenant_id)
        if project_id is not None:
            clauses.append(f"project_id={self.q}")
            parameters.append(project_id)
        if clauses:
            statement += " WHERE " + " AND ".join(clauses)
        statement += " ORDER BY tenant_id, project_id, document_id"
        rows = self.connection.execute(statement, tuple(parameters)).fetchall()
        return tuple(self._policy(row) for row in rows)

    def list_all_dispositions(
        self, *, tenant_id: str | None = None, project_id: str | None = None
    ) -> tuple[DocumentDisposition, ...]:
        statement = (
            "SELECT tenant_id, project_id, document_id, version, content_hash, "
            "reason, actor_id, disposed_at FROM project_document_disposition"
        )
        clauses: list[str] = []
        parameters: list[object] = []
        if tenant_id is not None:
            clauses.append(f"tenant_id={self.q}")
            parameters.append(tenant_id)
        if project_id is not None:
            clauses.append(f"project_id={self.q}")
            parameters.append(project_id)
        if clauses:
            statement += " WHERE " + " AND ".join(clauses)
        statement += " ORDER BY tenant_id, project_id, document_id, version"
        rows = self.connection.execute(statement, tuple(parameters)).fetchall()
        return tuple(self._disposition(row) for row in rows)

    def record_disposition(self, disposition: DocumentDisposition) -> DocumentDisposition:
        disposition.validate()
        existing = self.get_disposition(
            disposition.tenant_id,
            disposition.project_id,
            disposition.document_id,
            disposition.version,
        )
        if existing is not None:
            raise DocumentContentAlreadyDisposed("DOCUMENT_CONTENT_ALREADY_DISPOSED")
        cur = self.connection.execute(
            f"""INSERT INTO project_document_disposition
                (tenant_id, project_id, document_id, version, content_hash,
                 reason, actor_id, disposed_at)
                VALUES ({", ".join([self.q] * 8)})
                ON CONFLICT (tenant_id, project_id, document_id, version)
                DO NOTHING""",
            (
                disposition.tenant_id,
                disposition.project_id,
                disposition.document_id,
                disposition.version,
                disposition.content_hash,
                disposition.reason,
                disposition.actor_id,
                _iso(disposition.disposed_at),
            ),
        )
        if cur.rowcount != 1:
            raise DocumentContentAlreadyDisposed("DOCUMENT_CONTENT_ALREADY_DISPOSED")
        return disposition


class SQLiteDocumentRetentionStore(_DocumentRetentionStore):
    placeholder = "?"


class PostgresDocumentRetentionStore(_DocumentRetentionStore):
    placeholder = "%s"


class DocumentRetentionService:
    def __init__(
        self,
        store: _DocumentRetentionStore,
        content_repository,
        document_store,
        storage,
        authorization_policy,
    ) -> None:
        self.store = store
        self.content_repository = content_repository
        self.document_store = document_store
        self.storage = storage
        self.authorization_policy = authorization_policy

    def read(
        self,
        *,
        tenant_id: str,
        project_id: str,
        document_id: str,
        context,
        now: datetime | None = None,
    ) -> dict[str, object]:
        from .application.authorization import Permission

        self._check(context, tenant_id, project_id, Permission.PROJECT_READ)
        self.document_store.get(tenant_id, project_id, document_id)
        policy = self.store.get_policy(tenant_id, project_id, document_id)
        return {
            "policy": None if policy is None else policy.as_dict(),
            "dispositions": [
                item.as_dict()
                for item in self.store.list_dispositions(
                    tenant_id, project_id, document_id
                )
            ],
            "eligibility": self._eligibility(
                tenant_id,
                project_id,
                document_id,
                policy,
                datetime.now(timezone.utc) if now is None else now,
            ),
        }

    def plan(
        self, *, tenant_id: str, project_id: str, document_id: str, context, now: datetime
    ) -> dict[str, object]:
        from .application.authorization import Permission

        self._check(context, tenant_id, project_id, Permission.PROJECT_READ)
        self.document_store.get(tenant_id, project_id, document_id)
        policy = self.store.get_policy(tenant_id, project_id, document_id)
        return {
            "policy": None if policy is None else policy.as_dict(),
            "eligibility": self._eligibility(
                tenant_id, project_id, document_id, policy, now
            ),
        }

    def set_policy(
        self,
        *,
        tenant_id: str,
        project_id: str,
        document_id: str,
        retain_days: int,
        legal_hold: bool,
        reason: str,
        expected_revision: int,
        context,
        actor_id: str,
        occurred_at: datetime,
    ) -> DocumentRetentionPolicy:
        from .application.authorization import Permission

        self._check(context, tenant_id, project_id, Permission.PROJECT_WRITE)
        if actor_id != context.user_id:
            raise DocumentAuthorizationError("DOCUMENT_ACTOR_MISMATCH")
        stored = self.document_store.get(tenant_id, project_id, document_id)
        policy = DocumentRetentionPolicy(
            tenant_id=tenant_id,
            project_id=project_id,
            document_id=document_id,
            retain_days=retain_days,
            legal_hold=legal_hold,
            reason=reason,
            updated_by=actor_id,
            updated_at=occurred_at,
            revision=1,
        )
        policy.validate()
        created = self.store.set_policy(policy, expected_revision=expected_revision)
        self.document_store.update(
            stored.document,
            expected_revision=stored.revision,
            actor_id=actor_id,
            occurred_at=occurred_at,
            event_type="retention_updated",
            audit_reason=reason,
        )
        return created

    def dispose(
        self,
        *,
        tenant_id: str,
        project_id: str,
        document_id: str,
        version: int,
        confirm: str,
        reason: str,
        context,
        actor_id: str,
        occurred_at: datetime,
    ) -> DocumentDisposition:
        from .application.authorization import Permission

        self._check(context, tenant_id, project_id, Permission.PROJECT_WRITE)
        if actor_id != context.user_id:
            raise DocumentAuthorizationError("DOCUMENT_ACTOR_MISMATCH")
        if confirm != f"{document_id}:{version}":
            raise DocumentRetentionError(
                "INVALID_DOCUMENT_DISPOSITION_CONFIRMATION"
            )
        policy = self.store.get_policy(tenant_id, project_id, document_id)
        if policy is None:
            raise DocumentRetentionNotFound("DOCUMENT_RETENTION_NOT_FOUND")
        if policy.legal_hold:
            raise DocumentRetentionLegalHold("DOCUMENT_RETENTION_LEGAL_HOLD")
        content = self.content_repository.get(
            tenant_id, project_id, document_id, version
        )
        if content is None:
            raise DocumentRetentionNotFound("DOCUMENT_CONTENT_NOT_FOUND")
        if self.store.get_disposition(
            tenant_id, project_id, document_id, version
        ) is not None:
            raise DocumentContentAlreadyDisposed("DOCUMENT_CONTENT_ALREADY_DISPOSED")
        expires_at = content.uploaded_at + timedelta(days=policy.retain_days)
        if occurred_at < expires_at:
            raise DocumentRetentionNotEligible("DOCUMENT_RETENTION_NOT_ELIGIBLE")
        disposition = DocumentDisposition(
            tenant_id=tenant_id,
            project_id=project_id,
            document_id=document_id,
            version=version,
            content_hash=content.content_hash,
            reason=reason,
            actor_id=actor_id,
            disposed_at=occurred_at,
        )
        disposition.validate()
        try:
            self.storage.delete(
                content.storage_ref,
                tenant_id=tenant_id,
                project_id=project_id,
            )
        except DocumentContentNotFound:
            pass
        return self.store.record_disposition(disposition)

    def _eligibility(self, tenant_id, project_id, document_id, policy, now):
        versions = self.content_repository.list(tenant_id, project_id, document_id)
        items: list[dict[str, object]] = []
        for content in versions:
            disposed = self.store.get_disposition(
                tenant_id, project_id, document_id, content.version
            )
            expires_at = content.uploaded_at + timedelta(
                days=0 if policy is None else policy.retain_days
            )
            if disposed is not None:
                eligible, reason = False, "disposed"
            elif policy is None:
                eligible, reason = False, "no_policy"
            elif policy.legal_hold:
                eligible, reason = False, "legal_hold"
            elif now < expires_at:
                eligible, reason = False, "not_yet_due"
            else:
                eligible, reason = True, "eligible"
            items.append(
                RetentionEligibility(
                    version=content.version,
                    uploaded_at=content.uploaded_at,
                    expires_at=expires_at,
                    eligible=eligible,
                    reason=reason,
                ).as_dict()
            )
        return items

    def _check(self, context, tenant_id, project_id, permission) -> None:
        if context.tenant_id != tenant_id or context.project_id != project_id:
            raise DocumentAuthorizationError("DOCUMENT_CROSS_SCOPE")
        if not context.user_id.strip():
            raise DocumentAuthorizationError("DOCUMENT_ACTOR_REQUIRED")
        if not self.authorization_policy.is_allowed(context, permission):
            raise DocumentAuthorizationError("DOCUMENT_PERMISSION_DENIED")

    @staticmethod
    def error_dto(exc: Exception) -> APIError:
        if isinstance(exc, KeyError):
            code = str(exc.args[0]) if exc.args else "DOCUMENT_NOT_FOUND"
            return validation_error(code, code)
        if isinstance(exc, DocumentRetentionNotFound):
            return validation_error(str(exc) or "DOCUMENT_RETENTION_NOT_FOUND", str(exc))
        if isinstance(exc, DocumentRetentionRevisionConflict):
            return conflict_error(
                str(exc) or "DOCUMENT_RETENTION_REVISION_CONFLICT", str(exc)
            )
        if isinstance(
            exc,
            (
                DocumentRetentionLegalHold,
                DocumentRetentionNotEligible,
                DocumentContentAlreadyDisposed,
                DocumentContentDisposed,
            ),
        ):
            return conflict_error(str(exc) or type(exc).__name__, str(exc))
        if isinstance(exc, DocumentContentQuarantined):
            return conflict_error(
                str(exc) or "DOCUMENT_CONTENT_QUARANTINED", str(exc)
            )
        if isinstance(exc, DocumentAuthorizationError):
            return authorization_error(str(exc), str(exc))
        if isinstance(exc, DocumentRetentionError):
            return validation_error(str(exc) or type(exc).__name__, str(exc))
        if isinstance(exc, ValueError):
            return validation_error(str(exc) or type(exc).__name__, str(exc))
        return persistence_error(type(exc).__name__, str(exc))


__all__ = [
    "MAX_RETENTION_DAYS",
    "DocumentContentAlreadyDisposed",
    "DocumentContentDisposed",
    "DocumentDisposition",
    "DocumentRetentionError",
    "DocumentRetentionLegalHold",
    "DocumentRetentionNotEligible",
    "DocumentRetentionNotFound",
    "DocumentRetentionPolicy",
    "DocumentRetentionRevisionConflict",
    "DocumentRetentionService",
    "DocumentRetentionStore",
    "PostgresDocumentRetentionStore",
    "RetentionEligibility",
    "SQLiteDocumentRetentionStore",
]
