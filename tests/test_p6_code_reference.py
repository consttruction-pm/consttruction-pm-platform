"""Self-checks for the traceable CUBI P6 requirement registry.

These tests validate registry integrity only; they do not prove the scheduler
implements the behavior described by a requirement.
"""

from pathlib import Path

from construction_pm.p6_code_reference import (
    INVENTORY_REQUIRED,
    KNOWN_GAP,
    MAPPED_NOT_PROVEN,
    DOC_CORE_RULES_EXTRACTED,
    DOC_INDEXED_NOT_LINE_REVIEWED,
    DOC_PRODUCT_SCOPE_PENDING,
    DOC_TOPIC_MAP_PARTIAL,
    FORMULA_REFERENCE,
    ORACLE_SOURCES,
    P6_CODE_REFERENCE,
    REFERENCE_VERSION,
    P6_DOCUMENTATION_AUDIT,
    coverage_summary,
    documentation_audit_summary,
    get_formula_reference,
    get_reference,
    validate_all_reference_data,
    validate_documentation_audit,
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



def test_data_date_boundary_has_its_own_versioned_formula_reference():
    item = get_formula_reference("FRM-DATA-DATE-001")
    assert "start of the current scheduling workperiod" in item.formula_or_algorithm
    assert "src/construction_pm/scheduling/progress_state.py" in item.cubi_code_paths



def test_check_schedule_and_admin_category_inventory_remain_explicit_gaps():
    assert get_reference("SCH-014").coverage == INVENTORY_REQUIRED
    assert get_reference("ADMIN-003").coverage == INVENTORY_REQUIRED


def test_curve_earned_value_formula_is_separately_tracked():
    item = get_formula_reference("FRM-EVM-003")
    assert "Units Percent Complete" in item.formula_or_algorithm
    assert "BAC" in item.formula_or_algorithm
    assert item.status == "FORMULA_DOCUMENTED_EDGE_RULE_REQUIRED"



def test_every_referenced_cubi_repository_path_exists():
    repo_root = Path(__file__).resolve().parents[1]
    paths = {
        path
        for item in (*P6_CODE_REFERENCE, *FORMULA_REFERENCE)
        for path in item.cubi_code_paths
        if path.startswith(("src/", "apps/", "shared/", "docs/", "tests/"))
    }
    missing = sorted(path for path in paths if not (repo_root / path).exists())
    assert not missing, "Reference paths do not exist in this checkout: " + ", ".join(missing)



def test_documentation_audit_manifest_has_no_internal_integrity_errors():
    assert validate_documentation_audit() == ()
    assert validate_all_reference_data() == ()


def test_documentation_audit_ids_sources_and_open_review_boundaries_are_explicit():
    ids = [item.id for item in P6_DOCUMENTATION_AUDIT]
    assert ids
    assert len(ids) == len(set(ids))
    requirement_ids = {item.id for item in P6_CODE_REFERENCE}
    for item in P6_DOCUMENTATION_AUDIT:
        assert item.title.strip()
        assert item.official_url.startswith("https://docs.oracle.com/")
        assert item.reviewed_scope.strip()
        assert item.remaining_work.strip()
        assert set(item.linked_requirement_ids).issubset(requirement_ids)
    assert any(item.review_status == DOC_CORE_RULES_EXTRACTED for item in P6_DOCUMENTATION_AUDIT)
    assert any(item.review_status == DOC_INDEXED_NOT_LINE_REVIEWED for item in P6_DOCUMENTATION_AUDIT)
    assert any(item.review_status == DOC_TOPIC_MAP_PARTIAL for item in P6_DOCUMENTATION_AUDIT)
    assert any(item.review_status == DOC_PRODUCT_SCOPE_PENDING for item in P6_DOCUMENTATION_AUDIT)


def test_documentation_summary_is_not_reported_as_completion_percentage():
    summary = documentation_audit_summary()
    assert summary["TOTAL_DOCUMENT_FAMILIES"] == len(P6_DOCUMENTATION_AUDIT)
    assert sum(
        summary[key]
        for key in (
            DOC_CORE_RULES_EXTRACTED,
            DOC_INDEXED_NOT_LINE_REVIEWED,
            DOC_TOPIC_MAP_PARTIAL,
            DOC_PRODUCT_SCOPE_PENDING,
        )
    ) == len(P6_DOCUMENTATION_AUDIT)
    # The manifest must stay honest: index discovery is not line-by-line review.
    assert summary[DOC_INDEXED_NOT_LINE_REVIEWED] >= 1
    assert summary[DOC_PRODUCT_SCOPE_PENDING] >= 1


def test_calendar_and_data_date_links_point_to_current_official_p6_help_pages():
    assert ORACLE_SOURCES["calendars"].endswith("/calendars.htm")
    assert ORACLE_SOURCES["data_date"].endswith("/data_date.htm")


def test_resource_leveling_registry_tracks_merged_persisted_production_path_without_claiming_parity():
    assert REFERENCE_VERSION == "0.8.8"
    leveling = get_reference("RES-002")
    assert leveling.coverage == MAPPED_NOT_PROVEN
    assert "src/construction_pm/p6_persisted_resource_leveling_resolver.py" in leveling.cubi_code_paths
    assert "src/construction_pm/backend_p0/authoritative_schedule_query.py" in leveling.cubi_code_paths
    assert "tests/test_persisted_resource_leveling_resolver.py" in leveling.regression_tests
    assert "tests/test_authoritative_schedule_snapshot_composer.py" in leveling.regression_tests
    assert "Issue #1468 open" in leveling.known_gap

    capacity = get_reference("RES-003")
    assert "src/construction_pm/p6_persisted_resource_leveling_resolver.py" in capacity.cubi_code_paths
    assert "Hours-per-Time-Period" in capacity.known_gap

    formula = get_formula_reference("FRM-LEVEL-001")
    assert formula.status == "FORMULA_DOCUMENTED_PARITY_NOT_PROVEN"
    assert "src/construction_pm/p6_persisted_resource_leveling_resolver.py" in formula.cubi_code_paths
    assert "tests/scheduling/test_authoritative_schedule_batch.py" in formula.regression_tests
