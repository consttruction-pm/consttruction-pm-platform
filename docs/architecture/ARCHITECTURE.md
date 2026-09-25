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

## Global multilingual architecture

### Language-neutral core
Business rules, scheduling semantics, P6-compatible calculations, IDs, enum values, API contracts and persisted machine-readable fields must not depend on displayed language.

### Language registry
A central language registry defines BCP 47 language tag, localized display names, writing direction, locale/formatting rules, translation-pack version, AI/voice capability levels and fallback chain.

### Downloadable language packs
Language packs are versioned artifacts containing translation resources, terminology glossary, validation/error/help resources, report/print resources, locale metadata, checksum/signature, package size, release channel and rollback metadata. They support Web/PWA-capable offline assets where practical and Desktop/Mobile application packages.

### Preferred-language resolution
1. Explicit per-user preference.
2. Current device/app preference.
3. Tenant/project default when configured.
4. Environment locale.
5. Base/default language.
A user can override language per session.

### Offline performance
- Deterministic UI text loads from local resources first.
- Installed resources are cached locally.
- Only missing/new resources require network access.
- Language switching should not require an application restart unless technically required by the platform.
- Pack activation is atomic so a partial download cannot corrupt the active language.

### AI language layer
AI requests use a language-neutral internal contract containing input_language, output_language, project_language, terminology_profile, locale, voice_language, model_capabilities and provenance/audit context.
AI responses must preserve IDs, dates, numbers, activity codes, cost codes and other structured values exactly while translating presentation/linguistic content.

### Voice
Voice packs/models are independent from UI translation packs and are downloadable, versioned and device-capability aware. The client selects online or offline voice processing according to connectivity, installed pack and policy.

### Translation quality controls
- Controlled construction/project-controls glossary.
- Plural/gender/number rules where supported.
- RTL/LTR testing.
- Date/number/unit localization testing.
- Untranslated-string detection in CI.
- Language-pack compatibility tests.
- Snapshot/regression tests for core screens and reports.

## Cross-client parity
Web, Desktop and Mobile consume the same language contracts and terminology identifiers. Clients must not maintain divergent translation keys for the same product concept.