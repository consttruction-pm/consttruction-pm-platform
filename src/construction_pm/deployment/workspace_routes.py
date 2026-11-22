"""Resolve the canonical workspace route behind a Vercel rewrite.

Vercel maps the document routes (``/app``, ``/workbench``, ``/admin``,
``/enterprise``, ``/cubi/*`` and ``/ai-workbench/*``) onto the same function and carries the original
route in the ``__path`` query. This module decides which document the HTTP
boundary must see. It is shared by both Vercel entrypoints so a route can never
silently fall back to the Engineering shell.

Only these documents are accepted. An unknown or malformed ``__path`` falls
back to ``/app``; it never becomes a path outside the workspace family.
"""

from __future__ import annotations

from typing import Mapping
from urllib.parse import parse_qs

WORKSPACE_ROUTES = (
    "app",
    "enterprise",
    "cubi",
    "ai-workbench",
    # The Personal Workbench and the global administration panel are documents
    # of the same session-gated workspace family. They ship no static file, so
    # the deployment rewrites them here; without these segments Vercel answers
    # NOT_FOUND for /workbench/ and /admin before the identity boundary runs.
    "workbench",
    "admin",
)
FALLBACK_PATH = "/app"

# The old ``/enterprise`` address is still accepted so the HTTP boundary can
# redirect it to the canonical Enterprise document. It never serves the
# Engineering shell.
LEGACY_ENTERPRISE_PATHS = frozenset({"/enterprise", "/enterprise/"})


def _normalized_segments(value: str) -> list[str] | None:
    candidate = value.split("?", 1)[0]
    if not candidate.startswith("/"):
        candidate = "/" + candidate
    segments = [segment for segment in candidate.split("/") if segment]
    if not segments:
        return None
    if any(
        segment in {".", ".."}
        or segment.startswith(".")
        or any(ord(character) < 0x20 for character in segment)
        for segment in segments
    ):
        return None
    if segments[0] not in WORKSPACE_ROUTES:
        return None
    return segments


def resolve_workspace_path(environ: Mapping[str, object]) -> str:
    """Return the canonical document path the request actually addressed."""

    rewritten = parse_qs(str(environ.get("QUERY_STRING", "") or "")).get("__path")
    if rewritten:
        segments = _normalized_segments(rewritten[0])
        if segments is not None:
            return "/" + "/".join(segments)
    original = str(environ.get("PATH_INFO", "") or "")
    segments = _normalized_segments(original)
    if segments is not None:
        return "/" + "/".join(segments)
    if original.rstrip("/") in {path.rstrip("/") for path in LEGACY_ENTERPRISE_PATHS}:
        return "/enterprise"
    return FALLBACK_PATH


def query_without_rewrite(environ: Mapping[str, object]) -> str:
    """Drop the platform ``__path`` marker before the HTTP boundary sees it.

    The marker belongs to the rewrite, not to the user's query. Leaving it in
    place would append it to the document query and to the post-login ``next``
    target.
    """

    from urllib.parse import quote

    values = parse_qs(
        str(environ.get("QUERY_STRING", "") or ""), keep_blank_values=True
    )
    marker = values.pop("__path", None)
    # Vercel also exposes the matched ``:path*`` segment as a query parameter
    # named ``path``. It is a copy of the route, not user input: leaving it in
    # place makes /app/wbs/ look like a stray query and collapses the deep link
    # to /app. Drop it only when it reproduces the rewritten tail exactly.
    if marker:
        tail = marker[0].split("?", 1)[0].strip("/")
        tail = tail.split("/", 1)[1] if "/" in tail else ""
        copied = values.get("path")
        if tail and copied and len(copied) == 1 and copied[0].rstrip("/") == tail:
            values.pop("path", None)
    return "&".join(
        f"{quote(key)}={quote(value)}"
        for key, items in values.items()
        for value in items
    )


__all__ = [
    "WORKSPACE_ROUTES",
    "FALLBACK_PATH",
    "resolve_workspace_path",
    "query_without_rewrite",
]
