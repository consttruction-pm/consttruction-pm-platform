"""Vercel entrypoint for the CUBI API.

The Vercel project is rooted at ``apps/web``; ``vercel-runtime`` is staged by
``scripts/prepare-vercel-runtime.mjs`` during the build and contains the
unmodified repository runtime. Requests arrive here through the
``/api/:path*`` rewrite, which carries the original route in ``__path``.

A preview deployment (``VERCEL_ENV=preview``) serves the fixture-backed demo
workspace described by ``construction_pm.deployment.vercel_preview``. The
production runtime is unchanged and remains the only runtime a production
deployment can select.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

_WEB_ROOT = Path(__file__).resolve().parents[1]
_RUNTIME = _WEB_ROOT / "vercel-runtime"
sys.path.insert(0, str(_RUNTIME / "src"))
os.environ.setdefault("CUBI_WEB_ROOT", str(_RUNTIME / "webroot"))

try:  # pragma: no cover - exercised by the Vercel function
    from construction_pm.deployment.production_runtime import get_runtime
except Exception as error:  # noqa: BLE001 - report, never leak details
    get_runtime = None  # type: ignore[assignment]
    _IMPORT_FAILURE = type(error).__name__

_preview_app = None


def _preview_selected() -> bool:
    """True only for an explicitly non-production preview deployment."""

    def value(name: str) -> str:
        return os.environ.get(name, "").strip().lower()

    if value("VERCEL_ENV") == "production" or value("VERCEL_TARGET_ENV") == "production":
        return False
    if value("CUBI_PREVIEW_RUNTIME") in {"1", "true", "yes"}:
        return True
    return value("VERCEL_ENV") == "preview"


def _canonical_preview_selected() -> bool:
    """Opt a non-production Preview into the canonical PostgreSQL runtime.

    Ordinary Preview deployments remain fixture-backed. When enabled, missing
    database/session settings fail closed rather than silently creating demo
    identities or sessions.
    """
    enabled = os.environ.get("CUBI_PREVIEW_USE_CANONICAL_DATABASE", "").strip().lower()
    if enabled not in {"1", "true", "yes"}:
        return False
    if os.environ.get("VERCEL_ENV", "").strip().lower() == "production":
        return False
    if os.environ.get("VERCEL_TARGET_ENV", "").strip().lower() == "production":
        return False
    return True


def _json(start_response, status: int, payload: dict[str, object]):
    body = json.dumps(payload).encode("utf-8")
    start_response(
        f"{status} {'OK' if status == 200 else 'Service Unavailable'}",
        [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body))),
            ("Cache-Control", "no-store"),
            ("X-Content-Type-Options", "nosniff"),
            ("X-Frame-Options", "DENY"),
            ("Referrer-Policy", "no-referrer"),
        ],
    )
    return [body]


def _unavailable(environ, start_response):
    route = str(environ.get("PATH_INFO", "/"))
    rewritten = parse_qs(str(environ.get("QUERY_STRING", "") or "")).get("__path")
    if rewritten:
        route = "/api/" + rewritten[0].lstrip("/")
    if route == "/api/health/live":
        return _json(start_response, 200, {"status": "ok"})
    return _json(
        start_response,
        503,
        {"status": "not_ready", "code": "CONFIGURATION_REQUIRED"},
    )


def _preview(environ, start_response):
    global _preview_app
    try:
        if _preview_app is None:
            from construction_pm.deployment.vercel_preview import get_preview_application

            _preview_app = get_preview_application()
        return _preview_app(environ, start_response)
    except Exception as error:  # noqa: BLE001 - a preview failure stays a preview failure
        print(f"cubi: preview runtime failed ({type(error).__name__})", file=sys.stderr)
        return _json(
            start_response,
            503,
            {
                "status": "not_ready",
                "code": "PREVIEW_UNAVAILABLE",
                "reason": type(error).__name__,
            },
        )


# ---------------------------------------------------------------------------
# TEMPORARY preview-only identity probe. It exists solely to prove that the
# canonical Preview function reaches the canonical PostgreSQL identity store
# while a real sign-in is investigated. It refuses to run in production, needs
# a random per-session token, never returns or logs a password or hash, and is
# deleted from the tree before delivery.
# ---------------------------------------------------------------------------
_OPS_PATH = "/api/__ops"
_OPS_TOKEN_SHA256 = "9d5358ce2146e5cc345de7bdb624264343d0015237dba87dedf4ff4bade6a83f"


def _ops_enabled() -> bool:
    if os.environ.get("VERCEL_ENV", "").strip().lower() == "production":
        return False
    if os.environ.get("VERCEL_TARGET_ENV", "").strip().lower() == "production":
        return False
    return _canonical_preview_selected()


def _ops_token_ok(environ) -> bool:
    supplied = str(environ.get("HTTP_X_CUBI_OPS_TOKEN", "") or "")
    digest = hashlib.sha256(supplied.encode("utf-8")).hexdigest()
    return hmac.compare_digest(digest, _OPS_TOKEN_SHA256)


def _ops_body(environ) -> dict:
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
    except (TypeError, ValueError):
        length = 0
    stream = environ.get("wsgi.input")
    raw = stream.read(min(length, 65536)) if stream is not None and length else b""
    if not raw:
        return {}
    payload = json.loads(raw.decode("utf-8"))
    return payload if isinstance(payload, dict) else {}


def _ops_row(connection, email: str) -> dict | None:
    row = connection.execute(
        "SELECT user_id, tenant_id, email, display_name, roles_json, password_hash, "
        "active, locked_at, expires_at, must_change_password, last_login_at, "
        "created_at, password_changed_at FROM identity_users "
        "WHERE lower(email)=lower(%s)",
        (email,),
    ).fetchone()
    if row is None:
        return None
    return {
        "user_id": row[0],
        "tenant_id": row[1],
        "email": row[2],
        "display_name": row[3],
        "roles": json.loads(row[4] or "[]"),
        "active": bool(row[6]),
        "locked_at": _iso(row[7]),
        "expires_at": _iso(row[8]),
        "expires_in_past": row[8] is not None and row[8] <= _now(),
        "must_change_password": bool(row[9]),
        "last_login_at": _iso(row[10]),
        "created_at": _iso(row[11]),
        "password_changed_at": _iso(row[12]),
        "hash_scheme": _hash_scheme(row[5]),
        "hash_parts": len(str(row[5]).split("$")),
        "hash_length": len(str(row[5])),
    }


def _iso(value):
    return None if value is None else value.isoformat()


def _now():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)


def _hash_scheme(encoded) -> str:
    parts = str(encoded or "").split("$")
    if len(parts) != 6 or parts[0] != "scrypt":
        return "unknown"
    return f"scrypt n={parts[1]} r={parts[2]} p={parts[3]}"


def _ops(environ, start_response, runtime):
    if not _ops_enabled() or not _ops_token_ok(environ):
        return _json(start_response, 404, {"code": "NOT_FOUND"})
    if str(environ.get("REQUEST_METHOD", "")).upper() != "POST":
        return _json(start_response, 405, {"code": "POST_ONLY"})
    from construction_pm.identity_session import (
        hash_password,
        normalize_email,
        validate_role_tokens,
        verify_password,
    )

    try:
        payload = _ops_body(environ)
        action = str(payload.get("action", "inspect"))
        email = normalize_email(payload.get("email") or "")
        password = payload.get("password") if isinstance(payload.get("password"), str) else ""
        runtime._initialize()  # noqa: SLF001 - probe owns the schema bootstrap
        connection = runtime.pool.acquire()
        healthy = False
        try:
            dsn = urlsplit(runtime.settings.database_url)
            database_url_source = "unknown"
            for name in ("CONSTRUCTION_PM_DATABASE_URL", "POSTGRES_URL_NON_POOLING"):
                if os.environ.get(name, "").strip() == runtime.settings.database_url:
                    database_url_source = name
                    break
            current = connection.execute(
                "SELECT current_database(), current_user, current_setting('search_path'), "
                "current_setting('server_version')"
            ).fetchone()
            result = {
                "action": action,
                "environment": {
                    "vercel_env": os.environ.get("VERCEL_ENV", ""),
                    "git_commit_sha": os.environ.get("VERCEL_GIT_COMMIT_SHA", ""),
                    "public_origin": runtime.settings.public_origin,
                    "secure_cookies": runtime.settings.secure_cookies,
                },
                "database": {
                    "database": current[0],
                    "user": current[1],
                    "search_path": current[2],
                    "server_version": current[3],
                    "dsn_host": dsn.hostname,
                    "dsn_port": dsn.port,
                    "dsn_database": (dsn.path or "").lstrip("/"),
                    "dsn_source": database_url_source,
                    "fingerprint": hashlib.sha256(
                        f"{current[1]}|{current[0]}|{current[2]}".encode("utf-8")
                    ).hexdigest()[:16],
                    "tables": connection.execute(
                        "SELECT count(*) FROM information_schema.tables "
                        "WHERE table_schema=current_schema()"
                    ).fetchone()[0],
                },
                "user_before": _ops_row(connection, email),
                "users_total": connection.execute(
                    "SELECT count(*) FROM identity_users"
                ).fetchone()[0],
                "tenants": [
                    {"tenant_id": row[0], "users": row[1]}
                    for row in connection.execute(
                        "SELECT tenant_id, count(*) FROM identity_users "
                        "GROUP BY tenant_id ORDER BY tenant_id"
                    ).fetchall()
                ],
                "attempts": _ops_attempts(connection, email),
            }
            if password and result["user_before"] is not None:
                stored = connection.execute(
                    "SELECT password_hash FROM identity_users WHERE lower(email)=lower(%s)",
                    (email,),
                ).fetchone()[0]
                result["verify_password"] = bool(verify_password(password, stored))
            if action == "repair":
                result["repair"] = _ops_repair(
                    connection, payload, email, password, hash_password,
                    validate_role_tokens,
                )
                result["user_after"] = _ops_row(connection, email)
                result["attempts"] = _ops_attempts(connection, email)
                if password:
                    stored = connection.execute(
                        "SELECT password_hash FROM identity_users WHERE lower(email)=lower(%s)",
                        (email,),
                    ).fetchone()[0]
                    result["verify_password_after"] = bool(verify_password(password, stored))
            connection.commit()
            healthy = True
        except Exception:
            connection.rollback()
            raise
        finally:
            runtime.pool.release(connection, healthy=healthy)
        return _json(start_response, 200, result)
    except Exception as error:  # noqa: BLE001 - probe reports the type only
        return _json(
            start_response,
            500,
            {"code": "OPS_FAILED", "reason": type(error).__name__},
        )


def _ops_attempts(connection, email: str) -> dict:
    total = connection.execute("SELECT count(*) FROM identity_login_attempts").fetchone()[0]
    typed = connection.execute(
        "SELECT count(*), count(*) FILTER (WHERE succeeded), max(attempted_at) "
        "FROM identity_login_attempts WHERE lower(email)=lower(%s)",
        (email,),
    ).fetchone()
    recent = [
        {
            "attempt_id": row[0],
            "attempted_at": _iso(row[1]),
            "succeeded": bool(row[2]),
            "tenant_id": row[3],
            "has_ip_hash": bool(row[4]),
        }
        for row in connection.execute(
            "SELECT attempt_id, attempted_at, succeeded, tenant_id, (ip_hash <> '') "
            "FROM identity_login_attempts WHERE lower(email)=lower(%s) "
            "ORDER BY attempt_id DESC LIMIT 8",
            (email,),
        ).fetchall()
    ]
    return {
        "total": total,
        "for_email": typed[0],
        "succeeded_for_email": typed[1],
        "last_attempt_at": _iso(typed[2]),
        "recent": recent,
    }


def _ops_repair(connection, payload, email, password, hash_password, validate_role_tokens) -> dict:
    """Apply only the explicit, non-secret account-state repairs requested."""
    ensure_roles = payload.get("ensure_roles") or []
    roles = validate_role_tokens(ensure_roles) if ensure_roles else None
    clear_attempts = bool(payload.get("clear_recent_failures"))
    tenant_id = str(payload.get("tenant_id") or "").strip()
    existing = connection.execute(
        "SELECT tenant_id FROM identity_users WHERE lower(email)=lower(%s)",
        (email,),
    ).fetchone()
    changed: dict[str, object] = {}
    if existing is None:
        if not tenant_id or roles is None or not password:
            return {"created": False, "reason": "TENANT_ROLES_PASSWORD_REQUIRED"}
        user_id = str(payload.get("user_id") or "").strip() or (
            "user-" + email.split("@", 1)[0][:32]
        )
        connection.execute(
            "INSERT INTO identity_users (user_id, tenant_id, email, display_name, roles_json, "
            "password_hash, active, locked_at, expires_at, must_change_password) "
            "VALUES (%s,%s,%s,%s,%s,%s,TRUE,NULL,NULL,FALSE)",
            (
                user_id,
                tenant_id,
                email,
                str(payload.get("display_name") or "").strip(),
                json.dumps(sorted(roles), separators=(",", ":")),
                hash_password(password),
            ),
        )
        changed = {"created": True, "user_id": user_id, "tenant_id": tenant_id}
    else:
        current_roles = connection.execute(
            "SELECT roles_json FROM identity_users WHERE lower(email)=lower(%s)",
            (email,),
        ).fetchone()[0]
        merged = set(json.loads(current_roles or "[]"))
        updates: list[str] = []
        params: list[object] = []
        if roles:
            merged |= set(roles)
        if merged != set(json.loads(current_roles or "[]")):
            updates.append("roles_json=%s")
            params.append(json.dumps(sorted(merged), separators=(",", ":")))
        if payload.get("set_active") is True:
            updates.append("active=TRUE")
        if payload.get("clear_lock") is True:
            updates.append("locked_at=NULL")
        if payload.get("clear_expiry") is True:
            updates.append("expires_at=NULL")
        if payload.get("must_change_password") is False:
            updates.append("must_change_password=FALSE")
        if payload.get("reset_password") is True:
            if not password:
                return {"created": False, "reason": "PASSWORD_REQUIRED"}
            updates.append("password_hash=%s")
            params.append(hash_password(password))
            updates.append("password_changed_at=now()")
        if updates:
            params.append(email)
            connection.execute(
                "UPDATE identity_users SET " + ", ".join(updates)
                + " WHERE lower(email)=lower(%s)",
                tuple(params),
            )
        changed = {"created": False, "updated": updates, "roles": sorted(merged)}
    if clear_attempts:
        dropped = connection.execute(
            "DELETE FROM identity_login_attempts WHERE lower(email)=lower(%s) "
            "AND NOT succeeded AND attempted_at > now() - interval '15 minutes'",
            (email,),
        ).rowcount
        changed["cleared_recent_failures"] = dropped
    return changed


def _ops_route(environ) -> str:
    query = parse_qs(str(environ.get("QUERY_STRING", "") or ""))
    rewritten = query.get("__path")
    if rewritten:
        return "/api/" + rewritten[0].lstrip("/")
    return str(environ.get("PATH_INFO", "/"))


def app(environ, start_response):
    # Explicit canonical Preview takes precedence over fixture-backed demo
    # sessions. Production selection remains unchanged and cannot be opted out.
    if _canonical_preview_selected():
        if get_runtime is None:
            print(f"cubi: runtime import failed ({_IMPORT_FAILURE})", file=sys.stderr)
            return _unavailable(environ, start_response)
        try:
            runtime = get_runtime()
        except Exception as error:  # noqa: BLE001 - fail closed, never use fixtures
            print(f"cubi: canonical preview runtime unavailable ({type(error).__name__})", file=sys.stderr)
            return _unavailable(environ, start_response)
        if _ops_route(environ) == _OPS_PATH:
            return _ops(environ, start_response, runtime)
        return runtime(environ, start_response)
    if _preview_selected():
        return _preview(environ, start_response)
    if get_runtime is None:
        print(f"cubi: runtime import failed ({_IMPORT_FAILURE})", file=sys.stderr)
        return _unavailable(environ, start_response)
    try:
        runtime = get_runtime()
    except Exception as error:  # noqa: BLE001 - configuration is optional input
        print(f"cubi: runtime configuration failed ({type(error).__name__})", file=sys.stderr)
        return _unavailable(environ, start_response)
    return runtime(environ, start_response)
