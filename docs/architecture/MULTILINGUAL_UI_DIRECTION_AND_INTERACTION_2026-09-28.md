# Multilingual UI and Writing Direction — V1 Rule

Effective: 2026-09-28

## Product language model

The product is **fully multilingual**. Persian and English are only installed/example language packs; they are not the product language limit.

The language system uses the existing Language Registry and versioned language packs. Each pack is identified by a BCP-47 language tag and declares its writing direction metadata.

The same translation mechanism applies to:
- main menus and submenus;
- field names and user-entered field values where localization/display translation is applicable;
- tooltips and inline help;
- Smart Guide and other guidance content;
- dialogs, commands, statuses and validation/errors;
- reports and print labels;
- AI text/voice resources and offline language packs.

## Writing direction

Writing direction is a separate property from the language name. The UI must support:
- **LTR** — left-to-right writing;
- **RTL** — right-to-left writing;
- **Auto** — resolve from the language/script metadata, with explicit override available.

This follows the W3C internationalization model: direction metadata uses `ltr`, `rtl`, and `auto`; direction should not be inferred solely from the language code because a language can be represented with different scripts. citeturn279982search1turn279982search8

Therefore the implementation must never hard-code “fa = RTL, everything else = LTR” as the universal rule.

## Per-surface direction

Every interactive/textual surface must expose the direction setting:
- Menu
- Submenu
- Field label
- Field input/editor
- Field value/content
- Help/Smart Guide
- Tooltip
- Dialog/message
- Report/print text

For text inputs, `auto` is valid so mixed-script project data can be handled safely. Users can explicitly override a field to LTR or RTL when needed. W3C specifically documents per-form/per-input direction handling and `dir="auto"` for runtime-entered content. citeturn279982search0

## Layout behavior

Text direction must also drive directional layout behavior using logical start/end concepts rather than hard-coded left/right positioning. RTL is not merely “right-align the text”; the page and control flow must respond consistently while embedded LTR values such as codes, numbers and identifiers remain readable. citeturn279982search0turn279982search2

## Mouse/keyboard behavior

Writing direction does not change command semantics:
- left mouse click remains primary activation;
- right mouse click remains context menu;
- Enter/Space remains the keyboard activation equivalent;
- context actions remain permission-aware.

## Calculation boundary

Language, writing direction and presentation are UI concerns. Scheduling/P6, Calendar, Duration/Lag, Progress/EVM, Resource/Cost and Formula calculations remain authoritative in the Shared Domain/Calculation Core.

## V1 acceptance

Adding a new language or script must not require a change to domain calculation code. A language pack is usable only when its declared menu, field and help coverage and writing-direction behavior are tested.

