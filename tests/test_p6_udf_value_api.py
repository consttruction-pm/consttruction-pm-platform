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
from construction_pm.p6_field_registry import P6FieldType
from construction_pm.p6_udf_value_api import (
    P6_UDF_VALUE_API_VERSION,
    P6UserDefinedFieldValueAPI,
)
from construction_pm.p6_user_defined_field_values_repository import (
    P6UserDefinedFieldValueApplicationService,
    P6UserDefinedFieldValuePersistenceError,
    SQLiteP6UserDefinedFieldValueRepository,
)
from construction_pm.p6_user_defined_fields_repository import (
    P6UserDefinedFieldApplicationService,
    P6UserDefinedFieldDefinition,
    SQLiteP6UserDefinedFieldRepository,
)


SCOPE = BackendScope("tenant-a", "project-a", 2)


def _api() -> P6UserDefinedFieldValueAPI:
    connection = sqlite3.connect(":memory:")
    transaction_manager = SQLiteTransactionManager(connection)
    definitions = SQLiteP6UserDefinedFieldRepository(connection)
    definition_service = P6UserDefinedFieldApplicationService(definitions, transaction_manager)
    values = SQLiteP6UserDefinedFieldValueRepository(connection)
    value_service = P6UserDefinedFieldValueApplicationService(
        values, definitions, transaction_manager
    )
    for definition in (
        _definition("udf.activity.contract_status", P6FieldType.STRING),
        _definition(
            "udf.activity.stage",
            P6FieldType.ENUM,
            nullable=True,
            allowed_values=("draft", "active"),
        ),
        _definition("udf.activity.score", P6FieldType.INTEGER),
        _definition("udf.activity.verified", P6FieldType.BOOLEAN),
        _definition("udf.activity.review_date", P6FieldType.DATE, nullable=True),
        _definition("udf.activity.float", P6FieldType.DURATION),
        _definition("udf.activity.read_only", P6FieldType.STRING, writable=False),
    ):
        definition_service.save_definition(definition)
    return P6UserDefinedFieldValueAPI(value_service, default_project_policy())


def _definition(
    udf_id: str,
    data_type: P6FieldType,
    *,
    writable: bool = True,
    nullable: bool = False,
    allowed_values: tuple[str, ...] = (),
) -> P6UserDefinedFieldDefinition:
    return P6UserDefinedFieldDefinition(
        scope=SCOPE,
        registry_version="p6-field-registry.v1",
        udf_id=udf_id,
        subject_area="Activity",
        display_name=udf_id.rsplit(".", 1)[-1],
        data_type=data_type,
        writable=writable,
        nullable=nullable,
        allowed_values=allowed_values,
    )


def _auth(role: str = "planner") -> AuthorizationContext:
    return AuthorizationContext("tenant-a", "project-a", "user-a", frozenset({role}))


def test_api_round_trips_typed_activity_values() -> None:
    api = _api()
    saved = api.save_value(
        SCOPE,
        "p6-field-registry.v1",
        "activity",
        "A-100",
        "udf.activity.contract_status",
        "signed",
        auth_context=_auth(),
    )
    assert saved["contract_version"] == P6_UDF_VALUE_API_VERSION
    assert saved["kind"] == "user_defined_field_value"
    assert saved["udf_id"] == "udf.activity.contract_status"
    assert saved["subject_area"] == "Activity"
    assert saved["value"] == "signed"
    assert saved["scope"]["project_revision"] == 2

    api.save_value(
        SCOPE, "p6-field-registry.v1", "activity", "A-100", "udf.activity.stage", "draft",
        auth_context=_auth(),
    )
    api.save_value(
        SCOPE, "p6-field-registry.v1", "activity", "A-100", "udf.activity.score", 9,
        auth_context=_auth(),
    )
    api.save_value(
        SCOPE, "p6-field-registry.v1", "activity", "A-100", "udf.activity.verified", True,
        auth_context=_auth(),
    )
    api.save_value(
        SCOPE, "p6-field-registry.v1", "activity", "A-100", "udf.activity.review_date", "2026-11-12",
        auth_context=_auth(),
    )
    api.save_value(
        SCOPE,
        "p6-field-registry.v1",
        "activity",
        "A-100",
        "udf.activity.float",
        {"value": "4.5", "unit": "day"},
        auth_context=_auth(),
    )

    values = api.read_values(
        SCOPE, "p6-field-registry.v1", "activity", "A-100", auth_context=_auth("viewer")
    )
    by_id = {item["udf_id"]: item for item in values}
    assert by_id["udf.activity.contract_status"]["value"] == "signed"
    assert by_id["udf.activity.stage"]["value"] == "draft"
    assert by_id["udf.activity.score"]["value"] == 9
    assert by_id["udf.activity.verified"]["value"] is True
    assert by_id["udf.activity.review_date"]["value"] == "2026-11-12"
    assert by_id["udf.activity.float"]["value"] == {"value": "4.5", "unit": "day"}
    assert by_id["udf.activity.read_only"]["value"] is None

    # A second write replaces the stored value at the same object identity.
    api.save_value(
        SCOPE, "p6-field-registry.v1", "activity", "A-100", "udf.activity.contract_status", "closed",
        auth_context=_auth(),
    )
    refreshed = {
        item["udf_id"]: item
        for item in api.read_values(
            SCOPE, "p6-field-registry.v1", "activity", "A-100", auth_context=_auth("viewer")
        )
    }
    assert refreshed["udf.activity.contract_status"]["value"] == "closed"


