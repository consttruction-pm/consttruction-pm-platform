from construction_pm.p6_formula_compatibility import (
    CompatibilityStatus,
    FormulaDialect,
    formula_compatibility_registry,
    lookup_formula_compatibility,
)


def test_registry_is_deterministic_and_unique() -> None:
    entries_a = formula_compatibility_registry()
    entries_b = formula_compatibility_registry()
    keys = [(e.dialect.value, e.version, e.canonical_id) for e in entries_a]
    assert entries_a == entries_b
    assert len(keys) == len(set(keys))


def test_excel_common_functions_resolve() -> None:
    for name in ("IF", "SUM", "MIN", "MAX", "ABS", "ROUND", "AND", "OR", "NOT"):
        entry = lookup_formula_compatibility(FormulaDialect.EXCEL, name, "365")
        assert entry.status is CompatibilityStatus.SUPPORTED
        assert entry.canonical_id == name


def test_project_iif_is_translation_required() -> None:
    entry = lookup_formula_compatibility(FormulaDialect.MICROSOFT_PROJECT, "IIf")
    assert entry.canonical_id == "IIF"
    assert entry.status is CompatibilityStatus.TRANSLATION_REQUIRED


def test_p6_if_statement_is_translation_required() -> None:
    entry = lookup_formula_compatibility(
        FormulaDialect.P6_EPPM,
        "IF/ELSE statement",
        "26",
    )
    assert entry.canonical_id == "IF"
    assert entry.status is CompatibilityStatus.TRANSLATION_REQUIRED


def test_unknown_function_is_explicitly_unsupported() -> None:
    entry = lookup_formula_compatibility(FormulaDialect.EXCEL, "XLOOKUP", "365")
    assert entry.status is CompatibilityStatus.UNSUPPORTED


def test_canonical_surface_matches_current_engine() -> None:
    canonical = {
        entry.canonical_id
        for entry in formula_compatibility_registry()
        if entry.dialect is FormulaDialect.CANONICAL
    }
    assert canonical == {
        "IF", "SUM", "MIN", "MAX", "ABS", "ROUND",
        "COALESCE", "NOT", "AND", "OR",
    }
