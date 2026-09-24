# System Architecture

## Architectural baseline
The platform uses a Shared Domain/Calculation Core with strict separation of Domain, Application, Infrastructure and API layers.

## Web-readiness
- Domain and calculation logic are UI-independent.
- Windows, PostgreSQL, filesystem and authentication are infrastructure concerns.
- Document storage and background jobs use abstractions.
- API contracts expose application use cases rather than database internals.
- Multi-tenant boundaries, optimistic locking and transaction boundaries are first-class concerns.

## Core modules
Calendar, Scheduling, WBS/Activities, Resources, Costs, Progress, EVM, Reporting, Documents, Users/Security, AI Assistant.