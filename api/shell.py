"""Vercel entrypoint for the session-gated workspace documents.

Vercel rewrites ``/app``, ``/enterprise``, ``/cubi/*`` and ``/ai-workbench/*``
onto this function and carries the original route in ``__path``. The canonical
route must be restored before the HTTP boundary runs; otherwise every
environment would silently become the Engineering shell.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from construction_pm.deployment.production_runtime import get_runtime  # noqa: E402
from construction_pm.deployment.workspace_routes import (  # noqa: E402
    query_without_rewrite,
    resolve_workspace_path,
)


def app(environ, start_response):
    scoped = dict(environ)
    scoped["PATH_INFO"] = resolve_workspace_path(environ)
    scoped["QUERY_STRING"] = query_without_rewrite(environ)
    return get_runtime()(scoped, start_response)
