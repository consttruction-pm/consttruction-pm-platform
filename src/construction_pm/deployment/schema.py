"""Idempotent PostgreSQL schema creation for the production runtime.

Every statement is ``CREATE ... IF NOT EXISTS``. The bootstrap never drops,
truncates or rewrites a row, so provisioning an existing database is safe.
"""

from __future__ import annotations

from typing import Any

from ..activity_master_repository import PostgresActivityMasterRepository
from ..enterprise_task_repository import PostgresEnterpriseTaskRepository
from ..global_administration import PostgresGlobalAdministrationStore
from ..enterprise_organization_access_repository import PostgresEnterpriseOrganizationAccessRepository
from ..identity_session import PostgresIdentityStore
from ..p6_cost_account_repository import PostgresP6CostAccountRepository
from ..p6_obs_repository import PostgresP6OBSRepository
from ..p6_project_security_repository import PostgresP6ProjectSecurityRepository
from ..p6_associated_resource_repository import PostgresP6AssociatedResourceRepository
from ..p6_resource_master_repository import PostgresP6ResourceRepository
from ..p6_resource_assignment_repository import (
    PostgresP6ResourceAssignmentRepository,
    PostgresP6ResourceAssignmentPeriodRepository,
)
from ..p6_resource_spread_repository import PostgresP6ResourceSpreadRepository
from ..p6_resource_capacity_repository import PostgresP6ResourceCapacityRepository
from ..p6_resource_rate_repository import PostgresP6ResourceRateRepository
from ..p6_code_repository import PostgresP6CodeRepository
from ..p6_code_assignment_repository import PostgresP6CodeAssignmentRepository
from ..p6_field_registry_repository import PostgresP6FieldRegistryRepository
from ..p6_global_security import PostgresP6GlobalSecurityRepository
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
    PostgresGlobalAdministrationStore(connection).initialize()
    PostgresEnterpriseTaskRepository(connection).initialize()
    PostgresEnterpriseOrganizationAccessRepository(connection).initialize()
    initialize_project_lifecycle_schema(connection)
    PostgresActivityMasterRepository(connection).initialize()
    PostgresP6CostAccountRepository(connection).initialize()
    obs_repository = PostgresP6OBSRepository(connection)
    obs_repository.initialize()
    PostgresP6GlobalSecurityRepository(connection).initialize()
    PostgresP6ResourceRepository(connection).initialize()
    PostgresP6ResourceAssignmentRepository(connection).initialize()
    PostgresP6ResourceAssignmentPeriodRepository(connection).initialize()
    PostgresP6ResourceSpreadRepository(connection).initialize()
    PostgresP6ResourceCapacityRepository(connection).initialize()
    PostgresP6ResourceRateRepository(connection).initialize()
    PostgresP6CodeRepository(connection).initialize()
    PostgresP6CodeAssignmentRepository(connection).initialize()
    def project_obs_lookup(tenant_id: str, project_id: str) -> str | None:
        row = connection.execute(
            "SELECT obs_id FROM project_lifecycle_projects WHERE tenant_id=%s AND project_id=%s",
            (tenant_id, project_id),
        ).fetchone()
        return None if row is None or not row[0] else str(row[0])
    PostgresP6ProjectSecurityRepository(
        connection, project_obs_lookup=project_obs_lookup, obs_repository=obs_repository
    ).initialize()
    PostgresP6AssociatedResourceRepository(connection).initialize()
    PostgresWBSMasterRepository(connection).initialize()
    PostgresRelationshipMasterRepository(connection).initialize()
    PostgresP6FieldRegistryRepository(connection).initialize()
    PostgresP6LayoutRepository(connection).initialize()
    PostgresP6UserDefinedFieldRepository(connection).initialize()
    PostgresP6UserDefinedFieldValueRepository(connection).initialize()
    PostgresScheduleInputSnapshotRepository(connection).initialize()
    PostgresCalculationContextRepository(connection).initialize()
