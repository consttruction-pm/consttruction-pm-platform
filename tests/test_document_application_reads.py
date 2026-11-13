from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    Permission,
    RoleBasedAuthorizationPolicy,
    default_project_policy,
)
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.document_application import DocumentApplicationService
from construction_pm.document_content_repository import SQLiteDocumentContentRepository
from construction_pm.document_persistence import (
    DocumentAuthorizationError,
    DocumentRecord,
    RolePermissionDocumentLifecycleAuthorizer,
    SQLiteDocumentStore,
)
from construction_pm.document_storage import LocalDocumentStorage, validate_document_content

NOW = datetime(2026, 11, 12, 10, 0, tzinfo=timezone.utc)


def context(role: str = "planner", *, project: str = "P-1", tenant: str = "T-1") -> AuthorizationContext:
    return AuthorizationContext(tenant, project, "u-1", frozenset({role}))


def document(**changes: object) -> DocumentRecord:
    values = {
        "document_id": "DOC-1",
        "tenant_id": "T-1",
        "project_id": "P-1",
        "resource_type": "rfi",
        "title": "RFI 001",
        "status": "draft",
        "storage_ref": "object://rfi/1",
        "content_hash": "sha256:" + "a" * 64,
        "linked_entity_refs": ("A-1",),
    }
    values.update(changes)
    return DocumentRecord(**values)


@pytest.fixture()
def service() -> DocumentApplicationService:
    connection = sqlite3.connect(":memory:")
    store = SQLiteDocumentStore(connection)
    store.initialize()
    return DocumentApplicationService(
        store,
        default_project_policy(),
        RolePermissionDocumentLifecycleAuthorizer(),
        SQLiteTransactionManager(connection),
    )


def test_list_and_history_are_project_scoped_and_readable_by_viewers(service) -> None:
    service.create(
        document(),
        context=context(),
        idempotency_key="k-1",
        actor_id="u-1",
        occurred_at=NOW,
    )
    service.update(
        document(title="RFI 001 issued"),
        expected_revision=1,
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )

    viewer = AuthorizationContext("T-1", "P-1", "v-1", frozenset({"viewer"}))
    listed = service.list(tenant_id="T-1", project_id="P-1", context=viewer)
    assert [item.document.document_id for item in listed] == ["DOC-1"]
    assert listed[0].revision == 2

    filtered = service.list(
        tenant_id="T-1", project_id="P-1", context=viewer, resource_type="drawing"
    )
    assert filtered == ()

    history = service.history(
        tenant_id="T-1", project_id="P-1", document_id="DOC-1", context=viewer
    )
    assert [event.event_type for event in history] == ["created", "updated"]
    assert [event.revision for event in history] == [1, 2]

    with pytest.raises(DocumentAuthorizationError, match="DOCUMENT_CROSS_SCOPE"):
        service.list(tenant_id="T-1", project_id="P-2", context=viewer)


def test_no_role_policy_cannot_read_documents(service) -> None:
    service.create(
        document(),
        context=context(),
        idempotency_key="k-1",
        actor_id="u-1",
        occurred_at=NOW,
    )
    outsider = AuthorizationContext("T-1", "P-1", "x-1", frozenset({"contractor"}))
    with pytest.raises(DocumentAuthorizationError, match="DOCUMENT_PERMISSION_DENIED"):
        service.list(tenant_id="T-1", project_id="P-1", context=outsider)
    with pytest.raises(DocumentAuthorizationError, match="DOCUMENT_PERMISSION_DENIED"):
        service.history(tenant_id="T-1", project_id="P-1", document_id="DOC-1", context=outsider)


