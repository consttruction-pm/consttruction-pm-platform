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


## Stage 33.4.47 — Desktop Language Manager

The Desktop presentation layer now exposes a concrete native-shell-ready Language Manager surface. It is declarative and framework-neutral by design: a Windows/WPF/WinUI/Electron/Tauri host can render the surface without reimplementing language business rules.

Supported presentation commands:
- Use an installed verified language pack.
- Download the compatible catalog version.
- Update when a newer compatible version exists.
- Remove an inactive verified pack; the shared Controller still blocks removal of the active pack.
- Present localized errors, progress, locale, direction, and AI/Voice/offline capability state.

The Desktop view consumes the shared Language Manager Adapter and never performs project, schedule, cost, calendar, or other authoritative business calculations.
