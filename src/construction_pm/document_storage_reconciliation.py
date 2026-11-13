"""Reconcile document metadata with the object store, and clean up safely.

Document metadata (SQLite/PostgreSQL) and object bytes (local disk/S3) are two
systems that drift. An upload can leave staging bytes behind, a metadata row can
survive the loss of its object, an object can exist without a committed row, or
stored bytes can be replaced. This module classifies that drift, reports it in
machine-readable form, and removes bytes only when every safety condition holds.

Safety properties, in the order they are enforced:

* The metadata snapshot is read *first*. Any failure aborts the pass before the
  object store is listed, so a database outage can never look like "every
  object is an orphan".
* Dry-run is the default and performs no writes to either system.
* A single pass can never delete. ``min_observations`` is validated to be at
  least two, and the destructive claim re-checks observation count, grace and
  lease inside the same conditional SQL statement.
* An object is deleted only when its tenant/project scope hash maps to exactly
  one metadata scope. Objects outside any known scope are reported as
  ``unknown_object`` and never deleted.
* A version that retention disposed protects the bytes only while no live
  version still references them; a legal hold always wins.
* A lease is committed before the external delete, so competing reconcilers
  cannot both delete the same object and a crash leaves evidence behind.
* Every outcome appends an immutable cleanup record with actor, reason, object
  identity, checksum, status, attempt and timestamps.

Reports expose document identities, versions and opaque object handles only.
Storage references, filesystem paths, bucket names, credentials and payloads
are never emitted or logged.
"""

from __future__ import annotations

import hashlib
import os
import re
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from time import monotonic
from typing import Iterable, Protocol

from .document_content_repository import DocumentContentVersion
from .document_object_storage import (
    S3_STORAGE_REF_PREFIX,
    S3CompatibleDocumentStorage,
)
from .document_retention import DocumentDisposition, DocumentRetentionPolicy
from .document_storage import (
    DEFAULT_MAX_DOCUMENT_BYTES,
    STORAGE_REF_PREFIX,
    DocumentStorageError,
    storage_scope_key,
)
from .observability import OperationalMetrics

MATCH = "match"
METADATA_ONLY = "metadata_only"
ORPHAN_OBJECT = "orphan_object"
CHECKSUM_MISMATCH = "checksum_mismatch"
SIZE_MISMATCH = "size_mismatch"
INCOMPLETE_UPLOAD = "incomplete_upload"
PENDING_DELETION = "pending_deletion"
UNKNOWN_OBJECT = "unknown_object"
RETENTION_PROTECTED = "retention_protected"
UNAVAILABLE = "unavailable"

CLASSIFICATIONS = (
    MATCH,
    METADATA_ONLY,
    ORPHAN_OBJECT,
    CHECKSUM_MISMATCH,
    SIZE_MISMATCH,
    INCOMPLETE_UPLOAD,
    PENDING_DELETION,
    UNKNOWN_OBJECT,
    RETENTION_PROTECTED,
    UNAVAILABLE,
)

# Only these classes are ever candidates for destructive cleanup.
DELETABLE_CLASSIFICATIONS = frozenset(
    {ORPHAN_OBJECT, INCOMPLETE_UPLOAD, PENDING_DELETION}
)

ELIGIBLE = "eligible"
AWAITING_REPEATED_OBSERVATION = "awaiting_repeated_observation"
IN_GRACE_PERIOD = "in_grace_period"
NOT_APPLICABLE = "not_applicable"

COMPLETED = "completed"
ABORTED = "aborted"

