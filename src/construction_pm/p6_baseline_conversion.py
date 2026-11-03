from __future__ import annotations

"""Convert another project into an immutable baseline (BAS-001).

P6 baseline identity is project-scoped, so converting another project is a
real cross-scope operation: the source project is read through its own scope
and revision, the source activity values are copied, and only the target
project receives a new baseline identity and immutable baseline-activity
rows. The source project is never modified.

The source may be either the source project's current activity values or one
of its existing baselines. The conversion is atomic: baseline metadata and
every baseline activity row commit together, or nothing is written.
"""

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from typing import Callable, Iterable

from .backend_p0.models import BackendScope, MAX_SAFE_REVISION
from .p6_baseline_activity_repository import (
    P6BaselineActivity,
    P6BaselineActivityRepository,
)
from .p6_baseline_repository import P6Baseline, P6BaselineRepository
from .p6_baseline_update import BaselineCurrentActivitySource

BASELINE_CONVERSION_SOURCE_CURRENT = "CURRENT"
BASELINE_CONVERSION_SOURCE_BASELINE = "BASELINE"


class P6BaselineConversionError(ValueError):
    """Raised when a cross-project baseline conversion is invalid or conflicts."""


def _identifier(value: object, code: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise P6BaselineConversionError(code)
    return value


@dataclass(frozen=True)
class P6BaselineConversionResult:
    """The immutable target metadata, copied rows and source provenance."""

    source_scope: BackendScope
    target_scope: BackendScope
    source_kind: str
    source_baseline_id: str | None
    baseline: P6Baseline
    rows: tuple[P6BaselineActivity, ...]
    replayed: bool = False

    def currency_totals(self) -> tuple[dict[str, object], ...]:
        totals: dict[str, tuple[int, Decimal]] = {}
        for row in self.rows:
            count, amount = totals.get(
                row.currency, (0, Decimal("0"))
            )
            totals[row.currency] = (count + 1, amount + row.budgeted_cost)
        return tuple(
            {
                "currency": currency,
                "activity_count": totals[currency][0],
                "total_budget": str(totals[currency][1]),
            }
            for currency in sorted(totals)
        )


def _validated_rows(
    rows: Iterable[P6BaselineActivity],
    *,
    source_scope: BackendScope,
    code: str,
) -> tuple[P6BaselineActivity, ...]:
    result = tuple(rows)
    if not result:
        raise P6BaselineConversionError(code)
    seen: set[str] = set()
    for row in result:
        if not isinstance(row, P6BaselineActivity):
            raise P6BaselineConversionError("BASELINE_CONVERSION_SOURCE_ROW_INVALID")
        row.validate()
        if row.scope != source_scope:
            raise P6BaselineConversionError(
                "BASELINE_CONVERSION_SOURCE_SCOPE_MISMATCH"
            )
        if row.activity_id in seen:
            raise P6BaselineConversionError(
                f"BASELINE_CONVERSION_DUPLICATE_ACTIVITY:{row.activity_id}"
            )
        seen.add(row.activity_id)
    return tuple(sorted(result, key=lambda item: item.activity_id))


@dataclass(frozen=True)
class P6BaselineConversionService:
    """Read one project and write a new immutable baseline in another project."""

    baseline_repository: P6BaselineRepository
    baseline_activity_repository: P6BaselineActivityRepository
    current_source: BaselineCurrentActivitySource
    transaction_manager: object
    clock: Callable[[], str] | None = None

    def _now(self) -> str:
        if self.clock is not None:
            return self.clock()
        return datetime.now().astimezone().isoformat()

    def _source_rows(
        self,
        source_scope: BackendScope,
        source_baseline_id: str | None,
    ) -> tuple[str, str | None, tuple[P6BaselineActivity, ...]]:
        if source_baseline_id is None:
            rows = tuple(
                self.current_source.list_as_baseline(source_scope)
            )
            return (
                BASELINE_CONVERSION_SOURCE_CURRENT,
                None,
                _validated_rows(
                    rows,
                    source_scope=source_scope,
                    code="BASELINE_CONVERSION_SOURCE_EMPTY",
                ),
            )
        identifier = _identifier(
            source_baseline_id, "BASELINE_CONVERSION_SOURCE_INVALID"
        )
        if self.baseline_repository.get(source_scope, identifier) is None:
            raise P6BaselineConversionError(
                "BASELINE_CONVERSION_SOURCE_NOT_FOUND"
            )
        rows = tuple(
            self.baseline_activity_repository.list(source_scope, identifier)
        )
        return (
            BASELINE_CONVERSION_SOURCE_BASELINE,
            identifier,
            _validated_rows(
                rows,
                source_scope=source_scope,
                code="BASELINE_CONVERSION_SOURCE_EMPTY",
            ),
        )

    def convert(
        self,
        source_scope: BackendScope,
        target_scope: BackendScope,
        *,
        target_baseline_id: str,
        target_name: str,
        source_baseline_id: str | None = None,
        baseline_type: str = "USER_SELECTED",
        notes: str | None = None,
        created_at: str | None = None,
    ) -> P6BaselineConversionResult:
        source_scope.validate()
        target_scope.validate()
        if not 0 <= target_scope.project_revision <= MAX_SAFE_REVISION:
            raise P6BaselineConversionError("INVALID_PROJECT_REVISION")
        if source_scope.tenant_id != target_scope.tenant_id:
            raise P6BaselineConversionError(
                "BASELINE_CONVERSION_TENANT_MISMATCH"
            )
        if source_scope.project_id == target_scope.project_id:
            raise P6BaselineConversionError(
                "BASELINE_CONVERSION_SAME_PROJECT"
            )
        target_identifier = _identifier(
            target_baseline_id, "BASELINE_CONVERSION_TARGET_INVALID"
        )
        if not isinstance(target_name, str) or not target_name.strip():
            raise P6BaselineConversionError(
                "BASELINE_CONVERSION_TARGET_NAME_INVALID"
            )
        if notes is not None and not isinstance(notes, str):
            raise P6BaselineConversionError("BASELINE_CONVERSION_NOTES_INVALID")

        source_kind, resolved_source_id, source_rows = self._source_rows(
            source_scope, source_baseline_id
        )
        metadata = P6Baseline(
            scope=target_scope,
            baseline_id=target_identifier,
            name=target_name,
            baseline_type=baseline_type,
            source_revision=source_scope.project_revision,
            created_at=(
                created_at if created_at is not None else self._now()
            ),
            notes=notes,
        )
        metadata.validate()
        target_rows = tuple(
            replace(
                row,
                scope=target_scope,
                baseline_id=target_identifier,
            )
            for row in source_rows
        )
        for row in target_rows:
            row.validate()

        with self.transaction_manager.transaction():
            existing_metadata = self.baseline_repository.get(
                target_scope, target_identifier
            )
            existing_rows = self.baseline_activity_repository.list(
                target_scope, target_identifier
            )
            if existing_metadata is not None or existing_rows:
                # A retry generated its own timestamp; the conversion identity
                # is the metadata content plus the copied rows, not the clock.
                comparable = (
                    metadata
                    if created_at is not None
                    else (
                        metadata
                        if existing_metadata is None
                        else replace(
                            metadata,
                            created_at=existing_metadata.created_at,
                        )
                    )
                )
                if (
                    existing_metadata == comparable
                    and existing_rows == target_rows
                ):
                    return P6BaselineConversionResult(
                        source_scope=source_scope,
                        target_scope=target_scope,
                        source_kind=source_kind,
                        source_baseline_id=resolved_source_id,
                        baseline=comparable,
                        rows=target_rows,
                        replayed=True,
                    )
                raise P6BaselineConversionError(
                    "BASELINE_CONVERSION_TARGET_EXISTS"
                )
            stored_metadata = self.baseline_repository.upsert(metadata)
            if stored_metadata != metadata:
                raise P6BaselineConversionError(
                    "BASELINE_CONVERSION_METADATA_WRITE_MISMATCH"
                )
            stored_rows = self.baseline_activity_repository.save_many(
                target_rows
            )
            if stored_rows != target_rows:
                raise P6BaselineConversionError(
                    "BASELINE_CONVERSION_ROW_WRITE_MISMATCH"
                )
            return P6BaselineConversionResult(
                source_scope=source_scope,
                target_scope=target_scope,
                source_kind=source_kind,
                source_baseline_id=resolved_source_id,
                baseline=metadata,
                rows=target_rows,
            )


__all__ = [
    "BASELINE_CONVERSION_SOURCE_BASELINE",
    "BASELINE_CONVERSION_SOURCE_CURRENT",
    "P6BaselineConversionError",
    "P6BaselineConversionResult",
    "P6BaselineConversionService",
]
