from __future__ import annotations

"""Binary document storage adapters separate from document metadata.

The metadata store keeps the authoritative record and audit trail; this module
owns only the bytes. A storage reference is content-addressed and derived from
server-validated values, so a client-supplied file name can never become a
filesystem path. References are scoped by tenant and project, which keeps
cross-tenant reads impossible even when a reference leaks.

Storage adapters implement :class:`DocumentBinaryStorage`. The local adapter is
used by the preview/desktop composition; server deployments can supply an
object-storage adapter implementing the same three methods without touching
the application layer.
"""

import hashlib
import io
import os
import re
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


STORAGE_REF_PREFIX = "local:v1"
DEFAULT_MAX_DOCUMENT_BYTES = 25 * 1024 * 1024

# The allow-list is deliberate: an upload is rejected unless the server can
# recognise the payload. HTML, SVG and scripts are never accepted.
_CONTENT_TYPE_EXTENSIONS: dict[str, str] = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/tiff": ".tiff",
    "image/webp": ".webp",
    "text/plain": ".txt",
    "text/csv": ".csv",
    "application/xml": ".xml",
    "text/xml": ".xml",
    "application/msword": ".doc",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
}
_EXTENSION_CONTENT_TYPES = {
    extension: content_type
    for content_type, extension in _CONTENT_TYPE_EXTENSIONS.items()
    if content_type not in {"application/xml", "text/xml"}
}
_SAFE_EXTENSION = re.compile(r"^\.[a-z0-9]{1,8}$")
_HEX16 = re.compile(r"^[0-9a-f]{16}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_HEX2 = re.compile(r"^[0-9a-f]{2}$")


class DocumentStorageError(ValueError):
    """Base class for binary document storage failures."""


class DocumentContentTooLarge(DocumentStorageError):
    pass


class DocumentContentTypeRejected(DocumentStorageError):
    pass


class DocumentContentHashMismatch(DocumentStorageError):
    pass


class DocumentContentIntegrityError(DocumentStorageError):
    pass


class DocumentContentNotFound(DocumentStorageError):
    pass


class DocumentContentQuarantined(DocumentStorageError):
    """Stored bytes exist but are not cleared for serving."""


def storage_scope_key(value: str) -> str:
    """Opaque, non-reversible tenant/project path segment."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def document_object_parts(
    *,
    tenant_id: str,
    project_id: str,
    content_hash: str,
    extension: str,
) -> tuple[str, str, str, str]:
    """Return the four content-addressed object path segments.

    Every segment is server-derived: tenant/project hashes, a two-character
    digest prefix and the digest plus an allow-listed extension. A caller never
    supplies a path.
    """
    digest = (
        content_hash.split("sha256:", 1)[-1]
        if content_hash.startswith("sha256:")
        else content_hash
    )
    if not _HEX64.match(digest):
        raise DocumentStorageError("INVALID_DOCUMENT_CONTENT_HASH")
    if extension not in _CONTENT_TYPE_EXTENSIONS.values() or not _SAFE_EXTENSION.match(
        extension or ""
    ):
        raise DocumentContentTypeRejected("DOCUMENT_CONTENT_TYPE_REJECTED")
    return (
        storage_scope_key(tenant_id),
        storage_scope_key(project_id),
        digest[:2],
        f"{digest}{extension}",
    )


@dataclass(frozen=True)
class DocumentBlob:
    """Server-validated payload facts; the original file name is display-only."""

    content_hash: str
    byte_size: int
    content_type: str
    extension: str
    original_filename: str

    def validate(self) -> None:
        if not self.content_hash.startswith("sha256:") or len(self.content_hash) != 71:
            raise DocumentStorageError("INVALID_DOCUMENT_CONTENT_HASH")
        if isinstance(self.byte_size, bool) or self.byte_size < 0:
            raise DocumentStorageError("INVALID_DOCUMENT_CONTENT_SIZE")
        if self.content_type not in _CONTENT_TYPE_EXTENSIONS:
            raise DocumentContentTypeRejected("DOCUMENT_CONTENT_TYPE_REJECTED")
        if _EXTENSION_CONTENT_TYPES.get(self.extension) is None:
            raise DocumentContentTypeRejected("DOCUMENT_CONTENT_TYPE_REJECTED")
        if not isinstance(self.original_filename, str) or not self.original_filename.strip():
            raise DocumentStorageError("INVALID_DOCUMENT_FILENAME")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sanitize_document_filename(value: str | None) -> str:
    """Return a display-only basename with no path or control characters."""
    if not isinstance(value, str) or not value.strip():
        return "document"
    normalized = value.replace("\\", "/")
    base = normalized.rsplit("/", 1)[-1]
    base = "".join(character for character in base if character.isprintable())
    base = " ".join(base.split()).strip()
    if base in {"", ".", ".."}:
        return "document"
    return base[:200]


def _looks_like_text(data: bytes) -> bool:
    if b"\x00" in data:
        return False
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def _zip_content_type(data: bytes) -> str | None:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = set(archive.namelist())
    except (zipfile.BadZipFile, OSError):
        return None
    if "[Content_Types].xml" not in names:
        return None
    if any(name.startswith("word/") for name in names):
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if any(name.startswith("xl/") for name in names):
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    if any(name.startswith("ppt/") for name in names):
        return "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    return None


def sniff_document_content_type(data: bytes) -> str | None:
    """Detect the payload type from its bytes; never trust the declared header alone."""
    if not isinstance(data, (bytes, bytearray)) or not data:
        return None
    payload = bytes(data)
    if payload.startswith(b"%PDF-"):
        return "application/pdf"
    if payload.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if payload.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if payload.startswith((b"II*\x00", b"MM\x00*")):
        return "image/tiff"
    if payload[:4] == b"RIFF" and payload[8:12] == b"WEBP":
        return "image/webp"
    if payload.startswith(b"PK\x03\x04"):
        return _zip_content_type(payload)
    if payload.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        # Legacy OLE container: Word and Excel share the signature. The declared
        # type decides between the two and both remain in the allow-list.
        return "application/vnd.ms-office"
    if _looks_like_text(payload):
        stripped = payload.lstrip()
        if stripped.startswith(b"<?xml") or (
            stripped.startswith(b"<") and stripped.endswith(b">")
        ):
            return "application/xml"
        return "text/plain"
    return None


def validate_document_content(
    data: bytes,
    *,
    declared_content_type: str,
    filename: str | None = None,
    max_bytes: int = DEFAULT_MAX_DOCUMENT_BYTES,
) -> DocumentBlob:
    """Validate an upload and return server-derived facts.

    The declared content type must be allow-listed *and* consistent with the
    sniffed payload. Text payloads accept the text family, XML accepts both XML
    spellings, and OLE payloads accept the two declared legacy Office types.
    """
    if not isinstance(data, (bytes, bytearray)):
        raise DocumentContentTypeRejected("DOCUMENT_CONTENT_TYPE_REJECTED")
    payload = bytes(data)
    if not payload:
        raise DocumentStorageError("EMPTY_DOCUMENT_CONTENT")
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes <= 0:
        raise DocumentStorageError("INVALID_DOCUMENT_CONTENT_LIMIT")
    if len(payload) > max_bytes:
        raise DocumentContentTooLarge("DOCUMENT_CONTENT_TOO_LARGE")

    normalized_type = (declared_content_type or "").split(";", 1)[0].strip().lower()
    if normalized_type not in _CONTENT_TYPE_EXTENSIONS:
        raise DocumentContentTypeRejected("DOCUMENT_CONTENT_TYPE_REJECTED")

    sniffed = sniff_document_content_type(payload)
    if sniffed is None:
        raise DocumentContentTypeRejected("DOCUMENT_CONTENT_TYPE_UNRECOGNIZED")

    accepted = {sniffed}
    if sniffed == "text/plain":
        accepted = {"text/plain", "text/csv"}
    elif sniffed == "application/xml":
        accepted = {"application/xml", "text/xml"}
    elif sniffed == "application/vnd.ms-office":
        accepted = {"application/msword", "application/vnd.ms-excel"}
    if normalized_type not in accepted:
        raise DocumentContentTypeRejected("DOCUMENT_CONTENT_TYPE_MISMATCH")

    extension = _CONTENT_TYPE_EXTENSIONS[normalized_type]
    return DocumentBlob(
        content_hash=f"sha256:{_sha256_hex(payload)}",
        byte_size=len(payload),
        content_type=normalized_type,
        extension=extension,
        original_filename=sanitize_document_filename(filename),
    )


class DocumentBinaryStorage(Protocol):
    """Byte-level storage boundary; metadata stays in the document store."""

    def put(
        self,
        *,
        tenant_id: str,
        project_id: str,
        content_hash: str,
        extension: str,
        data: bytes,
    ) -> str: ...

    def read(
        self,
        storage_ref: str,
        *,
        tenant_id: str,
        project_id: str,
        expected_content_hash: str,
    ) -> bytes: ...

    def delete(
        self,
        storage_ref: str,
        *,
        tenant_id: str,
        project_id: str,
    ) -> None: ...


class LocalDocumentStorage:
    """Filesystem adapter with content-addressed, tenant-scoped paths.

    Path components are derived exclusively from SHA-256 digests and a fixed
    extension allow-list. Reads use ``O_NOFOLLOW`` and re-verify the digest, so
    a tampered or swapped file fails closed instead of being served.
    """

    def __init__(self, root: str | os.PathLike[str], *, max_bytes: int = DEFAULT_MAX_DOCUMENT_BYTES) -> None:
        if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes <= 0:
            raise ValueError("INVALID_DOCUMENT_CONTENT_LIMIT")
        self.root = Path(root).expanduser().resolve()
        self.max_bytes = max_bytes
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _scope_key(value: str) -> str:
        return storage_scope_key(value)

    def _relative_parts(
        self,
        tenant_id: str,
        project_id: str,
        content_hash: str,
        extension: str,
    ) -> tuple[str, ...]:
        return document_object_parts(
            tenant_id=tenant_id,
            project_id=project_id,
            content_hash=content_hash,
            extension=extension,
        )

    def _resolve(
        self,
        storage_ref: str,
        *,
        tenant_id: str,
        project_id: str,
    ) -> tuple[Path, str]:
        if not isinstance(storage_ref, str) or not storage_ref.startswith(f"{STORAGE_REF_PREFIX}/"):
            raise DocumentStorageError("INVALID_DOCUMENT_STORAGE_REF")
        parts = storage_ref[len(STORAGE_REF_PREFIX) + 1:].split("/")
        if len(parts) != 4:
            raise DocumentStorageError("INVALID_DOCUMENT_STORAGE_REF")
        tenant_key, project_key, prefix, name = parts
        if not (_HEX16.match(tenant_key) and _HEX16.match(project_key) and _HEX2.match(prefix)):
            raise DocumentStorageError("INVALID_DOCUMENT_STORAGE_REF")
        stem, extension = os.path.splitext(name)
        if not _HEX64.match(stem) or not stem.startswith(prefix) or not _SAFE_EXTENSION.match(extension):
            raise DocumentStorageError("INVALID_DOCUMENT_STORAGE_REF")
        if tenant_key != self._scope_key(tenant_id) or project_key != self._scope_key(project_id):
            raise DocumentStorageError("DOCUMENT_STORAGE_SCOPE_MISMATCH")
        candidate = (self.root / tenant_key / project_key / prefix / name).resolve()
        if not str(candidate).startswith(str(self.root) + os.sep):
            raise DocumentStorageError("DOCUMENT_STORAGE_PATH_ESCAPE")
        return candidate, f"sha256:{stem}"

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
        if _sha256_hex(payload) != digest:
            raise DocumentContentHashMismatch("DOCUMENT_CONTENT_HASH_MISMATCH")

        tenant_key, project_key, prefix, name = self._relative_parts(
            tenant_id, project_id, content_hash, extension
        )
        directory = self.root / tenant_key / project_key / prefix
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / name
        if target.exists():
            if target.stat().st_size != len(payload):
                raise DocumentContentIntegrityError("DOCUMENT_CONTENT_INTEGRITY_FAILED")
            return f"{STORAGE_REF_PREFIX}/{tenant_key}/{project_key}/{prefix}/{name}"

        handle, temporary_name = tempfile.mkstemp(prefix=".upload-", dir=directory)
        try:
            with os.fdopen(handle, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temporary_name, 0o600)
            os.replace(temporary_name, target)
        except BaseException:
            try:
                os.unlink(temporary_name)
            except OSError:
                pass
            raise
        return f"{STORAGE_REF_PREFIX}/{tenant_key}/{project_key}/{prefix}/{name}"

    def read(
        self,
        storage_ref: str,
        *,
        tenant_id: str,
        project_id: str,
        expected_content_hash: str,
    ) -> bytes:
        path, ref_hash = self._resolve(
            storage_ref, tenant_id=tenant_id, project_id=project_id
        )
        expected = expected_content_hash or ref_hash
        if expected != ref_hash:
            raise DocumentContentHashMismatch("DOCUMENT_CONTENT_HASH_MISMATCH")
        if not path.is_file():
            raise DocumentContentNotFound("DOCUMENT_CONTENT_NOT_FOUND")
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(path, flags)
        except FileNotFoundError as exc:
            raise DocumentContentNotFound("DOCUMENT_CONTENT_NOT_FOUND") from exc
        with os.fdopen(descriptor, "rb") as stream:
            payload = stream.read(self.max_bytes + 1)
        if len(payload) > self.max_bytes:
            raise DocumentContentTooLarge("DOCUMENT_CONTENT_TOO_LARGE")
        if _sha256_hex(payload) != ref_hash.split(":", 1)[-1]:
            raise DocumentContentIntegrityError("DOCUMENT_CONTENT_INTEGRITY_FAILED")
        return payload

    def delete(
        self,
        storage_ref: str,
        *,
        tenant_id: str,
        project_id: str,
    ) -> None:
        path, _ = self._resolve(storage_ref, tenant_id=tenant_id, project_id=project_id)
        try:
            path.unlink()
        except FileNotFoundError:
            return


def content_disposition(filename: str) -> str:
    """RFC 6266/5987 attachment header for a sanitized display name."""
    safe = sanitize_document_filename(filename)
    ascii_fallback = "".join(
        character if 32 <= ord(character) < 127 and character not in {'"', "\\"} else "_"
        for character in safe
    )
    from urllib.parse import quote

    return f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{quote(safe)}"


__all__ = [
    "DEFAULT_MAX_DOCUMENT_BYTES",
    "STORAGE_REF_PREFIX",
    "DocumentBinaryStorage",
    "DocumentBlob",
    "DocumentContentHashMismatch",
    "DocumentContentIntegrityError",
    "DocumentContentNotFound",
    "DocumentContentQuarantined",
    "DocumentContentTooLarge",
    "DocumentContentTypeRejected",
    "DocumentStorageError",
    "LocalDocumentStorage",
    "content_disposition",
    "document_object_parts",
    "sanitize_document_filename",
    "sniff_document_content_type",
    "storage_scope_key",
    "validate_document_content",
]
