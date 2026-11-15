"""HTTP transport for the production deployment.

Three responsibilities live here, and only these three:

1. Login and logout write a real persisted session and set hardened cookies.
2. Every state-changing API call must come from the deployed origin and carry
   the CSRF token derived from the caller's own session.
3. ``/app`` is never served without a valid session; ``/login`` is the only
   anonymous HTML surface, and static assets contain no user data.

The application routes themselves are unchanged and remain in
``ProjectLifecycleHttpRoutes``.
"""

from __future__ import annotations

import json
import mimetypes
import os
import traceback
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping
from urllib.parse import parse_qs, quote, unquote, urlsplit

from ..identity_session import (
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    SESSION_COOKIE_NAME,
    IdentityError,
    IdentityService,
    clear_cookie_header,
    clear_csrf_cookie_header,
    csrf_cookie_header,
    hash_client_ip,
    session_cookie_header,
)

StartResponse = Callable[[str, list[tuple[str, str]]], None]

LOGIN_PATH = "/login"
APP_PATH = "/app"
ENTERPRISE_PATH = "/enterprise"
API_PREFIX = "/api/"
LOGIN_BODY_LIMIT = 8_192
API_BODY_LIMIT = 1_048_576

_SECURITY_HEADERS = (
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "DENY"),
    ("Referrer-Policy", "no-referrer"),
    ("Permissions-Policy", "camera=(), microphone=(), geolocation=()"),
    ("Cross-Origin-¶»§q«^