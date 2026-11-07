from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from construction_pm.ai_learning_source_registry import (
    SourceRegistryError,
    load_source_registry,
    validate_source_registry,
)


REGISTRY_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "knowledge"
    / "source-registry.json"
)


def source_registry_payload():
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def test_registered_seventeen_source_catalogue_loads_as_metadata_only():
    registry = load_source_registry(REGISTRY_PATH)

    assert registry.registry_id == "cubi.project_management.sources"
    assert registry.registry_version == "1.0.0"
    assert len(registry.sources) == 17
    assert registry.get("P6-HELP-26") is not None
    assert registry.get("not-registered") is None
    assert all(not item.ingestion_authorized for item in registry.sources)
    assert all(item.persistent_full_text_ingestion_allowed is False for item in registry.sources)
    assert all(item.urls for item in registry.sources)
    # Parsed metadata is immutable and retains no source-document body field.
    with pytest.raises(TypeError):
        registry.sources[0].metadata["title"] = "mutated"
    assert all(
        not ({"body", "content", "full_text", "raw_text"} & set(item.metadata))
        for item in registry.sources
    )


def test_source_ids_are_unique_even_when_only_case_differs():
    payload = source_registry_payload()
    payload["sources"][1]["id"] = payload["sources"][0]["id"]

    with pytest.raises(SourceRegistryError, match="SOURCE_REGISTRY_DUPLICATE_SOURCE_ID"):
        validate_source_registry(payload)


@pytest.mark.parametrize(
    "url",
    [
        "http://docs.example.com/manual.pdf",
        "https://user:password@docs.example.com/manual.pdf",
        "https://localhost/manual.pdf",
        "https://service.internal/manual.pdf",
        "https://127.0.0.1/manual.pdf",
        "https://[::1]/manual.pdf",
        "https://docs.example.com:99999/manual.pdf",
        "https://docs.example.com/manual.pdf#private-fragment",
        "javascript:alert(1)",
    ],
)
def test_source_urls_reject_non_https_private_or_malformed_targets(url):
    payload = source_registry_payload()
    payload["sources"][0]["pdf_url"] = url

    with pytest.raises(SourceRegistryError):
        validate_source_registry(payload)


def test_source_registry_rejects_embedded_document_or_conversation_bodies():
    payload = source_registry_payload()
    payload["sources"][0]["extracted_text"] = "This must never be persisted."

    with pytest.raises(
        SourceRegistryError,
        match="SOURCE_REGISTRY_EMBEDDED_DOCUMENT_BODY_FORBIDDEN",
    ):
        validate_source_registry(payload)


def test_unknown_rights_and_true_boolean_without_approval_fail_closed():
    payload = source_registry_payload()
    payload["sources"][0]["rights_status"] = "unknown"
    payload["sources"][0]["persistent_full_text_ingestion_allowed"] = True

    with pytest.raises(
        SourceRegistryError,
        match="SOURCE_REGISTRY_RIGHTS_STATUS_NOT_APPROVED",
    ):
        validate_source_registry(payload)


def approved_source_payload():
    payload = source_registry_payload()
    source = payload["sources"][0]
    source["rights_status"] = "approved_for_persistent_ingestion"
    source["persistent_full_text_ingestion_allowed"] = True
    source["rights_review"] = {
        "decision": "approved",
        "approval_id": "rights-review-2026-001",
        "approved_by": "rights-officer",
        "approved_at": "2026-11-07T10:00:00Z",
        "license_id": "license-123",
        "permitted_uses": ["metadata", "persistent_full_text_ingestion"],
        "evidence_ref": "internal://rights/evidence/123",
    }
    source["ingestion_authorization"] = {
        "decision": "authorized",
        "authorization_id": "ingestion-auth-2026-001",
        "authorized_by": "platform-admin",
        "authorized_at": "2026-11-07T10:05:00+00:00",
        "permitted_uses": ["persistent_full_text_ingestion"],
        "evidence_ref": "internal://ingestion/authorization/123",
    }
    return payload


def test_explicit_rights_review_and_separate_ingestion_authorization_are_both_required():
    payload = approved_source_payload()
    registry = validate_source_registry(payload)

    source = registry.get(payload["sources"][0]["id"])
    assert source is not None
    assert source.ingestion_authorized is True
    assert source.persistent_full_text_ingestion_allowed is True

    without_authorization = copy.deepcopy(payload)
    del without_authorization["sources"][0]["ingestion_authorization"]
    with pytest.raises(
        SourceRegistryError,
        match="SOURCE_REGISTRY_INGESTION_AUTHORIZATION_INCOMPLETE",
    ):
        validate_source_registry(without_authorization)

    without_rights_review = copy.deepcopy(payload)
    del without_rights_review["sources"][0]["rights_review"]
    with pytest.raises(
        SourceRegistryError,
        match="SOURCE_REGISTRY_RIGHTS_REVIEW_INCOMPLETE",
    ):
        validate_source_registry(without_rights_review)


def test_registry_requires_exact_v1_source_count_and_disabled_video_sources():
    payload = source_registry_payload()
    payload["sources"].pop()

    with pytest.raises(SourceRegistryError, match="SOURCE_REGISTRY_SOURCE_COUNT_INVALID"):
        validate_source_registry(payload)

    payload = source_registry_payload()
    payload["video_sources_enabled"] = True
    with pytest.raises(
        SourceRegistryError,
        match="SOURCE_REGISTRY_VIDEO_SOURCES_MUST_BE_DISABLED",
    ):
        validate_source_registry(payload)


def test_duplicate_topics_and_invalid_page_counts_are_rejected():
    payload = source_registry_payload()
    payload["sources"][0]["topics"].append(payload["sources"][0]["topics"][0])
    with pytest.raises(SourceRegistryError, match="SOURCE_REGISTRY_TOPICS_DUPLICATE"):
        validate_source_registry(payload)

    payload = source_registry_payload()
    payload["sources"][0]["pages"] = 0
    with pytest.raises(SourceRegistryError, match="SOURCE_REGISTRY_PAGE_COUNT_INVALID"):
        validate_source_registry(payload)


def test_load_source_registry_rejects_malformed_and_oversized_files(tmp_path):
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{not-json", encoding="utf-8")
    with pytest.raises(SourceRegistryError, match="SOURCE_REGISTRY_JSON_INVALID"):
        load_source_registry(malformed)

    oversized = tmp_path / "oversized.json"
    oversized.write_bytes(b" " * (1_048_576 + 1))
    with pytest.raises(SourceRegistryError, match="SOURCE_REGISTRY_FILE_SIZE_INVALID"):
        load_source_registry(oversized)

def test_load_source_registry_rejects_duplicate_json_object_keys(tmp_path):
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text(
        '{"registry_id":"cubi.project_management.sources",'
        '"registry_id":"attacker-controlled"}',
        encoding="utf-8",
    )
    with pytest.raises(
        SourceRegistryError,
        match="SOURCE_REGISTRY_JSON_DUPLICATE_KEY",
    ):
        load_source_registry(duplicate)
