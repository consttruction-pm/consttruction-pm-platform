# Web Client

Stage 33.4 client foundation.

The Web client is a presentation/integration layer. It consumes versioned API/Application contracts and never reimplements Scheduling/P6, Progress/EVM, Resource/Cost, duration or calendar calculations.

Initial responsibilities:
- application shell and routing
- project/workspace navigation
- typed API contract consumption
- ProjectContext/session propagation
- stable error and conflict presentation
- fully multilingual localization with language-pack fallback and RTL/LTR text direction
- Jalali/Gregorian presentation
- parity with Desktop capabilities

Calculation authority remains in the Shared Domain/Calculation Core.


## Executable foundation — Stage 33.4.43

The Web client now has a framework-neutral TypeScript foundation under `src/`.
It provides a typed API transport that preserves tenant/project/revision context, stable API errors, and optional idempotency keys. It deliberately contains no scheduling, calendar, Progress/EVM, resource/cost, or financial calculation logic; those remain authoritative in the Shared Domain/Calculation Core.

This layer is the integration boundary for the future Web application shell and feature modules.

## V1 Beta executable preview

The V1 Web Beta now has a minimal executable browser entry point:
- index.html — browser entry and locale/calendar toolbar.
- src/app.ts — deterministic demo project bootstrap using the existing Workspace model/renderer.
- tsconfig.build.json — browser build output to dist/.
- dev-server.ts — dependency-light static server for local preview.

Run from apps/web/:

```bash
npm install
npm run dev
```

The preview intentionally uses demo project data and the existing authoritative contracts. It does not introduce client-side Scheduling/P6, Progress/EVM, Resource/Cost or Formula calculation logic.

The full production/API wiring remains part of the V1 audit and Beta gates tracked in Issue #459.
