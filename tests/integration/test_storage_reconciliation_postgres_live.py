from __future__ import annotations

import os
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN") or os.getenv("P6_TEST_POSTGRES_DSN")
if not DSN:
    pytest.skip(
        "CONSTRUCTION_PM_POSTGRES_DSN or P6_TEST_POSTGRES_DSN is not configured",
        allow_module_level=True,
    )

from construction_pm.document_content_repository import (
    DocumentContentVersion,
    PostgresDocumentContentRepository,
)
from construction_pm.document_retention import (
    PostgresDocumentRetentionStore,
)
from construction_pm.document_storage import (
    LocalDocumentStorage,
    validate_document_content,
)
from construction_pm.document_storage_reconciliation import (
    AWAITING_REPEATED_OBSERVATION,
    MATCH,
    ORPHAN_OBJECT,
    DocumentStorageReconciler,
    LocalDocumentObjectInventory,
    PostgresDocumentStorageReconciliationStore,
    ReconciliationPolicy,
)

NOW = datetime(2026, 11, 13, 12, 0, tzinfo=timezone.utc)
UPLOADED = datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc)
PDF_ONE = b"%PDF-1.7\nlive reconciliation one\n%%EOF\n"
PDF_TWO = b"%PDF-1.7\nlive reconciliation two\n%%EOF\n"
ZERO_GRACE = ReconciliationPolicy(grace_period=timedelta(0))


class World:
    def __init__(self, root: Path, suffix: str, connection) -> None:
        self.connection = connection
        self.content = PostgresDocumentContentRepository(connection)
        self.content.initialize()
        self.retention = PostgresDocumentRetentionStore(connection)
        self.retention.initialize()
        self.state = PostgresDocumentStorageReconciliationStore(connection)
        self.state.initialize()
        connection.commit()
        self.root = root / f"objects-{suffix}"
        self.storage = LocalDocumentStorage(self.root)
        self.tenant_id = f"recon-tenant-{suffix}"
        self.project_id = f"recon-project-{suffix}"

    def seed(self, document_id: str, data: bytes, *, version: int = 1) -> str:
        blob = validate_document_content(
            data, declared_content_type="application/pdf", filename="doc.pdf"
        )
        ref = self.storage.put(
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            content_hash=blob.content_hash,
            extension=blob.extension,
            data=data,
        )
        self.content.append(
            DocumentContentVersion(
                tenant_id=self.tenant_id,
                project_id=self.project_id,
                document_id=document_id,
                version=version,
                document_revision=version,
                storage_ref=ref,
                content_hash=blob.content_hash,
                content_type=blob.content_type,
                byte_size=blob.byte_size,
                original_filename=blob.original_filename,
                idempotency_key=f"upload-{document_id}-{version}",
                actor_id="uploader-1",
                uploaded_at=UPLOADED,
            )
        )
        self.connection.commit()
        return ref

    def orphan(self, data: bytes) -> str:
        blob = validate_document_content(
            data, declared_content_type="application/pdf", filename="doc.pdf"
        )
        ref = self.storage.put(
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            content_hash=blob.content_hash,
            extension=blob.extension,
            data=data,
        )
        self.connection.commit()
        return ref

    def reconcile(
        self,
        *,
        now: datetime,
        dry_run: bool,
        state=None,
        inventory=None,
        connection=None,
    ):
        local_connection = connection or self.connection
        reconciler = DocumentStorageReconciler(
            content_repository=PostgresDocumentContentRepository(local_connection),
            retention_store=PostgresDocumentRetentionStore(local_connection),
            inventory=inventory or LocalDocumentObjectInventory(self.root),
            state_store=state
            or PostgresDocumentStorageReconciliationStore(local_connection),
            policy=ZERO_GRACE,
        )
        return reconciler.reconcile(
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            now=now,
            dry_run=dry_run,
        )

    def path(self, ref: str) -> Path:
        return self.root.joinpath(*ref.split("local:v1/", 1)[1].split("/"))


