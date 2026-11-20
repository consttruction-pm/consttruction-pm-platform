import json
from dataclasses import replace
from datetime import date
from decimal import Decimal
import sqlite3

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.activity_master_repository import (
    ActivityMaster,
    ActivityPersistenceError,
    SQLiteActivityMasterRepository,
)
from construction_pm.scheduling.activity import (
    ActivityDurationType,
    ActivityLevelingPriority,
    ActivityStatus,
    ActivityStatusCode,
    ActivityType,
    PercentCompleteType,
)
from construction_pm.scheduling.time_duration import DurationUnit
from construction_pm.wbs_master_repository import (
    SQLiteWBSMasterRepository,
    WBSMaster,
    WBSParentKind,
)


def scope(revision: int = 7) -> BackendScope:
    return BackendScope("T-1", "P-1", revision)


def activity(revision: int = 7, duration: str = "2", expected_finish: date | None = None) -> ActivityMaster:
    return ActivityMaster(
        scope(revision),
        "A-1",
        Decimal(duration),
        DurationUnit.WORKING_DAY,
        date(2026, 9, 21),
        0,
        expected_finish,
    )


def test_activity_master_save_preserves_caller_owned_transaction():
    connection = sqlite3.connect(":memory:")
    repo = SQLiteActivityMasterRepository(connection)
    connection.execute("CREATE TABLE transaction_probe (probe_id INTEGER PRIMARY KEY)")
    connection.execute("BEGIN")
    connection.execute("INSERT INTO transaction_probe (probe_id) VALUES (1)")

    stored = repo.save(activity())

    assert connection.in_transaction
    assert repo.get(scope(), "A-1") == stored
    connection.rollback()

    assert repo.get(scope(), "A-1") is None
    assert connection.execute("SELECT COUNT(*) FROM transaction_probe").fetchone()[0] == 0


def test_activity_master_revision_conflict_does_not_rollback_caller_transaction():
    connection = sqlite3.connect(":memory:")
    repo = SQLiteActivityMasterRepository(connection)
    original = repo.save(activity())
    connection.execute("CREATE TABLE transaction_probe (probe_id INTEGER PRIMARY KEY)")
    connection.execute("BEGIN")
    connection.execute("INSERT INTO transaction_probe (probe_id) VALUES (1)")

    with pytest.raises(ActivityPersistenceError, match="REVISION_CONFLICT"):
        repo.save(activity(duration="4"), expected_revision=0)

    # The caller still owns the transaction after the repository raises.
    assert connection.in_transaction
    assert connection.execute("SELECT COUNT(*) FROM transaction_probe").fetchone()[0] == 1
    connection.rollback()

    assert repo.get(scope(), "A-1") == original
    assert connection.execute("SELECT COUNT(*) FROM transaction_probe").fetchone()[0] == 0


def test_activity_master_owned_transaction_rolls_back_failed_insert():
    connection = sqlite3.connect(":memory:")
    repo = SQLiteActivityMasterRepository(connection)
    connection.execute(
        """CREATE TRIGGER reject_activity_insert
        BEFORE INSERT ON activity_master
        BEGIN
            SELECT RAISE(ABORT, 'injected activity insert failure');
        END"""
    )

    with pytest.raises(sqlite3.IntegrityError, match="injected activity insert failure"):
        repo.save(activity())

    assert not connection.in_transaction
    assert repo.get(scope(), "A-1") is None


def test_activity_master_round_trip_and_revision():
    repo = SQLiteActivityMasterRepository(sqlite3.connect(":memory:"))
    stored = repo.save(activity())
    assert stored.record_revision == 1
    assert repo.get(scope(), "A-1") == stored

    updated = repo.save(activity(duration="3"), expected_revision=1)
    assert updated.record_revision == 2
    assert updated.duration_value == Decimal("3")


def test_activity_master_rejects_stale_update():
    repo = SQLiteActivityMasterRepository(sqlite3.connect(":memory:"))
    repo.save(activity())
    with pytest.raises(ActivityPersistenceError, match="REVISION_CONFLICT"):
        repo.save(activity(duration="4"), expected_revision=0)


def test_activity_master_rejects_cross_revision_read():
    repo = SQLiteActivityMasterRepository(sqlite3.connect(":memory:"))
    repo.save(activity(revision=7))
    with pytest.raises(ActivityPersistenceError, match="REVISION_CONFLICT"):
        repo.get(scope(8), "A-1")


