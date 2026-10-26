"""Local full-stack HTTP surface for the CUBI preview.

This module only translates HTTP. Authentication decisions stay in the real
lifecycle service, scheduling stays in the Shared Domain/Calculation Core and
the browser assets are the real built Web client. The preview adds exactly two
things: a fixture-only demo login (there is no production login here) and a
guard that keeps the workspace shell behind that demo session.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import sys
import traceback
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Iterable, Mapping
from urllib.parse import parse_qs, urlsplit

from construction_pm.application.project_lifecycle import AuthenticatedSession

from .runtime import PreviewRuntime, PreviewRuntimeError, open_preview_runtime
from .storage import (
    DEMO_USERS,
    DEMO_USERS_BY_ROLE,
    PREVIEW_SESSION_TTL,
)

SESSION_COOKIE = "cp_session"
LOGIN_PATH = "/preview/login"
LOGOUT_PATH = "/preview/logout"
HEALTH_PATH = "/preview/health"

_ALLOWED_ROOT_FILES = {
    "index.html",
    "styles.css",
    "cubi-platform-logo-primary.svg",
    "cubi-hero-field.svg",
    "favicon.ico",
}
_ALLOWED_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".map": "application/json; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".otf": "font/otf",
    ".ttf": "font/ttf",
    ".txt": "text/plain; charset=utf-8",
    ".webmanifest": "application/manifest+json",
}

def _json(status: int, payload: Mapping[str, object]) -> tuple[int, dict[str, str], bytes]:
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return status, {"Content-Type": "application/json; charset=utf-8"}, body


def _html(status: int, document: str) -> tuple[int, dict[str, str], bytes]:
    return status, {"Content-Type": "text/html; charset=utf-8"}, document.encode("utf-8")


def _safe_next(raw: object) -> str:
    value = str(raw or "").strip()
    if value in {"/app", "/app/"}:
        return "/app"
    return "/app"


def _cookie_header(session: AuthenticatedSession) -> tuple[str, str]:
    max_age = int(PREVIEW_SESSION_TTL.total_seconds())
    value = (
        f"{SESSION_COOKIE}={session.session_id}; Path=/; HttpOnly; SameSite=Lax; "
        f"Max-Age={max_age}"
    )
    return "Set-Cookie", value


def _clear_cookie_header() -> tuple[str, str]:
    return "Set-Cookie", f"{SESSION_COOKIE}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"


def _session_from_environ(runtime: PreviewRuntime, environ: Mapping[str, object]) -> AuthenticatedSession | None:
    raw = str(environ.get("HTTP_COOKIE", "") or "")
    if not raw:
        return None
    cookies = SimpleCookie()
    try:
        cookies.load(raw)
    except Exception:
        return None
    morsel = cookies.get(SESSION_COOKIE)
    if morsel is None or not morsel.value:
        return None
    return runtime.sessions.get(morsel.value)


def _wants_json(environ: Mapping[str, object]) -> bool:
    return str(environ.get("PATH_INFO", "")).startswith("/api/")


class PreviewFrontend:
    """Explicit, non-traversable static file mapping for the built Web client."""

    def __init__(self, web_root: Path) -> None:
        self.root = Path(web_root).expanduser().resolve()
        self.dist = self.root / "dist"
        self.public = self.root / "public"
        if not (self.dist / "web" / "src" / "landing-entry.js").is_file():
            raise PreviewRuntimeError(
                "PREVIEW_WEB_BUILD_MISSING",
                "The Web client is not built. Run `npm run build` in apps/web first.",
            )

    def resolve(self, request_path: str) -> Path | None:
        raw = urlsplit(request_path).path
        try:
            pathname = raw.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pathname = raw
        if not pathname.startswith("/"):
            return None
        segments = [segment for segment in pathname.split("/") if segment]
        if any(segment in {".", ".."} or segment.startswith(".") for segment in segments):
            return None
        try:
            return self._resolve_segments(segments)
        except (OSError, ValueError):
            return None

    def _resolve_segments(self, segments: list[str]) -> Path | None:
        if not segments:
            return self._file(self.root / "index.html")
        if segments == ["app"] or segments == ["app", "index.html"]:
            return self._file(self.root / "app.html")
        if segments == ["app.html"]:
            return self._file(self.root / "app.html")
        if segments[0] == "dist":
            rest = segments[1:]
            if not rest:
                return None
            if rest[0] in {"web", "client-sync"}:
                candidate = self.dist.joinpath(*rest)
            else:
                candidate = self.dist.joinpath("web", "src", *rest)
            return self._file(candidate)
        if segments[:2] == ["client-sync", "src"]:
            return self._file(self.dist.joinpath("client-sync", "src", *segments[2:]))
        if len(segments) == 1 and segments[0] in _ALLOWED_ROOT_FILES:
            return self._file(self.root / segments[0])
        if segments[0] == "public":
            if len(segments) < 2:
                return None
            return self._file(self.public.joinpath(*segments[1:]))
        public_candidate = self.public.joinpath(*segments)
        resolved = self._file(public_candidate)
        if resolved is not None:
            return resolved
        directory = public_candidate
        if directory.is_dir():
            return self._file(directory / "index.html")
        return None

    @staticmethod
    def _file(candidate: Path) -> Path | None:
        if not candidate.is_file():
            return None
        if candidate.suffix.lower() not in _ALLOWED_CONTENT_TYPES:
            return None
        return candidate


class PreviewApplication:
    """Small WSGI wrapper around the real CUBI WSGI application."""

    def __init__(self, runtime: PreviewRuntime) -> None:
        if runtime.web_root is None:
            raise PreviewRuntimeError(
                "PREVIEW_WEB_ROOT_REQUIRED",
                "A full-stack preview requires the built Web root.",
            )
        self.runtime = runtime
        self.frontend = PreviewFrontend(runtime.web_root)

    def __call__(self, environ: dict[str, object], start_response):
        method = str(environ.get("REQUEST_METHOD", "GET")).upper()
        path = urlsplit(str(environ.get("PATH_INFO", "/"))).path
        session = _session_from_environ(self.runtime, environ)

        try:
            if path == HEALTH_PATH and method in {"GET", "HEAD"}:
                status, headers, body = _json(200, self._health())
            elif path == LOGIN_PATH:
                status, headers, body = self._login(method, environ, session)
            elif path == LOGOUT_PATH:
                status, headers, body = self._logout(method, environ, session)
            elif path.startswith("/api/"):
                status, headers, body = self._delegate(environ)
                if status == 404 and body.strip() == b'{"code":"ROUTE_NOT_FOUND"}':
                    status, headers, body = _json(404, {"code": "ROUTE_NOT_FOUND"})
            elif path == "/app" or path.startswith("/app/") or path == "/app.html":
                status, headers, body = self._app_shell(environ, session)
            else:
                status, headers, body = self._static(path, method)
        except PreviewRuntimeError as exc:
            status, headers, body = _json(500, {"code": exc.code, "message": str(exc)})
        except Exception:
            traceback.print_exc()
            if _wants_json(environ):
                status, headers, body = _json(
                    500,
                    {"code": "PREVIEW_INTERNAL_ERROR", "message": "Unexpected preview server error."},
                )
            else:
                status, headers, body = _html(
                    500,
                    "<!doctype html><html><body><h1>Preview error</h1>"
                    "<p>The local preview server failed. See the terminal output.</p>"
                    "</body></html>",
                )

        if method == "HEAD":
            body = b""
        response_headers: list[tuple[str, str]] = list(headers.items())
        response_headers.extend([
            ("Content-Length", str(len(body))),
            ("Cache-Control", "no-store"),
            ("X-Content-Type-Options", "nosniff"),
            ("X-Frame-Options", "DENY"),
            ("Referrer-Policy", "no-referrer"),
        ])
        start_response(self._status_text(status), response_headers)
        return [body]

    def _health(self) -> dict[str, object]:
        health = self.runtime.health()
        health.update(
            {
                "production": False,
                "demo_data": True,
                "database": str(self.runtime.database),
                "web_root": str(self.runtime.web_root),
            }
        )
        return health

    def _login(
        self,
        method: str,
        environ: Mapping[str, object],
        session: AuthenticatedSession | None,
    ) -> tuple[int, dict[str, str], bytes]:
        if method == "GET":
            if session is not None:
                return _html(200, self._login_page(session=session))
            return _html(200, self._login_page())
        if method != "POST":
            return _json(405, {"code": "METHOD_NOT_ALLOWED"})
        length = _content_length(environ)
        if length is None:
            return _json(400, {"code": "PREVIEW_LOGIN_REQUEST_INVALID"})
        stream = environ.get("wsgi.input")
        raw = stream.read(length) if length and hasattr(stream, "read") else b""
        try:
            values = parse_qs(raw.decode("utf-8"), keep_blank_values=True)
        except UnicodeDecodeError:
            return _json(400, {"code": "PREVIEW_LOGIN_REQUEST_INVALID"})
        role = str((values.get("role") or [""])[0]).strip()
        user = DEMO_USERS_BY_ROLE.get(role)
        if user is None:
            return _html(
                400,
                self._login_page(error="Select one of the demo roles below."),
            )
        next_path = _safe_next((values.get("next") or [""])[0])
        created = self.runtime.sessions.create(user)
        headers = {
            "Content-Type": "text/html; charset=utf-8",
            "Location": next_path,
            "Set-Cookie": _cookie_header(created)[1],
        }
        return 303, headers, b""

    def _logout(
        self,
        method: str,
        environ: Mapping[str, object],
        session: AuthenticatedSession | None,
    ) -> tuple[int, dict[str, str], bytes]:
        if method != "POST":
            return _json(405, {"code": "METHOD_NOT_ALLOWED"})
        if session is not None:
            self.runtime.sessions.revoke(session.session_id)
        headers = {
            "Content-Type": "text/html; charset=utf-8",
            "Location": LOGIN_PATH,
            "Set-Cookie": _clear_cookie_header()[1],
        }
        return 303, headers, b""

    def _delegate(self, environ: dict[str, object]) -> tuple[int, dict[str, str], bytes]:
        captured: dict[str, object] = {}

        def start_response(status: str, headers: list[tuple[str, str]]) -> None:
            captured["status"] = status
            captured["headers"] = headers

        body = b"".join(self.runtime.app(environ, start_response))
        status_text = str(captured.get("status", "500 Internal Server Error"))
        try:
            status = int(status_text.split(" ", 1)[0])
        except ValueError:
            status = 500
        raw_headers = captured.get("headers") or []
        headers: dict[str, str] = {}
        for key, value in raw_headers:
            if key.lower() == "content-length":
                continue
            headers[key] = value
        return status, headers, body

    def _app_shell(
        self,
        environ: Mapping[str, object],
        session: AuthenticatedSession | None,
    ) -> tuple[int, dict[str, str], bytes]:
        if session is None:
            headers = {
                "Content-Type": "text/html; charset=utf-8",
                "Location": f"{LOGIN_PATH}?next=%2Fapp",
            }
            return 302, headers, b""
        shell = (self.frontend.root / "app.html").read_text(encoding="utf-8")
        banner = self._banner(session)
        if "</body>" in shell:
            shell = shell.replace("</body>", f"{banner}\n  </body>", 1)
        else:
            shell = shell + banner
        return 200, {"Content-Type": "text/html; charset=utf-8"}, shell.encode("utf-8")

    def _static(self, path: str, method: str) -> tuple[int, dict[str, str], bytes]:
        if method not in {"GET", "HEAD"}:
            return _json(405, {"code": "METHOD_NOT_ALLOWED"})
        file = self.frontend.resolve(path)
        if file is None:
            return _html(
                404,
                "<!doctype html><html><body><h1>Not found</h1>"
                "<p><a href=\"/\">CUBI preview home</a></p></body></html>",
            )
        content_type = _ALLOWED_CONTENT_TYPES.get(file.suffix.lower(), "application/octet-stream")
        body = file.read_bytes()
        return 200, {"Content-Type": content_type}, body

    def _login_page(
        self,
        *,
        session: AuthenticatedSession | None = None,
        error: str | None = None,
    ) -> str:
        if session is not None:
            user_id = html.escape(session.user_id)
            return f"""<!doctype html>
