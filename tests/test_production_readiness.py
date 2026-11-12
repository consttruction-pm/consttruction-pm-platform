from __future__ import annotations

import io
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from construction_pm.http.operational import (
    HEALTH_LIVE_PATH,
    HEALTH_READY_PATH,
    OperationalMiddleware,
)
from construction_pm.production_readiness import (
    ProductionReadinessError,
    ProbeResult,
    ReadinessCheck,
    ReadinessService,
    ReadinessStatus,
    Requirement,
    StructuredEventLogger,
    build_readiness_service,
    normalize_correlation_id,
    redact_fields,
    validate_environment,
)

PRODUCTION_ENV = {
    "CONSTRUCTION_PM_ENVIRONMENT": "production",
    "CONSTRUCTION_PM_SERVICE_NAME": "construction-pm",
    "CONSTRUCTION_PM_DATABASE_URL": "postgresql://user:password@db.internal:5432/cubi",
    "CONSTRUCTION_PM_DOCUMENT_STORAGE": "s3",
    "CONSTRUCTION_PM_S3_ENDPOINT_URL": "https://objects.internal",
    "CONSTRUCTION_PM_S3_BUCKET": "cubi-documents",
    "CONSTRUCTION_PM_S3_REGION": "us-east-1",
    "CONSTRUCTION_PM_S3_ACCESS_KEY": "access-key-value",
    "CONSTRUCTION_PM_S3_SECRET_KEY": "secret-key-value",
    "CONSTRUCTION_PM_S3_PREFIX": "documents",
    "CONSTRUCTION_PM_S3_PATH_STYLE": "true",
    "CONSTRUCTION_PM_S3_SSE": "AES256",
    "CONSTRUCTION_PM_SCANNER": "external",
    "CONSTRUCTION_PM_SCANNER_ENDPOINT": "https://scanner.internal/scan",
    "CONSTRUCTION_PM_REQUIRE_SCANNED_CONTENT": "true",
    "CONSTRUCTION_PM_OCR": "disabled",
    "CONSTRUCTION_PM_JOB_QUEUE": "durable",
    "CONSTRUCTION_PM_RETENTION": "enabled",
    "CONSTRUCTION_PM_LOG_FORMAT": "json",
    "CONSTRUCTION_PM_LOG_LEVEL": "info",
}


def _request(app, method: str, path: str, *, headers: dict[str, str] | None = None):
    environ: dict[str, object] = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
    }
    for key, value in (headers or {}).items():
        environ["HTTP_" + key.upper().replace("-", "_")] = value
    captured: dict[str, object] = {}

    def start_response(status, response_headers) -> None:
        captured["status"] = status
        captured["headers"] = dict(response_headers)

    body = b"".join(app(environ, start_response))
    return int(str(captured["status"]).split(" ", 1)[0]), captured["headers"], body, environ


def _static_app(status: str = "200 OK", body: bytes = b"ok"):
    def app(environ, start_response):
        start_response(status, [("Content-Type", "text/plain")])
        return [body]

    return app


def _service(*checks: ReadinessCheck) -> ReadinessService:
    return ReadinessService(
        checks,
        clock=lambda: datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc),
    )


def test_production_environment_template_is_valid() -> None:
    env: dict[str, str] = {}
    for line in Path("infra/deploy/production.env.example").read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        env[key.strip()] = value.strip()

    validation = validate_environment(env)
    assert validation.valid, validation.as_dict()
    assert validation.production is True
    assert validation.errors == ()
    assert all(validation.components[name] for name in (
        "database",
        "object_storage",
        "malware_scanner",
        "job_queue",
        "retention",
        "observability",
    ))
    assert validation.components["ocr"] is False


