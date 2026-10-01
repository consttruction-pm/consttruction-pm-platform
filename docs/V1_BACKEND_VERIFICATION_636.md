# V1 Backend/API Verification — #636

Snapshot: 2026-10-01
Base: current `main` after #640 and #641
Issue: #636

## Disposition

The requested Backend/API seam is substantially present on current `main`. This document records the current-main evidence so the lane does not invent a second domain model or duplicate #603/#635.

## Verification matrix

| Contract area | Current-main evidence | Status |
|---|---|---|
| Session / ProjectContext | `src/construction_pm/application/project_lifecycle.py`; `tests/test_project_lifecycle.py`, `tests/test_project_lifecycle_api.py` | Verified |
| Tenant/project authorization | `src/construction_pm/application/authorization.py`; `tests/test_application_authorization_context.py`; project lifecycle scope tests | Verified |
| Stale revision / optimistic locking | `tests/client_sync/test_revision_endpoint.py`; `tests/integration/test_application_api_revision_boundary.py`; `tests/resources/test_revision_propagation.py` | Verified |
| Idempotency / atomic replay | `tests/test_atomic_sync_idempotency_contract.py`; `tests/test_server_gateway_idempotency_atomic.py`; `tests/test_postgres_idempotency_lock.py` | Verified |
| PostgreSQL ProjectContext persistence | `src/construction_pm/postgres_project_lifecycle.py`; `tests/test_postgres_project_lifecycle.py` | Verified |
| Assignment read/persistence seam | `src/construction_pm/p6_resource_assignment_repository.py`; `tests/test_p6_resource_assignment_repository.py`; PostgreSQL live coverage exists under `tests/integration/` | Verified |
| Spread read/persistence seam | `src/construction_pm/p6_resource_spread_repository.py`; `tests/test_p6_resource_spread_repository.py`; PostgreSQL live coverage exists under `tests/integration/` | Verified |
| Typed activity-period API | `src/construction_pm/p6_activity_period_actual_api.py`; `tests/test_p6_activity_period_actual_api.py`; PostgreSQL live coverage exists | Verified |
| Calendar repository/API seam | `src/construction_pm/calendar_master_repository.py`; `tests/test_calendar_master_repository.py` | Verified |
| Schedule options contract | `src/construction_pm/scheduling/schedule_options.py`; `tests/scheduling/test_schedule_options.py`; canonical/options tests | Verified |
| Authoritative scheduling boundary | `src/construction_pm/scheduling/authoritative_schedule.py`; `tests/scheduling/test_authoritative_schedule.py` | Verified |

## Important boundary

No new P6/CPM calculation logic is added here. Scheduling semantics remain in Shared Core. Backend/API verification only establishes that existing authoritative contracts are exposed and persisted without a second calculation/domain model.

## Remaining evidence

The acceptance requirement still needs fresh focused test execution and relevant CI evidence on this current-main branch. If those checks pass, this lane has no identified implementation gap and can be closed without adding backend features.

If a focused test fails, the failure should be treated as the concrete next action and fixed in the smallest owning module.
