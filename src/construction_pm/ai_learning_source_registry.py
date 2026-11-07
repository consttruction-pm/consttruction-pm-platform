from __future__ import annotations

import ipaddress
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from types import MappingProxyType
from typing import Mapping
from urllib.parse import urlsplit


REGISTRY_ID = "cubi.project_management.sources"
REGISTRY_VERSION = "1.0.0"
EXPECTED_SOURCE_COUNT = 17
MAX_REGISTRY_BYTES = 1_048_576
_INGESTION_USE = "persistent_full_text_ingestion"
_SOURCE_ID_PATTERN = re.compile(r"^[A-Z0-9]+(?:-[A-Z0-9]+)*$")
_DOMAIN_LABEL_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
_FORBIDDEN_BODY_KEYS = {
    "body",
    "content",
    "conversation",
    "document_text",
    "extracted_text",
    "full_text",
    "html",
    "ocr_text",
    "payload",
    "pdf_bytes",
    "raw_text",
    "source_text",
    "transcript",
}
_ROOT_KEYS = {
    "registry_id",
    "registry_version",
    "registered_at",
    "authority",
    "video_sources_enabled",
    "ingestion_policy",
    "sources",
}
_SOURCE_REQUIRED_KEYS = {
    "id",
    "title",
    "publisher",
    "tier",
    "priority",
    "topics",
    "publication_status",
    "rights_status",
    "persistent_full_text_ingestion_allowed",
}
_SOURCE_OPTIONAL_KEYS = {
    "document_id",
    "edition",
    "issued",
    "pages",
    "accessible_pages",
    "errata_updated",
    "pdf_url",
    "html_url",
    "index_url",
    "purchase_url",
    "public_toc_pdf_url",
    "landing_url",
    "govuk_url",
    "official_url",
    "accessible_pdf_url",
    "fixed_version_pdf_url",
    "jurisdiction",
    "notes",
    "rights_review",
    "ingestion_authorization",
}
_RIGHTS_REVIEW_KEYS = {
    "decision",
    "approval_id",
    "approved_by",
    "approved_at",
    "license_id",
    "permitted_uses",
    "evidence_ref",
}
_INGESTION_AUTHORIZATION_KEYS = {
    "decision",
    "authorization_id",
    "authorized_by",
    "authorized_at",
    "permitted_uses",
    "evidence_ref",
}


class SourceRegistryError(ValueError):
    """Raised when source-registry metadata is invalid or unsafe."""


@dataclass(frozen=True)
class KnowledgeSource:
    """Validated source metadata. This type never stores source-document bodies."""

    source_id: str
    title: str
    publisher: str
    tier: str
    priority: str
    topics: tuple[str, ...]
    publication_status: str
    rights_status: str
    persistent_full_text_ingestion_allowed: bool
    urls: Mapping[str, str]
    metadata: Mapping[str, object]

    @property
    def ingestion_authorized(self) -> bool:
        """True only when both a recorded rights review and an explicit authorization exist."""
        return self.persistent_full_text_ingestion_allowed


@dataclass(frozen=True)
class SourceRegistry:
    registry_id: str
    registry_version: str
    registered_at: date
    authority: str
    ingestion_policy: str
    sources: tuple[KnowledgeSource, ...]

    def get(self, source_id: str) -> KnowledgeSource | None:
        return next((item for item in self.sources if item.source_id == source_id), None)


def _require_string(value: object, field: str, *, max_length: int = 512) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > max_length
        or value != value.strip()
    ):
        raise SourceRegistryError(f"SOURCE_REGISTRY_INVALID_STRING:{field}")
    return value


def _freeze_json(value: object) -> object:
    if isinstance(value, dict):
        return MappingProxyType({
            str(key): _freeze_json(item) for key, item in value.items()
        })
    if isinstance(value, list):
        return tuple(_freeze_json(item) for item in value)
    return value


