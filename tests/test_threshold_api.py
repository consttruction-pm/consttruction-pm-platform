from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    default_project_policy,
)
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.threshold_api import THRESHOLD_API_VERSION, ThresholdAPI
from construction_pm.threshold_application import ThresholdApplicationService
from construction_pm.threshold_persistence import SQLiteThresholdStore, Threshold

NOW = datetime(2026, 11, 12, 14, 0, tzinfo=timezone.utc)
WRITER_CALLS: list[str] = []


def context(role: str = "planner", *, user: str = "u-1") -> AuthorizationContext:
    return AuthorizationContext("T-1", "P-1", user, frozenset({role}))


def threshold(**changes: object) -> Threshold:
    values = {
        "tenant_id": "T-1",
        "project_id": "P-1",
        "threshold_id": "TH-1",
        "name": "Open issue watch",
        "monitoring_subject": "quality",
        "parameter": "open_issue_count",
        "currency": None,
        "lower_threshold": None,
        "upper_threshold": Decimal("5"),
        "warning_level": Decimal("1"),
        "issue_level": Decimal("3"),
        "responsible_manager": "u-manager",
        "status": "active",
    }
    values.update(changes)
    return Threshold(**values)


class Metrics:
    def __init__(self, *values: str) -> None:
        self.values = [Decimal(value) for value in values]

    def observe(self, **_kwargs: object) -> Decimal:
        return self.values.pop(0)


def write_issue(issue, *, context, occurred_at) -> str:
    WRITER_CALLS.append(issue.issue_id)
    return issue.issue_id


@pytest.fixture()
def api() -> ThresholdAPI:
    connection = sqlite3.connect(":memory:")
    store = SQLiteThresholdStore(connection)
    store.initialize()
    service = ThresholdApplicationService(
        store,
        default_project_policy(),
        SQLiteTransactionManager(connection),
        Metrics("6", "8"),
        write_issue,
    )
    return ThresholdAPI(service)


def test_api_returns_flat_versioned_threshold_and_error_dtos(api) -> None:
    created = api.create_threshold(
        threshold(),
        idempotency_key="k-1",
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    assert created["contract_version"] == THRESHOLD_API_VERSION
    assert created["threshold_id"] == "TH-1"
    assert created["upper_threshold"] == "5"
    assert created["warning_level"] == "1" and created["issue_level"] == "3"
    assert created["currency"] is None and created["revision"] == 1

    listed = api.list_thresholds(
        tenant_id="T-1",
        project_id="P-1",
        context=context("viewer", user="v-1"),
        parameter="open_issue_count",
    )
    assert [item["threshold_id"] for item in listed["thresholds"]] == ["TH-1"]

    read = api.read_threshold(
        tenant_id="T-1",
        project_id="P-1",
        threshold_id="TH-1",
        context=context(),
    )
    assert read["name"] == "Open issue watch"

    missing = api.read_threshold(
        tenant_id="T-1",
        project_id="P-1",
        threshold_id="TH-404",
        context=context(),
    )
    assert missing["category"] == "validation" and missing["code"] == "THRESHOLD_NOT_FOUND"
    assert missing["contract_version"] == THRESHOLD_API_VERSION

    denied = api.create_threshold(
        threshold(threshold_id="TH-2"),
        idempotency_key="k-2",
        context=context("viewer", user="v-1"),
        actor_id="v-1",
        occurred_at=NOW,
    )
    assert denied["category"] == "authorization"


def test_api_monitor_returns_run_and_generated_issue(api) -> None:
    api.create_threshold(
        threshold(),
        idempotency_key="k-1",
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    WRITER_CALLS.clear()
    first = api.monitor(
        tenant_id="T-1",
        project_id="P-1",
        project_revision=4,
        threshold_id="TH-1",
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    assert first["run"]["level"] == "warning" and first["run"]["observed_value"] == "6"
    assert first["run"]["generated_issue_id"] is None
    assert WRITER_CALLS == []

    second = api.monitor(
        tenant_id="T-1",
        project_id="P-1",
        project_revision=4,
        threshold_id="TH-1",
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    assert second["run"]["level"] == "issue"
    assert second["run"]["generated_issue_id"] == "THR-TH-1-R2"
    assert WRITER_CALLS == ["THR-TH-1-R2"]

    runs = api.runs(
        tenant_id="T-1",
        project_id="P-1",
        threshold_id="TH-1",
        context=context(),
    )
    assert [run["level"] for run in runs["runs"]] == ["warning", "issue"]

    history = api.threshold_history(
        tenant_id="T-1",
        project_id="P-1",
        threshold_id="TH-1",
        context=context(),
    )
    assert [event["event_type"] for event in history["events"]] == ["created"]


def test_api_update_delete_and_stale_conflict(api) -> None:
    api.create_threshold(
        threshold(),
        idempotency_key="k-1",
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    updated = api.update_threshold(
        threshold(name="Open issue watch revised"),
        expected_revision=1,
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    assert updated["revision"] == 2
    stale = api.update_threshold(
        threshold(name="Stale"),
        expected_revision=1,
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    assert stale["category"] == "conflict" and stale["retryable"] is True
    deleted = api.delete_threshold(
        tenant_id="T-1",
        project_id="P-1",
        threshold_id="TH-1",
        expected_revision=2,
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
        reason="superseded",
    )
    assert deleted["deleted"] is True
    missing = api.read_threshold(
        tenant_id="T-1",
        project_id="P-1",
        threshold_id="TH-1",
        context=context(),
    )
    assert missing["code"] == "THRESHOLD_NOT_FOUND"
