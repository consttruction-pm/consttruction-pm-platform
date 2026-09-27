from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Mapping


class P6RegistryStatus(str, Enum):
    SEEDED_CORE_CATALOG = "seeded_core_catalog"
    COMPLETE_CATALOG = "complete_catalog"
    CERTIFIED = "certified"


class P6FieldDisposition(str, Enum):
    SEEDED_NOT_CERTIFIED = "seeded_not_certified"
    IMPLEMENTED = "implemented"
    EQUIVALENT_SUPERSET = "equivalent_superset"
    OUTSIDE_SCOPE = "outside_scope"
    PENDING = "pending"


class P6RegistryCertificationError(ValueError):
    """Raised when a P6 registry is not eligible for certification."""


@dataclass(frozen=True)
class P6RegistryCompleteness:
    expected_field_count: int | None
    field_count: int
    dispositioned_field_count: int
    approved_field_count: int
    status: P6RegistryStatus

    @property
    def coverage_percent(self) -> float | None:
        if self.expected_field_count is None:
            return None
        if self.expected_field_count < 0:
            raise ValueError("expected_field_count must be non-negative")
        return round(
            (self.field_count / self.expected_field_count) * 100,
            2,
        ) if self.expected_field_count else 100.0

    @property
    def certification_ready(self) -> bool:
        return (
            self.status is P6RegistryStatus.CERTIFIED
            and self.expected_field_count is not None
            and self.field_count == self.expected_field_count
            and self.dispositioned_field_count == self.field_count
            and self.approved_field_count == self.field_count
        )


def summarize_completeness(
    *,
    status: P6RegistryStatus | str,
    expected_field_count: int | None,
    fields: Iterable[Mapping[str, object]],
) -> P6RegistryCompleteness:
    resolved_status = P6RegistryStatus(status)
    items = list(fields)
    seen: set[str] = set()
    for item in items:
        field_id = item.get("field_id")
        if not isinstance(field_id, str) or not field_id.strip():
            raise P6RegistryCertificationError("field_id is required")
        if field_id in seen:
            raise P6RegistryCertificationError(f"duplicate field_id: {field_id}")
        seen.add(field_id)

    dispositioned = 0
    approved = 0
    for item in items:
        raw = item.get("disposition")
        try:
            disposition = P6FieldDisposition(raw)
        except (TypeError, ValueError) as exc:
            raise P6RegistryCertificationError(
                f"invalid disposition for {item['field_id']}: {raw!r}"
            ) from exc

        if disposition in {
            P6FieldDisposition.IMPLEMENTED,
            P6FieldDisposition.EQUIVALENT_SUPERSET,
            P6FieldDisposition.OUTSIDE_SCOPE,
        }:
            approved += 1
            dispositioned += 1

    if expected_field_count is not None and expected_field_count < len(items):
        raise P6RegistryCertificationError(
            "expected_field_count cannot be lower than current field_count"
        )

    result = P6RegistryCompleteness(
        expected_field_count=expected_field_count,
        field_count=len(items),
        dispositioned_field_count=dispositioned,
        approved_field_count=approved,
        status=resolved_status,
    )
    return result


def require_certifiable(
    *,
    status: P6RegistryStatus | str,
    expected_field_count: int | None,
    fields: Iterable[Mapping[str, object]],
) -> P6RegistryCompleteness:
    result = summarize_completeness(
        status=status,
        expected_field_count=expected_field_count,
        fields=fields,
    )
    if not result.certification_ready:
        raise P6RegistryCertificationError(
            "P6 registry is not certification-ready"
        )
    return result
