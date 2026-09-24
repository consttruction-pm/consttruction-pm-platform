# Typed Client Adapter Contract v1

## Purpose

This contract defines the language-neutral adapter boundary that Web, Desktop, and Mobile implementations must consume. It does not introduce new business semantics.

The adapter is responsible for transport, serialization, ProjectContext propagation, revision/idempotency propagation, and stable error normalization.

Authoritative calculations remain in Shared Domain/Calculation Core and Application services.

## Request envelope

Every project-scoped mutation adapter must be able to carry:

- `contract_version`
- `operation`
- `context.tenant_id`
- `context.company_id`
- `context.project_id`
- `idempotency_key`
- optional `expected_revision`
- operation-specific `mutation`

The adapter must preserve explicit nullability and canonical decimal strings.

## Response envelope

The adapter must expose either:

1. a successful typed DTO with its contract version and revision, or
2. a normalized ApplicationError with:
   - category
   - code
   - message
   - retryable

Clients branch on category/code, never on localized message text.

## Mutation lifecycle

The adapter lifecycle is:

1. Validate required client-side shape only.
2. Attach current ProjectContext.
3. Attach a stable idempotency key for retryable mutation.
4. Attach expected revision when the resource is revisioned.
5. Send the versioned operation.
6. Normalize the authoritative response.
7. Surface `applied`, `replayed`, `conflict`, or `rejected` sync outcomes.
8. Update the client revision only from an authoritative response.
9. Preserve conflict information for explicit user resolution.

The adapter must not silently retry a mutation with a new idempotency key.

## Offline boundary

Offline clients persist the existing `offline-mutation.v1` shape. Queueing does not create a second business-logic path.

When reconnecting:

- retain the original idempotency key;
- retain the original expected revision;
- submit through the same authoritative mutation contract;
- treat conflict/rejection as an explicit outcome;
- do not locally recompute authoritative scheduling/resource/cost/progress results.

## Calendar boundary

Clients may read and edit versioned calendar references:

- `calendar_id`
- `calendar_version`
- `kind`

Clients do not perform calendar arithmetic. Effective calendar inheritance is resolved by the authoritative scheduling layer.

## Scheduling boundary

Until the authoritative scheduling API surface is released, the adapter exposes no client-owned Forward/Backward/Float calculation.

When scheduling integration is released, the adapter will transport authoritative inputs/results without reimplementing CPM semantics.

## Resource boundary

Resource and ResourceAssignment DTOs preserve decimal-like values as strings.

The client may format these values for display, but calculations such as remaining units/cost remain authoritative.

## Localization boundary

The adapter carries semantic values and stable error codes. UI layers own:

- Persian/English labels;
- Jalali/Gregorian display;
- number/date formatting;
- localized error messages.

Calendar/date arithmetic remains authoritative and must not be replaced by presentation formatting.

## Platform parity

Web, Desktop, and Mobile must implement equivalent adapter semantics for equivalent workflows. A platform-specific UX may differ, but the contract boundary and authoritative result semantics must remain aligned.
