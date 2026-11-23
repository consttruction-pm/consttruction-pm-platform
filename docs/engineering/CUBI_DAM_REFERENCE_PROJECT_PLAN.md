# CUBI shared dam reference project — build and audit plan

**Tracking:** [Issue #2132](https://github.com/consttruction-pm/consttruction-pm-platform/issues/2132)  
**Related P0 wizard work:** [Issue #2131](https://github.com/consttruction-pm/consttruction-pm-platform/issues/2131)  
**Target branch:** `fix/p0-p6-v26-project-creation-wizard`  
**Status:** shared in-progress build workspace; implementation/persistence blocked by remaining schema and application-access work. No project data has yet been inserted.

## Product contract

Create `CUBI-DAM-001` — Large Reservoir Dam and Hydropower Development — as the shared in-progress Engineering/Enterprise build workspace. It must behave like persisted operational project data, not like a finished sample/demo. TEMPORARY PROJECT-SCOPED EXCEPTION: display and read access to this project must not depend on the user's project role, team membership or project assignment. Every signed-in user must be able to find and open it from the relevant Engineering panels so all pages can be tested. This is not a global authentication/authorization bypass: keep login, tenant boundaries, environment permissions, admin controls and all other projects' role checks unchanged. For this shared reference dataset, keep destructive writes and edits guarded against accidental corruption unless a separate explicit test-write mode is implemented.

The shared build workspace is an explicit exception to ordinary user-owned projects: it must be discoverable through a separate shared-workspace entry in Engineering and Enterprise, and must not be mixed into users' personal project registers, project counts, or portfolio lists. Keep it in-progress and do not present it as completed, approved, or production-historical data. All Engineering and Enterprise pages under test must read the same canonical project/revision data from PostgreSQL. No page-local fixtures, duplicated project records, Excel source retention, or hardcoded CPM results. Keep `CUBI-REF-001/002/003` immutable.

## P6 Professional V26 Help crosswalk

Authoritative references:
- HTML Help TOC: https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm
- User Guide: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/index.html
- Create a Project: https://docs.oracle.com/cd/G48902_01/client_help/en_US/create_a_project.htm
- Project Details: https://docs.oracle.com/cd/G48902_01/client_help/en_US/defining_project_details.htm

| P6 workflow | CUBI implementation/data contract | Acceptance evidence |
|---|---|---|
| File > New / New Project Wizard | Typed create command: EPS, unique user-entered Project ID, Name, Planned Start, optional Must Finish By, OBS Responsible Manager, Default Rate Type | Browser→session API→route→application service→PostgreSQL create/list/open roundtrip |
| EPS | Select existing authorized EPS node; do not invent a tenant/organization binding | EPS picker, invalid/unauthorized EPS rejected |
| OBS / Responsible Manager | Choose manager from authorized OBS tree | OBS picker, invalid/unauthorized manager rejected |
| Project Details | General/project identity, dates, schedule defaults, codes, summarization, activity numbering, optimistic settings revision | Save/reload roundtrip and concurrent revision conflict |
| WBS | 4–6 levels, control accounts and work packages | Parent/child integrity, stable ordering, WBS summaries |
| Calendars | Project, resource and shift calendars; holidays/exceptions and work hours | Calendar resolution and working-time calculations |
| Activities | 700–1,000 uniquely identified activities with type/status/duration/percent-complete semantics | Valid activity master, WBS assignment, filters and grouping |
| Relationships | FS/SS/FF/SF, positive/negative lag with explicit units | Endpoint integrity, cycle validation, lag semantics |
| Resources | Labor, nonlabor/equipment and material resources; hierarchy, units and active state | Resource master CRUD and type validation |
| Assignments | Activity/resource/role, units, units/time, actual/remaining units, cost and calendar | Assignment totals, capacity and rate calculations |
| Schedule | Shared canonical scheduling engine; schedule options and status date | Engine-produced early/late dates, float and critical path; run/snapshot hash |
| Baseline | Immutable baseline header and activity snapshots | Baseline capture, compare and readback |
| Gantt | Read authoritative activity dates, progress, links, baseline and critical flags | Visual/API consistency with calculated schedule |
| Access modes | Shared and Read Only; Exclusive only with explicit privilege | Unauthorized write/checkout denied |

CUBI interface must not display Oracle, Primavera or P6 branding. The Help is a functional reference only.

## Initial project data scope

Major work packages:
1. Engineering, surveys, geotechnical investigations and permits
2. Access roads, camps, utilities and site preparation
3. River diversion tunnels, cofferdams and temporary works
4. Reservoir clearing, relocation and environmental/social mitigation
5. Foundation excavation, consolidation and curtain grouting
6. Concrete dam body, galleries and instrumentation
7. Spillway, gates, outlet works and energy dissipators
8. Intake, penstocks and hydraulic steel structures
9. Powerhouse civil works and embedded parts
10. Turbine-generator units, governors and auxiliaries
11. Switchyard, transformers, grid interconnection and transmission
12. Testing, commissioning, reservoir impoundment and handover

Target scale: 700–1,000 activities, 4–6 WBS levels, dense but acyclic predecessor network, multiple calendars, mixed relationship types, labor/equipment/material resources, resource assignments and rates, cost accounts, progress, baseline and schedule run. Dates and CPM outputs must be engine-derived.

## Live audit findings (2026-11-24)

Read-only checks against canonical Supabase project `pbgosszuzemljgoccppk`:
- Lifecycle, WBS, activity, activity-WBS, relationship, project schedule settings, input snapshot, calculation context and OBS tables exist; all are empty.
- Resource, calendar and baseline tables expected by repository code are not present in the live public schema (resource repository code expects `p6_resource_master`).
- One active non-test identity maps to tenant `cubi-platform`; this does **not** by itself authorize a service-role insert or prove the current browser session. No credentials/hash fields were read.
- Admin SQL context returns `auth.uid() = NULL`; it cannot impersonate the current authenticated browser user.
- Initial audit found 39 public tables without RLS. On 2026-11-24, all 59 current public base tables were secured: RLS enabled, explicit restrictive deny policies for `anon`/`authenticated`, and direct table privileges revoked. `service_role` retains server access. Security Advisor then returned zero security lints.
- Two trigger functions had mutable `search_path`; both now use `pg_catalog`.
- The deny policies intentionally block direct Supabase Data API access; all browser reads/writes must go through the authenticated CUBI server boundary. New tables created by later migrations must receive the same RLS/deny hardening before importer preflight can pass.
- Performance Advisor reports five unindexed foreign keys and 33 unused indexes. Unused-index notices are informational; do not delete them without workload evidence.
- The broad production schema bootstrap applies a migration registry and must not be invoked as a shortcut.

## Safe implementation sequence

1. Complete P0 project wizard and authenticated application-service path.
2. Inventory every repository initializer and reconcile missing live tables through reviewed additive migration(s); include resource, calendar, assignment, capacity/rate, baseline, activity actuals, OBS and schedule run/snapshot dependencies.
3. Implement a narrowly scoped project-ID-based shared visibility rule for `CUBI-DAM-001`: every authenticated user can list/open/read it in all relevant Engineering panels regardless of project role or membership. Do not create mass membership rows. This exception must not change role enforcement for other projects or bypass authentication/tenant/environment gates. Keep the reference dataset protected from accidental destructive writes.
4. Design RLS policies for the exposed schema, test existing login, Personal Workbench-first, environment selector, Engineering/Enterprise switching, admin dashboard and all existing user permissions.
5. Build deterministic generator in code; validate WBS/activities/relationships/resources/assignments/calendars before persistence. Persist via canonical repositories/application services in one transaction and invoke shared schedule engine.
6. Run API, Postgres, browser and regression checks using disposable identities/projects. Verify all pages read the same project revision and reference projects remain unchanged.
7. Only after all gates pass, create the shared project through the authenticated session and publish it to all users. No production DB mutation, merge, deployment or alias change before approval gates.

## Updated product clarification (2026-11-24)

`CUBI-DAM-001` is a temporary shared build workspace, not an ordinary customer-owned project and not a finished demo. It must be available to signed-in users in both Engineering and Enterprise for end-to-end construction and verification. It must be excluded from `/api/projects` and all ordinary user-owned project registers/portfolio counts; expose it through a separately labelled shared-workspace surface. Its underlying facts are persisted once and consumed by both environments. Do not create project membership rows for every user. The shared exception grants read access only; write/schedule permissions remain controlled by explicit project policy or a controlled test-write capability. Tenant boundaries, login, environment authorization and admin controls remain in force.

## Current stop conditions

- The original direct Data API exposure has been closed and Security Advisor currently reports zero lints. The registry-backed read-only shared-workspace access path and dedicated list endpoint are implemented in source; CI and browser verification are still pending.
- The database admin connection has no authenticated browser user context; do not use it to simulate a user session.
- Required resource/calendar/baseline and Enterprise schema is incomplete in the live database; repository migrations 14/15 are pending and must be applied through the versioned migration runner, then hardened with RLS and explicit direct-client denial.
- Therefore the reference project has **not** been inserted and no one should claim it is visible in user accounts yet.


## Implementation work started (2026-11-24)

The feature branch now contains:
- `src/construction_pm/importing/dam_reference_project.py`: deterministic in-memory dataset builder; 720 activities, 192 WBS records, 730 acyclic relationships across FS/SS/FF/SF, 72 labor resources, 48 equipment resources, 1,440 assignments, 720 baseline activity rows, progress facts, cost periods and budget inputs.
- `scripts/import_dam_reference_project.py`: guarded PostgreSQL import command. It does not run migrations, does not create user memberships, and refuses to persist until all public base tables have RLS enabled and every repository dependency exists. It calls the existing PostgreSQL reference importer with the generated bundle and requires a successful canonical schedule-engine manifest before reporting success.
- `tests/test_dam_reference_project.py`: deterministic counts, referential integrity, forward-only dependency graph and relationship-type coverage tests.
- The `cubi_reference_project` registry now has a dedicated authenticated `GET /api/shared-projects` read surface. Ordinary `/api/projects` lists only user memberships. PostgreSQL and preview repositories expose separate shared-reference listing and membership-free `get_for_user`; the project lifecycle service marks the authorization context as `shared_reference` only when the tenant-scoped registry confirms this project. The policy honors that flag for `PROJECT_READ` only; write/schedule/admin remain governed by the caller's actual roles. Engineering can deep-link the shared project without adding it to personal project tabs. Enterprise Projects and Portfolio render it in a separate Shared Build Workspace section, outside personal registers and portfolio counts. These code paths are committed but still require fresh CI and browser verification.

Current live preflight (read-only):
- `CUBI-DAM-001` does not exist yet.
- The three `CUBI-REF-001/002/003` project lifecycle rows are also absent in this database; this task does not create or modify them.
- After the security hardening migration, all 59 existing public base tables have RLS enabled; `anon` and `authenticated` have zero direct table privileges.
- Several required importer tables are missing, including the calendar master/snapshot/exception/work-hour tables, resource master/assignment/rate/capacity tables, baseline tables, activity-period actuals, financial periods, roles, expenses and reference import journal/registry tables.
- Code migration steps 14 and 15 (reference engineering/enterprise schema) are present in the repository but not reflected in the live schema ledger; the live ledger was advanced with three security hardening migrations.

A draft PR remains open for CI/review: PR #2133. Generator tests are committed but have not yet been executed in this environment. Security hardening migrations were applied to the live database; no project rows, schedule data, user sessions, roles or memberships were changed. The guarded importer remains blocked by missing reference engineering/Enterprise tables. Its preflight now additionally requires the explicit direct-client deny policy on every public table and zero anon/authenticated table privileges.
