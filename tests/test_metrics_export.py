from __future__ import annotations

import json

import pytest

from construction_pm.http.operational import (
    HEALTH_LIVE_PATH,
    METRICS_PATH,
    OperationalMiddleware,
)
from construction_pm.metrics_export import (
    CONTENT_TYPE,
    DeterministicPrometheusExporter,
    MetricsExportError,
    MetricsExportService,
    MetricsExportSettings,
    MetricsExportState,
    format_number,
)
from construction_pm.observability import ObservabilityError, OperationalMetrics

TOKEN = "scrape-token-0123456789"


def _app(environ, start_response):
    start_response("200 OK", [("Content-Type", "text/plain")])
    return [b"ok"]


def _settings(**overrides: object) -> MetricsExportSettings:
    values: dict[str, object] = {"enabled": True, "token": TOKEN}
    values.update(overrides)
    return MetricsExportSettings(**values)  # type: ignore[arg-type]


def _request(app, method: str, path: str, authorization: str | None = None):
    captured: dict[str, object] = {}

    def start_response(status, headers) -> None:
        captured["status"] = status
        captured["headers"] = dict(headers)

    environ: dict[str, object] = {"REQUEST_METHOD": method, "PATH_INFO": path}
    if authorization is not None:
        environ["HTTP_AUTHORIZATION"] = authorization
    body = b"".join(app(environ, start_response))
    return captured, body


def _service(
    metrics: OperationalMetrics | None = None, **settings_overrides: object
) -> MetricsExportService:
    return MetricsExportService(
        metrics, settings=_settings(**settings_overrides)
    )


# Settings -----------------------------------------------------------------


def test_settings_default_to_disabled() -> None:
    assert MetricsExportSettings().state is MetricsExportState.DISABLED
    assert MetricsExportSettings.from_environment({}).state is MetricsExportState.DISABLED
    assert (
        MetricsExportSettings.from_environment(
            {"CONSTRUCTION_PM_METRICS_EXPORT_ENABLED": "false"}
        ).state
        is MetricsExportState.DISABLED
    )


def test_settings_enabled_without_token_is_unavailable() -> None:
    settings = MetricsExportSettings.from_environment(
        {"CONSTRUCTION_PM_METRICS_EXPORT_ENABLED": "true"}
    )
    assert settings.state is MetricsExportState.UNAVAILABLE
    assert settings.error == "METRICS_EXPORT_TOKEN_MISSING"


def test_settings_reject_weak_tokens_without_echoing_them() -> None:
    for token in ("short", " token with spaces ", "x" * 513):
        settings = MetricsExportSettings.from_environment(
            {
                "CONSTRUCTION_PM_METRICS_EXPORT_ENABLED": "on",
                "CONSTRUCTION_PM_METRICS_EXPORT_TOKEN": token,
            }
        )
        assert settings.state is MetricsExportState.UNAVAILABLE
        assert settings.error == "METRICS_EXPORT_TOKEN_INVALID"
        assert token not in repr(settings)


def test_settings_parse_valid_token_and_bounds() -> None:
    settings = MetricsExportSettings.from_environment(
        {
            "CONSTRUCTION_PM_METRICS_EXPORT_ENABLED": "yes",
            "CONSTRUCTION_PM_METRICS_EXPORT_TOKEN": TOKEN,
            "CONSTRUCTION_PM_METRICS_EXPORT_MAX_BYTES": "4096",
            "CONSTRUCTION_PM_METRICS_EXPORT_MAX_SERIES": "10",
        }
    )
    assert settings.state is MetricsExportState.CONFIGURED
    assert settings.max_bytes == 4096
    assert settings.max_series == 10
    assert settings.token == TOKEN


def test_settings_reject_invalid_numbers_and_flags() -> None:
    base = {
        "CONSTRUCTION_PM_METRICS_EXPORT_ENABLED": "true",
        "CONSTRUCTION_PM_METRICS_EXPORT_TOKEN": TOKEN,
    }
    assert (
        MetricsExportSettings.from_environment(
            {**base, "CONSTRUCTION_PM_METRICS_EXPORT_MAX_BYTES": "0"}
        ).error
        == "METRICS_EXPORT_MAX_BYTES_INVALID"
    )
    assert (
        MetricsExportSettings.from_environment(
            {**base, "CONSTRUCTION_PM_METRICS_EXPORT_MAX_BYTES": "lots"}
        ).error
        == "METRICS_EXPORT_MAX_BYTES_INVALID"
    )
    assert (
        MetricsExportSettings.from_environment(
            {**base, "CONSTRUCTION_PM_METRICS_EXPORT_MAX_SERIES": "999999999"}
        ).error
        == "METRICS_EXPORT_MAX_SERIES_INVALID"
    )
    assert (
        MetricsExportSettings.from_environment(
            {"CONSTRUCTION_PM_METRICS_EXPORT_ENABLED": "sometimes"}
        ).error
        == "METRICS_EXPORT_ENABLED_INVALID"
    )


