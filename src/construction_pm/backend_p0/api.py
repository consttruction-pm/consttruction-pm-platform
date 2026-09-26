from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from construction_pm.application.authorization import AuthorizationContext

from .application import BackendP0ApplicationService
from .errors import BackendApplicationError
from .models import Record


@dataclass(frozen=True)
class BackendP0API:
    service: BackendP0ApplicationService

    def save(
        self,
        record: Record,
        *,
        auth_context: AuthorizationContext,
        expected_revision: int | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        try:
            stored = self.service.save(
                record,
                auth_context=auth_context,
                expected_revision=expected_revision,
                idempotency_key=idempotency_key,
            )
        except BackendApplicationError as exc:
            return exc.to_dto()
        dto = _json_safe(stored.record.as_dict())
        dto["record_revision"] = stored.record_revision
        dto["operation"] = "save"
        return dto

    def read(self, record: Record, *, auth_context: AuthorizationContext) -> dict[str, Any] | None:
        try:
            stored = self.service.get(record, auth_context=auth_context)
        except BackendApplicationError as exc:
            return exc.to_dto()
        if stored is None:
            return None
        dto = _json_safe(stored.record.as_dict())
        dto["record_revision"] = stored.record_revision
        return dto


def _json_safe(value: Any) -> Any:
    """Convert domain decimals to canonical exact decimal strings at the transport boundary."""
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value
