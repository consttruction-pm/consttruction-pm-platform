"""HTTPS adapter for an operational malware-scanning service.

The adapter posts raw document bytes to a single configured endpoint and
expects a small JSON verdict back. It performs no scanning itself, keeps no
credentials in logs or exception text, refuses redirects, bounds the response
size and fails closed on any transport, status or payload error.

The endpoint and bearer token are supplied by the deployment through
``CONSTRUCTION_PM_SCANNER_ENDPOINT`` and ``CONSTRUCTION_PM_SCANNER_TOKEN``;
production readiness rejects a non-HTTPS endpoint.
"""

from __future__ import annotations

import json
import re
from typing import Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import (
    HTTPRedirectHandler,
    Request,
    build_opener,
)
from urllib.response import addinfourl

from .document_scan import (
    DocumentScanError,
    DocumentScanUnavailable,
    ReferenceDocumentScanner,
    ScanVerdict,
)

DEFAULT_SCAN_TIMEOUT_SECONDS = 10.0
DEFAULT_MAX_RESPONSE_BYTES = 8_192
DEFAULT_MAX_PAYLOAD_BYTES = 64 * 1024 * 1024
_CONTENT_TYPE = re.compile(r"^[A-Za-z0-9.+-]+/[A-Za-z0-9.+-]+$")
_FAILED_ALIASES = ("error", "fatal", "timeout", "unavailable")


