"""Malware scanning contract for uploaded document bytes.

Scanning happens before bytes are committed to a version. A deterministic
reference scanner keeps development and contract tests hermetic; a production
deployment must inject a real engine adapter and set ``require_scanned_content``
so unscanned or failed content is never served as clean.

No scanner is embedded here and no network call is made. The reference scanner
recognises only the public antivirus test marker; it is not an antivirus.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

SCAN_STATUSES = ("clean", "infected", "failed", "unscanned")

EICAR_MARKER = b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE"


class DocumentScanError(ValueError):
    pass


class DocumentScanRejected(DocumentScanError):
    """The payload is known-malicious; it must not be stored or served."""


class DocumentScanUnavailable(DocumentScanError):
    """No trustworthy verdict is available; strict mode must fail closed."""


@dataclass(frozen=True)
class ScanVerdict:
    status: str
    engine: str
    engine_version: str
    detail: str = ""

    def validate(self) -> None:
        if self.status not in SCAN_STATUSES:
            raise DocumentScanError("INVALID_DOCUMENT_SCAN_STATUS")
        if not isinstance(self.engine, str) or not self.engine.strip():
            raise DocumentScanError("INVALID_DOCUMENT_SCAN_ENGINE")
        if not isinstance(self.engine_version, str) or not self.engine_version.strip():
            raise DocumentScanError("INVALID_DOCUMENT_SCAN_VERSION")
        if not isinstance(self.detail, str):
            raise DocumentScanError("INVALID_DOCUMENT_SCAN_DETAIL")

    def as_dict(self) -> dict[str, str]:
        return {
            "status": self.status,
            "engine": self.engine,
            "engine_version": self.engine_version,
            "detail": self.detail,
        }


class DocumentScanner(Protocol):
    def scan(self, data: bytes, *, content_type: str) -> ScanVerdict: ...


class ReferenceDocumentScanner:
    """Deterministic test scanner; never a substitute for a production engine."""

    def __init__(self, markers: tuple[bytes, ...] = (EICAR_MARKER,)) -> None:
        self.markers = tuple(markers)

    def scan(self, data: bytes, *, content_type: str) -> ScanVerdict:
        if not isinstance(data, (bytes, bytearray)):
            raise DocumentScanError("INVALID_DOCUMENT_SCAN_PAYLOAD")
        payload = bytes(data)
        if any(marker and marker in payload for marker in self.markers):
            return ScanVerdict(
                status="infected",
                engine="reference",
                engine_version="1",
                detail="test signature matched",
            )
        return ScanVerdict(
            status="clean", engine="reference", engine_version="1"
        )


__all__ = [
    "EICAR_MARKER",
    "SCAN_STATUSES",
    "DocumentScanError",
    "DocumentScanRejected",
    "DocumentScanUnavailable",
    "DocumentScanner",
    "ReferenceDocumentScanner",
    "ScanVerdict",
]
