# Desktop Client

Stage 33.4 client foundation.

The Desktop client is a presentation/integration layer using the same versioned API/Application contracts and Shared Domain/Calculation Core semantics as the Web client.

Initial responsibilities:
- application shell and routing/workspace
- typed API contract consumption
- ProjectContext/session propagation
- stable error and optimistic-lock conflict presentation
- Persian/English localization
- Jalali/Gregorian presentation
- offline-capable presentation features where explicitly supported
- capability parity with Web

The Desktop client must not create an alternative Scheduling/P6, Progress/EVM, Resource/Cost or calendar calculation engine.


## Stage 33.4.45

The executable TypeScript foundation provides a project runtime with explicit online/offline state and revision continuity. It is intentionally framework-neutral so the eventual Windows shell can consume the same boundary without introducing client-specific business calculations.
