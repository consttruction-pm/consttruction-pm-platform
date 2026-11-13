"""Vercel entrypoint for the session-gated ``/app`` workspace shell."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from construction_pm.deployment.production_runtime import get_runtime  # noqa: E402


def app(environ, start_response):
    scoped = dict(environ)
    scoped["PATH_INFO"] = "/app"
    return get_runtime()(scoped, start_response)