# Exporter -----------------------------------------------------------------


def test_exporter_renders_deterministic_sorted_text() -> None:
    metrics = OperationalMetrics()
    metrics.increment(
        "document_uploads_total",
        labels={
            "content_type": "application/pdf",
            "scan_status": "clean",
            "replay": "false",
        },
    )
    metrics.observe("http_request_duration_ms", 12.5, labels={"route": "http"})
    metrics.observe("http_request_duration_ms", 17.5, labels={"route": "http"})
    exporter = DeterministicPrometheusExporter()
    first = exporter.render(metrics.snapshot())
    second = exporter.render(metrics.snapshot())
    assert first == second
    assert first.splitlines() == [
        'document_uploads_total{content_type="application/pdf",replay="false",scan_status="clean"} 1',
        'http_request_duration_ms_count{route="http"} 2',
        'http_request_duration_ms_sum{route="http"} 30',
        'http_request_duration_ms_min{route="http"} 12.5',
        'http_request_duration_ms_max{route="http"} 17.5',
        'http_request_duration_ms_mean{route="http"} 15',
    ]
    assert first.endswith("\n")


def test_exporter_escapes_label_values() -> None:
    exporter = DeterministicPrometheusExporter()
    body = exporter.render(
        {
            "counters": [
                {
                    "name": "custom_total",
                    "labels": {"route": 'a"b\\c'},
                    "value": 3,
                }
            ],
            "observations": [],
        }
    )
    assert body == 'custom_total{route="a\\"b\\\\c"} 3\n'


def test_exporter_rejects_non_finite_and_malformed_snapshots() -> None:
    exporter = DeterministicPrometheusExporter()
    with pytest.raises(MetricsExportError, match="SNAPSHOT_INVALID"):
        exporter.render(
            {
                "counters": [
                    {"name": "custom_total", "labels": {}, "value": True}
                ],
                "observations": [],
            }
        )
    with pytest.raises(MetricsExportError, match="SNAPSHOT_INVALID"):
        exporter.render(
            {
                "counters": [],
                "observations": [
                    {
                        "name": "duration_ms",
                        "labels": {},
                        "count": 1,
                        "sum": float("nan"),
                        "min": 1.0,
                        "max": 1.0,
                        "mean": 1.0,
                    }
                ],
            }
        )
    with pytest.raises(MetricsExportError, match="SNAPSHOT_INVALID"):
        exporter.render(
            {
                "counters": [
                    {"name": "Bad-Name", "labels": {}, "value": 1}
                ],
                "observations": [],
            }
        )
    with pytest.raises(MetricsExportError, match="SNAPSHOT_INVALID"):
        exporter.render(
            {
                "counters": [
                    {"name": "custom_total", "labels": {"bad key": "x"}, "value": 1}
                ],
                "observations": [],
            }
        )


def test_exporter_requires_sum_but_derives_it_from_mean() -> None:
    exporter = DeterministicPrometheusExporter()
    body = exporter.render(
        {
            "counters": [],
            "observations": [
                {
                    "name": "duration_ms",
                    "labels": {},
                    "count": 4,
                    "min": 1.0,
                    "max": 3.0,
                    "mean": 2.0,
                }
            ],
        }
    )
    assert "duration_ms_sum 8\n" in body


def test_exporter_enforces_output_byte_limit() -> None:
    exporter = DeterministicPrometheusExporter(max_bytes=10)
    snapshot = {
        "counters": [{"name": "custom_total", "labels": {}, "value": 1}],
        "observations": [],
    }
    with pytest.raises(MetricsExportError, match="OUTPUT_LIMIT_EXCEEDED"):
        exporter.render(snapshot)


def test_format_number_is_stable() -> None:
    assert format_number(3) == "3"
    assert format_number(3.0) == "3"
    assert format_number(3.25) == "3.25"
    with pytest.raises(MetricsExportError, match="NOT_FINITE"):
        format_number(float("inf"))


def test_registry_rejects_non_finite_observations() -> None:
    metrics = OperationalMetrics()
    for value in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ObservabilityError, match="INVALID_METRIC_OBSERVATION"):
            metrics.observe("duration_ms", value)


