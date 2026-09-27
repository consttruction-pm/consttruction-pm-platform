from __future__ import annotations

import pytest

from construction_pm.document_ocr import (
    DocumentOCRAdapterError,
    OCRRequest,
    ReferenceDocumentOCRAdapter,
)


def request(revision=1):
    return OCRRequest(
        tenant_id="tenant-1",
        project_id="project-1",
        document_id="doc-1",
        revision=revision,
        storage_ref="object://documents/doc-1/rev-1",
    )


def test_reference_ocr_adapter_preserves_scope_and_revision():
    result = ReferenceDocumentOCRAdapter("Structural drawing text").extract(request(revision=3))
    assert result.tenant_id == "tenant-1"
    assert result.project_id == "project-1"
    assert result.document_id == "doc-1"
    assert result.revision == 3
    assert result.text == "Structural drawing text"
    assert result.provider == "reference"


def test_ocr_request_rejects_invalid_revision_and_missing_storage_ref():
    with pytest.raises(DocumentOCRAdapterError, match="INVALID_DOCUMENT_OCR_REVISION"):
        ReferenceDocumentOCRAdapter("").extract(request(revision=0))
    with pytest.raises(DocumentOCRAdapterError, match="INVALID_DOCUMENT_OCR_STORAGE_REF"):
        ReferenceDocumentOCRAdapter("").extract(
            OCRRequest("tenant-1", "project-1", "doc-1", 1, "")
        )


def test_ocr_adapter_does_not_mutate_request():
    req = request()
    ReferenceDocumentOCRAdapter("text", provider="vendor-a").extract(req)
    assert req.revision == 1
    assert req.storage_ref == "object://documents/doc-1/rev-1"