def test_activity_master_preserves_explicit_duration_unit():
    repo = SQLiteActivityMasterRepository(sqlite3.connect(":memory:"))
    stored = repo.save(activity())
    assert stored.duration_unit is DurationUnit.WORKING_DAY
    assert stored.duration_value == Decimal("2")


def test_activity_master_persists_expected_finish():
    repo = SQLiteActivityMasterRepository(sqlite3.connect(":memory:"))
    stored = repo.save(activity(expected_finish=date(2026, 9, 24)))
    assert stored.expected_finish == date(2026, 9, 24)
    assert repo.get(scope(), "A-1").expected_finish == date(2026, 9, 24)


def test_activity_master_updates_expected_finish_with_revision():
    repo = SQLiteActivityMasterRepository(sqlite3.connect(":memory:"))
    repo.save(activity(expected_finish=date(2026, 9, 24)))
    updated = repo.save(activity(expected_finish=date(2026, 9, 25)), expected_revision=1)
    assert updated.record_revision == 2
    assert updated.expected_finish == date(2026, 9, 25)


def test_activity_master_preserves_all_progress_state():
    repo = SQLiteActivityMasterRepository(sqlite3.connect(":memory:"))
    source = ActivityMaster(
        scope(),
        "A-PROGRESS",
        Decimal("4"),
        DurationUnit.WORKING_DAY,
        date(2026, 9, 21),
        0,
        date(2026, 9, 30),
        date(2026, 9, 24),
        2,
        date(2026, 9, 25),
        37.5,
        PercentCompleteType.PHYSICAL,
    )

    stored = repo.save(source)
    restored = repo.get(scope(), "A-PROGRESS")

    assert stored.actual_start == date(2026, 9, 21)
    assert stored.actual_finish == date(2026, 9, 24)
    assert stored.remaining_duration == 2
    assert stored.remaining_start == date(2026, 9, 25)
    assert stored.percent_complete == 37.5
    assert stored.percent_complete_type is PercentCompleteType.PHYSICAL
    assert restored == stored


def test_activity_master_preserves_progress_state_on_update():
    repo = SQLiteActivityMasterRepository(sqlite3.connect(":memory:"))
    initial = ActivityMaster(
        scope(),
        "A-UPDATE",
        Decimal("4"),
        DurationUnit.WORKING_DAY,
        date(2026, 9, 21),
        0,
        None,
        None,
        4,
        date(2026, 9, 21),
        10.0,
        PercentCompleteType.DURATION,
    )
    repo.save(initial)

    updated = ActivityMaster(
        scope(),
        "A-UPDATE",
        Decimal("5"),
        DurationUnit.WORKING_DAY,
        date(2026, 9, 21),
        0,
        None,
        None,
        3,
        date(2026, 9, 22),
        40.0,
        PercentCompleteType.PHYSICAL,
    )
    saved = repo.save(updated, expected_revision=1)

    assert saved.record_revision == 2
    assert repo.get(scope(), "A-UPDATE") == saved


def test_activity_master_round_trips_and_updates_distinct_planned_fields():
    repo = SQLiteActivityMasterRepository(sqlite3.connect(":memory:"))
    source = replace(
        activity(),
        planned_finish=date(2026, 9, 28),
        leveling_priority=ActivityLevelingPriority.LOWEST,
        original_duration=14,
    )
    stored = repo.save(source)
    restored = repo.get(scope(), "A-1")
    assert restored == stored
    assert restored.planned_finish == date(2026, 9, 28)
    assert restored.leveling_priority is ActivityLevelingPriority.LOWEST
    assert restored.original_duration == 14
    assert repo.list(scope()) == (stored,)

    updated = repo.save(
        replace(
            source,
            planned_finish=date(2026, 9, 29),
            leveling_priority=ActivityLevelingPriority.HIGH,
            original_duration=16,
        ),
        expected_revision=1,
    )
    assert updated.record_revision == 2
    assert updated.planned_finish == date(2026, 9, 29)
    assert updated.leveling_priority is ActivityLevelingPriority.HIGH
    assert updated.original_duration == 16
    assert repo.get(scope(), "A-1") == updated


