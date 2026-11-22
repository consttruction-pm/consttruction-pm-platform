"""Integration tests for the frozen reference-project persistence.

The test opens a real in-memory preview database, composes the same repository
graph the preview runtime uses, persists the three bundled projects, runs the
canonical schedule engine and measures EVM from the persisted facts. It then
repeats the import to prove that a restart never duplicates or mutates a
project that already exists.
"""

from __future__ import annotations

import sqlite3
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from construction_pm.backend_p0.models import BackendScope
from construction_pm.importing.reference_persistence import (
    BUNDLE_CONTRACT,
    DEFAULT_BUNDLE_PATH,
    ensure_reference_projects,
    load_bundle,
    read_run_manifests,
)
from construction_pm.p6_activity_period_actual_repository import (
    SQLiteP6ActivityPeriodActualRepository,
)
from construction_pm.p6_earned_value_read_model import P6EarnedValueReadModelService
from construction_pm.preview.runtime import PreviewRepositories
from construction_pm.preview.storage import (
    DEMO_PROJECT_MEMBER_USER_IDS,
    PreviewStore,
)
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver

TENANT = "cubi-preview-tenant"
PROJECT_IDS = ("CUBI-REF-001", "CUBI-REF-002", "CUBI-REF-003")


def _runtime() -> tuple[sqlite3.Connection, PreviewRepositories, PreviewStore]:
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    repositories = PreviewRepositories.create(connection)
    store = PreviewStore(connection)
    return connection, repositories, store


def test_bundle_is_packaged_and_valid() -> None:
    assert DEFAULT_BUNDLE_PATH.exists()
    bundle = load_bundle()
    assert bundle["contract"] == BUNDLE_CONTRACT
    assert tuple(sorted(bundle["projects"])) == PROJECT_IDS
    assert bundle["source"]["sha256"].startswith("0848454d")


def test_ensure_persists_every_layer_and_runs_the_engine() -> None:
    connection, repositories, store = _runtime()
    results = ensure_reference_projects(
        repositories,
        store,
        tenant_id=TENANT,
        member_user_ids=DEMO_PROJECT_MEMBER_USER_IDS,
    )

    assert tuple(item.project_id for item in results) == PROJECT_IDS
    bundle = load_bundle()
    for result in results:
        assert result.manifest.status == "SUCCESS"
        assert result.manifest.run_id
        assert len(result.manifest.input_hash) == 64
        assert len(result.manifest.output_hash) == 64
        assert result.manifest.project_revision == 1
        assert result.manifest.engine_version
        assert result.manifest.options["project_id"] == result.project_id
        scope = BackendScope(TENANT, result.project_id, 1)
        assert len(repositories.activities.list(scope)) == 180
        assert len(repositories.relationships.list(scope)) == 238
        entry = bundle["projects"][result.project_id]
        assert len(repositories.wbs.list(scope)) == 1 + len(entry["eps"]) + len(entry["wbs"])
        assert len(repositories.resource_assignments.list(scope)) == 240
        assert len(repositories.baseline_activities.list(scope, result.project_id + "-BL-001")) == 180
        assert len(repositories.expenses.list(scope)) > 180

    third = next(item for item in results if item.project_id == "CUBI-REF-003")
    assert len(third.manifest.warnings) == 3
    assert all("negative total float" in item for item in third.manifest.warnings)

    visible = {
        item.project_id
        for item in store.list_for_user(TENANT, "preview-admin")
        if item.project_id.startswith("CUBI-REF-")
    }
    assert visible == set(PROJECT_IDS)
    assert store.member_ids(TENANT, "CUBI-REF-001") == tuple(
        sorted(DEMO_PROJECT_MEMBER_USER_IDS)
    )
    assert len(read_run_manifests(connection, TENANT, "CUBI-REF-001")) == 1
    connection.close()


def test_second_ensure_is_a_no_op() -> None:
    connection, repositories, store = _runtime()
    ensure_reference_projects(
        repositories, store, tenant_id=TENANT, member_user_ids=DEMO_PROJECT_MEMBER_USER_IDS
    )
    before = connection.execute(
        "SELECT COUNT(*) FROM activity_master"
    ).fetchone()[0]
    again = ensure_reference_projects(
        repositories, store, tenant_id=TENANT, member_user_ids=DEMO_PROJECT_MEMBER_USER_IDS
    )
    after = connection.execute(
        "SELECT COUNT(*) FROM activity_master"
    ).fetchone()[0]
    assert again == ()
    assert before == after == 540
    connection.close()


def test_earned_value_is_reproducible_from_persisted_facts() -> None:
    connection, repositories, store = _runtime()
    results = ensure_reference_projects(
        repositories, store, tenant_id=TENANT, member_user_ids=DEMO_PROJECT_MEMBER_USER_IDS
    )
    service = P6EarnedValueReadModelService(
        baseline_activities=repositories.baseline_activities,
        activities=repositories.activities,
        actuals=SQLiteP6ActivityPeriodActualRepository(connection),
        expenses=repositories.expenses,
        resolver=WorkingTimeResolver(
            WorkingCalendar(working_weekdays=frozenset(range(7)))
        ),
        wbs_repository=repositories.wbs,
        resource_assignments=None,
    )
    for result in results:
        scope = BackendScope(TENANT, result.project_id, 1)
        payload = service.read(
            scope,
            f"{result.project_id}-BL-001",
            data_date=date(2026, 11, 22),
            currency="USD",
        ).to_payload()
        earned = payload["earned_value"]
        for key in (
            "planned_value",
            "earned_value",
            "actual_cost",
            "cost_variance",
            "schedule_variance",
            "cost_performance_index",
            "schedule_performance_index",
            "budget_at_completion",
            "estimate_to_complete",
            "estimate_at_completion",
            "variance_at_completion",
        ):
            assert earned[key] is not None, (result.project_id, key)
        assert Decimal("0.9") < Decimal(earned["cost_performance_index"]) < Decimal("1.1")
        assert Decimal("0.9") < Decimal(earned["schedule_performance_index"]) < Decimal("1.1")
        assert len(payload["activities"]) == 180
    connection.close()
