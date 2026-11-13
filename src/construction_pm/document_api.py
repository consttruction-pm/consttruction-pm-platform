from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .application.authorization import AuthorizationContext
from .api_errors import APIError, persistence_error
from .document_application import (
    DocumentApplicationService,
    DocumentContentDownload,
)
from .document_ocr import DocumentOcrService
from .document_persistence import DocumentAuditEvent, DocumentRecord, StoredDocument
from .document_retention import DocumentRetentionService

DOCUMENT_API_VERSION = "1.0"
DOCUMENT_CONTENT_API_VERSION = "1.0"
DOCUMENT_OCR_API_VERSION = "1.0"
DOCUMENT_RETENTION_API_VERSION = "1.0"


@dataclass(frozen=True)
class DocumentAPI:
    """Thin versioned transport adapter over the document application boundary."""

    service: DocumentApplicationService
    ocr: DocumentOcrService | None = None
    retention: DocumentRetentionService | None = None

    def create(
        self,
        document: DocumentRecord,
        *,
        context: AuthorizationContext,
        idempotency_key: str,
        actor_id: str,
        occurred_at: datetime,
    ) -> dict[str, Any]:
        try:
            return _resource(self.service.create(
                document,
                context=context,
                idempotency_key=idempotency_key,
                actor_id=actor_id,
                occurred_at=occurred_at,
            ))
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def read(
        self,
        *,
        tenant_id: str,
        project_id: str,
        document_id: str,
        context: AuthorizationContext,
    ) -> dict[str, Any]:
        try:
            return _resource(self.service.read(
                tenant_id=tenant_id,
                project_id=project_id,
                document_id=document_id,
                context=context,
            ))
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def list(
        self,
        *,
        tenant_id: str,
        project_id: str,
        context: AuthorizationContext,
        resource_type: str | None = None,
        status: str | None = None,
        search: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        try:
            kwargs: dict[str, Any] = {}
            if limit is not None:
                kwargs["limit"] = limit
            documents = self.service.list(
                tenant_id=tenant_id,
                project_id=project_id,
                context=context,
                resource_type=resource_type,
                status=status,
                search=search,
                **kwargs,
            )
            return {
                "contract_version": DOCUMENT_API_VERSION,
                "documents": [_resource(item) for item in documents],
            }
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def history(
        self,
        *,
        tenant_id: str,
        project_id: str,
        document_id: str,
        context: AuthorizationContext,
    ) -> dict[str, Any]:
        try:
            events = self.service.history(
                tenant_id=tenant_id,
                project_id=project_id,
                document_id=document_id,
                context=context,
            )
            return {
                "contract_version": DOCUMENT_API_VERSION,
                "events": [_event(event) for event in events],
            }
        except Exception as exc:
            return _error(self.service.error_dto(exc))

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
    ) -> dict[str, Any]:
        try:
            return _resource(self.service.update(
                document,
                expected_revision=expected_revision,
                context=context,
                actor_id=actor_id,
                occurred_at=occurred_at,
                event_type=event_type,
                audit_reason=audit_reason,
            ))
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def upload_content(
        self,
        *,
        tenant_id: str,
        project_id: str,
        document_id: str,
        data: bytes,
        content_type: str,
        filename: str | None,
        idempotency_key: str,
        expected_revision: int | None,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> dict[str, Any]:
        try:
            upload = self.service.upload_content(
                tenant_id=tenant_id,
                project_id=project_id,
                document_id=document_id,
                data=data,
                declared_content_type=content_type,
                filename=filename,
                idempotency_key=idempotency_key,
                expected_revision=expected_revision,
                context=context,
                actor_id=actor_id,
                occurred_at=occurred_at,
            )
            return {
                "contract_version": DOCUMENT_CONTENT_API_VERSION,
                "document_id": document_id,
                "content": upload.content.as_dict(),
                "storage_ref": upload.storage_ref,
                "idempotent_replay": upload.idempotent_replay,
            }
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def download_content(
        self,
        *,
        tenant_id: str,
        project_id: str,
        document_id: str,
        context: AuthorizationContext,
        version: int | None = None,
    ) -> DocumentContentDownload | dict[str, Any]:
        try:
            return self.service.download_content(
                tenant_id=tenant_id,
                project_id=project_id,
                document_id=document_id,
                context=context,
                version=version,
            )
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def list_content_versions(
        self,
        *,
        tenant_id: str,
        project_id: str,
        document_id: str,
        context: AuthorizationContext,
    ) -> dict[str, Any]:
        try:
            versions = self.service.list_content(
                tenant_id=tenant_id,
                project_id=project_id,
                document_id=document_id,
                context=context,
            )
            return {
                "contract_version": DOCUMENT_CONTENT_API_VERSION,
                "document_id": document_id,
                "versions": [version.as_dict() for version in versions],
            }
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def transition_status(
        self,
        document: DocumentRecord,
        *,
        expected_revision: int,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
        reason: str = "",
    ) -> dict[str, Any]:
        try:
            return _resource(self.service.transition_status(
                document,
                expected_revision=expected_revision,
                context=context,
                actor_id=actor_id,
                occurred_at=occurred_at,
                reason=reason,
            ))
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def request_ocr(
        self,
        *,
        tenant_id: str,
        project_id: str,
        document_id: str,
        version: int,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> dict[str, Any]:
        if self.ocr is None:
            return _error(persistence_error(
                "DOCUMENT_OCR_UNAVAILABLE", "DOCUMENT_OCR_UNAVAILABLE"
            ))
        try:
            job = self.ocr.request(
                tenant_id=tenant_id,
                project_id=project_id,
                document_id=document_id,
                version=version,
                context=context,
                actor_id=actor_id,
                occurred_at=occurred_at,
            )
            return {
                "contract_version": DOCUMENT_OCR_API_VERSION,
                "document_id": document_id,
                "ocr": job.as_dict(include_text=False),
            }
        except Exception as exc:
            return _error(self.ocr.error_dto(exc))

    def read_ocr(
        self,
        *,
        tenant_id: str,
        project_id: str,
        document_id: str,
        version: int,
        context: AuthorizationContext,
    ) -> dict[str, Any]:
        if self.ocr is None:
            return _error(persistence_error(
                "DOCUMENT_OCR_UNAVAILABLE", "DOCUMENT_OCR_UNAVAILABLE"
            ))
        try:
            job = self.ocr.read(
                tenant_id=tenant_id,
                project_id=project_id,
                document_id=document_id,
                version=version,
                context=context,
            )
            return {
                "contract_version": DOCUMENT_OCR_API_VERSION,
                "document_id": document_id,
                "ocr": job.as_dict(include_text=True),
            }
        except Exception as exc:
            return _error(self.ocr.error_dto(exc))

    def list_ocr(
        self,
        *,
        tenant_id: str,
        project_id: str,
        document_id: str,
        context: AuthorizationContext,
    ) -> dict[str, Any]:
        if self.ocr is None:
            return _error(persistence_error(
                "DOCUMENT_OCR_UNAVAILABLE", "DOCUMENT_OCR_UNAVAILABLE"
            ))
        try:
            jobs = self.ocr.list(
                tenant_id=tenant_id,
                project_id=project_id,
                document_id=document_id,
                context=context,
            )
            return {
                "contract_version": DOCUMENT_OCR_API_VERSION,
                "document_id": document_id,
                "jobs": [job.as_dict(include_text=False) for job in jobs],
            }
        except Exception as exc:
            return _error(self.ocr.error_dto(exc))

    def retry_ocr(
        self,
        *,
        tenant_id: str,
        project_id: str,
        document_id: str,
        version: int,
        context: AuthorizationContext,
        occurred_at: datetime,
    ) -> dict[str, Any]:
        if self.ocr is None:
            return _error(persistence_error(
                "DOCUMENT_OCR_UNAVAILABLE", "DOCUMENT_OCR_UNAVAILABLE"
            ))
        try:
            job = self.ocr.retry(
                tenant_id=tenant_id,
                project_id=project_id,
                document_id=document_id,
                version=version,
                context=context,
                occurred_at=occurred_at,
            )
            return {
                "contract_version": DOCUMENT_OCR_API_VERSION,
                "document_id": document_id,
                "ocr": job.as_dict(include_text=False),
            }
        except Exception as exc:
            return _error(self.ocr.error_dto(exc))

    def read_retention(
        self,
        *,
        tenant_id: str,
        project_id: str,
        document_id: str,
        context: AuthorizationContext,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        if self.retention is None:
            return _error(persistence_error(
                "DOCUMENT_RETENTION_UNAVAILABLE", "DOCUMENT_RETENTION_UNAVAILABLE"
            ))
        try:
            summary = self.retention.read(
                tenant_id=tenant_id,
                project_id=project_id,
                document_id=document_id,
                context=context,
                now=now,
            )
            return {
                "contract_version": DOCUMENT_RETENTION_API_VERSION,
                "document_id": document_id,
                "retention": summary,
            }
        except Exception as exc:
            return _error(self.retention.error_dto(exc))

    def set_retention(
        self,
        *,
        tenant_id: str,
        project_id: str,
        document_id: str,
        retain_days: int,
        legal_hold: bool,
        reason: str,
        expected_revision: int,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> dict[str, Any]:
        if self.retention is None:
            return _error(persistence_error(
                "DOCUMENT_RETENTION_UNAVAILABLE", "DOCUMENT_RETENTION_UNAVAILABLE"
            ))
        try:
            policy = self.retention.set_policy(
                tenant_id=tenant_id,
                project_id=project_id,
                document_id=document_id,
                retain_days=retain_days,
                legal_hold=legal_hold,
                reason=reason,
                expected_revision=expected_revision,
                context=context,
                actor_id=actor_id,
                occurred_at=occurred_at,
            )
            return {
                "contract_version": DOCUMENT_RETENTION_API_VERSION,
                "document_id": document_id,
                "policy": policy.as_dict(),
            }
        except Exception as exc:
            return _error(self.retention.error_dto(exc))

    def dispose_content(
        self,
        *,
        tenant_id: str,
        project_id: str,
        document_id: str,
        version: int,
        confirm: str,
        reason: str,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> dict[str, Any]:
        if self.retention is None:
            return _error(persistence_error(
                "DOCUMENT_RETENTION_UNAVAILABLE", "DOCUMENT_RETENTION_UNAVAILABLE"
            ))
        try:
            disposition = self.retention.dispose(
                tenant_id=tenant_id,
                project_id=project_id,
                document_id=document_id,
                version=version,
                confirm=confirm,
                reason=reason,
                context=context,
                actor_id=actor_id,
                occurred_at=occurred_at,
            )
            return {
                "contract_version": DOCUMENT_RETENTION_API_VERSION,
                "document_id": document_id,
                "disposition": disposition.as_dict(),
            }
        except Exception as exc:
            return _error(self.retention.error_dto(exc))


def _resource(stored: StoredDocument) -> dict[str, Any]:
    payload = stored.document.as_dict()
    payload.update({"contract_version": DOCUMENT_API_VERSION, "revision": stored.revision})
    return payload


def _event(event: DocumentAuditEvent) -> dict[str, Any]:
    return {
        "document_id": event.document_id,
        "revision": event.revision,
        "event_type": event.event_type,
        "actor_id": event.actor_id,
        "occurred_at": event.occurred_at.isoformat(),
        "reason": event.reason,
    }


def _error(error: APIError) -> dict[str, Any]:
    error.validate()
    return {
        "contract_version": DOCUMENT_API_VERSION,
        "category": error.category.value,
        "code": error.code,
        "message": error.message,
        "retryable": error.retryable,
    }