def test_activity_master_additively_migrates_legacy_schema_for_leveling_fields():
    connection = sqlite3.connect(":memory:")
    connection.execute(
        """CREATE TABLE activity_master (
            tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision INTEGER NOT NULL,
            activity_id TEXT NOT NULL, duration_value TEXT NOT NULL, duration_unit TEXT NOT NULL,
            actual_start TEXT, actual_finish TEXT, remaining_duration INTEGER, remaining_start TEXT,
            percent_complete REAL, percent_complete_type TEXT NOT NULL DEFAULT 'DURATION',
            record_revision INTEGER NOT NULL, expected_finish TEXT,
            PRIMARY KEY (tenant_id, project_id, activity_id))"""
    )
    connection.commit()
    repo = SQLiteActivityMasterRepository(connection)
    columns = {row[1] for row in connection.execute("PRAGMA table_info(activity_master)")}
    assert {"planned_finish", "leveling_priority", "original_duration", "short_name"}.issubset(columns)
    stored = repo.save(
        replace(
            activity(),
            planned_finish=date(2026, 9, 28),
            leveling_priority=ActivityLevelingPriority.TOP,
            original_duration=14,
            short_name="CP-1",
        )
    )
    assert stored.short_name == "CP-1"
    assert repo.get(scope(), "A-1") == stored


@pytest.mark.parametrize("value", [True, -1, 1.5, "14"])
def test_activity_master_rejects_invalid_original_duration(value):
    repo = SQLiteActivityMasterRepository(sqlite3.connect(":memory:"))
    with pytest.raises(ActivityPersistenceError, match="INVALID_ORIGINAL_DURATION"):
        repo.save(replace(activity(), original_duration=value))


def test_activity_master_round_trips_distinct_name_type_status_and_status_code():
    repo = SQLiteActivityMasterRepository(sqlite3.connect(":memory:"))
    source = replace(
        activity(),
        name="Bridge Deck",
        activity_type=ActivityType.LEVEL_OF_EFFORT,
        status=ActivityStatus.IN_PROGRESS,
        status_code=ActivityStatusCode.ACTIVE,
    )
    stored = repo.save(source)
    assert repo.get(scope(), "A-1") == stored
    assert stored.name == "Bridge Deck"
    assert stored.activity_type is ActivityType.LEVEL_OF_EFFORT
    assert stored.status is ActivityStatus.IN_PROGRESS
    assert stored.status_code is ActivityStatusCode.ACTIVE

    updated = repo.save(
        replace(
            stored,
            name="Bridge Deck Inspection",
            activity_type=ActivityType.TASK_DEPENDENT,
            status=ActivityStatus.COMPLETED,
            status_code=ActivityStatusCode.INACTIVE,
        ),
        expected_revision=1,
    )
    assert updated.record_revision == 2
    assert updated.name == "Bridge Deck Inspection"
    assert updated.activity_type is ActivityType.TASK_DEPENDENT
    assert updated.status is ActivityStatus.COMPLETED
    assert updated.status_code is ActivityStatusCode.INACTIVE
    assert repo.get(scope(), "A-1") == updated


def test_activity_master_round_trips_and_updates_short_name():
    connection = sqlite3.connect(":memory:")
    repo = SQLiteActivityMasterRepository(connection)

    stored = repo.save(replace(activity(), name="Bridge Deck", short_name="CP-1"))
    assert stored.short_name == "CP-1"
    assert repo.get(scope(), "A-1") == stored

    updated = repo.save(
        replace(stored, short_name="CP-2"),
        expected_revision=1,
    )
    assert updated.record_revision == 2
    assert updated.short_name == "CP-2"
    assert repo.get(scope(), "A-1") == updated

    cleared = repo.save(replace(updated, short_name=None), expected_revision=2)
    assert cleared.short_name is None
    assert repo.get(scope(), "A-1") == cleared


@pytest.mark.parametrize("value", ["", "   ", 7, True])
def test_activity_master_rejects_invalid_short_name(value):
    repo = SQLiteActivityMasterRepository(sqlite3.connect(":memory:"))
    with pytest.raises(ActivityPersistenceError, match="INVALID_SHORT_NAME"):
        repo.save(replace(activity(), short_name=value))


