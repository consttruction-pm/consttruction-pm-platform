"""Versioned transport adapter for project CSV exchange."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .application.authorization import AuthorizationContext
from .backend_p0.models import BackendScope
from .exchange_application import (
    EXCHANGE_EXPORT_FORMATS,
    ExchangeAuthorizationError,
    ExchangeError,
    ExchangeService,
)
from .exchange_persistence import ExchangeIdempotencyReuse, ExchangePersistenceError

EXCHANGE_API_VERSION = "p6-exchange-api.v1"


def _error_dto(error: Exception) -> dict[str, Any]:
    code = str(error)
    if isinstance(error, ExchangeAuthorizationError):
        category = "authorization"
    elif isinstance(error, ExchangeIdempotencyReuse):
        category = "conflict"
    elif isinstance(error, (ExchangeError, ExchangePersistenceError)):
        category = "validation"
    else:
        code = "EXCHANGE_REQUEST_INVALID"
        category = "validation"
    return {
        "contract_version": EXCHANGE_API_VERSION,
        "code": code,
        "category": category,
        "message": code,
    }


@dataclass(frozen=True)
class ExchangeAPI:
    """Thin DTO boundary over the exchange application service."""

    service: ExchangeService

    def catalogue(self) -> dict[str, Any]:
        return {
            "contract_version": EXCHANGE_API_VERSION,
            "datasets": list(self.service.catalogue()),
            "export_formats": list(EXCHANGE_EXPORT_FORMATS),
            "max_import_chars": 1_000_000,
        }

    def export(
        self,
        *,
        scope: BackendScope,
        dataset: str,
        context: AuthorizationContext,
        generated_at: datetime,
        export_format: str = "csv",
    ) -> dict[str, Any]:
        try:
            result = self.service.export(
                scope=scope,
                dataset=dataset,
                context=context,
                generated_at=generated_at,
                export_format=export_format,
            )
        except Exception as exc:  # noqa: BLE001 - bounded transport boundary
            return _error_dto(exc)
        return {"contract_version": EXCHANGE_API_VERSION, **result}

    def preview_import(
        self,
        *,
        scope: BackendScope,
        dataset: str,
        content: str,
        context: AuthorizationContext,
        occurred_at: datetime,
        import_format: str = "csv",
    ) -> dict[str, Any]:
        try:
            result = self.service.preview_import(
                scope=scope,
                dataset=dataset,
                content=content,
                context=context,
                occurred_at=occurred_at,
                import_format=import_format,
            )
        except Exception as exc:  # noqa: BLE001
            return _error_dto(exc)
        return {"contract_version": EXCHANGE_API_VERSION, **result}

    def apply_import(
        self,
        *,
        scope: BackendScope,
        dataset: str,
        content: str,
        idempotency_key: str,
        context: AuthorizationContext,
        occurred_at: datetime,
        import_format: str = "csv",
    ) -> dict[str, Any]:
        try:
            result = self.service.apply_import(
                scope=scope,
                dataset=dataset,
                content=content,
                idempotency_key=idempotency_key,
                context=context,
                occurred_at=occurred_at,
                import_format=import_format,
            )
        except Exception as exc:  # noqa: BLE001
            return _error_dto(exc)
        return {"contract_version": EXCHANGE_API_VERSION, **result}

    def imports(
        self,
        *,
        scope: BackendScope,
        context: AuthorizationContext,
        limit: int = 50,
    ) -> dict[str, Any]:
        try:
            runs = self.service.imports(
                scope=scope, context=context, limit=limit
            )
        except Exception as exc:  # noqa: BLE001
            return _error_dto(exc)
        return {"contract_version": EXCHANGE_API_VERSION, "runs": list(runs)}


__all__ = ["EXCHANGE_API_VERSION", "ExchangeAPI"]
