from datetime import datetime, timezone

from construction_pm.api_errors import APIErrorCategory
from construction_pm.application.authorization import AuthorizationContext, Permission, RoleBasedAuthorizationPolicy
from construction_pm.document_api import DocumentAPI
from construction_pm.document_application import DocumentApplicationService
from construction_pm.document_persistence import DocumentRecord, PostgresDocumentStore, RoleDocumentLifecycleAuthorizer


class Cursor:
    def __init__(self, row=None, rows=()):
        self.row = row
        self.rows = rows

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.rows


class Connection:
    def __init__(self):
        self.documents = {}
        self.idempotency = {}

    def execute(self, sql, params=()):
        if sql.startswith("SELECT document_id, fingerprint, revision"):
            return Cursor(self.idempotency.get(params))
        if sql.startswith("SELECT document_json, revision"):
            return Cursor(self.documents.get(params))
        if sql.startswith("INSERT INTO project_documents"):
            key = (params[0], params[1], params[3])
            self.idempotency[key] = (params[2], params[4], params[5])
            self.documents[(params[0], params[1], params[2])] = (params[6], params[5])
            return Cursor()
        if sql.startswith("INSERT INTO project_document_audit"):
            return Cursor()
        if sql.startswith("SELECT revision FROM project_documents"):
            return Cursor((1,))
        if sql.startswith("UPDATE project_documents"):
            key = (params[2], params[3], params[4])
            self.documents[key] = (params[1], params[0])
            return Cursor()
        if sql.startswith("SELECT error"):
            return Cursor()
        return Cursor(rows=())


    def transaction(self):
        class Tx:
            def __enter__(self): return self
            def __exit__(self, exc_type, exc, tb): return False
        return Tx()


def context(role="planner", project="P-1"):
    return AuthorizationContext("T-1", project, "u-1", frozenset({role}))


def policy():
    return RoleBasedAuthorizationPolicy({
        "planner": frozenset({Permission.PROJECT_READ, Permission.PROJECT_WRITE}),
        "viewer": frozenset({Permission.PROJECT_READ}),
    })


def document(**overrides):
    values = dict(
        document_id="DOC-1",
        tenant_id="T-1",
        project_id="P-1",
        resource_type="rfi",
        title="RFI 001",
        status="draft",
        storage_ref="storage://rfi/1",
        content_hash="sha256:" + "a" * 64,
        linked_entity_refs=("A-1",),
    )
    values.update(overrides)
    return DocumentRecord(**values)


def service():
    connection = Connection()
    store = PostgresDocumentStore(connection)
    store.initialize()
    return connection, DocumentApplicationService(
        store,
        policy(),
        RoleDocumentLifecycleAuthorizer({"u-approver"}),
    )


def test_rfi_create_and_read_are_context_scoped_and_versioned():
    connection, svc = service()
    created = svc.create(document(), context=context(), idempotency_key="k-1", actor_id="u-1", occurred_at=datetime(2026,9,27,tzinfo=timezone.utc))
    assert created.revision == 1
    read = svc.read(tenant_id="T-1", project_id="P-1", document_id="DOC-1", context=context())
    assert read.document.resource_type == "rfi"
    assert svc.error_dto(Exception("x")).category is APIErrorCategory.VALIDATION
    connection.close()


def test_cross_project_and_viewer_write_are_rejected():
    _, svc = service()
    try:
        svc.create(document(), context=context(project="P-2"), idempotency_key="k-2", actor_id="u-1", occurred_at=datetime.now(timezone.utc))
    except Exception as exc:
        assert str(exc) == "DOCUMENT_CROSS_SCOPE"
    try:
        svc.create(document(), context=context("viewer"), idempotency_key="k-3", actor_id="u-1", occurred_at=datetime.now(timezone.utc))
    except Exception as exc:
        assert str(exc) == "DOCUMENT_PERMISSION_DENIED"


def test_submittal_transition_requires_approver_and_revision():
    _, svc = service()
    created = svc.create(document(resource_type="submittal"), context=context(), idempotency_key="k-4", actor_id="u-1", occurred_at=datetime.now(timezone.utc))
    submitted = document(resource_type="submittal", status="submitted")
    try:
        svc.transition_status(submitted, expected_revision=1, context=context(), actor_id="u-1", occurred_at=datetime.now(timezone.utc))
    except Exception as exc:
        assert str(exc) == "DOCUMENT_TRANSITION_FORBIDDEN"
