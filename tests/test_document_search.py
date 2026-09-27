from __future__ import annotations

import pytest

from construction_pm.document_search import (
    DocumentSearchEntry,
    DocumentSearchRevisionConflict,
    InMemoryDocumentSearchAdapter,
)


def entry(revision=1, text="Structural drawing for level 2"):
    return DocumentSearchEntry(
        tenant_id="tenant-1",
        project_id="project-1",
        document_id="doc-1",
        revision=revision,
        content_hash="sha256:" + "a" * 64,
        text=text,
    )


def test_search_is_tenant_project_scoped_and_case_insensitive():
    adapter = InMemoryDocumentSearchAdapter()
    adapter.index(entry())
    adapter.index(
        DocumentSearchEntry(
            tenant_id="tenant-1",
            project_id="project-2",
            document_id="doc-2",
            revision=1,
            content_hash="sha256:" + "b" * 64,
            text="Structural drawing",
        )
    )
    assert [x.document_id for x in adapter.search("tenant-1", "project-1", "LEVEL 2")] == ["doc-1"]
    assert adapter.search("tenant-1", "project-2", "level 2") == ()


def test_stale_index_update_is_rejected_and_current_entry_is_preserved():
    adapter = InMemoryDocumentSearchAdapter()
    adapter.index(entry(revision=2, text="approved revision"))
    with pytest.raises(DocumentSearchRevisionConflict, match="DOCUMENT_SEARCH_STALE_REVISION"):
        adapter.index(entry(revision=1, text="stale text"))
    assert adapter.search("tenant-1", "project-1", "approved")[0].revision == 2


def test_remove_requires_current_revision():
    adapter = InMemoryDocumentSearchAdapter()
    adapter.index(entry(revision=2))
    with pytest.raises(DocumentSearchRevisionConflict, match="DOCUMENT_SEARCH_STALE_REVISION"):
        adapter.remove("tenant-1", "project-1", "doc-1", expected_revision=1)
    adapter.remove("tenant-1", "project-1", "doc-1", expected_revision=2)
    assert adapter.search("tenant-1", "project-1", "structural") == ()