def test_registry_snapshot_includes_observation_sum() -> None:
    metrics = OperationalMetrics()
    metrics.observe("duration_ms", 2.0)
    metrics.observe("duration_ms", 4.0)
    assert metrics.snapshot()["observations"][0]["sum"] == 6.0


# Service ------------------------------------------------------------------


def test_service_state_matrix() -> None:
    assert (
        MetricsExportService(OperationalMetrics()).state is MetricsExportState.DISABLED
    )
    assert (
        _service(None).state is MetricsExportState.UNAVAILABLE
    )
    assert (
        MetricsExportService(
            OperationalMetrics(),
            settings=MetricsExportSettings(enabled=True, error="METRICS_EXPORT_TOKEN_MISSING"),
        ).state
        is MetricsExportState.UNAVAILABLE
    )
    assert _service(OperationalMetrics()).state is MetricsExportState.CONFIGURED


def test_service_authorizes_only_matching_bearer_token() -> None:
    service = _service(OperationalMetrics())
    assert service.authorized(f"Bearer {TOKEN}")
    assert service.authorized(f"bearer {TOKEN}")
    assert not service.authorized(None)
    assert not service.authorized("")
    assert not service.authorized(TOKEN)
    assert not service.authorized("Bearer wrong-token-0123456789")
    assert not service.authorized("Basic " + TOKEN)


def test_service_scrape_isolates_exporter_failures() -> None:
    class Exploding:
        def render(self, snapshot):
            raise RuntimeError("secret-token-leak " + TOKEN)

    result = MetricsExportService(
        OperationalMetrics(), settings=_settings(), exporter=Exploding()
    ).scrape()
    assert result.state is MetricsExportState.UNAVAILABLE
    assert result.error == "RuntimeError"
    assert TOKEN not in (result.error or "")


def test_service_scrape_reports_missing_registry_as_unavailable() -> None:
    result = _service(None).scrape()
    assert result.state is MetricsExportState.UNAVAILABLE
    assert result.body == ""


# HTTP endpoint ------------------------------------------------------------


def test_metrics_endpoint_is_404_when_export_disabled() -> None:
    service = MetricsExportService(
        OperationalMetrics(), settings=MetricsExportSettings()
    )
    app = OperationalMiddleware(_app, metrics_export=service)
    captured, body = _request(app, "GET", METRICS_PATH, f"Bearer {TOKEN}")
    assert captured["status"].startswith("404")
    assert json.loads(body) == {"status": "not_found"}


def test_metrics_endpoint_is_absent_when_not_configured() -> None:
    app = OperationalMiddleware(_app)
    captured, body = _request(app, "GET", METRICS_PATH)
    assert captured["status"].startswith("200")
    assert body == b"ok"


def test_metrics_endpoint_requires_bearer_token() -> None:
    service = _service(OperationalMetrics())
    app = OperationalMiddleware(_app, metrics_export=service)
    for authorization in (None, "", f"Bearer wrong-token-0123456789"):
        captured, body = _request(app, "GET", METRICS_PATH, authorization)
        assert captured["status"].startswith("401")
        assert captured["headers"]["WWW-Authenticate"] == 'Bearer realm="metrics"'
        payload = json.loads(body)
        assert payload["code"] == "METRICS_EXPORT_UNAUTHORIZED"
        assert TOKEN not in body.decode("utf-8")


def test_metrics_endpoint_serves_bounded_text() -> None:
    metrics = OperationalMetrics()
    metrics.increment(
        "http_requests_total",
        labels={"route": "document_upload", "method": "POST", "status_class": "2xx"},
    )
    service = _service(metrics)
    app = OperationalMiddleware(_app, metrics_export=service)
    captured, body = _request(app, "GET", METRICS_PATH, f"Bearer {TOKEN}")
    assert captured["status"].startswith("200")
    assert captured["headers"]["Content-Type"] == CONTENT_TYPE
    assert captured["headers"]["Cache-Control"] == "no-store"
    text = body.decode("utf-8")
    assert (
        'http_requests_total{method="POST",route="document_upload",status_class="2xx"} 1\n'
        == text
    )
    assert str(len(body)) == captured["headers"]["Content-Length"]

    head, head_body = _request(app, "HEAD", METRICS_PATH, f"Bearer {TOKEN}")
    assert head["status"].startswith("200")
    assert head_body == b""
    assert head["headers"]["Content-Length"] == str(len(body))


