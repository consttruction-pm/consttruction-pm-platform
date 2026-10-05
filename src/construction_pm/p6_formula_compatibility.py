from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FormulaDialect(str, Enum):
    CANONICAL = "canonical"
    P6_EPPM = "p6_eppm"
    EXCEL = "excel"
    MICROSOFT_PROJECT = "microsoft_project"


class CompatibilityStatus(str, Enum):
    SUPPORTED = "supported"
    TRANSLATION_REQUIRED = "translation_required"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class FormulaCompatibility:
    canonical_id: str
    dialect: FormulaDialect
    source_names: tuple[str, ...]
    version: str
    status: CompatibilityStatus
    argument_signature: str
    result_type: str
    notes: str = ""


_REGISTRY: tuple[FormulaCompatibility, ...] = (
    FormulaCompatibility("IF", FormulaDialect.CANONICAL, ("IF",), "1", CompatibilityStatus.SUPPORTED, "(boolean, any, any) -> any", "polymorphic"),
    FormulaCompatibility("SUM", FormulaDialect.CANONICAL, ("SUM",), "1", CompatibilityStatus.SUPPORTED, "(number, ...number) -> number", "number"),
    FormulaCompatibility("MIN", FormulaDialect.CANONICAL, ("MIN",), "1", CompatibilityStatus.SUPPORTED, "(number, ...number) -> number", "number"),
    FormulaCompatibility("MAX", FormulaDialect.CANONICAL, ("MAX",), "1", CompatibilityStatus.SUPPORTED, "(number, ...number) -> number", "number"),
    FormulaCompatibility("ABS", FormulaDialect.CANONICAL, ("ABS",), "1", CompatibilityStatus.SUPPORTED, "(number) -> number", "number"),
    FormulaCompatibility("ROUND", FormulaDialect.CANONICAL, ("ROUND",), "1", CompatibilityStatus.SUPPORTED, "(number[, integer]) -> number", "number"),
    FormulaCompatibility("COALESCE", FormulaDialect.CANONICAL, ("COALESCE",), "1", CompatibilityStatus.SUPPORTED, "(any, ...any) -> any", "polymorphic"),
    FormulaCompatibility("NOT", FormulaDialect.CANONICAL, ("NOT",), "1", CompatibilityStatus.SUPPORTED, "(boolean) -> boolean", "boolean"),
    FormulaCompatibility("AND", FormulaDialect.CANONICAL, ("AND",), "1", CompatibilityStatus.SUPPORTED, "(boolean, ...boolean) -> boolean", "boolean"),
    FormulaCompatibility("OR", FormulaDialect.CANONICAL, ("OR",), "1", CompatibilityStatus.SUPPORTED, "(boolean, ...boolean) -> boolean", "boolean"),
    FormulaCompatibility("IF", FormulaDialect.EXCEL, ("IF",), "365", CompatibilityStatus.SUPPORTED, "(boolean, any, any) -> any", "polymorphic"),
    FormulaCompatibility("SUM", FormulaDialect.EXCEL, ("SUM",), "365", CompatibilityStatus.SUPPORTED, "(number, ...number) -> number", "number"),
    FormulaCompatibility("MIN", FormulaDialect.EXCEL, ("MIN",), "365", CompatibilityStatus.SUPPORTED, "(number, ...number) -> number", "number"),
    FormulaCompatibility("MAX", FormulaDialect.EXCEL, ("MAX",), "365", CompatibilityStatus.SUPPORTED, "(number, ...number) -> number", "number"),
    FormulaCompatibility("ABS", FormulaDialect.EXCEL, ("ABS",), "365", CompatibilityStatus.SUPPORTED, "(number) -> number", "number"),
    FormulaCompatibility("ROUND", FormulaDialect.EXCEL, ("ROUND",), "365", CompatibilityStatus.SUPPORTED, "(number, integer) -> number", "number"),
    FormulaCompatibility("NOT", FormulaDialect.EXCEL, ("NOT",), "365", CompatibilityStatus.SUPPORTED, "(boolean) -> boolean", "boolean"),
    FormulaCompatibility("AND", FormulaDialect.EXCEL, ("AND",), "365", CompatibilityStatus.SUPPORTED, "(boolean, ...boolean) -> boolean", "boolean"),
    FormulaCompatibility("OR", FormulaDialect.EXCEL, ("OR",), "365", CompatibilityStatus.SUPPORTED, "(boolean, ...boolean) -> boolean", "boolean"),
    FormulaCompatibility("IIF", FormulaDialect.MICROSOFT_PROJECT, ("IIf",), "desktop", CompatibilityStatus.TRANSLATION_REQUIRED, "(expression, truepart, falsepart) -> any", "polymorphic"),
    FormulaCompatibility("SUM", FormulaDialect.MICROSOFT_PROJECT, ("Sum",), "desktop", CompatibilityStatus.SUPPORTED, "(number, ...number) -> number", "number"),
    FormulaCompatibility("MIN", FormulaDialect.MICROSOFT_PROJECT, ("Min",), "desktop", CompatibilityStatus.SUPPORTED, "(number, ...number) -> number", "number"),
    FormulaCompatibility("MAX", FormulaDialect.MICROSOFT_PROJECT, ("Max",), "desktop", CompatibilityStatus.SUPPORTED, "(number, ...number) -> number", "number"),
    FormulaCompatibility("ABS", FormulaDialect.MICROSOFT_PROJECT, ("Abs",), "desktop", CompatibilityStatus.SUPPORTED, "(number) -> number", "number"),
    FormulaCompatibility("ROUND", FormulaDialect.MICROSOFT_PROJECT, ("Round",), "desktop", CompatibilityStatus.SUPPORTED, "(number, integer) -> number", "number"),
    FormulaCompatibility("IF", FormulaDialect.P6_EPPM, ("IF/ELSE statement",), "26", CompatibilityStatus.TRANSLATION_REQUIRED, "(condition, then, else) -> any", "polymorphic"),
)


