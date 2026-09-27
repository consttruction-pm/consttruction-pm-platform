# System Architecture

## Architectural baseline
The platform uses a Shared Domain/Calculation Core with strict separation of Domain, Application, Infrastructure and API layers.


## P6 parity architecture

P6 compatibility is implemented as a completeness layer over the Shared Domain/Calculation Core, not as UI-specific columns.

The core architecture shall include:
- a versioned P6 field registry by subject area;
- canonical typed field definitions with writable/read-only/filterable/orderable metadata;
- a reusable column/view/layout engine;
- typed custom fields/UDFs;
- a safe formula engine with AST/type checking/dependency graph/cycle detection;
- a single Shared Calendar/Unit subsystem for all calendar-aware calculations and conversions;
- a versioned calculation-options registry;
- a versioned import/export mapping registry for P6 and approved interoperability formats;
- conformance fixtures that prove data and calculation round trips.

The Field Registry is authoritative for Activity/WBS/Project/Resource/Role/Expense/Assignment/Calendar and other supported P6-equivalent subject areas. UI grids, APIs, reports and interchange adapters consume the registry rather than maintaining separate lists.

The product must never reduce a P6 field or option to a display-only label. A P6 field is complete only when its type, semantics, persistence, calculation behavior, permissions and interchange behavior are defined or explicitly dispositioned.

## Web-readiness
- Domain and calculation logic are UI-independent.
- Windows, PostgreSQL, filesystem and authentication are infrastructure concerns.
- Document storage and background jobs use abstractions.
- API contracts expose application use cases rather than database internals.
- Multi-tenant boundaries, optimistic locking and transaction boundaries are first-class concerns.

## Core modules
Calendar, Scheduling, WBS/Activities, Resources, Costs, Progress, EVM, Reporting, Documents, Users/Security, AI Assistant.