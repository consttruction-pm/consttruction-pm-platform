# Web Client

Stage 33.4 client foundation.

The Web client is a presentation/integration layer. It consumes versioned API/Application contracts and never reimplements Scheduling/P6, Progress/EVM, Resource/Cost, duration or calendar calculations.

Initial responsibilities:
- application shell and routing
- project/workspace navigation
- typed API contract consumption
- ProjectContext/session propagation
- stable error and conflict presentation
- Persian/English localization
- Jalali/Gregorian presentation
- parity with Desktop capabilities

Calculation authority remains in the Shared Domain/Calculation Core.


## Executable foundation — Stage 33.4.43

The Web client now has a framework-neutral TypeScript foundation under `src/`.
It provides a typed API transport that preserves tenant/project/revision context, stable API errors, and optional idempotency keys. It deliberately contains no scheduling, calendar, Progress/EVM, resource/cost, or financial calculation logic; those remain authoritative in the Shared Domain/Calculation Core.

This layer is the integration boundary for the future Web application shell and feature modules.
