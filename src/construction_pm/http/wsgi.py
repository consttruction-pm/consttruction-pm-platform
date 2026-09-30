from __future__ import annotations

from http.cookies import SimpleCookie
from typing import Callable, Iterable
from urllib.parse import urlsplit

from .project_lifecycle_routes import ProjectLifecycleHttpRoutes

StartResponse = Callable[[str, list[tuple[str, str]]], None]


class ProjectLifecycleWsgiApp:
    """Dependency-free WSGI adapter for the existing lifecycle HTTP boundary.

    This adapter contains transport translation only. Authentication, tenant
    isolation, project authorization, and lifecycle decisions stay in the
    application service behind ProjectLifecycleHttpRoutes.
    """

    def __init__(self, routes: ProjectLifecycleHttpRoutes) -> None:
        self._routes = routes

    def __call__(self, environ: dict[str, object], start_response: StartResponse) -> Iterable[bytes]:
        method = str(environ.get("REQUEST_METHOD", "GET")).upper()
        raw_path = str(environ.get("PATH_INFO", "/"))
        path = urlsplit(raw_path).path
        cookie_header = str(environ.get("HTTP_COOKIE", ""))
        cookies = SimpleCookie()
        cookies.load(cookie_header)
        cookie_values = {key: morsel.value for key, morsel in cookies.items()}
        try:
            length = int(str(environ.get("CONTENT_LENGTH", "0") or "0"))
        except ValueError:
            length = -1
        if length < 0 or length > 1_048_576:
            status, headers, body = 400, {"Content-Type": "application/json; charset=utf-8"}, b'{"code":"INVALID_CONTENT_LENGTH"}'
        else:
            stream = environ.get("wsgi.input")
            body = stream.read(length) if length and hasattr(stream, "read") else b""
            status, headers, body = self._routes.handle(
                method, path, cookies=cookie_values, body=body
            )
        reason = {200: "OK", 201: "Created", 400: "Bad Request", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found"}.get(status, "Internal Server Error")
        response_headers = [("Content-Length", str(len(body))), *headers.items(),
                            ("Cache-Control", "no-store"), ("X-Content-Type-Options", "nosniff")]
        start_response(f"{status} {reason}", response_headers)
        return [body]