def test_production_environment_rejects_missing_and_development_adapters() -> None:
    env = {
        "CONSTRUCTION_PM_ENVIRONMENT": "production",
        "CONSTRUCTION_PM_DATABASE_URL": "sqlite:///tmp/cubi.sqlite3",
        "CONSTRUCTION_PM_DOCUMENT_STORAGE": "local",
        "CONSTRUCTION_PM_SCANNER": "reference",
        "CONSTRUCTION_PM_JOB_QUEUE": "in_process",
        "CONSTRUCTION_PM_RETENTION": "disabled",
        "CONSTRUCTION_PM_LOG_FORMAT": "text",
    }
    validation = validate_environment(env)
    codes = {issue.code for issue in validation.errors}
    assert validation.valid is False
    assert {
        "SQLITE_FORBIDDEN_IN_PRODUCTION",
        "LOCAL_STORAGE_FORBIDDEN_IN_PRODUCTION",
        "REFERENCE_SCANNER_FORBIDDEN_IN_PRODUCTION",
        "IN_PROCESS_QUEUE_FORBIDDEN_IN_PRODUCTION",
        "RETENTION_REQUIRED_IN_PRODUCTION",
        "JSON_LOGS_REQUIRED_IN_PRODUCTION",
    } <= codes
    assert "MISSING_SCANNED_CONTENT_REQUIREMENT" in codes


def test_production_environment_requires_each_mandatory_setting() -> None:
    validation = validate_environment({"CONSTRUCTION_PM_ENVIRONMENT": "production"})
    codes = {issue.code for issue in validation.errors}
    assert {
        "MISSING_DATABASE_URL",
        "MISSING_DOCUMENT_STORAGE",
        "MISSING_SCANNER",
        "MISSING_JOB_QUEUE",
        "MISSING_RETENTION",
    } <= codes


def test_environment_report_never_contains_secret_values() -> None:
    env = dict(PRODUCTION_ENV)
    env["CONSTRUCTION_PM_S3_SECRET_KEY"] = "TOP-SECRET-VALUE"
    env["CONSTRUCTION_PM_S3_ACCESS_KEY"] = "ACCESS-VALUE"
    env["CONSTRUCTION_PM_DATABASE_URL"] = (
        "postgresql://user:DSN-PASSWORD@db.internal:5432/cubi"
    )
    validation = validate_environment(env)
    serialized = json.dumps(validation.as_dict(), sort_keys=True)
    assert "TOP-SECRET-VALUE" not in serialized
    assert "ACCESS-VALUE" not in serialized
    assert "DSN-PASSWORD" not in serialized


def test_non_production_environment_allows_local_adapters() -> None:
    validation = validate_environment(
        {
            "CONSTRUCTION_PM_ENVIRONMENT": "development",
            "CONSTRUCTION_PM_DATABASE_URL": "sqlite:///tmp/dev.sqlite3",
            "CONSTRUCTION_PM_DOCUMENT_STORAGE": "local",
        },
        production=False,
    )
    assert validation.valid
    assert validation.production is False
    assert validation.components["database"] is True
    assert validation.components["object_storage"] is True


def test_invalid_operational_values_are_errors() -> None:
    validation = validate_environment(
        {
            "CONSTRUCTION_PM_ENVIRONMENT": "production",
            "CONSTRUCTION_PM_DATABASE_URL": "mysql://host/db",
            "CONSTRUCTION_PM_DOCUMENT_STORAGE": "ftp",
            "CONSTRUCTION_PM_SCANNER": "unknown",
            "CONSTRUCTION_PM_OCR": "bogus",
            "CONSTRUCTION_PM_JOB_QUEUE": "bogus",
            "CONSTRUCTION_PM_RETENTION": "bogus",
            "CONSTRUCTION_PM_LOG_FORMAT": "xml",
            "CONSTRUCTION_PM_LOG_LEVEL": "verbose",
        },
        production=True,
    )
    codes = {issue.code for issue in validation.errors}
    assert {
        "INVALID_DATABASE_URL",
        "INVALID_DOCUMENT_STORAGE_KIND",
        "INVALID_SCANNER_KIND",
        "INVALID_OCR_KIND",
        "INVALID_JOB_QUEUE_KIND",
        "INVALID_RETENTION_KIND",
        "INVALID_LOG_FORMAT",
        "INVALID_LOG_LEVEL",
    } <= codes


def test_scanner_url_must_be_https_in_production() -> None:
    env = dict(PRODUCTION_ENV)
    env["CONSTRUCTION_PM_SCANNER_ENDPOINT"] = "http://scanner.internal/scan"
    validation = validate_environment(env)
    assert any(
        issue.code == "URL_REQUIRES_HTTPS"
        and issue.variable == "CONSTRUCTION_PM_SCANNER_ENDPOINT"
        for issue in validation.errors
    )


