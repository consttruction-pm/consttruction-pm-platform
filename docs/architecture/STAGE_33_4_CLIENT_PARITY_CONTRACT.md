# Stage 33.4 — Cross-Client Parity Contract

Date: 2026-09-24

## Authority

Web, Desktop and Mobile are first-class clients. They consume the same versioned API/Application contracts and Shared Domain/Calculation Core semantics.

The canonical contract is `shared/contracts/client-parity.schema.json` (v1).

## Rules

- Scheduling/P6 semantics are Shared Core authoritative.
- Progress/EVM semantics are Shared Core authoritative.
- Resource/Cost semantics are Shared Core authoritative.
- ProjectContext carries tenant, project and revision context.
- Web, Desktop and Mobile remain distinct UX surfaces but cannot redefine shared calculation semantics.
- Desktop may execute approved Shared Core workflows offline.
- Mobile may execute only approved offline workflows using the same portable Shared Core semantics.
- Localization and Jalali/Gregorian presentation remain client concerns; calendar arithmetic remains Shared Core.
- Capability differences must be explicit in contracts and covered by parity tests.

## Completion gate

The client-integration track is not complete until contract parsing, context propagation, capability parity and applicable Web/Desktop/Mobile regression tests pass.
