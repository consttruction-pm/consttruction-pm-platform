"""WSGI operational surface: liveness, readiness and request correlation.

The middleware is intentionally outside the domain/application layers. It only
answers read-only probe paths and annotates requests with a safe correlation
id. It never authenticates business traffic, mutates state, or exposes
configuration values.

- ``GET|HEAD /api/health/live``  — process liveness, always 200 while serving.
- ``GET|HEAD /api/health/ready`` — dependency readiness; 200 for ``ready`` and
  ``degraded``, 503 for ``not_ready``. A degraded response means only optional
  components are unavailable.
- ``GET|HEAD /api/metrics`` — optional bounded metrics scrape, only when a
  metrics export service is configured. It requires a bearer token, is never
  cached, and is served outside request instrumentation. Health and readiness
  never depend on it.
"""

from __future__ import annotations

import json
from time import monotonic
from typing import Callable, Iterable, Mapping
from urllib.parse import urlsplit

from ..metrics_export import (
    CONTENT_TYPE as METRICS_CONTENT_TYPE,
    METRICS_PATH,
    MetricsExportService,
    MetricsExportState,
)
from ..observability import (
    OperationalMetrics,
    reset_correlation_id,
    set_correlation_id,
)
from ..production_readiness import (
    ReadinessService,
    StructuredEventLogger,
    correlation_id_from_environ,
)

StartResponse = Callable[[str, list[tuple[str, str]]], None]

HEALTH_LIVE_PATH = "/api/health/live"
HEALTH_READY_PATH = "/api/health/ready"
HEALTH_PATHS = frozenset({HEALTH_LIVE_PATH, HEALTH_READY_PATH})
CORRELATION_HEADER = "X-Request-ID"
_ROUTE_TEMPLATES = (
    ("document_upload", "/documents/", "content", {"POST"}),
    ("exchange_import", "/exchange/", None, {"POST"}),
    ("exchange_export", "/exchange/", "export", {"GET"}),
    ("report_run", "/reports/", "runs", {"POST"}),
    ("report_export", "/reports/", "export", {"GET"}),
    ("report_schedule", "/reports/", "schedules", {"POST", "PUT", "DELETE"}),
)


def route_template(method: str, path: str) -> str:
    """Classify a request for bounded metric labels; never return a raw path."""
    for name, marker, suffix, methods in _ROUTE_TEMPLATES:
        if marker in path and method in methods:
            if suffix is None or path.rstrip("/").endswith(suffix):
                return name
    if "/documents/" in path:
        return "document"
    return "http"


def _json_response(
    start_response: StartResponse,
    status_code: int,
    payload: Mapping[str, object],
    *,
    correlation_id: str,
    extra_headers: Iterable[tuple[str, str]] = (),
    include_body: bool = True,
) -> list[bytes]:
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    reason = {
        200: "OK",
        401: "Unauthorized",
        404: "Not Found",
        405: "Method Not Allowed",
        503: "Service Unavailable",
    }.get(status_code, "OK")
    headers = [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(body))),
        ("Cache-Control", "no-store"),
        (CORRELATION_HEADER, correlation_id),
        *extra_headers,
    ]
    start_response(f"{status_code} {reason}", headers)
    return [body] if include_body else []


