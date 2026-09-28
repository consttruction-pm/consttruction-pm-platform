from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence

from .backend_p0.models import BackendScope
from .p6_interchange_mapping import (
    P6InterchangeMapper,
    P6InterchangeResult,
    P6InterchangeRow,
)
from .p6_mapping_registry import P6MappingFormat


class P6InterchangeAdapterError(ValueError):
    """Raised when a provider adapter violates the interchange boundary."""


class P6InterchangeCodec(Protocol):
    """Provider-specific parser/writer contract.

    Implementations own external file grammar. They must not implement canonical
    P6 field semantics; those semantics remain in P6InterchangeMapper.
    """

    format: P6MappingFormat

    def decode(self, payload: Any, scope: BackendScope) -> Sequence[P6InterchangeRow]:
        """Parse an external document into provider-format interchange rows."""

    def encode(
        self,
        rows: Sequence[P6InterchangeResult],
        scope: BackendScope,
    ) -> Any:
        """Serialize mapped provider-format rows into the external document."""


@dataclass(frozen=True)
class P6InterchangeAdapter:
    """Provider-neutral orchestration around a provider-specific codec."""

    mapper: P6InterchangeMapper
    codec: P6InterchangeCodec

    def import_document(
        self,
        payload: Any,
        *,
        scope: BackendScope,
    ) -> tuple[P6InterchangeResult, ...]:
        scope.validate()
        self._validate_codec_format()
        rows = tuple(self.codec.decode(payload, scope))
        self._validate_rows(rows, scope)
        return tuple(self.mapper.import_row(row) for row in rows)

    def export_document(
        self,
        values: Sequence[Mapping[str, Any]],
        *,
        scope: BackendScope,
        extensions: Sequence[Mapping[str, Any]] | None = None,
    ) -> Any:
        scope.validate()
        self._validate_codec_format()
        extension_rows = tuple(extensions or ())
        if len(extension_rows) not in (0, len(values)):
            raise P6InterchangeAdapterError("EXTENSION_ROW_COUNT_MISMATCH")

        rows = tuple(
            P6InterchangeRow(
                scope=scope,
                format=self.codec.format,
                values=dict(values[index]),
                extensions=dict(extension_rows[index]) if extension_rows else {},
            )
            for index in range(len(values))
        )
        results = tuple(self.mapper.export_row(row) for row in rows)
        return self.codec.encode(results, scope)

    def _validate_codec_format(self) -> None:
        if not isinstance(self.codec.format, P6MappingFormat):
            raise P6InterchangeAdapterError("INVALID_CODEC_FORMAT")

    def _validate_rows(
        self,
        rows: Sequence[P6InterchangeRow],
        scope: BackendScope,
    ) -> None:
        for row in rows:
            if row.scope != scope:
                raise P6InterchangeAdapterError("ROW_SCOPE_MISMATCH")
            if row.format is not self.codec.format:
                raise P6InterchangeAdapterError("ROW_FORMAT_MISMATCH")


__all__ = [
    "P6InterchangeAdapter",
    "P6InterchangeAdapterError",
    "P6InterchangeCodec",
]
