"""Fixture-backed CUBI workspace for Vercel preview deployments.

A preview deployment of the Web project must be reviewable without a
production database. This module composes the existing local preview stack -
the real HTTP routes, the real SQLite repositories and the curated demo
fixtures (including the Riverside Pump Station Upgrade project) - behind the
Vercel functions.

The composition is deliberately unreachable on a production deployment:

* ``VERCEL_ENV=production`` (or ``VERCEL_TARGET_ENV=production``) always
  selects the production runtime, even if the preview flag is set.
* A preview deployment (``VERCEL_ENV=preview``) or an explicit
  ``CUBI_PREVIEW_RUNTIME=1`` for local runs selects this module instead.
* Nothing here writes to PostgreSQL, contacts a paid service, or impersonates
  a production identity: sessions are the demo sessions of the local preview
  and the only data is the fixture seed in an ephemeral SQLite file.
"""

from __future__ import annotations

import json
import os
import re
import threading
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Callable, Mapping
from urllib.parse import parse_qs, urlencode

from construction_pm.preview.runtime import PreviewRuntime, PreviewRuntimeError, open_preview_runtime
from construction_pm.preview.server import (
    SESSION_COOKIE,
    PreviewApplication,
    _cookie_header,
)
from construction_pm.preview.storage import DEMO_USERS_BY_ROLE

DEFAULT_DATABASE = "/tmp/cubi-prev¶»§q«^