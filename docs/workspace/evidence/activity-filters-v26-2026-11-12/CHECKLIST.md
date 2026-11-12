# ACT-003 — Filters, compound conditions and saved filters (2026-11-12)

- Contract: `cubi-activity-filters-v26.v1`
- Suite: `apps/web/e2e/activity-filters-v26.mjs`
- Tested code: `857221097f4e6cbb878f225b3f409ad4aedec01f` (`85722109`)
- Fixture: local-full-stack preview, `preview-rps-01`, 14 activity rows, English LTR unless stated
- Help sources: [Create a filter](https://docs.oracle.com/cd/G48902_01/client_help/en_US/create_a_filter.htm), [Create a lookahead filter](https://docs.oracle.com/cd/G48902_01/client_help/en_US/create_a_lookahead_filter.htm)

| # | Scenario | Cell | Result |
|---|---|---|---|
| 01 | The manager and editor expose the version 26 surfaces (two starter rows, default/global/layout/user groups, six manager actions, Add/Delete/Move, six-column head, live preview, no overflow) | 1366×768 en LTR | PASS |
| 02 | The editor validates typed and relative dates before Apply (Start offers `is within range of` and no text operators; missing High value is invalid; `next week` rejected; `CS`…`CS+6w` valid with a partial match) | 1366×768 en LTR | PASS |
| 03 | Add and the High value column save a compound lookahead filter (Start range + Activity % Complete not equal to 100, saved as `Six-Week Lookahead`, grid row count equals the preview count, saved list contains the name) | 1366×768 en LTR | PASS |
| 04 | The saved filter and its result survive a full reload | 1366×768 en LTR | PASS |
| 05 | Any selected filter combined with Highlight keeps every row and highlights only the match set | 1366×768 en LTR | PASS |
| 06 | All Activities clears the filter and the highlight (14 rows, zero highlighted) | 1366×768 en LTR | PASS |
| 07 | Criterion rows renumber when moved and deleted (Add×2 → four rows, move up, delete, join labels renumber, Cancel leaves the saved catalogue unchanged) | 1366×768 en LTR | PASS |
| 08 | The editor renders in a Persian RTL cell without overflow (`در بازهٔ`, `dir=rtl`) | 1280×720 fa RTL | PASS |
| 09 | The dialog fits a 1920×1080 cell with no horizontal overflow | 1920×1080 en LTR | PASS |

Machine-readable report: `activity-filters-v26.json` — 9/9 scenarios pass, `testedCodeSha` = `gitHead` = `857221097f4e6cbb878f225b3f409ad4aedec01f`, zero exceptions, zero console errors, zero API failures. Screenshots: `01`–`07`.
