"""Authoritative datasets and authorization boundary for the report register."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Mapping, Protocol

from .api_errors import (
    APIError,
    authorization_error,
    conflict_error,
    validation_error,
)
from .application.authorization import (
    AuthorizationContext,
    AuthorizationPolicy,
    Permission,
)
from .backend_p0.models import BackendScope
from .report_persistence import (
    ReportAuditEvent,
    ReportDefinition,
    ReportIdempotencyReuse,
    ReportPersistenceError,
    ReportRevisionConflict,
    ReportRun,
    ReportStore,
    StoredReportDefinition,
)


class ReportAuthorizationError(ValueError):
    pass


class ReportDatasetError(ValueError):
    pass


class ReportDatasetSource(Protocol):
    def build(
        self, scope: BackendScope, subject: str, columns: tuple[str, ...]
    ) -> tuple[Mapping[str, Any], ...]: ...


def _iso(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _enum(value: object) -> str:
    return str(getattr(value, "value", value))


@dataclass(frozen=True)
class AuthoritativeReportDataset:
    """Reads stored facts for one subject; performs no calculation of its own."""

    activity_repository: object
    resource_repository: object
    risk_store: object

    def build(
        self, scope: BackendScope, subject: str, columns: tuple[str, ...]
    ) -> tuple[Mapping[str, Any], ...]:
        scope.validate()
        if subject not in {"activities", "resources", "risks"}:
            raise ReportDatasetError("INVALID_REPORT_SUBJECT")
        try:
            rows = tuple(self._rows(scope, subject))
        except ReportDatasetError:
            raise
        except Exception as exc:  # noqa: BLE001 - bounded dataset boundary
            raise ReportDatasetError("REPORT_DATASET_UNAVAILABLE") from exc
        return tuple(
            {column: self._value(row.get(column)) for column in columns}
            for row in rows
        )

    @staticmethod
    def _value(value: object) -> object:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return str(value)

    def _rows(self, scope: BackendScope, subject: str) -> list[dict[str, object]]:
        if subject == "activities":
            return [
                {
                    "activity_id": item.activity_id,
                    "name": item.name,
                    "activity_type": _enum(item.activity_type),
                    "status": _enum(item.status),
                    "actual_start": _iso(item.actual_start),
                    "expected_finish": _iso(item.expected_finish),
                    "duration": f"{item.duration_value} {_enum(item.duration_unit)}",
                    "percent_complete": item.percent_complete,
                }
                for item in sorted(
                    self.activity_repository.list(scope),
                    key=lambda item: item.activity_id,
                )
            ]
        if subject == "resources":
            return [
                {
                    "resource_id": item.resource_id,
                    "name": item.name,
                    "resource_type": item.resource_type,
                    "parent_resource_id": item.parent_resource_id,
                    "calendar_id": item.calendar_id,
                    "unit_of_measure": item.unit_of_measure,
                    "is_active": item.is_active,
                }
                for item in sorted(
                    self.resource_repository.list(
                        scope.tenant_id, scope.project_id, scope.project_revision
                    ),
                    key=lambda item: item.resource_id,
                )
            ]
        risks = self.risk_store.list_risks(scope.tenant_id, scope.project_id)
        return [
            {
                "risk_id": stored.risk.risk_id,
                "title": stored.risk.title,
                "category": stored.risk.category,
                "status": stored.risk.status,
                "probability": stored.risk.probability,
                "impact": stored.risk.impact,
                "score": stored.risk.score,
                "exposure_level": stored.risk.exposure_level,
            }
            for stored in sorted(risks, key=lambda item: item.risk.risk_id)
        ]


@dataclass(frozen=True)
class ReportApplicationService:
    """Authorization and run orchestration over the stored report register."""

    store: ReportStore
    dataset: ReportDatasetSource
    authorization_policy: AuthorizationPolicy
    transaction_manager: object

    # -- reads ------------------------------------------------------------
    def list_definitions(
        self,
        *,
        tenant_id: str,
        project_id: str,
        context: AuthorizationContext,
        subject: str | None = None,
        search: str | None = None,
    ) -> tuple[StoredReportDefinition, ...]:
        self._check(context, tenant_id, project_id, Permission.PROJECT_READ)
        return self.store.list_definitions(
            tenant_id, project_id, subject=subject, search=search
        )

    def read_definition(
        self,
        *,
        tenant_id: str,
        project_id: str,
        report_id: str,
        context: AuthorizationContext,
    ) -> StoredReportDefinition:
        self._check(context, tenant_id, project_id, Permission.PROJECT_READ)
        return self.store.get_definition(tenant_id, project_id, report_id)

    def definition_history(
        self,
        *,
        tenant_id: str,
        project_id: str,
        report_id: str,
        context: AuthorizationContext,
    ) -> tuple[ReportAuditEvent, ...]:
        self._check(context, tenant_id, project_id, Permission.PROJECT_READ)
        self.store.get_definition(tenant_id, project_id, report_id)
        return self.store.definition_history(tenant_id, project_id, report_id)

    def list_runs(
        self,
        *,
        tenant_id: str,
        project_id: str,
        report_id: str,
        context: AuthorizationContext,
    ) -> tuple[ReportRun, ...]:
        self._check(context, tenant_id, project_id, Permission.PROJECT_READ)
        self.store.get_definition(tenant_id, project_id, report_id)
        return self.store.list_runs(tenant_id, project_id, report_id)

    def read_run(
        self,
        *,
        tenant_id: str,
        project_id: str,
        report_id: str,
        run_id: str,
        context: AuthorizationContext,
    ) -> ReportRun:
        self._check(context, tenant_id, project_id, Permission.PROJECT_READ)
        self.store.get_definition(tenant_id, project_id, report_id)
        return self.store.get_run(tenant_id, project_id, report_id, run_id)

    # -- writes -----------------------------------------------------------
    def create_definition(
        self,
        definition: ReportDefinition,
        *,
        idempotency_key: str,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredReportDefinition:
        self._authorize_write(
            definition.tenant_id, definition.project_id, context, actor_id
        )
        with self.transaction_manager.transaction():
            return self.store.create_definition(
                definition,
                idempotency_key=idempotency_key,
                actor_id=actor_id,
                occurred_at=occurred_at,
            )

    def update_definition(
        self,
        definition: ReportDefinition,
        *,
        expected_revision: int,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
        reason: str = "",
    ) -> StoredReportDefinition:
        self._authorize_write(
            definition.tenant_id, definition.project_id, context, actor_id
        )
        with self.transaction_manager.transaction():
            return self.store.update_definition(
                definition,
                expected_revision=expected_revision,
                actor_id=actor_id,
                occurred_at=occurred_at,
                reason=reason,
            )

    def delete_definition(
        self,
        *,
        tenant_id: str,
        project_id: str,
        report_id: str,
        expected_revision: int,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
        reason: str = "",
    ) -> None:
        self._authorize_write(tenant_id, project_id, context, actor_id)
        with self.transaction_manager.transaction():
            self.store.delete_definition(
                tenant_id=tenant_id,
                project_id=project_id,
                report_id=report_id,
                expected_revision=expected_revision,
                actor_id=actor_id,
                occurred_at=occurred_at,
                reason=reason,
            )

    def run_report(
        self,
        *,
        tenant_id: str,
        project_id: str,
        project_revision: int,
        report_id: str,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> ReportRun:
        self._check(context, tenant_id, project_id, Permission.PROJECT_READ)
        if actor_id != context.user_id:
            raise ReportAuthorizationError("REPORT_ACTOR_MISMATCH")
        if (
            isinstance(project_revision, bool)
            or not isinstance(project_revision, int)
            or project_revision < 0
        ):
            raise ReportPersistenceError("INVALID_REPORT_PROJECT_REVISION")
        if not isinstance(occurred_at, datetime) or occurred_at.tzinfo is None:
            raise ReportPersistenceError("INVALID_REPORT_OCCURRED_AT")
        with self.transaction_manager.transaction():
            stored = self.store.get_definition(tenant_id, project_id, report_id)
            columns = stored.definition.columns
            subject = stored.definition.subject
            rows = self.dataset.build(
                BackendScope(tenant_id, project_id, project_revision), subject, columns
            )
            run = ReportRun(
                run_id=self.store.next_run_id(tenant_id, project_id, report_id),
                tenant_id=tenant_id,
                project_id=project_id,
                report_id=report_id,
                report_revision=stored.revision,
                project_revision=project_revision,
                subject=subject,
                columns=columns,
                rows=rows,
                generated_at=occurred_at,
                generated_by=actor_id,
            )
            return self.store.save_run(run)

    # -- helpers ----------------------------------------------------------
    def _check(
        self,
        context: AuthorizationContext,
        tenant_id: str,
        project_id: str,
        permission: Permission,
    ) -> None:
        if tenant_id != context.tenant_id or project_id != context.project_id:
            raise ReportAuthorizationError("REPORT_CROSS_SCOPE_ACCESS")
        if not self.authorization_policy.is_allowed(context, permission):
            raise ReportAuthorizationError("REPORT_PERMISSION_DENIED")

    def _authorize_write(
        self,
        tenant_id: str,
        project_id: str,
        context: AuthorizationContext,
        actor_id: str,
    ) -> None:
        if actor_id != context.user_id:
            raise ReportAuthorizationError("REPORT_ACTOR_MISMATCH")
        self._check(context, tenant_id, project_id, Permission.PROJECT_WRITE)

    @staticmethod
    def error_dto(exc: Exception) -> APIError:
        if isinstance(exc, KeyError):
            code = str(exc.args[0]) if exc.args else "REPORT_NOT_FOUND"
            return validation_error(code, code)
        if isinstance(exc, ReportRevisionConflict):
            return conflict_error("REPORT_REVISION_CONFLICT", str(exc), retryable=True)
        if isinstance(exc, ReportIdempotencyReuse):
            return conflict_error("REPORT_IDEMPOTENCY_KEY_REUSE", str(exc))
        if isinstance(exc, ReportAuthorizationError):
            return authorization_error(str(exc), str(exc))
        if isinstance(exc, (ReportPersistenceError, ReportDatasetError)):
            return validation_error(str(exc), str(exc))
        if isinstance(exc, ValueError):
            code = str(exc) or type(exc).__name__
            if code.endswith("_ALREADY_EXISTS"):
                return conflict_error(code, code)
            return validation_error(code, code)
        return validation_error(type(exc).__name__, str(exc))


__all__ = [
    "AuthoritativeReportDataset",
    "ReportApplicationService",
    "ReportAuthorizationError",
    "ReportDatasetError",
    "ReportDatasetSource",
]
