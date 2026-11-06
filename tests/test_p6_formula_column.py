from __future__ import annotations

import sqlite3

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    default_project_policy,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.p6_field_registry import P6FieldType, get_field
from construction_pm.p6_field_registry_api import P6FieldRegistryAPI, P6_FIELD_REGISTRY_API_VERSION
from construction_pm.p6_field_registry_repository import (
    P6FieldRegistryApplicationService,
    PersistedP6Field,
    SQLiteP6FieldRegistryRepository,
)
from construction_pm.p6_formula_authority_api import P6FormulaAuthorityAPI
from construction_pm.p6_formula_column import (
    P6_FORMULA_COLUMN_API_VERSION,
    P6FormulaColumnAPI,
    P6FormulaColumnError,
    P6FormulaColumnService,
    formula_column_dto,
    normalize_formula_column_id,
)
from construction_pm.p6_formula_definition_repository import (
    P6FormulaDefinitionApplicationService,
    SQLiteP6FormulaDefinitionRepository,
)
from construction_pm.p6_formula_engine import FormulaType
from construction_pm.p6_user_defined_fields_repository import (
    P6UserDefinedFieldApplicationService,
    SQLiteP6UserDefinedFieldRepository,
)


SCOPE = BackendScope("tenant-a", "project-a", 3)


def _auth(role: str, tenant: str = "tenant-a", project: str = "project-a") -> AuthorizationContext:
    return AuthorizationContext(tenant, project, "user-a", frozenset({role}))


def _services(connection: sqlite3.Connection):
    transaction_manager = SQLiteTransactionManager(connection)
    field_service = P6FieldRegistryApplicationService(
        SQLiteP6FieldRegistryRepository(connection), transaction_manager
    )
    for field_id in (
        "activity.activity_id",
        "activity.activity_name",
        "activity.percent_complete",
    ):
        field_service.save_field(
            PersistedP6Field(SCOPE, "p6-field-registry.v1", get_field(field_id))
        )
    definition_service = P6FormulaDefinitionApplicationService(
        SQLiteP6FormulaDefinitionRepository(connection), transaction_manager
    )
    return field_service, definition_service


def _column_service(connection: sqlite3.Connection) -> P6FormulaColumnService:
    field_service, definition_service = _services(connection)
    return P6FormulaColumnService(field_service, definition_service)


def test_formula_column_persists_a_versioned_definition() -> None:
    connection = sqlite3.connect(":memory:")
    service = _column_service(connection)

    record = service.create(
        SCOPE,
        formula_id="formula.double_progress",
        title="Double Progress",
        expression="[activity.percent_complete] * 2",
    )

    assert record.formula_id == "formula.double_progress"
    assert record.version == "1"
    assert record.semantic_version == "cubi-formula-column.v1"
    assert record.semantic_reference == "shared-core:p6-formula-column"
    assert record.definition.result_type is FormulaType.NUMBER
    assert record.dependencies == ("activity.percent_complete",)
    assert record.metadata == {
        "subject_area": "Activity",
        "title": "Double Progress",
        "source": "cubi-formula-column",
    }

    listed = service.list(SCOPE)
    assert [item.formula_id for item in listed] == ["formula.double_progress"]
    # list_all is revision scoped and never leaks another revision.
    assert service.list(BackendScope("tenant-a", "project-a", 4)) == ()

    dto = formula_column_dto(record)
    assert dto["contract_version"] == P6_FORMULA_COLUMN_API_VERSION
    assert dto["formula"] == {
        "formula_id": "formula.double_progress",
        "version": "1",
        "title": "Double Progress",
        "expression": "[activity.percent_complete] * 2",
        "result_type": "number",
        "data_type": "double",
        "result_unit": None,
        "dependencies": ["activity.percent_complete"],
    }


def test_formula_column_create_is_idempotent_for_identical_definition() -> None:
    connection = sqlite3.connect(":memory:")
    service = _column_service(connection)

    first = service.create(
        SCOPE,
        formula_id="formula.total",
        title="Total",
        expression="[activity.percent_complete] + 1",
    )
    second = service.create(
        SCOPE,
        formula_id="formula.total",
        title="Total",
        expression="[activity.percent_complete] + 1",
    )

    assert first == second
    assert len(service.list(SCOPE)) == 1


