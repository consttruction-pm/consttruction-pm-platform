from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from construction_pm.application.authorization import AuthorizationContext

from .application import BackendP0ApplicationService
from .errors import BackendApplicationError, ErrorCategory
from .models import Record
from .resource_envelope import to_resource_envelope
from .workspace_read import WorkspaceControlRoomReadService


@dataclass(frozen=True)
class BackendP0API:
    service: BackendP0ApplicationService
    workspace_read_service: WorkspaceControlRoomReadService | None = None

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

    def save_resource(
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
        return to_resource_envelope(stored)

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

    def read_workspace_control_room(
        self,
        *,
        tenant_id: str,
        project_id: str,
        revision: int,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any] | None:
        try:
            if self.workspace_read_service is None:
                raise BackendApplicationError(
                    ErrorCategory.VALIDATION,
                    "WORKSPACE_READ_NOT_CONFIGURED",
                    "Workspace control-room read service is not configured",
                )
            from .models import BackendScope
            snapshot = self.workspace_read_service.read(
                BackendScope(tenant_id, project_id, revision),
                auth_context=auth_context,
            )
        except BackendApplicationError as exc:
            return exc.to_dto()
        return _json_safe(snapshot) if snapshot is not None else None

    def read_resource(self, record: Record, *, auth_context: AuthorizationContext) -> dict[str, Any] | None:
        try:
            stored = self.service.get(record, auth_context=auth_context)
        except BackendApplicationError as exc:
            return exc.to_dto()
        if stored is None:
            return None
        return to_resource_envelope(stored)


def _json_safe(value: Any) -> Any:
    """Convert domain decimals to canonical exact decimal strings at the transport boundary."""
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value