def test_activity_master_persists_and_reassigns_canonical_wbs():
    connection = sqlite3.connect(":memory:")
    repo = SQLiteActivityMasterRepository(connection)
    wbs_repo = SQLiteWBSMasterRepository(connection)
    root = wbs_repo.save(
        WBSMaster(scope(), "W-ROOT", WBSParentKind.PROJECT, None, "1", "Project", 0)
    )
    child = wbs_repo.save(
        WBSMaster(scope(), "W-CHILD", WBSParentKind.WBS, "W-ROOT", "2", "Package", 1)
    )

    saved = repo.save(replace(activity(), wbs_id=root.wbs_id))
    assert saved.wbs_id == "W-ROOT"
    assert repo.get(scope(), "A-1") == saved
    assert repo.list(scope()) == (saved,)

    reassigned = repo.save(
        replace(saved, duration_value=Decimal("3"), wbs_id=child.wbs_id),
        expected_revision=1,
    )
    assert reassigned.record_revision == 2
    assert reassigned.wbs_id == "W-CHILD"
    assert repo.get(scope(), "A-1") == reassigned
    assert repo.list(scope()) == (reassigned,)

    # A canonical project must not lose its hierarchy link; the failed write
    # leaves the previously committed assignment untouched.
    with pytest.raises(ActivityPersistenceError, match="WBS_REQUIRED"):
        repo.save(replace(reassigned, wbs_id=None), expected_revision=2)
    assert repo.get(scope(), "A-1") == reassigned
    connection.close()


def test_activity_master_rejects_missing_cross_scope_and_stale_wbs_references():
    connection = sqlite3.connect(":memory:")
    repo = SQLiteActivityMasterRepository(connection)
    wbs_repo = SQLiteWBSMasterRepository(connection)

    with pytest.raises(ActivityPersistenceError, match="WBS_NOT_FOUND_OR_SCOPE_MISMATCH"):
        repo.save(replace(activity(), wbs_id="W-MISSING"))

    other_scope = BackendScope("T-OTHER", "P-OTHER", 7)
    wbs_repo.save(
        WBSMaster(other_scope, "W-OTHER", WBSParentKind.PROJECT, None, "1", "Other", 0)
    )
    with pytest.raises(ActivityPersistenceError, match="WBS_NOT_FOUND_OR_SCOPE_MISMATCH"):
        repo.save(replace(activity(), wbs_id="W-OTHER"))

    stale_scope = BackendScope(scope().tenant_id, scope().project_id, 8)
    wbs_repo.save(
        WBSMaster(stale_scope, "W-STALE", WBSParentKind.PROJECT, None, "1", "Stale", 0)
    )
    with pytest.raises(ActivityPersistenceError, match="REVISION_CONFLICT"):
        repo.save(replace(activity(), wbs_id="W-STALE"))

    with pytest.raises(ActivityPersistenceError, match="INVALID_WBS_ID"):
        repo.save(replace(activity(), wbs_id=123))

    assert repo.get(scope(), "A-1") is None
    connection.close()


def test_activity_master_duration_type_round_trips_and_updates_independently():
    repo = SQLiteActivityMasterRepository(sqlite3.connect(":memory:"))
    # The default is the P6 Fixed Duration & Units value, not an empty label.
    stored = repo.save(activity())
    assert stored.duration_type is ActivityDurationType.FIXED_DURATION_UNITS
    assert repo.get(scope(), "A-1").duration_type is ActivityDurationType.FIXED_DURATION_UNITS

    changed = replace(
        activity(), duration_type=ActivityDurationType.FIXED_UNITS_TIME
    )
    updated = repo.save(changed, expected_revision=1)
    assert updated.duration_type is ActivityDurationType.FIXED_UNITS_TIME
    assert repo.get(scope(), "A-1").duration_type is ActivityDurationType.FIXED_UNITS_TIME


def test_activity_master_migrates_an_existing_table_with_a_duration_type_default():
    connection = sqlite3.connect(":memory:")
    connection.execute(
        """CREATE TABLE activity_master (
            tenant_id TEXT NOT NULL, project_id TEXT NOT NULL,
            project_revision INTEGER NOT NULL, activity_id TEXT NOT NULL,
            duration_value TEXT NOT NULL, duration_unit TEXT NOT NULL,
            actual_start TEXT, actual_finish TEXT, remaining_duration INTEGER,
            remaining_start TEXT, percent_complete REAL, percent_complete_type TEXT,
            record_revision INTEGER NOT NULL DEFAULT 0, expected_finish TEXT,
            planned_finish TEXT, leveling_priority TEXT NOT NULL DEFAULT 'Normal',
            original_duration INTEGER, name TEXT NOT NULL DEFAULT '',
            activity_type TEXT NOT NULL DEFAULT 'Task Dependent',
            status TEXT NOT NULL DEFAULT 'Not Started',
            status_code TEXT NOT NULL DEFAULT 'Planned',
            short_name TEXT,
            PRIMARY KEY (tenant_id, project_id, activity_id))"""
    )
    connection.execute(
        "INSERT INTO activity_master (tenant_id, project_id, project_revision, "
        "activity_id, duration_value, duration_unit, percent_complete_type, "
        "record_revision) "
        "VALUES ('T-1', 'P-1', 7, 'A-LEGACY', '2', 'working-day', 'DURATION', 1)"
    )
    repo = SQLiteActivityMasterRepository(connection)
    restored = repo.get(scope(), "A-LEGACY")
    assert restored is not None
    assert restored.duration_type is ActivityDurationType.FIXED_DURATION_UNITS


