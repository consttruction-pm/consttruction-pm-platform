"""Versioned transport adapter for project and layout backup/recovery."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable

from .application.authorization import AuthorizationContext
from .backend_p0.models import BackendScope
from .backup_application import BackupAuthorizationError, BackupError, BackupService
from .backup_persistence import BackupIdempotencyReuse, BackupPersistenceError

BACKUP_API_VERSION = "p6-backup-api.v1"


def _error_dto(error: Exception) -> dict[str, Any]:
    code = str(error)
    if isinstance(error, BackupAuthorizationError):
        category = "authorization"
    elif isinstance(error, BackupIdempotencyReuse):
        category = "conflict"
    elif isinstance(error, (BackupError, BackupPersistenceError)):
        category = (
            "not_found"
            if code.endswith("_NOT_FOUND")
            else "conflict"
            if code in {"BACKUP_IDEMPOTENCY_KEY_REUSE"}
            else "validation"
        )
    else:
        code = "BACKUP_REQUEST_INVALID"
        category = "validation"
    return {
        "contract_version": BACKUP_API_VERSION,
        "code": code,
        "category": category,
        "message": code,
    }


@dataclass(frozen=True)
class BackupAPI:
    """Thin DTO boundary over the backup application service."""

    service: BackupService

    def create(
        self,
        *,
        scope: BackendScope,
        kind: str,
        label: str,
        idempotency_key: str,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> dict[str, Any]:
        try:
            result = self.service.capture(
                scope=scope,
                kind=kind,
                label=label,
                idempotency_key=idempotency_key,
                context=context,
                actor_id=actor_id,
                occurred_at=occurred_at,
            )
        except Exception as exc:  # noqa: BLE001 - bounded transport boundary
            return _error_dto(exc)
        return {"contract_version": BACKUP_API_VERSION, **result}

    def snapshots(
        self,
        *,
        scope: BackendScope,
        context: AuthorizationContext,
        limit: int = 50,
    ) -> dict[str, Any]:
        try:
            items = self.service.snapshots(
                scope=scope, context=context, limit=limit
            )
        except Exception as exc:  # noqa: BLE001
            return _error_dto(exc)
        return {"contract_version": BACKUP_API_VERSION, "snapshots": list(items)}

    def snapshot(
        self,
        *,
        scope: BackendScope,
        snapshot_id: str,
        context: AuthorizationContext,
    ) -> dict[str, Any]:
        try:
            result = self.service.snapshot(
                scope=scope, snapshot_id=snapshot_id, context=context
            )
        except Exception as exc:  # noqa: BLE001
            return _error_dto(exc)
        return {"contract_version": BACKUP_API_VERSION, **result}

    def content(
        self,
        *,
        scope: BackendScope,
        snapshot_id: str,
        context: AuthorizationContext,
    ) -> dict[str, Any]:
        try:
            result = self.service.content(
                scope=scope, snapshot_id=snapshot_id, context=context
            )
        except Exception as exc:  # noqa: BLE001
            return _error_dto(exc)
        return {"contract_version": BACKUP_API_VERSION, **result}

    def restore(
        self,
        *,
        scope: BackendScope,
        snapshot_id: str,
        mode: str,
        sections: Iterable[str] | None,
        idempotency_key: str,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> dict[str, Any]:
        try:
            result = self.service.restore(
                scope=scope,
                snapshot_id=snapshot_id,
                mode=mode,
                sections=sections,
                idempotency_key=idempotency_key,
                context=context,
                actor_id=actor_id,
                occurred_at=occurred_at,
            )
        except Exception as exc:  # noqa: BLE001
            return _error_dto(exc)
        return {"contract_version": BACKUP_API_VERSION, **result}

    def restores(
        self,
        *,
        scope: BackendScope,
        context: AuthorizationContext,
        limit: int = 50,
    ) -> dict[str, Any]:
        try:
            items = self.service.restores(
                scope=scope, context=context, limit=limit
            )
        except Exception as exc:  # noqa: BLE001
            return _error_dto(exc)
        return {"contract_version": BACKUP_API_VERSION, "runs": list(items)}


__all__ = ["BACKUP_API_VERSION", "BackupAPI"]
