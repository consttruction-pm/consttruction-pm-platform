from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class DocumentOCRAdapterError(ValueError):
    pass


@dataclass(frozen=True)
class OCRRequest:
    tenant_id: str
    project_id: str
    document_id: str
    revision: int
    storage_ref: str

    def validate(self) -> None:
        for name, value in (
            ("tenant_id", self.tenant_id),
            ("project_id", self.project_id),
            ("document_id", self.document_id),
            ("storage_ref", self.storage_ref),
        ):
            if not isinstance(value, str) or not value.strip():
                raise DocumentOCRAdapterError(f"INVALID_DOCUMENT_OCR_{name.upper()}")
        if isinstance(self.revision, bool) or not isinstance(self.revision, int) or self.revision < 1:
            raise DocumentOCRAdapterError("INVALID_DOCUMENT_OCR_REVISION")


@dataclass(frozen=True)
class OCRResult:
    tenant_id: str
    project_id: str
    document_id: str
    revision: int
    text: str
    provider: str

    def validate(self) -> None:
        for name, value in (
            ("tenant_id", self.tenant_id),
            ("project_id", self.project_id),
            ("document_id", self.document_id),
            ("provider", self.provider),
        ):
            if not isinstance(value, str) or not value.strip():
                raise DocumentOCRAdapterError(f"INVALID_DOCUMENT_OCR_{name.upper()}")
        if isinstance(self.revision, bool) or not isinstance(self.revision, int) or self.revision < 1:
            raise DocumentOCRAdapterError("INVALID_DOCUMENT_OCR_REVISION")
        if not isinstance(self.text, str):
            raise DocumentOCRAdapterError("INVALID_DOCUMENT_OCR_TEXT")


class DocumentOCRAdapter(Protocol):
    def extract(self, request: OCRRequest) -> OCRResult: ...


class ReferenceDocumentOCRAdapter:
    """Deterministic adapter used by tests; no OCR engine or storage access is embedded."""

    def __init__(self, extracted_text: str, provider: str = "reference") -> None:
        self.extracted_text = extracted_text
        self.provider = provider

    def extract(self, request: OCRRequest) -> OCRResult:
        request.validate()
        if not isinstance(self.extracted_text, str):
            raise DocumentOCRAdapterError("INVALID_DOCUMENT_OCR_TEXT")
        result = OCRResult(
            tenant_id=request.tenant_id,
            project_id=request.project_id,
            document_id=request.document_id,
            revision=request.revision,
            text=self.extracted_text,
            provider=self.provider,
        )
        result.validate()
        return result
