from dataclasses import replace
import sqlite3

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.wbs_master_repository import (
    SQLiteWBSMasterRepository,
    WBSMaster,
    WBSParentKind,
    WBSPersistenceError,
)


def scope(revision: int = 7, *, tenant: str = "T-1", project: str = "P-1") -> BackendScope:
    return BackendScope(tenant, project, revision)


def root(
    wbs_id: str = "W-ROOT",
    *,
    revision: int = 7,
    code: str = "1",
    name: str = "Project Root",
    sequence_number: int = 0,
) -> WBSMaster:
    return WBSMaster(
        scope(revision),
        wbs_id,
        WBSParentKind.PROJECT,
        None,
        code,
        name,
        sequence_number,
    )


def child(
    wbs_id: str,
    parent_id: str,
    *,
    revision: int = 7,
    code: str = "1",
    name: str = "Child",
    sequence_number: int = 1,
) -> WBSMaster:
    return WBSMaster(
        scope(revision),
        wbs_id,
        WBSParentKind.WBS,
        parent_id,
        code,
        name,
        sequence_number,
    )


def test_wbs_master_round_trip_explicit_project_root_and_nested_nodes():
    repo = SQLiteWBSMasterRepository(sqlite3.connect(":memory:"))
    stored_root = repo.save(root())
    stored_child = repo.save(child("W-CHILD", stored_root.wbs_id, code="2"))

    assert stored_root.record_revision == 1
    assert stored_root.parent_kind is WBSParentKind.PROJECT
    assert stored_root.parent_wbs_id is None
    assert stored_child.record_revision == 1
    assert stored_child.parent_kind is WBSParentKind.WBS
    assert stored_child.parent_wbs_id == stored_root.wbs_id
    assert repo.get(scope(), stored_root.wbs_id) == stored_root
    assert repo.get(scope(), stored_child.wbs_id) == stored_child
    assert repo.list(scope()) == (stored_root, stored_child)


def test_wbs_master_update_requires_expected_revision_and_advances_record_revision():
    repo = SQLiteWBSMasterRepository(sqlite3.connect(":memory:"))
    repo.save(root())

    updated = repo.save(replace(root(name="Revised Project Root"), name="Revised Project Root"), expected_revision=1)

    assert updated.record_revision == 2
    assert updated.name == "Revised Project Root"
    assert repo.get(scope(), "W-ROOT") == updated
    with pytest.raises(WBSPersistenceError, match="REVISION_CONFLICT"):
        repo.save(root(name="Stale update"), expected_revision=1)


def test_wbs_master_rejects_duplicate_project_root():
    repo = SQLiteWBSMasterRepository(sqlite3.connect(":memory:"))
    repo.save(root())

    with pytest.raises(WBSPersistenceError, match="WBS_PROJECT_ROOT_ALREADY_EXISTS"):
        repo.save(root(wbs_id="W-ROOT-2", code="2"))


def test_wbs_master_rejects_child_without_parent_and_cross_project_parent():
    repo = SQLiteWBSMasterRepository(sqlite3.connect(":memory:"))
    with pytest.raises(WBSPersistenceError, match="WBS_PARENT_NOT_FOUND_OR_SCOPE_MISMATCH"):
        repo.save(child("W-ORPHAN", "MISSING"))

    repo.save(root())
    repo.save(root(wbs_id="OTHER-ROOT", code="1", name="Other project") if False else root(
        wbs_id="OTHER-ROOT", code="1", name="Other project"
    )) if False else None
    other_repo = SQLiteWBSMasterRepository(sqlite3.connect(":memory:"))
    other_repo.save(WBSMaster(
        scope(tenant="T-OTHER", project="P-OTHER"),
        "W-ROOT",
        WBSParentKind.PROJECT,
        None,
        "1",
        "Other root",
        0,
    ))
    with pytest.raises(WBSPersistenceError, match="WBS_PARENT_NOT_FOUND_OR_SCOPE_MISMATCH"):
        repo.save(WBSMaster(
            scope(),
            "W-CROSS-SCOPE",
            WBSParentKind.WBS,
            "W-ROOT",
            "2",
            "Must not bind across projects",
            2,
        ))