def formula_compatibility_registry() -> tuple[FormulaCompatibility, ...]:
    return _REGISTRY


def lookup_formula_compatibility(
    dialect: FormulaDialect,
    source_name: str,
    version: str | None = None,
) -> FormulaCompatibility:
    normalized = source_name.strip().upper()
    matches = [
        entry for entry in _REGISTRY
        if entry.dialect is dialect
        and normalized in {name.upper() for name in entry.source_names}
        and (version is None or entry.version == version)
    ]
    if matches:
        return sorted(matches, key=lambda entry: (entry.version, entry.canonical_id))[0]
    return FormulaCompatibility(
        canonical_id=normalized,
        dialect=dialect,
        source_names=(source_name,),
        version=version or "unknown",
        status=CompatibilityStatus.UNSUPPORTED,
        argument_signature="unknown",
        result_type="unknown",
        notes="No compatibility mapping is registered for this source function.",
    )


def validate_formula_compatibility_registry() -> None:
    keys: set[tuple[FormulaDialect, str, str]] = set()
    aliases: set[tuple[FormulaDialect, str, str, str]] = set()
    for entry in _REGISTRY:
        key = (entry.dialect, entry.version, entry.canonical_id)
        if key in keys:
            raise ValueError(f"DUPLICATE_COMPATIBILITY_ENTRY:{key}")
        keys.add(key)
        for source_name in entry.source_names:
            alias = (entry.dialect, entry.version, entry.canonical_id, source_name.upper())
            if alias in aliases:
                raise ValueError(f"DUPLICATE_SOURCE_ALIAS:{entry.dialect.value}:{entry.version}:{source_name}")
            aliases.add(alias)


validate_formula_compatibility_registry()


__all__ = [
    "CompatibilityStatus",
    "FormulaCompatibility",
    "FormulaDialect",
    "formula_compatibility_registry",
    "lookup_formula_compatibility",
    "validate_formula_compatibility_registry",
]