def test_activity_master_cost_account_round_trips_and_clears_independently():
    repo = SQLiteActivityMasterRepository(sqlite3.connect(":memory:"))
    stored = repo.save(activity())
    assert stored.cost_account_id is None

    linked = repo.save(
        replace(activity(), cost_account_id="CA-CIVIL"), expected_revision=1
    )
    assert linked.cost_account_id == "CA-CIVIL"
    assert repo.get(scope(), "A-1").cost_account_id == "CA-CIVIL"

    cleared = repo.save(replace(activity(), cost_account_id=None), expected_revision=2)
    assert cleared.cost_account_id is None
    assert repo.get(scope(), "A-1").cost_account_id is None


def test_activity_master_rejects_an_empty_cost_account_reference():
    repo = SQLiteActivityMasterRepository(sqlite3.connect(":memory:"))
    with pytest.raises(ActivityPersistenceError, match="INVALID_COST_ACCOUNT_ID"):
        repo.save(replace(activity(), cost_account_id=" "))


def test_activity_master_migrates_an_existing_table_with_a_null_cost_account():
    connection = sqlite3.connect(":memory:")
    connection.execute(
        """CREATE TABLE activity_master (
            tenant_id TEXT NOT NULL, project_id TEXT NOT NULL,
            project_revision INTEGER NOT NULL, activity_id TEXT NOT NULL,
            duration_value TEXT NOT NULL, duration_unit TEXT NOT NULL,
            actual_start TEXT, actual_finish TEXT, remaining_duration INTEGER,
            remaining_start TEXT, percent_complete REAL, percent_complete_type TEXT,
            record_revision INTEGER NOT NULL DEFAULT 0, expected_finish TEXT,
            planned_finish TEXT, leveling_priority TEXT NOT NULL DEFAULT 'Normal',
            original_duration INTEGER, name TEXT NOT NULL DEFAULT '',
            activity_type TEXT NOT NULL DEFAULT 'Task Dependent',
            status TEXT NOT NULL DEFAULT 'Not Started',
            status_code TEXT NOT NULL DEFAULT 'Planned',
            short_name TEXT, duration_type TEXT,
            PRIMARY KEY (tenant_id, project_id, activity_id))"""
    )
    connection.execute(
        "INSERT INTO activity_master (tenant_id, project_id, project_revision, "
        "activity_id, duration_value, duration_unit, percent_complete_type, "
        "record_revision) "
        "VALUES ('T-1', 'P-1', 7, 'A-LEGACY', '2', 'working-day', 'DURATION', 1)"
    )
    repo = SQLiteActivityMasterRepository(connection)
    restored = repo.get(scope(), "A-LEGACY")
    assert restored is not None
    assert restored.cost_account_id is None