STAGING_PREFIX = ".upload-"
_HEX16 = re.compile(r"^[0-9a-f]{16}$")
_HEX2 = re.compile(r"^[0-9a-f]{2}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_SAFE_EXTENSION = re.compile(r"^\.[a-z0-9]{1,8}$")
MAX_ERROR_DETAIL = 300
MAX_ACTOR_LENGTH = 200
MAX_REASON_LENGTH = 500


class DocumentStorageReconciliationError(ValueError):
    pass


class DocumentStorageInventoryError(DocumentStorageError):
    """The object inventory could not be read; abort the pass."""


def _iso(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise DocumentStorageReconciliationError("INVALID_RECONCILIATION_TIMESTAMP")
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds")


def _parse(value: object) -> datetime:
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _error_detail(exc: BaseException) -> str:
    """Bound the recorded error and never copy a filesystem path or URL."""
    if isinstance(exc, DocumentStorageError):
        text = str(exc) or type(exc).__name__
    else:
        text = type(exc).__name__
    return text[:MAX_ERROR_DETAIL]


def object_handle(object_ref: str) -> str:
    """Non-reversible correlation handle; never the storage reference itself."""
    return hashlib.sha256(object_ref.encode("utf-8")).hexdigest()[:16]


# --------------------------------------------------------------------------
# policy and inventory
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ReconciliationPolicy:
    """Bounds that make a destructive pass impossible in one observation."""

    grace_period: timedelta = timedelta(hours=24)
    min_observations: int = 2
    verify_bytes: bool = False
    lease_seconds: int = 300
    max_objects: int = 5_000

    def validate(self) -> None:
        if not isinstance(self.grace_period, timedelta) or self.grace_period < timedelta(0):
            raise DocumentStorageReconciliationError("INVALID_RECONCILIATION_GRACE_PERIOD")
        if (
            isinstance(self.min_observations, bool)
            or not isinstance(self.min_observations, int)
            or self.min_observations < 2
        ):
            raise DocumentStorageReconciliationError(
                "INVALID_RECONCILIATION_MIN_OBSERVATIONS"
            )
        if not isinstance(self.verify_bytes, bool):
            raise DocumentStorageReconciliationError("INVALID_RECONCILIATION_BYTE_VERIFICATION")
        if (
            isinstance(self.lease_seconds, bool)
            or not isinstance(self.lease_seconds, int)
            or not 1 <= self.lease_seconds <= 86_400
        ):
            raise DocumentStorageReconciliationError("INVALID_RECONCILIATION_LEASE")
        if (
            isinstance(self.max_objects, bool)
            or not isinstance(self.max_objects, int)
            or not 1 <= self.max_objects <= 1_000_000
        ):
            raise DocumentStorageReconciliationError("INVALID_RECONCILIATION_OBJECT_LIMIT")


@dataclass(frozen=True)
class StoredObject:
    """One object observed in the byte store, or one staging artifact."""

    object_ref: str
    tenant_key: str
    project_key: str
    digest: str | None
    extension: str | None
    byte_size: int | None
    last_modified: datetime | None
    staging: bool = False
    valid_shape: bool = True


class DocumentObjectInventory(Protocol):
    def list(
        self, *, tenant_id: str | None = None, project_id: str | None = None
    ) -> Iterable[StoredObject]: ...

    def read(
        self, item: StoredObject, *, tenant_id: str, project_id: str
    ) -> bytes: ...

    def delete(
        self, item: StoredObject, *, tenant_id: str, project_id: str
    ) -> None: ...


class LocalDocumentObjectInventory:
    """Filesystem inventory for content-addressed local objects and staging.

    Only regular files inside the configured root are listed. Symlinks are
    skipped: they can never be served by ``LocalDocumentStorage`` and treating
    them as objects would make an unsafe cleanup decision possible.
    """

    def __init__(
        self, root: str | os.PathLike[str], *, max_bytes: int = DEFAULT_MAX_DOCUMENT_BYTES
    ) -> None:
        if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes <= 0:
            raise DocumentStorageReconciliationError("INVALID_DOCUMENT_CONTENT_LIMIT")
        self.root = os.path.realpath(os.fspath(root))
        self.max_bytes = max_bytes

    def _scoped_keys(
        self, tenant_id: str | None, project_id: str | None
    ) -> tuple[str | None, str | None]:
        if project_id is not None and tenant_id is None:
            raise DocumentStorageReconciliationError("INVALID_RECONCILIATION_SCOPE")
        return (
            None if tenant_id is None else storage_scope_key(tenant_id),
            None if project_id is None else storage_scope_key(project_id),
        )

    def list(
        self, *, tenant_id: str | None = None, project_id: str | None = None
    ) -> Iterable[StoredObject]:
        tenant_key, project_key = self._scoped_keys(tenant_id, project_id)
        if not os.path.isdir(self.root):
            raise DocumentStorageInventoryError("DOCUMENT_STORAGE_INVENTORY_UNAVAILABLE")
        items: list[StoredObject] = []
        try:
            tenant_names = sorted(os.listdir(self.root))
        except OSError as exc:
            raise DocumentStorageInventoryError(
                "DOCUMENT_STORAGE_INVENTORY_UNAVAILABLE"
            ) from exc
        for tenant_name in tenant_names:
            if not _HEX16.match(tenant_name):
                continue
            if tenant_key is not None and tenant_name != tenant_key:
                continue
            tenant_path = os.path.join(self.root, tenant_name)
            if not os.path.isdir(tenant_path) or os.path.islink(tenant_path):
                continue
            project_names = sorted(os.listdir(tenant_path))
            for project_name in project_names:
                if not _HEX16.match(project_name):
                    continue
                if project_key is not None and project_name != project_key:
                    continue
                project_path = os.path.join(tenant_path, project_name)
                if not os.path.isdir(project_path) or os.path.islink(project_path):
                    continue
                for prefix_name in sorted(os.listdir(project_path)):
                    if not _HEX2.match(prefix_name):
                        continue
                    directory = os.path.join(project_path, prefix_name)
                    if not os.path.isdir(directory) or os.path.islink(directory):
                        continue
                    for name in sorted(os.listdir(directory)):
                        path = os.path.join(directory, name)
                        if os.path.islink(path) or not os.path.isfile(path):
                            continue
                        items.append(
                            self._entry(
                                path,
                                tenant_key=tenant_name,
                                project_key=project_name,
                                prefix_name=prefix_name,
                                name=name,
                            )
                        )
        return tuple(items)

    def _entry(
        self,
        path: str,
        *,
        tenant_key: str,
        project_key: str,
        prefix_name: str,
        name: str,
    ) -> StoredObject:
        stat = os.stat(path)
        modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
        if name.startswith(STAGING_PREFIX):
            return StoredObject(
                object_ref=(
                    f"{STORAGE_REF_PREFIX}/{tenant_key}/{project_key}/"
                    f"{prefix_name}/{name}"
                ),
                tenant_key=tenant_key,
                project_key=project_key,
                digest=None,
                extension=None,
                byte_size=stat.st_size,
                last_modified=modified,
                staging=True,
            )
        stem, extension = os.path.splitext(name)
        if (
            not _HEX64.match(stem)
            or not stem.startswith(prefix_name)
            or not _SAFE_EXTENSION.match(extension)
        ):
            return StoredObject(
                object_ref=(
                    f"{STORAGE_REF_PREFIX}/{tenant_key}/{project_key}/"
                    f"{prefix_name}/{name}"
                ),
                tenant_key=tenant_key,
                project_key=project_key,
                digest=None,
                extension=extension or None,
                byte_size=stat.st_size,
                last_modified=modified,
                valid_shape=False,
            )
        return StoredObject(
            object_ref=(
                f"{STORAGE_REF_PREFIX}/{tenant_key}/{project_key}/"
                f"{prefix_name}/{stem}{extension}"
            ),
            tenant_key=tenant_key,
            project_key=project_key,
            digest=f"sha256:{stem}",
            extension=extension,
            byte_size=stat.st_size,
            last_modified=modified,
        )

    def _path(self, item: StoredObject) -> str:
        prefix = f"{STORAGE_REF_PREFIX}/"
        if not item.object_ref.startswith(prefix):
            raise DocumentStorageError("INVALID_DOCUMENT_STORAGE_REF")
        parts = item.object_ref[len(prefix):].split("/")
        if len(parts) != 4:
            raise DocumentStorageError("INVALID_DOCUMENT_STORAGE_REF")
        tenant_key, project_key, prefix_name, name = parts
        if not (
            _HEX16.match(tenant_key)
            and _HEX16.match(project_key)
            and _HEX2.match(prefix_name)
        ):
            raise DocumentStorageError("INVALID_DOCUMENT_STORAGE_REF")
        if tenant_key != item.tenant_key or project_key != item.project_key:
            raise DocumentStorageError("DOCUMENT_STORAGE_SCOPE_MISMATCH")
        if name.startswith(STAGING_PREFIX):
            if not item.staging:
                raise DocumentStorageError("INVALID_DOCUMENT_STORAGE_REF")
        else:
            stem, extension = os.path.splitext(name)
            if (
                not _HEX64.match(stem)
                or not stem.startswith(prefix_name)
                or not _SAFE_EXTENSION.match(extension)
            ):
                raise DocumentStorageError("INVALID_DOCUMENT_STORAGE_REF")
        direct = os.path.join(
            self.root, tenant_key, project_key, prefix_name, name
        )
        if os.path.islink(direct):
            raise DocumentStorageError("DOCUMENT_STORAGE_PATH_ESCAPE")
        candidate = os.path.realpath(direct)
        if candidate != direct or not candidate.startswith(self.root + os.sep):
            raise DocumentStorageError("DOCUMENT_STORAGE_PATH_ESCAPE")
        return candidate

    def read(self, item: StoredObject, *, tenant_id: str, project_id: str) -> bytes:
        if item.staging:
            raise DocumentStorageError("INVALID_DOCUMENT_STORAGE_REF")
        if item.tenant_key != storage_scope_key(tenant_id) or item.project_key != storage_scope_key(
            project_id
        ):
            raise DocumentStorageError("DOCUMENT_STORAGE_SCOPE_MISMATCH")
        path = self._path(item)
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(path, flags)
        except FileNotFoundError as exc:
            raise DocumentStorageInventoryError("DOCUMENT_STORAGE_OBJECT_MISSING") from exc
        with os.fdopen(descriptor, "rb") as stream:
            payload = stream.read(self.max_bytes + 1)
        if len(payload) > self.max_bytes:
            raise DocumentStorageInventoryError("DOCUMENT_STORAGE_OBJECT_UNAVAILABLE")
        return payload

    def delete(self, item: StoredObject, *, tenant_id: str, project_id: str) -> None:
        if item.tenant_key != storage_scope_key(tenant_id) or item.project_key != storage_scope_key(
            project_id
        ):
            raise DocumentStorageError("DOCUMENT_STORAGE_SCOPE_MISMATCH")
        path = self._path(item)
        try:
            os.unlink(path)
        except FileNotFoundError:
            return
        except OSError as exc:
            raise DocumentStorageInventoryError(
                "DOCUMENT_STORAGE_DELETE_FAILED"
            ) from exc


class S3DocumentObjectInventory:
    """Inventory over the configured bucket and prefix, via ListObjectsV2."""

    def __init__(
        self,
        storage: S3CompatibleDocumentStorage,
        *,
        max_bytes: int = DEFAULT_MAX_DOCUMENT_BYTES,
    ) -> None:
        if not isinstance(storage, S3CompatibleDocumentStorage):
            raise DocumentStorageReconciliationError("INVALID_DOCUMENT_STORAGE_ADAPTER")
        if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes <= 0:
            raise DocumentStorageReconciliationError("INVALID_DOCUMENT_CONTENT_LIMIT")
        self.storage = storage
        self.max_bytes = max_bytes
        configured = (storage.settings.prefix or "").strip("/")
        self._base_prefix = f"{configured}/" if configured else ""

    def list(
        self, *, tenant_id: str | None = None, project_id: str | None = None
    ) -> Iterable[StoredObject]:
        if project_id is not None and tenant_id is None:
            raise DocumentStorageReconciliationError("INVALID_RECONCILIATION_SCOPE")
        prefix = self._base_prefix
        if tenant_id is not None:
            prefix += storage_scope_key(tenant_id) + "/"
        if project_id is not None:
            prefix += storage_scope_key(project_id) + "/"
        items: list[StoredObject] = []
        for key, size, modified in self.storage.list_objects(prefix=prefix):
            items.append(self._entry(key, size=size, modified=modified))
        return tuple(items)

    def _entry(
        self, key: str, *, size: int, modified: datetime | None
    ) -> StoredObject:
        relative = key[len(self._base_prefix):] if self._base_prefix else key
        if self._base_prefix and not key.startswith(self._base_prefix):
            return self._unknown(key, size=size, modified=modified)
        parts = relative.split("/")
        if len(parts) != 4:
            return self._unknown(key, size=size, modified=modified)
        tenant_key, project_key, prefix_name, name = parts
        if not (
            _HEX16.match(tenant_key)
            and _HEX16.match(project_key)
            and _HEX2.match(prefix_name)
        ):
            return self._unknown(key, size=size, modified=modified)
        stem, extension = os.path.splitext(name)
        if (
            not _HEX64.match(stem)
            or not stem.startswith(prefix_name)
            or not _SAFE_EXTENSION.match(extension)
        ):
            return self._unknown(key, size=size, modified=modified)
        return StoredObject(
            object_ref=(
                f"{S3_STORAGE_REF_PREFIX}/{tenant_key}/{project_key}/"
                f"{prefix_name}/{stem}{extension}"
            ),
            tenant_key=tenant_key,
            project_key=project_key,
            digest=f"sha256:{stem}",
            extension=extension,
            byte_size=size,
            last_modified=modified,
        )

    def _unknown(
        self, key: str, *, size: int, modified: datetime | None
    ) -> StoredObject:
        return StoredObject(
            object_ref=f"{S3_STORAGE_REF_PREFIX}/invalid/{object_handle(key)}",
            tenant_key="",
            project_key="",
            digest=None,
            extension=None,
            byte_size=size,
            last_modified=modified,
            valid_shape=False,
        )

    def read(self, item: StoredObject, *, tenant_id: str, project_id: str) -> bytes:
        if item.digest is None:
            raise DocumentStorageError("INVALID_DOCUMENT_STORAGE_REF")
        payload = self.storage.read(
            item.object_ref,
            tenant_id=tenant_id,
            project_id=project_id,
            expected_content_hash=item.digest,
        )
        if len(payload) > self.max_bytes:
            raise DocumentStorageError("DOCUMENT_CONTENT_TOO_LARGE")
        return payload

    def delete(self, item: StoredObject, *, tenant_id: str, project_id: str) -> None:
        self.storage.delete(
            item.object_ref, tenant_id=tenant_id, project_id=project_id
        )


# --------------------------------------------------------------------------
# durable state and append-only cleanup audit
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class StorageObservationState:
    tenant_id: str
    project_id: str
    object_ref: str
    classification: str
    first_observed_at: datetime
    last_observed_at: datetime
    observations: int
    status: str
    attempts: int
    last_error: str
    claim_token: str | None
    claimed_until: datetime | None


@dataclass(frozen=True)
class StorageCleanupRecord:
    tenant_id: str
    project_id: str
    cleanup_id: str
    object_ref: str
    classification: str
    actor_id: str
    reason: str
    content_hash: str | None
    byte_size: int | None
    status: str
    attempt: int
    occurred_at: datetime
    detail: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "cleanup_id": self.cleanup_id,
            "object_handle": object_handle(self.object_ref),
            "classification": self.classification,
            "actor_id": self.actor_id,
            "reason": self.reason,
            "content_hash": self.content_hash,
            "byte_size": self.byte_size,
            "status": self.status,
            "attempt": self.attempt,
            "occurred_at": _iso(self.occurred_at),
            "detail": self.detail,
        }


class DocumentStorageReconciliationStore(Protocol):
    def initialize(self) -> None: ...

    def get(
        self, tenant_id: str, project_id: str, object_ref: str
    ) -> StorageObservationState | None: ...

    def record_observation(
        self,
        *,
        tenant_id: str,
        project_id: str,
        object_ref: str,
        classification: str,
        now: datetime,
    ) -> StorageObservationState: ...

    def claim(
        self,
        *,
        tenant_id: str,
        project_id: str,
        object_ref: str,
        now: datetime,
        grace_cutoff: datetime,
        min_observations: int,
        lease_seconds: int,
    ) -> tuple[int, str] | None: ...

    def commit_claim(self) -> None: ...

    def commit(self) -> None: ...

    def mark_deleted(
        self,
        *,
        tenant_id: str,
        project_id: str,
        object_ref: str,
        now: datetime,
        claim_token: str,
    ) -> bool: ...

    def mark_failed(
        self,
        *,
        tenant_id: str,
        project_id: str,
        object_ref: str,
        now: datetime,
        detail: str,
        claim_token: str,
    ) -> bool: ...

    def mark_resolved(
        self, *, tenant_id: str, project_id: str, object_ref: str
    ) -> bool: ...

    def record_cleanup(self, record: StorageCleanupRecord) -> StorageCleanupRecord: ...

    def list_cleanup(
        self,
        tenant_id: str,
        project_id: str,
        *,
        object_ref: str | None = None,
    ) -> tuple[StorageCleanupRecord, ...]: ...


class _DocumentStorageReconciliationStore:
    placeholder = "?"

    def __init__(self, connection) -> None:
        self.connection = connection

    @property
    def q(self) -> str:
        return self.placeholder

    def initialize(self) -> None:
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS project_document_storage_observation (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                object_ref TEXT NOT NULL,
                classification TEXT NOT NULL,
                first_observed_at TEXT NOT NULL,
                last_observed_at TEXT NOT NULL,
                observations BIGINT NOT NULL,
                status TEXT NOT NULL,
                attempts BIGINT NOT NULL,
                last_error TEXT NOT NULL,
                claim_token TEXT,
                claimed_until TEXT,
                PRIMARY KEY (tenant_id, project_id, object_ref)
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS project_document_storage_cleanup (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                cleanup_id TEXT NOT NULL,
                object_ref TEXT NOT NULL,
                classification TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                reason TEXT NOT NULL,
                content_hash TEXT,
                byte_size BIGINT,
                status TEXT NOT NULL,
                attempt BIGINT NOT NULL,
                occurred_at TEXT NOT NULL,
                detail TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, cleanup_id)
            )"""
        )
        self.connection.execute(
            """CREATE INDEX IF NOT EXISTS idx_document_storage_observation_status
               ON project_document_storage_observation
               (tenant_id, project_id, status, last_observed_at)"""
        )
        self.connection.execute(
            """CREATE INDEX IF NOT EXISTS idx_document_storage_cleanup_scope
               ON project_document_storage_cleanup
               (tenant_id, project_id, occurred_at)"""
        )

    def _state(self, row) -> StorageObservationState:
        return StorageObservationState(
            tenant_id=row[0],
            project_id=row[1],
            object_ref=row[2],
            classification=row[3],
            first_observed_at=_parse(row[4]),
            last_observed_at=_parse(row[5]),
            observations=int(row[6]),
            status=row[7],
            attempts=int(row[8]),
            last_error=row[9],
            claim_token=row[10],
            claimed_until=None if row[11] is None else _parse(row[11]),
        )

    def _cleanup(self, row) -> StorageCleanupRecord:
        return StorageCleanupRecord(
            tenant_id=row[0],
            project_id=row[1],
            cleanup_id=row[2],
            object_ref=row[3],
            classification=row[4],
            actor_id=row[5],
            reason=row[6],
            content_hash=row[7],
            byte_size=None if row[8] is None else int(row[8]),
            status=row[9],
            attempt=int(row[10]),
            occurred_at=_parse(row[11]),
            detail=row[12],
        )

    def get(self, tenant_id: str, project_id: str, object_ref: str):
        rows = self.connection.execute(
            f"""SELECT tenant_id, project_id, object_ref, classification,
                       first_observed_at, last_observed_at, observations, status,
                       attempts, last_error, claim_token, claimed_until
                FROM project_document_storage_observation
                WHERE tenant_id={self.q} AND project_id={self.q}
                  AND object_ref={self.q}""",
            (tenant_id, project_id, object_ref),
        ).fetchall()
        return None if not rows else self._state(rows[0])

    def record_observation(
        self,
        *,
        tenant_id: str,
        project_id: str,
        object_ref: str,
        classification: str,
        now: datetime,
    ) -> StorageObservationState:
        stamp = _iso(now)
        self.connection.execute(
            f"""INSERT INTO project_document_storage_observation
                (tenant_id, project_id, object_ref, classification,
                 first_observed_at, last_observed_at, observations, status,
                 attempts, last_error, claim_token, claimed_until)
                VALUES ({", ".join([self.q] * 6)}, 1, 'observed', 0, '', NULL, NULL)
                ON CONFLICT (tenant_id, project_id, object_ref) DO UPDATE SET
                    last_observed_at=excluded.last_observed_at,
                    classification=excluded.classification,
                    first_observed_at=CASE
                        WHEN project_document_storage_observation.status
                             IN ('deleted', 'resolved')
                        THEN excluded.first_observed_at
                        ELSE project_document_storage_observation.first_observed_at
                        END,
                    observations=CASE
                        WHEN project_document_storage_observation.status
                             IN ('deleted', 'resolved') THEN 1
                        ELSE project_document_storage_observation.observations + 1
                        END,
                    status=CASE
                        WHEN project_document_storage_observation.claim_token IS NOT NULL
                             AND project_document_storage_observation.claimed_until IS NOT NULL
                             AND project_document_storage_observation.claimed_until
                                 > excluded.last_observed_at
                        THEN project_document_storage_observation.status
                        ELSE 'observed' END,
                    last_error=CASE
                        WHEN project_document_storage_observation.claim_token IS NOT NULL
                             AND project_document_storage_observation.claimed_until IS NOT NULL
                             AND project_document_storage_observation.claimed_until
                                 > excluded.last_observed_at
                        THEN project_document_storage_observation.last_error
                        ELSE '' END""",
            (
                tenant_id,
                project_id,
                object_ref,
                classification,
                stamp,
                stamp,
            ),
        )
        stored = self.get(tenant_id, project_id, object_ref)
        if stored is None:
            raise DocumentStorageReconciliationError(
                "DOCUMENT_STORAGE_OBSERVATION_WRITE_FAILED"
            )
        return stored

    def claim(
        self,
        *,
        tenant_id: str,
        project_id: str,
        object_ref: str,
        now: datetime,
        grace_cutoff: datetime,
        min_observations: int,
        lease_seconds: int,
    ) -> tuple[int, str] | None:
        token = uuid.uuid4().hex
        claimed_until = _iso(now + timedelta(seconds=lease_seconds))
        cursor = self.connection.execute(
            f"""UPDATE project_document_storage_observation
                SET status='deleting', claim_token={self.q}, claimed_until={self.q},
                    attempts=attempts + 1
                WHERE tenant_id={self.q} AND project_id={self.q}
                  AND object_ref={self.q}
                  AND status IN ('observed', 'deleting')
                  AND observations >= {self.q}
                  AND first_observed_at <= {self.q}
                  AND (claim_token IS NULL OR claimed_until IS NULL
                       OR claimed_until <= {self.q})""",
            (
                token,
                claimed_until,
                tenant_id,
                project_id,
                object_ref,
                min_observations,
                _iso(grace_cutoff),
                _iso(now),
            ),
        )
        if cursor.rowcount != 1:
            return None
        stored = self.get(tenant_id, project_id, object_ref)
        return None if stored is None else (stored.attempts, token)

    def commit_claim(self) -> None:
        """Make the lease durable before the external delete is attempted."""
        self.connection.commit()

    def commit(self) -> None:
        """Make observations and cleanup audit rows durable for this pass."""
        self.connection.commit()

    def mark_deleted(
        self,
        *,
        tenant_id: str,
        project_id: str,
        object_ref: str,
        now: datetime,
        claim_token: str,
    ) -> bool:
        cursor = self.connection.execute(
            f"""UPDATE project_document_storage_observation
                SET status='deleted', claim_token=NULL, claimed_until=NULL,
                    last_error='', last_observed_at={self.q}
                WHERE tenant_id={self.q} AND project_id={self.q}
                  AND object_ref={self.q} AND status='deleting'
                  AND claim_token={self.q}""",
            (_iso(now), tenant_id, project_id, object_ref, claim_token),
        )
        return cursor.rowcount == 1

    def mark_failed(
        self,
        *,
        tenant_id: str,
        project_id: str,
        object_ref: str,
        now: datetime,
        detail: str,
        claim_token: str,
    ) -> bool:
        cursor = self.connection.execute(
            f"""UPDATE project_document_storage_observation
                SET status='failed', claim_token=NULL, claimed_until=NULL,
                    last_error={self.q}, last_observed_at={self.q}
                WHERE tenant_id={self.q} AND project_id={self.q}
                  AND object_ref={self.q} AND status='deleting'
                  AND claim_token={self.q}""",
            (
                (detail or "DOCUMENT_STORAGE_DELETE_FAILED")[:MAX_ERROR_DETAIL],
                _iso(now),
                tenant_id,
                project_id,
                object_ref,
                claim_token,
            ),
        )
        return cursor.rowcount == 1

    def mark_resolved(
        self, *, tenant_id: str, project_id: str, object_ref: str
    ) -> bool:
        cursor = self.connection.execute(
            f"""UPDATE project_document_storage_observation
                SET status='resolved', claim_token=NULL, claimed_until=NULL
                WHERE tenant_id={self.q} AND project_id={self.q}
                  AND object_ref={self.q} AND status <> 'resolved'
                  AND claim_token IS NULL""",
            (tenant_id, project_id, object_ref),
        )
        return cursor.rowcount == 1

    def record_cleanup(self, record: StorageCleanupRecord) -> StorageCleanupRecord:
        self.connection.execute(
            f"""INSERT INTO project_document_storage_cleanup
                (tenant_id, project_id, cleanup_id, object_ref, classification,
                 actor_id, reason, content_hash, byte_size, status, attempt,
                 occurred_at, detail)
                VALUES ({", ".join([self.q] * 13)})
                ON CONFLICT (tenant_id, project_id, cleanup_id) DO NOTHING""",
            (
                record.tenant_id,
                record.project_id,
                record.cleanup_id,
                record.object_ref,
                record.classification,
                record.actor_id,
                record.reason,
                record.content_hash,
                record.byte_size,
                record.status,
                record.attempt,
                _iso(record.occurred_at),
                record.detail[:MAX_ERROR_DETAIL],
            ),
        )
        return record

    def list_cleanup(
        self, tenant_id: str, project_id: str, *, object_ref: str | None = None
    ) -> tuple[StorageCleanupRecord, ...]:
        statement = (
            "SELECT tenant_id, project_id, cleanup_id, object_ref, classification, "
            "actor_id, reason, content_hash, byte_size, status, attempt, "
            "occurred_at, detail FROM project_document_storage_cleanup "
            f"WHERE tenant_id={self.q} AND project_id={self.q}"
        )
        parameters: list[object] = [tenant_id, project_id]
        if object_ref is not None:
            statement += f" AND object_ref={self.q}"
            parameters.append(object_ref)
        statement += " ORDER BY occurred_at, cleanup_id"
        rows = self.connection.execute(statement, tuple(parameters)).fetchall()
        return tuple(self._cleanup(row) for row in rows)


class SQLiteDocumentStorageReconciliationStore(_DocumentStorageReconciliationStore):
    placeholder = "?"

    def initialize(self) -> None:
        super().initialize()
        self.connection.commit()


class PostgresDocumentStorageReconciliationStore(_DocumentStorageReconciliationStore):
    placeholder = "%s"


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ReconciliationEntry:
    classification: str
    object_handle: str
    document_id: str | None
    version: int | None
    content_hash: str | None
    byte_size: int | None
    eligibility: str
    action: str
    detail: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "classification": self.classification,
            "object_handle": self.object_handle,
            "document_id": self.document_id,
            "version": self.version,
            "content_hash": self.content_hash,
            "byte_size": self.byte_size,
            "eligibility": self.eligibility,
            "action": self.action,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class ReconciliationReport:
    status: str
    dry_run: bool
    tenant_id: str | None
    project_id: str | None
    scanned_objects: int
    scanned_metadata: int
    counts: tuple[tuple[str, int], ...]
    deleted: int
    failed: int
    skipped: int
    eligible: int
    truncated: bool
    entries: tuple[ReconciliationEntry, ...]
    reason: str = ""

    def count(self, classification: str) -> int:
        return dict(self.counts).get(classification, 0)

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "dry_run": self.dry_run,
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "scanned_objects": self.scanned_objects,
            "scanned_metadata": self.scanned_metadata,
            "counts": dict(self.counts),
            "deleted": self.deleted,
            "failed": self.failed,
            "skipped": self.skipped,
            "eligible": self.eligible,
            "truncated": self.truncated,
            "reason": self.reason,
            "entries": [entry.as_dict() for entry in self.entries],
        }


@dataclass(frozen=True)
class _MetadataReference:
    tenant_id: str
    project_id: str
    document_id: str
    version: int
    object_ref: str
    content_hash: str
    byte_size: int
    disposed: bool
    legal_hold: bool


# --------------------------------------------------------------------------
# reconciler
# --------------------------------------------------------------------------


class DocumentStorageReconciler:
    """Classify metadata/object drift and run verified cleanup when asked."""

    def __init__(
        self,
        *,
        content_repository,
        retention_store,
        inventory: DocumentObjectInventory,
        state_store: DocumentStorageReconciliationStore,
        metrics: OperationalMetrics | None = None,
        logger=None,
        policy: ReconciliationPolicy | None = None,
        document_store=None,
    ) -> None:
        self.content_repository = content_repository
        self.retention_store = retention_store
        self.inventory = inventory
        self.state_store = state_store
        self.document_store = document_store
        self.metrics = metrics
        self.logger = logger
        self.policy = policy or ReconciliationPolicy()
        self.policy.validate()

    # -- public ------------------------------------------------------------
    def reconcile(
        self,
        *,
        tenant_id: str | None = None,
        project_id: str | None = None,
        now: datetime | None = None,
        dry_run: bool = True,
        actor_id: str = "storage-reconciler",
        reason: str = "scheduled storage reconciliation",
    ) -> ReconciliationReport:
        started = monotonic()
        if project_id is not None and tenant_id is None:
            raise DocumentStorageReconciliationError("INVALID_RECONCILIATION_SCOPE")
        for name, value, limit in (
            ("ACTOR", actor_id, MAX_ACTOR_LENGTH),
            ("REASON", reason, MAX_REASON_LENGTH),
        ):
            if not isinstance(value, str) or not value.strip() or len(value) > limit:
                raise DocumentStorageReconciliationError(
                    f"INVALID_RECONCILIATION_{name}"
                )
        moment = datetime.now(timezone.utc) if now is None else now
        if not isinstance(moment, datetime) or moment.tzinfo is None:
            raise DocumentStorageReconciliationError("INVALID_RECONCILIATION_TIMESTAMP")
        moment = moment.astimezone(timezone.utc)

        try:
            references = self._metadata_references(
                tenant_id=tenant_id, project_id=project_id
            )
            document_refs = self._document_references(
                tenant_id=tenant_id, project_id=project_id
            )
        except Exception as exc:  # noqa: BLE001 - fail closed before any listing
            return self._finish(
                self._aborted_report(
                    dry_run=dry_run,
                    tenant_id=tenant_id,
                    project_id=project_id,
                    reason="metadata_unavailable",
                    detail=_error_detail(exc),
                ),
                started,
            )

        try:
            objects = tuple(
                self.inventory.list(tenant_id=tenant_id, project_id=project_id)
            )
        except Exception as exc:  # noqa: BLE001 - an unreadable store deletes nothing
            return self._finish(
                self._aborted_report(
                    dry_run=dry_run,
                    tenant_id=tenant_id,
                    project_id=project_id,
                    reason="inventory_unavailable",
                    detail=_error_detail(exc),
                ),
                started,
            )

        objects, truncated = self._bounded(objects)
        scope_owners = self._scope_owners(references)
        reference_index = self._reference_index(references)
        holds = self._legal_holds(references)

        counts: Counter[str] = Counter()
        entries: list[ReconciliationEntry] = []
        deleted = failed = skipped = eligible = 0

        for item in objects:
            classification, tenant, project, primary, detail = self._classify(
                item,
                references=reference_index,
                scope_owners=scope_owners,
                holds=holds,
                document_refs=document_refs,
            )
            counts[classification] += 1
            if classification == MATCH:
                if not dry_run:
                    self.state_store.mark_resolved(
                        tenant_id=tenant,
                        project_id=project,
                        object_ref=item.object_ref,
                    )
                continue
            if classification in DELETABLE_CLASSIFICATIONS:
                outcome, eligibility, action = self._cleanup(
                    item,
                    tenant_id=tenant,
                    project_id=project,
                    classification=classification,
                    now=moment,
                    dry_run=dry_run,
                    actor_id=actor_id,
                    reason=reason,
                )
                if eligibility == ELIGIBLE:
                    eligible += 1
                if outcome == "deleted":
                    deleted += 1
                elif outcome == "failed":
                    failed += 1
                elif outcome == "skipped":
                    skipped += 1
            else:
                eligibility = NOT_APPLICABLE
                action = "none"
            entries.append(
                ReconciliationEntry(
                    classification=classification,
                    object_handle=object_handle(item.object_ref),
                    document_id=None if primary is None else primary.document_id,
                    version=None if primary is None else primary.version,
                    content_hash=item.digest,
                    byte_size=item.byte_size,
                    eligibility=eligibility,
                    action=action,
                    detail=detail,
                )
            )

        if not truncated:
            observed_refs = {
                item.object_ref for item in objects if item.valid_shape
            }
            for object_ref, references_for_ref in sorted(reference_index.items()):
                if object_ref in observed_refs:
                    continue
                live = [reference for reference in references_for_ref if not reference.disposed]
                if not live:
                    # Disposed versions are expected to have no bytes.
                    continue
                counts[METADATA_ONLY] += 1
                primary = live[0]
                entries.append(
                    ReconciliationEntry(
                        classification=METADATA_ONLY,
                        object_handle=object_handle(object_ref),
                        document_id=primary.document_id,
                        version=primary.version,
                        content_hash=primary.content_hash,
                        byte_size=primary.byte_size,
                        eligibility=NOT_APPLICABLE,
                        action="none",
                        detail="object_missing",
                    )
                )

        if not dry_run:
            # Persist observation counters for items that were not eligible yet;
            # destructive outcomes have already committed their audit rows.
            self.state_store.commit()

        report = ReconciliationReport(
            status=COMPLETED,
            dry_run=dry_run,
            tenant_id=tenant_id,
            project_id=project_id,
            scanned_objects=len(objects),
            scanned_metadata=len(references),
            counts=tuple(sorted(counts.items())),
            deleted=deleted,
            failed=failed,
            skipped=skipped,
            eligible=eligible,
            truncated=truncated,
            entries=tuple(entries),
        )
        return self._finish(report, started)

    # -- reporting ---------------------------------------------------------
    def _aborted_report(
        self,
        *,
        dry_run: bool,
        tenant_id: str | None,
        project_id: str | None,
        reason: str,
        detail: str,
    ) -> ReconciliationReport:
        return ReconciliationReport(
            status=ABORTED,
            dry_run=dry_run,
            tenant_id=tenant_id,
            project_id=project_id,
            scanned_objects=0,
            scanned_metadata=0,
            counts=(),
            deleted=0,
            failed=0,
            skipped=0,
            eligible=0,
            truncated=False,
            entries=(),
            reason=f"{reason}:{detail}" if detail else reason,
        )

    def _finish(
        self, report: ReconciliationReport, started: float
    ) -> ReconciliationReport:
        elapsed = (monotonic() - started) * 1000
        if self.metrics is not None:
            try:
                self.metrics.increment(
                    "document_storage_reconciliation_pass_total",
                    labels={"status": report.status},
                )
                for classification, value in report.counts:
                    self.metrics.increment(
                        "document_storage_reconciliation_object_total",
                        labels={"classification": classification},
                        value=value,
                    )
                if report.status == COMPLETED and not report.dry_run:
                    for result, value in (
                        ("deleted", report.deleted),
                        ("failed", report.failed),
                        ("skipped", report.skipped),
                    ):
                        if value:
                            self.metrics.increment(
                                "document_storage_cleanup_total",
                                labels={"result": result},
                                value=value,
                            )
                self.metrics.observe(
                    "document_storage_reconciliation_pass_ms", elapsed
                )
            except ValueError:
                pass
        if self.logger is not None:
            try:
                self.logger.emit(
                    "document_storage_reconciliation_completed",
                    severity="info" if report.status == COMPLETED else "warning",
                    fields={
                        "status": report.status,
                        "dry_run": report.dry_run,
                        "scanned_objects": report.scanned_objects,
                        "scanned_metadata": report.scanned_metadata,
                        "deleted": report.deleted,
                        "failed": report.failed,
                        "skipped": report.skipped,
                        "counts": dict(report.counts),
                    },
                )
            except Exception:  # noqa: BLE001 - observability never blocks cleanup
                pass
        return report

    # -- snapshots ---------------------------------------------------------
    def _metadata_references(
        self, *, tenant_id: str | None, project_id: str | None
    ) -> tuple[_MetadataReference, ...]:
        versions: tuple[DocumentContentVersion, ...] = tuple(
            self.content_repository.list_all(
                tenant_id=tenant_id, project_id=project_id
            )
        )
        dispositions: tuple[DocumentDisposition, ...] = tuple(
            self.retention_store.list_all_dispositions(
                tenant_id=tenant_id, project_id=project_id
            )
        )
        policies: tuple[DocumentRetentionPolicy, ...] = tuple(
            self.retention_store.list_all_policies(
                tenant_id=tenant_id, project_id=project_id
            )
        )
        disposed = {
            (item.tenant_id, item.project_id, item.document_id, item.version)
            for item in dispositions
        }
        holds = {
            (item.tenant_id, item.project_id, item.document_id)
            for item in policies
            if item.legal_hold
        }
        references: list[_MetadataReference] = []
        for version in versions:
            if tenant_id is not None and version.tenant_id != tenant_id:
                continue
            if project_id is not None and version.project_id != project_id:
                continue
            key = (
                version.tenant_id,
                version.project_id,
                version.document_id,
                version.version,
            )
            references.append(
                _MetadataReference(
                    tenant_id=version.tenant_id,
                    project_id=version.project_id,
                    document_id=version.document_id,
                    version=version.version,
                    object_ref=version.storage_ref,
                    content_hash=version.content_hash,
                    byte_size=version.byte_size,
                    disposed=key in disposed,
                    legal_hold=(
                        version.tenant_id,
                        version.project_id,
                        version.document_id,
                    )
                    in holds,
                )
            )
        return tuple(references)

    def _document_references(
        self, *, tenant_id: str | None, project_id: str | None
    ) -> frozenset[str]:
        """Object refs held directly by a document record.

        Legacy records point at bytes that have no content-version row. They are
        still live metadata, so an object referenced only this way must never be
        classified as an orphan and deleted.
        """
        if self.document_store is None:
            return frozenset()
        documents = self.document_store.list_all(
            tenant_id=tenant_id, project_id=project_id
        )
        return frozenset(
            stored.document.storage_ref for stored in documents if stored.document.storage_ref
        )

    @staticmethod
    def _reference_index(
        references: Iterable[_MetadataReference],
    ) -> dict[str, list[_MetadataReference]]:
        index: dict[str, list[_MetadataReference]] = {}
        for reference in references:
            index.setdefault(reference.object_ref, []).append(reference)
        return index

    @staticmethod
    def _scope_owners(
        references: Iterable[_MetadataReference],
    ) -> dict[tuple[str, str], tuple[tuple[str, str], ...]]:
        owners: dict[tuple[str, str], set[tuple[str, str]]] = {}
        for reference in references:
            key = (
                storage_scope_key(reference.tenant_id),
                storage_scope_key(reference.project_id),
            )
            owners.setdefault(key, set()).add(
                (reference.tenant_id, reference.project_id)
            )
        return {key: tuple(sorted(value)) for key, value in owners.items()}

    @staticmethod
    def _legal_holds(
        references: Iterable[_MetadataReference],
    ) -> set[tuple[str, str, str]]:
        return {
            (reference.tenant_id, reference.project_id, reference.document_id)
            for reference in references
            if reference.legal_hold
        }

    def _bounded(
        self, objects: tuple[StoredObject, ...]
    ) -> tuple[tuple[StoredObject, ...], bool]:
        ordered = tuple(sorted(objects, key=lambda item: item.object_ref))
        if len(ordered) <= self.policy.max_objects:
            return ordered, False
        return ordered[: self.policy.max_objects], True

    # -- classification ----------------------------------------------------
    def _classify(
        self,
        item: StoredObject,
        *,
        references: dict[str, list[_MetadataReference]],
        scope_owners: dict[tuple[str, str], tuple[tuple[str, str], ...]],
        holds: set[tuple[str, str, str]],
        document_refs: frozenset[str] = frozenset(),
    ) -> tuple[str, str, str, _MetadataReference | None, str]:
        if not item.valid_shape:
            return UNKNOWN_OBJECT, "", "", None, "malformed_object_key"
        owners = scope_owners.get((item.tenant_key, item.project_key))
        if not owners:
            return UNKNOWN_OBJECT, "", "", None, "unmapped_scope"
        if len(owners) != 1:
            return UNKNOWN_OBJECT, "", "", None, "ambiguous_scope"
        tenant_id, project_id = owners[0]
        if item.staging:
            return (
                INCOMPLETE_UPLOAD,
                tenant_id,
                project_id,
                None,
                "abandoned_staging_object",
            )
        referencing = references.get(item.object_ref, [])
        if not referencing:
            if item.object_ref in document_refs:
                # A document record still serves these bytes; there is no
                # version row to verify, so retain them as a metadata match.
                return MATCH, tenant_id, project_id, None, "document_record_reference"
            return ORPHAN_OBJECT, tenant_id, project_id, None, "no_metadata_reference"
        live = [reference for reference in referencing if not reference.disposed]
        primary = live[0] if live else referencing[0]
        if item.digest is None:
            return UNAVAILABLE, tenant_id, project_id, primary, "unreadable_object_key"
        if any(reference.content_hash != item.digest for reference in referencing):
            return CHECKSUM_MISMATCH, tenant_id, project_id, primary, "content_hash_mismatch"
        if live:
            if any(
                reference.byte_size != item.byte_size
                for reference in live
                if item.byte_size is not None
            ):
                return SIZE_MISMATCH, tenant_id, project_id, primary, "byte_size_mismatch"
            if self.policy.verify_bytes:
                try:
                    payload = self.inventory.read(
                        item, tenant_id=tenant_id, project_id=project_id
                    )
                except DocumentStorageError as exc:
                    return (
                        UNAVAILABLE,
                        tenant_id,
                        project_id,
                        primary,
                        _error_detail(exc),
                    )
                except Exception as exc:  # noqa: BLE001 - report, never delete
                    return (
                        UNAVAILABLE,
                        tenant_id,
                        project_id,
                        primary,
                        _error_detail(exc),
                    )
                if hashlib.sha256(payload).hexdigest() != item.digest.split(":", 1)[-1]:
                    return (
                        CHECKSUM_MISMATCH,
                        tenant_id,
                        project_id,
                        primary,
                        "stored_bytes_digest_mismatch",
                    )
            return MATCH, tenant_id, project_id, primary, ""
        if any(
            (reference.tenant_id, reference.project_id, reference.document_id) in holds
            for reference in referencing
        ):
            return (
                RETENTION_PROTECTED,
                tenant_id,
                project_id,
                primary,
                "legal_hold",
            )
        return PENDING_DELETION, tenant_id, project_id, primary, "all_versions_disposed"

    # -- cleanup -----------------------------------------------------------
    def _eligibility(
        self, state: StorageObservationState, now: datetime
    ) -> str:
        if state.observations < self.policy.min_observations:
            return AWAITING_REPEATED_OBSERVATION
        if state.first_observed_at + self.policy.grace_period > now:
            return IN_GRACE_PERIOD
        return ELIGIBLE

    def _cleanup(
        self,
        item: StoredObject,
        *,
        tenant_id: str,
        project_id: str,
        classification: str,
        now: datetime,
        dry_run: bool,
        actor_id: str,
        reason: str,
    ) -> tuple[str, str, str]:
        if dry_run:
            # A dry run must not advance the observation window, so eligibility
            # is computed from the durable state only.
            observed = self.state_store.get(tenant_id, project_id, item.object_ref)
            eligibility = (
                AWAITING_REPEATED_OBSERVATION
                if observed is None
                else self._eligibility(observed, now)
            )
            return (
                "none",
                eligibility,
                "would_delete" if eligibility == ELIGIBLE else "none",
            )
        state = self.state_store.record_observation(
            tenant_id=tenant_id,
            project_id=project_id,
            object_ref=item.object_ref,
            classification=classification,
            now=now,
        )
        eligibility = self._eligibility(state, now)
        if eligibility != ELIGIBLE:
            return "skipped", eligibility, "none"
        claimed = self.state_store.claim(
            tenant_id=tenant_id,
            project_id=project_id,
            object_ref=item.object_ref,
            now=now,
            grace_cutoff=now - self.policy.grace_period,
            min_observations=self.policy.min_observations,
            lease_seconds=self.policy.lease_seconds,
        )
        if claimed is None:
            return "skipped", eligibility, "skipped"
        attempt, claim_token = claimed
        # The lease must survive the external delete: a crash leaves the
        # occurrence claimed instead of silently retryable in a tight loop.
        self.state_store.commit_claim()
        cleanup_id = uuid.uuid4().hex
        try:
            self.inventory.delete(
                item, tenant_id=tenant_id, project_id=project_id
            )
        except Exception as exc:  # noqa: BLE001 - record and retry later
            detail = _error_detail(exc)
            if not self.state_store.mark_failed(
                tenant_id=tenant_id,
                project_id=project_id,
                object_ref=item.object_ref,
                now=now,
                detail=detail,
                claim_token=claim_token,
            ):
                return "skipped", eligibility, "lease_lost"
            self.state_store.record_cleanup(
                StorageCleanupRecord(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    cleanup_id=cleanup_id,
                    object_ref=item.object_ref,
                    classification=classification,
                    actor_id=actor_id,
                    reason=reason,
                    content_hash=item.digest,
                    byte_size=item.byte_size,
                    status="failed",
                    attempt=attempt,
                    occurred_at=now,
                    detail=detail,
                )
            )
            self.state_store.commit()
            return "failed", eligibility, "failed"
        if not self.state_store.mark_deleted(
            tenant_id=tenant_id,
            project_id=project_id,
            object_ref=item.object_ref,
            now=now,
            claim_token=claim_token,
        ):
            return "skipped", eligibility, "lease_lost"
        self.state_store.record_cleanup(
            StorageCleanupRecord(
                tenant_id=tenant_id,
                project_id=project_id,
                cleanup_id=cleanup_id,
                object_ref=item.object_ref,
                classification=classification,
                actor_id=actor_id,
                reason=reason,
                content_hash=item.digest,
                byte_size=item.byte_size,
                status="deleted",
                attempt=attempt,
                occurred_at=now,
            )
        )
        self.state_store.commit()
        return "deleted", eligibility, "deleted"


__all__ = [
    "ABORTED",
    "AWAITING_REPEATED_OBSERVATION",
    "CHECKSUM_MISMATCH",
    "CLASSIFICATIONS",
    "COMPLETED",
    "DELETABLE_CLASSIFICATIONS",
    "DocumentObjectInventory",
    "DocumentStorageInventoryError",
    "DocumentStorageReconciliationError",
    "DocumentStorageReconciliationStore",
    "DocumentStorageReconciler",
    "ELIGIBLE",
    "INCOMPLETE_UPLOAD",
    "IN_GRACE_PERIOD",
    "LocalDocumentObjectInventory",
    "MATCH",
    "METADATA_ONLY",
    "NOT_APPLICABLE",
    "ORPHAN_OBJECT",
    "PENDING_DELETION",
    "PostgresDocumentStorageReconciliationStore",
    "RETENTION_PROTECTED",
    "ReconciliationEntry",
    "ReconciliationPolicy",
    "ReconciliationReport",
    "S3DocumentObjectInventory",
    "SIZE_MISMATCH",
    "SQLiteDocumentStorageReconciliationStore",
    "StorageCleanupRecord",
    "StorageObservationState",
    "StoredObject",
    "UNAVAILABLE",
    "UNKNOWN_OBJECT",
    "object_handle",
]
