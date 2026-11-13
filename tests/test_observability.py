from __future__ import annotations

import io
import json
from datetime import datetime, timezone

import pytest

from construction_pm.http.operational import OperationalMiddleware, route_template
from construction_pm.observability import (
    ObservabilityError,
    OperationalMetrics,
    current_correlation_id,
    reset_correlation_id,
    set_correlation_id,
)
from construction_pm.production_readiness import StructuredEventLogger


def _app(environ, start_response):
    start_response("200 OK", [("Content-Type", "text/plain")])
    return [b"ok"]


def _request(app, method: str, path: str):
    captured: dict[str, object] = {}

    def start_response(status, headers) -> None:
        captured["status"] = status
        captured["headers"] = dict(headers)

    body = b"".join(app({"REQUEST_METHOD": method, "PATH_INFO": path}, start_response))
    return captured, body


def test_metrics_count_and_snapshot() -> None:
    metrics = OperationalMetrics()
    metrics.increment("http_requests_total", labels={"route": "http", "status_class": "2xx"})
    metrics.increment("http_requests_total", labels={"route": "http", "status_class": "2xx"})
    metrics.observe("http_request_duration_ms", 12.5, labels={"route": "http"})
    metrics.observe("http_request_duration_ms", 17.5, labels={"route": "http"})
    snapshot = metrics.snapshot()
    assert snapshot["counters"] == [
        {
            "name": "http_requests_total",
            "labels": {"route": "http", "status_class": "2xx"},
            "value": 2,
        }
    ]
    observation = snapshot["observations"][0]
    assert observation["count"] == 2
    assert observation["min"] == 12.5
    assert observation["max"] == 17.5
    assert observation["mean"] == 15.0


def test_metrics_validate_names_labels_and_bounds() -> None:
    metrics = OperationalMetrics(max_series=1)
    with pytest.raises(ObservabilityError, match="INVALID_METRIC_NAME"):
        metrics.increment("Bad-Name")
    with pytest.raises(ObservabilityError, match="INVALID_METRIC_LABEL_NAME"):
        metrics.increment("valid_name", labels={"Bad-Key": "x"})
    with pytest.raises(ObservabilityError, match="INVALID_METRIC_LABEL_VALUE"):
        metrics.increment("valid_name", labels={"route": "value with spaces"})
    with pytest.raises(ObservabilityError, match="INVALID_METRIC_OBSERVATION"):
        metrics.observe("valid_name", -1)
    metrics.increment("valid_name", labels={"route": "http"})
    with pytest.raises(ObservabilityError, match="METRIC_SERIES_LIMIT_REACHED"):
        metrics.increment("valid_name", labels={"route": "document"})


def test_observation_series_are_bounded() -> None:
    metrics = OperationalMetrics(max_series=1)
    metrics.observe("duration_ms", 1.0, labels={"route": "http"})
    metrics.observe("duration_ms", 2.0, labels={"route": "http"})
    with pytest.raises(ObservabilityError, match="METRIC_SERIES_LIMIT_REACHED"):
        metrics.observe("duration_ms", 3.0, labels={"route": "document"})


def test_observation_samples_are_bounded() -> None:
    metrics = OperationalMetrics()
    for value in range(10):
        metrics.observe("duration_ms", value, max_samples=3)
    observation = metrics.snapshot()["observations"][0]
    assert observation["count"] == 3
    assert observation["min"] == 7
    assert observation["max"] == 9


def test_route_template_replaces_identifiers() -> None:
    assert route_template("POST", "/api/projects/P-1/documents/D-1/content") == "document_upload"
    assert route_template("POST", "/api/projects/P-1/exchange/import/apply") == "exchange_import"
    assert route_template("GET", "/api/projects/P-1/exchange/export") == "exchange_export"
    assert route_template("POST", "/api/projects/P-1/reports/R-1/runs") == "report_run"
    assert route_template("GET", "/api/projects/P-1/reports/R-1/runs/run-1/export") == "report_export"
    assert route_template("POST", "/api/projects/P-1/reports/R-1/schedules") == "report_schedule"
    assert route_template("GET", "/api/projects/P-1/documents/D-1") == "document"
    assert route_template("GET", "/api/projects/P-1/tracking/read") == "http"


def test_middleware_metrics_use_route_templates_not_raw_paths() -> None:
    metrics = OperationalMetrics()
    app = OperationalMiddleware(_app, metrics=metrics)
    _request(app, "POST", "/api/projects/P-1/documents/D-1/content")
    snapshot = metrics.snapshot()
    counters = snapshot["counters"]
    assert counters[0]["labels"] == {
        "method": "POST",
        "route": "document_upload",
        "status_class": "2xx",
    }
    serialized = json.dumps(snapshot)
    assert "P-1" not in serialized
    assert "D-1" not in serialized
    observations = snapshot["observations"]
    assert observations[0]["labels"] == {"route": "document_upload"}


def test_correlation_context_reaches_structured_logger() -> None:
    stream = io.StringIO()
    logger = StructuredEventLogger(
        stream=stream,
        clock=lambda: datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc),
    )
    token = set_correlation_id("req-from-context")
    try:
        assert current_correlation_id() == "req-from-context"
        logger.emit("document.content.uploaded", fields={"document_id": "DOC-1"})
    finally:
        reset_correlation_id(token)
    record = json.loads(stream.getvalue())
    assert record["correlation_id"] == "req-from-context"
    assert record["document_id"] == "DOC-1"
