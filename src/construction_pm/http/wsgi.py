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
    DEFAULT_FORM_ASSET_BODY_LIMIT = 21 * 1_024 * 1_024
    DEFAULT_DOCUMENT_CONTENT_BODY_LIMIT = 25 * 1_024 * 1_024

    def __init__(
        self,
        routes: ProjectLifecycleHttpRoutes,
        *,
        default_body_limit: int = DEFAULT_BODY_LIMIT,
        p6_import_body_limit: int = DEFAULT_P6_IMPORT_BODY_LIMIT,
        form_asset_body_limit: int = DEFAULT_FORM_ASSET_BODY_LIMIT,
        document_content_body_limit: int = DEFAULT_DOCUMENT_CONTENT_BODY_LIMIT,
    ) -> None:
        if default_body_limit <= 0 or p6_import_body_limit <= 0:
            raise ValueError("body limits must be positive")
        if p6_import_body_limit < default_body_limit:
            raise ValueError("P6 import body limit must not be smaller than default limit")
        if form_asset_body_limit < default_body_limit:
            raise ValueError("form asset body limit must not be smaller than default limit")
        if document_content_body_limit < default_body_limit:
            raise ValueError("document content body limit must not be smaller than default limit")
        self._routes = routes
        self._default_body_limit = default_body_limit
        self._p6_import_body_limit = p6_import_body_limit
        self._form_asset_body_limit = form_asset_body_limit
        self._document_content_body_limit = document_content_body_limit

    def __call__(self, environ: dict[str, object], start_response: StartResponse) -> Iterable[bytes]:
        method = str(environ.get("REQUEST_METHOD", "GET")).upper()
        raw_path = str(environ.get("PATH_INFO", "/"))
        path = urlsplit(raw_path).path
        query_string = str(environ.get("QUERY_STRING", "") or "")
        if query_string and (
            path.startswith("/api/forms/")
            or (path.startswith("/api/projects/") and "/forms" in path)
            or (path.startswith("/api/projects/") and "/p6/issues" in path)
            or (path.startswith("/api/projects/") and path.endswith("/documents"))
            or (path.startswith("/api/projects/") and "/documents/" in path)
            or (path.startswith("/api/projects/") and path.endswith("/budget/lines"))
            or (path.startswith("/api/projects/") and path.endswith("/budget/funding"))
            or (path.startswith("/api/projects/") and path.endswith("/cost/accounts"))
            or (path.startswith("/api/projects/") and path.endswith("/cost/expenses"))
            or (path.startswith("/api/projects/") and "/cost/accounts/" in path)
            or (path.startswith("/api/projects/") and "/cost/expenses/" in path)
            or (path.startswith("/api/projects/") and "/thresholds" in path)
            or (path.startswith("/api/projects/") and "/risks" in path)
            or (path.startswith("/api/projects/") and "/reports" in path)
            or (path.startswith("/api/projects/") and path.endswith("/tracking/read"))
            or (path.startswith("/api/projects/") and "/administration" in path)
            or (path.startswith("/api/projects/") and "/exchange" in path)
            or (path.startswith("/api/projects/") and "/backup" in path)
        ):
            # Form and issue endpoints read filters and locale from the query
            # string; carry it on the routed path so the shared handler sees it.
            path = f"{path}?{query_string}"
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
            body = b""
            if length and hasattr(stream, "read"):
                body = _read_request_body(stream, length)
            if len(body) > limit:
                status, headers, body = self._error(413, "REQUEST_BODY_TOO_LARGE")
            elif length and len(body) != length:
                # A short read is a truncated request, never a complete body.
                status, headers, body = self._error(400, "REQUEST_BODY_INCOMPLETE")
            else:
                status, headers, body = self._routes.handle(
                    method, path, cookies=cookie_values, body=body, headers=request_headers
                )
        reason = {200: "OK", 201: "Created", 400: "Bad Request", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found", 409: "Conflict", 413: "Payload Too Large", 415: "Unsupported Media Type", 502: "Bad Gateway", 503: "Service Unavailable"}.get(status, "Internal Server Error")
        response_headers = [("Content-Length", str(len(body))), *headers.items(),
                            ("Cache-Control", "no-store"), ("X-Content-Type-Options", "nosniff")]
        start_response(f"{status} {reason}", response_headers)
        return [body]


    def _body_limit(self, method: str, path: str) -> int:
        path = urlsplit(path).path
        if method == "POST" and path.startswith("/api/projects/") and "/p6/interchange/" in path and path.endswith("/import"):
            return self._p6_import_body_limit
        if method == "POST" and (
            path.endswith("/forms/assets") or path == "/api/forms/organization/assets"
        ):
            return self._form_asset_body_limit
        if (
            method == "POST"
            and path.startswith("/api/projects/")
            and "/documents/" in path
            and path.endswith("/content")
        ):
            return self._document_content_body_limit
        return self._default_body_limit

    @staticmethod
    def _error(status: int, code: str) -> tuple[int, dict[str, str], bytes]:
        return (status, {"Content-Type": "application/json; charset=utf-8"}, ('{"code":"' + code + '"}').encode("utf-8"))

    @staticmethod
    def _request_headers(environ: Mapping[str, object]) -> dict[str, str]:
        headers: dict[str, str] = {}
        content_type = environ.get("CONTENT_TYPE")
        if content_type:
            # WSGI exposes Content-Type outside the HTTP_* namespace.
            headers["Content-Type"] = str(content_type)
        for key, value in environ.items():
            if not key.startswith("HTTP_") or key == "HTTP_COOKIE":
                continue
            if value is None:
                continue
            header_name = "-".join(part.capitalize() for part in key[5:].split("_"))
            headers[header_name] = str(value)
        return headers


def _read_request_body(stream, length: int) -> bytes:
    """Read exactly ``length`` bytes, or fewer only on end of stream.

    WSGI permits ``read()`` to return a short buffer, so one call is not
    enough to conclude the request body arrived complete.
    """
    chunks: list[bytes] = []
    remaining = length
    while remaining > 0:
        chunk = stream.read(min(remaining, 65536))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)
