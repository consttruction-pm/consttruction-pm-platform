# Canonical Cross-Client Scheduling Adapter

## Purpose

Issue #1249 establishes one versioned scheduling request/result seam for Web, Desktop and Mobile.

The authoritative scheduling implementation remains the Shared Domain/Calculation Core. Client adapters only validate/transport typed contracts and delegate to the Core.

## Canonical contract

Request contract:
- `constructionpm://contracts/time-scheduling/v1`
- contract version `1.0`
- explicit project scope: tenant_id, project_id, revision
- calculation context: schedule mode, project start/finish, Data Date, precision/rounding, calendar references and schedule options
- typed activity durations
- FS/SS/FF/SF relationships with signed Decimal-like lag/lead
- versioned activity and relationship-lag calendar references
- six P6-aligned datetime constraints

Result contract:
- `constructionpm://contracts/time-scheduling-result/v1`
- contract version `1.0`
- original project scope
- authoritative calculation fingerprint
- project finish
- typed activity start/finish/duration/float/criticality

## Client boundary

`apps/client-sync/src/scheduling-adapter.ts` is the canonical TypeScript adapter contract.

Web:
- `apps/web/src/shared-scheduling-adapter.ts`

Desktop:
- `apps/desktop/src/shared-scheduling-adapter.ts`

Mobile:
- `apps/mobile/src/shared-scheduling-adapter.ts` is a compatibility shim over the canonical adapter.

No client adapter contains CPM, calendar arithmetic, EVM, resource, cost or financial calculations.

## Parity evidence

`shared/contracts/time-scheduling-parity.fixture.json` is the shared request/result fixture.

The Web, Desktop and Mobile/client-sync regression tests consume the same fixture and validate:
- contract version
- project tenant/project/revision scope
- typed duration/lag values
- authoritative result identity
- rejection of version/scope mismatch
- unchanged delegation to the Shared Core

## Compatibility rule

Older Mobile naming is preserved only as a compatibility alias. It is not a second semantic contract.

Any future change to scheduling request/result semantics must change the shared versioned contract first, update the common fixture/tests, then update all three client adapters without introducing client-specific calculations.

## Acceptance gate

Issue #1249 closes only after exact-head Client Typecheck and ConstructionPM CI are green on the merged head.

This document does not claim Oracle certification; it records an internal engineering parity contract.
