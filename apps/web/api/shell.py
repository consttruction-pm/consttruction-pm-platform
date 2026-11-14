"""Vercel entrypoint for the session-gated ``/app`` workspace shell.

On a preview deployment the shell is served by the fixture-backed preview
runtime, which keeps the same ``/app`` route and the same built Web client but
uses the demo fixtures instead of PostgreSQL.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_WEB_ROOT = Path(__file__).resolve().parents[1]
_RUNTIME = _WEB_ROOT / "vercel-runtime"
sys.path.insert(0, str(_RUNTIME / "src"))
os.environ.setdefault("CUBI_WEB_ROOT", str(_RUNTIME / "webroot"))

try:  # pragma: no cover - exercised by the Vercel function
    from construction_pm.deployment.production_runtime import get_runtime
except Exception as error:  # noqa: BLE001 - report, never leak details
    get_runtime = None  # type: ignore[assignment]
    _IMPORT_FAILURE = type(error).__name__

_preview_app = None


def _preview_selected() -> bool:
    """True only for an explicitly non-production preview deployment."""

    def value(name: str) -> str:
        return os.environ.get(name, "").strip().lower()

    if value("VERCEL_ENV") == "production" or value("VERCEL_TARGET_ENV") == "production":
        return False
    if value("CUBI_PREVIEW_RUNTIME") in {"1", "true", "yes"}:
        return True
    return value("VERCEL_ENV") == "preview"


def _unavailable(start_response):
    body = (
        "<!doctype html><html lang=\"en\"><meta charset=\"utf-8\">"
        "<title>CUBI Unavailable</title>"
        "<p>CUBI is not configured on this deployment.</p>"
    ).encode("utf-8")
    start_response(
        "503 Service Unavailable",
        [
            ("Content-Type", "text/html; charset=utf-8"),
            ("Content-Length", str(len(body))),
            ("Cache-Control", "no-store"),
            ("X-Content-Type-Options", "nosniff"),
            ("X-Frame-Options", "DENY"),
            ("Referrer-Policy", "no-referrer"),
        ],
    )
    return [body]


def app(environ, start_response):
    scoped = dict(environ)
    scoped["PATH_INFO"] = "/app"
    if _preview_selected():
        global _preview_app
        try:
            if _preview_app is None:
                from construction_pm.deployment.vercel_preview import get_preview_application

                _preview_app = get_preview_application()
            return _preview_app(scoped, start_response)
        except Exception as error:  # noqa: BLE001 - keep preview failures explicit
            print(f"cubi: preview shell failed ({type(error).__name__})", file=sys.stderr)
            return _unavailable(start_response)
    if get_runtime is None:
        print(f"cubi: runtime import failed ({_IMPORT_FAILURE})", file=sys.stderr)
        return _unavailable(start_response)
    try:
        runtime = get_runtime()
    except Exception as error:  # noqa: BLE001 - configuration is optional input
        print(f"cubi: runtime configuration failed ({type(error).__name__})", file=sys.stderr)
        return _unavailable(start_response)
    return runtime(scoped, start_response)