<html lang="en" dir="ltr">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>CUBI preview session</title>
<style>{_LOGIN_CSS}</style></head>
<body><main class="card">
<p class="eyebrow">Local full-stack preview</p>
<h1>You are signed in</h1>
<p>Demo identity <code>{user_id}</code> is active for this browser tab. The session lasts eight hours and is not a production credential.</p>
<p><a class="primary" href="/app">Open the CUBI workspace</a></p>
<form method="post" action="{LOGOUT_PATH}"><button class="secondary" type="submit">Sign out</button></form>
</main></body></html>"""
        cards = []
        for user in DEMO_USERS:
            label = html.escape(user.label_en)
            fa = html.escape(user.label_fa)
            role = html.escape(user.role)
            description = {
                "planner": "Read projects, edit activities, save layouts and publish schedule snapshots.",
                "viewer": "Read-only project access. Writes are denied by the server.",
                "admin": "Planner capabilities plus project creation.",
            }[user.role]
            cards.append(
                f"""<form method="post" action="{LOGIN_PATH}" class="persona">
<button type="submit" name="role" value="{role}">
<span class="name">{label} <span class="fa" lang="fa" dir="rtl">{fa}</span></span>
<span class="desc">{html.escape(description)}</span>
</button></form>"""
            )
        error_block = (
            f'<p class="error" role="alert">{html.escape(error)}</p>' if error else ""
        )
        return f"""<!doctype html>
