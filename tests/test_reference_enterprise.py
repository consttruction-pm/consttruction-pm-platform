"""Integration tests for the Enterprise registers of the reference bundle.

The tests open a real in-memory preview database, persist the Engineering
projects, then persist the Enterprise rows into the same canonical stores the
product reads (risk register, issue register, document register, Enterprise
task store and the generic revisioned register). They assert exact counts,
repeatability and that unsupported source sheets are reported rather than
silently dropped.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from construction_pm.backend_p0.models import BackendScope
from construction_pm.enterprise_workbench_http import EnterpriseWorkbenchStore
from construction_pm.importing.reference_enterprise import (
    UNSUPPORTED_SHEETS,
    ensure_reference_enterprise,
    read_enterprise_state,
)
from construction_pm.importing.reference_persistence import (
    ensure_reference_projects,
    load_bundle,
)
from construction_pm.preview.runtime import PreviewRepositories
from construction_pm.preview.storage import DEMO_PROJECT_MEMBER_USER_IDS, PreviewStore

TENANT = "cubi-preview-tenant"
PROJECT_IDS = ("CUBI-REF-001", "CUBI-REF-002", "CUBI-REF-003")

EXPECTED = {
    "risks": 15,
    "issues": 8,
    "documents": 15,
    "tasks": 12,
    "organizations": 8,
    "teams": 8,
    "responsibilities": 30,
    "contracts": 5,
    "contract_packages": 5,
    "procurement": 5,
    "vendors": 5,
    "change_requests": 4,
    "communication": 1,
    "approvals": 1,
    "forms": 1,
    "workflows": 1,
    "timesheets": 10,
    "milestones": 12,
}


def _runtime():
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    repositories = PreviewRepositories.create(connection)
    store = PreviewStore(connection)
    ensure_reference_projects(
        repositories, store, tenant_id=TENANT, member_user_ids=DEMO_PROJECT_MEMBER_USER_IDS
    )
    enterprise = EnterpriseWorkbenchStore(connection)
    enterprise.initialize()
    return connection, repositories, enterprise


def test_every_representable_row_is_persisted_once() -> None:
    connection, repositories, enterprise = _runtime()
    results = ensure_reference_enterprise(
        connection, repositories, enterprise, tenant_id=TENANT
    )
    assert tuple(item.project_id for item in results) == PROJECT_IDS
    for item in results:
        assert item.status == "COMPLETE"
        assert item.missing == {}
        for kind, total in EXPECTED.items():
            assert item.present[kind] == total, (item.project_id, kind)
            assert item.created[kind] == total, (item.project_id, kind)

    # The rows are in the canonical stores, not only in a marker table.
    assert len(repositories.risks.list_risks(TENANT, "CUBI-REF-001")) == 15
    assert len(repositories.issues.list(BackendScope(TENANT, "CUBI-REF-001", 1))) == 8
    assert len(
        repositories.documents.list_all(tenant_id=TENANT, project_id="CUBI-REF-001")
    ) == 15
    connection.close()


def test_second_import_creates_nothing_and_keeps_counts() -> None:
    connection, repositories, enterprise = _runtime()
    ensure_reference_enterprise(connection, repositories, enterprise, tenant_id=TENANT)
    before = connection.execute("SELECT COUNT(*) FROM enterprise_records").fetchone()[0]
    again = ensure_reference_enterprise(
        connection, repositories, enterprise, tenant_id=TENANT
    )
    after = connection.execute("SELECT COUNT(*) FROM enterprise_records").fetchone()[0]
    assert before == after
    for item in again:
        assert all(value == 0 for value in item.created.values())
        assert item.missing == {}
    connection.close()


def test_risk_register_keeps_source_fields_the_model_has_no_column_for() -> None:
    connection, repositories, enterprise = _runtime()
    ensure_reference_enterprise(connection, repositories, enterprise, tenant_id=TENANT)
    stored = repositories.risks.list_risks(TENANT, "CUBI-REF-001")
    assert all(item.risk.status == "open" for item in stored)
    first = next(item.risk for item in stored if item.risk.risk_id.endswith("RSK-001"))
    assert "Source category: Procurement" in first.description
    assert "Response" in first.description
    assert first.response_owner
    connection.close()


def test_unsupported_sheets_are_reported_not_dropped() -> None:
    bundle = load_bundle()
    for project_id in PROJECT_IDS:
        entry = bundle["projects"][project_id]
        for sheet in UNSUPPORTED_SHEETS:
            assert entry.get(sheet), (project_id, sheet)
    connection, repositories, enterprise = _runtime()
    results = ensure_reference_enterprise(
        connection, repositories, enterprise, tenant_id=TENANT
    )
    assert all(tuple(item.unsupported) == tuple(UNSUPPORTED_SHEETS) for item in results)
    state = read_enterprise_state(connection, TENANT)
    assert {row["status"] for row in state} == {"COMPLETE"}
    connection.close()
