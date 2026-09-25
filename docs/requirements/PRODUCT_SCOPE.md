# Product Scope

Construction project management and construction control platform.

## Primary requirements
- Global multilingual support for the public website, product UI, stored project data labels/metadata where applicable, AI assistant, Smart Guide, voice workflows, reports and notifications.
- Persian and English remain first-class; the architecture must support adding any future language through downloadable language packs rather than code changes.
- Jalali/Shamsi and Gregorian calendars.
- Enterprise scheduling comparable to Primavera P6.
- WBS, activities, Gantt, relationships, automatic scheduling.
- Work calendars, resources, costs, Excel import/export and user management.
- Remote daily reports and controlled web access.
- Documentation, OCR, revisions, RFI, Submittal, delay claims and audit trail.
- AI assistant, Smart Guide and voice-assisted data entry with multilingual input/output.

## Global language architecture
- Every user has a preferred language and optional fallback language chain.
- Language identifiers use BCP 47-compatible tags.
- Website language is selectable independently and can remember visitor preference.
- Desktop and mobile applications expose a language manager with downloadable, versioned, signed language packs.
- The preferred language pack can be downloaded once and then used locally/offline for UI, standard terminology, help content, validation messages, reports and deterministic text.
- Switching language must not require reinstalling the application.
- Language packs are cacheable and incrementally updatable.
- The system falls back to a default/base language only when a requested translation is absent.
- Project data must never be corrupted or reinterpreted when UI language changes.
- Dates, calendars, number formats, units, names and locale formatting are separate concerns from translation text.

## Multilingual AI
- AI Assistant and Smart Guide support the same language-pack architecture and a language-neutral semantic contract.
- AI input may be in one supported language and output may be requested in another.
- Offline-capable AI features use downloadable language/model packs appropriate to device capability.
- Online AI may access newer language/model capabilities, but must preserve project-language, permissions, provenance and audit rules.
- AI terminology uses a controlled glossary so P6/project-controls/construction terms remain semantically stable across languages.
- Voice input/output uses language-specific packs/models and supports offline operation where a pack exists.
- Language/model packs require version, compatibility range, checksum/signature, download size and rollback metadata.

## Compatibility principle
For functionality overlapping Primavera P6, P6 logic is the baseline and calculations must be testable against it.