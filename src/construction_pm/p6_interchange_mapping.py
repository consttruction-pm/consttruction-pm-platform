from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from .backend_p0.models import BackendScope
from .p6_mapping_registry import P6MappingFormat, P6MappingStatus, PersistedP6Mapping


class P6InterchangeCompatibilityError(ValueError):
    """Raised when an interchange row cannot be represented losslessly."""


class P6InterchangeDirection(str, Enum):
    IMPORT = "IMPORT"
    EXPORT = "EXPORT"


@dataclass(frozen=True)
class P6InterchangeRow:
    scope: BackendScope
    format: P6MappingFormat
    values: Mapping[str, Any]
    extensions: Mapping[str, Any] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self.scope.validate()
        if not isinstance(self.values, Mapping):
            raise TypeError("values must be a mapping")
        if self.extensions is None:
            object.__setattr__(self, "extensions", {})


@dataclass(frozen=True)
class P6InterchangeResult:
    values: dict[str, Any]
    extensions: dict[str, Any]
    warnings: tuple[str, ...] = ()


class P6InterchangeMapper:
    """Provider-neutral row mapper driven only by persisted P6 mappings."""

    def __init__(self, mappings: Sequence[PersistedP6Mapping]) -> None:
        if not mappings:
            raise ValueError("at least one mapping is required")
        first_scope = mappings[0].scope
        self._scope = first_scope
        self._mappings = tuple(sorted(mappings, key=lambda item: item.definition.mapping_id))
        seen_sources: set[tuple[P6MappingFormat, str]] = set()
        seen_canonical: set[tuple[P6MappingFormat, str]] = set()
        for item in self._mappings:
            if item.scope != first_scope:
                raise P6InterchangeCompatibilityError("MAPPING_SCOPE_MISMATCH")
            definition = item.definition
            source_key = (definition.format, definition.source_field)
            canonical_key = (definition.format, definition.canonical_field)
            if source_key in seen_sources:
                raise P6InterchangeCompatibilityError(
                    f"AMBIGUOUS_SOURCE_FIELD:{definition.format.value}:{definition.source_field}"
                )
            if canonical_key in seen_canonical:
                raise P6InterchangeCompatibilityError(
                    f"AMBIGUOUS_CANONICAL_FIELD:{definition.format.value}:{definition.canonical_field}"
                )
            seen_sources.add(source_key)
            seen_canonical.add(canonical_key)

    def import_row(self, row: P6InterchangeRow) -> P6InterchangeResult:
        self._validate_scope(row.scope)
        self._validate_format(row.format)
        canonical: dict[str, Any] = {}
        extensions = dict(row.extensions)
        warnings: list[str] = []
        mapped_sources: set[str] = set()

        for item in self._mappings:
            definition = item.definition
            if definition.format is not row.format:
                continue
            source = definition.source_field
            if source not in row.values:
                continue
            mapped_sources.add(source)
            value = row.values[source]
            if definition.status is P6MappingStatus.SUPPORTED:
                canonical[definition.canonical_field] = value
            elif definition.status is P6MappingStatus.UNSUPPORTED_PRESERVE:
                extensions[self._extension_key(definition.source_field)] = value
                warnings.append(f"PRESERVED_UNSUPPORTED_FIELD:{source}")
            else:
                raise P6InterchangeCompatibilityError(
                    f"UNSUPPORTED_FIELD_REJECTED:{source}"
                )

        for source, value in row.values.items():
            if source not in mapped_sources:
                extensions[self._extension_key(source)] = value
                warnings.append(f"PRESERVED_UNKNOWN_FIELD:{source}")

        return P6InterchangeResult(canonical, extensions, tuple(sorted(set(warnings))))

    def export_row(
        self,
        row: P6InterchangeRow,
    ) -> P6InterchangeResult:
        self._validate_scope(row.scope)
        self._validate_format(row.format)
        source_values: dict[str, Any] = {}
        extensions = dict(row.extensions)
        warnings: list[str] = []
        mapped_canonical: set[str] = set()

        for item in self._mappings:
            definition = item.definition
            if definition.format is not row.format:
                continue
            canonical = definition.canonical_field
            if canonical not in row.values:
                continue
            mapped_canonical.add(canonical)
            value = row.values[canonical]
            if definition.status is P6MappingStatus.SUPPORTED:
                source_values[definition.source_field] = value
            elif definition.status is P6MappingStatus.UNSUPPORTED_PRESERVE:
                extensions[self._extension_key(definition.source_field)] = value
                warnings.append(f"PRESERVED_UNSUPPORTED_FIELD:{canonical}")
            else:
                raise P6InterchangeCompatibilityError(
                    f"UNSUPPORTED_FIELD_REJECTED:{canonical}"
                )

        for canonical, value in row.values.items():
            if canonical not in mapped_canonical:
                extensions[self._extension_key(f"canonical:{canonical}")] = value
                warnings.append(f"PRESERVED_UNKNOWN_CANONICAL_FIELD:{canonical}")

        return P6InterchangeResult(source_values, extensions, tuple(sorted(set(warnings))))

    def _validate_scope(self, scope: BackendScope) -> None:
        if scope != self._scope:
            raise P6InterchangeCompatibilityError("ROW_SCOPE_MISMATCH")

    def _validate_format(self, format: P6MappingFormat) -> None:
        if not isinstance(format, P6MappingFormat):
            raise TypeError("format must be P6MappingFormat")

    def _extension_key(self, field: str) -> str:
        return f"p6.interchange.{self._scope.tenant_id}.{self._scope.project_id}.{field}"


__all__ = [
    "P6InterchangeCompatibilityError",
    "P6InterchangeDirection",
    "P6InterchangeMapper",
    "P6InterchangeResult",
    "P6InterchangeRow",
]
