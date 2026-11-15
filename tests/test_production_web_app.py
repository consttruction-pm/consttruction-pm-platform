"""WSGI-level tests for the production HTTP surface.

The inner API application is stubbed here: these tests are about the boundary
that the real deployment puts in front of it (login, logout, cookies, CSRF,
origin checks, the ``/app`` gate and static delivery). The full composed stack
against PostgreSQL is covered by the integration test.
"""

from __future__ import annotations

import io
import json
import sqlite3
from pathlib import Path
from wsgiref.util import setup_testing_defaults

import pytest

from construction_pm.deployment.production_web import ProductionWebApp, StaticSite, _client_ip
from construction_pm.identity_session import (
    IdentityService,
    IdentityUser,
    SQLiteIdentityStore,
    hash_password,
)

ORIGIN = "https://cubi.example.test"
SECRET = "web-test-session-secret-0123456789abc"
PASSWORD = "correct horse battery staple"


class StubApi:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def __call__(self, environ, start_response):
        self.calls.append((environ["REQUEST_METHOD"], environ["PATH_INFO"]))
        start_response(
            "200 OK",
            [
                ("Content-Type", "application/json"),
                ("Content-Length", "2"),
                ("X-Frame-Options", "DENY"),
            ],
        )
        session_id = environ.get("HTTP_COOKIE", "")
        return [json.dumps({"ok": True, "seen": environ["PATH_INFO"]}).encode()]


@pytest.fixture()
def site_root(tmp_path: Path) -> P¶»§q«^