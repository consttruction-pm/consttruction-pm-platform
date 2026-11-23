"""Canonical identity of the shared reference dataset.

The three reference projects are defined by the frozen import bundle, not by a
hard-coded list in a view or a prefix heuristic. This module reads only the
bundle's project keys and is deliberately free of the heavy persistence,
scheduling and spreadsheet imports so that request-path code can ask "is this a
reference project?" without loading the importer.
"""

from __future__ import annotations

import gzip
import json
from functools import lru_cache
from pathlib import Path

BUNDLE_CONTRACT = "cubi-reference-import-bundle.v1"
DEFAULT_BUNDLE_PATH = (
    Path(__file__).resolve().parent / "data" / "cubi_reference_projects.v1.json.gz"
)


class ReferenceCatalogError(RuntimeError):
    """The frozen bundle is missing or does not satisfy its contract."""

    def __init__(self, code: str, message: str = "") -> None:
        self.code = code
        super().__init__(message or code)


@lru_cache(maxsize=1)
def reference_project_ids() -> tuple[str, ...]:
    """Return the project ids of the frozen reference bundle, sorted."""

    try:
        with gzip.open(DEFAULT_BUNDLE_PATH, "rt", encoding="utf-8") as handle:
            payload = json.load(handle)
    except OSError as exc:
        raise ReferenceCatalogError("REFERENCE_BUNDLE_UNAVAILABLE", str(exc)) from exc
    if payload.get("contract") != BUNDLE_CONTRACT:
        raise ReferenceCatalogError("REFERENCE_BUNDLE_CONTRACT_UNSUPPORTED")
    projects = payload.get("projects")
    if not isinstance(projects, dict) or not projects:
        raise ReferenceCatalogError("REFERENCE_BUNDLE_EMPTY")
    return tuple(sorted(str(project_id) for project_id in projects))


def is_reference_project(project_id: str) -> bool:
    return project_id in reference_project_ids()
