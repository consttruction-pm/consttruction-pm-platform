from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from .api_errors import (
    APIError,
    authorization_error,
    conflict_error,
    persistence_error,
    validation_error,
)
from .application.authorization import AuthorizationContext, AuthorizationPolicy, Permission
from .backend_p0.transactions import TransactionManager
from .document_content_repository import (
    DocumentContentRepository,
    DocumentContentVersion,
)
from .document_persistence import (
    DocumentApprovalTransitionError,
    DocumentAuthorizationError,
    DocumentIdempotencyReuse,
    DocumentRecord,
    DocumentRevisionConflict,
    DocumentLifecycleAuthorizer,
    DocumentStore,
    StoredDocument,
)
from .document_scan import (
    DocumentScanError,
    DocumentScanRejected,
    DocumentScanUnavailable,
    DocumentScanner,
    ScanVerdict,
)
from .document_storage import (
    DEFAULT_MAX_DOCUMENT_BYTES,
    DocumentBinaryStorage,
    DocumentContentHashMismatch,
    DocumentContentIntegrityError,
    DocumentContentNotFound,
    DocumentContentQuarantined,
    DocumentContentTooLarge,
    DocumentContentTypeRejected,
    DocumentStorageError,
    validate_document_content,
)


class DocumentStorageUnavailable(ValueError):
    """Raised when binary routes are configured without a storage adapter."""


@dataclass(frozen=True)
class DocumentContentUpload:
    content: DocumentContentVersion
    storage_ref: str
    idempotent_replay: bool = False


@dataclass(frozen=True)
class DocumentContentDownload:
    content_type: str
    filename: str
    data: bytes
    content_hash: str
    version: int | None


