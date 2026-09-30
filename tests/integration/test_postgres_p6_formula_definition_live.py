from __future__ import annotations

import os

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_formula_definition_repository import (
    P6FormulaDefinitionPersistenceError,
    PersistedP6FormulaDefinition,
    PostgresP6FormulaDefinitionRepository,
)
from construction_pm.p6_formula_engine import FormulaDefinition, FormulaType

pytestmark = pytest.mark.skipif(
    not os.getenv("CONSTRUCTION_PM_POSTGRES_DSN"),
    reason="CONSTRUCTION_PM_POSTGRES_DSN is not configured",
)


def connect():
    import psycopg

    return psycopg.connect(os.environ["CONSTRUCTION_PM_POSTGRES_DSN"])


def record(scope: BackendScope, version: str = "1.0") -> PersistedP6FormulaDefinition:
    return PersistedP6FormulaDefinition(
        scope=scope,
        semantic_version="p6-formula.v1",
        semantic_reference="shared-core:p6-formula",
        definition=FormulaDefinition(
            "activity.total",
            version,
            "[activity.qty] * [activity.rate]",
            FormulaType.NUMBER,
        ),
        result_unit="m3",
        dependencies=("activity.qty", "activity.rate"),
        metadata={"futureFlag": {"enabled": True}, "source": "shared-core"},
    )


def test_postgres_formula_definition_round_trip_versions_isolation_and_revision():
    with connect() as conn:
        repo = PostgresP6FormulaDefinitionRepository(conn)
        repo.initialize()
        scope = BackendScope("tenant-formula-pg", "project-formula-pg", 7)
        first = record(scope, "1.0")
        second = record(scope, "2.0")

        assert repo.upsert(first) == first
        assert repo.upsert(second) == second
        assert repo.get(scope, first.formula_id, "1.0") == first
        assert repo.get(scope, first.formula_id, "2.0") == second
        assert tuple(item.version for item in repo.list_versions(scope, first.formula_id)) == ("1.0", "2.0")
        assert repo.get(
            BackendScope("other-tenant", scope.project_id, scope.project_revision),
            first.formula_id,
            "1.0",
        ) is None
        with pytest.raises(P6FormulaDefinitionPersistenceError, match="REVISION_CONFLICT"):
            repo.get(
                BackendScope(scope.tenant_id, scope.project_id, scope.project_revision + 1),
                first.formula_id,
                "1.0",
            )


def test_postgres_formula_definition_is_immutable_and_preserves_committed_row():
    with connect() as conn:
        repo = PostgresP6FormulaDefinitionRepository(conn)
        repo.initialize()
        scope = BackendScope("tenant-formula-rb", "project-formula-rb", 3)
        original = record(scope)
        repo.upsert(original)
        conn.commit()

        changed = PersistedP6FormulaDefinition(
            scope=scope,
            semantic_version=original.semantic_version,
            semantic_reference=original.semantic_reference,
            definition=original.definition,
            result_unit="day",
            dependencies=original.dependencies,
            metadata=original.metadata,
        )
        with pytest.raises(P6FormulaDefinitionPersistenceError, match="IMMUTABLE_FORMULA_DEFINITION"):
            repo.upsert(changed)
        conn.rollback()

        assert repo.get(scope, original.formula_id, original.version) == original


def test_postgres_formula_definition_conflicting_insert_does_not_replace_existing_row():
    with connect() as conn:
        repo = PostgresP6FormulaDefinitionRepository(conn)
        repo.initialize()
        scope = BackendScope("tenant-formula-conflict", "project-formula-conflict", 4)
        original = record(scope)
        repo.upsert(original)
        conn.commit()

        conflicting = PersistedP6FormulaDefinition(
            scope=scope,
            semantic_version=original.semantic_version,
            semantic_reference=original.semantic_reference,
            definition=original.definition,
            result_unit="day",
            dependencies=original.dependencies,
            metadata=original.metadata,
        )
        with pytest.raises(P6FormulaDefinitionPersistenceError, match="IMMUTABLE_FORMULA_DEFINITION"):
            repo.upsert(conflicting)
        conn.rollback()

        assert repo.get(scope, original.formula_id, original.version) == original
