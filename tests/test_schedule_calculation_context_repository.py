from __future__ import annotations

from datetime import datetime, timezone
import sqlite3

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.schedule_calculation_context_repository import (
    CalculationContextPersistenceError,
    PersistedCalculationContext,
    SQLiteCalculationContextRepository,
    build_persisted_context,
)
from construction_pm.scheduling.calculation_context import CalculationContext


def make_context(snapshot_id: str = "S-1") -> CalculationContext:
    return CalculationContext(
        project_id="P-1",
        project_version=7,
        calendar_id="CAL-1",
        calendar_version="3",
        rules_version="rules-9",
        engine_version="engine-4",
        timezone="Asia/Baku",
        calculation_timestamp="2026-10-08T12:00:00+04:00",
        input_snapshot_id=snapshot_id,
        tenant_id="T-1",
        actor_id="actor-1",
        request_id="request-1",
        idempotency_key="idem-1",
    )


def scope() -> BackendScope:
    return BackendScope("T-1", "P-1", 7)


def test_context_round_trip_preserves_all_authoritative_fields():
    connection = sqlite3.connect(":memory:")
    repo = SQLiteCalculationContextRepository(connection)
    record = build_persisted_context(scope(), make_context())

    assert repo.save(record) == record
    loaded = repo.get(scope(), "S-1")
    assert loaded == record
    assert loaded is not None
    assert loaded.context.to_dict() == record.context.to_dict()
    assert loaded.context.sha256() == loaded.context_sha256
    assert loaded.context.calculation_identity == loaded.calculation_identity


def test_context_save_is_immutable_and_idempotent_for_same_content():
    repo = SQLiteCalculationContextRepository(sqlite3.connect(":memory:"))
    first = build_persisted_context(scope(), make_context())

    assert repo.save(first) == first
    assert repo.save(first) == first


def test_context_save_rejects_immutable_conflict():
    repo = SQLiteCalculationContextRepository(sqlite3.connect(":memory:"))
    first = build_persisted_context(scope(), make_context())
    changed = build_persisted_context(
        scope(),
        CalculationContext(
            **{
                **make_context().to_dict(),
                "actor_id": "actor-2",
            }
        ),
    )

    repo.save(first)
    with pytest.raises(CalculationContextPersistenceError, match="CONTEXT_IMMUTABLE_CONFLICT"):
        repo.save(changed)


def test_context_get_rejects_scope_revision_mismatch():
    repo = SQLiteCalculationContextRepository(sqlite3.connect(":memory:"))
    repo.save(build_persisted_context(scope(), make_context()))

    with pytest.raises(CalculationContextPersistenceError, match="REVISION_CONFLICT"):
        repo.get(BackendScope("T-1", "P-1", 8), "S-1")


def test_context_get_rejects_identity_mismatch_against_snapshot():
    repo = SQLiteCalculationContextRepository(sqlite3.connect(":memory:"))
    repo.save(build_persisted_context(scope(), make_context()))

    with pytest.raises(CalculationContextPersistenceError, match="CALCULATION_IDENTITY_MISMATCH"):
        repo.get(scope(), "S-1", expected_calculation_identity="0" * 64)


def test_context_get_rejects_tampered_context_hash():
    connection = sqlite3.connect(":memory:")
    repo = SQLiteCalculationContextRepository(connection)
    repo.save(build_persisted_context(scope(), make_context()))
    connection.execute(
        "UPDATE schedule_calculation_context SET context_sha256=? WHERE snapshot_id=?",
        ("0" * 64, "S-1"),
    )
    connection.commit()

    with pytest.raises(CalculationContextPersistenceError, match="CONTEXT_SHA256_MISMATCH"):
        repo.get(scope(), "S-1")


def test_context_resolution_is_deterministic_for_replay():
    repo = SQLiteCalculationContextRepository(sqlite3.connect(":memory:"))
    context = make_context()
    repo.save(build_persisted_context(scope(), context))

    first = repo.get(scope(), "S-1")
    second = repo.get(scope(), "S-1")
    assert first == second
    assert first is not None
    assert first.context.calculation_identity == context.calculation_identity
    assert first.context.sha256() == second.context.sha256()


def test_persisted_context_validation_requires_matching_snapshot_id():
    record = build_persisted_context(scope(), make_context())
    invalid = PersistedCalculationContext(
        **{
            **record.__dict__,
            "snapshot_id": "S-OTHER",
        }
    )
    with pytest.raises(CalculationContextPersistenceError, match="SNAPSHOT_CONTEXT_ID_MISMATCH"):
        invalid.validate()


@pytest.fixture(scope="module")
def postgres_dsn():
    import os

    dsn = os.getenv("P6_TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("P6_TEST_POSTGRES_DSN is not configured")
    return dsn


def test_postgres_context_round_trip(postgres_dsn):
    psycopg = pytest.importorskip("psycopg")
    connection = psycopg.connect(postgres_dsn)
    from construction_pm.schedule_calculation_context_repository import PostgresCalculationContextRepository

    repo = PostgresCalculationContextRepository(connection)
    repo.initialize()
    connection.commit()
    try:
        connection.execute("TRUNCATE TABLE schedule_calculation_context")
        connection.commit()
        record = build_persisted_context(scope(), make_context())
        with connection.transaction():
            assert repo.save(record) == record
        loaded = repo.get(scope(), "S-1", expected_calculation_identity=record.calculation_identity)
        assert loaded == record
    finally:
        connection.rollback()
        connection.execute("TRUNCATE TABLE schedule_calculation_context")
        connection.commit()
        connection.close()
