# Multilingual UI, Text Direction and Mouse Interaction — V1 Rule

Effective: 2026-09-28

## Product rule

The product is **multilingual**, not bilingual. Persian/English are initial installed language examples only. The architecture must accept additional BCP-47 language tags through the existing Language Registry and versioned language packs.

The same language mechanism applies to:
- main menus and submenus;
- field names, field values where translated display is appropriate, tooltips and validation messages;
- Smart Guide/help content;
- reports, dialogs, commands, statuses and errors;
- offline language packs and future AI/voice resources.

## Language resolution

1. Resolve the user's preferred language tag.
2. Follow its configured fallback chain.
3. Use the default language only when the configured chain has no verified installed pack.
4. Never infer that only `fa` and `en` are supported.
5. Untranslated keys fall back through the configured language-pack chain; they are not silently duplicated as new hard-coded language-specific implementations.

## Direction

Direction is independent from language identity.

Every textual UI surface supports:
- `auto` — resolve from the language/script;
- `ltr`;
- `rtl`.

Text input fields must permit explicit per-field direction override when project data contains mixed scripts (for example a Persian description containing an English code).

Project UI direction and individual field/input direction are separate concerns.

## Mouse and keyboard

Every interactive menu, submenu, field editor, help/guide control and command follows the same interaction contract:
- left mouse button: primary activation;
- right mouse button: context menu;
- Enter/Space: keyboard equivalent of primary activation;
- context actions remain permission-aware;
- right-click must never bypass authorization or authoritative business rules.

The shared UI interaction contract is defined in `shared/contracts/ui-text-and-interaction.schema.json`.

## Calculation boundary

Multilingual rendering, direction and interaction handling are presentation concerns. Scheduling/P6, Calendar, Duration/Lag, Progress/EVM, Resource/Cost and Formula calculations remain in the Shared Domain/Calculation Core.

## V1 acceptance

A new language does not require changes to domain/calculation code. A language pack is considered usable only when menu/submenu, fields, help, reports and validation strings are covered at the declared language-pack scope, with fallback behavior tested.

