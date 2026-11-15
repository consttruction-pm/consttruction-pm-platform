"""Tests for the Vercel entrypoints in the ``apps/web`` project root.

The production Vercel project is rooted at ``apps/web``, so its functions live
in ``apps/web/api`` and import the runtime staged into ``vercel-runtime``.
These tests cover the bootstrap behaviour without a database: liveness must
stay honest, and every other route must report a configuration requirement
instead of pretending to be authenticated or ready.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
from pathlib import Path

import pytest

WEB_ROOT = Path(__file__).resolve().parents[1] / "apps" / "web"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    before = dict(os.environ)
    try:
        spec.loader.exec_module(module)
    finally:
        # The entrypoints default CUBI_WEB_ROOT for the deployed layout; never
        # leak that into the rest of the suite.
        os.environ.clear()
        os.environ.update(before)
    return module


@pytest.fixture()
def unconfigured(monkeypatch):
    for name in (
        "CONSTRUCTION_PM_DATABASE_URL",
        "CONSTRUCTION_PM_SESSION_SECRET",
        "CONSTRUCTION_PM_PUBLIC_ORIGIN",
    ):
        monkeypatch.delenv(name, raising=False)
    from construction_pm.deployment import production_runtime

    monkeypatch.setattr(production_runtime, "_RUNTIME", None)
    return (
        ¶»§q«^