"""S3-compatible document object storage and explicit configuration.

The adapter uses the S3 REST API directly (SigV4 over stdlib HTTP), so a
deployment does not inherit a vendor SDK. Object keys are derived only from
server-validated tenant/project hashes and the payload digest; a reference that
carries another scope is rejected before any request is made.

Configuration is explicit: production mode never falls back to local disk. If
production selects local storage, or does not select any storage, startup fails
with a configuration error instead of silently writing bytes to a container
filesystem.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

from .document_storage import (
    DEFAULT_MAX_DOCUMENT_BYTES,
    DocumentBinaryStorage,
    DocumentContentHashMismatch,
    DocumentContentIntegrityError,
    DocumentContentNotFound,
    DocumentContentTooLarge,
    DocumentStorageError,
    LocalDocumentStorage,
    document_object_parts,
    storage_scope_key,
)

S3_STORAGE_REF_PREFIX = "s3:v1"
DOCUMENT_STORAGE_KINDS = ("local", "s3")

_BUCKET = re.compile(r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$")
_PREFIX = re.compile(r"^[A-Za-z0-9._/-]{1,120}$")
_HEX16 = re.compile(r"^[0-9a-f]{16}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_HEX2 = re.compile(r"^[0-9a-f]{2}$")
_SAFE_EXTENSION = re.compile(r"^\.[a-z0-9]{1,8}$")


class DocumentStorageConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class DocumentObjectStorageSettings:
    endpoint_url: str
    bucket: str
    region: str
    access_key: str
    secret_key: str
    prefix: str = "documents"
    path_style: bool = True
    server_side_encryption: str | None = None
    session_token: str | None = None
    connect_timeout: float = 10.0
    read_timeout: float = 30.0

    def validate(self) -> None:
        endpoint = self.endpoint_url.strip().rstrip("/")
        parsed = urlsplit(endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise DocumentStorageConfigurationError(
                "INVALID_DOCUMENT_STORAGE_ENDPOINT"
            )
        if parsed.query or parsed.fragment:
            raise DocumentStorageConfigurationError(
                "INVALID_DOCUMENT_STORAGE_ENDPOINT"
            )
        if not _BUCKET.match(self.bucket or ""):
            raise DocumentStorageConfigurationError("INVALID_DOCUMENT_STORAGE_BUCKET")
        for name, value in (("REGION", self.region), ("ACCESS_KEY", self.access_key), ("SECRET_KEY", self.secret_key)):
            if not isinstance(value, str) or not value.strip():
                raise DocumentStorageConfigurationError(
                    f"MISSING_DOCUMENT_STORAGE_{name}"
                )
        prefix = (self.prefix or "").strip("/")
        if prefix and (
            not _PREFIX.match(prefix)
            or any(part in {"", ".", ".."} for part in prefix.split("/"))
        ):
            raise DocumentStorageConfigurationError("INVALID_DOCUMENT_STORAGE_PREFIX")
        if self.server_side_encryption not in {None, "AES256", "aws:kms"}:
            raise DocumentStorageConfigurationError(
                "INVALID_DOCUMENT_STORAGE_ENCRYPTION"
            )
        if self.session_token is not None and not isinstance(self.session_token, str):
            raise DocumentStorageConfigurationError(
                "INVALID_DOCUMENT_STORAGE_SESSION_TOKEN"
            )
        for name, value in (("CONNECT_TIMEOUT", self.connect_timeout), ("READ_TIMEOUT", self.read_timeout)):
            if not isinstance(value, (int, float)) or value <= 0:
                raise DocumentStorageConfigurationError(
                    f"INVALID_DOCUMENT_STORAGE_{name}"
                )


class S3CompatibleDocumentStorage:
    """Private, content-addressed S3 objects behind the binary-storage port."""

    def __init__(
        self,
        settings: DocumentObjectStorageSettings,
        *,
        max_bytes: int = DEFAULT_MAX_DOCUMENT_BYTES,
    ) -> None:
        settings.validate()
        if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes <= 0:
            raise DocumentStorageConfigurationError("INVALID_DOCUMENT_CONTENT_LIMIT")
        self.settings = settings
        self.max_bytes = max_bytes

    # -- references --------------------------------------------------------
    def _key(self, parts: tuple[str, str, str, str]) -> str:
        joined = "/".join(parts)
        prefix = (self.settings.prefix or "").strip("/")
        return f"{prefix}/{joined}" if prefix else joined

    def _reference(self, parts: tuple[str, str, str, str]) -> str:
        return f"{S3_STORAGE_REF_PREFIX}/" + "/".join(parts)

    def _resolve(
        self, storage_ref: str, *, tenant_id: str, project_id: str
    ) -> tuple[str, str]:
        if not isinstance(storage_ref, str) or not storage_ref.startswith(
            f"{S3_STORAGE_REF_PREFIX}/"
        ):
            raise DocumentStorageError("INVALID_DOCUMENT_STORAGE_REF")
        parts = storage_ref[len(S3_STORAGE_REF_PREFIX) + 1:].split("/")
        if len(parts) != 4:
            raise DocumentStorageError("INVALID_DOCUMENT_STORAGE_REF")
        tenant_key, project_key, prefix, name = parts
        if not (_HEX16.match(tenant_key) and _HEX16.match(project_key) and _HEX2.match(prefix)):
            raise DocumentStorageError("INVALID_DOCUMENT_STORAGE_REF")
        stem, extension = os.path.splitext(name)
        if (
            not _HEX64.match(stem)
            or not stem.startswith(prefix)
            or not _SAFE_EXTENSION.match(extension)
        ):
            raise DocumentStorageError("INVALID_DOCUMENT_STORAGE_REF")
        if tenant_key != storage_scope_key(tenant_id) or project_key != storage_scope_key(project_id):
            raise DocumentStorageError("DOCUMENT_STORAGE_SCOPE_MISMATCH")
        return self._key((tenant_key, project_key, prefix, name)), f"sha256:{stem}"

    # -- HTTP/SigV4 --------------------------------------------------------
    def _url(self, key: str) -> str:
        endpoint = self.settings.endpoint_url.rstrip("/")
        quoted = "/".join(quote(segment, safe="-_.~") for segment in key.split("/"))
        if self.settings.path_style:
            return f"{endpoint}/{quote(self.settings.bucket, safe='-_.~')}/{quoted}"
        parsed = urlsplit(endpoint)
        return f"{parsed.scheme}://{self.settings.bucket}.{parsed.netloc}/{quoted}"

    @staticmethod
    def _signing_key(secret: str, datestamp: str, region: str) -> bytes:
        date_key = hmac.new(
            ("AWS4" + secret).encode("utf-8"), datestamp.encode("utf-8"), hashlib.sha256
        ).digest()
        region_key = hmac.new(date_key, region.encode("utf-8"), hashlib.sha256).digest()
        service_key = hmac.new(region_key, b"s3", hashlib.sha256).digest()
        return hmac.new(service_key, b"aws4_request", hashlib.sha256).digest()

    def _request(
        self, method: str, key: str, *, payload: bytes | None = None
    ) -> tuple[int, bytes]:
        url = self._url(key)
        parsed = urlsplit(url)
        now = datetime.now(timezone.utc)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        datestamp = now.strftime("%Y%m%d")
        body = payload or b""
        payload_hash = hashlib.sha256(body).hexdigest()
        headers: dict[str, str] = {
            "host": parsed.netloc,
            "x-amz-content-sha256": payload_hash,
            "x-amz-date": amz_date,
        }
        if self.settings.session_token:
            headers["x-amz-security-token"] = self.settings.session_token
        if self.settings.server_side_encryption and method == "PUT":
            headers["x-amz-server-side-encryption"] = self.settings.server_side_encryption
        canonical_uri = parsed.path or "/"
        names = sorted(headers)
        canonical_headers = "".join(f"{name}:{headers[name]}\n" for name in names)
        signed_headers = ";".join(names)
        canonical_request = "\n".join(
            (method, canonical_uri, "", canonical_headers, signed_headers, payload_hash)
        )
        scope = f"{datestamp}/{self.settings.region}/s3/aws4_request"
        string_to_sign = "\n".join(
            (
                "AWS4-HMAC-SHA256",
                amz_date,
                scope,
                hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
            )
        )
        signature = hmac.new(
            self._signing_key(self.settings.secret_key, datestamp, self.settings.region),
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        request_headers = {
            "Host": parsed.netloc,
            "x-amz-content-sha256": payload_hash,
            "x-amz-date": amz_date,
            "Authorization": (
                "AWS4-HMAC-SHA256 "
                f"Credential={self.settings.access_key}/{scope}, "
                f"SignedHeaders={signed_headers}, Signature={signature}"
            ),
        }
        if self.settings.session_token:
            request_headers["x-amz-security-token"] = self.settings.session_token
        if self.settings.server_side_encryption and method == "PUT":
            request_headers["x-amz-server-side-encryption"] = (
                self.settings.server_side_encryption
            )
        request = Request(
            url,
            data=body if method == "PUT" else None,
            method=method,
            headers=request_headers,
        )
        try:
            with urlopen(request, timeout=self.settings.read_timeout) as response:
                return int(response.status), response.read(self.max_bytes + 1)
        except HTTPError as exc:
            if exc.code == 404:
                raise DocumentContentNotFound("DOCUMENT_CONTENT_NOT_FOUND") from exc
            raise DocumentStorageError(
                f"DOCUMENT_STORAGE_OBJECT_UNAVAILABLE:{exc.code}"
            ) from exc
        except URLError as exc:
            raise DocumentStorageError("DOCUMENT_STORAGE_OBJECT_UNAVAILABLE") from exc

    # -- port --------------------------------------------------------------
    def put(
        self,
        *,
        tenant_id: str,
        project_id: str,
        content_hash: str,
        extension: str,
        data: bytes,
    ) -> str:
        if not isinstance(data, (bytes, bytearray)):
            raise DocumentStorageError("INVALID_DOCUMENT_CONTENT")
        payload = bytes(data)
        if not payload:
            raise DocumentStorageError("EMPTY_DOCUMENT_CONTENT")
        if len(payload) > self.max_bytes:
            raise DocumentContentTooLarge("DOCUMENT_CONTENT_TOO_LARGE")
        digest = content_hash.split("sha256:", 1)[-1]
        if hashlib.sha256(payload).hexdigest() != digest:
            raise DocumentContentHashMismatch("DOCUMENT_CONTENT_HASH_MISMATCH")
        parts = document_object_parts(
            tenant_id=tenant_id,
            project_id=project_id,
            content_hash=content_hash,
            extension=extension,
        )
        self._request("PUT", self._key(parts), payload=payload)
        return self._reference(parts)

    def read(
        self,
        storage_ref: str,
        *,
        tenant_id: str,
        project_id: str,
        expected_content_hash: str,
    ) -> bytes:
        key, ref_hash = self._resolve(
            storage_ref, tenant_id=tenant_id, project_id=project_id
        )
        expected = expected_content_hash or ref_hash
        if expected != ref_hash:
            raise DocumentContentHashMismatch("DOCUMENT_CONTENT_HASH_MISMATCH")
        _, payload = self._request("GET", key)
        if len(payload) > self.max_bytes:
            raise DocumentContentTooLarge("DOCUMENT_CONTENT_TOO_LARGE")
        if hashlib.sha256(payload).hexdigest() != ref_hash.split(":", 1)[-1]:
            raise DocumentContentIntegrityError("DOCUMENT_CONTENT_INTEGRITY_FAILED")
        return payload

    def delete(
        self,
        storage_ref: str,
        *,
        tenant_id: str,
        project_id: str,
    ) -> None:
        key, _ = self._resolve(storage_ref, tenant_id=tenant_id, project_id=project_id)
        try:
            self._request("DELETE", key)
        except DocumentContentNotFound:
            return


_S3_ENVIRONMENT = {
    "endpoint_url": "CONSTRUCTION_PM_S3_ENDPOINT_URL",
    "bucket": "CONSTRUCTION_PM_S3_BUCKET",
    "region": "CONSTRUCTION_PM_S3_REGION",
    "access_key": "CONSTRUCTION_PM_S3_ACCESS_KEY",
    "secret_key": "CONSTRUCTION_PM_S3_SECRET_KEY",
    "prefix": "CONSTRUCTION_PM_S3_PREFIX",
    "server_side_encryption": "CONSTRUCTION_PM_S3_SSE",
    "session_token": "CONSTRUCTION_PM_S3_SESSION_TOKEN",
}


def s3_settings_from_environment(
    environ: Mapping[str, str] | None = None,
) -> DocumentObjectStorageSettings:
    env = os.environ if environ is None else environ
    missing = [
        name
        for key, name in _S3_ENVIRONMENT.items()
        if key not in {"prefix", "server_side_encryption", "session_token"}
        and not (env.get(name) or "").strip()
    ]
    if missing:
        raise DocumentStorageConfigurationError(
            "MISSING_DOCUMENT_STORAGE_CONFIGURATION:" + ",".join(missing)
        )
    path_style = (env.get("CONSTRUCTION_PM_S3_PATH_STYLE") or "true").strip().lower()
    if path_style not in {"true", "1", "yes", "false", "0", "no"}:
        raise DocumentStorageConfigurationError(
            "INVALID_DOCUMENT_STORAGE_PATH_STYLE"
        )
    settings = DocumentObjectStorageSettings(
        endpoint_url=(env.get(_S3_ENVIRONMENT["endpoint_url"]) or "").strip(),
        bucket=(env.get(_S3_ENVIRONMENT["bucket"]) or "").strip(),
        region=(env.get(_S3_ENVIRONMENT["region"]) or "").strip(),
        access_key=(env.get(_S3_ENVIRONMENT["access_key"]) or "").strip(),
        secret_key=(env.get(_S3_ENVIRONMENT["secret_key"]) or "").strip(),
        prefix=(env.get(_S3_ENVIRONMENT["prefix"]) or "documents").strip(),
        path_style=path_style in {"true", "1", "yes"},
        server_side_encryption=(
            env.get(_S3_ENVIRONMENT["server_side_encryption"]) or None
        ),
        session_token=(env.get(_S3_ENVIRONMENT["session_token"]) or None),
    )
    settings.validate()
    return settings


def build_document_storage_from_environment(
    *,
    local_root: str | os.PathLike[str],
    environ: Mapping[str, str] | None = None,
    production: bool | None = None,
    max_bytes: int = DEFAULT_MAX_DOCUMENT_BYTES,
) -> DocumentBinaryStorage:
    """Select the adapter explicitly; never fall back in production."""
    env = os.environ if environ is None else environ
    if production is None:
        production = (env.get("CONSTRUCTION_PM_ENVIRONMENT") or "").strip().lower() in {
            "production",
            "prod",
        }
    kind = (env.get("CONSTRUCTION_PM_DOCUMENT_STORAGE") or "").strip().lower()
    if not kind:
        if production:
            raise DocumentStorageConfigurationError(
                "DOCUMENT_STORAGE_CONFIGURATION_REQUIRED"
            )
        kind = "local"
    if kind not in DOCUMENT_STORAGE_KINDS:
        raise DocumentStorageConfigurationError("INVALID_DOCUMENT_STORAGE_KIND")
    if kind == "local":
        if production:
            raise DocumentStorageConfigurationError(
                "DOCUMENT_STORAGE_LOCAL_FORBIDDEN_IN_PRODUCTION"
            )
        return LocalDocumentStorage(Path(local_root), max_bytes=max_bytes)
    return S3CompatibleDocumentStorage(
        s3_settings_from_environment(env), max_bytes=max_bytes
    )


__all__ = [
    "DOCUMENT_STORAGE_KINDS",
    "S3_STORAGE_REF_PREFIX",
    "DocumentObjectStorageSettings",
    "DocumentStorageConfigurationError",
    "S3CompatibleDocumentStorage",
    "build_document_storage_from_environment",
    "s3_settings_from_environment",
]
