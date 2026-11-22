# Ten product locales in both environments — 2026-11-22

## What changed

Mission rule 7 requires every locale (`fa`, `en`, `de`, `fr`, `zh`, `ja`, `ko`,
`ru`, `ar`, `tr-TR`) with the right direction, dates, numbers, sorting and
terminology. Both environment documents already carried ten dictionaries; the
browser run only exercised `en` and `fa`. The journeys now sweep all ten.

| Layer | File | Change |
| --- | --- | --- |
| Workbench journey | `apps/web/e2e/preview-e2e.mjs` | set every locale, assert `lang`, `dir`, five studios, Persian ≠ English shell |
| Enterprise journey | same | set every locale, assert `lang` (incl. `tr-TR`), `dir`, no Engineering root, translated sidebar |
| Sorting | `apps/web/src/enterprise-records.test.ts` | German collation proven against code-point order |

## Observations recorded by the run

- Workbench: `en:ltr`, `fa:rtl`, `de:ltr`, `zh:ltr`, `ar:rtl`, `fr:ltr`,
  `ja:ltr`, `ko:ltr`, `ru:ltr`, `tr:ltr`; five studios in every locale.
- Enterprise: the same ten locales keep their own document, set `html lang`
  (`tr` → `tr-TR`) and translate the sidebar for every non-English locale.
- The Personal Workbench and Engineering shells already use the shared
  localization catalog for the remaining eight locales; this slice verifies the
  two documents the mission owns rather than re-translating them.

## Verification

- `npm test` — 1299 + 16 passed (one new collation case)
- `npm run typecheck` — clean
- `CUBI_CHROME_NO_SANDBOX=1 npm run test:e2e:preview` — 127 recorded checks,
  including:
  - `locale switch covers all ten product locales, keeps the five studios and flips direction`
  - `Enterprise locale switch serves all ten product locales in its own document`

## Not claimed

Numbers and dates are formatted with `Intl` in the shared helpers
(`formatDateTime`, `formatDate`); this slice asserts direction, language and
terminology, not a pixel comparison of every numeric format. A locale whose
catalog lacks a specific page string still falls back to English, and the
Workbench transcript flags that fallback where it applies.