class OperationalMiddleware:
    """Read-only health endpoints plus request correlation and event logging."""

    def __init__(
        self,
        app: Callable[[dict[str, object], StartResponse], Iterable[bytes]],
        *,
        readiness: ReadinessService | None = None,
        logger: StructuredEventLogger | None = None,
        metrics: OperationalMetrics | None = None,
        metrics_export: MetricsExportService | None = None,
    ) -> None:
        if not callable(app):
            raise ValueError("OPERATIONAL_APP_NOT_CALLABLE")
        self._app = app
        self._readiness = readiness
        self._logger = logger
        self._metrics = metrics
        self._metrics_export = metrics_export

    def __call__(
        self, environ: dict[str, object], start_response: StartResponse
    ) -> Iterable[bytes]:
        method = str(environ.get("REQUEST_METHOD", "GET")).upper()
        path = urlsplit(str(environ.get("PATH_INFO", "/"))).path
        correlation_id = correlation_id_from_environ(environ)
        environ["construction_pm.correlation_id"] = correlation_id
        environ["HTTP_X_REQUEST_ID"] = correlation_id
        if path in HEALTH_PATHS:
            return self._health(method, path, start_response, correlation_id)
        if path == METRICS_PATH and self._metrics_export is not None:
            return self._scrape(
                method,
                start_response,
                correlation_id,
                str(environ.get("HTTP_AUTHORIZATION", "") or ""),
            )

        started = monotonic()
        status = {"code": 500}
        route = route_template(method, path)
        correlation_token = set_correlation_id(correlation_id)

        def correlated_start_response(
            value: str,
            headers: list[tuple[str, str]],
            exc_info: object = None,
        ) -> object:
            try:
                status["code"] = int(str(value).split(" ", 1)[0])
            except (TypeError, ValueError):
                status["code"] = 500
            prepared = list(headers)
            if not any(name.lower() == CORRELATION_HEADER.lower() for name, _ in prepared):
                prepared.append((CORRELATION_HEADER, correlation_id))
            if exc_info is None:
                return start_response(value, prepared)
            return start_response(value, prepared, exc_info)  # type: ignore[call-arg]

        try:
            response = self._app(environ, correlated_start_response)
        except Exception as exc:
            self._emit(
                "http.request.failed",
                severity="error",
                correlation_id=correlation_id,
                fields={
                    "method": method,
                    "path": path,
                    "duration_ms": int((monotonic() - started) * 1000),
                    "error_type": type(exc).__name__,
                },
            )
            self._record(route, method, 500, started)
            raise
        finally:
            reset_correlation_id(correlation_token)
        self._emit(
            "http.request.completed",
            correlation_id=correlation_id,
            fields={
                "method": method,
                "path": path,
                "status": status["code"],
                "duration_ms": int((monotonic() - started) * 1000),
            },
        )
        self._record(route, method, status["code"], started)
        return response

    def _record(self, route: str, method: str, status: int, started: float) -> None:
        if self._metrics is None:
            return
        status_class = f"{status // 100}xx"
        duration_ms = (monotonic() - started) * 1000
        try:
            self._metrics.increment(
                "http_requests_total",
                labels={"route": route, "method": method, "status_class": status_class},
            )
            self._metrics.observe(
                "http_request_duration_ms", duration_ms, labels={"route": route}
            )
        except ValueError:
            # Metrics must never break a request; label validation is bounded
            # above, so this only guards a custom registry implementation.
            return

    def _emit(self, event: str, **kwargs: object) -> None:
        if self._logger is not None:
            self._logger.emit(event, **kwargs)  # type: ignore[arg-type]

    def _record_metrics_export_unauthorized(self, correlation_id: str) -> None:
        """Bound the observable cost of unauthenticated scrape attempts.

        The counter has no labels, so hostile callers cannot grow the series
        set, and the event carries no credential material. Failures while
        recording must never change the 401 response.
        """

        if self._metrics is not None:
            try:
                self._metrics.increment("metrics_export_unauthorized_total")
            except ValueError:
                pass
        self._emit(
            "metrics_export_unauthorized",
            severity="warning",
            correlation_id=correlation_id,
            fields={"path": METRICS_PATH, "reason": "bearer_rejected"},
        )

    def _scrape(
        self,
        method: str,
        start_response: StartResponse,
        correlation_id: str,
        authorization: str,
    ) -> list[bytes]:
        assert self._metrics_export is not None
        service = self._metrics_export
        if service.state is MetricsExportState.DISABLED:
            # The route does not exist when export is disabled.
            return _json_response(
                start_response,
                404,
                {"status": "not_found"},
                correlation_id=correlation_id,
            )
        if method not in {"GET", "HEAD"}:
            return _json_response(
                start_response,
                405,
                {"status": "method_not_allowed"},
                correlation_id=correlation_id,
                extra_headers=[("Allow", "GET, HEAD")],
            )
        if not service.authorized(authorization):
            self._record_metrics_export_unauthorized(correlation_id)
            return _json_response(
                start_response,
                401,
                {"status": "unauthorized", "code": "METRICS_EXPORT_UNAUTHORIZED"},
                correlation_id=correlation_id,
                extra_headers=[("WWW-Authenticate", 'Bearer realm="metrics"')],
            )
        result = service.scrape()
        if not result.ok:
            return _json_response(
                start_response,
                503,
                {
                    "status": "unavailable",
                    "code": result.error or "METRICS_EXPORT_UNAVAILABLE",
                },
                correlation_id=correlation_id,
            )
        payload = result.body.encode("utf-8")
        include_body = method != "HEAD"
        start_response(
            "200 OK",
            [
                ("Content-Type", METRICS_CONTENT_TYPE),
                ("Content-Length", str(len(payload))),
                ("Cache-Control", "no-store"),
                (CORRELATION_HEADER, correlation_id),
            ],
        )
        return [payload] if include_body else []

    def _health(
        self,
        method: str,
        path: str,
        start_response: StartResponse,
        correlation_id: str,
    ) -> list[bytes]:
        if method not in {"GET", "HEAD"}:
            return _json_response(
                start_response,
                405,
                {"status": "method_not_allowed"},
                correlation_id=correlation_id,
                extra_headers=[("Allow", "GET, HEAD")],
                include_body=method != "HEAD",
            )
        include_body = method != "HEAD"
        if self._readiness is None:
            if path == HEALTH_LIVE_PATH:
                return _json_response(
                    start_response,
                    200,
                    {"status": "alive", "service": "construction-pm"},
                    correlation_id=correlation_id,
                    include_body=include_body,
                )
            return _json_response(
                start_response,
                503,
                {
                    "status": "not_ready",
                    "components": [
                        {
                            "name": "readiness",
                            "requirement": "required",
                            "status": "unhealthy",
                            "detail": "READINESS_NOT_CONFIGURED",
                        }
                    ],
                },
                correlation_id=correlation_id,
                include_body=include_body,
            )
        if path == HEALTH_LIVE_PATH:
            return _json_response(
                start_response,
                200,
                {"status": "alive", "service": "construction-pm"},
                correlation_id=correlation_id,
                include_body=include_body,
            )
        report = self._readiness.report()
        payload = report.as_dict()
        status_code = 200 if report.ready else 503
        return _json_response(
            start_response,
            status_code,
            payload,
            correlation_id=correlation_id,
            include_body=include_body,
        )


__all__ = [
    "CORRELATION_HEADER",
    "HEALTH_LIVE_PATH",
    "HEALTH_PATHS",
    "HEALTH_READY_PATH",
    "METRICS_PATH",
    "OperationalMiddleware",
]
