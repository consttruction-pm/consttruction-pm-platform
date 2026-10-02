from __future__ import annotations

import sqlite3

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    default_project_policy,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_mapping_api import P6_MAPPING_API_VERSION, P6MappingAPI
from construction_pm.p6_mapping_registry import (
    P6MappingDefinition,
    P6MappingFormat,
    P6MappingRegistryApplicationService,
    P6MappingStatus,
    PersistedP6Mapping,
    SQLiteP6MappingRegistryRepository,
)


class Tx:
    def transaction(self):
        class C:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        return C()


def scope() -> BackendScope:
    return BackendScope("t1", "p1", 4)


def auth(role: str = "planner", tenant: str = "t1", project: str = "p1") -> AuthorizationContext:
    return AuthorizationContext(
        tenant_id=tenant,
        project_id=project,
        user_id="u1",
        roles=frozenset({role}),
    )


def record() -> PersistedP6Mapping:
    return PersistedP6Mapping(
        scope(),
        P6MappingDefinition(
            "activity.code",
            "p6-field-registry.v1",
            P6MappingFormat.XER_PROJECT,
            "Activity",
            "task_code",
            "activity.code",
            P6MappingStatus.SUPPORTED,
            "string",
            "string",
        ),
    )


def api() -> P6MappingAPI:
    repository = SQLiteP6MappingRegistryRepository(sqlite3.connect(":memory:"))
    return P6MappingAPI(
        P6MappingRegistryApplicationService(repository, Tx()),
        default_project_policy(),
    )


def test_typed_mapping_round_trip_and_filter() -> None:
    a = api()
    created = a.create(record(), auth_context=auth())
    assert created["contract_version"] == P6_MAPPING_API_VERSION
    assert created["mapping"]["mapping_id"] == "activity.code"
    assert a.get(scope(), "activity.code", auth_context=auth()) == created
    assert a.list(
        scope(),
        format=P6MappingFormat.XER_PROJECT,
        subject_area="Activity",
        auth_context=auth(),
    ) == (created,)


def test_mapping_api_rejects_cross_scope_and_read_without_permission() -> None:
    a = api()
    with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
        a.create(
            PersistedP6Mapping(BackendScope("other", "p1", 4), record().definition),
            auth_context=auth(),
        )
    a.create(record(), auth_context=auth())
    with pytest.raises(AuthorizationError):
        a.get(scope(), "activity.code", auth_context=auth("viewer"))


def test_mapping_api_write_requires_project_write() -> None:
    with pytest.raises(AuthorizationError):
        api().create(record(), auth_context=auth("viewer"))