def test_approval_requires_project_admin_role_not_a_user_id(service) -> None:
    service.create(
        document(),
        context=context(),
        idempotency_key="k-1",
        actor_id="u-1",
        occurred_at=NOW,
    )
    submitted = service.transition_status(
        document(status="submitted"),
        expected_revision=1,
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    assert submitted.revision == 2

    with pytest.raises(DocumentAuthorizationError, match="DOCUMENT_TRANSITION_FORBIDDEN"):
        service.transition_status(
            document(status="approved"),
            expected_revision=2,
            context=context(),
            actor_id="u-1",
            occurred_at=NOW,
        )

    approved = service.transition_status(
        document(status="approved"),
        expected_revision=2,
        context=context("project_admin"),
        actor_id="u-1",
        occurred_at=NOW,
    )
    assert approved.document.status == "approved"
    assert approved.revision == 3

    # Rejection is an approval decision as well.
    service.create(
        document(document_id="DOC-2"),
        context=context(),
        idempotency_key="k-2",
        actor_id="u-1",
        occurred_at=NOW,
    )
    service.transition_status(
        document(document_id="DOC-2", status="submitted"),
        expected_revision=1,
        context=context(),
        actor_id="u-1",
        occurred_at=NOW,
    )
    with pytest.raises(DocumentAuthorizationError, match="DOCUMENT_TRANSITION_FORBIDDEN"):
        service.transition_status(
            document(document_id="DOC-2", status="rejected"),
            expected_revision=2,
            context=context(),
            actor_id="u-1",
            occurred_at=NOW,
        )


def test_metadata_update_cannot_bypass_the_status_transition_endpoint(service) -> None:
    service.create(
        document(),
        context=context(),
        idempotency_key="k-1",
        actor_id="u-1",
        occurred_at=NOW,
    )
    with pytest.raises(ValueError, match="DOCUMENT_STATUS_REQUIRES_TRANSITION"):
        service.update(
            document(status="approved"),
            expected_revision=1,
            context=context(),
            actor_id="u-1",
            occurred_at=NOW,
        )
    current = service.read(
        tenant_id="T-1", project_id="P-1", document_id="DOC-1", context=context()
    )
    assert current.document.status == "draft"
    assert current.revision == 1


def test_approval_role_gate_can_be_configured_without_changing_the_store() -> None:
    connection = sqlite3.connect(":memory:")
    store = SQLiteDocumentStore(connection)
    store.initialize()
    policy = RoleBasedAuthorizationPolicy(
        {
            "writer": frozenset({Permission.PROJECT_READ, Permission.PROJECT_WRITE}),
            "reviewer": frozenset(
                {Permission.PROJECT_READ, Permission.PROJECT_WRITE}
            ),
        }
    )
    service = DocumentApplicationService(
        store,
        policy,
        RolePermissionDocumentLifecycleAuthorizer(frozenset({"reviewer"})),
        SQLiteTransactionManager(connection),
    )
    ctx = AuthorizationContext("T-1", "P-1", "u-1", frozenset({"writer"}))
    service.create(document(), context=ctx, idempotency_key="k-1", actor_id="u-1", occurred_at=NOW)
    service.transition_status(
        document(status="submitted"),
        expected_revision=1,
        context=ctx,
        actor_id="u-1",
        occurred_at=NOW,
    )
    reviewer = AuthorizationContext("T-1", "P-1", "u-1", frozenset({"reviewer"}))
    approved = service.transition_status(
        document(status="approved"),
        expected_revision=2,
        context=reviewer,
        actor_id="u-1",
        occurred_at=NOW,
    )
    assert approved.document.status == "approved"


def test_update_cannot_retarget_the_content_reference(service) -> None:
    service.create(
        document(),
        context=context(),
        idempotency_key="k-ref",
        actor_id="u-1",
        occurred_at=NOW,
    )
    with pytest.raises(ValueError, match="DOCUMENT_CONTENT_REFERENCE_IMMUTABLE"):
        service.update(
            document(
                title="Renamed",
                storage_ref="local:v1/0123456789abcdef/0123456789abcdef/1f/" + "f" * 64 + ".bin",
                content_hash="sha256:" + "f" * 64,
            ),
            expected_revision=1,
            context=context(),
            actor_id="u-1",
            occurred_at=NOW,
        )

    stored = service.read(
        tenant_id="T-1", project_id="P-1", document_id="DOC-1", context=context()
    )
    assert stored.document.storage_ref == "object://rfi/1"
    assert stored.document.title == "RFI 001"
    assert stored.revision == 1


def _service_with_storage(tmp_path):
    connection = sqlite3.connect(":memory:")
    store = SQLiteDocumentStore(connection)
    store.initialize()
    content = SQLiteDocumentContentRepository(connection)
    content.initialize()
    storage = LocalDocumentStorage(tmp_path / "store")
    service = DocumentApplicationService(
        store,
        default_project_policy(),
        RolePermissionDocumentLifecycleAuthorizer(),
        SQLiteTransactionManager(connection),
        storage=storage,
        content_repository=content,
    )
    return service, storage


def test_create_rejects_a_legacy_reference_that_does_not_resolve(tmp_path) -> None:
    service, _ = _service_with_storage(tmp_path)

    with pytest.raises(ValueError, match="DOCUMENT_CONTENT_REFERENCE_UNVERIFIED"):
        service.create(
            document(
                storage_ref="local:v1/aaaaaaaaaaaaaaaa/bbbbbbbbbbbbbbbb/cc/"
                + "d" * 64
                + ".pdf",
                content_hash="sha256:" + "d" * 64,
            ),
            context=context(),
            idempotency_key="k-unverified",
            actor_id="u-1",
            occurred_at=NOW,
        )

    assert service.list(tenant_id="T-1", project_id="P-1", context=context()) == ()


def test_create_accepts_a_legacy_reference_that_resolves_in_scope(tmp_path) -> None:
    service, storage = _service_with_storage(tmp_path)
    data = b"legacy bytes\n"
    blob = validate_document_content(
        data, declared_content_type="text/plain", filename="legacy.txt"
    )
    ref = storage.put(
        tenant_id="T-1",
        project_id="P-1",
        content_hash=blob.content_hash,
        extension=blob.extension,
        data=data,
    )

    created = service.create(
        document(storage_ref=ref, content_hash=blob.content_hash),
        context=context(),
        idempotency_key="k-legacy",
        actor_id="u-1",
        occurred_at=NOW,
    )
    assert created.document.storage_ref == ref
    download = service.download_content(
        tenant_id="T-1", project_id="P-1", document_id="DOC-1", context=context()
    )
    assert download.version is None
    assert download.data == data
