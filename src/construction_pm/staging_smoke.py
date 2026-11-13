"""Read-only staging smoke test for the operational health endpoints.

The smoke test issues only ``GET`` requests. It never writes, migrates, sends
messages or mutates a deployment. A deployment owner runs it against a staging
base URL after starting the candidate build; the result is evidence for staging,
not a claim that production was verified.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Callable, Iterable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .http.operational import HEALTH_LIVE_PATH, HEALTH_READY_PATH

DEFAULT_TIMEOUT_SECONDS = 5.0
MAX_RESPONSE_BYTES = 65_536


class StagingSmokeError(ValueError):
    """The staging target or smoke contract is invalid."""


@dataclass(frozen=True)
class SmokeCheck:
    name: str
    ok: bool
    status_code: int | None
    detail: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "ok": self.ok,
            "status_code": self.status_code,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class SmokeReport:
    base_url: str
    checks: tuple[SmokeCheck, ...]

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)

    def as_dict(self) -> dict[str, object]:
        return {
            "base_url": self.base_url,
            "ok": self.ok,
            "checks": [check.as_dict() for check in self.checks],
            "mutated": False,
        }


def _normalize_base_url(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StagingSmokeError("STAGING_BASE_URL_REQUIRED")
    candidate = value.strip().rstrip("/")
    parsed = urlsplit(candidate)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise StagingSmokeError("INVALID_STAGING_BASE_URL")
    return candidate


def _fetch_json(
    url: str,
    *,
    timeout: float,
    opener: Callable[..., object],
) -> tuple[int, Mapping[str, object] | None, str]:
    request = Request(url, method="GET", headers={"Accept": "application/json"})
    try:
        response = opener(request, timeout=timeout)
    except HTTPError as exc:
        status = int(getattr(exc, "code", 0) or 0)
        try:
            payload = exc.read(MAX_RESPONSE_BYTES)
        finally:
            close = getattr(exc, "close", None)
            if callable(close):
                close()
        return status, _decode(payload), "HTTP_ERROR"
    except URLError as exc:
        return 0, None, f"TRANSPORT_ERROR:{type(exc.reason).__name__}"
    except OSError as exc:
        return 0, None, f"TRANSPORT_ERROR:{type(exc).__name__}"
    try:
        status = int(getattr(response, "status", 200) or 200)
        payload = response.read(MAX_RESPONSE_BYTES)
    finally:
        close = getattr(response, "close", None)
        if callable(close):
            close()
    return status, _decode(payload), ""


def _decode(payload: object) -> Mapping[str, object] | None:
    if not isinstance(payload, (bytes, bytearray)):
        return None
    try:
        value = json.loads(bytes(payload).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def run_staging_smoke(
    base_url: str,
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    opener: Callable[..., object] = urlopen,
    required_components: Iterable[str] = ("configuration", "database"),
) -> SmokeReport:
    """Probe liveness and readiness with read-only GET requests."""
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
        raise StagingSmokeError("INVALID_SMOKE_TIMEOUT")
    base = _normalize_base_url(base_url)
    required = tuple(str(name) for name in required_components)
    checks: list[SmokeCheck] = []

    live_status, live_body, live_error = _fetch_json(
        f"{base}{HEALTH_LIVE_PATH}", timeout=float(timeout), opener=opener
    )
    live_ok = (
        live_status == 200
        and live_body is not None
        and live_body.get("status") == "alive"
    )
    checks.append(
        SmokeCheck(
            "liveness",
            live_ok,
            live_status,
            "" if live_ok else (live_error or "UNEXPECTED_LIVENESS_RESPONSE"),
        )
    )

    ready_status, ready_body, ready_error = _fetch_json(
        f"{base}{HEALTH_READY_PATH}", timeout=float(timeout), opener=opener
    )
    ready_ok = (
        ready_status == 200
        and ready_body is not None
        and ready_body.get("status") in {"ready", "degraded"}
    )
    detail = "" if ready_ok else (ready_error or "NOT_READY")
    components = ready_body.get("components") if isinstance(ready_body, dict) else None
    observed: dict[str, str] = {}
    if isinstance(components, list):
        for component in components:
            if isinstance(component, dict):
                name = component.get("name")
                state = component.get("status")
                if isinstance(name, str) and isinstance(state, str):
                    observed[name] = state
    if ready_ok:
        missing = [name for name in required if observed.get(name) != "healthy"]
        if missing:
            ready_ok = False
            detail = "REQUIRED_COMPONENT_NOT_HEALTHY:" + ",".join(sorted(missing))
    else:
        unhealthy = [name for name in required if observed.get(name) == "unhealthy"]
        if unhealthy:
            detail = "NOT_READY:" + ",".join(sorted(unhealthy))
    checks.append(SmokeCheck("readiness", ready_ok, ready_status, detail))
    return SmokeReport(base_url=base, checks=tuple(checks))


def main(
    argv: Iterable[str] | None = None,
    *,
    opener: Callable[..., object] = urlopen,
) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only staging smoke test for /api/health/live and /api/health/ready."
    )
    parser.add_argument("--base-url", required=True, help="Staging base URL, e.g. https://staging.example")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument(
        "--require-component",
        action="append",
        default=[],
        help="Component that must report healthy in readiness (repeatable).",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    required = tuple(args.require_component) or ("configuration", "database")
    try:
        report = run_staging_smoke(
            args.base_url, timeout=args.timeout, opener=opener, required_components=required
        )
    except StagingSmokeError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(report.as_dict(), ensure_ascii=False, sort_keys=True))
    return 0 if report.ok else 1


if __name__ == "__main__":  # pragma: no cover - exercised through the script wrapper
    raise SystemExit(main())
