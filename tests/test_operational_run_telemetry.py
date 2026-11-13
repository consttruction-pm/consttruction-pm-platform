from __future__ import annotations

import io
import json
import sqlite3
from datetime import datetime, timezone

from construction_pm.application.authorization import (
    AuthorizationContext,
    Permission,
    RoleBasedAuthorizationPolicy,
    default_project_policy,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.exchange_application import ExchangeService
from construction_pm.exchange_persistence import SQLiteExchangeStore
from construction_pm.observability import OperationalMetrics
from construction_pm.p6_resource_master_repository import SQLiteP6ResourceRepository
from construction_pm.production_readiness import StructuredEventLogger
from construction_pm.report_application import ReportApplicationService
from construction_pm.report_persistence import ReportDefinition, SQLiteReportStore

NOW = datetime(2026, 11, 13, 9, 0, tzinfo=timezone.utc)


def _logger(stream: io.StringIO) -> StructuredEventLogger:
    return StructuredEventLogger(stream=stream, clock=lambda: NOW)


class _Empty:
    def list(self, *args, **kwargs):
        return ()


def test_exchange_records_preview_export_and_apply_telemetry(tmp_path) -> None:
    connection = sqlite3.connect(tmp_path / "exchange.sqlite3")
    store = SQLiteExchangeStore(connection)
    store.initialize()
    resources = SQLiteP6ResourceRepository(connection)
    metrics = OperationalMetrics()
    stream = io.StringIO()
    service = ExchangeService(
        store=store,
        activity_repository=_Empty(),
        resource_repository=resources,
        resource_api=object(),
        risk_store=object(),
        authorization_policy=default_project_policy(),
        transaction_manager=SQLiteTransactionManager(connection),
        metrics=metrics,
        logger=_logger(stream),
    )
    context = AuthorizationContext("t1", "p1", "u1", frozenset({"project_admin"}))

    invalid = service.preview_import(
        scope=BackendScope("t1", "p1", 1),
        dataset="resources",
        content="",
        context=context,
        occurred_at=NOW,
    )
    assert invalid["valid"] is False
    exported = service.export(
        scope=BackendScope("t1", "p1", 1),
        dataset="resources",
        context=context,
        generated_at=NOW,
    )
    assert exported["row_count"] == 0

    records = [json.loads(line) for line in stream.getvalue().splitlines()]
    events = {record["event"]: record for record in records}
    assert events["exchange.run"]["operation"] in {"preview", "export"}
    snapshot = metrics.snapshot()
    labels = {
        (item["labels"]["operation"], item["labels"]["status"])
        for item in snapshot["counters"]
        if item["name"] == "exchange_runs_total"
    }
    assert ("preview", "failed") in labels
    assert ("export", "succeeded") in labels
    assert "CSV" not in stream.getvalue()
    connection.close()


class _Dataset:
    def build(self, scope, subject, columns, parameters=None):
        return ({"activity_id": "A1", "name": "Dig", "status": "Completed"},)


def test_report_run_records_interactive_and_scheduled_telemetry(tmp_path) -> None:
    connection = sqlite3.connect(tmp_path / "reports.sqlite3")
    reports = SQLiteReportStore(connection)
    reports.initialize()
    metrics = OperationalMetrics()
    stream = io.StringIO()
    policy = RoleBasedAuthorizationPolicy(
        {"planner": frozenset({Permission.PROJECT_READ, Permission.PROJECT_WRITE})}
    )
    application = ReportApplicationService(
        reports,
        _Dataset(),
        policy,
        SQLiteTransactionManager(connection),
        metrics=metrics,
        logger=_logger(stream),
    )
    reports.create_definition(
        ReportDefinition(
            tenant_id="t1",
            project_id="p1",
            report_id="RPT-1",
            name="Activities",
            subject="activities",
            columns=("activity_id", "name", "status"),
        ),
        idempotency_key="definition-key",
        actor_id="u1",
        occurred_at=NOW,
    )
    context = AuthorizationContext("t1", "p1", "u1", frozenset({"planner"}))
    application.run_report(
        tenant_id="t1",
        project_id="p1",
        project_revision=1,
        report_id="RPT-1",
        context=context,
        actor_id="u1",
        occurred_at=NOW,
    )
    application.run_scheduled(
        tenant_id="t1",
        project_id="p1",
        project_revision=1,
        report_id="RPT-1",
        parameters=None,
        actor_id="scheduler",
        occurred_at=NOW,
        run_id="RUN-SCH-1",
    )

    snapshot = metrics.snapshot()
    sources = {
        item["labels"]["source"]
        for item in snapshot["counters"]
        if item["name"] == "report_runs_total"
    }
    assert sources == {"interactive", "scheduled"}
    records = [json.loads(line) for line in stream.getvalue().splitlines()]
    events = [record for record in records if record["event"] == "report.run.completed"]
    assert {event["source"] for event in events} == {"interactive", "scheduled"}
    assert all("rows" not in event for event in events)
    connection.close()
