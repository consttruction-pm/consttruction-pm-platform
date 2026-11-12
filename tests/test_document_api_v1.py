from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pytest

from construction_pm.application.authorization import AuthorizationContext, default_project_policy
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.document_api import DOCUMENT_API_VERSION, DocumentAPI
from construction_pm.document_application import DocumentApplicationService
from construction_pm.document_persistence import (
    DocumentRecord,
    RolePermissionDocumentLifecycleAuthorizer,
    SQLiteDocumentStore,
)

NOW = datetime(2026, 11, 12, 11, 45, tzinfo=timezone.utc)


def document(**changes: object) -> DocumentRecord:
    values = {
        "document_id": "DOC-1",
        "tenant_id": "T-1",
        "project_id": "P-1",
        "resource_type": "submittal",
        "title": "Rebar shop drawing",
        "status": "draft",
        "storage_ref": "object://submittals/1",
        "content_hash": "sha256:" + "b" * 64,
        "linked_entity_refs": ("A-1", "WBS-2"),
    }
    values.update(changes)
    return DocumentRecord(**values)


@pytest.fixture()
def api() -> DocumentAPI:
    connection = sqlite3.connect(":memory:")
    store = SQLiteDocumentStore(connection)
    store.initialize()
    service = DocumentApplicationService(
        store,
        default_project_policy(),
        RolePermissionDocumentLifecycleAuthorizer(),
        SQLiteTransactionManager(connection),
    )
    return DocumentAPI(service)


def context(role: str = "planner", *, project: str = "P-1") -> AuthorizationContext:
    return AuthorizationContext("T-1", project, "u-1", frozenset({role}))


def test_create_list_and_history_share_one_contract_version(api: DocumentAPI) -> None:
    created = api.create(
        document(),
        context=context(),
        idempotency_key="k-1",
        actor_id="u-1",
        occurred_at=NOW,
    )
    assert created["contract_version"] == DOCUMENT_API_VERSION == "1.0"
    assert created["revision"] == 1
    assert created["linked_entity_refs"] == ["A-1", "WBS-2"]

    listed = api.list(tenant_id="T-1", project_id="P-1", context=context())
    assert listed["contract_version"] == DOCUMENT_API_VERSION
    assert [item["document_id"] for item in listed["documents"]] == ["DOC-1"]

    filtered = api.list(
        tenant_id="T-1", project_id="P-1", context=context(), resource_type="rfi"
    )
    assert filtered == {"contract_version": DOCUMENT_API_VERSION, "documents": []}

    history = api.history(
        tenant_id="T-1", project_id="P-1", document_id="DOC-1", context=context()
    )
    assert history["contract_version"] == DOCUMENT_API_VERSION
    assert [event["event_type"] for event in history["events"]] == ["created"]
    assert history["events"][0]["occurred_at"] == NOW.isoformat()
    assert history["events"][0]["actor_id"] == "u-1"


def test_api_maps_not_found_and_invalid_filters_to_versioned_errors(api: DocumentAPI) -> None:
    missing = api.read(
        tenant_id="T-1", project_id="P-1", document_id="missing", context=context()
    )
    assert missing["contract_version"] == DOCUMENT_API_VERSION
    assert missing["code"] == "DOCUMENT_NOT_FOUND"
    assert missing["message"] == "DOCUMENT_NOT_FOUND"
    assert missing["retryable"] is False

    invalid = api.list(
        tenant_id="T-1",
        project_id="P-1",
        context=context(),
        status="unknown",
    )
    assert invalid["code"] == "INVALID_DOCUMENT_STATUS_FILTER"
    assert invalid["category"] == "validation"

    history = api.history(
        tenant_id="T-1", project_id="P-1", document_id="missing", context=context()
    )
    assert history["code"] == "DOCUMENT_NOT_FOUND"


def test_api_maps_approval_role_and_revision_conflicts(api: DocumentAPI) -> None:
    api.create(
        document(),
        context=context(),
        idempotency_key="k-1",
        actor_id="u-1",
        occurred_at=NOW,
    )
    api.transition_status(
        document(status="submitted"),
        expected_revision=1,
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )

    forbidden = api.transition_status(
        document(status="approved"),
        expected_revision=2,
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    assert forbidden["category"] == "authorization"
    assert forbidden["code"] == "DOCUMENT_TRANSITION_FORBIDDEN"

    conflict = api.transition_status(
        document(status="approved"),
        expected_revision=1,
        context=context("project_admin"),
        actor_id="u-1",
        occurred_at=NOW,
    )
    assert conflict["category"] == "conflict"
    assert conflict["code"] == "DOCUMENT_REVISION_CONFLICT"
    assert conflict["retryable"] is True
