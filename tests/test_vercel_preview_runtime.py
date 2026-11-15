"""Tests for the fixture-backed Vercel preview composition.

The composition must stay unreachable on production deployments, must restore
the rewritten route, and must keep a demo session without any PostgreSQL.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlencode

import pytest

from construction_pm.deployment import vercel_preview
from construction_pm.preview.runtime import open_preview_runtime
from construction_pm.preview.server import PreviewApplication
from construction_pm.preview.storage import DEMO_USERS_BY_ROLE

WEB_ROOT = Path(__file__).resolve().parents[1] / "apps" / "web"


def test_production_never_selects_the_preview_runtime():
    assert vercel_preview.preview_mode({"VERCEL_ENV": "production"}) is False
    assert vercel_preview.preview_mode(
        {"VERCEL_ENV": "production", "CUBI_PREVIEW_RUNTIME": "1"}
    ) is False
    assert vercel_preview.preview_mode({"VERCEL_TARGET_ENV": "production"}) is False


def test_preview_deployment_and_explicit_local_flag_select_the_runtime():
    assert vercel_preview.preview_mode({"VERCEL_ENV": "preview"}) is True
    assert vercel_preview.preview_mode({"CUBI_PREVIEW_RUNTIME": "1"}) is True
    assert vercel_preview.preview_mode({}) is False


def test_restore_path_maps_api_and_preview_routes():
    environ = {"PATH_INFO": "/api", "QUERY_STRING": "__path=projects&view=live"}
    assert ver¶»§q«^