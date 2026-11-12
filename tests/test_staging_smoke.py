from __future__ import annotations

import io
import json
import threading
from urllib.error import HTTPError, URLError
from wsgiref.simple_server import WSGIRequestHandler, make_server

import pytest

from construction_pm.http.operational import OperationalMiddleware
from construction_pm.production_readiness import (
    ReadinessCheck,
    ReadinessService,
    Requirement,
)
from construction_pm.staging_smoke import (
    StagingSmokeError,
    main,
    run_staging_smoke,
)


class _Response:
    def __init__(self, payload: dict[str, object], status: int = 200) -> None:
        self.status = status
        self._payload = json.dumps(payload).encode("utf-8")
        self.closed = False

    def read(self, limit: int) -> bytes:
        return self._payload[:limit]

    def close(self) -> None:
        self.closed = True


def _opener(responses):
    calls: list[tuple[str, str]] = []

    def open_request(request, *, timeout):
        calls.append((request.get_method(), request.full_url))
        response = responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    return open_request, calls


def _ready_body(status: str = "ready", *, database: str = "healthy") -> dict[str, object]:
    return {
        "status": status,
        "generated_at": "2026-11-12T12:00:00+00:00",
        "components": [
            {"name": "configuration", "requirement": "required", "status": "healthy", "detail": "OK"},
            {"name": "database", "requirement": "required", "status": database, "detail": "OK"},
        ],
    }


def test_smoke_uses_only_get_requests_and_passes() -> None:
    opener, calls = _opener([
        _Response({"status": "alive"}),
        _Response(_ready_body()),
    ])
    report = run_staging_smoke("https://staging.example", opener=opener)
    assert report.ok
    assert [method for method, _ in calls] == ["GET", "GET"]
    assert calls[0][1] == "https://staging.example/api/health/live"
    assert calls[1][1] == "https://staging.example/api/health/ready"
    assert report.as_dict()["mutated"] is False


def test_smoke_fails_when_readiness_is_not_ready() -> None:
    opener, _ = _opener([
        _Response({"status": "alive"}),
        _Response(_ready_body("not_ready", database="unhealthy"), status=200),
    ])
    report = run_staging_smoke("https://staging.example", opener=opener)
    assert report.ok is False
    readiness = report.checks[1]
    assert readiness.name == "readiness"
    assert readiness.ok is False
    assert "REQUIRED_COMPONENT_NOT_HEALTHY:database" in readiness.detail or (
        "NOT_READY:database" in readiness.detail
    )


def test_smoke_accepts_degraded_readiness() -> None:
    opener, _ = _opener([
        _Response({"status": "alive"}),
        _Response(_ready_body("degraded")),
    ])
    report = run_staging_smoke("https://staging.example", opener=opener)
    assert report.ok is True


def test_smoke_handles_http_and_transport_errors() -> None:
    error = HTTPError(
        "https://staging.example/api/health/live",
        503,
        "unavailable",
        None,
        io.BytesIO(b'{"status":"not_ready"}'),
    )
    opener, _ = _opener([error, URLError("connection refused")])
    report = run_staging_smoke("https://staging.example", opener=opener)
    assert report.ok is False
    assert report.checks[0].status_code == 503
    assert report.checks[1].detail.startswith("TRANSPORT_ERROR")


def test_smoke_rejects_invalid_targets() -> None:
    for value in (
        "",
        "ftp://staging.example",
        "https://user:password@staging.example",
        "https://staging.example/path?token=x",
        "not-a-url",
    ):
        with pytest.raises(StagingSmokeError):
            run_staging_smoke(value)


def test_smoke_rejects_invalid_timeout() -> None:
    with pytest.raises(StagingSmokeError, match="INVALID_SMOKE_TIMEOUT"):
        run_staging_smoke("https://staging.example", timeout=0)


def test_smoke_cli_returns_expected_exit_codes(capsys) -> None:
    opener, _ = _opener([
        _Response({"status": "alive"}),
        _Response(_ready_body()),
    ])
    assert main(["--base-url", "https://staging.example"], opener=opener) == 0
    output = json.loads(capsys.readouterr().out.strip())
    assert output["ok"] is True

    assert main(["--base-url", "ftp://bad"], opener=opener) == 2
    assert json.loads(capsys.readouterr().out.strip())["error"] == "INVALID_STAGING_BASE_URL"


class _QuietHandler(WSGIRequestHandler):
    def log_message(self, format, *args) -> None:  # noqa: A002 - stdlib signature
        return


def test_smoke_over_real_http_server() -> None:
    methods: list[str] = []

    def base_app(environ, start_response):
        methods.append(str(environ.get("REQUEST_METHOD")))
        start_response("200 OK", [("Content-Type", "text/plain")])
        return [b"ok"]

    readiness = ReadinessService(
        (
            ReadinessCheck("configuration", Requirement.REQUIRED, lambda: True),
            ReadinessCheck("database", Requirement.REQUIRED, lambda: True),
        )
    )
    app = OperationalMiddleware(base_app, readiness=readiness)
    server = make_server("127.0.0.1", 0, app, handler_class=_QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        report = run_staging_smoke(
            f"http://127.0.0.1:{server.server_port}",
            required_components=("configuration", "database"),
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    assert report.ok, report.as_dict()
    assert methods == []  # health paths were answered by the middleware, not the app
