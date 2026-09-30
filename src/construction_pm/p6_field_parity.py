from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class FieldMetadataMismatch:
    key: tuple[str, str]
    attribute: str
    registry_value: object
    inventory_value: object


@dataclass(frozen=True)
class FieldParityComparison:
    exact_matches: tuple[tuple[str, str], ...]
    registry_only: tuple[tuple[str, str], ...]
    inventory_only: tuple[tuple[str, str], ...]
    metadata_mismatches: tuple[FieldMetadataMismatch, ...]

    @property
    def exact_match_count(self) -> int:
        return len(self.exact_matches)

    @property
    def registry_only_count(self) -> int:
        return len(self.registry_only)

    @property
    def inventory_only_count(self) -> int:
        return len(self.inventory_only)

    @property
    def is_metadata_consistent(self) -> bool:
        return not self.metadata_mismatches


def _field_key(field: Mapping[str, object]) -> tuple[str, str]:
    subject_area = field.get("subject_area")
    p6_field = field.get("p6_field")
    if not isinstance(subject_area, str) or not subject_area:
        raise ValueError("field subject_area must be a non-empty string")
    if not isinstance(p6_field, str) or not p6_field:
        raise ValueError("field p6_field must be a non-empty string")
    return subject_area, p6_field


def _index_fields(
    fields: Sequence[Mapping[str, object]],
) -> dict[tuple[str, str], Mapping[str, object]]:
    indexed: dict[tuple[str, str], Mapping[str, object]] = {}
    for field in fields:
        key = _field_key(field)
        if key in indexed:
            raise ValueError(f"duplicate field identity: {key[0]}::{key[1]}")
        indexed[key] = field
    return indexed


def compare_field_registry_to_inventory(
    registry_fields: Sequence[Mapping[str, object]],
    inventory_fields: Sequence[Mapping[str, object]],
) -> FieldParityComparison:
    """Compare P6 registry identities and populated metadata against a source inventory.

    Matching is intentionally based only on the explicit subject-area + P6 field
    identity. A name similarity or alias is never treated as an exact match.

    Inventory values of None are treated as not-yet-certified evidence and are
    therefore not compared. Once authoritative evidence populates a property,
    any registry mismatch becomes visible to this gate.
    """

    registry = _index_fields(registry_fields)
    inventory = _index_fields(inventory_fields)

    shared = sorted(registry.keys() & inventory.keys())
    registry_only = tuple(sorted(registry.keys() - inventory.keys()))
    inventory_only = tuple(sorted(inventory.keys() - registry.keys()))

    mismatches: list[FieldMetadataMismatch] = []
    comparable_attributes = ("data_type", "writable", "computed", "unit")

    for key in shared:
        registry_field = registry[key]
        inventory_field = inventory[key]
        for attribute in comparable_attributes:
            inventory_value = inventory_field.get(attribute)
            if inventory_value is None:
                continue
            registry_value = registry_field.get(attribute)
            if registry_value != inventory_value:
                mismatches.append(
                    FieldMetadataMismatch(
                        key=key,
                        attribute=attribute,
                        registry_value=registry_value,
                        inventory_value=inventory_value,
                    )
                )

    return FieldParityComparison(
        exact_matches=tuple(shared),
        registry_only=registry_only,
        inventory_only=inventory_only,
        metadata_mismatches=tuple(mismatches),
    )
