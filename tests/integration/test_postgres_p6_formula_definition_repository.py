from __future__ import annotations

import os
import uuid

import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
if not DSN:
    pytest.skip("CONSTRUCTION_PM_POSTGRES_DSN is not configured", allow_module_level=True)

from construction_pm.backend_p0.models import BackendScope
from construction_pm.client_sync.postgres_transaction import PostgresTransactionManager
from construction_pm.p6_formula_definition_repository import (
    P6FormulaDefinitionPersistenceError,
    PersistedP6FormulaDefinition,
    PostgresP6FormulaDefinitionRepository,
)
from construction_pm.p6_formula_engine import FormulaDefinition, FormulaType


def scope(revision: int = 4) -> BackendScope:
    suffix = uuid.uuid4().hex
    return BackendScope(f"formula-tenant-{suffix}", f"formula-project-{suffix}", revision)


def record(current_scope: BackendScope, version: str = "1.0") -> PersistedP6FormulaDefinition:
    return PersistedP6FormulaDefinition(
        scope=current_scope,
        semantic_version="p6-formula.v1",
        semantic_reference="shared-core:p6-formula",
        definition=FormulaDefinition(
            "activity.total", version, "[activity.qty] * [activity.rate]", FormulaType.NUMBER
        ),
        result_unit="m3",
        dependencies=("activity.qty", "activity.rate"),
        metadata={"future": {"preserve": True}, "source": "shared-core"},
    )


def test_postgres_formula_definition_round_trip_versions_isolation_and_conflict() -> None:
    current_scope = scope()
    first = record(current_scope, "1.0")
    second = record(current_scope, "2.0")
    with psycopg.connect(DSN) as connection:
        repository = PostgresP6FormulaDefinitionRepository(connection)
        repository.initialize()
        connection.commit()

        with PostgresTransactionManager(connection).transaction():
            repository.upsert(first)
            repository.upsert(second)

        assert repository.get(current_scope, first.formula_id, "1.0") == first
        assert repository.get(current_scope, first.formula_id, "2.0") == second
        assert repository.get(
            BackendScope(current_scope.tenant_id + "-other", current_scope.project_id, current_scope.project_revision),
            first.formula_id,
            "1.0",
        ) is None
        with pytest.raises(P6FormulaDefinitionPersistenceError, match="REVISION_CONFLICT"):
            repository.get(
                BackendScope(current_scope.tenant_id, current_scope.project_id, current_scope.project_revision + 1),
                first.formula_id,
                "1.0",
            )


def test_postgres_formula_definition_is_immutable() -> None:
    current_scope = scope()
    original = record(current_scope)
    changed = PersistedP6FormulaDefinition(
        **{**original.__dict__, "result_unit": "day"}
    )
    with psycopg.connect(DSN) as connection:
        repository = PostgresP6FormulaDefinitionRepository(connection)
        repository.initialize()
        connection.commit()
        with PostgresTransactionManager(connection).transaction():
            repository.upsert(original)
        with pytest.raises(P6FormulaDefinitionPersistenceError, match="IMMUTABLE_FORMULA_DEFINITION"):
            with PostgresTransactionManager(connection).transaction():
                repository.upsert(changed)


def test_postgres_formula_definition_rollback() -> None:
    current_scope = scope()
    original = record(current_scope)
    with psycopg.connect(DSN) as connection:
        repository = PostgresP6FormulaDefinitionRepository(connection)
        repository.initialize()
        connection.commit()
        with pytest.raises(RuntimeError, match="FORCED_ROLLBACK"):
            with PostgresTransactionManager(connection).transaction():
                repository.upsert(original)
                raise RuntimeError("FORCED_ROLLBACK")
        assert repository.get(current_scope, original.formula_id, original.version) is None

def test_postgres_formula_definition_concurrent_identical_upsert_is_idempotent() -> None:
    import threading
    from concurrent.futures import ThreadPoolExecutor

    current_scope = scope()
    original = record(current_scope)
    barrier = threading.Barrier(2)

    def save() -> PersistedP6FormulaDefinition:
        with psycopg.connect(DSN) as connection:
            repository = PostgresP6FormulaDefinitionRepository(connection)
            repository.initialize()
            connection.commit()
            barrier.wait(timeout=5)
            with PostgresTransactionManager(connection).transaction():
                return repository.upsert(original)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(save), pool.submit(save)]
        results = [future.result(timeout=10) for future in futures]

    assert results == [original, original]
