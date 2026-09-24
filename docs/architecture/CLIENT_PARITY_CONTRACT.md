# Client Parity Contract — Web + Desktop Application

## Purpose
The Web product and Desktop Application are two clients of the same ConstructionPM product. They must remain capability-equivalent at the business-function level and must never implement competing calculation rules.

## Non-negotiable architecture
- Shared Domain/Calculation Core is the single source of truth.
- Scheduling, Calendar, Progress, EVM, Resource, Cost and other business calculations are never duplicated in a client.
- Web and Desktop call the same Application/API contracts.
- Clients never access the database directly.
- Typed API contracts preserve Decimal, date, duration, Boolean and text semantics.
- Tenant/company/project context is explicit.
- Optimistic locking, transactions, audit/revision and portability rules remain server/core responsibilities.
- UI differences may exist for platform usability, but business meaning and calculated results must match.

## Required parity
Both clients must expose, according to product permissions and feature maturity:
WBS, Activities, Gantt, relationships FS/SS/FF/SF, calendars, constraints, scheduling, baselines/current/actual/forecast, progress, EVM, resources, costs, documents, reports/print, import/export, users/security, AI Assistant and Smart Guide.

## Calculation parity test
Given the same project, schema versions, calendar/version, scheduling settings, resource/cost configuration and input data, Web and Desktop must display the same authoritative calculated values.

## Change rule
A client-only implementation is forbidden when the behavior changes business semantics. Such changes must first be implemented in Shared Domain/Calculation Core or the Application/API contract and documented.

## UI rule
UI state, routing, rendering, keyboard shortcuts and platform-specific interaction may differ. Business rules may not.

## Release gate
A feature is not considered complete until:
1. Shared contract is defined.
2. Core/Application implementation exists where required.
3. Web client is integrated.
4. Desktop client is integrated.
5. Shared regression tests pass.
6. Cross-client parity test passes for calculated outputs.