def test_wbs_master_enforces_unique_sibling_codes_but_keeps_codes_local():
    repo = SQLiteWBSMasterRepository(sqlite3.connect(":memory:"))
    repo.save(root())
    repo.save(child("W-A", "W-ROOT", code="A"))
    repo.save(child("W-B", "W-ROOT", code="B", sequence_number=2))
    repo.save(child("W-A-CHILD", "W-A", code="1"))

    with pytest.raises(WBSPersistenceError, match="WBS_SIBLING_CODE_CONFLICT"):
        repo.save(child("W-DUPLICATE", "W-ROOT", code="A", sequence_number=3))

    # Codes are local to their parent; this repository does not persist a
    # concatenated display path as the node's identity or local Code field.
    repo.save(child("W-B-CHILD", "W-B", code="1"))
    assert repo.get(scope(), "W-A-CHILD").code == "1"
    assert repo.get(scope(), "W-B-CHILD").code == "1"


def test_wbs_master_rejects_parent_cycle_on_update():
    repo = SQLiteWBSMasterRepository(sqlite3.connect(":memory:"))
    repo.save(root())
    repo.save(child("W-CHILD", "W-ROOT", code="2"))
    repo.save(child("W-GRANDCHILD", "W-CHILD", code="3"))

    cyclic_root = replace(
        root(),
        parent_kind=WBSParentKind.WBS,
        parent_wbs_id="W-CHILD",
    )
    with pytest.raises(WBSPersistenceError, match="WBS_HIERARCHY_CYCLE"):
        repo.save(cyclic_root, expected_revision=1)

    assert repo.get(scope(), "W-ROOT").parent_kind is WBSParentKind.PROJECT


@pytest.mark.parametrize(
    ("source", "error_code"),
    [
        (replace(root(), wbs_id=" "), "INVALID_WBS_ID"),
        (replace(root(), code=" "), "INVALID_WBS_CODE"),
        (replace(root(), name=" "), "INVALID_WBS_NAME"),
        (replace(root(), sequence_number=True), "INVALID_WBS_SEQUENCE_NUMBER"),
        (replace(root(), sequence_number=-1), "INVALID_WBS_SEQUENCE_NUMBER"),
        (replace(root(), record_revision=True), "INVALID_WBS_RECORD_REVISION"),
        (replace(root(), parent_kind=WBSParentKind.WBS, parent_wbs_id=None), "WBS_PARENT_REQUIRED"),
        (replace(root(), parent_wbs_id="W-CHILD"), "PROJECT_PARENT_CANNOT_REFERENCE_WBS"),
    ],
)
def test_wbs_master_rejects_invalid_contract_values(source, error_code):
    with pytest.raises(WBSPersistenceError, match=error_code):
        source.validate()


def test_wbs_master_rejects_cross_revision_reads_and_partial_tree_reads():
    connection = sqlite3.connect(":memory:")
    repo = SQLiteWBSMasterRepository(connection)
    repo.save(root())
    with pytest.raises(WBSPersistenceError, match="REVISION_CONFLICT"):
        repo.get(scope(8), "W-ROOT")

    # A mixed-revision tree must fail closed rather than silently omitting a
    # persisted node from the authoritative project hierarchy.
    connection.execute(
        "UPDATE wbs_master SET project_revision=6 WHERE tenant_id=? AND project_id=?",
        ("T-1", "P-1"),
    )
    connection.commit()
    with pytest.raises(WBSPersistenceError, match="REVISION_CONFLICT"):
        repo.list(scope())


def test_wbs_master_preserves_application_owned_sqlite_transaction():
    connection = sqlite3.connect(":memory:")
    repo = SQLiteWBSMasterRepository(connection)
    connection.execute("BEGIN")
    repo.save(root())

    assert connection.in_transaction
    connection.rollback()
    assert repo.get(scope(), "W-ROOT") is None


def test_wbs_master_orders_siblings_deterministically():
    repo = SQLiteWBSMasterRepository(sqlite3.connect(":memory:"))
    repo.save(root())
    repo.save(child("W-LATE", "W-ROOT", code="B", sequence_number=20))
    repo.save(child("W-EARLY", "W-ROOT", code="A", sequence_number=10))

    assert [item.wbs_id for item in repo.list(scope())] == [
        "W-ROOT",
        "W-EARLY",
        "W-LATE",
    ]