def _renumber_reference_fixture(connection: sqlite3.Connection) -> None:
    connection.execute(
        "CREATE TABLE relationship_master (tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, "
        "project_revision INTEGER NOT NULL, relationship_id TEXT NOT NULL, predecessor_id TEXT NOT NULL, "
        "successor_id TEXT NOT NULL, relationship_type TEXT NOT NULL, lag_value TEXT NOT NULL, "
        "lag_unit TEXT NOT NULL, record_revision INTEGER NOT NULL, "
        "PRIMARY KEY (tenant_id, project_id, relationship_id))"
    )
    connection.execute(
        "CREATE TABLE p6_activity_code_assignment (tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, "
        "project_revision INTEGER NOT NULL, assignment_id TEXT NOT NULL, activity_id TEXT NOT NULL, "
        "code_type TEXT NOT NULL, code_value TEXT NOT NULL, description TEXT, record_revision INTEGER NOT NULL, "
        "created_at TEXT NOT NULL, updated_at TEXT NOT NULL, "
        "PRIMARY KEY (tenant_id, project_id, assignment_id))"
    )
    connection.execute(
        "CREATE TABLE p6_activity_step (tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, "
        "project_revision INTEGER NOT NULL, step_id TEXT NOT NULL, activity_id TEXT NOT NULL, "
        "sequence INTEGER NOT NULL, description TEXT NOT NULL, weight REAL NOT NULL, "
        "percent_complete REAL NOT NULL, record_revision INTEGER NOT NULL, "
        "PRIMARY KEY (tenant_id, project_id, step_id))"
    )
    connection.execute(
        "CREATE TABLE p6_expense (tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, "
        "project_revision INTEGER NOT NULL, expense_id TEXT NOT NULL, name TEXT NOT NULL, "
        "category TEXT NOT NULL, activity_id TEXT, wbs_id TEXT, expense_date TEXT, planned_cost TEXT, "
        "actual_cost TEXT, remaining_cost TEXT, currency TEXT, note TEXT, "
        "PRIMARY KEY (tenant_id, project_id, expense_id))"
    )
    connection.execute(
        "CREATE TABLE project_documents (tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, "
        "document_id TEXT NOT NULL, document_json TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1, "
        "PRIMARY KEY (tenant_id, project_id, document_id))"
    )
    connection.execute(
        "INSERT INTO relationship_master VALUES "
        "('T-1','P-1',7,'R-1','A-1','A-2','FS','0','working-day',1)"
    )
    connection.execute(
        "INSERT INTO p6_activity_code_assignment VALUES "
        "('T-1','P-1',7,'CODE-1','A-1','AREA','CIVIL',NULL,1,'2026-01-01','2026-01-01')"
    )
    connection.execute(
        "INSERT INTO p6_activity_step VALUES "
        "('T-1','P-1',7,'STEP-1','A-1',1,'Pour',1,0,1)"
    )
    connection.execute(
        "INSERT INTO p6_expense VALUES "
        "('T-1','P-1',7,'EXP-1','Formwork','labor','A-1',NULL,NULL,'100','0','100','USD',NULL)"
    )
    connection.execute(
        "INSERT INTO project_documents VALUES ('T-1','P-1','DOC-1',?,1)",
        (json.dumps({"document_id": "DOC-1", "linked_entity_refs": ["A-1", "W-1"]}),),
    )


def test_activity_master_renumber_moves_every_reference_and_can_reuse_ids():
    connection = sqlite3.connect(":memory:")
    repo = SQLiteActivityMasterRepository(connection)
    repo.save(replace(activity(), name="Foundation activity"))
    repo.save(replace(activity(), activity_id="A-2", name="Second activity"))
    _renumber_reference_fixture(connection)

    result = repo.renumber(scope(), (("A-1", "A-20", 1), ("A-2", "A-1", 1)))

    assert result["renumbered"] == 2
    assert result["references_updated"] >= 5
    assert repo.get(scope(), "A-2") is None
    assert repo.get(scope(), "A-20").name == "Foundation activity"
    # The ID vacated by the first activity is now owned by the second one.
    assert repo.get(scope(), "A-1").name == "Second activity"
    assert connection.execute(
        "SELECT predecessor_id, successor_id FROM relationship_master WHERE relationship_id='R-1'"
    ).fetchone() == ("A-20", "A-1")
    assert connection.execute(
        "SELECT activity_id FROM p6_activity_code_assignment WHERE assignment_id='CODE-1'"
    ).fetchone()[0] == "A-20"
    assert connection.execute(
        "SELECT activity_id FROM p6_activity_step WHERE step_id='STEP-1'"
    ).fetchone()[0] == "A-20"
    assert connection.execute(
        "SELECT activity_id FROM p6_expense WHERE expense_id='EXP-1'"
    ).fetchone()[0] == "A-20"
    document = json.loads(
        connection.execute(
            "SELECT document_json FROM project_documents WHERE document_id='DOC-1'"
        ).fetchone()[0]
    )
    assert document["linked_entity_refs"] == ["A-20", "W-1"]


def test_activity_master_renumber_rejects_collisions_and_stale_revisions():
    connection = sqlite3.connect(":memory:")
    repo = SQLiteActivityMasterRepository(connection)
    repo.save(activity())
    repo.save(replace(activity(), activity_id="A-2", name="Second activity"))

    with pytest.raises(ActivityPersistenceError, match="RENUMBER_TARGET_EXISTS"):
        repo.renumber(scope(), (("A-1", "A-2", 1),))
    with pytest.raises(ActivityPersistenceError, match="REVISION_CONFLICT"):
        repo.renumber(scope(), (("A-1", "A-10", 9),))

    assert repo.get(scope(), "A-1") is not None
    assert repo.get(scope(), "A-10") is None
