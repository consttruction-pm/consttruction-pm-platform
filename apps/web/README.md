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