def test_database_variable_conflict_is_a_warning() -> None:
    env = dict(PRODUCTION_ENV)
    env["CONSTRUCTION_PM_POSTGRES_DSN"] = "postgresql://other:other@other/db"
    validation = validate_environment(env)
    assert validation.valid
    assert any(issue.code == "DATABASE_URL_CONFLICT" for issue in validation.warnings)


def test_readiness_required_failure_is_not_ready() -> None:
    service = _service(
        ReadinessCheck("configuration", Requirement.REQUIRED, lambda: True),
        ReadinessCheck("database", Requirement.REQUIRED, lambda: ProbeResult(False, "DB_DOWN")),
    )
    report = service.report()
    assert report.status is ReadinessStatus.NOT_READY
    assert report.ready is False
    assert report.as_dict()["status"] == "not_ready"


def test_readiness_optional_failure_is_degraded() -> None:
    service = _service(
        ReadinessCheck("configuration", Requirement.REQUIRED, lambda: True),
        ReadinessCheck("database", Requirement.REQUIRED, lambda: True),
        ReadinessCheck("ocr", Requirement.OPTIONAL, lambda: ProbeResult(False, "OCR_DOWN")),
    )
    report = service.report()
    assert report.status is ReadinessStatus.DEGRADED
    assert report.ready is True


def test_readiness_probe_exception_does_not_leak_message() -> None:
    def broken() -> object:
        raise RuntimeError("token=TOP-SECRET-VALUE")

    service = _service(
        ReadinessCheck("database", Requirement.REQUIRED, broken),
    )
    report = service.report()
    component = report.components[0]
    assert component.healthy is False
    assert component.detail == "PROBE_FAILED:RuntimeError"
    assert "TOP-SECRET-VALUE" not in json.dumps(report.as_dict())


def test_readiness_rejects_duplicate_or_unknown_components() -> None:
    with pytest.raises(ProductionReadinessError, match="DUPLICATE_READINESS_COMPONENT"):
        _service(
            ReadinessCheck("database", Requirement.REQUIRED, lambda: True),
            ReadinessCheck("database", Requirement.REQUIRED, lambda: True),
        )
    with pytest.raises(ProductionReadinessError, match="INVALID_READINESS_COMPONENT"):
        _service(ReadinessCheck("unknown", Requirement.REQUIRED, lambda: True))


def test_build_readiness_requires_real_probes_in_production() -> None:
    service = build_readiness_service(
        PRODUCTION_ENV,
        probes={"database": lambda: True},
    )
    report = service.report()
    assert report.status is ReadinessStatus.NOT_READY
    details = {component.name: component.detail for component in report.components}
    assert details["database"] == "OK"
    assert details["object_storage"] == "PROBE_NOT_CONFIGURED"
    assert details["ocr"] == "NOT_CONFIGURED"


def test_build_readiness_ready_with_all_required_probes() -> None:
    names = (
        "database",
        "object_storage",
        "malware_scanner",
        "job_queue",
        "retention",
        "observability",
    )
    service = build_readiness_service(
        PRODUCTION_ENV,
        probes={name: (lambda: ProbeResult(True, "OK")) for name in names},
    )
    report = service.report()
    assert report.status is ReadinessStatus.READY
    assert report.ready is True
    by_name = {component.name: component for component in report.components}
    assert by_name["ocr"].requirement is Requirement.OPTIONAL


def test_correlation_id_validation_and_generation() -> None:
    assert normalize_correlation_id("req-123.abc:def") == "req-123.abc:def"
    injected = normalize_correlation_id("value\r\nInjected: yes")
    assert "\r" not in injected and "\n" not in injected
    assert len(injected) == 32
    assert normalize_correlation_id("x" * 129) != "x" * 129


