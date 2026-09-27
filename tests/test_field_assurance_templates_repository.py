from datetime import datetime, timezone
import sqlite3

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.field_assurance_templates import (
    FieldAssuranceTemplate,
    FieldAssuranceTemplateInputType,
    FieldAssuranceTemplateItem,
    FieldAssuranceTemplateType,
)
from construction_pm.field_assurance_templates_repository import (
    FieldAssuranceExecution,
    FieldAssuranceTemplateApplicationService,
    FieldAssuranceTemplatePersistenceError,
    SQLiteFieldAssuranceTemplateRepository,
)


def _scope(revision: int = 4) -> BackendScope:
    return BackendScope("tenant-1", "project-1", revision)


def _template(revision: int = 4, version: int = 2) -> FieldAssuranceTemplate:
    return FieldAssuranceTemplate(
        "TPL-1", _scope(revision), version, FieldAssuranceTemplateType.INSPECTION, "inspection.concrete",
        (
            FieldAssuranceTemplateItem("I-1", 1, "criterion.dimension", FieldAssuranceTemplateInputType.NUMBER, True),
            FieldAssuranceTemplateItem("I-2", 2, "criterion.finish", FieldAssuranceTemplateInputType.SELECT, True, ("pass", "fail")),
            FieldAssuranceTemplateItem("I-3", 3, "criterion.note", FieldAssuranceTemplateInputType.TEXT, False),
        ),
    )


def _service():
    connection = sqlite3.connect(":memory:")
    repository = SQLiteFieldAssuranceTemplateRepository(connection)
    service = FieldAssuranceTemplateApplicationService(repository, SQLiteTransactionManager(connection))
    return connection, service


def _execution(scope: BackendScope = _scope()) -> FieldAssuranceExecution:
    return FieldAssuranceExecution(
        "EXEC-1", "TPL-1", 2, scope, (("I-1", "12.5"), ("I-2", "pass")),
        "user-1", datetime(2026, 9, 28, 8, 0, tzinfo=timezone.utc),
    )


def test_create_read_preserves_version_and_scope():
    connection, service = _service()
    try:
        service.create_template(_template())
        value = service.read_template(_scope(), "TPL-1", 2)
        assert value is not None
        assert value.template_version == 2
        assert value.scope == _scope()
        assert [item.item_id for item in value.items] == ["I-1", "I-2", "I-3"]
    finally:
        connection.close()


def test_historical_versions_are_immutable():
    connection, service = _service()
    try:
        service.create_template(_template(version=1))
        service.create_template(_template(version=2))
        with pytest.raises(FieldAssuranceTemplatePersistenceError, match="IMMUTABLE_TEMPLATE_VERSION"):
            service.create_template(_template(version=2, revision=5))
        assert service.read_template(_scope(), "TPL-1", 1).template_version == 1
    finally:
        connection.close()


def test_execution_requires_exact_template_version_and_required_answers():
    connection, service = _service()
    try:
        service.create_template(_template())
        with pytest.raises(FieldAssuranceTemplatePersistenceError, match="MISSING_REQUIRED_ANSWER"):
            service.execute(FieldAssuranceExecution(
                "EXEC-MISSING", "TPL-1", 2, _scope(), (("I-2", "pass"),),
                "user-1", datetime.now(timezone.utc),
            ))
        with pytest.raises(FieldAssuranceTemplatePersistenceError, match="TEMPLATE_VERSION_MISMATCH"):
            service.execute(FieldAssuranceExecution(
                "EXEC-OLD", "TPL-1", 1, _scope(), (("I-1", "12.5"), ("I-2", "pass")),
                "user-1", datetime.now(timezone.utc),
            ))
    finally:
        connection.close()


def test_execution_rejects_scope_mismatch():
    connection, service = _service()
    try:
        service.create_template(_template())
        with pytest.raises(FieldAssuranceTemplatePersistenceError, match="TEMPLATE_SCOPE_MISMATCH"):
            service.execute(_execution(_scope(5)))
        with pytest.raises(FieldAssuranceTemplatePersistenceError, match="TEMPLATE_NOT_FOUND"):
            service.execute(FieldAssuranceExecution(
                "EXEC-TENANT", "TPL-1", 2, BackendScope("tenant-2", "project-1", 4),
                (("I-1", "12.5"), ("I-2", "pass")), "user-1", datetime.now(timezone.utc),
            ))
    finally:
        connection.close()


def test_execution_is_idempotent_and_conflicts_are_rejected():
    connection, service = _service()
    try:
        service.create_template(_template())
        first = service.execute(_execution())
        replay = service.execute(_execution())
        assert replay.as_dict() == first.as_dict()
        with pytest.raises(FieldAssuranceTemplatePersistenceError, match="EXECUTION_ID_CONFLICT"):
            service.execute(FieldAssuranceExecution(
                "EXEC-1", "TPL-1", 2, _scope(), (("I-1", "99"), ("I-2", "pass")),
                "user-1", datetime.now(timezone.utc),
            ))
    finally:
        connection.close()


def test_execution_rollback_leaves_no_partial_row():
    connection, service = _service()
    try:
        service.create_template(_template())
        bad = FieldAssuranceExecution(
            "EXEC-ROLLBACK", "TPL-1", 2, _scope(), (("I-1", "12.5"),),
            "user-1", datetime.now(timezone.utc),
        )
        with pytest.raises(FieldAssuranceTemplatePersistenceError):
            service.execute(bad)
        assert service.repository.get_execution(_scope(), "EXEC-ROLLBACK") is None
    finally:
        connection.close()
