from __future__ import annotations

"""Read-only, scope-bound source adapter for ENG-06 auxiliary project records."""

from contextlib import nullcontext
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)
from construction_pm.backend_p0.models import BackendScope
from .quality_policy_pack import ScheduleQualityPolicyRepository
from construction_pm.p6_interchange_import_ledger import P6InterchangeImportLedgerRepository


class ReadRepository(Protocol):
    def list(self, scope: BackendScope) -> tuple[Any, ...]: ...


class BaselineActivityRepository(Protocol):
    def list(self, scope: BackendScope, baseline_id: str) -> tuple[Any, ...]: ...


class ResourcePeriodRepository(Protocol):
    def list(
        self, scope: BackendScope, assignment_id: str | None = None
    ) -> tuple[Any, ...]: ...


class TransactionManager(Protocol):
    def transaction(self): ...


def _enum_value(value: object) -> object:
    return getattr(value, "value", value)


def _decimal_text(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


@dataclass(frozen=True)
class ScheduleQualityAuditContextReader:
    """Load only auxiliary records needed to audit one project revision."""

    authorization_policy: AuthorizationPolicy
    wbs_repository: ReadRepository | None = None
    baseline_repository: ReadRepository | None = None
    baseline_activity_repository: BaselineActivityRepository | None = None
    baseline_assignment_repository: ReadRepository | None = None
    resource_assignment_repository: ReadRepository | None = None
    resource_period_repository: ResourcePeriodRepository | None = None
    code_definition_repository: ReadRepository | None = None
    code_assignment_repository: ReadRepository | None = None
    quality_policy_repository: ScheduleQualityPolicyRepository | None = None
    interchange_import_ledger_repository: P6InterchangeImportLedgerRepository | None = None
    transaction_manager: TransactionManager | None = None

    def load(
        self,
        scope: BackendScope,
        auth_context: AuthorizationContext,
    ) -> dict[str, object]:
        scope.validate()
        auth_context.validate()
        if (
            scope.tenant_id != auth_context.tenant_id
            or scope.project_id != auth_context.project_id
        ):
            raise AuthorizationError("CROSS_SCOPE_ACCESS")
        if not self.authorization_policy.is_allowed(
            auth_context, Permission.PROJECT_READ
        ):
            raise AuthorizationError("authorization denied for permission=project.read")

        transaction = (
            self.transaction_manager.transaction()
            if self.transaction_manager is not None
            else nullcontext()
        )
        with transaction:
            wbs_nodes = self._load_wbs(scope)
            baselines, baseline_activities = self._load_baselines(scope)
            baseline_assignments = self._load_baseline_assignments(scope)
            resource_assignments = self._load_resource_assignments(scope)
            resource_periods = self._load_resource_periods(scope)
            code_definitions = self._load_code_definitions(scope)
            code_assignments = self._load_code_assignments(scope)
            quality_policy_pack = self._load_approved_quality_policy(scope)
            interchange_import_batches = self._load_interchange_import_batches(scope)

        return {
            "wbs_nodes": wbs_nodes,
            "baselines": baselines,
            "baseline_activities": baseline_activities,
            "baseline_assignments": baseline_assignments,
            "resource_assignments": resource_assignments,
            "resource_periods": resource_periods,
            "code_definitions": code_definitions,
            "code_assignments": code_assignments,
            "quality_policy_repository_configured": self.quality_policy_repository is not None,
            "approved_quality_policy_pack": quality_policy_pack,
            "interchange_import_ledger_configured": self.interchange_import_ledger_repository is not None,
            "interchange_import_batches": interchange_import_batches,
        }

    def _load_wbs(self, scope: BackendScope) -> list[dict[str, object]] | None:
        if self.wbs_repository is None:
            return None
        return [
            {
                "wbs_id": item.wbs_id,
                "parent_kind": str(_enum_value(item.parent_kind)),
                "parent_wbs_id": item.parent_wbs_id,
                "code": item.code,
                "name": item.name,
                "sequence_number": item.sequence_number,
                "record_revision": item.record_revision,
            }
            for item in self.wbs_repository.list(scope)
        ]

    def _load_baselines(
        self, scope: BackendScope
    ) -> tuple[list[dict[str, object]] | None, list[dict[str, object]] | None]:
        if self.baseline_repository is None:
            return None, None
        baselines = self.baseline_repository.list(scope)
        metadata = [
            {
                "baseline_id": item.baseline_id,
                "name": item.name,
                "baseline_type": item.baseline_type,
                "source_revision": item.source_revision,
                "created_at": item.created_at,
            }
            for item in baselines
        ]
        if self.baseline_activity_repository is None:
            return metadata, None
        rows: list[dict[str, object]] = []
        for baseline in baselines:
            for item in self.baseline_activity_repository.list(
                scope, baseline.baseline_id
            ):
                rows.append(
                    {
                        "baseline_id": item.baseline_id,
                        "activity_id": item.activity_id,
                        "planned_start": item.planned_start.isoformat(),
                        "planned_finish": item.planned_finish.isoformat(),
                        "budgeted_cost": _decimal_text(item.budgeted_cost),
                        "currency": item.currency,
                        "wbs_id": item.wbs_id,
                        "earned_value_technique": item.earned_value_technique,
                    }
                )
        return metadata, rows

    def _load_baseline_assignments(
        self, scope: BackendScope
    ) -> list[dict[str, object]] | None:
        if self.baseline_assignment_repository is None:
            return None
        return [
            {"role": item.role, "baseline_id": item.baseline_id}
            for item in self.baseline_assignment_repository.list(scope)
        ]

    def _load_resource_assignments(
        self, scope: BackendScope
    ) -> list[dict[str, object]] | None:
        if self.resource_assignment_repository is None:
            return None
        return [
            {
                "assignment_id": item.assignment_id,
                "activity_id": item.activity_id,
                "resource_id": item.resource_id,
                "role_id": item.role_id,
                "units": _decimal_text(item.units),
                "actual_units": _decimal_text(item.actual_units),
                "remaining_units": _decimal_text(item.remaining_units),
                "planned_cost": _decimal_text(item.planned_cost),
                "actual_cost": _decimal_text(item.actual_cost),
                "remaining_cost": _decimal_text(item.remaining_cost),
                "unit": item.unit,
                "currency": item.currency,
                "calendar_id": item.calendar_id,
                "calendar_version": item.calendar_version,
                "is_driving": item.is_driving,
                "units_per_time": _decimal_text(item.units_per_time),
                "units_per_time_period": item.units_per_time_period,
                "hours_per_units_time_period": _decimal_text(
                    item.hours_per_units_time_period
                ),
            }
            for item in self.resource_assignment_repository.list(scope)
        ]

    def _load_code_definitions(
        self, scope: BackendScope
    ) -> list[dict[str, object]] | None:
        if self.code_definition_repository is None:
            return None
        return [
            {
                "code_id": item.code_id,
                "name": item.name,
                "subject_area": item.subject_area,
                "scope_kind": item.scope_kind,
                "scope_key": item.scope_key,
                "values": [
                    {
                        "value_id": value.value_id,
                        "value": value.value,
                    }
                    for value in item.values
                ],
            }
            for item in self.code_definition_repository.list(scope)
        ]

    def _load_code_assignments(
        self, scope: BackendScope
    ) -> list[dict[str, object]] | None:
        if self.code_assignment_repository is None:
            return None
        return [
            {
                "code_id": item.code_id,
                "value_id": item.value_id,
                "owner_type": item.owner_type,
                "owner_id": item.owner_id,
            }
            for item in self.code_assignment_repository.list(scope)
        ]

    def _load_interchange_import_batches(
        self, scope: BackendScope
    ) -> list[dict[str, object]] | None:
        if self.interchange_import_ledger_repository is None:
            return None
        return [
            {
                "batch_id": item.batch_id,
                "project_revision": item.scope.project_revision,
                "format": item.format,
                "source_sha256": item.source_sha256,
                "source_byte_count": item.source_byte_count,
                "row_count": item.row_count,
                "mapping_snapshot": [dict(mapping) for mapping in item.mapping_snapshot],
                "row_summaries": [dict(row) for row in item.row_summaries],
                "imported_by": item.imported_by,
                "imported_at": item.imported_at.isoformat(),
                "target_application_status": item.target_application_status,
            }
            for item in self.interchange_import_ledger_repository.list(scope, limit=100)
        ]

    def _load_approved_quality_policy(
        self, scope: BackendScope
    ) -> dict[str, object] | None:
        if self.quality_policy_repository is None:
            return None
        pack = self.quality_policy_repository.latest_approved(scope)
        if pack is None:
            return None
        return {
            "policy_id": pack.policy_id,
            "version": pack.version,
            "name": pack.name,
            "scoring_method": pack.scoring_method,
            "thresholds": dict(pack.thresholds),
            "weights": dict(pack.weights),
            "created_by": pack.created_by,
            "created_at": pack.created_at.isoformat(),
            "approved_by": pack.approved_by,
            "approved_at": None if pack.approved_at is None else pack.approved_at.isoformat(),
        }

    def _load_resource_periods(
        self, scope: BackendScope
    ) -> list[dict[str, object]] | None:
        if self.resource_period_repository is None:
            return None
        return [
            {
                "assignment_id": item.assignment_id,
                "activity_id": item.activity_id,
                "resource_id": item.resource_id,
                "period_start": item.period_start,
                "units": _decimal_text(item.units),
                "cost": _decimal_text(item.cost),
            }
            for item in self.resource_period_repository.list(scope)
        ]


__all__ = ["ScheduleQualityAuditContextReader"]