def test_structured_logger_redacts_and_bounds_fields() -> None:
    stream = io.StringIO()
    logger = StructuredEventLogger(
        stream=stream,
        clock=lambda: datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc),
    )
    payload = logger.emit(
        "http.request.completed",
        correlation_id="req-1",
        fields={
            "path": "/api/projects/P1/documents",
            "authorization": "Bearer abc",
            "access_token": "abc",
            "content": "raw bytes",
            "note": "Bearer abcdef",
            "long": "z" * 600,
        },
    )
    line = stream.getvalue().strip()
    record = json.loads(line)
    assert record["correlation_id"] == "req-1"
    assert record["severity"] == "info"
    assert record["authorization"] == "[redacted]"
    assert record["access_token"] == "[redacted]"
    assert record["content"] == "[redacted]"
    assert "abcdef" not in record["note"]
    assert len(record["long"]) == 512
    assert payload["event"] == "http.request.completed"


def test_redact_fields_handles_nested_sensitive_keys() -> None:
    redacted = redact_fields({"DB_PASSWORD": "x", "safe": 3, "payload_bytes": 10})
    assert redacted == {"DB_PASSWORD": "[redacted]", "safe": 3, "payload_bytes": "[redacted]"}


def test_operational_middleware_liveness_correlation_and_delegation() -> None:
    app = OperationalMiddleware(_static_app())
    status, headers, body, environ = _request(
        app, "GET", HEALTH_LIVE_PATH, headers={"X-Request-ID": "req-42"}
    )
    assert status == 200
    assert json.loads(body)["status"] == "alive"
    assert headers["X-Request-ID"] == "req-42"
    assert headers["Cache-Control"] == "no-store"
    assert environ["construction_pm.correlation_id"] == "req-42"

    status, headers, body, environ = _request(app, "GET", "/api/projects/P-1")
    assert status == 200
    assert body == b"ok"
    assert len(headers["X-Request-ID"]) == 32
    assert environ["construction_pm.correlation_id"] == headers["X-Request-ID"]


def test_operational_middleware_rejects_injected_correlation_id() -> None:
    app = OperationalMiddleware(_static_app())
    status, headers, _, _ = _request(
        app, "GET", HEALTH_LIVE_PATH, headers={"X-Request-ID": "bad\r\nInjected: yes"}
    )
    assert status == 200
    assert "\r" not in headers["X-Request-ID"]
    assert "\n" not in headers["X-Request-ID"]


def test_operational_middleware_readiness_status_codes() -> None:
    not_ready = _service(
        ReadinessCheck("database", Requirement.REQUIRED, lambda: False)
    )
    app = OperationalMiddleware(_static_app(), readiness=not_ready)
    status, headers, body, _ = _request(app, "GET", HEALTH_READY_PATH)
    assert status == 503
    assert json.loads(body)["status"] == "not_ready"

    degraded = _service(
        ReadinessCheck("database", Requirement.REQUIRED, lambda: True),
        ReadinessCheck("ocr", Requirement.OPTIONAL, lambda: False),
    )
    app = OperationalMiddleware(_static_app(), readiness=degraded)
    status, _, body, _ = _request(app, "GET", HEALTH_READY_PATH)
    assert status == 200
    assert json.loads(body)["status"] == "degraded"


def test_operational_middleware_without_readiness_fails_ready_closed() -> None:
    app = OperationalMiddleware(_static_app())
    status, _, body, _ = _request(app, "GET", HEALTH_READY_PATH)
    assert status == 503
    assert json.loads(body)["status"] == "not_ready"


def test_operational_middleware_method_and_head_behavior() -> None:
    app = OperationalMiddleware(_static_app())
    status, headers, _, _ = _request(app, "POST", HEALTH_LIVE_PATH)
    assert status == 405
    assert headers["Allow"] == "GET, HEAD"

    status, headers, body, _ = _request(app, "HEAD", HEALTH_LIVE_PATH)
    assert status == 200
    assert body == b""
    assert int(headers["Content-Length"]) > 0


def test_operational_middleware_logs_path_without_query_string() -> None:
    stream = io.StringIO()
    logger = StructuredEventLogger(stream=stream)
    app = OperationalMiddleware(_static_app(), logger=logger)
    _request(app, "GET", "/api/projects/P-1?token=secret-value")
    record = json.loads(stream.getvalue().strip().splitlines()[-1])
    assert record["event"] == "http.request.completed"
    assert record["path"] == "/api/projects/P-1"
    assert "secret-value" not in stream.getvalue()
    assert record["status"] == 200
