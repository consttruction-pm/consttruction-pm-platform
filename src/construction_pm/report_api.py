"""Versioned transport adapter for the project report register."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .api_errors import APIError
from .application.authorization import AuthorizationContext
from .report_application import ReportApplicationService
from .report_export import REPORT_EXPORT_FORMATS, ReportExportDocument
from .report_persistence import (
    ReportAuditEvent,
    ReportDefinition,
    ReportRun,
    StoredReportDefinition,
    report_catalogue,
)

REPORT_API_VERSION = "p6-report-api.v1"


@dataclass(frozen=True)
class ReportAPI:
    """Thin DTO boundary over the report application service."""

    service: ReportApplicationService

    def catalogue(self) -> dict[str, Any]:
        return {
            "contract_version": REPORT_API_VERSION,
            "subjects": report_catalogue(),
            "export_formats": list(REPORT_EXPORT_FORMATS),
        }

    def list_definitions(
        self,
        *,
        tenant_id: str,
        project_id: str,
        context: AuthorizationContext,
        subject: str | None = None,
        search: str | None = None,
    ) -> dict[str, Any]:
        try:
            return {
                "contract_version": REPORT_API_VERSION,
                "catalogue": report_catalogue(),
                "reports": [
                    _definition(item)
                    for item in self.service.list_definitions(
                        tenant_id=tenant_id,
                        project_id=project_id,
                        context=context,
                        subject=subject,
                        search=search,
                    )
                ],
            }
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def read_definition(
        self,
        *,
        tenant_id: str,
        project_id: str,
        report_id: str,
        context: AuthorizationContext,
    ) -> dict[str, Any]:
        try:
            return _definition(
                self.service.read_definition(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    report_id=report_id,
                    context=context,
                )
            )
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def definition_history(
        self,
        *,
        tenant_id: str,
        project_id: str,
        report_id: str,
        context: AuthorizationContext,
    ) -> dict[str, Any]:
        try:
            return {
                "contract_version": REPORT_API_VERSION,
                "events": [
                    _event(item)
                    for item in self.service.definition_history(
                        tenant_id=tenant_id,
                        project_id=project_id,
                        report_id=report_id,
                        context=context,
                    )
                ],
            }
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def create_definition(
        self,
        definition: ReportDefinition,
        *,
        idempotency_key: str,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> dict[str, Any]:
        try:
            return _definition(
                self.service.create_definition(
                    definition,
                    idempotency_key=idempotency_key,
                    context=context,
                    actor_id=actor_id,
                    occurred_at=occurred_at,
                )
            )
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def update_definition(
        self,
        definition: ReportDefinition,
        *,
        expected_revision: int,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
        reason: str = "",
    ) -> dict[str, Any]:
        try:
            return _definition(
                self.service.update_definition(
                    definition,
                    expected_revision=expected_revision,
                    context=context,
                    actor_id=actor_id,
                    occurred_at=occurred_at,
                    reason=reason,
                )
            )
        except Exception as exc:
            return _error(self.service.error_dto(exc))

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
    ) -> dict[str, Any]:
        try:
            self.service.delete_definition(
                tenant_id=tenant_id,
                project_id=project_id,
                report_id=report_id,
                expected_revision=expected_revision,
                context=context,
                actor_id=actor_id,
                occurred_at=occurred_at,
                reason=reason,
            )
            return {"contract_version": REPORT_API_VERSION, "deleted": True}
        except Exception as exc:
            return _error(self.service.error_dto(exc))

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
    ) -> dict[str, Any]:
        try:
            return _run(
                self.service.run_report(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    project_revision=project_revision,
                    report_id=report_id,
                    context=context,
                    actor_id=actor_id,
                    occurred_at=occurred_at,
                )
            )
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def list_runs(
        self,
        *,
        tenant_id: str,
        project_id: str,
        report_id: str,
        context: AuthorizationContext,
    ) -> dict[str, Any]:
        try:
            runs = self.service.list_runs(
                tenant_id=tenant_id,
                project_id=project_id,
                report_id=report_id,
                context=context,
            )
            return {
                "contract_version": REPORT_API_VERSION,
                "report_id": report_id,
                "runs": [_run_summary(item) for item in runs],
            }
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def read_run(
        self,
        *,
        tenant_id: str,
        project_id: str,
        report_id: str,
        run_id: str,
        context: AuthorizationContext,
    ) -> dict[str, Any]:
        try:
            return _run(
                self.service.read_run(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    report_id=report_id,
                    run_id=run_id,
                    context=context,
                )
            )
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def export_run(
        self,
        *,
        tenant_id: str,
        project_id: str,
        report_id: str,
        run_id: str,
        export_format: str,
        context: AuthorizationContext,
    ) -> ReportExportDocument | dict[str, Any]:
        try:
            return self.service.export_run(
                tenant_id=tenant_id,
                project_id=project_id,
                report_id=report_id,
                run_id=run_id,
                export_format=export_format,
                context=context,
            )
        except Exception as exc:
            return _error(self.service.error_dto(exc))


def _definition(stored: StoredReportDefinition) -> dict[str, Any]:
    return {"contract_version": REPORT_API_VERSION, **stored.as_dict()}


def _run(run: ReportRun) -> dict[str, Any]:
    return {"contract_version": REPORT_API_VERSION, **run.as_dict()}


def _run_summary(run: ReportRun) -> dict[str, Any]:
    return {
        "contract_version": REPORT_API_VERSION,
        "run_id": run.run_id,
        "report_id": run.report_id,
        "report_revision": run.report_revision,
        "project_revision": run.project_revision,
        "subject": run.subject,
        "columns": list(run.columns),
        "row_count": len(run.rows),
        "generated_at": run.generated_at.isoformat(),
        "generated_by": run.generated_by,
    }


def _event(event: ReportAuditEvent) -> dict[str, Any]:
    return {"contract_version": REPORT_API_VERSION, **event.as_dict()}


def _error(error: APIError) -> dict[str, Any]:
    error.validate()
    return {
        "contract_version": REPORT_API_VERSION,
        "category": error.category.value,
        "code": error.code,
        "message": error.message,
        "retryable": error.retryable,
    }


__all__ = ["REPORT_API_VERSION", "ReportAPI"]