def _reject_embedded_bodies(value: object, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).strip().lower().replace("-", "_")
            if normalized in _FORBIDDEN_BODY_KEYS:
                raise SourceRegistryError(
                    f"SOURCE_REGISTRY_EMBEDDED_DOCUMENT_BODY_FORBIDDEN:{path}.{key}"
                )
            _reject_embedded_bodies(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_embedded_bodies(child, f"{path}[{index}]")


def _validate_public_https_url(value: object, field: str) -> str:
    url = _require_string(value, field, max_length=2048)
    if any(ord(char) < 32 for char in url):
        raise SourceRegistryError(f"SOURCE_REGISTRY_URL_INVALID:{field}")
    try:
        parsed = urlsplit(url)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise SourceRegistryError(f"SOURCE_REGISTRY_URL_INVALID:{field}") from exc

    if (
        parsed.scheme.lower() != "https"
        or not parsed.netloc
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise SourceRegistryError(f"SOURCE_REGISTRY_URL_MUST_BE_PUBLIC_HTTPS:{field}")
    if port is not None and not 1 <= port <= 65535:
        raise SourceRegistryError(f"SOURCE_REGISTRY_URL_PORT_INVALID:{field}")

    host = hostname.rstrip(".").lower()
    if not host or host in {"localhost", "localhost.localdomain"}:
        raise SourceRegistryError(f"SOURCE_REGISTRY_URL_HOST_NOT_PUBLIC:{field}")
    if host.endswith((".localhost", ".local", ".internal", ".test", ".invalid")):
        raise SourceRegistryError(f"SOURCE_REGISTRY_URL_HOST_NOT_PUBLIC:{field}")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None:
        if not address.is_global:
            raise SourceRegistryError(f"SOURCE_REGISTRY_URL_HOST_NOT_PUBLIC:{field}")
        raise SourceRegistryError(f"SOURCE_REGISTRY_URL_IP_LITERAL_FORBIDDEN:{field}")

    try:
        ascii_host = host.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise SourceRegistryError(f"SOURCE_REGISTRY_URL_HOST_INVALID:{field}") from exc
    labels = ascii_host.split(".")
    if len(labels) < 2 or any(not _DOMAIN_LABEL_PATTERN.fullmatch(label) for label in labels):
        raise SourceRegistryError(f"SOURCE_REGISTRY_URL_HOST_INVALID:{field}")
    return url


def _validate_timestamp(value: object, field: str) -> None:
    stamp = _require_string(value, field, max_length=64)
    try:
        parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SourceRegistryError(f"SOURCE_REGISTRY_TIMESTAMP_INVALID:{field}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SourceRegistryError(f"SOURCE_REGISTRY_TIMESTAMP_MUST_BE_TIMEZONE_AWARE:{field}")


def _validate_rights_review(value: object) -> None:
    if not isinstance(value, dict) or set(value) != _RIGHTS_REVIEW_KEYS:
        raise SourceRegistryError("SOURCE_REGISTRY_RIGHTS_REVIEW_INCOMPLETE")
    if value.get("decision") != "approved":
        raise SourceRegistryError("SOURCE_REGISTRY_RIGHTS_REVIEW_NOT_APPROVED")
    for field in ("approval_id", "approved_by", "license_id", "evidence_ref"):
        _require_string(value.get(field), f"rights_review.{field}", max_length=256)
    _validate_timestamp(value.get("approved_at"), "rights_review.approved_at")
    uses = value.get("permitted_uses")
    if (
        not isinstance(uses, list)
        or any(not isinstance(item, str) for item in uses)
        or _INGESTION_USE not in uses
    ):
        raise SourceRegistryError("SOURCE_REGISTRY_RIGHTS_USE_NOT_GRANTED")


def _validate_ingestion_authorization(value: object) -> None:
    if not isinstance(value, dict) or set(value) != _INGESTION_AUTHORIZATION_KEYS:
        raise SourceRegistryError("SOURCE_REGISTRY_INGESTION_AUTHORIZATION_INCOMPLETE")
    if value.get("decision") != "authorized":
        raise SourceRegistryError("SOURCE_REGISTRY_INGESTION_NOT_AUTHORIZED")
    for field in ("authorization_id", "authorized_by", "evidence_ref"):
        _require_string(value.get(field), f"ingestion_authorization.{field}", max_length=256)
    _validate_timestamp(value.get("authorized_at"), "ingestion_authorization.authorized_at")
    uses = value.get("permitted_uses")
    if (
        not isinstance(uses, list)
        or any(not isinstance(item, str) for item in uses)
        or _INGESTION_USE not in uses
    ):
        raise SourceRegistryError("SOURCE_REGISTRY_INGESTION_USE_NOT_AUTHORIZED")


def _validate_source(raw: object, index: int) -> KnowledgeSource:
    if not isinstance(raw, dict):
        raise SourceRegistryError(f"SOURCE_REGISTRY_SOURCE_NOT_OBJECT:{index}")
    _reject_embedded_bodies(raw)
    unknown = set(raw) - _SOURCE_REQUIRED_KEYS - _SOURCE_OPTIONAL_KEYS
    missing = _SOURCE_REQUIRED_KEYS - set(raw)
    if unknown:
        raise SourceRegistryError(
            f"SOURCE_REGISTRY_SOURCE_UNKNOWN_FIELDS:{index}:{','.join(sorted(unknown))}"
        )
    if missing:
        raise SourceRegistryError(
            f"SOURCE_REGISTRY_SOURCE_REQUIRED_FIELDS_MISSING:{index}:{','.join(sorted(missing))}"
        )

    source_id = _require_string(raw["id"], f"sources[{index}].id", max_length=96)
    if not _SOURCE_ID_PATTERN.fullmatch(source_id):
        raise SourceRegistryError(f"SOURCE_REGISTRY_SOURCE_ID_INVALID:{source_id}")

    title = _require_string(raw["title"], f"sources[{index}].title", max_length=512)
    publisher = _require_string(raw["publisher"], f"sources[{index}].publisher", max_length=256)
    tier = _require_string(raw["tier"], f"sources[{index}].tier", max_length=96)
    priority = _require_string(raw["priority"], f"sources[{index}].priority", max_length=32)
    publication_status = _require_string(
        raw["publication_status"], f"sources[{index}].publication_status", max_length=128
    )
    rights_status = _require_string(
        raw["rights_status"], f"sources[{index}].rights_status", max_length=160
    )

    topics_raw = raw["topics"]
    if (
        not isinstance(topics_raw, list)
        or not topics_raw
        or any(not isinstance(topic, str) or not topic.strip() for topic in topics_raw)
    ):
        raise SourceRegistryError(f"SOURCE_REGISTRY_TOPICS_INVALID:{source_id}")
    topics = tuple(topic.strip() for topic in topics_raw)
    if len({topic.casefold() for topic in topics}) != len(topics):
        raise SourceRegistryError(f"SOURCE_REGISTRY_TOPICS_DUPLICATE:{source_id}")

    for field in ("pages", "accessible_pages"):
        if field in raw:
            value = raw[field]
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise SourceRegistryError(f"SOURCE_REGISTRY_PAGE_COUNT_INVALID:{source_id}:{field}")

    for field in (
        "document_id", "edition", "issued", "errata_updated", "jurisdiction", "notes"
    ):
        if field in raw:
            _require_string(raw[field], f"sources[{index}].{field}", max_length=2048)

    urls: dict[str, str] = {}
    for field, value in raw.items():
        if field.endswith("_url"):
            urls[field] = _validate_public_https_url(value, f"sources[{index}].{field}")

    allowed = raw["persistent_full_text_ingestion_allowed"]
    if allowed is True:
        if rights_status != "approved_for_persistent_ingestion":
            raise SourceRegistryError(
                f"SOURCE_REGISTRY_RIGHTS_STATUS_NOT_APPROVED:{source_id}"
            )
        _validate_rights_review(raw.get("rights_review"))
        _validate_ingestion_authorization(raw.get("ingestion_authorization"))
    elif allowed is False:
        if "rights_review" in raw or "ingestion_authorization" in raw:
            raise SourceRegistryError(
                f"SOURCE_REGISTRY_INCONSISTENT_INGESTION_METADATA:{source_id}"
            )
    elif isinstance(allowed, str) and allowed.strip():
        if "rights_review" in raw or "ingestion_authorization" in raw:
            raise SourceRegistryError(
                f"SOURCE_REGISTRY_UNAPPROVED_RIGHTS_METADATA:{source_id}"
            )
    else:
        raise SourceRegistryError(
            f"SOURCE_REGISTRY_INGESTION_POLICY_MUST_DEFAULT_DENY:{source_id}"
        )

    metadata = _freeze_json(dict(raw))
    return KnowledgeSource(
        source_id=source_id,
        title=title,
        publisher=publisher,
        tier=tier,
        priority=priority,
        topics=topics,
        publication_status=publication_status,
        rights_status=rights_status,
        persistent_full_text_ingestion_allowed=(allowed is True),
        urls=MappingProxyType(urls),
        metadata=metadata,  # type: ignore[arg-type]
    )


def validate_source_registry(payload: object) -> SourceRegistry:
    """Validate registry metadata without opening or downloading any source URL."""
    if not isinstance(payload, dict):
        raise SourceRegistryError("SOURCE_REGISTRY_ROOT_MUST_BE_OBJECT")
    _reject_embedded_bodies(payload)
    unknown = set(payload) - _ROOT_KEYS
    missing = _ROOT_KEYS - set(payload)
    if unknown:
        raise SourceRegistryError(
            "SOURCE_REGISTRY_UNKNOWN_FIELDS:" + ",".join(sorted(unknown))
        )
    if missing:
        raise SourceRegistryError(
            "SOURCE_REGISTRY_REQUIRED_FIELDS_MISSING:" + ",".join(sorted(missing))
        )

    if payload["registry_id"] != REGISTRY_ID:
        raise SourceRegistryError("SOURCE_REGISTRY_ID_UNSUPPORTED")
    if payload["registry_version"] != REGISTRY_VERSION:
        raise SourceRegistryError("SOURCE_REGISTRY_VERSION_UNSUPPORTED")
    registered_at_raw = _require_string(payload["registered_at"], "registered_at", max_length=32)
    try:
        registered_at = date.fromisoformat(registered_at_raw)
    except ValueError as exc:
        raise SourceRegistryError("SOURCE_REGISTRY_REGISTERED_AT_INVALID") from exc
    authority = _require_string(payload["authority"], "authority", max_length=256)
    ingestion_policy = _require_string(
        payload["ingestion_policy"], "ingestion_policy", max_length=256
    )
    if payload["video_sources_enabled"] is not False:
        raise SourceRegistryError("SOURCE_REGISTRY_VIDEO_SOURCES_MUST_BE_DISABLED")

    raw_sources = payload["sources"]
    if not isinstance(raw_sources, list) or len(raw_sources) != EXPECTED_SOURCE_COUNT:
        raise SourceRegistryError(
            f"SOURCE_REGISTRY_SOURCE_COUNT_INVALID:expected={EXPECTED_SOURCE_COUNT}"
        )

    sources = tuple(_validate_source(item, index) for index, item in enumerate(raw_sources))
    canonical_ids = [item.source_id.casefold() for item in sources]
    if len(set(canonical_ids)) != len(canonical_ids):
        raise SourceRegistryError("SOURCE_REGISTRY_DUPLICATE_SOURCE_ID")
    return SourceRegistry(
        registry_id=REGISTRY_ID,
        registry_version=REGISTRY_VERSION,
        registered_at=registered_at,
        authority=authority,
        ingestion_policy=ingestion_policy,
        sources=sources,
    )


def load_source_registry(path: str | Path) -> SourceRegistry:
    """Read a bounded local JSON metadata file; performs no network or body ingestion."""
    registry_path = Path(path)
    try:
        size = registry_path.stat().st_size
        if size <= 0 or size > MAX_REGISTRY_BYTES:
            raise SourceRegistryError("SOURCE_REGISTRY_FILE_SIZE_INVALID")
        raw = registry_path.read_bytes()
    except SourceRegistryError:
        raise
    except OSError as exc:
        raise SourceRegistryError("SOURCE_REGISTRY_FILE_UNAVAILABLE") from exc
    if len(raw) > MAX_REGISTRY_BYTES:
        raise SourceRegistryError("SOURCE_REGISTRY_FILE_SIZE_INVALID")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceRegistryError("SOURCE_REGISTRY_JSON_INVALID") from exc
    return validate_source_registry(payload)


__all__ = [
    "KnowledgeSource",
    "REGISTRY_ID",
    "REGISTRY_VERSION",
    "SourceRegistry",
    "SourceRegistryError",
    "load_source_registry",
    "validate_source_registry",
]
