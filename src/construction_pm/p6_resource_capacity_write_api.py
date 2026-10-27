"""Authorized write boundary for typed effective-dated resource capacity.

The client never supplies an identity, derived rate, or provenance. The server
computes the content-addressed identity, derives the source from the
authenticated principal, validates the effective interval and rejects ambiguous
overlaps. Closing an open-ended segment is append-only: the prior row is retained
and linked to a new closed segment through the supersession table.
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
from .p6_resource_capacity_repository import (
    P6ResourceCapacityApplicationService,
    P6ResourceCapacityRecord,
    P6ResourceCapacityRepositoryError,
    P6ResourceCapacityWriteResult,
)
from .resources.max_units_time import (
    ResourceCapacityBasis,
    ResourceCapacityError,
    ResourceMaxUnitsTime,
)

P6_RESOURCE_CAPACITY_WRITE_API_VERSION = "p6-resource-capacity-write-api.v1"

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


def _capacity_dto(segment: ResourceMaxUnitsTime) -> dict[str, Any]:
    return {
        "resource_id": segment.resource_id,
        "identity": segment.identity,
        "max_units": segment.max_units,
        "unit_basis": segment.unit_basis.value,
        "hours_per_time_period": segment.hours_per_time_period,
        "units_per_hour": segment.units_per_hour,
        "effective_from": segment.effective_from.isoformat(),
        "effective_to": None
        if segment.effective_to is None
        else segment.effective_to.isoformat(),
        "source": segment.source,
    }


def _decimal(value: object, code: str) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ResourceCapacityError(code) from exc
    if not parsed.is_finite():
        raise ResourceCapacityError(code)
    return parsed


def _date(value: object, code: str) -> date:
    if not isinstance(value, str) or not value.strip():
        raise ResourceCapacityError(code)
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ResourceCapacityError(code) from exc


@dataclass(frozen=True)
class P6ResourceCapacityWriteAPI:
    service: P6ResourceCapacityApplicationService
    authorization_policy: AuthorizationPolicy
    clock: object | None = None

    def save_effective_change(
        self,
        scope: BackendScope,
        *,
        resource_id: object,
        max_units: object,
        unit_basis: object,
        hours_per_time_period: object,
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
            raise ResourceCapacityError("INVALID_EXPECTED_REVISION")
        if expected_revision != scope.project_revision:
            raise ResourceCapacityError("REVISION_CONFLICT")
        if close_open_segment is not None and not isinstance(
            close_open_segment, bool
        ):
            raise ResourceCapacityError("INVALID_CAPACITY_CLOSE_FLAG")
        if not isinstance(resource_id, str) or not resource_id.strip():
            raise ResourceCapacityError("INVALID_RESOURCE_ID")
        if resource_id != resource_id.strip() or "/" in resource_id:
            raise ResourceCapacityError("INVALID_RESOURCE_ID")
        try:
            basis = ResourceCapacityBasis(str(unit_basis))
        except ValueError as exc:
            raise ResourceCapacityError("INVALID_CAPACITY_BASIS") from exc
        from_date = _date(effective_from, "INVALID_EFFECTIVE_FROM")
        to_date = (
            None
            if effective_to is None
            else _date(effective_to, "INVALID_EFFECTIVE_TO")
        )
        segment = ResourceMaxUnitsTime.create(
            resource_id=resource_id,
            max_units=_decimal(max_units, "INVALID_MAX_UNITS"),
            unit_basis=basis,
            hours_per_time_period=_decimal(
                hours_per_time_period, "INVALID_HOURS_PER_TIME_PERIOD"
            ),
            effective_from=from_date,
            effective_to=to_date,
            # Provenance is authenticated, not client-supplied. The same values
            # submitted by the same principal therefore remain content-identical.
            source=f"{SOURCE_PREFIX}:{auth_context.user_id}",
        )
        record = P6ResourceCapacityRecord(scope=scope, segment=segment)
        try:
            result = self.service.save_effective_change(
                record,
                close_open_segment=bool(close_open_segment),
                recorded_at=self._now(),
            )
        except ResourceCapacityError:
            raise
        except P6ResourceCapacityRepositoryError:
            raise
        return _write_dto(result)

    def _now(self) -> datetime:
        clock = self.clock
        if clock is not None and hasattr(clock, "now"):
            value = clock.now()
            if isinstance(value, datetime):
                return value
        return datetime.now(timezone.utc)


def _write_dto(result: P6ResourceCapacityWriteResult) -> dict[str, Any]:
    superseded = None
    if result.superseded_identity is not None and result.closed_segment is not None:
        superseded = {
            "identity": result.superseded_identity,
            "replacement_identity": result.closed_segment.identity,
            "effective_to": result.closed_segment.effective_to.isoformat()
            if result.closed_segment.effective_to is not None
            else None,
        }
    return {
        "contract_version": P6_RESOURCE_CAPACITY_WRITE_API_VERSION,
        "kind": "resource_capacity_write",
        "scope": _scope_dto(result.record.scope),
        "capacity": _capacity_dto(result.record.segment),
        "superseded": superseded,
        "status": "REGISTERED",
    }


__all__ = [
    "P6_RESOURCE_CAPACITY_WRITE_API_VERSION",
    "P6ResourceCapacityWriteAPI",
    "SOURCE_PREFIX",
]