class _RejectRedirects(HTTPRedirectHandler):
    """A scanner must answer directly; a redirect is never followed."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        raise HTTPError(req.full_url, code, "scanner redirect refused", headers, fp)


def _clean(value: object, limit: int) -> str:
    if not isinstance(value, str):
        return ""
    printable = "".join(character for character in value if character.isprintable())
    return printable.strip()[:limit]


class HttpDocumentScanner:
    """Fail-closed client for an external scanning service."""

    def __init__(
        self,
        endpoint: str,
        *,
        token: str | None = None,
        timeout: float = DEFAULT_SCAN_TIMEOUT_SECONDS,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
        max_payload_bytes: int = DEFAULT_MAX_PAYLOAD_BYTES,
        allow_insecure: bool = False,
        opener=None,
    ) -> None:
        if not isinstance(endpoint, str) or not endpoint.strip():
            raise DocumentScanError("INVALID_SCANNER_ENDPOINT")
        parsed = urlsplit(endpoint.strip())
        if parsed.scheme not in {"https", "http"} or not parsed.hostname:
            raise DocumentScanError("INVALID_SCANNER_ENDPOINT")
        if parsed.scheme == "http" and not allow_insecure:
            raise DocumentScanError("SCANNER_ENDPOINT_REQUIRES_HTTPS")
        if token is not None and (not isinstance(token, str) or not token.strip()):
            raise DocumentScanError("INVALID_SCANNER_TOKEN")
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or timeout <= 0
            or timeout > 120
        ):
            raise DocumentScanError("INVALID_SCANNER_TIMEOUT")
        for name, value in (
            ("max_response_bytes", max_response_bytes),
            ("max_payload_bytes", max_payload_bytes),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise DocumentScanError(f"INVALID_SCANNER_{name.upper()}")
        self._endpoint = endpoint.strip()
        self._token = None if token is None else token.strip()
        self._timeout = float(timeout)
        self._max_response_bytes = max_response_bytes
        self._max_payload_bytes = max_payload_bytes
        self._opener = build_opener(_RejectRedirects) if opener is None else opener

    @property
    def endpoint(self) -> str:
        return self._endpoint

    def scan(self, data: bytes, *, content_type: str) -> ScanVerdict:
        if not isinstance(data, (bytes, bytearray)):
            raise DocumentScanError("INVALID_DOCUMENT_SCAN_PAYLOAD")
        payload = bytes(data)
        if not payload:
            raise DocumentScanError("INVALID_DOCUMENT_SCAN_PAYLOAD")
        if len(payload) > self._max_payload_bytes:
            raise DocumentScanError("DOCUMENT_SCAN_PAYLOAD_TOO_LARGE")
        headers = {
            "Content-Type": "application/octet-stream",
            "Accept": "application/json",
        }
        if isinstance(content_type, str) and _CONTENT_TYPE.match(content_type):
            headers["X-Document-Content-Type"] = content_type
        if self._token is not None:
            headers["Authorization"] = f"Bearer {self._token}"
        request = Request(
            self._endpoint,
            data=payload,
            headers=headers,
            method="POST",
        )
        try:
            response = self._opener.open(request, timeout=self._timeout)
        except HTTPError as exc:
            raise DocumentScanUnavailable(
                f"SCANNER_HTTP_{int(getattr(exc, 'code', 0) or 0)}"
            ) from None
        except (URLError, TimeoutError, OSError) as exc:
            raise DocumentScanUnavailable("SCANNER_UNAVAILABLE") from exc
        try:
            return self._verdict(response)
        finally:
            close = getattr(response, "close", None)
            if callable(close):
                close()

    def _verdict(self, response: addinfourl) -> ScanVerdict:
        status = getattr(response, "status", None) or getattr(response, "code", None)
        if status is not None and int(status) != 200:
            raise DocumentScanUnavailable(f"SCANNER_HTTP_{int(status)}")
        try:
            raw = response.read(self._max_response_bytes + 1)
        except (OSError, ValueError) as exc:
            raise DocumentScanUnavailable("SCANNER_RESPONSE_UNREADABLE") from exc
        if len(raw) > self._max_response_bytes:
            raise DocumentScanUnavailable("SCANNER_RESPONSE_TOO_LARGE")
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise DocumentScanUnavailable("SCANNER_RESPONSE_INVALID") from None
        if not isinstance(parsed, dict):
            raise DocumentScanUnavailable("SCANNER_RESPONSE_INVALID")
        reported = _clean(parsed.get("status"), 32).lower()
        if reported in _FAILED_ALIASES:
            reported = "failed"
        engine = _clean(parsed.get("engine"), 128)
        engine_version = _clean(parsed.get("engine_version"), 64)
        detail = _clean(parsed.get("detail"), 256)
        if not reported or not engine or not engine_version:
            raise DocumentScanUnavailable("SCANNER_RESPONSE_INCOMPLETE")
        verdict = ScanVerdict(
            status=reported,
            engine=engine,
            engine_version=engine_version,
            detail=detail,
        )
        verdict.validate()
        return verdict


def scanner_from_environment(
    environment: Mapping[str, str],
    *,
    opener=None,
) -> object:
    """Build the configured scanner adapter; never returns an implicit engine."""
    kind = _clean(environment.get("CONSTRUCTION_PM_SCANNER"), 32).lower()
    if kind == "reference":
        return ReferenceDocumentScanner()
    if kind != "external":
        raise DocumentScanError("UNCONFIGURED_SCANNER")
    endpoint = environment.get("CONSTRUCTION_PM_SCANNER_ENDPOINT")
    if not isinstance(endpoint, str) or not endpoint.strip():
        raise DocumentScanError("MISSING_SCANNER_ENDPOINT")
    token = environment.get("CONSTRUCTION_PM_SCANNER_TOKEN")
    raw_timeout = _clean(
        environment.get("CONSTRUCTION_PM_SCANNER_TIMEOUT_SECONDS"), 16
    )
    try:
        timeout = (
            DEFAULT_SCAN_TIMEOUT_SECONDS if not raw_timeout else float(raw_timeout)
        )
    except ValueError:
        raise DocumentScanError("INVALID_SCANNER_TIMEOUT") from None
    return HttpDocumentScanner(
        endpoint,
        token=token,
        timeout=timeout,
        opener=opener,
    )


__all__ = [
    "DEFAULT_MAX_PAYLOAD_BYTES",
    "DEFAULT_MAX_RESPONSE_BYTES",
    "DEFAULT_SCAN_TIMEOUT_SECONDS",
    "HttpDocumentScanner",
    "scanner_from_environment",
]
