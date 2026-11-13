"""Idempotent PostgreSQL schema creation for the production runtime.

Every statement is ``CREATE ... IF NOT EXISTS``. The bootstrap never drops,
truncates or rewrites a row, so provisioning an existing database is safe.
"""

from __future__ import annotations

from typing import Any

from ..activity_master_repository import PostgresActivityMasterRepository
from ..identity_session import PostgresIdentityStore
from ..p6_field_registry_repository import PostgresP6FieldRegistryRepository
from ..p6_layout_definition_repository import PostgresP6LayoutRepository
from ..p6_user_defined_field_values_repository import (
    PostgresP6UserDefinedFieldValueRepository,
)
from ..p6_user_defined_fields_repository import PostgresP6UserDefinedFieldRepository
from ..postgres_project_lifecycle import initialize_project_lifecycle_schema
from ..relationship_master_repository import PostgresRelationshipMasterRepository
from ..schedule_calculation_context_repository import (
    PostgresCalculationContextRepository,
)
from ..schedule_input_snapshot_repository import (
    PostgresScheduleInputSnapshotRepository,
)
from ..wbs_master_repository import PostgresWBSMasterRepository


def initialize_production_schema(connection: Any) -> None:
    """Create every table the deployed surface reads or writes."""
    PostgresIdentityStore(connection).initialize()
    initialize_project_lifecycle_schema(connection)
    PostgresActivityMasterRepository(connection).initialize()
    PostgresWBSMasterRepository(connection).initialize()
    PostgresRelationshipMasterRepository(connection).initialize()
    PostgresP6FieldRegistryRepository(connection).initialize()
    PostgresP6LayoutRepository(connection).initialize()
    PostgresP6UserDefinedFieldRepository(connection).initialize()
    PostgresP6UserDefinedFieldValueRepository(connection).initialize()
    PostgresScheduleInputSnapshotRepository(connection).initialize()
    PostgresCalculationContextRepository(connection).initialize()
