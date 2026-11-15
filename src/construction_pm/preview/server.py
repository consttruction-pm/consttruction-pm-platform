"""Local full-stack HTTP surface for the CUBI preview.

This module only translates HTTP. Authentication decisions stay in the real
lifecycle service, scheduling stays in the Shared Domain/Calculation Core and
the browser assets are the real built Web client. The preview adds exactly two
things: a fixture-only demo login (there is no production login here) and a
guard that keeps the workspace shell behind that demo session.
"""

from __future__ import annotations

import argparse
import gzip
import html
import hmac
import json
import os
import sys
import threading
import traceback
from http.cookies import SimpleCookie
from pathlib import Path
from socketserver import ThreadingMixIn
from typing import Iterable, Mapping
from urllib.parse import parse_qs, urlencode, urlsplit
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

from construction_pm.application.project_lifecycle import AuthenticatedSession

from .runtime import PreviewRuntime, PreviewRuntimeError, open_preview_runtime
from .storage import (
    DEMO_USERS,
    DEMO_USERS_BY_ROLE,
    PREVIEW_SEED_VERSION,
    PREVIEW_SESSION_TTL,
)

SESSION_COOKIE = "cp_session"
LOGIN_PATH = "/preview/login"
LOGOUT_PATH = "/preview/logout"
PRIVATE_LOGIN_PATH = "/preview/private-login"
HEALTH_PATH = "/preview/health"

_ALLOWED_ROOT_FILES = {
    "index.html",
    "styles.css",
    "role-workbench.css",
    "cubi-platform-logo-primary.svg",
    "cubi-hero-field.svg",
    "favicon.ico",
}
_ALLOWED_CONTENT_TY¶»§q«^uá…Ñ±ä…Ì¥Ğ‘½•Ìİ¡•¸Í•ÉÙ•™É½´€½‘¥ÍĞ¼¸%Ğ(€€€€€€€€€€€€ŒÑ¡•É•™½É”µÕÍĞ­••ÀÑ¡É•”‘¥É•Ñ½Éä±•Ù•±Ì‰•±½ÜÑ¡”8É•˜É½½Ğ(€€€€€€€€€€€€Œ½ÈÑ¡”±½¼‰•½µ•Ì„€ĞÀĞ¸Q¡”…ÍÍ¥ÍÑ…¹Ğ±…Õ¹¡•ÈÍÑ…åÌÍ…µ”µ½É¥¥¸(€€€€€€€€€€€€Œ‰•…ÕÍ”¥Ğ‘•É¥Ù•ÌÑ¡”€½…ÁÀ½€İ½É­ÍÁ…”±¥¹¬™É½´¥ÑÌ½İ¸UI0¸(€€€€€€€€€€€™½È…ÍÍ•Ğ°É•µ½Ñ”¥¸€ (€€€€€€€€€€€€€€€€ ˆ½ÍÑå±•Ì¹ÍÌˆ°€ˆ½ÍÑå±•Ì¹ÍÌˆ¤°(€€€€€€€€€€€€€€€€ ˆ½‘¥ÍĞ½µ…¥¸¹‰Õ¹‘±”¹©Ìˆ°€ˆ½…ÁÁÌ½İ•ˆ½‘¥ÍĞ½µ…¥¸¹‰Õ¹‘±”¹©Ìˆ¤°(€€€€€€€€€€€€¤è(€€€€€€€€€€€€€€€Í¡•±°€ôÍ¡•±°¹É•Á±…”¡˜œ‰í…ÍÍ•Ñôˆœ°˜œ‰íÍ•±˜¹…ÍÍ•Ñ}‰…Í•õíÉ•µ½Ñ•ôˆœ¤(€€€€€€€‰…¹¹•È€ôÍ•±˜¹}‰…¹¹•È¡Í•ÍÍ¥½¸¤(€€€€€€€¥˜€ˆğ½‰½‘äøˆ¥¸Í¡•±°è(€€€€€€€€€€€Í¡•±°€ôÍ¡•±°¹É•Á±…” ˆğ½‰½‘äøˆ°˜‰í‰…¹¹•Éõq¸€€ğ½‰½‘äøˆ°€Ä¤(€€€€€€€•±Í”è(€€€€€€€€€€€Í¡•±°€ôÍ¡•±°€¬‰…¹¹•È(€€€€€€€É•ÑÕÉ¸€ÈÀÀ°ì‰½¹Ñ•¹ĞµQåÁ”ˆè€‰Ñ•áĞ½¡Ñµ°ì¡…ÉÍ•ĞõÕÑ˜´à‰ô°Í¡•±°¹•¹½‘” ‰ÕÑ˜´àˆ¤((€€€‘•˜}ÍÑ…Ñ¥Œ¡Í•±˜°Á…Ñ èÍÑÈ°µ•Ñ¡½èÍÑÈ¤€´øÑÕÁ±•m¥¹Ğ°‘¥ÑmÍÑÈ°ÍÑÉt°‰åÑ•Ítè(€€€€€€€¥˜µ•Ñ¡½¹½Ğ¥¸ì‰Pˆ°€‰!‰ôè(€€€€€€€€€€€É•ÑÕÉ¸}©Í½¸ ĞÀÔ°ì‰½‘”ˆè€‰5Q!=}9=Q}11=]‰ô¤(€€€€€€€€Œ	É½İÍ•ÉÌ½¹Ù•¹Ñ¥½¹…±±äÁÉ½‰”€½™…Ù¥½¸¹¥¼•Ù•¸İ¡•¸Ñ¡”Á…”‘•±…É•Ì(€€€€€€€€Œ…¸MY™…Ù¥½¸¸M•ÉÙ”Ñ¡”…¹½¹¥…°U	$…ÉÑİ½É¬…ĞÑ¡…Ğ½µÁ…Ñ¥‰¥±¥Ñä(€€€€€€€€ŒÁ…Ñ Í¼Ñ¡”¡½ÍÑ•ÁÉ•Ù¥•Ü‘½•Ì¹½Ğ•µ¥Ğ„¹½¥Íä€ĞÀĞ™½È•Ù•ÉäÙ¥Í¥Ğ¸(€€€€€€€¥˜Á…Ñ €ôô€ˆ½™…Ù¥½¸¹¥¼ˆè(€€€€€€€€€€€±½¼€ôÍ•±˜¹™É½¹Ñ•¹¹É•Í½±Ù” ˆ½Õ‰¤µÁ±…Ñ™½É´µ±½¼µÁÉ¥µ…Éä¹ÍÙœˆ¤(€€€€€€€€€€€¥˜±½¼¥Ì¹½Ğ9½¹”è(€€€€€€€€€€€€€€€É•ÑÕÉ¸€ÈÀÀ°ì‰½¹Ñ•¹ĞµQåÁ”ˆè€‰¥µ…”½ÍÙœ­áµ°‰ô°±½¼¹É•…‘}‰åÑ•Ì ¤(€€€€€€€™¥±”€ôÍ•±˜¹™ÊÚîÆ­y