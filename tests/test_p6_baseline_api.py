from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import pytest

from construction_pm.application.authorization import AuthorizationContext, AuthorizationError, default_project_policy
from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_baseline_api import P6_BASELINE_API_VERSION, P6BaselineAPI
from construction_pm.p6_baseline_repository import P6Baseline, P6BaselineApplicationService, SQLiteP6BaselineRepository


class TransactionManager:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    @contextmanager
    def transaction(self):
        try:
            yield
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise


def scope(revision: int = 7) -> BackendScope:
    return BackendScope("tenant-a", "project-a", revision)


def auth(*, tenant_id: str = "tenant-a", project_id: str = "project-a", role: str = "planner") -> AuthorizationContext:
    return AuthorizationContext(
        tenant_id=tenant_id,
        project_id=project_id,
        user_id="u1",
        roles=frozenset({role}),
    )


def baseline(item_id: str = "b-1") -> P6Baseline:
    return P6Baseline(
        scope(), item_id, "Approved Baseline", "PRIMARY", 3,
        "2026-09-28T10:00:00Z", "immutable metadata",
    )


def api() -> P6BaselineAPI:
    connection = sqlite3.connect(":memory:")
    repository = SQLiteP6BaselineRepository(connection)
    service = P6BaselineApplicationService(repository, TransactionManager(connection))
    return P6BaselineAPI(service, default_project_policy())


def test_versioned_typed_create_get_and_list_boundary() -> None:
    schema_path = Path(__file__).parents[1] / "shared/contracts/p6-baseline-api.v1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert P6_BASELINE_API_VERSION == schema["properties"]["contract_version"]["const"]

    instance = api()
    created = instance.create(baseline(), auth_context=auth())

    assert created["contract_version"] == P6_BASELINE_API_VERSION
    assert created["kind"] == "p6_baseline"
    assert created["baseline"]["baseline_id"] == "b-1"
    assert instance.get(scope(), "b-1", auth_context=auth()) == created
    assert instance.list(scope(), auth_context=auth()) == (created,)


def test_cross_scope_and_missing_permission_are_rejected() -> None:
    instance = api()
    with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
        instance.create(baseline(), auth_context=auth(tenant_id="other"))
    with pytest.raises(AuthorizationError, match="authorization denied"):
        instance.get(scope(), "b-1", auth_context=auth(role="writer"))
