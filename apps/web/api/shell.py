"""Vercel entrypoint for the session-gated ``/app`` workspace shell."""

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
    if get_runtime is None:
        print(f"cubi: runtime import failed ({_IMPORT_FAILURE})", file=sys.stderr)
        return _unavailable(start_response)
    try:
        runtime = get_runtime()
    except Exception as error:  # noqa: BLE001 - configuration is optional input
        print(f"cubi: runtime configuration failed ({type(error).__name__})", file=sys.stderr)
        return _unavailable(start_response)
    scoped = dict(environ)
    scoped["PATH_INFO"] = "/app"
    return runtime(scoped, start_response)