def test_metrics_endpoint_is_503_when_registry_missing_and_business_continues() -> None:
    service = _service(None)
    app = OperationalMiddleware(_app, metrics_export=service)
    captured, body = _request(app, "GET", METRICS_PATH, f"Bearer {TOKEN}")
    assert captured["status"].startswith("503")
    assert json.loads(body)["code"] == "METRICS_EXPORT_UNAVAILABLE"
    business, business_body = _request(app, "GET", "/api/projects/P-1/tracking/read")
    assert business["status"].startswith("200")
    assert business_body == b"ok"
    health, _ = _request(app, "GET", HEALTH_LIVE_PATH)
    assert health["status"].startswith("200")


def test_metrics_endpoint_isolates_render_failure_from_business_requests() -> None:
    class Exploding:
        def render(self, snapshot):
            raise RuntimeError("boom")

    metrics = OperationalMetrics()
    service = MetricsExportService(
        metrics, settings=_settings(), exporter=Exploding()
    )
    app = OperationalMiddleware(_app, metrics_export=service, metrics=metrics)
    captured, body = _request(app, "GET", METRICS_PATH, f"Bearer {TOKEN}")
    assert captured["status"].startswith("503")
    assert json.loads(body)["code"] == "RuntimeError"
    business, business_body = _request(app, "GET", "/api/projects/P-1/tracking/read")
    assert business["status"].startswith("200")
    assert business_body == b"ok"
    assert metrics.snapshot()["counters"][0]["labels"]["route"] == "http"


def test_metrics_endpoint_enforces_output_limit() -> None:
    metrics = OperationalMetrics()
    metrics.increment("http_requests_total", labels={"route": "http"})
    service = _service(metrics, max_bytes=8)
    app = OperationalMiddleware(_app, metrics_export=service)
    captured, body = _request(app, "GET", METRICS_PATH, f"Bearer {TOKEN}")
    assert captured["status"].startswith("503")
    assert json.loads(body)["code"] == "METRICS_EXPORT_OUTPUT_LIMIT_EXCEEDED"
    assert len(body) < 200


def test_metrics_endpoint_rejects_unsupported_methods() -> None:
    service = _service(OperationalMetrics())
    app = OperationalMiddleware(_app, metrics_export=service)
    captured, body = _request(app, "POST", METRICS_PATH, f"Bearer {TOKEN}")
    assert captured["status"].startswith("405")
    assert captured["headers"]["Allow"] == "GET, HEAD"
    assert json.loads(body)["status"] == "method_not_allowed"


def test_scrape_and_health_are_not_instrumented() -> None:
    metrics = OperationalMetrics()
    app = OperationalMiddleware(
        _app, metrics=metrics, metrics_export=_service(metrics)
    )
    _request(app, "GET", METRICS_PATH, f"Bearer {TOKEN}")
    _request(app, "GET", HEALTH_LIVE_PATH)
    assert metrics.snapshot() == {"counters": [], "observations": []}


def test_export_covers_domain_metric_names_without_sensitive_labels() -> None:
    metrics = OperationalMetrics()
    metrics.increment(
        "document_uploads_total",
        labels={"content_type": "application/pdf", "scan_status": "clean", "replay": "false"},
    )
    metrics.increment("document_ocr_jobs_total", labels={"status": "succeeded"})
    metrics.increment(
        "exchange_runs_total",
        labels={"operation": "import", "dataset": "activities", "status": "applied"},
    )
    metrics.increment("report_runs_total", labels={"source": "interactive", "status": "succeeded"})
    metrics.increment("report_schedule_runs_total", labels={"state": "succeeded"})
    metrics.increment(
        "http_requests_total",
        labels={"route": "http", "method": "GET", "status_class": "2xx"},
    )
    text = _service(metrics).scrape().body
    for name in (
        "document_uploads_total",
        "document_ocr_jobs_total",
        "exchange_runs_total",
        "report_runs_total",
        "report_schedule_runs_total",
        "http_requests_total",
    ):
        assert name in text
    for forbidden in ("tenant", "user_id", "token", "document_name", "/api/projects"):
        assert forbidden not in text


def test_scrape_fails_closed_when_series_limit_is_exceeded() -> None:
    metrics = OperationalMetrics()
    metrics.increment("custom_total", labels={"route": "a"})
    metrics.observe("duration_ms", 1.0, labels={"route": "a"})
    service = _service(metrics, max_series=1)
    result = service.scrape()
    assert result.state is MetricsExportState.UNAVAILABLE
    assert result.error == "METRICS_EXPORT_SERIES_LIMIT_EXCEEDED"
    assert result.body == ""

    one_series = OperationalMetrics()
    one_series.increment("custom_total", labels={"route": "a"})
    allowed = _service(one_series, max_series=1).scrape()
    assert allowed.ok is True
