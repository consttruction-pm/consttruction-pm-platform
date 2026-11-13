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

    updated = repo.save(replace(root(), name="Revised Project Root"), expected_revision=1)

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
    # A node with the same ID in another tenant/project does not satisfy this
    # project's parent reference.
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
    with pytest.raises(WBSPersistenceError, match="WBS_PARENT_NOT_FOUND_OR_SCOPE_MISMATCH"):
        repo.save(child("W-ORPHAN", "MISSING"))


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


def test_wbs_master_delete_requires_current_revision_and_removes_leaf():
    repo = SQLiteWBSMasterRepository(sqlite3.connect(":memory:"))
    repo.save(root())
    stored = repo.save(child("W-LEAF", "W-ROOT", code="2"))

    with pytest.raises(WBSPersistenceError, match="REVISION_CONFLICT"):
        repo.delete(scope(), "W-LEAF", expected_revision=stored.record_revision + 1)

    repo.delete(scope(), "W-LEAF", expected_revision=stored.record_revision)
    assert repo.get(scope(), "W-LEAF") is None
    assert [item.wbs_id for item in repo.list(scope())] == ["W-ROOT"]


def test_wbs_master_delete_rejects_nodes_with_children():
    repo = SQLiteWBSMasterRepository(sqlite3.connect(":memory:"))
    repo.save(root())
    parent = repo.save(child("W-PARENT", "W-ROOT", code="2"))
    repo.save(child("W-CHILD", "W-PARENT", code="3"))

    with pytest.raises(WBSPersistenceError, match="WBS_IN_USE"):
        repo.delete(scope(), parent.wbs_id, expected_revision=parent.record_revision)

    assert repo.get(scope(), parent.wbs_id) == parent


def test_wbs_status_and_percent_complete_technique_round_trip_and_update():
    from construction_pm.wbs_master_repository import (
        PercentCompleteTechnique,
        WBSStatus,
    )

    repo = SQLiteWBSMasterRepository(sqlite3.connect(":memory:"))
    stored = repo.save(replace(root(), status=WBSStatus.ACTIVE))
    assert stored.status is WBSStatus.ACTIVE
    assert stored.percent_complete_technique is PercentCompleteTechnique.ACTIVITIES
    assert repo.get(scope(), "W-ROOT").status is WBSStatus.ACTIVE

    updated = repo.save(
        replace(stored, status=WBSStatus.WHAT_IF, percent_complete_technique=PercentCompleteTechnique.MILESTONES),
        expected_revision=1,
    )
    assert updated.status is WBSStatus.WHAT_IF
    assert updated.percent_complete_technique is PercentCompleteTechnique.MILESTONES
    reread = repo.get(scope(), "W-ROOT")
    assert reread.status is WBSStatus.WHAT_IF
    assert reread.percent_complete_technique is PercentCompleteTechnique.MILESTONES


def test_weighted_milestones_replace_advances_revision_and_rolls_up_percent():
    from construction_pm.wbs_master_repository import (
        PercentCompleteTechnique,
        WBSMilestone,
        weighted_percent_complete,
    )

    repo = SQLiteWBSMasterRepository(sqlite3.connect(":memory:"))
    stored = repo.save(
        replace(root(), percent_complete_technique=PercentCompleteTechnique.MILESTONES)
    )
    milestones = (
        WBSMilestone(scope(), "W-ROOT", "M-1", "Mobilize", 9.0, True, 0),
        WBSMilestone(scope(), "W-ROOT", "M-2", "Foundations", 1.0, False, 1),
        WBSMilestone(scope(), "W-ROOT", "M-3", "Steel", 1.0, False, 2),
        WBSMilestone(scope(), "W-ROOT", "M-4", "Handover", 1.0, False, 3),
    )
    updated, written = repo.replace_milestones(
        scope(), "W-ROOT", milestones, expected_revision=stored.record_revision
    )
    assert updated.record_revision == stored.record_revision + 1
    assert [item.milestone_id for item in written] == ["M-1", "M-2", "M-3", "M-4"]
    assert weighted_percent_complete(written) == 75.0
    assert [item.milestone_id for item in repo.list_milestones(scope(), "W-ROOT")] == [
        "M-1", "M-2", "M-3", "M-4"
    ]

    completed = tuple(
        replace(item, completed=True) if item.milestone_id == "M-4" else item
        for item in written
    )
    _, written_two = repo.replace_milestones(
        scope(), "W-ROOT", completed, expected_revision=updated.record_revision
    )
    # M-1 (9.0) and M-4 (1.0) complete out of 12.0 total weight.
    assert weighted_percent_complete(written_two) == 83.33