def test_postgres_reconciliation_is_durable_across_connections(tmp_path: Path) -> None:
    suffix = uuid.uuid4().hex[:10]
    with psycopg.connect(DSN) as connection:
        world = World(tmp_path, suffix, connection)
        matched = world.seed("doc-1", PDF_ONE)
        orphan = world.orphan(PDF_TWO)

        dry = world.reconcile(now=NOW, dry_run=True)
        assert dry.dry_run is True
        assert dry.count(MATCH) == 1
        assert dry.count(ORPHAN_OBJECT) == 1
        assert world.state.get(world.tenant_id, world.project_id, orphan) is None
        assert world.state.list_cleanup(world.tenant_id, world.project_id) == ()

        first = world.reconcile(now=NOW, dry_run=False)
        assert first.count(ORPHAN_OBJECT) == 1
        assert first.deleted == 0
        assert first.entries[0].eligibility == AWAITING_REPEATED_OBSERVATION

        second = world.reconcile(now=NOW + timedelta(seconds=1), dry_run=False)
        assert second.deleted == 1

        versions = world.content.list_all(tenant_id=world.tenant_id)
        assert [version.document_id for version in versions] == ["doc-1"]
        assert world.content.list_all(
            tenant_id=world.tenant_id, project_id=world.project_id
        ) == versions
        assert world.retention.list_all_dispositions(
            tenant_id=world.tenant_id
        ) == ()
        assert world.retention.list_all_policies(tenant_id=world.tenant_id) == ()
        assert world.path(matched).exists()
        assert not world.path(orphan).exists()

    # A fresh connection must observe the same durable outcome.
    with psycopg.connect(DSN) as other:
        store = PostgresDocumentStorageReconciliationStore(other)
        records = store.list_cleanup(world.tenant_id, world.project_id)
        assert [record.status for record in records] == ["deleted"]
        assert records[0].actor_id == "storage-reconciler"
        assert records[0].content_hash is not None
        state = store.get(world.tenant_id, world.project_id, orphan)
        assert state is not None
        assert state.status == "deleted"
        assert state.observations == 2
        assert state.attempts == 1


def test_concurrent_reconcilers_delete_the_orphan_once(tmp_path: Path) -> None:
    suffix = uuid.uuid4().hex[:10]
    with psycopg.connect(DSN) as setup:
        world = World(tmp_path, suffix, setup)
        world.seed("doc-1", PDF_ONE)
        orphan = world.orphan(PDF_TWO)
        setup_report = world.reconcile(now=NOW, dry_run=False)
        assert setup_report.deleted == 0
        state = world.state.get(world.tenant_id, world.project_id, orphan)
        assert state is not None and state.observations == 1

    barrier = threading.Barrier(2)
    reports: list[object] = []
    errors: list[BaseException] = []

    class SlowInventory(LocalDocumentObjectInventory):
        def delete(self, item, *, tenant_id, project_id):
            time.sleep(0.3)
            return super().delete(item, tenant_id=tenant_id, project_id=project_id)

    def worker() -> None:
        try:
            with psycopg.connect(DSN) as connection:
                barrier.wait(timeout=10)
                report = world.reconcile(
                    now=NOW + timedelta(seconds=1),
                    dry_run=False,
                    inventory=SlowInventory(world.root),
                    connection=connection,
                )
                reports.append(report)
        except BaseException as exc:  # noqa: BLE001 - surfaced through the assertion
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert not errors
    assert len(reports) == 2
    assert sum(report.deleted for report in reports) == 1
    assert not world.path(orphan).exists()

    with psycopg.connect(DSN) as other:
        store = PostgresDocumentStorageReconciliationStore(other)
        records = store.list_cleanup(world.tenant_id, world.project_id)
        assert [record.status for record in records] == ["deleted"]
        state = store.get(world.tenant_id, world.project_id, orphan)
        assert state is not None and state.status == "deleted"


def test_postgres_lease_is_exclusive_and_reclaimable(tmp_path: Path) -> None:
    suffix = uuid.uuid4().hex[:10]
    with psycopg.connect(DSN) as connection:
        world = World(tmp_path, suffix, connection)
        orphan = world.orphan(PDF_TWO)
        store = PostgresDocumentStorageReconciliationStore(connection)
        store.record_observation(
            tenant_id=world.tenant_id,
            project_id=world.project_id,
            object_ref=orphan,
            classification=ORPHAN_OBJECT,
            now=NOW,
        )
        assert (
            store.claim(
                tenant_id=world.tenant_id,
                project_id=world.project_id,
                object_ref=orphan,
                now=NOW,
                grace_cutoff=NOW,
                min_observations=2,
                lease_seconds=60,
            )
            is None
        )
        store.record_observation(
            tenant_id=world.tenant_id,
            project_id=world.project_id,
            object_ref=orphan,
            classification=ORPHAN_OBJECT,
            now=NOW,
        )
        first = store.claim(
            tenant_id=world.tenant_id,
            project_id=world.project_id,
            object_ref=orphan,
            now=NOW,
            grace_cutoff=NOW,
            min_observations=2,
            lease_seconds=60,
        )
        assert first == 1
        store.commit_claim()

        with psycopg.connect(DSN) as competing:
            other = PostgresDocumentStorageReconciliationStore(competing)
            assert (
                other.claim(
                    tenant_id=world.tenant_id,
                    project_id=world.project_id,
                    object_ref=orphan,
                    now=NOW + timedelta(seconds=1),
                    grace_cutoff=NOW,
                    min_observations=2,
                    lease_seconds=60,
                )
                is None
            )
            # The crashed worker's lease expires and the occurrence is reclaimable.
            assert (
                other.claim(
                    tenant_id=world.tenant_id,
                    project_id=world.project_id,
                    object_ref=orphan,
                    now=NOW + timedelta(seconds=61),
                    grace_cutoff=NOW,
                    min_observations=2,
                    lease_seconds=60,
                )
                == 2
            )
            competing.rollback()