def test_formula_column_rejects_invalid_ids_and_conflicting_redefinitions() -> None:
    connection = sqlite3.connect(":memory:")
    service = _column_service(connection)

    with pytest.raises(P6FormulaColumnError, match="INVALID_FORMULA_COLUMN_ID"):
        normalize_formula_column_id("total")
    with pytest.raises(P6FormulaColumnError, match="INVALID_FORMULA_COLUMN_ID"):
        normalize_formula_column_id("formula.")
    with pytest.raises(P6FormulaColumnError, match="INVALID_FORMULA_COLUMN_ID"):
        normalize_formula_column_id("formula.has space")

    with pytest.raises(P6FormulaColumnError, match="FORMULA_COLUMN_TITLE_REQUIRED"):
        service.create(SCOPE, formula_id="formula.total", title="  ", expression="1")
    with pytest.raises(P6FormulaColumnError, match="FORMULA_COLUMN_EXPRESSION_REQUIRED"):
        service.create(SCOPE, formula_id="formula.total", title="Total", expression=" ")

    service.create(SCOPE, formula_id="formula.total", title="Total", expression="1 + 1")
    with pytest.raises(P6FormulaColumnError, match="FORMULA_COLUMN_ALREADY_EXISTS"):
        service.create(SCOPE, formula_id="formula.total", title="Total", expression="2 + 2")


def test_formula_column_rejects_unknown_fields_and_self_reference() -> None:
    connection = sqlite3.connect(":memory:")
    service = _column_service(connection)

    with pytest.raises(P6FormulaColumnError, match="FIELD_NOT_FOUND"):
        service.create(
            SCOPE,
            formula_id="formula.total",
            title="Total",
            expression="[missing.field] + 1",
        )

    # A formula definition cannot be available while it is being compiled, so
    # self reference fails closed instead of storing a cyclic definition.
    with pytest.raises(P6FormulaColumnError):
        service.create(
            SCOPE,
            formula_id="formula.total",
            title="Total",
            expression="[formula.total] + 1",
        )

    assert service.list(SCOPE) == ()


def test_formula_column_evaluates_real_cells_in_dependency_order() -> None:
    connection = sqlite3.connect(":memory:")
    service = _column_service(connection)
    service.create(
        SCOPE,
        formula_id="formula.double_progress",
        title="Double Progress",
        expression="[activity.percent_complete] * 2",
    )
    service.create(
        SCOPE,
        formula_id="formula.progress_bonus",
        title="Progress Bonus",
        expression="[formula.double_progress] + 5",
    )

    result = service.evaluate(
        SCOPE,
        {
            "A-1": {"activity.activity_id": "A-1", "activity.percent_complete": 25},
            "A-2": {"activity.activity_id": "A-2", "activity.percent_complete": "12.5"},
            "A-3": {"activity.activity_id": "A-3"},
        },
        ("formula.double_progress", "formula.progress_bonus"),
    )

    assert result["A-1"] == {
        "formula.double_progress": "50",
        "formula.progress_bonus": "55",
    }
    assert result["A-2"] == {
        "formula.double_progress": "25.0",
        "formula.progress_bonus": "30.0",
    }
    # A missing source cell produces an empty cell, never an invented value.
    assert result["A-3"] == {
        "formula.double_progress": None,
        "formula.progress_bonus": None,
    }


def test_formula_column_evaluation_is_blank_when_a_formula_is_not_persisted() -> None:
    connection = sqlite3.connect(":memory:")
    service = _column_service(connection)

    assert service.evaluate(SCOPE, {"A-1": {}}, ("formula.missing",)) == {}


