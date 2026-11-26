"""Contract tests for the guarded CUBI-DAM-001 import command.

The command has two confirmation paths (first import and idempotent re-run) and
both compare the durable journal status. A regression here silently blocks the
only supported way to create or verify the shared dam workspace, so the status
vocabulary is pinned on the writer side as well as in the command.
"""

from __future__ import annotations

import importlib.util
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from construction_pm.importing.reference_journal import (
    IMPORT_STATUS_COMPLETE,
    PostgresReferenceJournal,
    SQLiteReferenceJournal,
)

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "import_dam_reference_project.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("import_dam_reference_project", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_journal_status_is_the_canonical_complete_value() -> None:
    assert IMPORT_STATUS_COMPLETE == "COMPLETE"


def test_command_accepts_only_a_complete_manifest() -> None:
    script = _load_script()
    complete = {"project_id": "CUBI-DAM-001", "status": IMPORT_STATUS_COMPLETE}
    assert script._import_is_complete(complete) is True
    assert script._import_is_complete({"status": "PARTIAL"}) is False
    assert script._import_is_complete({"status": "SUCCESS"}) is False
    assert script._import_is_complete(None) is False
    assert script._import_is_complete({}) is False


def test_sqlite_journal_records_the_canonical_status() -> None:
    connection = sqlite3.connect(":memory:")
    journal = SQLiteReferenceJournal(connection)
    journal.prepare()
    journal.record_import(
        "tenant",
        "CUBI-DAM-001",
        {"activities": 720},
        datetime(2026, 11, 26, tzinfo=timezone.utc),
        "a" * 64,
    )
    status = connection.execute(
        "SELECT status FROM cubi_reference_import WHERE project_id='CUBI-DAM-001'"
    ).fetchone()[0]
    assert status == IMPORT_STATUS_COMPLETE


def test_postgres_journal_records_the_canonical_status() -> None:
    class _Connection:
        def __init__(self) -> None:
            self.params: tuple[object, ...] | None = None

        def execute(self, _statement: str, params: tuple[object, ...]):
            self.params = params
            return self

    connection = _Connection()
    PostgresReferenceJournal(connection).record_import(
        "tenant",
        "CUBI-DAM-001",
        {"activities": 720},
        datetime(2026, 11, 26, tzinfo=timezone.utc),
        "a" * 64,
    )
    assert connection.params is not None
    assert connection.params[4] == IMPORT_STATUS_COMPLETE
