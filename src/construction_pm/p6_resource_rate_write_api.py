"""Authorized write boundary for effective-dated resource rate facts.

The client never supplies an identity, provenance or derived currency. The
server computes the content-addressed identity, derives the source from the
authenticated principal, validates the effective interval and rejects ambiguous
overlaps. Closing an open-ended fact is append-only: the prior row is retained
and linked to a new closed fact through the supersession table.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from .application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)
from .backend_p0.models import BackendScope
from .p6_resource_rate_repository import (
    P6ResourceRateApplicationService,
    P6ResourceRateRecord,
    P6ResourceRateRepositoryError,
    P6ResourceRateWriteResult,
)
from .resources.models import CostBasis
from .resources.rate_facts import ResourceRateFact, ResourceRateFactError

P6_RESOURCE_RATE_WRITE_API_VERSION = "p6-resource-rate-write-api.v1"

SOURCE_PREFIX = "manual-entry"


def _require_scope(scope: BackendScope, auth_context: AuthorizationContext) -> None:
    scope.validate()
    auth_context.validate()
    if (
        scope.tenant_id != auth_context.tenant_id
        or scope.project_id != auth_context.project_id
    ):
        raise AuthorizationError("CROSS_SCOPE_ACCESS")


def _require_write(
    policy: AuthorizationPolicy, auth_context: AuthorizationContext
) -> None:
    if not policy.is_allowed(auth_context, Permission.PROJECT_WRITE):
        raise AuthorizationError(
            f"authorization denied for permission={Permission.PROJECT_WRITE.value}"
        )


def _scope_dto(scope: BackendScope) -> dict[str, Any]:
    return {
        "tenant_id": scope.tenant_id,
        "project_id": scope.project_id,
        "project_revision": scope.project_revision,
    }


def _rate_dto(fact: ResourceRateFact) -> dict[str, Any]:
    return {
        "resource_id": fact.resource_id,
        "identity": fact.identity,
        "rate": fact.rate,
        "basis": fact.basis.value,
        "currency": fact.currency,
        "unit": fact.unit,
        "effective_from": fact.effective_from.isoformat(),
        "effective_to": None
        if fact.effective_to is None
        else fact.effective_to.isoformat(),
        "source": fact.source,
    }


def _decimal(value: object, code: str) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ResourceRateFactError(code) from exc
    if not parsed.is_finite():
        raise ResourceRateFactError(code)
    return parsed


def _date(value: object, code: str) -> date:
    if not isinstance(value, str) or not value.strip():
        raise ResourceRateFactError(code)
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ResourceRateFactError(code) from exc


def _text(value: object, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ResourceRateFactError(code)
    if value != value.strip():
        raise ResourceRateFactError(code)
    return value


@dataclass(frozen=True)
class P6ResourceRateWriteAPI:
    service: P6ResourceRateApplicationService
    authorization_policy: AuthorizationPolicy
    clock: object | None = None

    def save_effective_change(
        self,
        scope: BackendScope,
        *,
        resource_id: object,
        rate: object,
        basis: object,
        currency: object,
        unit: object,
        effective_from: object,
        effective_to: object,
        expected_revision: object,
        close_open_segment: object,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(scope, auth_context)
        _require_write(self.authorization_policy, auth_context)
        if (
            isinstance(expected_revision, bool)
            or not isinstance(expected_revision, int)
            or expected_revision < 0
        ):
            raise ResourceRateFactError("INVALID_EXPECTED_REVISION")
        if expected_revision != scope.project_revision:
            raise ResourceRateFactError("REVISION_CONFLICT")
        if close_open_segment is not None and not isinstance(
            close_open_segment, bool
        ):
            raise ResourceRateFactError("INVALID_RATE_CLOSE_FLAG")
        resource = _text(resource_id, "INVALID_RESOURCE_ID")
        if "/" in resource:
            raise ResourceRateFactError("INVALID_RESOURCE_ID")
        try:
            parsed_basis = CostBasis(str(basis))
        except ValueError as exc:
            raise ResourceRateFactError("INVALID_RATE_BASIS") from exc
        from_date = _date(effective_from, "INVALID_RATE_EFFECTIVE_FROM")
        to_date = (
            None
            if effective_to is None
            else _date(effective_to, "INVALID_RATE_EFFECTIVE_TO")
        )
        fact = ResourceRateFact.create(
            resource_id=resource,
            rate=_decimal(rate, "INVALID_RATE_VALUE"),
            basis=parsed_basis,
            currency=_text(currency, "INVALID_RATE_CURRENCY"),
            unit=_text(unit, "INVALID_RATE_UNIT"),
            effective_from=from_date,
            effective_to=to_date,
            # Provenance is authenticated, not client-supplied. The same values
            # submitted by the same principal therefore remain content-identical.
            source=f"{SOURCE_PREFIX}:{auth_context.user_id}",
        )
        record = P6ResourceRateRecord(scope=scope, fact=fact)
        try:
            result = self.service.save_effective_change(
                record,
                close_open_segment=bool(close_open_segment),
                recorded_at=self._now(),
            )
        except ResourceRateFactError:
            raise
        except P6ResourceRateRepositoryError:
            raise
        return _write_dto(result)

    def _now(self) -> datetime:
        clock = self.clock
        if clock is not None and hasattr(clock, "now"):
            value = clock.now()
            if isinstance(value, datetime):
                return value
        return datetime.now(timezone.utc)


def _write_dto(result: P6ResourceRateWriteResult) -> dict[str, Any]:
    superseded = None
    if result.superseded_identity is not None and result.closed_fact is not None:
        superseded = {
            "identity": result.superseded_identity,
            "replacement_identity": result.closed_fact.identity,
            "effective_to": result.closed_fact.effective_to.isoformat()
            if result.closed_fact.effective_to is not None
            else None,
        }
    return {
        "contract_version": P6_RESOURCE_RATE_WRITE_API_VERSION,
        "kind": "resource_rate_write",
        "scope": _scope_dto(result.record.scope),
        "rate": _rate_dto(result.record.fact),
        "superseded": superseded,
        "status": "REGISTERED",
    }


__all__ = [
    "P6_RESOURCE_RATE_WRITE_API_VERSION",
    "P6ResourceRateWriteAPI",
    "SOURCE_PREFIX",
]
