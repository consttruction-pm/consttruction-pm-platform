from __future__ import annotations

import json
import sqlite3

from construction_pm.application.authorization import AuthorizationContext, default_project_policy
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.p6_field_registry import get_field
from construction_pm.p6_field_registry_api import P6FieldRegistryAPI
from construction_pm.p6_field_registry_repository import P6FieldRegistryApplicationService, PersistedP6Field, SQLiteP6FieldRegistryRepository
from construction_pm.p6_user_defined_fields_repository import P6UserDefinedFieldApplicationService, SQLiteP6UserDefinedFieldRepository

SCHEDULE_OPTIONS_METADATA = (
    "schedule_options.create_date",
    "schedule_options.create_user",
    "schedule_options.last_update_date",
    "schedule_options.last_update_user",
    "schedule_options.project_id",
    "schedule_options.project_object_id",
    "schedule_options.user_name",
    "schedule_options.user_object_id",
)


def _scope() -> BackendScope:
    return BackendScope("tenant-schedule-options", "project-schedule-options", 9)


def _api() -> P6FieldRegistryAPI:
    connection = sqlite3.connect(":memory:")
    return P6FieldRegistryAPI(
        field_service=P6FieldRegistryApplicationService(
            SQLiteP6FieldRegistryRepository(connection),
            SQLiteTransactionManager(connection),
        ),
        udf_service=P6UserDefinedFieldApplicationService(
            SQLiteP6UserDefinedFieldRepository(connection),
            SQLiteTransactionManager(connection),
        ),
        authorization_policy=default_project_policy(),
    )


def _auth(role: str) -> AuthorizationContext:
    scope = _scope()
    return AuthorizationContext(scope.tenant_id, scope.project_id, "schedule-options-test-user", frozenset({role}))


def test_schedule_options_metadata_round_trips_through_existing_registry_persistence() -> None:
    connection = sqlite3.connect(":memory:")
    repository = SQLiteP6FieldRegistryRepository(connection)
    scope = _scope()
    records = tuple(
        PersistedP6Field(scope=scope, registry_version="p6-field-registry.v1", field=get_field(field_id))
        for field_id in SCHEDULE_OPTIONS_METADATA
    )
    for record in records:
        assert record.field.writable is False
        assert record.field.computed is False
        repository.upsert_field(record)
    loaded = tuple(repository.get_field(scope, "p6-field-registry.v1", field_id) for field_id in SCHEDULE_OPTIONS_METADATA)
    assert loaded == records


def test_schedule_options_metadata_preserves_scope_and_canonical_payload() -> None:
    connection = sqlite3.connect(":memory:")
    repository = SQLiteP6FieldRegistryRepository(connection)
    scope = _scope()
    record = PersistedP6Field(
        scope=scope,
        registry_version="p6-field-registry.v1",
        field=get_field("schedule_options.project_object_id"),
    )
    repository.upsert_field(record)
    row_before = connection.execute(
        "SELECT payload_json FROM p6_field_registry WHERE tenant_id=? AND project_id=? AND field_id=?",
        (scope.tenant_id, scope.project_id, record.field.field_id),
    ).fetchone()
    assert row_before is not None
    assert json.loads(row_before[0])["field"]["data_type"] == "object-id"
    assert repository.upsert_field(record) == record
    row_after = connection.execute(
        "SELECT payload_json FROM p6_field_registry WHERE tenant_id=? AND project_id=? AND field_id=?",
        (scope.tenant_id, scope.project_id, record.field.field_id),
    ).fetchone()
    assert row_after == row_before
    assert repository.get_field(
        BackendScope(scope.tenant_id, "other-project", scope.project_revision),
        "p6-field-registry.v1",
        record.field.field_id,
    ) is None


def test_schedule_options_metadata_is_exposed_as_read_only_typed_api_contract() -> None:
    api = _api()
    scope = _scope()
    for field_id in SCHEDULE_OPTIONS_METADATA:
        result = api.save_field(scope, "p6-field-registry.v1", get_field(field_id), auth_context=_auth("planner"))
        assert result["field"]["writable"] is False
        assert result["field"]["computed"] is False
        loaded = api.get_field(scope, "p6-field-registry.v1", field_id, auth_context=_auth("viewer"))
        assert loaded == result
    listed = api.list_fields(scope, "p6-field-registry.v1", "ScheduleOptions", auth_context=_auth("viewer"))
    assert [item["field"]["field_id"] for item in listed] == sorted(SCHEDULE_OPTIONS_METADATA)
