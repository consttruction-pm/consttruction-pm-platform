"""Unit coverage for the production identity/session boundary.

These tests exercise the same code path the Vercel runtime uses
(``IdentityService`` over a SQL store), with SQLite standing in for
PostgreSQL. The live PostgreSQL variant lives in
``tests/integration/test_production_login_postgres_live.py``.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from construction_pm.identity_session import (
    CSRF_COOKIE_NAME,
    DEFAULT_IDLE_TIMEOUT,
    DEFAULT_SESSION_TTL,
    IdentityError,
    IdentityService,
    IdentityUser,
    SQLiteIdentityStore,
    clear_cookie_header,
    clear_csrf_cookie_header,
    csrf_cookie_header,
    csrf_token,
    hash_client_ip,
    hash_password,
    load_identity_settings,
    normalize_email,
    password_policy_error,
    session_cookie_header,
    token_hash,
    validate_role_tokens,
    verify_password,
)

SECRET = "unit-test-session-secret-0123456789"
PASSWORD = "correct horse battery staple"


def _clock(start: datetime):
    current = {"now": start}

    def read() -> datetime:
        return current["now"]

    def advance(delta: timedelta) -> None:
        current["now"] = current["now"] + delta

    return read, advance


@pytest.fixture()
def store() -> SQLiteIdentityStore:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    adapter = SQLiteIdentityStore(connection)
    adapter.initialize()
    return adapter


def _user(**overrides) -> IdentityUser:
    values = {
        "user_id": "user-1",
        "tenant_id": "tenant-a",
        "email": "engineer@example.test",
        "display_name": "Engineer",
        "roles": frozenset({"planner"}),
        "password_hash": hash_password(PASSWORD),
    }
    values.update(overrides)
    return IdentityUser(**values)


def _service(store: SQLiteIdentityStore, **kwargs) -> IdentityService:
    return IdentityService(store, csrf_secret=SECRET, **kwargs)


def test_hash_is_self_describing_and_verifiable():
    encoded = hash_password(PASSWORD)
    assert encoded.startswith("scrypt$16384$8$1$")
    assert PASSWORD not in encoded
    assert verify_password(PASSWORD, encoded)
    assert not verify_password(PASSWORD + "x", encoded)
    assert not verify_password(PASSWORD, encoded[:-4] + "AAAA")


def test_hash_uses_a_fresh_salt_each_time():
    first = hash_password(PASSWORD)
    second = hash_password(PASSWORD)
    assert first != second
    assert verify_password(PASSWORD, second)


def test_verify_rejects_malformed_or_weakened_hashes():
    assert not verify_password(PASSWORD, "")
    assert not verify_password(PASSWORD, "plaintext")
    assert not verify_password(PASSWORD, "scrypt$1$8$1$abc$def")
    assert not verify_password(PASSWORD, "scrypt$x$8$1$abc$def")


def test_password_policy():
    assert password_policy_error("") == "PASSWORD_REQUIRED"
    assert password_policy_error("short") == "PASSWORD_TOO_SHORT"
    assert password_policy_error("x" * 300) == "PASSWORD_TOO_LONG"
    assert password_policy_error(PASSWORD) is None


def test_normalize_email():
    assert normalize_email("  Engineer@Example.TEST ") == "engineer@example.test"
    for bad in (None, "", "no-at-sign", "@example.test", "user@", "a b@c.test", "u@localhost"):
        with pytest.raises(IdentityError):
            normalize_email(bad)


def test_validate_role_tokens_rejects_unknown_shapes():
    assert validate_role_tokens(["viewer", " planner "]) == frozenset({"viewer", "planner"})
    for bad in ([], "viewer", ["ok", ""], [1], ["ro le"], ["x" * 65]):
        with pytest.raises(IdentityError):
            validate_role_tokens(bad)


def test_login_issues_opaque_token_and_persists_only_its_hash(store):
    store.upsert_user(_user())
    start = datetime(2026, 11, 13, 8, 0, tzinfo=timezone.utc)
    read, _ = _clock(start)
    service = _service(store, now=read)

    issued = service.login("Engineer@Example.test", PASSWORD)

    assert issued.user_id == "user-1"
    assert issued.tenant_id == "tenant-a"
    assert issued.roles == frozenset({"planner"})
    assert issued.expires_at == start + DEFAULT_SESSION_TTL
    assert len(issued.token) >= 32
    rows = store.connection.execute("SELECT token_hash FROM identity_sessions").fetchall()
    assert [row[0] for row in rows] == [token_hash(issued.token)]
    assert issued.token not in {row[0] for row in rows}

    resolved = service.resolve(issued.token)
    assert resolved is not None
    assert resolved.user_id == "user-1"
    assert resolved.tenant_id == "tenant-a"
    assert resolved.roles == frozenset({"planner"})


def test_login_rejects_wrong_password_and_unknown_account_identically(store):
    store.upsert_user(_user())
    service = _service(store)

    with pytest.raises(IdentityError) as wrong:
        service.login("engineer@example.test", "not the password value")
    with pytest.raises(IdentityError) as unknown:
        service.login("nobody@example.test", "not the password value")
    assert wrong.value.code == unknown.value.code == "AUTHENTICATION_FAILED"

    attempts = store.connection.execute(
        "SELECT email, succeeded FROM identity_login_attempts ORDER BY attempt_id"
    ).fetchall()
    assert [(row[0], row[1]) for row in attempts] == [
        ("engineer@example.test", 0),
        ("nobody@example.test", 0),
    ]


def test_inactive_user_cannot_login(store):
    store.upsert_user(_user(active=False))
    with pytest.raises(IdentityError) as failure:
        _service(store).login("engineer@example.test", PASSWORD)
    assert failure.value.code == "AUTHENTICATION_FAILED"
    assert store.connection.execute("SELECT COUNT(*) FROM identity_sessions").fetchone()[0] == 0


def test_login_is_throttled_after_repeated_failures(store):
    store.upsert_user(_user())
    service = _service(store, max_email_failures=3)

    for _ in range(3):
        with pytest.raises(IdentityError):
            service.login("engineer@example.test", "wrong password value")

    with pytest.raises(IdentityError) as throttled:
        service.login("engineer@example.test", PASSWORD)
    assert throttled.value.code == "AUTHENTICATION_THROTTLED"


def test_ip_throttle_is_independent_of_email(store):
    store.upsert_user(_user())
    service = _service(store, max_ip_failures=2)

    for index in range(2):
        with pytest.raises(IdentityError):
            service.login(f"person{index}@example.test", "wrong password value", ip_hash="ip-1")

    with pytest.raises(IdentityError) as throttled:
        service.login("engineer@example.test", PASSWORD, ip_hash="ip-1")
    assert throttled.value.code == "AUTHENTICATION_THROTTLED"


def test_session_expires_at_absolute_ttl(store):
    store.upsert_user(_user())
    start = datetime(2026, 11, 13, 8, 0, tzinfo=timezone.utc)
    read, advance = _clock(start)
    service = _service(store, now=read, session_ttl=timedelta(minutes=30))

    issued = service.login("engineer@example.test", PASSWORD)
    advance(timedelta(minutes=29, seconds=30))
    assert service.resolve(issued.token) is not None
    advance(timedelta(seconds=31))
    assert service.resolve(issued.token) is None
    assert service.resolve(issued.token) is None


def test_session_expires_after_idle_timeout(store):
    store.upsert_user(_user())
    start = datetime(2026, 11, 13, 8, 0, tzinfo=timezone.utc)
    read, advance = _clock(start)
    service = _service(store, now=read, idle_timeout=timedelta(minutes=10))

    issued = service.login("engineer@example.test", PASSWORD)
    advance(DEFAULT_IDLE_TIMEOUT if DEFAULT_IDLE_TIMEOUT < timedelta(minutes=10) else timedelta(minutes=10))
    assert service.resolve(issued.token) is None


def test_logout_revokes_and_cannot_be_replayed(store):
    store.upsert_user(_user())
    service = _service(store)
    issued = service.login("engineer@example.test", PASSWORD)

    assert service.logout(issued.token) is True
    assert service.resolve(issued.token) is None
    assert service.logout(issued.token) is False


def test_resolve_rejects_forged_tokens(store):
    store.upsert_user(_user())
    service = _service(store)
    issued = service.login("engineer@example.test", PASSWORD)

    assert service.resolve(issued.token + "x") is None
    assert service.resolve("") is None
    assert service.resolve("not-a-real-token") is None


def test_csrf_token_is_bound_to_the_session_token():
    first = csrf_token(SECRET, "token-a")
    assert first == csrf_token(SECRET, "token-a")
    assert first != csrf_token(SECRET, "token-b")
    assert first != csrf_token(SECRET + "x", "token-a")


def test_verify_csrf_is_constant_time_and_rejects_missing(store):
    store.upsert_user(_user())
    service = _service(store)
    issued = service.login("engineer@example.test", PASSWORD)

    assert service.csrf_for(issued.token) == issued.csrf_token
    assert service.verify_csrf(issued.token, issued.csrf_token)
    assert not service.verify_csrf(issued.token, None)
    assert not service.verify_csrf(issued.token, "")
    assert not service.verify_csrf(issued.token, issued.csrf_token + "x")


def test_service_rejects_short_csrf_secret(store):
    with pytest.raises(IdentityError):
        IdentityService(store, csrf_secret="too-short")


def test_cookie_headers_carry_security_attributes():
    session = session_cookie_header(
        name="cp_session", value="abc", max_age=43200, secure=True
    )
    assert "HttpOnly" in session
    assert "Secure" in session
    assert "SameSite=Lax" in session
    assert "Path=/" in session
    assert "Max-Age=43200" in session

    csrf_cookie = csrf_cookie_header(
        name=CSRF_COOKIE_NAME, value="a+b/c=", max_age=43200, secure=True
    )
    assert "HttpOnly" not in csrf_cookie
    assert "cubi_csrf=a%2Bb" in csrf_cookie
    assert "%3D" in csrf_cookie
    assert "Secure" in csrf_cookie

    assert "Max-Age=0" in clear_cookie_header(name="cp_session", secure=True)
    assert "Max-Age=0" in clear_csrf_cookie_header(name=CSRF_COOKIE_NAME, secure=True)


def test_ip_hash_never_contains_the_raw_address():
    digest = hash_client_ip(SECRET, "203.0.113.7")
    assert "203.0.113.7" not in digest
    assert digest == hash_client_ip(SECRET, "203.0.113.7")
    assert digest != hash_client_ip(SECRET, "203.0.113.8")
    assert hash_client_ip(SECRET, "") == ""


def test_touch_updates_last_seen_so_active_sessions_survive(store):
    store.upsert_user(_user())
    start = datetime(2026, 11, 13, 8, 0, tzinfo=timezone.utc)
    read, advance = _clock(start)
    service = _service(store, now=read, idle_timeout=timedelta(minutes=10))

    issued = service.login("engineer@example.test", PASSWORD)
    for _ in range(5):
        advance(timedelta(minutes=5))
        assert service.resolve(issued.token) is not None


def test_https_origin_can_never_disable_secure_cookies():
    settings = load_identity_settings(
        {
            "CONSTRUCTION_PM_SESSION_SECRET": SECRET,
            "CONSTRUCTION_PM_PUBLIC_ORIGIN": "https://cubi.example.test",
            "CONSTRUCTION_PM_INSECURE_COOKIES": "true",
        }
    )
    assert settings["secure_cookies"] is True
    assert settings["public_origin"] == "https://cubi.example.test"


def test_loopback_http_harness_may_opt_out_of_secure_cookies():
    settings = load_identity_settings(
        {
            "CONSTRUCTION_PM_SESSION_SECRET": SECRET,
            "CONSTRUCTION_PM_PUBLIC_ORIGIN": "http://127.0.0.1:4180",
            "CONSTRUCTION_PM_INSECURE_COOKIES": "1",
        }
    )
    assert settings["secure_cookies"] is False
