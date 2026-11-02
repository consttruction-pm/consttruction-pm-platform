from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from .application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)
from .backend_p0.models import BackendScope
from .p6_earned_value_read_model import (
    P6_EARNED_VALUE_READ_MODEL_VERSION,
    P6EarnedValueReadModelError,
    P6EarnedValueReadModelService,
)


def _require_scope(scope: BackendScope, auth_context: AuthorizationContext) -> None:
    scope.validate()
    auth_context.validate()
    if (
        scope.tenant_id != auth_context.tenant_id
        or scope.project_id != auth_context.project_id
    ):
        raise AuthorizationError("CROSS_SCOPE_ACCESS")


@dataclass(frozen=True)
class P6EarnedValueReadModelAPI:
    """Typed transport boundary for an authoritative EVM measurement."""

    service: P6EarnedValueReadModelService
    authorization_policy: AuthorizationPolicy

    def get(
        self,
        scope: BackendScope,
        baseline_id: str,
        *,
        data_date: date,
        currency: str,
        auth_context: AuthorizationContext,
        etc_method: str | None = None,
        performance_factor: Decimal | str | float | int | None = None,
    ) -> dict[str, Any]:
        _require_scope(scope, auth_context)
        if not self.authorization_policy.is_allowed(
            auth_context, Permission.PROJECT_READ
        ):
            raise AuthorizationError(
                "authorization denied for permission=project.read"
            )
        if isinstance(data_date, datetime):
            raise P6EarnedValueReadModelError("EVM_DATA_DATE_INVALID")
        kwargs: dict[str, Any] = {}
        if etc_method is not None:
            kwargs["etc_method"] = etc_method
        if performance_factor is not None:
            kwargs["performance_factor"] = Decimal(str(performance_factor))
        try:
            result = self.service.read(
                scope,
                baseline_id,
                data_date=data_date,
                currency=currency,
                **kwargs,
            )
        except P6EarnedValueReadModelError:
            raise
        return result.to_payload()


__all__ = [
    "P6_EARNED_VALUE_READ_MODEL_VERSION",
    "P6EarnedValueReadModelAPI",
]
