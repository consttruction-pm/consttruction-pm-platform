from datetime import datetime, timezone
import os
import uuid

import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
if not DSN:
    pytest.skip("CONSTRUCTION_PM_POSTGRES_DSN is not configured", allow_module_level=True)

from construction_pm.client_sync.postgres_transaction import PostgresTransactionManager
from construction_pm.backend_p0.models import BackendScope
from construction_pm.field_assurance_templates import FieldAssuranceTemplate, FieldAssuranceTemplateInputType, FieldAssuranceTemplateItem, FieldAssuranceTemplateType
from construction_pm.field_assurance_templates_repository import FieldAssuranceExecution, PostgresFieldAssuranceTemplateRepository

def template(suffix):
    return FieldAssuranceTemplate(f"TPL-{suffix}", BackendScope("tenant-live", f"project-{suffix}", 4), 1, FieldAssuranceTemplateType.INSPECTION, "inspection.concrete", (FieldAssuranceTemplateItem("I-1", 1, "criterion.dimension", FieldAssuranceTemplateInputType.NUMBER, True),))

def execution(t, execution_id, value="12.5"):
    return FieldAssuranceExecution(execution_id, t.template_id, t.template_version, t.scope, (("I-1", value),), "user-live", datetime(2026, 9, 28, 8, 0, tzinfo=timezone.utc))

def test_postgres_field_assurance_template_execution_replay_and_conflict():
    suffix = uuid.uuid4().hex
    t = template(suffix)
    with psycopg.connect(DSN) as connection:
        repository = PostgresFieldAssuranceTemplateRepository(connection)
        repository.initialize()
        connection.commit()
        with PostgresTransactionManager(connection).transaction():
            repository.create_template(t)
            first = repository.create_execution(execution(t, f"EXEC-{suffix}"))
        with PostgresTransactionManager(connection).transaction():
            replay = repository.create_execution(execution(t, f"EXEC-{suffix}"))
        assert replay.as_dict() == first.as_dict()
        with pytest.raises(ValueError, match="EXECUTION_ID_CONFLICT"):
            with PostgresTransactionManager(connection).transaction():
                repository.create_execution(execution(t, f"EXEC-{suffix}", "99"))
        connection.rollback()

def test_postgres_field_assurance_template_execution_rolls_back():
    suffix = uuid.uuid4().hex
    t = template(suffix)
    with psycopg.connect(DSN) as connection:
        repository = PostgresFieldAssuranceTemplateRepository(connection)
        repository.initialize()
        connection.commit()
        with pytest.raises(RuntimeError, match="FORCED_ROLLBACK"):
            with PostgresTransactionManager(connection).transaction():
                repository.create_template(t)
                repository.create_execution(execution(t, f"EXEC-{suffix}"))
                raise RuntimeError("FORCED_ROLLBACK")
        assert repository.get_template(t.scope, t.template_id, t.template_version) is None
        assert repository.get_execution(t.scope, f"EXEC-{suffix}") is None