<html lang="en" dir="ltr">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>CUBI local full-stack preview</title>
<style>{_LOGIN_CSS}</style></head>
<body><main class="card">
<p class="eyebrow">CUBI · local full-stack preview</p>
<h1>Choose a demo identity</h1>
<p class="lede">This page exists only on the local preview server. There is no password and no production identity. Each role is enforced by the real CUBI authorization policy after login.</p>
{error_block}
<div class="personas">{''.join(cards)}</div>
<p class="notice"><strong>Demo data:</strong> two fixture projects are seeded into a guarded local SQLite database. The workspace reads and recalculates through the real WSGI API and Shared Domain/Calculation Core. No production system is contacted.</p>
<p class="notice fa-note" lang="fa" dir="rtl">این صفحه فقط برای پیش‌نمایش محلی است؛ دادهٔ نمایشی و نقش‌های آزمایشی است و به محیط تولید متصل نیست.</p>
<p class="meta">Seed: cubi-preview-seed.v1 · <a href="/preview/health">health</a> · <a href="/">landing page</a></p>
</main></body></html>"""

    def _banner(self, session: AuthenticatedSession) -> str:
        role = "viewer"
        for user in DEMO_USERS:
            if user.user_id == session.user_id:
                role = user.role
                break
        user_id = html.escape(session.user_id)
        role = html.escape(role)
        return f"""<style>
  #cubi-preview-banner {{
    position: fixed; inset: auto 0 0 0; z-index: 2147483000;
    display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: center;
    padding: 7px 14px; background: #12263f; color: #f7fbff;
    font: 12px/1.4 system-ui, -apple-system, "Segoe UI", sans-serif;
    box-shadow: 0 -1px 0 rgba(255,255,255,.18);
  }}
  #cubi-preview-banner strong {{ color: #ffd166; letter-spacing: .04em; }}
  #cubi-preview-banner .fa {{ direction: rtl; unicode-bidi: isolate; }}
  #cubi-preview-banner .grow {{ flex: 1 1 auto; }}
  #cubi-preview-banner form {{ margin: 0; }}
  #cubi-preview-banner button {{
    border: 1px solid rgba(255,255,255,.5); background: transparent; color: inherit;
    border-radius: 4px; padding: 2px 9px; cursor: pointer; font: inherit;
  }}
