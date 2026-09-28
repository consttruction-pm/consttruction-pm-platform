from __future__ import annotations

import sqlite3
from contextlib import contextmanager

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    default_project_policy,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_mapping_registry import (
    P6MappingDefinition,
    P6MappingFormat,
    P6MappingRegistryApplicationService,
    P6MappingStatus,
    PersistedP6Mapping,
    SQLiteP6MappingRegistryRepository,
)
from construction_pm.p6_mapping_registry_api import (
    P6_MAPPING_REGISTRY_API_VERSION,
    P6MappingRegistryAPI,
)


class TransactionManager:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    @contextmanager
    def transaction(self):
        try:
            yield
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise


def scope(revision: int = 1) -> BackendScope:
    return BackendScope(tenant_id="t1", project_id="p1", project_revision=revision)


def auth(
    *,
    tenant_id: str = "t1",
    project_id: str = "p1",
    role: str = "planner",
) -> AuthorizationContext:
    return AuthorizationContext(
        tenant_id=tenant_id,
        project_id=project_id,
        user_id="u1",
        roles=frozenset({role}),
    )


def record(mapping_id: str = "activity.code") -> PersistedP6Mapping:
    return PersistedP6Mapping(
        scope=scope(),
        definition=P6MappingDefinition(
            mapping_id=mapping_id,
            registry_version="p6-field-registry.v1",
            format=P6MappingFormat.XER_PROJECT,
            subject_area="Activity",
            source_field="task_code",
            canonical_field="activity.code",
            status=P6MappingStatus.SUPPORTED,
            source_type="string",
            canonical_type="string",
        ),
    )


def api() -> P6MappingRegistryAPI:
    connection = sqlite3.connect(":memory:")
    repository = SQLiteP6MappingRegistryRepository(connection)
    manager = TransactionManager(connection)
    service = P6MappingRegistryApplicationService(repository, manager)
    return P6MappingRegistryAPI(service, default_project_policy())


def test_create_and_read_expose_versioned_typed_boundary() -> None:
    instance = api()
    created = instance.create(record(), auth_context=auth())
    assert created["contract_version"] == P6_MAPPING_REGISTRY_API_VERSION
    assert created["mapping"]["format"] == "XER_PROJECT"
    assert created["mapping"]["status"] == "SUPPORTED"
    assert instance.get(scope(), "activity.code", auth_context=auth()) == created


def test_list_supports_explicit_status_filter_without_recalculating_mapping() -> None:
    instance = api()
    instance.create(record("activity.code"), auth_context=auth())
    preserve = record("activity.name")
    preserve = PersistedP6Mapping(
        scope=preserve.scope,
        definition=P6MappingDefinition(
            **{**preserve.definition.__dict__, "status": P6MappingStatus.UNSUPPORTED_PRESERVE}
        ),
    )
    instance.create(preserve, auth_context=auth())
    result = instance.list(
        scope(),
        status=P6MappingStatus.UNSUPPORTED_PRESERVE,
        auth_context=auth(),
    )
    assert [item["mapping"]["mapping_id"] for item in result] == ["activity.name"]


def test_cross_scope_and_missing_permission_are_rejected() -> None:
    instance = api()
    with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
        instance.create(record(), auth_context=auth(tenant_id="other"))
    with pytest.raises(AuthorizationError, match="authorization denied"):
        instance.get(scope(), "activity.code", auth_context=auth(role="writer"))