def test_api_allows_clearing_only_a_nullable_udf() -> None:
    api = _api()
    saved = api.save_value(
        SCOPE, "p6-field-registry.v1", "activity", "A-100", "udf.activity.stage", None,
        auth_context=_auth(),
    )
    assert saved["value"] is None

    with pytest.raises(P6UserDefinedFieldValuePersistenceError, match="INVALID_NULL_VALUE"):
        api.save_value(
            SCOPE, "p6-field-registry.v1", "activity", "A-100",
            "udf.activity.contract_status", None, auth_context=_auth(),
        )


def test_api_rejects_values_that_do_not_match_the_stored_definition() -> None:
    api = _api()
    with pytest.raises(P6UserDefinedFieldValuePersistenceError, match="INVALID_ENUM_VALUE"):
        api.save_value(
            SCOPE, "p6-field-registry.v1", "activity", "A-100", "udf.activity.stage", "unknown",
            auth_context=_auth(),
        )
    with pytest.raises(P6UserDefinedFieldValuePersistenceError, match="INVALID_INTEGER_VALUE"):
        api.save_value(
            SCOPE, "p6-field-registry.v1", "activity", "A-100", "udf.activity.score", True,
            auth_context=_auth(),
        )
    with pytest.raises(P6UserDefinedFieldValuePersistenceError, match="INVALID_DATE_VALUE"):
        api.save_value(
            SCOPE, "p6-field-registry.v1", "activity", "A-100", "udf.activity.review_date", "12/11/2026",
            auth_context=_auth(),
        )
    with pytest.raises(P6UserDefinedFieldValuePersistenceError, match="INVALID_DURATION_VALUE"):
        api.save_value(
            SCOPE, "p6-field-registry.v1", "activity", "A-100", "udf.activity.float", {"value": "1"},
            auth_context=_auth(),
        )


def test_api_rejects_unknown_objects_udfs_and_unwritable_definitions() -> None:
    api = _api()
    with pytest.raises(P6UserDefinedFieldValuePersistenceError, match="UNSUPPORTED_UDF_OBJECT_TYPE"):
        api.save_value(
            SCOPE, "p6-field-registry.v1", "wbs", "W-1", "udf.activity.stage", "draft",
            auth_context=_auth(),
        )
    with pytest.raises(P6UserDefinedFieldValuePersistenceError, match="UDF_NOT_FOUND"):
        api.save_value(
            SCOPE, "p6-field-registry.v1", "activity", "A-100", "udf.activity.unknown", "x",
            auth_context=_auth(),
        )
    with pytest.raises(P6UserDefinedFieldValuePersistenceError, match="UDF_NOT_WRITABLE"):
        api.save_value(
            SCOPE, "p6-field-registry.v1", "activity", "A-100", "udf.activity.read_only", "x",
            auth_context=_auth(),
        )
    with pytest.raises(P6UserDefinedFieldValuePersistenceError, match="UNSUPPORTED_REGISTRY_VERSION"):
        api.read_values(
            SCOPE, "p6-field-registry.v2", "activity", "A-100", auth_context=_auth("viewer")
        )


def test_api_enforces_project_permission_and_scope() -> None:
    api = _api()
    with pytest.raises(AuthorizationError, match="authorization denied"):
        api.save_value(
            SCOPE, "p6-field-registry.v1", "activity", "A-100", "udf.activity.stage", "draft",
            auth_context=_auth("viewer"),
        )
    with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
        api.read_values(
            BackendScope("tenant-b", "project-a", 2),
            "p6-field-registry.v1",
            "activity",
            "A-100",
            auth_context=_auth("viewer"),
        )
