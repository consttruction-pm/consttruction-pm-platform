"""Typed, effective-dated resource price/rate facts.

P6 resource prices are effective-dated: the rate in force on a working day is
selected by the interval that contains that day. This module models the rate
fact itself, independently of any request-supplied cost:

* a fact carries an explicit ``CostBasis`` and currency;
* its content identity is a hash of the complete priced content, so identical
  replays are idempotent and divergent content cannot reuse an identity;
* effective intervals never overlap, so a day resolves to exactly one rate;
* the model never converts currency and never assumes a calendar or an
  hours-per-day factor.

Persistence and HTTP layers build on these facts; nothing here reads a
repository or a clock.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from .models import CostBasis, ResourceRate


class ResourceRateFactError(ValueError):
    """Raised when a resource rate fact is invalid or unresolvable."""


def _decimal_token(value: Decimal) -> str:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ResourceRateFactError("INVALID_RATE_VALUE")
    normalized = value.normalize()
    return format(normalized, "f") if normalized != 0 else "0"


def _text(value: object, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ResourceRateFactError(code)
    return value.strip()


def _effective_date(value: object, code: str) -> date:
    if not isinstance(value, date) or isinstance(value, datetime):
        raise ResourceRateFactError(code)
    return value


def compute_rate_identity(
    *,
    resource_id: str,
    rate: Decimal,
    basis: CostBasis,
    currency: str,
    unit: str,
    effective_from: date,
    effective_to: date | None,
    source: str,
) -> str:
    """Return the content identity of one priced interval.

    ``version`` is intentionally excluded: a version is an append-only
    allocation made by persistence, while the identity names the priced
    content itself.
    """

    if not isinstance(basis, CostBasis):
        raise ResourceRateFactError("INVALID_RATE_BASIS")
    payload = json.dumps(
        {
            "resource_id": _text(resource_id, "INVALID_RATE_RESOURCE_ID"),
            "rate": _decimal_token(rate),
            "basis": basis.value,
            "currency": _text(currency, "INVALID_RATE_CURRENCY"),
            "unit": _text(unit, "INVALID_RATE_UNIT"),
            "effective_from": _effective_date(
                effective_from, "INVALID_RATE_EFFECTIVE_FROM"
            ).isoformat(),
            "effective_to": (
                None
                if effective_to is None
                else _effective_date(effective_to, "INVALID_RATE_EFFECTIVE_TO").isoformat()
            ),
            "source": _text(source, "INVALID_RATE_SOURCE"),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ResourceRateFact:
    """One immutable effective-dated price interval for a resource."""

    resource_id: str
    rate: Decimal
    basis: CostBasis
    currency: str
    unit: str
    effective_from: date
    effective_to: date | None
    source: str
    identity: str

    def __post_init__(self) -> None:
        if not isinstance(self.resource_id, str) or not self.resource_id.strip():
            raise ResourceRateFactError("INVALID_RATE_RESOURCE_ID")
        if (
            not isinstance(self.rate, Decimal)
            or not self.rate.is_finite()
            or self.rate < 0
        ):
            raise ResourceRateFactError("INVALID_RATE_VALUE")
        if not isinstance(self.basis, CostBasis):
            raise ResourceRateFactError("INVALID_RATE_BASIS")
        if not isinstance(self.currency, str) or not self.currency.strip():
            raise ResourceRateFactError("INVALID_RATE_CURRENCY")
        if not isinstance(self.unit, str) or not self.unit.strip():
            raise ResourceRateFactError("INVALID_RATE_UNIT")
        if not isinstance(self.effective_from, date) or isinstance(
            self.effective_from, datetime
        ):
            raise ResourceRateFactError("INVALID_RATE_EFFECTIVE_FROM")
        if self.effective_to is not None:
            if not isinstance(self.effective_to, date) or isinstance(
                self.effective_to, datetime
            ):
                raise ResourceRateFactError("INVALID_RATE_EFFECTIVE_TO")
            if self.effective_to < self.effective_from:
                raise ResourceRateFactError("INVALID_RATE_INTERVAL")
        if not isinstance(self.source, str) or not self.source.strip():
            raise ResourceRateFactError("INVALID_RATE_SOURCE")
        expected = compute_rate_identity(
            resource_id=self.resource_id,
            rate=self.rate,
            basis=self.basis,
            currency=self.currency,
            unit=self.unit,
            effective_from=self.effective_from,
            effective_to=self.effective_to,
            source=self.source,
        )
        if self.identity != expected:
            raise ResourceRateFactError("RATE_IDENTITY_MISMATCH")

    @classmethod
    def create(
        cls,
        *,
        resource_id: str,
        rate: Decimal,
        basis: CostBasis,
        currency: str,
        unit: str,
        effective_from: date,
        effective_to: date | None,
        source: str,
    ) -> "ResourceRateFact":
        identity = compute_rate_identity(
            resource_id=resource_id,
            rate=rate,
            basis=basis,
            currency=currency,
            unit=unit,
            effective_from=effective_from,
            effective_to=effective_to,
            source=source,
        )
        return cls(
            resource_id=resource_id,
            rate=rate,
            basis=basis,
            currency=currency,
            unit=unit,
            effective_from=effective_from,
            effective_to=effective_to,
            source=source,
            identity=identity,
        )

    def is_effective_on(self, value: date) -> bool:
        if not isinstance(value, date) or isinstance(value, datetime):
            raise ResourceRateFactError("INVALID_RATE_EFFECTIVE_DATE")
        return value >= self.effective_from and (
            self.effective_to is None or value <= self.effective_to
        )

    def to_resource_rate(self, *, version: int = 1) -> ResourceRate:
        return ResourceRate(
            rate=self.rate,
            basis=self.basis,
            currency=self.currency,
            effective_from=self.effective_from,
            effective_to=self.effective_to,
            version=version,
        )


@dataclass(frozen=True)
class ResourceRateProfile:
    """Validated, non-overlapping effective-dated price intervals."""

    resource_id: str
    facts: tuple[ResourceRateFact, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.resource_id, str) or not self.resource_id.strip():
            raise ResourceRateFactError("INVALID_RATE_RESOURCE_ID")
        if not isinstance(self.facts, tuple):
            raise ResourceRateFactError("INVALID_RATE_FACTS")
        ordered = tuple(sorted(self.facts, key=lambda item: item.effective_from))
        for fact in ordered:
            if not isinstance(fact, ResourceRateFact):
                raise ResourceRateFactError("INVALID_RATE_FACT")
            if fact.resource_id != self.resource_id:
                raise ResourceRateFactError("RATE_RESOURCE_MISMATCH")
        previous: ResourceRateFact | None = None
        for fact in ordered:
            if previous is not None:
                if previous.effective_to is None:
                    raise ResourceRateFactError("RATE_INTERVALS_OVERLAP")
                if fact.effective_from <= previous.effective_to:
                    raise ResourceRateFactError("RATE_INTERVALS_OVERLAP")
            previous = fact
        object.__setattr__(self, "facts", ordered)

    def fact_on(self, value: date) -> ResourceRateFact:
        if not isinstance(value, date) or isinstance(value, datetime):
            raise ResourceRateFactError("INVALID_RATE_EFFECTIVE_DATE")
        matches = tuple(fact for fact in self.facts if fact.is_effective_on(value))
        if not matches:
            raise ResourceRateFactError("RATE_NOT_EFFECTIVE")
        if len(matches) > 1:
            raise ResourceRateFactError("RATE_INTERVALS_OVERLAP")
        return matches[0]


__all__ = [
    "ResourceRateFact",
    "ResourceRateFactError",
    "ResourceRateProfile",
    "compute_rate_identity",
]
