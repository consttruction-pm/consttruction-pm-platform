from __future__ import annotations

from http.cookies import SimpleCookie
from typing import Callable, Iterable, Mapping
from urllib.parse import urlsplit

from .project_lifecycle_routes import ProjectLifecycleHttpRoutes

StartResponse = Callable[[str, list[tuple[str, str]]], None]


class ProjectLifecycleWsgiApp:
    """Dependency-free WSGI adapter for the existing lifecycle HTTP boundary.

    This adapter contains transport translation only. Authentication, tenant
    isolation, project authorization, and lifecycle decisions stay in the
    application service behind ProjectLifecycleHttpRoutes.
    """

    DEFAULT_BODY_LIMIT = 1_048_576
    DEFAULT_P6_IMPORT_BODY_LIMIT = 50 * 1_024 * 1_024

    def __init__(
        self,
        routes: ProjectLifecycleHttpRoutes,
        *,
        default_body_limit: int = DEFAULT_BODY_LIMIT,
        p6_import_body_limit: int = DEFAULT_P6_IMPORT_BODY_LIMIT,
    ) -> None:
        if default_body_limit <= 0 or p6_import_body_limit <= 0:
            raise ValueError("body limits must be positive")
        if p6_import_body_limit < default_body_limit:
            raise ValueError("P6 import body limit must not be smaller than default limit")
        self._routes = routes
        self._default_body_limit = default_body_limit
        self._p6_import_body_limit = p6_import_body_limit

    def __call__(self, environ: dict[str, object], start_response: StartResponse) -> Iterable[bytes]:
        method = str(environ.get("REQUEST_METHOD", "GET")).upper()
        raw_path = str(environ.get("PATH_INFO", "/"))
        path = urlsplit(raw_path).path
        cookie_header = str(environ.get("HTTP_COOKIE", ""))
        cookies = SimpleCookie()
        cookies.load(cookie_header)
        cookie_values = {key: morsel.value for key, morsel in cookies.items()}
        request_headers = self._request_headers(environ)
        limit = self._body_limit(method, path)
        try:
            length = int(str(environ.get("CONTENT_LENGTH", "0") or "0"))
        except ValueError:
            length = -1
        if length < 0:
            status, headers, body = self._error(400, "INVALID_CONTENT_LENGTH")
        elif length > limit:
            status, headers, body = self._error(413, "REQUEST_BODY_TOO_LARGE")
        else:
            stream = environ.get("wsgi.input")
            if length and hasattr(stream, "read"):
                body = stream.read(min(length, limit + 1))
            else:
                body = b""
            if len(body) > limit:
                status, headers, body = self._error(413, "REQUEST_BODY_TOO_LARGE")
            else:
                status, headers, body = self._routes.handle(
                    method, path, cookies=cookie_values, body=body, headers=request_headers
                )
        reason = {200: "OK", 201: "Created", 400: "Bad Request", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found", 409: "Conflict", 413: "Payload Too Large", 502: "Bad Gateway"}.get(status, "Internal Server Error")
        response_headers = [("Content-Length", str(len(body))), *headers.items(),
                            ("Cache-Control", "no-store"), ("X-Content-Type-Options", "nosniff")]
        start_response(f"{status} {reason}", response_headers)
        return [body]


    def _body_limit(self, method: str, path: str) -> int:
        if method == "POST" and path.startswith("/api/projects/") and "/p6/interchange/" in path and path.endswith("/import"):
            return self._p6_import_body_limit
        return self._default_body_limit

    @staticmethod
    def _error(status: int, code: str) -> tuple[int, dict[str, str], bytes]:
        return (status, {"Content-Type": "application/json; charset=utf-8"}, ('{"code":"' + code + '"}').encode("utf-8"))

    @staticmethod
    def _request_headers(environ: Mapping[str, object]) -> dict[str, str]:
        headers: dict[str, str] = {}
        for key, value in environ.items():
            if not key.startswith("HTTP_") or key == "HTTP_COOKIE":
                continue
            if value is None:
                continue
            header_name = "-".join(part.capitalize() for part in key[5:].split("_"))
            headers[header_name] = str(value)
        return headers