def test_weighted_milestones_reject_stale_revision_duplicates_and_bad_weights():
    from construction_pm.wbs_master_repository import WBSMilestone

    repo = SQLiteWBSMasterRepository(sqlite3.connect(":memory:"))
    stored = repo.save(root())
    items = (WBSMilestone(scope(), "W-ROOT", "M-1", "One", 1.0, False, 0),)
    repo.replace_milestones(scope(), "W-ROOT", items, expected_revision=stored.record_revision)

    with pytest.raises(WBSPersistenceError, match="REVISION_CONFLICT"):
        repo.replace_milestones(scope(), "W-ROOT", items, expected_revision=stored.record_revision)
    with pytest.raises(WBSPersistenceError, match="DUPLICATE_WBS_MILESTONE_ID"):
        repo.replace_milestones(
            scope(),
            "W-ROOT",
            (items[0], WBSMilestone(scope(), "W-ROOT", "M-1", "Again", 2.0, False, 1)),
            expected_revision=2,
        )
    with pytest.raises(WBSPersistenceError, match="INVALID_WBS_MILESTONE_WEIGHT"):
        repo.replace_milestones(
            scope(),
            "W-ROOT",
            (WBSMilestone(scope(), "W-ROOT", "M-2", "Zero", 0.0, False, 0),),
            expected_revision=2,
        )
    with pytest.raises(WBSPersistenceError, match="WBS_MILESTONE_SCOPE_MISMATCH"):
        repo.replace_milestones(
            scope(),
            "W-ROOT",
            (WBSMilestone(scope(8), "W-ROOT", "M-2", "Other", 1.0, False, 0),),
            expected_revision=2,
        )


def test_deleting_a_leaf_removes_its_milestones():
    from construction_pm.wbs_master_repository import WBSMilestone

    repo = SQLiteWBSMasterRepository(sqlite3.connect(":memory:"))
    stored = repo.save(root())
    updated, _ = repo.replace_milestones(
        scope(),
        "W-ROOT",
        (WBSMilestone(scope(), "W-ROOT", "M-1", "One", 1.0, False, 0),),
        expected_revision=stored.record_revision,
    )
    repo.delete(scope(), "W-ROOT", expected_revision=updated.record_revision)
    assert repo.list_milestones(scope(), "W-ROOT") == ()


def test_existing_database_gains_status_columns_with_planned_defaults():
    connection = sqlite3.connect(":memory:")
    SQLiteWBSMasterRepository(connection)
    connection.execute("DROP TABLE wbs_master")
    connection.execute(
        """CREATE TABLE wbs_master (
            tenant_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            project_revision INTEGER NOT NULL,
            wbs_id TEXT NOT NULL,
            parent_kind TEXT NOT NULL,
            parent_wbs_id TEXT,
            code TEXT NOT NULL,
            name TEXT NOT NULL,
            sequence_number INTEGER NOT NULL,
            record_revision INTEGER NOT NULL,
            PRIMARY KEY (tenant_id, project_id, wbs_id)
        )"""
    )
    connection.execute(
        "INSERT INTO wbs_master VALUES ('T-1','P-1',7,'W-OLD','project',NULL,'1','Old',0,1)"
    )
    connection.commit()
    repo = SQLiteWBSMasterRepository(connection)
    loaded = repo.get(scope(), "W-OLD")
    assert loaded.status.value == "planned"
    assert loaded.percent_complete_technique.value == "activities"


def _copy_fixture() -> tuple[SQLiteWBSMasterRepository, WBSMaster]:
    from construction_pm.wbs_master_repository import (
        PercentCompleteTechnique,
        WBSMilestone,
        WBSStatus,
    )

    repo = SQLiteWBSMasterRepository(sqlite3.connect(":memory:"))
    repo.save(root())
    repo.save(
        WBSMaster(
            scope(),
            "W-CIVIL",
            WBSParentKind.WBS,
            "W-ROOT",
            "1.1",
            "Civil",
            0,
            status=WBSStatus.ACTIVE,
            percent_complete_technique=PercentCompleteTechnique.MILESTONES,
        )
    )
    repo.save(child("W-CIVIL-SITE", "W-CIVIL", code="1.1.1", name="Site works", sequence_number=0))
    repo.save(child("W-PM", "W-ROOT", code="1.2", name="Project management", sequence_number=1))
    source = repo.replace_milestones(
        scope(),
        "W-CIVIL",
        (
            WBSMilestone(scope(), "W-CIVIL", "M-1", "Design", 9.0, True, 0),
            WBSMilestone(scope(), "W-CIVIL", "M-2", "Permits", 3.0, False, 1),
        ),
        expected_revision=1,
    )[0]
    return repo, source