</style>
<div id="cubi-preview-banner" role="status">
  <strong>LOCAL PREVIEW · DEMO DATA · NOT PRODUCTION</strong>
  <span class="fa">پیش‌نمایش محلی — دادهٔ نمایشی — محیط تولید نیست</span>
  <span class="grow">Signed in as <b>{user_id}</b> ({role})</span>
  <form method="post" action="{LOGOUT_PATH}"><button type="submit">Sign out</button></form>
</div>
<style>body {{ padding-bottom: 46px; }}</style>"""

    @staticmethod
    def _status_text(status: int) -> str:
        reasons = {
            200: "OK",
            201: "Created",
            302: "Found",
            303: "See Other",
            304: "Not Modified",
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            405: "Method Not Allowed",
            409: "Conflict",
            413: "Payload Too Large",
            500: "Internal Server Error",
            502: "Bad Gateway",
        }
        return f"{status} {reasons.get(status, 'Response')}"


def _content_length(environ: Mapping[str, object]) -> int | None:
    raw = str(environ.get("CONTENT_LENGTH", "0") or "0")
    try:
        length = int(raw)
    except ValueError:
        return None
    if length < 0 or length > 64 * 1024:
        return None
    return length


_LOGIN_CSS = """
:root { color-scheme: dark; }
* { box-sizing: border-box; }
body {
  margin: 0; min-height: 100vh; display: grid; place-items: center; padding: 28px 16px;
  background: radial-gradient(circle at 20% 0%, #1d4468 0%, #081a2f 46%, #050f1c 100%);
  color: #f3f8ff; font: 15px/1.55 system-ui, -apple-system, "Segoe UI", sans-serif;
}
.card {
  width: min(760px, 100%); padding: 32px; border-radius: 18px;
  border: 1px solid rgba(255,255,255,.14);
  background: rgba(8, 26, 47, .88); box-shadow: 0 30px 80px rgba(0,0,0,.4);
}
.eyebrow { margin: 0 0 10px; color: #7fd1ff; font-size: 12px; letter-spacing: .14em; text-transform: uppercase; }
h1 { margin: 0 0 12px; font-size: clamp(26px, 4vw, 34px); line-height: 1.15; }
.lede { margin: 0 0 20px; color: #c5d6e8; }
.personas { display: grid; gap: 10px; margin: 22px 0; }
.persona button {
  width: 100%; text-align: left; cursor: pointer; color: inherit;
  border: 1px solid rgba(127, 209, 255, .32); border-radius: 12px;
  background: linear-gradient(180deg, rgba(30, 76, 118, .55), rgba(14, 39, 66, .55));
  padding: 15px 18px; display: grid; gap: 4px; font: inherit;
}
.persona button:hover, .persona button:focus-visible { outline: 2px solid #7fd1ff; outline-offset: 2px; }
.persona .name { font-weight: 700; font-size: 16px; }
.persona .fa { color: #9fc6e8; font-weight: 500; }
.persona .desc { color: #bed2e6; font-size: 13px; }
.notice { color: #a9bfd4; font-size: 13px; border-left: 3px solid #7fd1ff; padding-left: 12px; }
.fa-note { border-left: 0; border-right: 3px solid #7fd1ff; padding-left: 0; padding-right: 12px; }
.error { color: #ffb3b3; border: 1px solid #b54848; border-radius: 8px; padding: 10px 12px; }
.meta { color: #8fa8be; font-size: 12px; margin-bottom: 0; }
a { color: #8fd6ff; }
.primary {
  display: inline-block; margin: 6px 0 16px; padding: 10px 16px; border-radius: 8px;
  background: #0c8bcc; color: #fff; text-decoration: none; font-weight: 700;
}
.secondary {
  border: 1px solid rgba(255,255,255,.4); background: transparent; color: inherit;
  border-radius: 8px; padding: 8px 14px; font: inherit; cursor: pointer;
}
code { color: #ffd166; }
"""


def build_preview_application(runtime: PreviewRuntime) -> PreviewApplication:
    return PreviewApplication(runtime)


def serve_preview(
    runtime: PreviewRuntime,
    *,
    host: str = "127.0.0.1",
    port: int = 4174,
) -> None:
    from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

    class RequestHandler(WSGIRequestHandler):
        # A dropped or idle browser connection must not block the single-threaded
        # preview server forever while it waits for another request line.
        timeout = 10

        def log_message(self, format: str, *args) -> None:  # noqa: A002
            sys.stderr.write(
                "%s - [%s] %s\n"
                % (self.address_string(), self.log_date_time_string(), format % args)
            )

    class PreviewServer(WSGIServer):
        # The Web client loads a module graph in parallel. The default listen
        # backlog of five can strand connections when a page reloads.
        request_queue_size = 64

    app = build_preview_application(runtime)
    server = make_server(
        host,
        port,
        app,
        server_class=PreviewServer,
        handler_class=RequestHandler,
    )
    display_host = host if host not in {"0.0.0.0", "::"} else "localhost"
    print("CUBI local full-stack preview (demo data, not production)")
    print(f"  URL:      http://{display_host}:{port}/")
    print(f"  Login:    http://{display_host}:{port}{LOGIN_PATH}")
    print(f"  Health:   http://{display_host}:{port}{HEALTH_PATH}")
    print(f"  Database: {runtime.database}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping CUBI local preview.")
    finally:
        server.server_close()


def _default_database() -> Path:
    root = Path(__file__).resolve().parents[3]
    return root / ".preview" / "cubi-preview.sqlite3"


def _default_web_root() -> Path:
    return Path(__file__).resolve().parents[3] / "apps" / "web"


def _is_loopback(host: str) -> bool:
    return host in {"127.0.0.1", "localhost", "::1"}


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cubi-preview",
        description=(
            "Run the CUBI Web client with the real WSGI API, SQLite persistence "
            "and Shared Domain/Calculation Core on a local demo database."
        ),
    )
    parser.add_argument("--database", type=Path, default=_default_database())
    parser.add_argument("--web-root", type=Path, default=_default_web_root())
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4174)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Back up the recognised preview database and rebuild the demo seed.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if not _is_loopback(args.host) and os.environ.get("CUBI_PREVIEW_ALLOW_LAN") != "1":
        print(
            "Refusing to expose the demo login to a non-loopback address. "
            "The preview has no production authentication. Set "
            "CUBI_PREVIEW_ALLOW_LAN=1 only on a trusted machine.",
            file=sys.stderr,
        )
        return 2
    if not (args.web_root / "dist" / "web" / "src" / "landing-entry.js").is_file():
        print(
            f"Web build not found under {args.web_root}. Run `npm run build` in apps/web first.",
            file=sys.stderr,
        )
        return 2

    try:
        runtime = open_preview_runtime(
            args.database,
            web_root=args.web_root,
            reset=args.reset,
        )
    except PreviewRuntimeError as exc:
        print(f"Preview startup failed [{exc.code}]: {exc}", file=sys.stderr)
        return 1

    try:
        serve_preview(runtime, host=args.host, port=args.port)
    finally:
        runtime.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