def test_formula_column_api_enforces_scope_and_permissions() -> None:
    connection = sqlite3.connect(":memory:")
    service = _column_service(connection)
    api = P6FormulaColumnAPI(service, default_project_policy())

    created = api.create(
        SCOPE,
        formula_id="formula.total",
        title="Total",
        expression="[activity.percent_complete] * 2",
        auth_context=_auth("planner"),
    )
    assert created["formula"]["formula_id"] == "formula.total"

    listed = api.list(SCOPE, auth_context=_auth("viewer"))
    assert [item["formula"]["formula_id"] for item in listed] == ["formula.total"]

    with pytest.raises(AuthorizationError, match="authorization denied"):
        api.create(
            SCOPE,
            formula_id="formula.other",
            title="Other",
            expression="1",
            auth_context=_auth("viewer"),
        )

    with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
        api.list(BackendScope("tenant-b", "project-a", 3), auth_context=_auth("viewer"))


def test_field_registry_projects_formula_columns_as_computed_activity_fields() -> None:
    connection = sqlite3.connect(":memory:")
    field_service, definition_service = _services(connection)
    column_service = P6FormulaColumnService(field_service, definition_service)
    column_service.create(
        SCOPE,
        formula_id="formula.double_progress",
        title="Double Progress",
        expression="[activity.percent_complete] * 2",
    )
    api = P6FieldRegistryAPI(
        field_service,
        P6UserDefinedFieldApplicationService(
            SQLiteP6UserDefinedFieldRepository(connection), SQLiteTransactionManager(connection)
        ),
        default_project_policy(),
        column_service,
    )

    result = api.list_fields(
        SCOPE, "p6-field-registry.v1", "Activity", auth_context=_auth("viewer")
    )
    assert result
    assert all(item["contract_version"] == P6_FIELD_REGISTRY_API_VERSION for item in result)
    by_id = {item["field"]["field_id"]: item["field"] for item in result}
    assert by_id["formula.double_progress"]["computed"] is True
    assert by_id["formula.double_progress"]["writable"] is False
    assert by_id["formula.double_progress"]["read_only"] is True
    assert by_id["formula.double_progress"]["data_type"] == "double"
    assert by_id["formula.double_progress"]["display_name"] == "Double Progress"
    assert by_id["formula.double_progress"]["formula"] == "[activity.percent_complete] * 2"
    assert by_id["formula.double_progress"]["disposition"] == "implemented"

    # Formula columns are Activity-only; other subject areas stay untouched.
    non_activity = api.list_fields(
        SCOPE, "p6-field-registry.v1", "Resource", auth_context=_auth("viewer")
    )
    assert "formula.double_progress" not in {
        item["field"]["field_id"] for item in non_activity
    }


def test_formula_authority_validates_against_formula_columns() -> None:
    connection = sqlite3.connect(":memory:")
    field_service, definition_service = _services(connection)
    column_service = P6FormulaColumnService(field_service, definition_service)
    column_service.create(
        SCOPE,
        formula_id="formula.double_progress",
        title="Double Progress",
        expression="[activity.percent_complete] * 2",
    )
    api = P6FormulaAuthorityAPI(field_service, default_project_policy(), column_service)
    auth = _auth("viewer")

    result = api.validate(
        SCOPE,
        "p6-field-registry.v1",
        "[formula.double_progress] + 1",
        auth_context=auth,
    )
    assert result["validation"]["valid"] is True
    assert result["dependencies"]["field_ids"] == ["formula.double_progress"]
    assert result["result_type"] == {"data_type": "double"}

    # The stored formula column is itself valid to validate.
    stored = api.validate(
        SCOPE,
        "p6-field-registry.v1",
        "[activity.percent_complete] * 2",
        auth_context=auth,
    )
    assert stored["validation"]["valid"] is True

    # Computed fields stay readable but not writable through the registry.
    field_api = P6FieldRegistryAPI(
        field_service,
        P6UserDefinedFieldApplicationService(
            SQLiteP6UserDefinedFieldRepository(connection), SQLiteTransactionManager(connection)
        ),
        default_project_policy(),
        column_service,
    )
    fields = field_api.list_fields(
        SCOPE, "p6-field-registry.v1", "Activity", auth_context=auth
    )
    field = next(item["field"] for item in fields if item["field"]["field_id"] == "formula.double_progress")
    assert field["data_type"] == "double"
    assert field["subject_area"] == "Activity"
    assert field["data_type"] != P6FieldType.ENUM.value
