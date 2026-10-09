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


## GitHub Codespaces preview

From the repository root:

```bash
cd apps/web
npm install
npm run preview
```

The command builds the Web client and starts a dependency-free HTTP preview server on port **4173**. In GitHub Codespaces, open the forwarded **4173** port in the browser.

The preview serves the existing CUBI landing page and the compiled Web client exactly from the repository build output. It does not add a browser-side scheduling, calendar, P6, Progress/EVM, Resource/Cost or financial calculation engine.

> Runtime integration status: the workspace-control-room endpoint is implemented in the Python HTTP route layer (`GET /api/v1/workspace/control-room/read`), and the browser client calls that same path. However, the Codespaces preview is a static Web preview; it does not start or configure the Python backend. The production composition function also accepts `backend_p0_api` as an optional dependency, so a deployment must explicitly supply a configured `BackendP0API` along with authenticated lifecycle/session and persistence dependencies. Until that runtime composition is deployed and verified end to end, the existence of route/unit tests must not be treated as proof that opening a real project workspace works in production.
