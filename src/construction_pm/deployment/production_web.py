"""HTTP transport for the production deployment.

Three responsibilities live here, and only these three:

1. Login and logout write a real persisted session and set hardened cookies.
2. Every state-changing API call must come from the deployed origin and carry
   the CSRF token derived from the caller's own session.
3. ``/app`` is never served without a valid session; ``/login`` is the only
   anonymous HTML surface, and static assets contain no user data.

The application routes themselves are unchanged and remain in
``ProjectLifecycleHttpRoutes``.
"""

from __future__ import annotations

import json
import mimetypes
import os
import traceback
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping
from urllib.parse import parse_qs, quote, unquote, urlencode, urlsplit

from ..identity_session import (
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    SESSION_COOKIE_NAME,
    IdentityError,
    IdentityService,
    clear_cookie_header,
    clear_csrf_cookie_header,
    csrf_cookie_header,
    hash_client_ip,
    session_cookie_header,
)

StartResponse = Callable[[str, list[tuple[str, str]]], None]

LOGIN_PATH = "/login"
APP_PATH = "/app"
ADMIN_PATH = "/admin"
ENTERPRISE_PATH = "/enterprise"
CUBI_PATH = "/cubi"
WORKBENCH_PATH = "/workbench"
AI_WORKBENCH_PATH = "/ai-workbench"
WORKSPACE_PATHS = frozenset({APP_PATH, ADMIN_PATH, WORKBENCH_PATH})
# Public (unauthenticated) documents of the Enterprise application. The login
# card and the public home page must render before a session exists; every
# other /cubi/* document is a signed-in surface.
CUBI_PUBLIC_PATHS = frozenset(
    {CUBI_PATH, CUBI_PATH + "/", CUBI_PATH + "/login", CUBI_PATH + "/login/"}
)
CUBI_ENTERPRISE_PREFIX = CUBI_PATH + "/enterprise"
ENTERPRISE_ACCESS_ROLES = frozenset(
    {"enterprise_admin", "enterprise_user", "enterprise_viewer", "global_admin"}
)
API_PREFIX = "/api/"
LOGIN_BODY_LIMIT = 8_192
API_BODY_LIMIT = 1_048_576

_SECURITY_HEADERS = (
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "DENY"),
    ("Referrer-Policy", "no-referrer"),
    ("Permissions-Policy", "camera=(), microphone=(), geolocation=()"),
    ("Cross-Origin-Opener-Policy", "same-origin"),
)

_STATIC_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".map": "application/json; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
    ".txt": "text/plain; charset=utf-8",
    ".xml": "application/xml",
    ".webmanifest": "application/manifest+json",
}


