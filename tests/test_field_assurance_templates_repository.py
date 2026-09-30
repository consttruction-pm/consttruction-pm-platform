from datetime import datetime, timezone
import sqlite3

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    Permission,
    RoleBasedAuthorizationPolicy,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.field_assurance_application import FieldAssuranceApplicationService
from construction_pm.field_assurance_execution import FieldAssuranceExecution, FieldAssuranceExecutionAnswer
from construction_pm.field_assurance_templates import (
    FieldAssuranceTemplate,
    FieldAssuranceTemplateInputType,
    FieldAssuranceTemplateItem,
    FieldAssuranceTemplateType,
)
from construction_pm.field_assurance_templates_repository import (
    FieldAssuranceTemplatePersistenceError,
    SQLiteFieldAssuranceTemplateRepository,
)


def _scope(revision: int = 4, tenant: str = "tenant-1", project: str = "project-1") -> BackendScope:
    return BackendScope(tenant, project, revision)


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
    policy = RoleBasedAuthorizationPolicy(
        {"planner": frozenset({Permission.PROJECT_READ, Permission.PROJECT_WRITE})}
    )
    service = FieldAssuranceApplicationService(
        repository=repository,
        authorization_policy=policy,
        transaction_manager=SQLiteTransactionManager(connection),
    )
    context = AuthorizationContext(
        "tenant-1", "project-1", "user-1", frozenset({"planner"})
    )
    return connection, repository, service, context


def _execution(scope: BackendScope = _scope()) -> FieldAssuranceExecution:
    return FieldAssuranceExecution(
        "EXEC-1", scope, "TPL-1", 2,
        (
            FieldAssuranceExecutionAnswer("I-1", 12.5),
            FieldAssuranceExecutionAnswer("I-2", "pass"),
        ),
        "user-1",
        datetime(2026, 9, 28, 8, 0, tzinfo=timezone.utc),
    )


def test_canonical_application_service_uses_production_sqlite_repository():
    connection, repository, service, context = _service()
    try:
        saved_template = service.create_template(
            _template(),
            context=context,
            expected_project_revision=4,
            actor_id="user-1",
        )
        saved_execution = service.execute(
            _execution(),
            context=context,
            expected_project_revision=4,
            actor_id="user-1",
        )
        assert saved_template == repository.get_template(_scope(), "TPL-1", 2)
        assert saved_execution == repository.get_execution(_scope(), "EXEC-1")
    finally:
        connection.close()


def test_create_read_preserves_version_and_scope():
    connection, _, service, context = _service()
    try:
        service.create_template(
            _template(),
            context=context,
            expected_project_revision=4,
            actor_id="user-1",
        )
        value = service.get_template(
            context=context,
            template_id="TPL-1",
            template_version=2,
            project_revision=4,
        )
        assert value is not None
        assert value.template_version == 2
        assert value.scope == _scope()
        assert [item.item_id for item in value.items] == ["I-1", "I-2", "I-3"]
    finally:
        connection.close()


def test_historical_versions_are_immutable():
    connection, _, service, context = _service()
    try:
        service.create_template(
            _template(version=1),
            context=context,
            expected_project_revision=4,
            actor_id="user-1",
        )
        service.create_template(
            _template(version=2),
            context=context,
            expected_project_revision=4,
            actor_id="user-1",
        )
        with pytest.raises(FieldAssuranceTemplatePersistenceError, match="IMMUTABLE_TEMPLATE_VERSION"):
            service.create_template(
                _template(version=2, revision=5),
                context=context,
                expected_project_revision=5,
                actor_id="user-1",
            )
        value = service.get_template(
            context=context,
            template_id="TPL-1",
            template_version=1,
            project_revision=4,
        )
        assert value is not None
        assert value.template_version == 1
    finally:
        connection.close()


def test_repository_execute_implements_field_assurance_contract():
    connection, repository, _, _ = _service()
    try:
        repository.create_template(_template())
        saved = repository.execute(_execution())
        assert saved == _execution()
        assert repository.get_execution(_scope(), "EXEC-1") == saved
    finally:
        connection.close()


