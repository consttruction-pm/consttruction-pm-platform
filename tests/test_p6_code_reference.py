"""Self-checks for the traceable CUBI P6 requirement registry.

These tests validate registry integrity only; they do not prove the scheduler
implements the behavior described by a requirement.
"""

from construction_pm.p6_code_reference import (
    INVENTORY_REQUIRED,
    KNOWN_GAP,
    MAPPED_NOT_PROVEN,
    FORMULA_REFERENCE,
    P6_CODE_REFERENCE,
    coverage_summary,
    get_formula_reference,
    get_reference,
    validate_formula_registry,
    validate_registry,
)


def test_p6_code_reference_registry_has_no_internal_integrity_errors():
    assert validate_registry() == ()


def test_p6_code_reference_ids_are_unique_and_stable_strings():
    ids = [item.id for item in P6_CODE_REFERENCE]
    assert ids
    assert len(ids) == len(set(ids))
    assert all(isinstance(value, str) and value.strip() for value in ids)


def test_every_entry_has_source_and_code_mapping_and_explicit_evidence_label():
    allowed = {MAPPED_NOT_PROVEN, KNOWN_GAP, INVENTORY_REQUIRED}
    for item in P6_CODE_REFERENCE:
        assert item.official_sources
        assert item.cubi_code_paths
        assert item.coverage in allowed
        if item.coverage == KNOWN_GAP:
            assert item.known_gap.strip()


def test_resource_dependent_driving_gap_is_explicit_not_marked_complete():
    item = get_reference("RES-001")
    assert item.coverage == KNOWN_GAP
    assert "RESOURCE_DEPENDENT_DRIVING_ASSIGNMENT_UNSUPPORTED" in item.known_gap
    assert "nondriving placement" in item.known_gap


def test_key_schedule_options_have_separate_reference_ids():
    ids = {item.id for item in P6_CODE_REFERENCE}
    assert {
        "SCH-003",   # total-float formula selection
        "SCH-004",   # critical activity rule
        "SCH-007",   # out-of-sequence behavior
        "SCH-008",   # relationship/lag calendar
        "SCH-012",   # SS lag expiry basis
        "SCH-013",   # schedule dialog and multi-project Data Date
        "RES-002",   # resource leveling
        "RES-005",   # cross-project leveling controls
    }.issubset(ids)


def test_coverage_summary_is_a_registry_count_not_a_completion_percent():
    summary = coverage_summary()
    assert summary["TOTAL_REGISTERED"] == len(P6_CODE_REFERENCE)
    assert sum(
        summary[key]
        for key in (MAPPED_NOT_PROVEN, KNOWN_GAP, INVENTORY_REQUIRED)
    ) == len(P6_CODE_REFERENCE)
    assert summary[KNOWN_GAP] >= 1
    assert summary[INVENTORY_REQUIRED] >= 1



def test_p6_formula_registry_has_no_internal_integrity_errors():
    assert validate_formula_registry() == ()


def test_formula_ids_are_unique_and_have_sources_and_code_targets():
    formula_ids = [item.id for item in FORMULA_REFERENCE]
    assert formula_ids
    assert len(formula_ids) == len(set(formula_ids))
    for item in FORMULA_REFERENCE:
        assert item.official_sources
        assert item.cubi_code_paths
        assert item.formula_or_algorithm.strip()


def test_float_formula_reference_lists_all_three_selected_modes():
    item = get_formula_reference("FRM-TF-001")
    assert "Start Float = Late Start - Early Start" in item.formula_or_algorithm
    assert "Finish Float = Late Finish - Early Finish" in item.formula_or_algorithm
    assert "Smallest Float" in item.formula_or_algorithm


def test_resource_dependent_formula_remains_marked_as_a_known_gap():
    item = get_formula_reference("FRM-RESOURCE-DUR-001")
    assert item.status == "KNOWN_GAP"
    assert "RESOURCE_DEPENDENT_DRIVING_ASSIGNMENT_UNSUPPORTED" in item.known_gap
