from __future__ import annotations

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_interchange_mapping import (
    P6InterchangeCompatibilityError,
    P6InterchangeMapper,
    P6InterchangeRow,
)
from construction_pm.p6_mapping_registry import (
    P6MappingDefinition,
    P6MappingFormat,
    P6MappingStatus,
    PersistedP6Mapping,
)


def scope() -> BackendScope:
    return BackendScope(tenant_id="t1", project_id="p1", project_revision=4)


def mapping(
    mapping_id: str,
    *,
    source: str,
    canonical: str,
    status: P6MappingStatus,
) -> PersistedP6Mapping:
    return PersistedP6Mapping(
        scope=scope(),
        definition=P6MappingDefinition(
            mapping_id=mapping_id,
            registry_version="p6-field-registry.v1",
            format=P6MappingFormat.XER_PROJECT,
            subject_area="Activity",
            source_field=source,
            canonical_field=canonical,
            status=status,
        ),
    )


def mapper() -> P6InterchangeMapper:
    return P6InterchangeMapper(
        (
            mapping(
                "activity.code",
                source="task_code",
                canonical="activity.code",
                status=P6MappingStatus.SUPPORTED,
            ),
            mapping(
                "activity.legacy",
                source="legacy_code",
                canonical="activity.legacy",
                status=P6MappingStatus.UNSUPPORTED_PRESERVE,
            ),
        )
    )


def test_import_maps_supported_and_preserves_unsupported_and_unknown_fields() -> None:
    result = mapper().import_row(
        P6InterchangeRow(
            scope=scope(),
            format=P6MappingFormat.XER_PROJECT,
            values={
                "task_code": "A-10",
                "legacy_code": "L-7",
                "vendor_extension": {"raw": 1},
            },
        )
    )

    assert result.values == {"activity.code": "A-10"}
    assert result.extensions["p6.interchange.t1.p1.legacy_code"] == "L-7"
    assert result.extensions["p6.interchange.t1.p1.vendor_extension"] == {"raw": 1}
    assert "PRESERVED_UNSUPPORTED_FIELD:legacy_code" in result.warnings
    assert "PRESERVED_UNKNOWN_FIELD:vendor_extension" in result.warnings


def test_export_maps_supported_and_preserves_unknown_canonical_fields() -> None:
    result = mapper().export_row(
        P6InterchangeRow(
            scope=scope(),
            format=P6MappingFormat.XER_PROJECT,
            values={"activity.code": "A-10", "activity.custom": 42},
        )
    )

    assert result.values == {"task_code": "A-10"}
    assert result.extensions["p6.interchange.t1.p1.canonical:activity.custom"] == 42
    assert "PRESERVED_UNKNOWN_CANONICAL_FIELD:activity.custom" in result.warnings


def test_mapping_for_other_format_is_not_applied() -> None:
    other_format = PersistedP6Mapping(
        scope=scope(),
        definition=P6MappingDefinition(
            mapping_id="activity.other-format",
            registry_version="p6-field-registry.v1",
            format=P6MappingFormat.XLSX,
            subject_area="Activity",
            source_field="xlsx_task_code",
            canonical_field="activity.xlsx_code",
            status=P6MappingStatus.SUPPORTED,
        ),
    )
    mapper_for_both = P6InterchangeMapper((mapping(
        "activity.code",
        source="task_code",
        canonical="activity.code",
        status=P6MappingStatus.SUPPORTED,
    ), other_format))

    result = mapper_for_both.import_row(
        P6InterchangeRow(
            scope=scope(),
            format=P6MappingFormat.XER_PROJECT,
            values={"task_code": "A-10", "xlsx_task_code": "X-10"},
        )
    )

    assert result.values == {"activity.code": "A-10"}
    assert result.extensions["p6.interchange.t1.p1.xlsx_task_code"] == "X-10"
    assert "PRESERVED_UNKNOWN_FIELD:xlsx_task_code" in result.warnings



def test_reject_status_fails_closed_in_both_directions() -> None:
    reject = P6InterchangeMapper(
        (
            mapping(
                "activity.secret",
                source="secret_code",
                canonical="activity.secret",
                status=P6MappingStatus.UNSUPPORTED_REJECT,
            ),
        )
    )
    row = P6InterchangeRow(
        scope=scope(),
        format=P6MappingFormat.XER_PROJECT,
        values={"secret_code": "X"},
    )

    with pytest.raises(
        P6InterchangeCompatibilityError,
        match="UNSUPPORTED_FIELD_REJECTED:secret_code",
    ):
        reject.import_row(row)

    export_row = P6InterchangeRow(
        scope=scope(),
        format=P6MappingFormat.XER_PROJECT,
        values={"activity.secret": "X"},
    )
    with pytest.raises(
        P6InterchangeCompatibilityError,
        match="UNSUPPORTED_FIELD_REJECTED:activity.secret",
    ):
        reject.export_row(export_row)


def test_ambiguous_source_or_canonical_mapping_is_rejected() -> None:
    duplicate_source = mapping(
        "activity.code.alias",
        source="task_code",
        canonical="activity.code.alias",
        status=P6MappingStatus.SUPPORTED,
    )
    with pytest.raises(
        P6InterchangeCompatibilityError,
        match="AMBIGUOUS_SOURCE_FIELD:XER_PROJECT:task_code",
    ):
        P6InterchangeMapper((mapping(
            "activity.code",
            source="task_code",
            canonical="activity.code",
            status=P6MappingStatus.SUPPORTED,
        ), duplicate_source))

    duplicate_canonical = mapping(
        "activity.code.alias",
        source="other_task_code",
        canonical="activity.code",
        status=P6MappingStatus.SUPPORTED,
    )
    with pytest.raises(
        P6InterchangeCompatibilityError,
        match="AMBIGUOUS_CANONICAL_FIELD:XER_PROJECT:activity.code",
    ):
        P6InterchangeMapper((mapping(
            "activity.code",
            source="task_code",
            canonical="activity.code",
            status=P6MappingStatus.SUPPORTED,
        ), duplicate_canonical))


def test_mapping_scope_mismatch_is_rejected() -> None:
    other = PersistedP6Mapping(
        scope=BackendScope(tenant_id="other", project_id="p1", project_revision=4),
        definition=P6MappingDefinition(
            mapping_id="other.code",
            registry_version="p6-field-registry.v1",
            format=P6MappingFormat.XER_PROJECT,
            subject_area="Activity",
            source_field="other_code",
            canonical_field="activity.other",
            status=P6MappingStatus.SUPPORTED,
        ),
    )

    with pytest.raises(
        P6InterchangeCompatibilityError,
        match="MAPPING_SCOPE_MISMATCH",
    ):
        P6InterchangeMapper((mapping(
            "activity.code",
            source="task_code",
            canonical="activity.code",
            status=P6MappingStatus.SUPPORTED,
        ), other))


def test_row_scope_mismatch_is_rejected() -> None:
    other_scope = BackendScope(
        tenant_id="other",
        project_id="p1",
        project_revision=4,
    )
    row = P6InterchangeRow(
        scope=other_scope,
        format=P6MappingFormat.XER_PROJECT,
        values={"task_code": "A-10"},
    )

    with pytest.raises(
        P6InterchangeCompatibilityError,
        match="ROW_SCOPE_MISMATCH",
    ):
        mapper().import_row(row)
