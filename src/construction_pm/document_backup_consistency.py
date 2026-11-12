"""Read-only consistency checks for document object storage and metadata.

Document metadata rows and their bytes live in two systems. A database backup
alone cannot restore downloadable documents: the object store must be captured
at a compatible point in time and both restored together. This module verifies
the relationship after a restore without deleting, repairing or rewriting
anything.

A report contains counts and document identities only; it never includes raw
bytes, tokens or storage credentials. ``storage_ref`` is not emitted by
``as_dict`` because operators should query the metadata store for routing
details rather than copy references into tickets or logs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol

from .document_content_repository import DocumentContentVersion
from .document_storage import (
    DocumentBinaryStorage,
    DocumentContentHashMismatch,
    DocumentContentIntegrityError,
    DocumentContentNotFound,
    DocumentStorageError,
)

OK = "ok"
MISSING = "missing"
INTEGRITY_FAILED = "integrity_failed"
UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class VersionConsistency:
    tenant_id: str
    project_id: str
    document_id: str
    version: int
    status: str

    def as_dict(self) -> dict[str, object]:
        return {
            "document_id": self.document_id,
            "version": self.version,
            "status": self.status,
        }


@dataclass(frozen=True)
class StorageConsistencyReport:
    checked: int
    entries: tuple[VersionConsistency, ...]

    @property
    def ok(self) -> int:
        return sum(1 for entry in self.entries if entry.status == OK)

    @property
    def missing(self) -> int:
        return sum(1 for entry in self.entries if entry.status == MISSING)

    @property
    def integrity_failed(self) -> int:
        return sum(1 for entry in self.entries if entry.status == INTEGRITY_FAILED)

    @property
    def unavailable(self) -> int:
        return sum(1 for entry in self.entries if entry.status == UNAVAILABLE)

    @property
    def consistent(self) -> bool:
        return (
            self.checked == len(self.entries)
            and self.missing == 0
            and self.integrity_failed == 0
            and self.unavailable == 0
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "checked": self.checked,
            "ok": self.ok,
            "missing": self.missing,
            "integrity_failed": self.integrity_failed,
            "unavailable": self.unavailable,
            "consistent": self.consistent,
            "failures": [
                entry.as_dict()
                for entry in self.entries
                if entry.status != OK
            ],
        }


class DocumentContentLister(Protocol):
    def list(
        self, tenant_id: str, project_id: str, document_id: str
    ) -> Iterable[DocumentContentVersion]: ...


def verify_document_versions(
    versions: Iterable[DocumentContentVersion],
    storage: DocumentBinaryStorage,
) -> StorageConsistencyReport:
    """Verify every version's object exists and still matches its digest."""
    entries: list[VersionConsistency] = []
    prepared = tuple(versions)
    for version in prepared:
        try:
            storage.read(
                version.storage_ref,
                tenant_id=version.tenant_id,
                project_id=version.project_id,
                expected_content_hash=version.content_hash,
            )
        except DocumentContentNotFound:
            status = MISSING
        except (DocumentContentHashMismatch, DocumentContentIntegrityError):
            status = INTEGRITY_FAILED
        except DocumentStorageError:
            status = UNAVAILABLE
        except Exception:  # noqa: BLE001 - keep the operator report bounded
            status = UNAVAILABLE
        else:
            status = OK
        entries.append(
            VersionConsistency(
                tenant_id=version.tenant_id,
                project_id=version.project_id,
                document_id=version.document_id,
                version=version.version,
                status=status,
            )
        )
    return StorageConsistencyReport(checked=len(prepared), entries=tuple(entries))


def verify_document_scope(
    content_repository: DocumentContentLister,
    storage: DocumentBinaryStorage,
    *,
    tenant_id: str,
    project_id: str,
    document_ids: Iterable[str],
) -> StorageConsistencyReport:
    """Verify all stored versions for the supplied documents in one scope."""
    versions: list[DocumentContentVersion] = []
    for document_id in document_ids:
        versions.extend(
            content_repository.list(tenant_id, project_id, document_id)
        )
    return verify_document_versions(versions, storage)


__all__ = [
    "INTEGRITY_FAILED",
    "MISSING",
    "OK",
    "StorageConsistencyReport",
    "UNAVAILABLE",
    "VersionConsistency",
    "verify_document_scope",
    "verify_document_versions",
]