@dataclass(frozen=True)
class DocumentApplicationService:
    """Application boundary for versioned document/RFI/Submittal operations."""

    store: DocumentStore
    authorization_policy: AuthorizationPolicy
    lifecycle_authorizer: DocumentLifecycleAuthorizer
    transaction_manager: TransactionManager
    storage: DocumentBinaryStorage | None = None
    content_repository: DocumentContentRepository | None = None
    max_content_bytes: int = DEFAULT_MAX_DOCUMENT_BYTES
    scanner: DocumentScanner | None = None
    require_scanned_content: bool = False

    def create(
        self,
        document: DocumentRecord,
        *,
        context: AuthorizationContext,
        idempotency_key: str,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredDocument:
        self._authorize_write(document, context, actor_id)
        with self.transaction_manager.transaction():
            return self.store.persist(
                document,
                idempotency_key=idempotency_key,
                actor_id=actor_id,
                occurred_at=occurred_at,
            )

    def read(
        self,
        *,
        tenant_id: str,
        project_id: str,
        document_id: str,
        context: AuthorizationContext,
    ) -> StoredDocument:
        self._check_permission(context, tenant_id, project_id, Permission.PROJECT_READ)
        return self.store.get(tenant_id, project_id, document_id)

    def list(
        self,
        *,
        tenant_id: str,
        project_id: str,
        context: AuthorizationContext,
        resource_type: str | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> tuple[StoredDocument, ...]:
        self._check_permission(context, tenant_id, project_id, Permission.PROJECT_READ)
        return self.store.list(
            tenant_id,
            project_id,
            resource_type=resource_type,
            status=status,
            search=search,
        )

    def history(
        self,
        *,
        tenant_id: str,
        project_id: str,
        document_id: str,
        context: AuthorizationContext,
    ):
        self._check_permission(context, tenant_id, project_id, Permission.PROJECT_READ)
        self.store.get(tenant_id, project_id, document_id)
        return self.store.history(tenant_id, project_id, document_id)

    def update(
        self,
        document: DocumentRecord,
        *,
        expected_revision: int,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
        event_type: str = "updated",
        audit_reason: str = "",
    ) -> StoredDocument:
        self._authorize_write(document, context, actor_id)
        with self.transaction_manager.transaction():
            current = self.store.get(
                document.tenant_id, document.project_id, document.document_id
            )
            if document.status != current.document.status:
                # Status is an approval decision with its own revision-guarded,
                # audited transition endpoint. A metadata edit must not bypass it.
                raise ValueError("DOCUMENT_STATUS_REQUIRES_TRANSITION")
            return self.store.update(
                document,
                expected_revision=expected_revision,
                actor_id=actor_id,
                occurred_at=occurred_at,
                event_type=event_type,
                audit_reason=audit_reason,
            )

    def transition_status(
        self,
        document: DocumentRecord,
        *,
        expected_revision: int,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
        reason: str = "",
    ) -> StoredDocument:
        self._authorize_write(document, context, actor_id)
        with self.transaction_manager.transaction():
            current = self.store.get(document.tenant_id, document.project_id, document.document_id)
            self.lifecycle_authorizer.authorize_transition(
                actor_id=actor_id,
                tenant_id=document.tenant_id,
                project_id=document.project_id,
                document_id=document.document_id,
                from_status=current.document.status,
                to_status=document.status,
                roles=context.roles,
            )
            return self.store.transition_status(
                document,
                expected_revision=expected_revision,
                actor_id=actor_id,
                occurred_at=occurred_at,
                reason=reason,
            )

    def upload_content(
        self,
        *,
        tenant_id: str,
        project_id: str,
        document_id: str,
        data: bytes,
        declared_content_type: str,
        filename: str | None,
        idempotency_key: str,
        expected_revision: int | None,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> DocumentContentUpload:
        """Store immutable bytes for a document and record the new version.

        Validation is server-side: the declared type must be allow-listed and
        match the sniffed payload, the size limit is enforced here and in the
        storage adapter, and the digest is derived from the bytes. A retried
        upload with the same idempotency key returns the stored version.
        """
        self._check_permission(context, tenant_id, project_id, Permission.PROJECT_WRITE)
        if actor_id != context.user_id:
            raise DocumentAuthorizationError("DOCUMENT_ACTOR_MISMATCH")
        if self.storage is None or self.content_repository is None:
            raise DocumentStorageUnavailable("DOCUMENT_STORAGE_UNAVAILABLE")
        if not isinstance(idempotency_key, str) or not idempotency_key.strip():
            raise ValueError("INVALID_DOCUMENT_IDEMPOTENCY_KEY")
        if expected_revision is not None and (
            isinstance(expected_revision, bool)
            or not isinstance(expected_revision, int)
            or expected_revision < 1
        ):
            raise ValueError("INVALID_EXPECTED_DOCUMENT_REVISION")

        current = self.store.get(tenant_id, project_id, document_id)
        if expected_revision is not None and current.revision != expected_revision:
            raise DocumentRevisionConflict("DOCUMENT_REVISION_CONFLICT")

        replay = self.content_repository.get_by_idempotency(
            tenant_id, project_id, document_id, idempotency_key
        )
        blob = validate_document_content(
            data,
            declared_content_type=declared_content_type,
            filename=filename,
            max_bytes=self.max_content_bytes,
        )
        if replay is not None:
            if (
                replay.content_hash != blob.content_hash
                or replay.content_type != blob.content_type
                or replay.byte_size != blob.byte_size
            ):
                raise DocumentIdempotencyReuse("DOCUMENT_CONTENT_IDEMPOTENCY_KEY_REUSE")
            return DocumentContentUpload(
                content=replay,
                storage_ref=replay.storage_ref,
                idempotent_replay=True,
            )

        verdict = self._scan_payload(data, blob.content_type)
        storage_ref = self.storage.put(
            tenant_id=tenant_id,
            project_id=project_id,
            content_hash=blob.content_hash,
            extension=blob.extension,
            data=bytes(data),
        )

        with self.transaction_manager.transaction():
            current = self.store.get(tenant_id, project_id, document_id)
            if expected_revision is not None and current.revision != expected_revision:
                raise DocumentRevisionConflict("DOCUMENT_REVISION_CONFLICT")
            existing = self.content_repository.get_by_idempotency(
                tenant_id, project_id, document_id, idempotency_key
            )
            if existing is not None:
                if (
                    existing.content_hash != blob.content_hash
                    or existing.content_type != blob.content_type
                    or existing.byte_size != blob.byte_size
                ):
                    raise DocumentIdempotencyReuse("DOCUMENT_CONTENT_IDEMPOTENCY_KEY_REUSE")
                return DocumentContentUpload(
                    content=existing,
                    storage_ref=existing.storage_ref,
                    idempotent_replay=True,
                )
            versions = self.content_repository.list(tenant_id, project_id, document_id)
            updated = self.store.update(
                replace(
                    current.document,
                    storage_ref=storage_ref,
                    content_hash=blob.content_hash,
                ),
                expected_revision=current.revision,
                actor_id=actor_id,
                occurred_at=occurred_at,
                event_type="content_uploaded",
                audit_reason=blob.original_filename,
            )
            version = self.content_repository.append(
                DocumentContentVersion(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    document_id=document_id,
                    version=len(versions) + 1,
                    document_revision=updated.revision,
                    storage_ref=storage_ref,
                    content_hash=blob.content_hash,
                    content_type=blob.content_type,
                    byte_size=blob.byte_size,
                    original_filename=blob.original_filename,
                    idempotency_key=idempotency_key,
                    actor_id=actor_id,
                    uploaded_at=occurred_at,
                    scan_status=verdict.status if verdict else "unscanned",
                    scan_engine=verdict.engine if verdict else "",
                    scan_engine_version=verdict.engine_version if verdict else "",
                    scan_detail=verdict.detail if verdict else "",
                )
            )
            return DocumentContentUpload(content=version, storage_ref=storage_ref)

    def download_content(
        self,
        *,
        tenant_id: str,
        project_id: str,
        document_id: str,
        context: AuthorizationContext,
        version: int | None = None,
    ) -> DocumentContentDownload:
        """Return verified bytes for the latest or a specific stored version."""
        self._check_permission(context, tenant_id, project_id, Permission.PROJECT_READ)
        if self.storage is None or self.content_repository is None:
            raise DocumentStorageUnavailable("DOCUMENT_STORAGE_UNAVAILABLE")
        current = self.store.get(tenant_id, project_id, document_id)
        if version is not None:
            if isinstance(version, bool) or not isinstance(version, int) or version < 1:
                raise ValueError("INVALID_DOCUMENT_CONTENT_VERSION")
            selected = self.content_repository.get(
                tenant_id, project_id, document_id, version
            )
            if selected is None:
                raise DocumentContentNotFound("DOCUMENT_CONTENT_NOT_FOUND")
        else:
            selected = self.content_repository.latest(tenant_id, project_id, document_id)
        if selected is None:
            # Metadata-first documents may still carry a storage reference that
            # was written before version tracking existed. Serve it only when
            # the adapter recognises the reference and the digest matches.
            document = current.document
            if self.require_scanned_content:
                # Legacy references carry no scan verdict at all, so they can
                # never satisfy a quarantine-first serving policy.
                raise DocumentContentQuarantined("DOCUMENT_CONTENT_QUARANTINED")
            if document.storage_ref.startswith("local:v1/") and document.content_hash.startswith("sha256:"):
                payload = self.storage.read(
                    document.storage_ref,
                    tenant_id=tenant_id,
                    project_id=project_id,
                    expected_content_hash=document.content_hash,
                )
                return DocumentContentDownload(
                    content_type="application/octet-stream",
                    filename=document.document_id,
                    data=payload,
                    content_hash=document.content_hash,
                    version=None,
                )
            raise DocumentContentNotFound("DOCUMENT_CONTENT_NOT_FOUND")

        if self.require_scanned_content and selected.scan_status != "clean":
            raise DocumentContentQuarantined("DOCUMENT_CONTENT_QUARANTINED")
        payload = self.storage.read(
            selected.storage_ref,
            tenant_id=tenant_id,
            project_id=project_id,
            expected_content_hash=selected.content_hash,
        )
        return DocumentContentDownload(
            content_type=selected.content_type,
            filename=selected.original_filename,
            data=payload,
            content_hash=selected.content_hash,
            version=selected.version,
        )

    def list_content(
        self,
        *,
        tenant_id: str,
        project_id: str,
        document_id: str,
        context: AuthorizationContext,
    ) -> tuple[DocumentContentVersion, ...]:
        self._check_permission(context, tenant_id, project_id, Permission.PROJECT_READ)
        if self.content_repository is None:
            raise DocumentStorageUnavailable("DOCUMENT_STORAGE_UNAVAILABLE")
        self.store.get(tenant_id, project_id, document_id)
        return self.content_repository.list(tenant_id, project_id, document_id)

    def _scan_payload(self, data: bytes, content_type: str) -> ScanVerdict | None:
        """Return a usable verdict, or fail closed when scanning is required.

        Infected payloads are rejected before any bytes reach storage, in both
        modes. A missing or broken scanner is only tolerated in the explicit
        non-strict development mode, where the version is recorded as
        ``failed``/``unscanned`` and therefore can never be served as clean.
        """
        if self.scanner is None:
            if self.require_scanned_content:
                raise DocumentScanUnavailable("DOCUMENT_SCAN_UNAVAILABLE")
            return None
        try:
            verdict = self.scanner.scan(bytes(data), content_type=content_type)
        except (DocumentScanRejected, DocumentScanUnavailable):
            raise
        except Exception as exc:
            if self.require_scanned_content:
                raise DocumentScanUnavailable("DOCUMENT_SCAN_UNAVAILABLE") from exc
            return ScanVerdict(
                status="failed",
                engine="unavailable",
                engine_version="0",
                detail=type(exc).__name__,
            )
        if not isinstance(verdict, ScanVerdict):
            raise DocumentScanError("INVALID_DOCUMENT_SCAN_RESULT")
        verdict.validate()
        if verdict.status == "infected":
            raise DocumentScanRejected("DOCUMENT_CONTENT_INFECTED")
        if self.require_scanned_content and verdict.status in {"unscanned", "failed"}:
            raise DocumentScanUnavailable("DOCUMENT_SCAN_FAILED")
        return verdict

    def _check_permission(
        self,
        context: AuthorizationContext,
        tenant_id: str,
        project_id: str,
        permission: Permission,
    ) -> None:
        if context.tenant_id != tenant_id or context.project_id != project_id:
            raise DocumentAuthorizationError("DOCUMENT_CROSS_SCOPE")
        if not context.user_id.strip():
            raise DocumentAuthorizationError("DOCUMENT_ACTOR_REQUIRED")
        if not self.authorization_policy.is_allowed(context, permission):
            raise DocumentAuthorizationError("DOCUMENT_PERMISSION_DENIED")

    def _authorize_write(
        self,
        document: DocumentRecord,
        context: AuthorizationContext,
        actor_id: str,
    ) -> None:
        if actor_id != context.user_id:
            raise DocumentAuthorizationError("DOCUMENT_ACTOR_MISMATCH")
        self._check_permission(
            context,
            document.tenant_id,
            document.project_id,
            Permission.PROJECT_WRITE,
        )

    @staticmethod
    def error_dto(exc: Exception) -> APIError:
        if isinstance(exc, DocumentContentTooLarge):
            return validation_error("DOCUMENT_CONTENT_TOO_LARGE", str(exc))
        if isinstance(exc, DocumentContentTypeRejected):
            return validation_error(str(exc) or "DOCUMENT_CONTENT_TYPE_REJECTED", str(exc))
        if isinstance(exc, DocumentContentNotFound):
            return validation_error("DOCUMENT_CONTENT_NOT_FOUND", str(exc))
        if isinstance(exc, DocumentContentQuarantined):
            return conflict_error(
                str(exc) or "DOCUMENT_CONTENT_QUARANTINED", str(exc)
            )
        if isinstance(exc, DocumentScanRejected):
            return conflict_error(str(exc) or "DOCUMENT_CONTENT_INFECTED", str(exc))
        if isinstance(exc, DocumentScanUnavailable):
            return persistence_error(str(exc) or "DOCUMENT_SCAN_UNAVAILABLE", str(exc))
        if isinstance(exc, DocumentScanError):
            return validation_error(str(exc) or type(exc).__name__, str(exc))
        if isinstance(exc, (DocumentContentHashMismatch, DocumentContentIntegrityError)):
            return validation_error(str(exc), str(exc))
        if isinstance(exc, DocumentStorageUnavailable):
            return validation_error("DOCUMENT_STORAGE_UNAVAILABLE", str(exc))
        if isinstance(exc, DocumentStorageError):
            return validation_error(str(exc) or type(exc).__name__, str(exc))
        if isinstance(exc, KeyError):
            code = str(exc.args[0]) if exc.args else "DOCUMENT_NOT_FOUND"
            return validation_error(code, code)
        if isinstance(exc, DocumentRevisionConflict):
            return conflict_error("DOCUMENT_REVISION_CONFLICT", str(exc), retryable=True)
        if isinstance(exc, DocumentIdempotencyReuse):
            code = str(exc) or "DOCUMENT_IDEMPOTENCY_KEY_REUSE"
            return conflict_error(code, str(exc))
        if isinstance(exc, DocumentAuthorizationError):
            return authorization_error(str(exc), str(exc))
        if isinstance(exc, DocumentApprovalTransitionError):
            return validation_error("DOCUMENT_INVALID_STATUS_TRANSITION", str(exc))
        if isinstance(exc, ValueError):
            return validation_error(str(exc) or type(exc).__name__, str(exc))
        return validation_error(type(exc).__name__, str(exc))
