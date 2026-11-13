"""Vercel entrypoint for the CUBI production API.

Vercel rewrites every ``/api/*`` request to this function and carries the
original path in ``__path``. The WSGI application is the same composition the
local conformance tests exercise; no preview adapter is reachable here.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from construction_pm.deployment.production_runtime import get_runtime  # noqa: E402


def app(environ, start_response):
    return get_runtime()(environ, start_response)
