from __future__ import annotations

import sqlite3

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.client_sync.postgres_transaction import PostgresTransactionManager
from construction_pm.p6_formula_engine import FormulaType
from construction_pm.p6_formula_definition_repository import (
    FormulaDefinitionCreateRequest,
    P6FormulaDefinitionApplicationService,
    P6FormulaDefinitionPersistenceError,
    PersistedP6FormulaDefinition,
    SQLiteP6FormulaDefinitionRepository,
)


def scope(revision: int = 7) -> BackendScope:
    return BackendScope("tenant-formula", "project-formula", revision)


def record(version: str = "1.0", revision: int = 7) -> PersistedP6FormulaDefinition:
    return PersistedP6FormulaDefinition(
        scope=scope(revision),
        semantic_version="p6-formula.v1",
        semantic_reference="shared-core:p6-formula",
        definition=__import__("construction_pm.p6_formula_engine", fromlist=["FormulaDefinition"]).FormulaDefinition(
            "activity.total", version, "[activity.qty] * [activity.rate]", FormulaType.NUMBER
        ),
        result_unit="m3",
        dependencies=("activity.qty", "activity.rate"),
        metadata={"futureFlag": {"enabled": True}, "source": "shared-core"},
    )


def test_formula_definition_round_trip_versions_and_unknown_metadata() -> None:
    connection = sqlite3.connect(":memory:")
    repository = SQLiteP6FormulaDefinitionRepository(connection)
    first = record("1.0")
    second = record("2.0")
    repository.upsert(first)
    repository.upsert(second)

    assert repository.get(first.scope, first.formula_id, "1.0") == first
    assert repository.get(first.scope, first.formula_id, "2.0") == second
    assert tuple(item.version for item in repository.list_versions(first.scope, first.formula_id)) == ("1.0", "2.0")
    assert repository.get(first.scope, first.formula_id, "1.0").metadata["futureFlag"] == {"enabled": True}


def test_formula_definition_is_immutable_and_revision_scoped() -> None:
    connection = sqlite3.connect(":memory:")
    repository = SQLiteP6FormulaDefinitionRepository(connection)
    original = record()
    repository.upsert(original)
    changed = PersistedP6FormulaDefinition(
        **{**original.__dict__, "result_unit": "day"}
    )
    with pytest.raises(P6FormulaDefinitionPersistenceError, match="IMMUTABLE_FORMULA_DEFINITION"):
        repository.upsert(changed)
    with pytest.raises(P6FormulaDefinitionPersistenceError, match="REVISION_CONFLICT"):
        repository.get(scope(8), original.formula_id, original.version)


def test_formula_definition_application_service_owns_transaction() -> None:
    class TransactionManager:
        def __init__(self):
            self.entered = 0
        class Context:
            def __init__(self, outer): self.outer = outer
            def __enter__(self): self.outer.entered += 1
            def __exit__(self, *_): return False
        def transaction(self): return self.Context(self)

    connection = sqlite3.connect(":memory:")
    repository = SQLiteP6FormulaDefinitionRepository(connection)
    manager = TransactionManager()
    service = P6FormulaDefinitionApplicationService(repository, manager)
    request = FormulaDefinitionCreateRequest(
        scope=scope(),
        semantic_version="p6-formula.v1",
        semantic_reference="shared-core:p6-formula",
        formula_id="activity.total",
        version="1.0",
        expression="[activity.qty] * [activity.rate]",
        result_type=FormulaType.NUMBER,
        result_unit="m3",
        dependencies=("activity.qty", "activity.rate"),
        metadata={"unknown": "preserve"},
    )
    created = service.create(request)
    assert created.version == "1.0"
    assert manager.entered == 1
    assert service.read(scope(), "activity.total", "1.0").formula == created


def test_formula_definition_rollback() -> None:
    class TransactionManager:
        class Context:
            def __init__(self, connection): self.connection = connection
            def __enter__(self): return self
            def __exit__(self, exc_type, *_):
                if exc_type: self.connection.rollback()
                return False
        def __init__(self, connection): self.connection = connection
        def transaction(self): return self.Context(self.connection)

    connection = sqlite3.connect(":memory:")
    repository = SQLiteP6FormulaDefinitionRepository(connection)
    manager = TransactionManager(connection)
    service = P6FormulaDefinitionApplicationService(repository, manager)
    request = FormulaDefinitionCreateRequest(
        scope=scope(), semantic_version="p6-formula.v1", semantic_reference="shared-core:p6-formula",
        formula_id="activity.rollback", version="1.0", expression="[x]", result_type=FormulaType.NUMBER,
        result_unit=None, dependencies=("x",), metadata={"keep": True},
    )
    with pytest.raises(RuntimeError):
        with manager.transaction():
            repository.upsert(
                PersistedP6FormulaDefinition(
                    scope=scope(), semantic_version=request.semantic_version,
                    semantic_reference=request.semantic_reference,
                    definition=__import__("construction_pm.p6_formula_engine", fromlist=["FormulaDefinition"]).FormulaDefinition(
                        request.formula_id, request.version, request.expression, request.result_type
                    ),
                    result_unit=request.result_unit, dependencies=request.dependencies, metadata=request.metadata
                )
            )
            raise RuntimeError("FORCED_ROLLBACK")
    assert repository.get(scope(), "activity.rollback", "1.0") is None