class StaticSite:
    """Explicit, non-traversable static file mapping for the built client."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root).expanduser().resolve()
        self.public = self.root / "public"
        self.dist = self.root / "dist"

    def resolve(self, request_path: str) -> Path | None:
        raw = urlsplit(request_path).path
        try:
            pathname = unquote(raw.encode("latin-1").decode("utf-8"))
        except (UnicodeEncodeError, UnicodeDecodeError):
            pathname = unquote(raw)
        if not pathname.startswith("/"):
            return None
        segments = [segment for segment in pathname.split("/") if segment]
        if any(segment in {".", ".."} or segment.startswith(".") for segment in segments):
            return None
        try:
            candidate = self._resolve(segments)
        except OSError:
            return None
        if candidate is None:
            return None
        try:
            if not candidate.resolve().is_relative_to(self.root):
                return None
        except (OSError, ValueError):
            return None
        return candidate

    def _resolve(self, segments: list[str]) -> Path | None:
        if not segments:
            return _file(self.root / "index.html")
        if segments == ["index.html"]:
            return _file(self.root / "index.html")
        if segments in (["app"], ["app", "index.html"]):
            return _file(self.root / "app.html")
        # The AI Workbench has its own document and bundle inside the
        # Engineering environment; it is never the general workspace shell.
        if segments in (
            ["ai-workbench"],
            ["ai-workbench", "index.html"],
            ["ai-workbench.html"],
        ):
            return _file(self.root / "ai-workbench.html")
        # The Enterprise application is its own document (`enterprise.html`).
        # It is never served as the Engineering shell. Every /cubi/* path is
        # owned by the Enterprise client router, so all of them resolve to the
        # same document; the HTTP boundary applies the session gate.
        if segments and segments[0] == "cubi":
            return _file(self.root / "enterprise.html")
        # The retired /enterprise address is redirected by the HTTP boundary;
        # mapping it here as well means an accidental static fallthrough can
        # still never expose the Engineering shell.
        if segments in (["enterprise"], ["enterprise", "index.html"]):
            return _file(self.root / "enterprise.html")
        if segments[0] == "dist":
            rest = segments[1:]
            if not rest:
                return None
            if rest[0] in {"web", "client-sync"}:
                return _file(self.dist.joinpath(*rest))
            # The Vercel build flattens bundles into ``public/dist``; the local
            # web root keeps the tsc/esbuild layout at ``dist/web/src``.
            return _file(self.dist.joinpath(*rest)) or _file(
                self.dist.joinpath("web", "src", *rest)
            )
        if segments[:2] == ["client-sync", "src"]:
            return _file(self.dist.joinpath("client-sync", "src", *segments[2:]))
        if len(segments) == 1:
            direct = _file(self.root / segments[0]) or _file(self.public / segments[0])
            if direct is not None:
                return direct
            # Public directories such as /environments/ ship as index.html.
            # The assembled deployment flattens them into the web root.
            for directory in (self.root / segments[0], self.public / segments[0]):
                if directory.is_dir():
                    index = _file(directory / "index.html")
                    if index is not None:
                        return index
            return None
        if segments[0] == "public":
            return _file(self.public.joinpath(*segments[1:])) if len(segments) > 1 else None
        direct = _file(self.public.joinpath(*segments))
        if direct is not None:
            return direct
        directory = self.public.joinpath(*segments)
        if directory.is_dir():
            return _file(directory / "index.html")
        return _file(self.root.joinpath(*segments))


def _file(candidate: Path) -> Path | None:
    try:
        return candidate if candidate.is_file() else None
    except OSError:
        return None


def _content_type(path: Path) -> str:
    return _STATIC_TYPES.get(
        path.suffix.lower(),
        mimetypes.guess_type(path.name)[0] or "application/octet-stream",
    )


def _cookie_values(environ: Mapping[str, Any]) -> dict[str, str]:
    from http.cookies import SimpleCookie

    cookies = SimpleCookie()
    try:
        cookies.load(str(environ.get("HTTP_COOKIE", "")))
    except Exception:
        return {}
    return {key: morsel.value for key, morsel in cookies.items()}


def _header(environ: Mapping[str, Any], name: str) -> str:
    key = "HTTP_" + name.upper().replace("-", "_")
    value = environ.get(key)
    if value is None and name.lower() == "content-type":
        value = environ.get("CONTENT_TYPE")
    if value is None and name.lower() == "content-length":
        value = environ.get("CONTENT_LENGTH")
    return str(value or "")


def _client_ip(environ: Mapping[str, Any]) -> str:
    # Vercel overwrites ``x-forwarded-for`` with the client address and also
    # sets ``x-real-ip``. Prefer the single-value header, then the first
    # forwarded entry, so throttling cannot be keyed by a client-supplied list.
    real = _header(environ, "x-real-ip").strip()
    if real:
        return real
    forwarded = _header(environ, "x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return str(environ.get("REMOTE_ADDR", "") or "")


def _safe_next(value: str | None) -> str:
    """Return a same-origin destination, defaulting to the Personal Workbench.

    Sign-in must not drop an ordinary account into the Engineering workspace.
    The Personal Workbench is the single signed-in entry that lets the caller
    choose an environment. Two explicit destinations survive the round trip:

    * ``/app?view=live`` (optionally with a project id) — a requested
      Engineering deep link;
    * ``/cubi/*`` — a requested Enterprise document.

    Everything else resolves to the Workbench.
    """
    fallback = f"{WORKBENCH_PATH}/"
    if not isinstance(value, str):
        return fallback
    candidate = value.strip()
    if not candidate.startswith("/") or candidate.startswith("//"):
        return fallback
    if "\\" in candidate or any(ord(char) < 0x20 for char in candidate):
        return fallback
    split = urlsplit(candidate)
    if split.scheme or split.netloc or split.fragment:
        return fallback
    path = split.path
    if path in (CUBI_PATH, CUBI_PATH + "/") or path.startswith(CUBI_PATH + "/"):
        return candidate
    if path in (WORKBENCH_PATH, WORKBENCH_PATH + "/", ADMIN_PATH, ADMIN_PATH + "/"):
        return candidate
    if path in (AI_WORKBENCH_PATH, AI_WORKBENCH_PATH + "/"):
        query = parse_qs(split.query, keep_blank_values=True)
        if set(query) - {"project", "lang", "studio"}:
            return AI_WORKBENCH_PATH
        project_values = query.get("project", [])
        project_id = project_values[0].strip() if len(project_values) == 1 else ""
        if project_values and (
            not project_id
            or len(project_id) > 200
            or any(ord(char) < 0x20 or char in "/\\" for char in project_id)
        ):
            return AI_WORKBENCH_PATH
        preserved = {key: [query[key][0]] for key in ("lang", "studio") if key in query}
        if project_id:
            preserved["project"] = [project_id]
        return AI_WORKBENCH_PATH + (
            "?" + urlencode(preserved, doseq=True) if preserved else ""
        )
    if path not in (APP_PATH, APP_PATH + "/"):
        return fallback
    query = parse_qs(split.query, keep_blank_values=True)
    if set(query) - {"project", "view"}:
        return f"{APP_PATH}?view=live"
    project_values = query.get("project", [])
    if len(project_values) > 1:
        return f"{APP_PATH}?view=live"
    project_id = project_values[0].strip() if project_values else ""
    if project_values and (
        not project_id
        or len(project_id) > 200
        or any(ord(char) < 0x20 or char in "/\\" for char in project_id)
    ):
        return f"{APP_PATH}?view=live"
    view_values = query.get("view", [])
    if len(view_values) > 1 or (view_values and view_values[0] not in {"live", "visual"}):
        return f"{APP_PATH}?view=live"
    if project_id:
        return f"{APP_PATH}?" + urlencode({"project": project_id, "view": "live"})
    return f"{APP_PATH}?view=live"


def _read_body(environ: Mapping[str, Any], limit: int) -> bytes:
    try:
        length = int(str(environ.get("CONTENT_LENGTH", "0") or "0"))
    except ValueError:
        raise IdentityError("REQUEST_LENGTH_INVALID") from None
    if length < 0 or length > limit:
        raise IdentityError("REQUEST_TOO_LARGE")
    stream = environ.get("wsgi.input")
    if length == 0 or not hasattr(stream, "read"):
        return b""
    body = stream.read(length)
    if len(body) != length:
        raise IdentityError("REQUEST_BODY_INCOMPLETE")
    return body


def _origin_is_acceptable(origin: str) -> bool:
    """Production is HTTPS; plain HTTP is only tolerated on the loopback host.

    The local end-to-end harness serves the exact production runtime over
    ``http://127.0.0.1``. Any other non-HTTPS origin is a configuration error.
    """
    if origin.startswith("https://"):
        return True
    split = urlsplit(origin)
    return split.scheme == "http" and split.hostname in {"127.0.0.1", "localhost", "::1"}


class ProductionWebApp:
    def __init__(
        self,
        *,
        api_app: Callable[[dict[str, object], StartResponse], Iterable[bytes]],
        identity: IdentityService,
        site: StaticSite,
        public_origin: str,
        secure_cookies: bool,
        readiness: Callable[[], Mapping[str, object]],
        ip_secret: str | None = None,
    ) -> None:
        if not _origin_is_acceptable(public_origin):
            raise ValueError("PUBLIC_ORIGIN_MUST_BE_HTTPS")
        self.api_app = api_app
        self.identity = identity
        self.site = site
        self.public_origin = public_origin.rstrip("/")
        self.secure_cookies = secure_cookies
        self.readiness = readiness
        # Use the identity secret the service actually verifies with; the
        # environment fallback only exists for callers that construct the
        # service directly.
        self._ip_secret = ip_secret or os.environ.get("CONSTRUCTION_PM_SESSION_SECRET", "")

    # -- WSGI --------------------------------------------------------------
    def __call__(
        self, environ: dict[str, object], start_response: StartResponse
    ) -> Iterable[bytes]:
        method = str(environ.get("REQUEST_METHOD", "GET")).upper()
        path = str(environ.get("PATH_INFO", "/")) or "/"
        # Vercel rewrites the catch-all API route to this function and keeps
        # the original path in the query string.
        query = parse_qs(str(environ.get("QUERY_STRING", "") or ""), keep_blank_values=True)
        rewritten = query.pop("__path", None)
        if rewritten is None and path in {"/api", "/api/index", "/api/index.py"}:
            # Defensive fallback if the platform preserves the original path in
            # a header instead of the rewrite query.
            for name in ("x-vercel-original-path", "x-original-url", "x-forwarded-uri"):
                candidate = _header(environ, name)
                if candidate.startswith("/api/"):
                    rewritten = [candidate[len("/api/"):]]
                    break
        if rewritten is None and path == "/api":
            # A direct invocation of the catch-all function carries no route.
            path = "/api/__cubi_root"
            environ = dict(environ)
            environ["PATH_INFO"] = path
        if rewritten is not None:
            path = "/api/" + rewritten[0].lstrip("/")
            environ = dict(environ)
            environ["PATH_INFO"] = path
            environ["QUERY_STRING"] = "&".join(
                f"{quote(key)}={quote(value)}"
                for key, values in query.items()
                for value in values
            )
        try:
            status, headers, body = self._dispatch(method, path, environ)
        except IdentityError as error:
            status, headers, body = _json(400, {"code": error.code})
        except Exception:
            traceback.print_exc()
            status, headers, body = _json(500, {"code": "INTERNAL_ERROR"})
        response_headers = [
            ("Content-Length", str(len(body))),
            *headers,
            *_SECURITY_HEADERS,
        ]
        if str(environ.get("wsgi.url_scheme", "")).lower() == "https" or _header(
            environ, "x-forwarded-proto"
        ).lower() == "https":
            response_headers.append(
                ("Strict-Transport-Security", "max-age=63072000; includeSubDomains")
            )
        reason = {
            200: "OK",
            204: "No Content",
            302: "Found",
            303: "See Other",
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            405: "Method Not Allowed",
            409: "Conflict",
            413: "Payload Too Large",
            429: "Too Many Requests",
            503: "Service Unavailable",
        }.get(status, "Internal Server Error")
        start_response(f"{status} {reason}", response_headers)
        return [body]

    def _dispatch(
        self, method: str, path: str, environ: Mapping[str, Any]
    ) -> tuple[int, list[tuple[str, str]], bytes]:
        if path == "/api/health/live":
            return _json(200, {"status": "ok"}, cache="no-store")
        if path == "/api/health/ready":
            report = dict(self.readiness())
            ready = report.get("status") == "ready"
            return _json(200 if ready else 503, report, cache="no-store")
        if path == "/api/session" and method == "POST":
            return self._login(environ)
        if path == "/api/session" and method == "DELETE":
            return self._logout(environ)
        if path.startswith(API_PREFIX):
            return self._api(method, path, environ)
        if path in (ENTERPRISE_PATH, ENTERPRISE_PATH + "/"):
            # The legacy /enterprise path used to serve the Engineering shell.
            # It now resolves to the canonical Enterprise document so no
            # Enterprise link can be mistaken for the Engineering workspace.
            query = environ.get("QUERY_STRING", "")
            target = CUBI_PATH + "/" + (f"?{query}" if query else "")
            return 308, [("Location", target), ("Cache-Control", "no-store")], b""
        if path == CUBI_PATH or path.startswith(CUBI_PATH + "/"):
            return self._cubi(method, environ)
        if path == AI_WORKBENCH_PATH or path.startswith(AI_WORKBENCH_PATH + "/"):
            return self._workbench(method, environ)
        if path in WORKSPACE_PATHS or path.rstrip("/") in WORKSPACE_PATHS:
            return self._app(method, environ)
        if path == LOGIN_PATH:
            return self._login_page(method, environ)
        if method in {"GET", "HEAD"}:
            return self._static(method, path)
        return _json(405, {"code": "METHOD_NOT_ALLOWED"}, cache="no-store")

    # -- authentication ----------------------------------------------------
    def _login(
        self, environ: Mapping[str, Any]
    ) -> tuple[int, list[tuple[str, str]], bytes]:
        if not self._origin_allowed(environ):
            return _json(403, {"code": "ORIGIN_NOT_ALLOWED"}, cache="no-store")
        content_type = _header(environ, "content-type").split(";")[0].strip().lower()
        if content_type != "application/json":
            return _json(400, {"code": "LOGIN_REQUEST_INVALID"}, cache="no-store")
        try:
            raw = _read_body(environ, LOGIN_BODY_LIMIT)
            payload = json.loads(raw.decode("utf-8") or "{}")
        except (IdentityError, UnicodeDecodeError, json.JSONDecodeError):
            return _json(400, {"code": "LOGIN_REQUEST_INVALID"}, cache="no-store")
        if not isinstance(payload, dict):
            return _json(400, {"code": "LOGIN_REQUEST_INVALID"}, cache="no-store")
        email = payload.get("email")
        password = payload.get("password")
        if not isinstance(email, str) or not isinstance(password, str):
            return _json(400, {"code": "LOGIN_REQUEST_INVALID"}, cache="no-store")
        ip_hash = hash_client_ip(self._ip_secret, _client_ip(environ))
        try:
            issued = self.identity.login(email, password, ip_hash=ip_hash)
        except IdentityError as error:
            if error.code == "AUTHENTICATION_THROTTLED":
                return _json(
                    429,
                    {"code": error.code},
                    cache="no-store",
                    extra=[("Retry-After", "900")],
                )
            return _json(401, {"code": "AUTHENTICATION_FAILED"}, cache="no-store")
        max_age = max(1, int((issued.expires_at - issued.created_at).total_seconds()))
        headers = [
            ("Set-Cookie", session_cookie_header(
                name=SESSION_COOKIE_NAME,
                value=issued.token,
                max_age=max_age,
                secure=self.secure_cookies,
            )),
            ("Set-Cookie", csrf_cookie_header(
                name=CSRF_COOKIE_NAME,
                value=issued.csrf_token,
                max_age=max_age,
                secure=self.secure_cookies,
            )),
        ]
        return _json(
            200,
            {
                "user_id": issued.user_id,
                "tenant_id": issued.tenant_id,
                "roles": sorted(issued.roles),
                "expires_at": issued.expires_at.isoformat(),
            },
            cache="no-store",
            extra=headers,
        )

    def _logout(
        self, environ: Mapping[str, Any]
    ) -> tuple[int, list[tuple[str, str]], bytes]:
        if not self._origin_allowed(environ):
            return _json(403, {"code": "ORIGIN_NOT_ALLOWED"}, cache="no-store")
        cookies = _cookie_values(environ)
        token = cookies.get(SESSION_COOKIE_NAME, "")
        csrf = _header(environ, CSRF_HEADER_NAME)
        if token and not self.identity.verify_csrf(token, csrf):
            return _json(403, {"code": "CSRF_TOKEN_INVALID"}, cache="no-store")
        if token:
            self.identity.logout(token)
        headers = [
            ("Set-Cookie", clear_cookie_header(
                name=SESSION_COOKIE_NAME, secure=self.secure_cookies,
            )),
            ("Set-Cookie", clear_csrf_cookie_header(
                name=CSRF_COOKIE_NAME, secure=self.secure_cookies,
            )),
        ]
        return 204, headers, b""

    # -- API delegation ----------------------------------------------------
    def _api(
        self, method: str, path: str, environ: Mapping[str, Any]
    ) -> tuple[int, list[tuple[str, str]], bytes]:
        if method not in {"GET", "HEAD", "OPTIONS"}:
            if not self._origin_allowed(environ):
                return _json(403, {"code": "CSRF_ORIGIN_MISMATCH"}, cache="no-store")
            cookies = _cookie_values(environ)
            token = cookies.get(SESSION_COOKIE_NAME, "")
            if token and not self.identity.verify_csrf(
                token, _header(environ, CSRF_HEADER_NAME)
            ):
                return _json(403, {"code": "CSRF_TOKEN_INVALID"}, cache="no-store")
        collected: dict[str, Any] = {}

        def capture(status: str, headers: list[tuple[str, str]]) -> None:
            collected["status"] = status
            collected["headers"] = headers

        body = b"".join(
            self.api_app(dict(environ), capture)  # type: ignore[arg-type]
        )
        status_text = str(collected.get("status", "500 Internal Server Error"))
        try:
            status = int(status_text.split(" ", 1)[0])
        except ValueError:
            status = 500
        headers = [
            (key, value)
            for key, value in collected.get("headers", [])
            if key.lower()
            not in {
                "content-length",
                "x-content-type-options",
                "x-frame-options",
                "referrer-policy",
                "permissions-policy",
                "cross-origin-opener-policy",
            }
        ]
        return status, headers, body

    # -- HTML surfaces -----------------------------------------------------
    def _app(
        self, method: str, environ: Mapping[str, Any]
    ) -> tuple[int, list[tuple[str, str]], bytes]:
        if method not in {"GET", "HEAD"}:
            return _json(405, {"code": "METHOD_NOT_ALLOWED"}, cache="no-store")
        cookies = _cookie_values(environ)
        session = self.identity.resolve(cookies.get(SESSION_COOKIE_NAME, ""))
        if session is None:
            target = _safe_next(
                str(environ.get("PATH_INFO", APP_PATH))
                + (
                    f"?{environ.get('QUERY_STRING')}"
                    if environ.get("QUERY_STRING")
                    else ""
                )
            )
            return 302, [
                ("Location", f"{LOGIN_PATH}?{quote('next')}={quote(target)}"),
                ("Cache-Control", "no-store"),
            ], b""
        page = self.site.resolve("/app")
        if page is None:
            return _json(503, {"code": "APP_SHELL_MISSING"}, cache="no-store")
        return 200, [
            ("Content-Type", "text/html; charset=utf-8"),
            ("Cache-Control", "no-store"),
        ], page.read_bytes()

    def _workbench(
        self, method: str, environ: Mapping[str, Any]
    ) -> tuple[int, list[tuple[str, str]], bytes]:
        """Serve the AI Workbench document with a session gate.

        The document is only the shell: every workbench API call authorizes the
        project and tenant independently, so this gate never substitutes for
        server-side authorization.
        """
        if method not in {"GET", "HEAD"}:
            return _json(405, {"code": "METHOD_NOT_ALLOWED"}, cache="no-store")
        cookies = _cookie_values(environ)
        session = self.identity.resolve(cookies.get(SESSION_COOKIE_NAME, ""))
        if session is None:
            requested = str(environ.get("PATH_INFO", AI_WORKBENCH_PATH)) + (
                f"?{environ.get('QUERY_STRING')}" if environ.get("QUERY_STRING") else ""
            )
            target = _safe_next(requested)
            return 302, [
                ("Location", f"{LOGIN_PATH}?{quote('next')}={quote(target)}"),
                ("Cache-Control", "no-store"),
            ], b""
        page = self.site.resolve(AI_WORKBENCH_PATH)
        if page is None:
            return _json(503, {"code": "AI_WORKBENCH_SHELL_MISSING"}, cache="no-store")
        return 200, [
            ("Content-Type", "text/html; charset=utf-8"),
            ("Cache-Control", "no-store"),
        ], page.read_bytes()

    def _cubi(
        self, method: str, environ: Mapping[str, Any]
    ) -> tuple[int, list[tuple[str, str]], bytes]:
        """Serve the Enterprise document under /cubi/* with a session gate.

        The public home page and the sign-in card are anonymous. Every other
        Enterprise document requires a session; the API still authorizes each
        call independently, so this gate is only the document boundary.
        """
        if method not in {"GET", "HEAD"}:
            return _json(405, {"code": "METHOD_NOT_ALLOWED"}, cache="no-store")
        path = str(environ.get("PATH_INFO", CUBI_PATH))
        query = str(environ.get("QUERY_STRING", "") or "")
        normalized = path if path in CUBI_PUBLIC_PATHS else path.rstrip("/")
        if normalized not in CUBI_PUBLIC_PATHS:
            cookies = _cookie_values(environ)
            session = self.identity.resolve(cookies.get(SESSION_COOKIE_NAME, ""))
            if session is None:
                # Preserve the exact Enterprise document (and its query) the
                # visitor asked for. Replacing it with the bare /cubi/ entry
                # would silently drop a valid deep link after sign-in.
                requested = path + (f"?{query}" if query else "")
                target = _safe_next(requested)
                return 302, [
                    ("Location", f"{LOGIN_PATH}?{quote('next')}={quote(target)}"),
                    ("Cache-Control", "no-store"),
                ], b""
            roles = frozenset(getattr(session, "roles", ()) or ())
            if path.startswith(CUBI_ENTERPRISE_PREFIX) and not roles.intersection(
                ENTERPRISE_ACCESS_ROLES
            ):
                # The Enterprise data area requires an Enterprise entitlement.
                # The Workbench explains both environments and never pretends
                # the environment is available.
                return 303, [
                    ("Location", f"{WORKBENCH_PATH}/"),
                    ("Cache-Control", "no-store"),
                ], b""
        page = self.site.resolve(CUBI_PATH + "/")
        if page is None:
            return _json(503, {"code": "ENTERPRISE_SHELL_MISSING"}, cache="no-store")
        return 200, [
            ("Content-Type", "text/html; charset=utf-8"),
            ("Cache-Control", "no-store"),
        ], page.read_bytes()

    def _login_page(
        self, method: str, environ: Mapping[str, Any]
    ) -> tuple[int, list[tuple[str, str]], bytes]:
        if method not in {"GET", "HEAD"}:
            return _json(405, {"code": "METHOD_NOT_ALLOWED"}, cache="no-store")
        cookies = _cookie_values(environ)
        session = self.identity.resolve(cookies.get(SESSION_COOKIE_NAME, ""))
        query = parse_qs(str(environ.get("QUERY_STRING", "") or ""), keep_blank_values=True)
        if session is not None and query.get("reauth", [""])[0] not in {"1", "true"}:
            target = _safe_next(query.get("next", [""])[0])
            return 303, [
                ("Location", target),
                ("Cache-Control", "no-store"),
            ], b""
        page = self.site.resolve("/login.html")
        if page is None:
            return _json(503, {"code": "LOGIN_PAGE_MISSING"}, cache="no-store")
        return 200, [
            ("Content-Type", "text/html; charset=utf-8"),
            ("Cache-Control", "no-store"),
        ], page.read_bytes()

    def _static(
        self, method: str, path: str
    ) -> tuple[int, list[tuple[str, str]], bytes]:
        file = self.site.resolve(path)
        if file is None:
            return _json(404, {"code": "NOT_FOUND"}, cache="no-store")
        body = file.read_bytes()
        cache = (
            "public, max-age=31536000, immutable"
            if "/dist/" in path
            else "public, max-age=300, must-revalidate"
        )
        return 200, [
            ("Content-Type", _content_type(file)),
            ("Cache-Control", cache),
        ], body

    # -- origin ------------------------------------------------------------
    def _origin_allowed(self, environ: Mapping[str, Any]) -> bool:
        origin = _header(environ, "origin").rstrip("/")
        if origin:
            return origin == self.public_origin
        referer = _header(environ, "referer")
        if referer:
            try:
                split = urlsplit(referer)
            except ValueError:
                return False
            return f"{split.scheme}://{split.netloc}" == self.public_origin
        return False


def _json(
    status: int,
    payload: Mapping[str, object],
    *,
    cache: str = "no-store",
    extra: list[tuple[str, str]] | None = None,
) -> tuple[int, list[tuple[str, str]], bytes]:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    headers = [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Cache-Control", cache),
        *(extra or []),
    ]
    return status, headers, body


__all__ = [
    "APP_PATH",
    "ADMIN_PATH",
    "ENTERPRISE_PATH",
    "CUBI_PATH",
    "WORKBENCH_PATH",
    "WORKSPACE_PATHS",
    "CUBI_PUBLIC_PATHS",
    "LOGIN_PATH",
    "ProductionWebApp",
    "StaticSite",
]
