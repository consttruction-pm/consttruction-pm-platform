"""Vercel entrypoint for the CUBI production API.

The Vercel project is rooted at ``apps/web``; ``vercel-runtime`` is staged by
``scripts/prepare-vercel-runtime.mjs`` during the build and contains the
unmodified repository runtime. Requests arrive here through the
``/api/:path*`` rewrite, which carries the original route in ``__path``.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.parse import parse_qs

_WEB_ROOT = Path(__file__).resolve().parents[1]
_RUNTIME = _WEB_ROOT / "vercel-runtime"
sys.path.insert(0, str(_RUNTIME / "src"))
os.environ.setdefault("CUBI_WEB_ROOT", str(_RUNTIME / "webroot"))

try:  # pragma: no cover - exercised by the Vercel function
    from construction_pm.deployment.production_runtime import get_runtime
except Exception as error:  # noqa: BLE001 - report, never leak details
    get_runtime = None  # type: ignore[assignment]
    _IMPORT_FAILURE = type(error).__name__


def _json(start_response, status: int, payload: dict[str, object]):
    body = json.dumps(payload).encode("utf-8")
    start_response(
        f"{status} {'OK' if status == 200 else 'Service Unavailable'}",
        [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body))),
            ("Cache-Control", "no-store"),
            ("X-Content-Type-Options", "nosniff"),
            ("X-Frame-Options", "DENY"),
            ("Referrer-Policy", "no-referrer"),
        ],
    )
    return [body]


def _unavailable(environ, start_response):
    route = str(environ.get("PATH_INFO", "/"))
    rewritten = parse_qs(str(environ.get("QUERY_STRING", "") or "")).get("__path")
    if rewritten:
        route = "/api/" + rewritten[0].lstrip("/")
    if route == "/api/health/live":
        return _json(start_response, 200, {"status": "ok"})
    return _json(
        start_response,
        503,
        {"status": "not_ready", "code": "CONFIGURATION_REQUIRED"},
    )


def app(environ, start_response):
    if get_runtime is None:
        print(f"cubi: runtime import failed ({_IMPORT_FAILURE})", file=sys.stderr)
        return _unavailable(environ, start_response)
    try:
        runtime = get_runtime()
    except Exception as error:  # noqa: BLE001 - configuration is optional input
        print(f"cubi: runtime configuration failed ({type(error).__name__})", file=sys.stderr)
        return _unavailable(environ, start_response)
    return runtime(environ, start_response)
