# ACT-003 filters — typed values, Optimize and Duplicate (2026-11-13)

- Contract: `cubi-activity-filters-v26.v2`
- Tested code: `d9452209ac3b30cc397fd115f54812cbe7bed7a7` (code commit; evidence is committed separately)
- Environment: local full-stack preview, `python3 -m construction_pm.preview --web-root apps/web --port 4226 --database /tmp/cubi-act003f.sqlite --reset`, tenant `cubi-preview-tenant`, project `preview-rps-01` (14 activities)
- Help topics:
  - [Create a filter](https://docs.oracle.com/cd/G48902_01/client_help/en_US/create_a_filter.htm): Parameter / Is / Value rows, Add, the Value field, "To review your filter criteria to eliminate redundancy, from the Display Options bar, choose Optimize", and "To make this filter available to all users, select it, then click Make Global in the Filters dialog box."
  - [Create a lookahead filter](https://docs.oracle.com/cd/G48902_01/client_help/en_US/create_a_lookahead_filter.htm): All/Any, Replace vs Highlight.
- CUBI component: Activities → View → Filter By → Customize (Filters dialog).
- Code path: `apps/web/src/workspace-activity-filters.ts` (choice values, Optimize, Duplicate) → `apps/web/src/workspace-dialogs.ts` (picker markup, renumbering, footer and Optimize button, layout patch) → `apps/web/src/workspace-desktop-shell.ts` (change/preview/optimize wiring) → `WorkspacePresentation.filters` saved with the Activities layout → `applyActivityFilterState` / `filterAndSortActivities` in `apps/web/src/workspace-view.ts`.
- Persistence / API boundary: the dialog still submits through `readLayoutPatch` and the existing saved-layout metadata (`GET|POST /api/projects/{id}/p6/layouts/{scope}/activity`). No activity row, date, duration, relationship or other schedule input is written; filtering is display-only.
- Permissions: saving a filter uses the same `PROJECT_WRITE` path as the layout; the Viewer path is unchanged and out of scope for this slice.
- Slice delivered:
  - `activityFilterChoiceValues` supplies the stored values for Activity Status (`Not Started`, `In Progress`, `Completed`), Activity Type (six values) and Critical (`true`/`false`).
  - The Value cell for a list parameter is a `select[name="filter.value.N"][data-filter-choice]` with a "Select a value" placeholder and Yes/No labels for the flag. An unknown stored value is preserved as an extra option; `is-empty`/`is-not-empty` disable the picker. `syncFilterField` swaps the Value cell type when the parameter changes, and renumbering also renames select values.
  - `optimizeActivityFilterCriteria` drops blank rows only when a complete criterion remains, collapses exact duplicates, and removes criteria implied by another: with All, `equals X` is kept over `contains X`, the longer `contains` is kept, and `not-contains X` is kept over `not-equals X`; with Any, the broader criterion is kept. Matching is unchanged (unit test compares filtered ids and the browser compares preview counts).
  - `duplicateActivityFilter` stores "Name (copy)" in the same scope with a unique id and selects it; built-in filters stay read-only.
- Browser scenarios (`apps/web/e2e/activity-filters-v26.mjs`, 12/12 pass, 0 exceptions / 0 console errors / 0 5xx):
  1. Manager and editor surfaces, including the new Duplicate action and Optimize button; no overflow.
  2. Date/relative validation before Apply.
  3. Compound lookahead saved and applied; grid count equals preview.
  4. Filter and result survive a full reload.
  5. Any + Highlight keeps all rows and highlights the match set.
  6. All Activities clears filtering and highlighting.
  7. Row Add/Move/Delete renumbering; Cancel is exact.
  8. Persian RTL editor at 1280×720 without overflow.
  9. English editor at 1920×1080 without overflow.
  10. Activity Status renders a picker (no text input), the Critical flag offers Yes/No, the picked value previews 1 of 14, saving applies exactly that count, and the value reloads in the picker after a full reload and through Modify.
  11. All-mode Optimize removes an implied `contains` criterion (status "Removed 1 redundant criteria."), leaves the match count unchanged, collapses an exact duplicate, and reports "No redundant criteria found" on a clean filter.
  12. Duplicate keeps "Six-Week Lookahead", adds and selects "Six-Week Lookahead (copy)", and the copy survives a full reload.
- Screenshots: `01`…`11` in this folder; scenario 10 = `08-filter-choice-picker-en-1366.png`, `09-filter-choice-reload-en-1366.png`; scenario 11 = `10-filter-optimize-en-1366.png`; scenario 12 = `11-filter-duplicate-en-1366.png`.
- Unit tests at the same code: 999 `tsx` + 14 `node --test` pass; `npx tsc --noEmit` and `npm run build` pass.
- Remaining gaps: Make Global still changes only the within-project scope label (no tenant-wide sharing; backend contract needed); nested AND/OR groups are not modelled; criterion-level copy/paste is not offered; Optimize compares only the text containment family (not numeric/date bounds); the saved filter list has no reorder action beyond the existing name/select sort.
