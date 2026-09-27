import os
import uuid

import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
if not DSN:
    pytest.skip("CONSTRUCTION_PM_POSTGRES_DSN is not configured", allow_module_level=True)

from construction_pm.document_search import (
    DocumentSearchEntry,
    DocumentSearchRevisionConflict,
    PostgresDocumentSearchAdapter,
)


def make_entry(suffix: str, revision: int = 1, text: str = "Structural drawing for level 2") -> DocumentSearchEntry:
    return DocumentSearchEntry(
        tenant_id="live-search-tenant",
        project_id=f"project-{suffix}",
        document_id="doc-1",
        revision=revision,
        content_hash="sha256:" + ("a" * 64),
        text=text,
    )


def test_document_search_postgres_live_scope_revision_and_removal() -> None:
    suffix = uuid.uuid4().hex
    entry = make_entry(suffix)
    with psycopg.connect(DSN) as connection:
        adapter = PostgresDocumentSearchAdapter(connection)
        adapter.initialize()
        connection.commit()

        adapter.index(entry)
        connection.commit()
        assert [item.document_id for item in adapter.search(entry.tenant_id, entry.project_id, "LEVEL 2")] == ["doc-1"]

        with pytest.raises(DocumentSearchRevisionConflict, match="DOCUMENT_SEARCH_STALE_REVISION"):
            adapter.index(make_entry(suffix, revision=0, text="stale"))
        connection.rollback()

        other_project = DocumentSearchEntry(
            tenant_id=entry.tenant_id,
            project_id=f"other-{suffix}",
            document_id="doc-2",
            revision=1,
            content_hash="sha256:" + ("b" * 64),
            text="Structural drawing",
        )
        adapter.index(other_project)
        connection.commit()

        assert adapter.search(entry.tenant_id, entry.project_id, "structural")
        assert adapter.search(entry.tenant_id, other_project.project_id, "level 2") == ()

        with pytest.raises(DocumentSearchRevisionConflict, match="DOCUMENT_SEARCH_STALE_REVISION"):
            adapter.remove(entry.tenant_id, entry.project_id, entry.document_id, expected_revision=0)
        connection.rollback()

        adapter.remove(entry.tenant_id, entry.project_id, entry.document_id, expected_revision=1)
        connection.commit()
        assert adapter.search(entry.tenant_id, entry.project_id, "structural") == ()