def test_copy_subtree_creates_new_records_and_keeps_the_source_unchanged():
    repo, source = _copy_fixture()

    copied = repo.copy_subtree(
        scope(),
        "W-CIVIL",
        target_parent_wbs_id="W-PM",
        root_code="1.2.1",
        expected_revision=source.record_revision,
    )

    assert len(copied) == 2
    copy_root, copy_child = copied
    assert copy_root.wbs_id.startswith("WBS-COPY-")
    assert copy_root.parent_kind is WBSParentKind.WBS
    assert copy_root.parent_wbs_id == "W-PM"
    assert copy_root.code == "1.2.1"
    assert copy_root.name == "Civil"
    assert copy_root.record_revision == 1
    assert copy_root.status.value == "active"
    assert copy_root.percent_complete_technique.value == "milestones"
    assert copy_child.parent_wbs_id == copy_root.wbs_id
    assert copy_child.code == "1.1.1"
    assert copy_child.name == "Site works"

    original = repo.get(scope(), "W-CIVIL")
    assert original is not None
    assert original.record_revision == source.record_revision
    # The source subtree and its original child are still in place; the copy
    # added two further records beneath the target.
    assert len(repo.list(scope())) == 6
    assert repo.get(scope(), "W-CIVIL-SITE") is not None


def test_copy_subtree_copies_weighted_milestones():
    from construction_pm.wbs_master_repository import weighted_percent_complete

    repo, source = _copy_fixture()
    copied = repo.copy_subtree(
        scope(),
        "W-CIVIL",
        target_parent_wbs_id="W-PM",
        root_code="1.2.1",
        expected_revision=source.record_revision,
    )

    milestones = repo.list_milestones(scope(), copied[0].wbs_id)
    assert [item.milestone_id for item in milestones] == ["M-1", "M-2"]
    assert [item.record_revision for item in milestones] == [1, 1]
    assert weighted_percent_complete(milestones) == 75.0


def test_copy_subtree_rejects_a_stale_source_revision():
    repo, source = _copy_fixture()

    with pytest.raises(WBSPersistenceError, match="REVISION_CONFLICT"):
        repo.copy_subtree(
            scope(),
            "W-CIVIL",
            target_parent_wbs_id="W-PM",
            root_code="1.2.1",
            expected_revision=source.record_revision - 1,
        )
    assert len(repo.list(scope())) == 4


def test_copy_subtree_rejects_a_sibling_code_collision_without_writing():
    repo, source = _copy_fixture()
    repo.save(child("W-PM-EXISTING", "W-PM", code="1.2.1", name="Existing", sequence_number=0))

    with pytest.raises(WBSPersistenceError, match="WBS_SIBLING_CODE_CONFLICT"):
        repo.copy_subtree(
            scope(),
            "W-CIVIL",
            target_parent_wbs_id="W-PM",
            root_code="1.2.1",
            expected_revision=source.record_revision,
        )
    assert not any(node.wbs_id.startswith("WBS-COPY-") for node in repo.list(scope()))


def test_copy_subtree_rejects_an_unknown_target():
    repo, source = _copy_fixture()

    with pytest.raises(WBSPersistenceError, match="WBS_PARENT_NOT_FOUND_OR_SCOPE_MISMATCH"):
        repo.copy_subtree(
            scope(),
            "W-CIVIL",
            target_parent_wbs_id="W-MISSING",
            root_code="1.2.1",
            expected_revision=source.record_revision,
        )
    with pytest.raises(WBSPersistenceError, match="WBS_NOT_FOUND"):
        repo.copy_subtree(
            scope(),
            "W-MISSING",
            target_parent_wbs_id="W-PM",
            root_code="1.2.1",
            expected_revision=1,
        )


def test_copy_subtree_validates_its_arguments():
    repo, source = _copy_fixture()

    with pytest.raises(WBSPersistenceError, match="INVALID_WBS_PARENT"):
        repo.copy_subtree(
            scope(),
            "W-CIVIL",
            target_parent_wbs_id="",
            root_code="1.2.1",
            expected_revision=source.record_revision,
        )
    with pytest.raises(WBSPersistenceError, match="INVALID_WBS_CODE"):
        repo.copy_subtree(
            scope(),
            "W-CIVIL",
            target_parent_wbs_id="W-PM",
            root_code="   ",
            expected_revision=source.record_revision,
        )
    with pytest.raises(WBSPersistenceError, match="EXPECTED_REVISION_REQUIRED"):
        repo.copy_subtree(
            scope(),
            "W-CIVIL",
            target_parent_wbs_id="W-PM",
            root_code="1.2.1",
            expected_revision=0,
        )