def test_execution_requires_exact_template_version_and_required_answers():
    connection, _, service, context = _service()
    try:
        service.create_template(
            _template(),
            context=context,
            expected_project_revision=4,
            actor_id="user-1",
        )
        with pytest.raises(FieldAssuranceTemplatePersistenceError, match="MISSING_REQUIRED_EXECUTION_ANSWERS"):
            service.execute(
                FieldAssuranceExecution(
                    "EXEC-MISSING", _scope(), "TPL-1", 2,
                    (FieldAssuranceExecutionAnswer("I-2", "pass"),),
                    "user-1", datetime.now(timezone.utc),
                ),
                context=context,
                expected_project_revision=4,
                actor_id="user-1",
            )
        with pytest.raises(FieldAssuranceTemplatePersistenceError, match="TEMPLATE_VERSION_MISMATCH"):
            service.execute(
                FieldAssuranceExecution(
                    "EXEC-OLD", _scope(), "TPL-1", 1,
                    (
                        FieldAssuranceExecutionAnswer("I-1", 12.5),
                        FieldAssuranceExecutionAnswer("I-2", "pass"),
                    ),
                    "user-1", datetime.now(timezone.utc),
                ),
                context=context,
                expected_project_revision=4,
                actor_id="user-1",
            )
    finally:
        connection.close()


def test_execution_rejects_scope_mismatch():
    connection, _, service, context = _service()
    try:
        service.create_template(
            _template(),
            context=context,
            expected_project_revision=4,
            actor_id="user-1",
        )
        with pytest.raises(FieldAssuranceTemplatePersistenceError, match="EXECUTION_SCOPE_MISMATCH"):
            service.execute(
                _execution(_scope(5)),
                context=context,
                expected_project_revision=5,
                actor_id="user-1",
            )
        with pytest.raises(FieldAssuranceTemplatePersistenceError, match="TEMPLATE_NOT_FOUND"):
            service.execute(
                FieldAssuranceExecution(
                    "EXEC-TENANT", _scope(4, "tenant-2"), "TPL-1", 2,
                    (
                        FieldAssuranceExecutionAnswer("I-1", 12.5),
                        FieldAssuranceExecutionAnswer("I-2", "pass"),
                    ),
                    "user-1", datetime.now(timezone.utc),
                ),
                context=context,
                expected_project_revision=4,
                actor_id="user-1",
            )
    finally:
        connection.close()


def test_execution_is_idempotent_and_conflicts_are_rejected():
    connection, _, service, context = _service()
    try:
        service.create_template(
            _template(),
            context=context,
            expected_project_revision=4,
            actor_id="user-1",
        )
        first = service.execute(
            _execution(),
            context=context,
            expected_project_revision=4,
            actor_id="user-1",
        )
        replay = service.execute(
            _execution(),
            context=context,
            expected_project_revision=4,
            actor_id="user-1",
        )
        assert replay.as_dict() == first.as_dict()
        with pytest.raises(FieldAssuranceTemplatePersistenceError, match="EXECUTION_ID_CONFLICT"):
            service.execute(
                FieldAssuranceExecution(
                    "EXEC-1", _scope(), "TPL-1", 2,
                    (
                        FieldAssuranceExecutionAnswer("I-1", 99),
                        FieldAssuranceExecutionAnswer("I-2", "pass"),
                    ),
                    "user-1", datetime.now(timezone.utc),
                ),
                context=context,
                expected_project_revision=4,
                actor_id="user-1",
            )
    finally:
        connection.close()


def test_execution_rollback_leaves_no_partial_row():
    connection, repository, service, context = _service()
    try:
        service.create_template(
            _template(),
            context=context,
            expected_project_revision=4,
            actor_id="user-1",
        )
        bad = FieldAssuranceExecution(
            "EXEC-ROLLBACK", _scope(), "TPL-1", 2,
            (FieldAssuranceExecutionAnswer("I-1", "12.5"),),
            "user-1", datetime.now(timezone.utc),
        )
        with pytest.raises(FieldAssuranceTemplatePersistenceError):
            service.execute(
                bad,
                context=context,
                expected_project_revision=4,
                actor_id="user-1",
            )
        assert repository.get_execution(_scope(), "EXEC-ROLLBACK") is None
    finally:
        connection.close()


def test_postgres_repository_round_trip_is_exported():
    from construction_pm.field_assurance_templates_repository import PostgresFieldAssuranceTemplateRepository
    assert PostgresFieldAssuranceTemplateRepository is not None
