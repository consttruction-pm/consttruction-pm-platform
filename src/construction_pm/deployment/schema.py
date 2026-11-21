"""Idempotent PostgreSQL schema creation for the production runtime.

Every statement is ``CREATE ... IF NOT EXISTS``. The bootstrap never drops,
truncates or rewrites a row, so provisioning an existing database is safe.
"""

from __future__ import annotations

from typing import Any

from ..activity_master_repository import PostgresActivityMasterRepository
from ..calendar_exception_repository import PostgresCalendarExceptionRepository
from ..calendar_master_repository import PostgresCalendarMasterRepository
from ..calendar_snapshot_repository import PostgresCalendarSnapshotRepository
from ..calendar_work_hours_repository import PostgresCalendarWorkHourRepository
from ..enterprise_task_repository import PostgresEnterpriseTaskRepository
from ..global_administration import PostgresGlobalAdministrationStore
from ..enterprise_organization_access_repository import PostgresEnterpriseOrganizationAccessRepository
from ..identity_session import PostgresIdentityStore
from ..p6_cost_account_repository import PostgresP6CostAccountRepository
from ..p6_obs_repository import PostgresP6OBSRepository
from ..p6_field_registry_repository import PostgresP6FieldRegistryRepository
from ..p6_layout_definition_repository import PostgresP6LayoutRepository
from ..p6_user_defined_field_values_repository import (
    PostgresP6UserDefinedFieldValueRepository,
)
from ..p6_user_defined_fields_repository import PostgresP6UserDefinedFieldRepository
from ..postgres_project_lifecycle import initialize_project_lifecycle_schema
from ..postgres_scheduling_job_lifecycle import initialize_scheduling_job_schema
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
    PostgresGlobalAdministrationStore(connection).initialize()
    PostgresEnterpriseTaskRepository(connection).initialize()
    PostgresEnterpriseOrganizationAccessRepository(connection).initialize()
    initialize_project_lifecycle_schema(connection)
    PostgresActivityMasterRepository(connection).initialize()
    PostgresP6CostAccountRepository(connection).initialize()
    PostgresP6OBSRepository(connection).initialize()
    PostgresWBSMasterRepository(connection).initialize()
    PostgresRelationshipMasterRepository(connection).initialize()
    PostgresP6FieldRegistryRepository(connection).initialize()
    PostgresP6LayoutRepository(connection).initialize()
    PostgresP6UserDefinedFieldRepository(connection).initialize()
    PostgresP6UserDefinedFieldValueRepository(connection).initialize()
    PostgresScheduleInputSnapshotRepository(connection).initialize()
    PostgresCalculationContextRepository(connection).initialize()
    # Calendar definitions, their immutable snapshots, work-hour rules and
    # exceptions are the real inputs of Schedule Query. Creating the tables is
    # idempotent and never seeds a default calendar.
    PostgresCalendarMasterRepository(connection).initialize()
    PostgresCalendarSnapshotRepository(connection).initialize()
    PostgresCalendarWorkHourRepository(connection).initialize()
    PostgresCalendarExceptionRepository(connection).initialize()
    initialize_scheduling_job_schema(connection)
