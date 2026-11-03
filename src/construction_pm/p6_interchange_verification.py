from __future__ import annotations

"""Explicit round-trip verification for interchange documents (INT-01).

The verifier distinguishes the two outcomes that must never be conflated:

* implementation loss — a mapped canonical value did not come back equal;
* intentionally nonportable information — an unmapped/unsupported field was
  preserved in extensions and reported as a warning, not silently dropped.

A format is only "lossless" for the supplied canonical fields when every
mapped value matches. Preserved extensions are reported separately and never
count as canonical loss.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping, Sequence

from .backend_p0.models import BackendScope
from .p6_interchange_adapter import P6InterchangeAdapter
from .p6_mapping_registry import P6MappingFormat

P6_INTERCHANGE_VERIFICATION_VERSION = "p6-interchange-round-trip.v1"


class P6InterchangeVerificationError(ValueError):
    """Raised when a round-trip cannot produce one comparable row."""


def _normalized(value: Any) -> Any:
    """Compare timestamps/dates and decimals by value, not representation."""
    if isinstance(value, Decimal):
        return value.normalize()
    return value


@dataclass(frozen=True)
class P6InterchangeRoundTripReport:
    format: P6MappingFormat
    fields: tuple[str, ...]
    mismatched_fields: tuple[str, ...]
    input_values: Mapping[str, Any]
    output_values: Mapping[str, Any]
    preserved_fields: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def canonical_lossless(self) -> bool:
        return not self.mismatched_fields

    def to_payload(self) -> dict[str, Any]:
        return {
            "contract_version": P6_INTERCHANGE_VERIFICATION_VERSION,
            "kind": "p6_interchange_round_trip",
            "format": self.format.value,
            "canonical_lossless": self.canonical_lossless,
            "fields": list(self.fields),
            "mismatched_fields": list(self.mismatched_fields),
            "preserved_fields": list(self.preserved_fields),
            "warnings": list(self.warnings),
            "input_values": {
                field: _jsonable(self.input_values.get(field))
                for field in self.fields
            },
            "output_values": {
                field: _jsonable(self.output_values.get(field))
                for field in self.fields
            },
        }


def _jsonable(value: Any) -> Any:
    from datetime import date, datetime

    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if hasattr(value, "value") and hasattr(value, "unit"):
        return {"value": str(value.value), "unit": value.unit}
    return value


def verify_round_trip(
    adapter: P6InterchangeAdapter,
    *,
    scope: BackendScope,
    values: Mapping[str, Any],
    extensions: Mapping[str, Any] | None = None,
) -> P6InterchangeRoundTripReport:
    """Export one row and re-import it through the same format adapter."""
    if not isinstance(values, Mapping) or not values:
        raise P6InterchangeVerificationError("ROUND_TRIP_VALUES_REQUIRED")
    exported = adapter.export_document(
        (dict(values),),
        scope=scope,
        extensions=None if extensions is None else (dict(extensions),),
    )
    imported = adapter.import_document(exported, scope=scope)
    if len(imported) != 1:
        raise P6InterchangeVerificationError(
            f"ROUND_TRIP_ROW_COUNT_MISMATCH:{len(imported)}"
        )
    result = imported[0]
    output = result.values
    fields = tuple(sorted(values))
    mismatched = tuple(
        field
        for field in fields
        if _normalized(output.get(field)) != _normalized(values.get(field))
    )
    preserved = tuple(
        sorted(
            key
            for key in result.extensions
            if key not in (extensions or {})
        )
    )
    return P6InterchangeRoundTripReport(
        format=adapter.codec.format,
        fields=fields,
        mismatched_fields=mismatched,
        input_values=dict(values),
        output_values=dict(output),
        preserved_fields=preserved,
        warnings=result.warnings,
    )


def verify_round_trips(
    adapter: P6InterchangeAdapter,
    *,
    scope: BackendScope,
    rows: Sequence[tuple[Mapping[str, Any], Mapping[str, Any] | None]],
) -> tuple[P6InterchangeRoundTripReport, ...]:
    """Verify several independent rows and preserve their order."""
    return tuple(
        verify_round_trip(
            adapter,
            scope=scope,
            values=values,
            extensions=extensions,
        )
        for values, extensions in rows
    )


__all__ = [
    "P6_INTERCHANGE_VERIFICATION_VERSION",
    "P6InterchangeRoundTripReport",
    "P6InterchangeVerificationError",
    "verify_round_trip",
    "verify_round_trips",
]
