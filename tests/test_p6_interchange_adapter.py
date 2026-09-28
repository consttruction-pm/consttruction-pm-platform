from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_interchange_adapter import (
    P6InterchangeAdapter,
    P6InterchangeAdapterError,
)
from construction_pm.p6_interchange_mapping import (
    P6InterchangeResult,
    P6InterchangeRow,
)
from construction_pm.p6_mapping_registry import (
    P6MappingDefinition,
    P6MappingFormat,
    P6MappingStatus,
    PersistedP6Mapping,
)
from construction_pm.p6_interchange_mapping import P6InterchangeMapper


def scope() -> BackendScope:
    return BackendScope(tenant_id="t1", project_id="p1", project_revision=4)


def mapper() -> P6InterchangeMapper:
    return P6InterchangeMapper(
        (
            PersistedP6Mapping(
                scope=scope(),
                definition=P6MappingDefinition(
                    mapping_id="activity.code",
                    registry_version="p6-field-registry.v1",
                    format=P6MappingFormat.XER_PROJECT,
                    subject_area="Activity",
                    source_field="task_code",
                    canonical_field="activity.code",
                    status=P6MappingStatus.SUPPORTED,
                ),
            ),
        )
    )


@dataclass
class FakeCodec:
    format: P6MappingFormat = P6MappingFormat.XER_PROJECT
    encoded: tuple[P6InterchangeResult, ...] | None = None

    def decode(self, payload: Any, scope: BackendScope) -> Sequence[P6InterchangeRow]:
        return (
            P6InterchangeRow(
                scope=scope,
                format=self.format,
                values=dict(payload),
            ),
        )

    def encode(
        self,
        rows: Sequence[P6InterchangeResult],
        scope: BackendScope,
    ) -> Any:
        self.encoded = tuple(rows)
        return {"rows": [row.values for row in rows]}


def test_import_delegates_external_parsing_to_codec_and_mapping_to_mapper() -> None:
    codec = FakeCodec()
    adapter = P6InterchangeAdapter(mapper=mapper(), codec=codec)

    result = adapter.import_document({"task_code": "A-10"}, scope=scope())

    assert result[0].values == {"activity.code": "A-10"}
    assert result[0].extensions == {}


def test_export_delegates_mapping_then_external_serialization_to_codec() -> None:
    codec = FakeCodec()
    adapter = P6InterchangeAdapter(mapper=mapper(), codec=codec)

    payload = adapter.export_document(({"activity.code": "A-10"},), scope=scope())

    assert payload == {"rows": [{"task_code": "A-10"}]}
    assert codec.encoded is not None
    assert codec.encoded[0].values == {"task_code": "A-10"}


def test_adapter_rejects_codec_rows_from_wrong_format() -> None:
    class WrongFormatCodec(FakeCodec):
        def decode(self, payload: Any, scope: BackendScope) -> Sequence[P6InterchangeRow]:
            return (
                P6InterchangeRow(
                    scope=scope,
                    format=P6MappingFormat.XLSX,
                    values=dict(payload),
                ),
            )

    with pytest.raises(P6InterchangeAdapterError, match="ROW_FORMAT_MISMATCH"):
        P6InterchangeAdapter(mapper=mapper(), codec=WrongFormatCodec()).import_document(
            {"task_code": "A-10"}, scope=scope()
        )


def test_adapter_rejects_codec_rows_from_wrong_scope() -> None:
    class WrongScopeCodec(FakeCodec):
        def decode(self, payload: Any, scope: BackendScope) -> Sequence[P6InterchangeRow]:
            other_scope = BackendScope(
                tenant_id="other",
                project_id=scope.project_id,
                project_revision=scope.project_revision,
            )
            return (
                P6InterchangeRow(
                    scope=other_scope,
                    format=self.format,
                    values={"task_code": "A-10"},
                ),
            )

    with pytest.raises(P6InterchangeAdapterError, match="ROW_SCOPE_MISMATCH"):
        P6InterchangeAdapter(mapper=mapper(), codec=WrongScopeCodec()).import_document(
            {"task_code": "A-10"}, scope=scope()
        )


def test_export_rejects_mismatched_extension_row_count() -> None:
    codec = FakeCodec()
    adapter = P6InterchangeAdapter(mapper=mapper(), codec=codec)

    with pytest.raises(P6InterchangeAdapterError, match="EXTENSION_ROW_COUNT_MISMATCH"):
        adapter.export_document(
            ({"activity.code": "A-10"}, {"activity.code": "A-20"}),
            scope=scope(),
            extensions=({"p6.example": "x"},),
        )
