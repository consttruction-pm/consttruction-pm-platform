"""Vercel entrypoint for the isolated, session-gated Enterprise environment."""

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


def _preview_selected() -> bool:
    def value(name: str) -> str:
        return os.environ.get(name, "").strip().lower()

    if value("VERCEL_ENV") == "production" or value("VERCEL_TARGET_ENV") == "production":
        return False
    return value("CUBI_PREVIEW_RUNTIME") in {"1", "true", "yes"} or value("VERCEL_ENV") == "preview"


def _unavailable(start_response, message: str = "CUBI Enterprise is not configured on this deployment."):
    body = (
        "<!doctype html><html lang=\"en\"><meta charset=\"utf-8\">"
        "<title>CUBI Enterprise Unavailable</title>"
        f"<p>{message}</p>"
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
    scoped["PATH_INFO"] = "/enterprise"
    if _preview_selected():
        return _unavailable(start_response, "CUBI Enterprise is not available in this preview.")
    if get_runtime is None:
        print(f"cubi: enterprise runtime import failed ({_IMPORT_FAILURE})", file=sys.stderr)
        return _unavailable(start_response)
    try:
        runtime = get_runtime()
    except Exception as error:  # noqa: BLE001 - configuration is optional input
        print(f"cubi: enterprise runtime configuration failed ({type(error).__name__})", file=sys.stderr)
        return _unavailable(start_response)
    return runtime(scoped, start_response)
