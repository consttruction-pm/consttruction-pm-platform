# CUBI Multilingual Language Support

## Required language set

The public website and authenticated visual workspace must support:

| Language | Tag | Native name | Direction | Locale |
|---|---|---|---|---|
| English | en | English | LTR | en-US |
| Persian | fa | فارسی | RTL | fa-IR |
| German | de | Deutsch | LTR | de-DE |
| Simplified Chinese | zh | 中文 | LTR | zh-CN |
| Arabic | ar | العربية | RTL | ar |
| French | fr | Français | LTR | fr-FR |
| Japanese | ja | 日本語 | LTR | ja-JP |
| Korean | ko | 한국어 | LTR | ko-KR |

## Coverage requirement

A language is not considered fully supported merely because it appears in a dropdown. Every published language must cover:
- Public website: Home, Platform, Solutions, Resources, Contact, Pricing, navigation, footer, checkout text, metadata, SEO titles/descriptions, Open Graph metadata, canonical and reciprocal hreflang links.
- Authenticated workspace: all global menus/submenus, toolbars, contextual command bars, window tabs, navigation tree, Details tabs and fields, dialogs, forms, tables, filters, group/sort, reports, charts, status messages, validation/errors, help and assistant surfaces.
- Bootstrap, sign-in/account flows and language preference persistence.
- Accessibility labels, tooltips, keyboard hints and empty/error/loading states.

## Direction, typography and locale behavior

- Persian and Arabic are RTL; all other listed languages are LTR.
- Direction is a UI presentation property and must not change project data, scheduling, project calendar, dates, or calculations.
- Use locale-aware number, date, time, currency and plural formatting without changing canonical stored values.
- Use appropriate font fallbacks and shaping: Arabic/Persian shaping, French diacritics, Japanese kana/kanji, Korean Hangul and Simplified Chinese glyphs.
- Mixed-direction content (activity IDs, codes, file paths, numbers and formulas) must use bidi isolation so identifiers remain readable.
- Switching language must preserve selected project/object, open windows, layout, filters, column widths, pane sizes, calendar selection and unsaved drafts.

## Delivery and release gates

- Language registry entries identify direction, locale, fallback and capability.
- UI translations are stored under stable translation IDs in versioned language packs and activated only after integrity/signature validation.
- Built-in language registry availability is distinct from a verified translation pack being installed.
- Public site route sets must not be published until every required page exists in that language. A language switcher must never lead to a dead route.
- Missing strings may use a clearly defined fallback during development, but fallback coverage is not a release-quality translation.
- Report translation coverage by locale and namespace; release requires 100% coverage of visible user-facing strings for every published locale, excluding approved proper nouns and technical identifiers.
- Test all eight locales, RTL/LTR, mobile and desktop breakpoints, date/number rendering, text expansion, truncation, focus order, screenshots and public SEO route integrity.

## Current implementation status (2026-11-02)

- Added ar, fr, ja, and ko to the workspace locale registry and language selector source.
- Browser-language detection recognizes the four additional locales.
- Arabic direction is registered as RTL; French, Japanese and Korean are LTR.
- The visual command shell resolves translated menu/toolbar strings from activated language-pack resources and uses the locale direction, including Arabic RTL.
- The example shared language registry lists all eight languages.
- Full translation resources for the four new languages have not yet been authored/activated.
- Public website routes remain restricted to English and Persian until the complete translated route sets and SEO metadata are supplied. The new languages must not be advertised on the public site before those routes are ready.
